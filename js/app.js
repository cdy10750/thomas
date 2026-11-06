/* Bisaya for Thomas - static self-study app.
 * Data: data/weeks.json + data/weekNN.json. Audio: audio/wNN/<ID>.mp3.
 * Progress and review schedule are stored in localStorage (key below). */
(function () {
  "use strict";

  var STORE_KEY = "bisaya-thomas-v1";
  var REVIEW_CAP = 12;                       // about 10 minutes of review
  var INTERVAL = { 1: 1, 2: 3, 3: 7, 4: 14, 5: 30 }; // Leitner box -> days until next review
  var TYPE_RANK = { listen_meaning: 0, scene: 1, respond: 2, fill: 3, order: 4 };
  var SPEAKER_LABEL = {
    Thomas: "You (Thomas)", Jiana: "Jiana", Nanay: "Nanay (Mom)", Tatay: "Tatay (Dad)",
    Kuya: "Kuya (big brother)", Dodong: "Dodong (little brother)", Inday: "Inday (little sister)",
    Tindera: "Tindera (vendor)"
  };
  var FEMALE = { Jiana: 1, Nanay: 1, Inday: 1, Tindera: 1 };

  var app = document.getElementById("app");
  var player = document.getElementById("player");
  var toastEl = document.getElementById("toast");
  var backBtn = document.getElementById("backBtn");
  var topTitle = document.getElementById("topTitle");
  var topProgress = document.getElementById("topProgress");
  var topProgressFill = document.getElementById("topProgressFill");

  var weeks = [];        // from weeks.json
  var data = {};         // week number -> week json
  var items = {};        // id -> { id, ceb, en, speaker, scene, tip, lit, week }
  var exIndex = {};      // exercise key -> exercise (with week/day)
  var progress = loadProgress();
  var session = null;

  /* ---------- utilities ---------- */
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function today() { var d = new Date(); return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function addDays(iso, n) {
    var p = iso.split("-"); var d = new Date(+p[0], +p[1] - 1, +p[2] + n);
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }
  function shuffle(a) {
    a = a.slice();
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }
  function norm(s) { return s.toLowerCase().replace(/[^a-z0-9'\- ]/g, " ").replace(/\s+/g, " ").trim(); }
  function el(tag, attrs) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (k === "class") e.className = attrs[k];
      else if (k === "text") e.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") e.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] === true) e.setAttribute(k, "");
      else if (attrs[k] !== false && attrs[k] != null) e.setAttribute(k, attrs[k]);
    }
    for (var i = 2; i < arguments.length; i++) {
      var c = arguments[i];
      if (c == null || c === false) continue;
      if (Array.isArray(c)) c.forEach(function (x) { if (x) e.appendChild(typeof x === "string" ? document.createTextNode(x) : x); });
      else e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    }
    return e;
  }
  function clear() { app.innerHTML = ""; window.scrollTo(0, 0); }
  var toastTimer;
  function toast(msg) {
    toastEl.textContent = msg; toastEl.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { toastEl.hidden = true; }, 2600);
  }

  /* ---------- storage ---------- */
  function loadProgress() {
    var p = null;
    try { p = JSON.parse(localStorage.getItem(STORE_KEY)); } catch (e) { p = null; }
    p = p || {};
    p.done = p.done || {}; p.srs = p.srs || {}; p.streak = p.streak || { last: null, count: 0 };
    p.missions = p.missions || {}; p.totals = p.totals || { answered: 0, correct: 0, minutes: 0 };
    p.settings = p.settings || {}; if (p.settings.sfx === undefined) p.settings.sfx = true;
    return p;
  }
  function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(progress)); } catch (e) { /* storage unavailable */ } }

  /* ---------- audio ---------- */
  var playingBtn = null, playQueue = null, lastAudioError = 0;
  function audioSrc(id) { var it = items[id]; return "audio/w" + pad(it ? it.week : 1) + "/" + id + ".mp3"; }
  function stopAudio() {
    playQueue = null; player.pause();
    if (playingBtn) playingBtn.classList.remove("playing"); playingBtn = null;
    document.querySelectorAll(".dialogue-line.active").forEach(function (n) { n.classList.remove("active"); });
  }
  function play(id, slow, btn, keepQueue) {
    if (!keepQueue) playQueue = null;
    if (playingBtn) playingBtn.classList.remove("playing");
    playingBtn = btn || null;
    if (btn) btn.classList.add("playing");
    player.src = audioSrc(id);
    var rate = slow ? 0.75 : 1;
    player.defaultPlaybackRate = rate; player.playbackRate = rate;
    if ("preservesPitch" in player) player.preservesPitch = true;
    var pr = player.play();
    if (pr && pr.catch) pr.catch(function () { /* autoplay blocked or missing file: handled by error event */ });
  }
  player.addEventListener("loadedmetadata", function () { player.playbackRate = player.defaultPlaybackRate; });
  player.addEventListener("ended", function () {
    if (playingBtn) playingBtn.classList.remove("playing"); playingBtn = null;
    if (playQueue && playQueue.length) { var next = playQueue.shift(); setTimeout(function () { next(); }, 450); }
  });
  player.addEventListener("error", function () {
    if (playingBtn) playingBtn.classList.remove("playing"); playingBtn = null;
    if (Date.now() - lastAudioError > 3000) toast("Audio for this phrase isn't available yet.");
    lastAudioError = Date.now();
    if (playQueue && playQueue.length) { var next = playQueue.shift(); setTimeout(next, 300); }
  });

  /* Answer sound effects, synthesized with Web Audio (no files needed). */
  var sfxCtx = null;
  function sfx(correct) {
    if (!progress.settings.sfx) return;
    try {
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return;
      sfxCtx = sfxCtx || new AC();
      if (sfxCtx.state === "suspended") sfxCtx.resume();
      var t0 = sfxCtx.currentTime + 0.01;
      var notes = correct ? [[880, 0, 0.13], [1318.5, 0.11, 0.22]]   // A5 -> E6: bright two-note chime
                          : [[196, 0, 0.16], [164.8, 0.14, 0.24]];   // G3 -> E3: low, short "uh-oh"
      notes.forEach(function (n) {
        var osc = sfxCtx.createOscillator(), gain = sfxCtx.createGain();
        osc.type = correct ? "sine" : "triangle";
        osc.frequency.value = n[0];
        var a = t0 + n[1], z = a + n[2];
        gain.gain.setValueAtTime(0.0001, a);
        gain.gain.exponentialRampToValueAtTime(correct ? 0.25 : 0.3, a + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.0001, z);
        osc.connect(gain); gain.connect(sfxCtx.destination);
        osc.start(a); osc.stop(z + 0.02);
      });
    } catch (e) { /* sound effects are optional */ }
  }

  var ICON_PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>';
  function audioRow(id, opts) {
    opts = opts || {};
    var playBtn = el("button", { class: "audio-btn", type: "button" });
    playBtn.innerHTML = ICON_PLAY + "<span>Play</span>";
    playBtn.addEventListener("click", function () { play(id, false, playBtn); });
    var slowBtn = el("button", { class: "audio-btn slow", type: "button", "aria-label": "Play slowly (0.75x)" }, "Slow");
    slowBtn.addEventListener("click", function () { play(id, true, slowBtn); });
    if (opts.autoplay) setTimeout(function () { play(id, false, playBtn); }, 250);
    return el("div", { class: "audio-row" }, playBtn, slowBtn);
  }
  function miniPlay(id) {
    var b = el("button", { class: "audio-btn mini", type: "button", "aria-label": "Play" });
    b.innerHTML = ICON_PLAY;
    b.addEventListener("click", function () { play(id, false, b); });
    return b;
  }
  function speakerTag(sp) {
    return el("span", { class: "speaker-tag " + (FEMALE[sp] ? "f" : "m"), text: SPEAKER_LABEL[sp] || sp });
  }

  /* ---------- data loading ---------- */
  function fetchJSON(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(url + " " + r.status); return r.json();
    });
  }
  function indexWeek(d) {
    var w = d.week;
    data[w] = d;
    d.chunks.forEach(function (c) { items[c.id] = Object.assign({ week: w }, c); });
    d.dialogues.forEach(function (dlg) {
      dlg.lines.forEach(function (ln) { if (ln.id) items[ln.id] = Object.assign({ week: w, scene: dlg.scene }, ln); });
    });
    d.days.forEach(function (day) { dayExercises(w, day.day).forEach(function (ex) { exIndex[ex.key] = ex; }); });
  }
  function dayExercises(w, dayNum) {
    var d = data[w], day = d.days[dayNum - 1], list = [];
    var pre = "W" + pad(w) + "-d" + dayNum;
    day.new.forEach(function (cid) { list.push({ key: pre + "-lm-" + cid, type: "listen_meaning", ref: cid, week: w, day: dayNum }); });
    day.exercises.forEach(function (ex, i) { list.push(Object.assign({ key: pre + "-e" + (i + 1), week: w, day: dayNum }, ex)); });
    list.forEach(function (ex, i) { ex._i = i; });
    list.sort(function (a, b) { return (TYPE_RANK[a.type] - TYPE_RANK[b.type]) || (a._i - b._i); });
    return list;
  }

  /* ---------- progress helpers ---------- */
  function isDone(w, d) { return !!progress.done[w + "-" + d]; }
  function nextLesson() {
    for (var i = 0; i < weeks.length; i++) {
      var w = weeks[i].week; if (!data[w]) continue;
      for (var d = 1; d <= data[w].days.length; d++) if (!isDone(w, d)) return { week: w, day: d };
    }
    return null;
  }
  function dayUnlocked(w, d) {
    if (d > 1) return isDone(w, d - 1);
    if (w === 1) return true;
    var prev = data[w - 1]; return !prev || isDone(w - 1, prev.days.length);
  }
  function dueReviews(excludeKeys) {
    var t = today(), out = [];
    for (var k in progress.srs) {
      if (!exIndex[k] || (excludeKeys && excludeKeys[k])) continue;
      if (progress.srs[k].due <= t) out.push(k);
    }
    out.sort(function (a, b) {
      var A = progress.srs[a], B = progress.srs[b];
      return A.due < B.due ? -1 : A.due > B.due ? 1 : A.box - B.box;
    });
    return out;
  }
  function learnedPhraseCount() {
    var n = 0;
    for (var w in data) data[w].days.forEach(function (day) { if (isDone(+w, day.day)) n += day.new.length; });
    return n;
  }
  function grade(ex, correct) {
    var t = today(), rec = progress.srs[ex.key];
    if (!rec) rec = { box: 1, due: addDays(t, 1) };                 // brand new: see it again tomorrow
    else if (correct) { rec.box = Math.min(rec.box + 1, 5); rec.due = addDays(t, INTERVAL[rec.box]); }
    else { rec.box = 1; rec.due = addDays(t, 1); }
    rec.last = t;
    progress.srs[ex.key] = rec;
    progress.totals.answered++; if (correct) progress.totals.correct++;
    save();
  }

  /* ---------- top bar ---------- */
  function setTop(title, inSession) {
    topTitle.textContent = title;
    backBtn.hidden = !inSession; topProgress.hidden = !inSession;
  }
  function setBar(frac) { topProgressFill.style.width = Math.round(Math.max(0, Math.min(1, frac)) * 100) + "%"; }
  backBtn.addEventListener("click", function () {
    function leave() { stopAudio(); session = null; renderHome(); }
    if (session && !session.finished) {
      askConfirm("Leave this lesson?", "Your answers so far are saved, but the lesson won't be marked as done.", "Leave lesson", leave);
    } else leave();
  });

  /* In-page confirmation (browser confirm() dialogs are not available everywhere). */
  function askConfirm(title, text, okLabel, onOk) {
    var old = document.getElementById("confirmBox"); if (old) old.remove();
    var box = el("div", { class: "overlay", id: "confirmBox", role: "dialog", "aria-modal": "true", "aria-label": title });
    function close() { box.remove(); }
    var ok = el("button", { class: "btn primary", type: "button", onclick: function () { close(); onOk(); } }, okLabel);
    box.appendChild(el("div", { class: "card overlay-card" },
      el("h2", { text: title }), el("p", { class: "muted", text: text }),
      el("div", { class: "btn-row" }, el("button", { class: "btn", type: "button", onclick: close }, "Cancel"), ok)));
    box.addEventListener("click", function (e) { if (e.target === box) close(); });
    document.body.appendChild(box);
    ok.focus();
  }

  /* ---------- HOME ---------- */
  function renderHome() {
    stopAudio(); session = null; setTop("Bisaya for Thomas", false); clear();
    var next = nextLesson();
    var hero;
    if (next) {
      var d = data[next.week], day = d.days[next.day - 1];
      hero = el("section", { class: "card hero" },
        el("div", { class: "eyebrow", text: "Today - Week " + next.week + ", Day " + next.day }),
        el("h1", { text: day.title }),
        el("p", { class: "muted small", text: day.new.length
          ? day.new.length + " new phrases, then review and reading aloud. About 30 minutes."
          : "Conversations, review, and your video-call mission. About 30 minutes." }),
        el("button", { class: "btn primary block", type: "button", onclick: function () { startDay(next.week, next.day); } }, "Start today's lesson"));
    } else {
      hero = el("section", { class: "card hero" },
        el("div", { class: "eyebrow", text: "All caught up" }),
        el("h1", { text: "You've finished every lesson available so far." }),
        el("p", { class: "muted small", text: "Keep your reviews going every day. New weeks will appear here." }));
    }
    app.appendChild(hero);

    var due = dueReviews().length;
    app.appendChild(el("section", { class: "card" },
      el("div", { class: "section-label" }, el("h2", { text: "Review" }), el("span", { class: "muted small", text: due + " due" })),
      el("p", { class: "muted small", text: due
        ? "Phrases you missed or learned recently come back here at growing intervals."
        : "Nothing due right now. Missed and new phrases will show up here on the next days." }),
      el("button", { class: "btn block", type: "button", disabled: !due, onclick: startReview }, due ? "Review now (" + Math.min(due, REVIEW_CAP) + ")" : "No reviews due")));

    var daysDone = Object.keys(progress.done).length;
    var acc = progress.totals.answered ? Math.round(100 * progress.totals.correct / progress.totals.answered) + "%" : "-";
    var streak = progress.streak.last && progress.streak.last >= addDays(today(), -1) ? progress.streak.count : 0;
    app.appendChild(el("section", { class: "card" },
      el("div", { class: "section-label" }, el("h2", { text: "Your progress" }), el("span", { class: "muted small", text: daysDone + " of 91 days" })),
      el("div", { class: "bar" }, el("div", { class: "bar-fill", style: "width:" + Math.round(daysDone / 91 * 100) + "%" })),
      el("div", { class: "stats", style: "margin-top:12px" },
        stat(learnedPhraseCount(), "Phrases learned"), stat(streak, "Day streak"), stat(acc, "Accuracy"))));

    var list = el("ul", { class: "week-list" });
    weeks.forEach(function (wk) {
      var avail = !!data[wk.week];
      var doneCount = avail ? data[wk.week].days.filter(function (d) { return isDone(wk.week, d.day); }).length : 0;
      var info = el("div", { class: "week-info" },
        el("div", { class: "week-title", text: wk.title }),
        el("div", { class: "week-theme", text: avail ? wk.theme + " - " + doneCount + "/7 days" : wk.theme + " - coming soon" }));
      var inner = [el("div", { class: "week-num", text: String(wk.week) }), info];
      var li = el("li", { class: "week-item" + (avail ? " open" : "") });
      if (avail) li.appendChild(el("button", { class: "link", type: "button", onclick: function () { renderWeek(wk.week); } }, inner));
      else inner.forEach(function (n) { li.appendChild(n); });
      list.appendChild(li);
    });
    app.appendChild(el("section", { class: "card" }, el("h2", { text: "13-week plan" }), list));

    var sfxToggle = el("input", { type: "checkbox", id: "sfxToggle" });
    sfxToggle.checked = !!progress.settings.sfx;
    sfxToggle.addEventListener("change", function () {
      progress.settings.sfx = sfxToggle.checked; save();
      if (sfxToggle.checked) sfx(true);
    });
    app.appendChild(el("section", { class: "card" },
      el("div", { class: "check-list" }, el("label", { for: "sfxToggle", style: "display:flex;gap:10px;align-items:center" },
        sfxToggle, el("span", null, el("strong", { text: "Sound effects" }),
          el("span", { class: "muted small", text: " - a chime for right answers, a low tone for wrong ones" }))))));
    app.appendChild(el("p", { class: "muted small", style: "text-align:center" },
      el("button", { class: "reveal-btn", type: "button", onclick: function () {
        askConfirm("Reset progress?", "This erases all lessons done and the review schedule on this device.", "Erase progress",
          function () { progress = loadProgressFrom({}); save(); renderHome(); });
      } }, "Reset progress on this device")));
  }
  function loadProgressFrom(p) {
    p.done = {}; p.srs = {}; p.streak = { last: null, count: 0 }; p.missions = {}; p.totals = { answered: 0, correct: 0, minutes: 0 };
    p.settings = { sfx: true };
    return p;
  }
  function stat(n, label) {
    return el("div", { class: "stat" }, el("div", { class: "stat-num", text: String(n) }), el("div", { class: "stat-label", text: label }));
  }

  /* ---------- WEEK ---------- */
  function renderWeek(w) {
    stopAudio(); var d = data[w];
    setTop("Week " + w, true); topProgress.hidden = true; clear();
    app.appendChild(el("section", { class: "card" },
      el("div", { class: "eyebrow", text: "Week " + w }),
      el("h1", { text: d.title }), el("p", { class: "muted", text: d.subtitle }),
      el("p", { class: "small", text: d.goal })));
    var list = el("div", { class: "day-list" });
    d.days.forEach(function (day) {
      var done = isDone(w, day.day), unlocked = done || dayUnlocked(w, day.day);
      var nxt = nextLesson(); var isNext = nxt && nxt.week === w && nxt.day === day.day;
      list.appendChild(el("button", {
        class: "day-item" + (done ? " done" : "") + (isNext ? " next" : ""), type: "button", disabled: !unlocked,
        onclick: function () { startDay(w, day.day); }
      },
        el("span", { class: "day-dot", text: done ? "OK" : String(day.day) }),
        el("span", null, el("div", { style: "font-weight:700", text: "Day " + day.day + ": " + day.title }),
          el("div", { class: "muted small", text: done ? "Done - tap to practice again" : (unlocked ? (day.new.length ? day.new.length + " new phrases" : "Conversations and mission") : "Finish the previous day first") }))));
    });
    app.appendChild(el("section", { class: "card" }, el("h2", { text: "Days" }), list));
    app.appendChild(missionCard(w));
  }

  function missionCard(w) {
    var m = data[w].mission, saved = progress.missions[w] || [];
    var ul = el("ul", { class: "check-list" });
    m.steps.forEach(function (s, i) {
      var id = "m" + w + "-" + i;
      var cb = el("input", { type: "checkbox", id: id });
      cb.checked = !!saved[i];
      cb.addEventListener("change", function () {
        var arr = progress.missions[w] || []; arr[i] = cb.checked; progress.missions[w] = arr; save();
      });
      ul.appendChild(el("li", null, cb, el("label", { for: id, text: s })));
    });
    return el("section", { class: "card note" },
      el("div", { class: "eyebrow", text: "Mission" }), el("h2", { text: m.title }),
      el("p", { class: "small muted", text: "Do this on your next video call with Jiana. Tick each step when you've done it." }), ul);
  }

  /* ---------- SESSION ---------- */
  function startDay(w, dayNum) {
    var exs = dayExercises(w, dayNum), keys = {};
    exs.forEach(function (e) { keys[e.key] = 1; });
    var reviewKeys = dueReviews(keys).slice(0, REVIEW_CAP);
    session = {
      kind: "day", week: w, day: dayNum, started: Date.now(),
      exercises: exs, review: reviewKeys.map(function (k) { return exIndex[k]; }),
      stats: { newRight: 0, newTotal: 0, revRight: 0, revTotal: 0 }, graded: {}, steps: 0
    };
    session.totalSteps = exs.length + session.review.length;
    renderIntro();
  }
  function startReview() {
    var keys = dueReviews().slice(0, REVIEW_CAP);
    if (!keys.length) return;
    session = {
      kind: "review", started: Date.now(), exercises: [], review: keys.map(function (k) { return exIndex[k]; }),
      stats: { newRight: 0, newTotal: 0, revRight: 0, revTotal: 0 }, graded: {}, steps: 0
    };
    session.totalSteps = session.review.length;
    setTop("Review", true); setBar(0);
    runQueue(session.review.slice(), "review", finishSession);
  }
  function stepDone() { session.steps++; setBar(session.steps / Math.max(1, session.totalSteps)); }

  /* Intro: culture note, then each new phrase (or the week's conversations on review day). */
  function renderIntro() {
    var d = data[session.week], day = d.days[session.day - 1];
    setTop("Week " + session.week + " - Day " + session.day, true); setBar(0); clear();
    app.appendChild(el("section", { class: "card" },
      el("div", { class: "eyebrow", text: "Day " + session.day }), el("h1", { text: day.title }), el("p", { text: day.intro })));
    if (day.culture) app.appendChild(el("section", { class: "card note" },
      el("div", { class: "eyebrow", text: "Culture note" }), el("h2", { text: day.culture.title }), el("p", { text: day.culture.text })));
    var label = day.new.length ? "Meet today's " + day.new.length + " phrases" : "Listen to this week's conversations";
    app.appendChild(stickyButton(label, function () {
      if (day.new.length) showPhrase(day.new, 0); else showDialogues(day.dialogues || [], 0);
    }));
  }
  function phraseCard(id, opts) {
    var it = items[id];
    return el("section", { class: "card" },
      speakerTag(it.speaker),
      el("div", { class: "ceb big", text: it.ceb }),
      el("div", { class: "en", text: it.en }),
      it.lit ? el("div", { class: "muted small", text: "Literally: " + it.lit }) : null,
      audioRow(id, opts),
      it.scene ? el("div", { class: "muted small", text: "Where you'll hear it: " + it.scene }) : null,
      it.tip ? el("div", { class: "tip", text: it.tip }) : null);
  }
  function showPhrase(list, i) {
    stopAudio(); clear();
    app.appendChild(el("div", { class: "eyebrow", text: "New phrase " + (i + 1) + " of " + list.length }));
    app.appendChild(phraseCard(list[i], { autoplay: true }));
    app.appendChild(el("p", { class: "muted small", text: "Listen a few times. Use Slow if you need it. Say it out loud once before moving on." }));
    app.appendChild(stickyButton(i + 1 < list.length ? "Next phrase" : "Start practice", function () {
      if (i + 1 < list.length) showPhrase(list, i + 1); else startExercises();
    }));
  }
  function dialogueCard(dlg) {
    var showEn = { on: true };
    var lines = dlg.lines.map(function (ln) { return ln.chunk ? items[ln.chunk] : items[ln.id]; });
    var rows = lines.map(function (it) {
      var en = el("div", { class: "en small", text: it.en });
      var row = el("div", { class: "dialogue-line" }, miniPlay(it.id),
        el("div", { class: "text" }, speakerTag(it.speaker), el("div", { class: "ceb", text: it.ceb }), en));
      row._en = en; return row;
    });
    var playAll = el("button", { class: "btn primary", type: "button" }, "Play conversation");
    playAll.addEventListener("click", function () {
      stopAudio();
      var steps = lines.map(function (it, i) {
        return function () {
          rows.forEach(function (r) { r.classList.remove("active"); });
          rows[i].classList.add("active"); play(it.id, false, null, true);
        };
      });
      steps.push(function () { rows.forEach(function (r) { r.classList.remove("active"); }); });
      playQueue = steps.slice(1); steps[0]();
    });
    var toggle = el("button", { class: "btn", type: "button" }, "Hide English");
    toggle.addEventListener("click", function () {
      showEn.on = !showEn.on; toggle.textContent = showEn.on ? "Hide English" : "Show English";
      rows.forEach(function (r) { r._en.hidden = !showEn.on; });
    });
    return el("section", { class: "card" },
      el("div", { class: "eyebrow", text: "Conversation" }), el("h2", { text: dlg.title }),
      el("div", { class: "btn-row", style: "margin-bottom:8px" }, playAll, toggle), rows);
  }
  function findDialogue(id) {
    var d = data[session.week]; for (var i = 0; i < d.dialogues.length; i++) if (d.dialogues[i].id === id) return d.dialogues[i];
  }
  function showDialogues(ids, i) {
    stopAudio(); clear();
    if (!ids.length) return startExercises();
    app.appendChild(el("div", { class: "eyebrow", text: "Conversation " + (i + 1) + " of " + ids.length }));
    app.appendChild(dialogueCard(findDialogue(ids[i])));
    app.appendChild(el("p", { class: "muted small", text: "Play it twice: once reading along, once with the English hidden." }));
    app.appendChild(stickyButton(i + 1 < ids.length ? "Next conversation" : "Start practice", function () {
      if (i + 1 < ids.length) showDialogues(ids, i + 1); else startExercises();
    }));
  }
  function startExercises() {
    var first = session.exercises.slice();
    runQueue(first, "new", function () {
      if (session.review.length) {
        interstitial("Review time", "Now " + session.review.length + " phrases from earlier days. About 10 minutes.", "Start review", function () {
          runQueue(session.review.slice(), "review", readAloud);
        });
      } else readAloud();
    });
  }

  /* Runs a list of exercises; wrong answers come back once at the end. */
  function runQueue(queue, mode, done) {
    var retry = [];
    function next() {
      if (!queue.length) {
        if (retry.length) {
          var r = retry; retry = [];
          return interstitial("One more try", "Let's go back to the " + r.length + " you missed.", "Try again", function () { queue = r; next(); });
        }
        return done();
      }
      var ex = queue.shift();
      runExercise(ex, function (correct) {
        if (!session.graded[ex.key]) {
          session.graded[ex.key] = 1; grade(ex, correct); stepDone();
          if (mode === "new") { session.stats.newTotal++; if (correct) session.stats.newRight++; }
          else { session.stats.revTotal++; if (correct) session.stats.revRight++; }
          if (!correct) retry.push(ex);
        }
        next();
      });
    }
    next();
  }

  function interstitial(title, text, btnLabel, fn) {
    stopAudio(); clear();
    app.appendChild(el("section", { class: "card" }, el("h1", { text: title }), el("p", { text: text })));
    app.appendChild(stickyButton(btnLabel, fn));
  }
  function stickyButton(label, fn, disabled) {
    var b = el("button", { class: "btn primary block", type: "button", disabled: !!disabled }, label);
    b.addEventListener("click", fn);
    var wrap = el("div", { class: "sticky-actions" }, el("div", { class: "inner" }, b));
    wrap._btn = b; return wrap;
  }

  /* ---------- EXERCISES ---------- */
  function shadowItemFor(ex) { return ex.type === "respond" ? ex.answer : ex.ref; }

  function runExercise(ex, cb) {
    stopAudio(); clear();
    var r = RENDER[ex.type](ex);
    app.appendChild(r.node);
    r.onAnswer = function (correct, detail) {
      stopAudio();
      sfx(correct);
      var it = items[shadowItemFor(ex)];
      var fb = el("div", { class: "feedback " + (correct ? "good" : "bad") },
        el("div", { class: "feedback-title", text: correct ? "Correct!" : "Not quite." }),
        detail || null,
        el("div", { class: "ceb", text: it.ceb }), el("div", { class: "en", text: it.en }));
      app.appendChild(fb);
      app.appendChild(stickyButton("Continue", function () { shadow(it.id, function () { cb(correct); }); }));
      if (ex.type === "fill" || ex.type === "order" || ex.type === "respond") setTimeout(function () { play(it.id, false); }, 650);
      fb.scrollIntoView({ behavior: "smooth", block: "nearest" });
    };
  }

  function shadow(id, cb) {
    stopAudio(); clear();
    var it = items[id], count = 0;
    var next = stickyButton("Next", cb);
    var reps = el("div", { class: "reps" });
    [1, 2, 3].forEach(function (n) {
      var b = el("button", { class: "rep", type: "button", "aria-label": "I said it out loud, time " + n }, String(n));
      b.addEventListener("click", function () {
        if (b.classList.contains("done")) return;
        b.classList.add("done"); count++;
        if (count < 3) play(id, false);
      });
      reps.appendChild(b);
    });
    app.appendChild(el("section", { class: "card" },
      el("div", { class: "eyebrow", text: "Shadowing" }),
      el("h2", { text: "Listen and repeat 3 times out loud" }),
      speakerTag(it.speaker),
      el("div", { class: "ceb big", text: it.ceb }), el("div", { class: "en", text: it.en }),
      audioRow(id, { autoplay: true }),
      el("p", { class: "muted small", text: "Play it, then say it out loud - copy the rhythm, not just the words. Tap a circle each time you say it." }),
      reps));
    app.appendChild(next);
  }

  function choiceButtons(options, correctValue, onPick, cebStyle) {
    var wrap = el("div", { class: "options" }), btns = [];
    options.forEach(function (o) {
      var b = el("button", { class: "option" + (cebStyle ? " ceb-opt" : ""), type: "button" }, o.label);
      b.addEventListener("click", function () {
        btns.forEach(function (x) { x.disabled = true; if (x._v === correctValue) x.classList.add("correct"); });
        if (o.value !== correctValue) b.classList.add("wrong");
        onPick(o.value === correctValue);
      });
      b._v = o.value; btns.push(b); wrap.appendChild(b);
    });
    return wrap;
  }
  function revealText(id) {
    var it = items[id];
    var t = el("div", { class: "ceb", text: it.ceb }); t.hidden = true;
    var b = el("button", { class: "reveal-btn", type: "button" }, "Show the Bisaya text");
    b.addEventListener("click", function () { t.hidden = false; b.hidden = true; });
    return el("div", null, b, t);
  }

  function englishDistractors(ex, n) {
    var target = items[ex.ref], seen = {}; seen[target.en] = 1;
    var pool = data[ex.week].chunks.filter(function (c) { return c.id !== ex.ref; });
    var learned = pool.filter(function (c) {
      return data[ex.week].days.some(function (d) { return d.day <= ex.day && d.new.indexOf(c.id) >= 0; });
    });
    var src = shuffle(learned.length >= n ? learned : pool), out = [];
    for (var i = 0; i < src.length && out.length < n; i++) if (!seen[src[i].en]) { seen[src[i].en] = 1; out.push(src[i].en); }
    return out;
  }

  var RENDER = {
    listen_meaning: function (ex) {
      var r = {}, it = items[ex.ref];
      var opts = shuffle([it.en].concat(englishDistractors(ex, 2))).map(function (v) { return { label: v, value: v }; });
      r.node = el("section", { class: "card" },
        el("div", { class: "question", text: "What does this mean?" }),
        el("p", { class: "muted small", text: "Listen, then choose the meaning." }),
        speakerTag(it.speaker), audioRow(ex.ref, { autoplay: true }), revealText(ex.ref),
        choiceButtons(opts, it.en, function (ok) { r.onAnswer(ok); }));
      return r;
    },
    scene: function (ex) {
      var r = {}, it = items[ex.ref];
      var opts = shuffle(ex.options).map(function (v) { return { label: v, value: v }; });
      r.node = el("section", { class: "card" },
        el("div", { class: "question", text: "Where are you most likely to hear this?" }),
        speakerTag(it.speaker), audioRow(ex.ref, { autoplay: true }), revealText(ex.ref),
        choiceButtons(opts, ex.answer, function (ok) { r.onAnswer(ok); }));
      return r;
    },
    respond: function (ex) {
      var r = {};
      var ids = shuffle([ex.answer].concat(ex.distractors));
      var opts = ids.map(function (id) { return { label: items[id].ceb, value: id }; });
      var head;
      if (ex.prompt) {
        var p = items[ex.prompt];
        head = [el("div", { class: "question", text: (SPEAKER_LABEL[p.speaker] || p.speaker).replace(/ \(.*\)/, "") + " says to you:" }),
          speakerTag(p.speaker), audioRow(ex.prompt, { autoplay: true }), revealText(ex.prompt),
          el("div", { class: "question", style: "margin-top:12px", text: "What do you say back?" })];
      } else {
        head = [el("div", { class: "eyebrow", text: "Situation" }), el("div", { class: "context", text: ex.context }),
          el("div", { class: "question", text: "What do you say?" })];
      }
      r.node = el("section", { class: "card" }, head,
        choiceButtons(opts, ex.answer, function (ok) {
          var detail = ex.prompt ? el("div", { class: "small muted", text: items[ex.prompt].speaker + " said: " + items[ex.prompt].ceb + " (" + items[ex.prompt].en + ")" }) : null;
          r.onAnswer(ok, detail);
        }, true));
      return r;
    },
    fill: function (ex) {
      var r = {}, it = items[ex.ref];
      var parts = ex.text.split("___");
      var blank = el("span", { class: "blank", text: "?" });
      var opts = shuffle(ex.options).map(function (v) { return { label: v, value: v }; });
      r.node = el("section", { class: "card" },
        el("div", { class: "question", text: "Fill in the blank" }),
        el("div", { class: "en", text: it.en }),
        el("div", { class: "blank-sentence" }, parts[0], blank, parts[1] || ""),
        choiceButtons(opts, ex.answer, function (ok) { blank.textContent = ex.answer; r.onAnswer(ok); }, true));
      return r;
    },
    order: function (ex) {
      var r = {}, it = items[ex.ref], picked = [];
      var answerArea = el("div", { class: "tile-area answer", "aria-label": "Your sentence" });
      var bank = el("div", { class: "tile-area", "aria-label": "Pieces" });
      var check = el("button", { class: "btn primary block", type: "button", disabled: true }, "Check");
      var reset = el("button", { class: "btn", type: "button" }, "Clear");
      var tiles = shuffle(ex.tiles.map(function (t, i) { return { text: t, i: i }; }));
      function redraw() {
        answerArea.innerHTML = "";
        picked.forEach(function (t, pos) {
          var b = el("button", { class: "tile", type: "button" }, t.text);
          b.addEventListener("click", function () { if (r.locked) return; picked.splice(pos, 1); t.btn.classList.remove("used"); redraw(); });
          answerArea.appendChild(b);
        });
        if (!picked.length) answerArea.appendChild(el("span", { class: "muted small", text: "Tap the pieces in order" }));
        check.disabled = !picked.length;
      }
      tiles.forEach(function (t) {
        t.btn = el("button", { class: "tile", type: "button" }, t.text);
        t.btn.addEventListener("click", function () {
          if (r.locked || t.btn.classList.contains("used")) return;
          picked.push(t); t.btn.classList.add("used"); redraw();
        });
        bank.appendChild(t.btn);
      });
      reset.addEventListener("click", function () { if (r.locked) return; picked = []; tiles.forEach(function (t) { t.btn.classList.remove("used"); }); redraw(); });
      check.addEventListener("click", function () {
        r.locked = true; check.disabled = true; reset.disabled = true;
        var mine = norm(picked.map(function (t) { return t.text; }).join(" "));
        var match = -1;
        ex.answers.forEach(function (a, i) { if (match < 0 && norm(a.join(" ")) === mine) match = i; });
        var detail = null;
        if (match > 0) detail = el("div", { class: "small", text: "Your order works too. The most common way:" });
        else if (match < 0 && ex.answers.length > 1) detail = el("div", { class: "small", text: "Accepted orders: " + ex.answers.map(function (a) { return a.join(" / "); }).join("  |  ") });
        r.onAnswer(match >= 0, detail);
      });
      redraw();
      r.node = el("section", { class: "card" },
        el("div", { class: "question", text: "Put the pieces in order" }),
        el("div", { class: "en", text: it.en }),
        ex.tiles.length > ex.answers[0].length ? el("div", { class: "muted small", text: "Careful: one piece doesn't belong." }) : null,
        answerArea, bank, el("div", { class: "btn-row" }, reset, check));
      return r;
    }
  };

  /* ---------- READ ALOUD + RESULTS ---------- */
  function readAloud() {
    stopAudio(); clear(); setBar(1);
    var day = data[session.week].days[session.day - 1];
    app.appendChild(el("section", { class: "card" },
      el("div", { class: "eyebrow", text: "Read aloud - about 5 minutes" }),
      el("h1", { text: "Say it like you mean it" }),
      el("p", { text: day.new.length
        ? "Go down the list. Play each phrase, then read it out loud 3 times. Last round: cover the Bisaya and say it from the English."
        : "Play each conversation. The second time, read Thomas's lines out loud together with him, then try them before he speaks." })));
    if (day.new.length) day.new.forEach(function (id) {
      var it = items[id];
      app.appendChild(el("section", { class: "card" },
        el("div", { class: "dialogue-line", style: "border:0;padding:0" }, miniPlay(id),
          el("div", { class: "text" }, speakerTag(it.speaker), el("div", { class: "ceb", text: it.ceb }), el("div", { class: "en small", text: it.en })))));
    });
    else (day.dialogues || []).forEach(function (id) { app.appendChild(dialogueCard(findDialogue(id))); });
    app.appendChild(stickyButton("Finish today's lesson", finishSession));
  }

  function finishSession() {
    stopAudio(); session.finished = true;
    var mins = Math.max(1, Math.round((Date.now() - session.started) / 60000));
    progress.totals.minutes += mins;
    var t = today();
    if (session.kind === "day") progress.done[session.week + "-" + session.day] = progress.done[session.week + "-" + session.day] || t;
    if (progress.streak.last !== t) {
      progress.streak.count = progress.streak.last === addDays(t, -1) ? progress.streak.count + 1 : 1;
      progress.streak.last = t;
    }
    save();
    setTop(session.kind === "day" ? "Lesson complete" : "Review complete", true); topProgress.hidden = true; clear();
    var s = session.stats;
    var hero = el("section", { class: "card hero" },
      el("div", { class: "eyebrow", text: session.kind === "day" ? "Week " + session.week + ", Day " + session.day : "Review" }),
      el("h1", { text: session.kind === "day" ? "Maayo kaayo! Day " + session.day + " done." : "Maayo kaayo! Review done." }),
      el("p", { class: "muted small", text: "Maayo kaayo = Very good." }));
    app.appendChild(hero);
    app.appendChild(el("section", { class: "card" },
      el("div", { class: "stats" },
        session.kind === "day" ? stat(s.newRight + "/" + s.newTotal, "New practice") : null,
        stat(s.revTotal ? s.revRight + "/" + s.revTotal : "-", "Review"),
        stat(mins + " min", "Time"))));
    if (session.kind === "day") {
      var day = data[session.week].days[session.day - 1];
      if (day.new.length) {
        app.appendChild(el("section", { class: "card" }, el("h2", { text: "Today's phrases" }),
          day.new.map(function (id) {
            var it = items[id];
            return el("div", { class: "dialogue-line" }, miniPlay(id),
              el("div", { class: "text" }, el("div", { class: "ceb", text: it.ceb }), el("div", { class: "en small", text: it.en })));
          })));
      }
      if (session.day === data[session.week].days.length) app.appendChild(missionCard(session.week));
      else app.appendChild(el("p", { class: "muted small", text: "Missed answers will come back in your review tomorrow." }));
    }
    app.appendChild(stickyButton("Back to home", renderHome));
  }

  /* ---------- boot ---------- */
  function boot() {
    fetchJSON("data/weeks.json").then(function (ws) {
      weeks = ws;
      return Promise.all(ws.filter(function (w) { return w.available; }).map(function (w) {
        return fetchJSON("data/week" + pad(w.week) + ".json").then(indexWeek);
      }));
    }).then(renderHome).catch(function (e) {
      clear();
      app.appendChild(el("section", { class: "card" }, el("h1", { text: "Couldn't load the lessons" }),
        el("p", { text: "If you opened index.html directly from your computer, start a small local web server instead (see README). Details: " + e.message })));
    });
  }
  /* ---------- access code (website only; see js/config.js) ---------- */
  var ACCESS_KEY = "bisaya-thomas-access";
  function sha256hex(text) {
    return crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)).then(function (buf) {
      return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
    });
  }
  function gate(next) {
    var cfg = window.BISAYA_ACCESS;
    if (!cfg || !cfg.hash) return next();
    var saved = null;
    try { saved = localStorage.getItem(ACCESS_KEY); } catch (e) { saved = null; }
    if (saved === cfg.hash) return next();
    clear(); setTop("Bisaya for Thomas", false);
    if (!window.crypto || !crypto.subtle) {
      app.appendChild(el("section", { class: "card" }, el("h1", { text: "Please open the secure link" }),
        el("p", { text: "This page must be opened with https:// to check your access code." })));
      return;
    }
    var input = el("input", { class: "code-input", id: "accessCode", type: "password", autocomplete: "current-password",
      autocapitalize: "none", spellcheck: "false", "aria-label": "Access code" });
    var msg = el("p", { class: "small", role: "alert", style: "color:var(--bad);min-height:1.5em" });
    var btn = el("button", { class: "btn primary block", type: "submit" }, "Open the course");
    var form = el("form", { class: "card" },
      el("div", { class: "eyebrow", text: "Welcome" }),
      el("h1", { text: "Maayong pag-abot!" }),
      el("p", { text: "Enter the access code from your teacher. You only need to do this once on this device." }),
      el("label", { for: "accessCode", class: "small muted", text: "Access code" }), input, msg, btn);
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var code = input.value.trim().toLowerCase();
      if (!code) { msg.textContent = "Type the access code first."; return; }
      btn.disabled = true;
      sha256hex(cfg.salt + code).then(function (h) {
        btn.disabled = false;
        if (h !== cfg.hash) { msg.textContent = "That code isn't right. Check it and try again."; input.select(); return; }
        try { localStorage.setItem(ACCESS_KEY, h); } catch (err) { /* will ask again next time */ }
        clear(); app.appendChild(el("p", { class: "muted", text: "Loading lessons..." }));
        next();
      });
    });
    app.appendChild(form);
    input.focus();
  }

  gate(boot);
})();
