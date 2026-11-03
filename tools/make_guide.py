#!/usr/bin/env python3
"""Build the learner's course guide: docs/Bisaya_for_Thomas_Course_Guide.pdf"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "Bisaya_for_Thomas_Course_Guide.pdf"
COURSE_URL = "https://claude.ai/artifact/U49bQF6puCEADHm5BrGmiY"

TEAL = colors.HexColor("#0f6e6e")
TEAL_SOFT = colors.HexColor("#dceeed")
AMBER = colors.HexColor("#c7781a")
AMBER_SOFT = colors.HexColor("#f8ead6")
INK = colors.HexColor("#1f2328")
MUTED = colors.HexColor("#5f6670")
LINE = colors.HexColor("#ddd6cb")

body = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=INK, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontSize=9, leading=12.5, textColor=MUTED)
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=26, leading=31, textColor=TEAL, spaceAfter=6)
sub = ParagraphStyle("sub", parent=body, fontSize=13, leading=18, textColor=MUTED, spaceAfter=18)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=TEAL, spaceBefore=14, spaceAfter=8)
h3 = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=8, spaceAfter=3)
cell = ParagraphStyle("cell", parent=body, fontSize=9.5, leading=12.5, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")
ceb = ParagraphStyle("ceb", parent=body, fontName="Helvetica-Bold", textColor=TEAL)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=3)


def P(t, s=body):
    return Paragraph(t, s)


def bullets(items):
    return [Paragraph(t, bullet, bulletText="•") for t in items]


def box(flowables, bg=TEAL_SOFT, border=TEAL):
    t = Table([[flowables]], colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return t


def table(rows, widths, header=True):
    data = [[P(c, cellb if (header and i == 0) else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * inch for w in widths], repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), TEAL_SOFT), ("LINEBELOW", (0, 0), (-1, 0), 1, TEAL)]
    t.setStyle(TableStyle(style))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(inch, 0.6 * inch, "Bisaya for Thomas - Course Guide")
    canvas.drawRightString(letter[0] - inch, 0.6 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(inch, 0.75 * inch, letter[0] - inch, 0.75 * inch)
    canvas.restoreState()


def build():
    s = []
    # ---------- cover / introduction ----------
    s += [Spacer(1, 0.4 * inch), P("Bisaya for Thomas", h1),
          P("Course guide: what this course is for, how it was designed, and how to use it every day", sub)]
    s.append(box([P("<b>Maayong pag-abot!</b> (Welcome!)", ceb),
                  P("This is a 13-week, 30-minutes-a-day course in Bisaya (Cebuano), built for one purpose: "
                    "so you can talk with Jiana's family in Bohol - at the dinner table, in the living room, on the "
                    "way to church, and on video calls. It is not a general language course. Every sentence in it is "
                    "something Nanay, Tatay, Kuya, Dodong, Inday or Jiana is likely to say to you, or something you "
                    "will want to say to them.")]))
    s.append(Spacer(1, 10))
    s.append(P("Your goals for the 90 days", h2))
    s.append(table([
        ["Goal", "What it looks like in Bohol"],
        ["1. Understand what the family says to you", "You recognize Kaon na! (Come eat!), Kapoy ka? (Are you tired?) and Kanus-a ka mouli? (When are you going home?) when you hear them at natural speed."],
        ["2. Answer with short, ready-made phrases", "You can answer without translating in your head: Busog na ko. (I'm full.) Lami kaayo! (Very delicious!) Mobalik gyud ko. (I'll definitely come back.)"],
        ["3. Keep the conversation going when you're lost", "Instead of smiling and nodding, you say Unsa? (What?), Hinay-hinay lang, palihug. (Slowly, please.) or Wala ko kasabot. (I don't understand.)"],
    ], [2.2, 4.3]))
    s.append(Spacer(1, 6))
    s.append(P("Goal 3 matters most. With the phrases from Week 1, no conversation can leave you completely stuck - "
               "and families warm up quickly to someone who keeps trying.", small))

    # ---------- design principles ----------
    s.append(P("What this course focuses on", h2))
    principles = [
        ("Phrases, not word lists", "You never memorize a single word on its own. You learn whole phrases (\"chunks\") exactly as people say them - Kaon pa! instead of 'kaon = eat, pa = more'. Short tips explain the parts, but the chunk is what you keep."),
        ("Real people, real situations", "Every line belongs to someone in Jiana's family and to a real scene: arriving at the house, the dinner table, a fiesta, a motorbike ride, a video call. You learn what you will actually hear."),
        ("Listening first", "Most exercises start with audio. Understanding comes before speaking, so you hear each phrase many times before you have to produce it."),
        ("Bisaya mixed with English", "Families in Bohol switch between Bisaya and English all the time: Okay ra, Jet lag pa ka?, Asa ang CR? The course teaches this natural mix instead of an artificial 'pure' language."),
        ("Very little grammar", "There are no grammar lessons. A few small patterns (nag- = doing now, mo- = will, ka = you, ko = I) are pointed out inside the tips, only when they help."),
        ("Speaking out loud every day", "After every exercise you repeat the phrase three times out loud, and each lesson ends with five minutes of reading aloud. Your mouth needs practice, not only your ears."),
        ("Culture with every lesson", "Each day has a short culture note: the mano blessing, why hosts keep saying Kaon pa!, fiestas, pasalubong, Filipino time. Knowing these matters as much as the words."),
        ("Practice with Jiana", "Each week ends with a video-call mission, so what you learn is used with a real person within days."),
    ]
    for title, text in principles:
        s.append(KeepTogether([P(title, h3), P(text)]))

    # ---------- the 13 weeks ----------
    s.append(PageBreak())
    s.append(P("The 13 weeks", h2))
    s.append(P("Each week has about 22-25 new phrases, spread over six days, plus a seventh day of conversations and a mission. "
               "The weeks build on each other, and earlier phrases keep coming back in reviews and conversations."))
    s.append(table([
        ["Week", "Theme", "Examples you will learn"],
        ["1", "Greetings, introductions, asking to repeat", "Maayong buntag! - Mano, Nay. - Wala ko kasabot. - Unsa'y English ana?"],
        ["2", "At the dinner table", "Kaon na! - Busog na ko. - Lami kaayo! - Nikaon na ka?"],
        ["3", "The family and what they ask you", "Kini si Kuya. - Pila imong igsoon? - Ako ang uyab ni Jiana."],
        ["4", "Health, heat, feeling tired", "Kapoy ka? - Init kaayo! - Sakit akong ulo. - Katulgon na ko."],
        ["5", "Numbers, time, arriving and leaving", "Kanus-a ka niabot? - Alas tres na. - Usa, duha, tulo..."],
        ["6", "Likes, dislikes, food reactions", "Ganahan ka og isda? - Halang! - Paborito nako ang lechon."],
        ["7", "Shopping, the market, prices", "Pila ni? - Mahal kaayo! - Pwede hangyo? - Asa ang CR?"],
        ["8", "Church, fiesta, family events", "Mosimba ta. - Mosayaw ka? - Kanta ta! - Salamat sa pag-imbita."],
        ["9", "Daily life at home", "Maligo na ka. - Unsa'y akong matabang? - Brownout na pud!"],
        ["10", "Going out around Bohol", "Asa ta padulong? - Liko sa wala. - Nindot kaayo ang dagat!"],
        ["11", "Video calls with Jiana", "Madungog ko nimo? - Mingaw na ko nimo. - Gihigugma tika."],
        ["12", "Thanks, feelings, goodbye", "Salamat sa tanan. - Mingawon ko ninyo. - Mobalik gyud ko."],
        ["13", "Full review: the whole trip", "From Jiana! Mingaw kaayo ko nimo! at the airport to Mobalik gyud ko. Babay! at the door."],
    ], [0.55, 2.15, 3.8]))
    s.append(Spacer(1, 8))
    s.append(KeepTogether([P("Who you will hear", h3), table([
        ["Person", "Who they are", "Voice"],
        ["Thomas", "You. Your own lines are the ones to practice saying.", "Male voice"],
        ["Jiana", "Your girlfriend - often on video calls.", "Female voice"],
        ["Nanay / Tatay", "Jiana's mother and father (Nay, Tay for short).", "Female / male"],
        ["Kuya / Dodong / Inday", "Jiana's older brother, younger brother, and younger sister.", "Male / male / female"],
        ["Tindera", "A market vendor (Week 7 only).", "Female voice"],
    ], [1.6, 3.6, 1.3])]))
    s.append(P("The audio was generated with natural-sounding Cebuano AI voices, recorded once at natural speed. "
               "Use the Slow button whenever you need it.", small))

    # ---------- how to use ----------
    s.append(PageBreak())
    s.append(P("How to use the course", h2))
    s.append(P("Opening it", h3))
    s += bullets([
        f"Open the course page in Claude: <font color='#0f6e6e'>{COURSE_URL}</font> (it must be shared with you from the Share menu first).",
        "It works on a phone, tablet or computer. A phone with headphones is ideal.",
        "Your progress and review schedule are saved in the browser you use. Use the same device and browser every day so your progress follows you.",
    ])
    s.append(KeepTogether([P("Your daily 30 minutes", h3), table([
        ["Part", "Time", "What you do"],
        ["New lesson", "about 15 min", "Read the culture note. Meet each new phrase: listen, use Slow if needed, read the tip, say it once. Then answer the practice questions."],
        ["Review", "about 10 min", "Phrases from earlier days that are due come back automatically - the ones you missed and the ones you just learned."],
        ["Read aloud", "about 5 min", "Go down the list of today's phrases (or the week's conversations) and say each one out loud three times."],
    ], [1.2, 1.1, 4.2])]))
    s.append(Spacer(1, 6))
    s.append(P("Press <b>Start today's lesson</b> on the home screen - the course always knows which day is next. "
               "When you finish, the day is marked done and the next one opens."))

    s.append(KeepTogether([P("The practice questions (from easiest to hardest)", h3), table([
        ["Type", "What you do"],
        ["What does this mean?", "Listen to a phrase and choose its English meaning."],
        ["Where would you hear this?", "Listen and choose the scene: dinner table, airport, church, market..."],
        ["What do you say back?", "A family member speaks (or a situation is described). Choose your reply. This is a mini conversation."],
        ["Fill in the blank", "Choose the missing word in a phrase. The English meaning is shown as a hint."],
        ["Put the pieces in order", "Tap phrase pieces in the right order. Sometimes one piece doesn't belong. If Bisaya allows more than one order, every correct order is accepted."],
        ["Listen and repeat 3 times", "After every question: play the phrase and say it out loud three times, tapping a circle each time."],
    ], [2.0, 4.5])]))
    s.append(Spacer(1, 4))
    s.append(P("If you answer wrong, the correct answer and its audio are shown, and the question comes back once at the end of the lesson.", small))

    s.append(KeepTogether([P("Day 7 and the video-call mission", h3), P("The seventh day of each week has no new phrases. You listen to three short conversations "
               "(you can hide the English the second time), answer as Thomas, and then get the week's mission: "
               "five or six things to try on your next video call with Jiana. Tick each step when you've done it. "
               "Jiana is your best teacher - ask her to correct your pronunciation and to teach you how her family says things.")]))

    s.append(KeepTogether([P("How the review works", h3), P("Every question you meet goes into a review box. A new or missed question comes back the next day. "
               "Each time you get it right, it waits longer before it returns: 3 days, then 7, 14 and 30 days. "
               "This spacing is what moves phrases into long-term memory. The <b>Review</b> card on the home screen shows "
               "how many are due; you can also run a review on its own on days without a new lesson.")]))

    # ---------- tips ----------
    s.append(P("Tips for getting the most out of it", h2))
    tips = [
        "<b>Say everything out loud.</b> Whispering or thinking it doesn't train your mouth. The three-repetition screens are the most valuable part of the course - don't skip them.",
        "<b>Copy the music, not just the words.</b> Bisaya has a rhythm and melody. Imitate the speaker's tone, speed and stress.",
        "<b>Use Slow, then normal.</b> Listen slowly to catch the sounds, then switch back to normal speed - that's how the family will talk.",
        "<b>A little every day beats a lot once a week.</b> If you only have 10 minutes, do the review. If you miss a day, simply continue - the course waits for you.",
        "<b>Don't worry about grammar.</b> If a phrase works, use it as it is. Understanding why comes later, on its own.",
        "<b>Expect a different accent.</b> In Bohol you may hear 'maajo' for 'maayo' and slightly different words from family to family. Ask Jiana, and use the family's version.",
        "<b>Use your survival phrases without shame.</b> Unsa? and Hinay-hinay lang, palihug are signs of effort, not failure. Filipino families appreciate the effort enormously.",
        "<b>Before a trip,</b> repeat Week 13 and the weeks for situations you expect (Week 2 for meals, Week 8 if there's a fiesta).",
    ]
    s += bullets(tips)

    s.append(KeepTogether([P("Your survival kit (Week 1)", h2), table([
        ["Bisaya", "English", "When to use it"],
        ["Unsa?", "What?", "You didn't catch something."],
        ["Hinay-hinay lang, palihug.", "Slowly, please.", "Someone is speaking too fast."],
        ["Balika, palihug.", "Say it again, please.", "You almost caught it."],
        ["Wala ko kasabot.", "I don't understand.", "You heard it but don't know the meaning."],
        ["Unsa'y English ana?", "What's that in English?", "You need the meaning of a word."],
        ["Salamat kaayo.", "Thank you very much.", "Always."],
    ], [2.2, 1.7, 2.6])]))

    s.append(KeepTogether([P("Good to know", h2)] + bullets([
        "The Bisaya in this course is standard Cebuano with natural English mixing. It has not yet been fully checked by a native speaker; a review sheet is kept so that Jiana or her family can correct anything that sounds unnatural.",
        "The voices are AI-generated. They are clear and natural, but real people in Bohol will speak faster, with local accent and slang - that's what the survival phrases are for.",
        "Resetting progress (link at the bottom of the home screen) erases everything on that device, so use it only to start over.",
    ])))
    s.append(Spacer(1, 14))
    s.append(box([P("<b>Kaya nimo ni!</b> - You can do this!", ceb),
                  P("Thirty minutes a day for thirteen weeks is about 45 hours of practice - enough to change how your next visit feels. "
                    "Maayong pagtuon! (Happy studying!)")], bg=AMBER_SOFT, border=AMBER))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(OUT), pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=0.9 * inch,
                            bottomMargin=1.0 * inch, title="Bisaya for Thomas - Course Guide", author="Bisaya for Thomas")
    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    build()
