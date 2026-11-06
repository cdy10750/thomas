#!/usr/bin/env python3
"""Set (or remove) the access code students type to open the course website.

  python3 tools/set_password.py              # make a new random code and print it
  python3 tools/set_password.py my-code-123  # use this code
  python3 tools/set_password.py --off        # no access code

Only a salted SHA-256 hash of the code is written to js/config.js; the code itself is never stored
in the repository. Codes are not case-sensitive and surrounding spaces are ignored.
After changing it, commit and push js/config.js; devices that already entered the old code will be
asked for the new one.
"""
import hashlib
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "js" / "config.js"
WORDS = ["kaon-na", "lami-kaayo", "maayong-buntag", "salamat-kaayo", "hinay-hinay", "mingaw-na", "sige-na", "busog-na"]


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg == "--off":
        CONFIG.write_text("/* No access code: the course opens for anyone with the link. */\nwindow.BISAYA_ACCESS = null;\n")
        print("Access code removed.")
        return
    code = (arg or f"{secrets.choice(WORDS)}-{secrets.randbelow(9000) + 1000}").strip().lower()
    salt = secrets.token_hex(8)
    digest = hashlib.sha256((salt + code).encode("utf-8")).hexdigest()
    CONFIG.write_text(
        "/* Access code check for the course website. Only a salted hash is stored here.\n"
        " * Change it with: python3 tools/set_password.py */\n"
        f'window.BISAYA_ACCESS = {{ salt: "{salt}", hash: "{digest}" }};\n')
    print(f"Access code set: {code}")


if __name__ == "__main__":
    main()
