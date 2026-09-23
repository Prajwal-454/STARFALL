"""Shared terminal sprites still drawn as plain ASCII art.

The Aurora (rendering/aurora.py) and the enemy fleet
(rendering/enemies_art.py) render through layered true-color cell grids.
What remains here is used as-is:

- EXPLOSION_FRAMES / explosion_frame: generic starburst for the player
  wreck, nova leftovers and satellite boss explosions (per-class kills
  use tinted wreck grids from enemies_art instead).
- NOVA_FRAMES: expanding Nova Cannon rings.
- POWERUP_GLYPHS: floating pickup labels.
- UNICODE_OK: flipped to False at runtime if the terminal cannot render
  Unicode cleanly.
"""

UNICODE_OK = True

# ---------------------------------------------------------------- explosions (6 frames)
EXPLOSION_FRAMES = [
    [
        r"  *  ",
        r" *** ",
        r"**X**",
        r" *** ",
        r"  *  ",
    ],
    [
        r"   .   ",
        r"  \*/*  ",
        r" **X** ",
        r"  */\*  ",
        r"   '   ",
    ],
    [
        r" .  . ",
        r".+***+.",
        r" *X+X* ",
        r".+***+.",
        r" '  ' ",
    ],
    [
        r"  . .  ",
        r" . * . ",
        r".  .  .",
        r" . * . ",
        r"  . .  ",
    ],
    [
        r"   .   ",
        r"       ",
        r"   .   ",
        r"       ",
        r"   .   ",
    ],
    [],
]

NOVA_FRAMES = [
    ["       |       ", "      \\|/      ", "  ---***---  ", "      /|\\      ", "       |       "],
    ["    \\  |  /    ", "  --*******--  ", "-*************-", "  --*******--  ", "    /  |  \\    "],
    ["--*****************--", "**  NOVA CANNON  **", "--*****************--"],
]

# ---------------------------------------------------------------- power-ups
POWERUP_GLYPHS = {
    "health": ("[+]", "Health +30"),
    "shield": ("[S]", "Shield +30"),
    "energy": ("[E]", "Energy +40"),
    "rapid": ("[F]", "Rapid Fire"),
    "double": ("[D]", "Double Damage 15s"),
    "bomb": ("[B]", "Bomb +1"),
    "weapon": ("[W]", "Weapon Up"),
    "life": ("[1UP]", "Extra Life"),
}


def explosion_frame(t):
    """t in 0..1 -> sprite rows."""
    idx = int(t * len(EXPLOSION_FRAMES))
    idx = max(0, min(len(EXPLOSION_FRAMES) - 1, idx))
    return EXPLOSION_FRAMES[idx]
