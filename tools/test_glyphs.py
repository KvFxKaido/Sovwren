# test_glyphs.py
"""Test which Nerd Font glyphs render in your terminal."""

from glyphs import (
    LOCK, UNLOCK, GLOBE, CLOUD, FILE, FOLDER, SEARCH, GEAR, BOOKMARK,
    WRENCH, MOON, CLOCK, CALENDAR, COMMENT, CHART, SAVE, EXPAND,
    LENS_BLUE, LENS_RED, LENS_PURPLE, WARNING, THREAD, HANDSHAKE,
    SQUARE, BULB, CHAT, ROBOT, MIRROR, UPLOAD, DOWNLOAD, PENCIL,
    MEMO, THOUGHT,
)

GLYPHS = {
    # Gates & security
    "lock": LOCK,
    "unlock": UNLOCK,
    "globe": GLOBE,
    "cloud": CLOUD,

    # Files & folders
    "file": FILE,
    "folder": FOLDER,
    "save": SAVE,

    # Actions
    "search": SEARCH,
    "gear": GEAR,
    "bookmark": BOOKMARK,
    "expand": EXPAND,

    # Modes
    "wrench": WRENCH,
    "moon": MOON,

    # Status
    "clock": CLOCK,
    "calendar": CALENDAR,
    "comment": COMMENT,
    "chart": CHART,
    "warning": WARNING,

    # Lens
    "blue": LENS_BLUE,
    "red": LENS_RED,
    "purple": LENS_PURPLE,

    # UI elements
    "thread": THREAD,
    "handshake": HANDSHAKE,
    "square": SQUARE,
    "bulb": BULB,
    "chat": CHAT,
    "robot": ROBOT,
    "mirror": MIRROR,
    "upload": UPLOAD,
    "download": DOWNLOAD,
    "pencil": PENCIL,
    "memo": MEMO,
    "thought": THOUGHT,
}

print("\n=== Sovwren Glyph Test ===\n")
print("If any glyph shows as [] or ?, it's not rendering.\n")

for name, glyph in GLYPHS.items():
    print(f"  {glyph}  {name}")

print("\n=== Done ===\n")
print("To switch to ASCII fallbacks, set USE_NERD_FONTS = False in glyphs.py")
