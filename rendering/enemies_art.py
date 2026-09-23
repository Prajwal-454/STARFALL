"""Enemy fleet art: six reference-sheet ships as layered terminal sprites.

Same procedural/mirrored construction as THE AURORA (rendering/aurora.py)
so the whole cast shares one pixel-art universe: block-cell rendering,
per-cell true-color (16-color fallback), cached frames, 60fps-safe blits.

Orientation: enemies fly NOSE-DOWN (they dive toward the player), so
engines/flames sit on TOP, guns/muzzles at the BOTTOM (nose).

Identities (color + silhouette):
  fighter     red/crimson, dark body, blue engine, narrow dart
  interceptor blue/cyan sleek, long sharp nose, wide wings, amber lights
  tank        purple heavy armor, huge magenta core, twin engines
  bomber      white/silver + orange core/engines, side pods, wide wings
  elite       cyan/blue + green core, swept wings, triple engines
  boss        purple/magenta capital ship, giant core, 5 engines
  minion      (kept tiny legacy sprite — chaff, not a reference class)
"""

from rendering import colors as C
from rendering.aurora import tc

# ------------------------------------------------------------------ styles
# kind -> legend -> (display char, rgb, 16-color fallback)
STYLES = {
    "fighter": {
        "H": ("█", (58, 63, 82), C.BRIGHT_BLACK),
        "h": ("▓", (30, 33, 48), C.BLACK),
        "D": ("▓", (12, 13, 22), C.BLACK),
        "C": ("█", (255, 42, 42), C.BRIGHT_RED),
        "c": ("█", (255, 150, 120), C.BRIGHT_YELLOW),
        "E": ("▓", (63, 169, 255), C.BRIGHT_BLUE),   # blue engine glow
        "W": ("█", (70, 76, 100), C.BRIGHT_BLACK),
        "w": ("▒", (38, 42, 60), C.BLACK),
        "O": ("█", (255, 120, 40), C.YELLOW),
        "V": ("█", (63, 169, 255), C.BRIGHT_BLUE),
    },
    "interceptor": {
        "H": ("█", (42, 107, 255), C.BLUE),
        "h": ("▓", (24, 60, 160), C.BLUE),
        "D": ("▓", (10, 20, 60), C.BLACK),
        "C": ("█", (140, 240, 255), C.BRIGHT_CYAN),
        "c": ("█", (255, 255, 255), C.BRIGHT_WHITE),
        "E": ("▓", (90, 230, 255), C.BRIGHT_CYAN),
        "W": ("█", (60, 140, 255), C.BRIGHT_BLUE),
        "w": ("▒", (30, 80, 190), C.BLUE),
        "O": ("█", (255, 170, 30), C.BRIGHT_YELLOW),  # amber side lights
        "V": ("█", (200, 245, 255), C.BRIGHT_WHITE),
    },
    "tank": {
        "H": ("█", (74, 53, 102), C.MAGENTA),
        "h": ("▓", (44, 30, 66), C.BLACK),
        "D": ("▓", (18, 10, 30), C.BLACK),
        "C": ("█", (255, 42, 255), C.BRIGHT_MAGENTA),  # huge magenta core
        "c": ("█", (255, 180, 255), C.BRIGHT_WHITE),
        "E": ("▓", (190, 80, 255), C.MAGENTA),
        "W": ("█", (88, 64, 120), C.MAGENTA),
        "w": ("▒", (52, 36, 78), C.BLACK),
        "P": ("█", (96, 70, 130), C.MAGENTA),
        "O": ("█", (255, 120, 255), C.BRIGHT_MAGENTA),
        "V": ("█", (190, 80, 255), C.MAGENTA),
    },
    "bomber": {
        "H": ("█", (220, 228, 242), C.WHITE),
        "h": ("▓", (150, 160, 185), C.WHITE),
        "D": ("▓", (60, 70, 95), C.BRIGHT_BLACK),
        "C": ("█", (255, 138, 0), C.YELLOW),           # big orange core
        "c": ("█", (255, 220, 150), C.BRIGHT_WHITE),
        "E": ("▓", (255, 150, 40), C.BRIGHT_YELLOW),
        "W": ("█", (205, 213, 230), C.WHITE),
        "w": ("▒", (140, 150, 175), C.BRIGHT_BLACK),
        "P": ("█", (225, 232, 245), C.BRIGHT_WHITE),   # side engine pods
        "O": ("█", (255, 100, 0), C.RED),
        "V": ("█", (255, 150, 40), C.BRIGHT_YELLOW),
    },
    "elite": {
        "H": ("█", (30, 158, 191), C.CYAN),
        "h": ("▓", (16, 90, 115), C.BLUE),
        "D": ("▓", (6, 34, 46), C.BLACK),
        "C": ("█", (57, 255, 106), C.BRIGHT_GREEN),    # green core
        "c": ("█", (220, 255, 225), C.BRIGHT_WHITE),
        "E": ("▓", (120, 240, 255), C.BRIGHT_CYAN),
        "W": ("█", (45, 180, 210), C.CYAN),
        "w": ("▒", (22, 105, 130), C.BLUE),
        "O": ("█", (120, 255, 170), C.BRIGHT_GREEN),
        "V": ("█", (57, 255, 170), C.BRIGHT_GREEN),
    },
    "boss": {
        "H": ("█", (58, 31, 92), C.MAGENTA),
        "h": ("▓", (34, 18, 58), C.BLACK),
        "D": ("▓", (14, 6, 26), C.BLACK),
        "C": ("█", (255, 58, 216), C.BRIGHT_MAGENTA),  # giant magenta core
        "c": ("█", (255, 200, 245), C.BRIGHT_WHITE),
        "E": ("▓", (255, 90, 230), C.BRIGHT_MAGENTA),
        "W": ("█", (74, 42, 112), C.MAGENTA),
        "w": ("▒", (44, 26, 72), C.BLACK),
        "P": ("█", (86, 50, 128), C.MAGENTA),
        "O": ("█", (255, 120, 220), C.BRIGHT_MAGENTA),
        "V": ("█", (255, 90, 230), C.BRIGHT_MAGENTA),
    },
    "minion": {  # boss-spawned chaff: magenta-red dart, single engine
        "H": ("█", (120, 30, 60), C.RED),
        "h": ("▓", (70, 16, 36), C.BLACK),
        "D": ("▓", (26, 6, 14), C.BLACK),
        "C": ("█", (255, 70, 150), C.BRIGHT_MAGENTA),
        "c": ("█", (255, 210, 225), C.BRIGHT_WHITE),
        "E": ("▓", (255, 90, 140), C.BRIGHT_RED),
    },
}

# Body sizes (w, h) — relative proportions from the sheet, scaled to play.
SIZES = {
    "fighter": (9, 7),
    "interceptor": (11, 9),
    "tank": (13, 8),
    "bomber": (13, 8),
    "elite": (13, 9),
    "boss": (31, 12),
    "minion": (5, 3),
}

# Engine stacks (dx offsets from center) + flame colors per kind.
STACKS = {
    "fighter": ((-1, 0, 1), "E"),
    "interceptor": ((-1, 0, 1), "V"),
    "tank": ((-2, 2), "E"),
    "bomber": ((-4, 4), "V"),
    "elite": ((-3, 0, 3), "V"),
    "boss": ((-11, -6, 0, 6, 11), "V"),
    "minion": ((0,), "E"),
}
FLAME_LEN = [1, 2, 3, 2]  # 4-frame engine cycle

# Projectile identity per kind: (char, rgb, fallback, radius).
PROJECTILE = {
    "fighter": ("!", (255, 90, 42), C.BRIGHT_RED, 0.9),
    "interceptor": ("|", (90, 200, 255), C.BRIGHT_CYAN, 0.9),
    "tank": ("o", (255, 140, 0), C.YELLOW, 1.2),
    "bomber": ("O", (255, 120, 0), C.BRIGHT_RED, 1.3),
    "elite": ("!", (80, 255, 120), C.BRIGHT_GREEN, 0.9),
    "minion": (".", (255, 60, 60), C.BRIGHT_RED, 0.9),
    "boss_aimed": ("*", (255, 80, 220), C.BRIGHT_MAGENTA, 1.0),
    "boss_ring": ("o", (190, 90, 255), C.MAGENTA, 1.0),
}

# Wreck tint per kind: (core rgb, spark rgb, smoke fallback).
WRECK_TINT = {
    "fighter": ((255, 120, 40), (255, 42, 42)),
    "interceptor": ((120, 220, 255), (42, 107, 255)),
    "tank": ((255, 42, 255), (150, 60, 220)),
    "bomber": ((255, 160, 40), (255, 100, 0)),
    "elite": ((80, 255, 150), (57, 255, 106)),
    "minion": ((255, 120, 40), (255, 42, 42)),
    "boss": ((255, 90, 230), (255, 42, 180)),
}


# ------------------------------------------------------------------ builders
def _blank(w, h):
    grid: list = [[None] * w for _ in range(h)]
    return grid


def _set(g, x, y, leg):
    if 0 <= y < len(g) and 0 <= x < len(g[0]) and leg:
        g[y][x] = leg


def _hull(g, cx, profile):
    for y, hw in enumerate(profile):
        for dx in range(-hw, hw + 1):
            _set(g, cx + dx, y, "H")
        _set(g, cx - hw, y, "D")
        _set(g, cx + hw, y, "D")


def _wings(g, cx, cols):
    """cols: {rx: (top, bot)} right-side wing columns."""
    for side in (1, -1):
        for rx, (top, bot) in cols.items():
            x = cx + side * rx
            for y in range(top, bot + 1):
                _set(g, x, y, "W")
            _set(g, x, top, "E")
            _set(g, x, bot, "w")


def _core(g, cx, x0, x1, y0, y1, shine=True):
    for y in range(y0, y1 + 1):
        for x in range(cx + x0, cx + x1 + 1):
            _set(g, x, y, "C")
    if shine:
        _set(g, cx, y0, "c")


def _build(kind):
    w, h = SIZES[kind]
    cx = w // 2
    g = _blank(w, h)
    if kind == "fighter":
        # narrow dart, red core, blue engine bar, sharp nose
        _hull(g, cx, [1, 1, 1, 2, 2, 1, 0])
        _wings(g, cx, {2: (3, 4), 3: (3, 4), 4: (3, 4)})
        _core(g, cx, 0, 0, 2, 4)
        for dx in (-1, 0, 1):
            _set(g, cx + dx, 0, "E")
        _set(g, cx, 6, "H")
    elif kind == "interceptor":
        # long sleek body, very sharp nose, wide angular wings, ambers
        _hull(g, cx, [1, 1, 1, 1, 2, 2, 2, 1, 0])
        _wings(g, cx, {3: (4, 5), 4: (4, 6), 5: (4, 6)})
        _core(g, cx, 0, 0, 2, 4)
        for dx in (-1, 0, 1):
            _set(g, cx + dx, 0, "V")
        for s in (1, -1):
            _set(g, cx + s * 4, 5, "O")
            _set(g, cx + s * 2, 6, "O")
        _set(g, cx, 8, "H")  # visible sharp nose tip (not outline-only)
    elif kind == "tank":
        # wide armored slab, huge magenta core, armor blocks, twin engines
        _hull(g, cx, [2, 3, 3, 3, 3, 3, 2, 1])
        for s in (1, -1):
            for y in (2, 3, 4, 5):
                _set(g, cx + s * 4, y, "P")
                _set(g, cx + s * 5, y, "D")
            _set(g, cx + s * 2, 0, "E")
            _set(g, cx + s * 2, 1, "E")
        _wings(g, cx, {5: (4, 6), 6: (4, 6)})
        _core(g, cx, -1, 1, 2, 5)
        _set(g, cx - 1, 2, "c")
        _set(g, cx + 1, 2, "c")
        _set(g, cx - 1, 4, "c")
        _set(g, cx + 1, 4, "c")
    elif kind == "bomber":
        # white hull, big orange core, side pods, wide wings
        _hull(g, cx, [1, 2, 2, 2, 3, 3, 2, 1])
        for s in (1, -1):
            for y in (3, 4, 5):
                _set(g, cx + s * 4, y, "P")
            _set(g, cx + s * 4, 3, "E")
            _set(g, cx + s * 4, 5, "O")
        _wings(g, cx, {3: (4, 5), 4: (4, 6), 5: (4, 6), 6: (5, 6)})
        _core(g, cx, -1, 1, 3, 5)
        for dx in (-1, 0, 1):
            _set(g, cx + dx, 0, "E")
        _set(g, cx, 7, "H")
    elif kind == "elite":
        # sharp swept elite, green core, cyan edges, triple engines
        _hull(g, cx, [1, 1, 2, 2, 2, 3, 3, 2, 0])
        _wings(g, cx, {3: (5, 6), 4: (5, 7), 5: (5, 7), 6: (6, 7)})
        _core(g, cx, -1, 1, 2, 4)
        _set(g, cx, 2, "c")
        for dx in (-2, 0, 2):
            _set(g, cx + dx, 0, "V")
        for s in (1, -1):
            _set(g, cx + s * 5, 6, "O")
        _set(g, cx, 8, "H")  # visible sharp nose tip (not outline-only)
    elif kind == "boss":
        # capital ship: vast hull, giant core, side citadels, main cannon
        _hull(g, cx, [6, 8, 10, 12, 13, 14, 15, 14, 12, 9, 5, 2])
        for s in (1, -1):
            for y in (4, 5, 6, 7):
                for dx in (10, 11, 12):
                    _set(g, cx + s * dx, y, "P")
            _set(g, cx + s * 12, 4, "E")
            _set(g, cx + s * 10, 7, "O")
        _wings(g, cx, {13: (6, 8), 14: (6, 9), 15: (6, 9)})
        _core(g, cx, -3, 3, 3, 7)
        _set(g, cx - 2, 3, "c")
        _set(g, cx + 2, 3, "c")
        _set(g, cx, 4, "c")
        for dx in (-11, -6, 0, 6, 11):
            _set(g, cx + dx, 0, "V")
            _set(g, cx + dx, 1, "V")
        _set(g, cx, 11, "V")  # main cannon muzzle
        _set(g, cx - 1, 11, "D")
        _set(g, cx + 1, 11, "D")
    elif kind == "minion":
        # tiny boss-spawned dart: engine bar, magenta core, sharp nose
        _hull(g, cx, [1, 1, 0])
        _set(g, cx, 0, "E")
        _set(g, cx, 1, "C")
        _set(g, cx, 2, "H")  # visible nose tip (not outline-only)
    return g


_BASES = {k: _build(k) for k in SIZES}


# -------------------------------------------------------------- materialize
def _colorize(kind, leg, phase=0, damage=False, rage=False):
    ch, rgb, fb = STYLES[kind][leg]
    key = leg
    if damage and leg in ("H", "W", "P", "h", "w"):
        return (ch, tc((255, 255, 255), C.BRIGHT_WHITE))
    if rage and leg in ("E", "C"):
        return (ch, tc((255, 60, 60), C.BRIGHT_RED))
    if leg == "E" and phase == 1:
        # engine/edge pulse on off-phase: slightly deeper tone
        r, g_, b = rgb
        return (ch, tc((max(0, r - 40), max(0, g_ - 40), b), fb))
    return (ch, tc(rgb, fb))


def _materialize(kind, phase=0, damage=False, rage=False):
    base = _BASES[kind]
    h, w = len(base), len(base[0])
    cells: list = [[None] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            leg = base[y][x]
            if leg is None:
                continue
            cells[y][x] = _colorize(kind, leg, phase, damage, rage)
    return cells


def _shear(cells, bank, cx):
    out: list = [[None] * len(cells[0]) for _ in range(len(cells))]
    for y, row in enumerate(cells):
        off = int(round((y - len(cells) / 2) * 0.25 * bank))
        for x, cell in enumerate(row):
            if cell is None:
                continue
            nx = x + off
            if 0 <= nx < len(row):
                out[y][nx] = cell
    return out


CACHE: dict = {}


def body_frame(kind, variant="idle", phase=0, rage=False):
    """Cached body grid. variant: idle/left/right/shoot/dmg/charge/warn."""
    key = (kind, variant, phase, rage)
    if key in CACHE:
        return CACHE[key]
    damage = variant == "dmg"
    cells = _materialize(kind, phase=phase % 2, damage=damage, rage=rage)
    w = len(cells[0])
    cx = w // 2
    if variant == "left":
        cells = _shear(cells, -1, cx)
    elif variant == "right":
        cells = _shear(cells, 1, cx)
    elif variant == "charge":
        # core charging: brighten core block to white-hot
        for y, row in enumerate(cells):
            for x, cell in enumerate(row):
                leg = _BASES[kind][y][x]
                if leg in ("C", "c"):
                    cells[y][x] = ("█", tc((255, 255, 255), C.BRIGHT_WHITE))
    elif variant == "warn":
        # warning flash: edges blink white (mirror-safe checker)
        w = len(cells[0])
        for y, row in enumerate(cells):
            for x, cell in enumerate(row):
                leg = _BASES[kind][y][x]
                mx = min(x, w - 1 - x)
                if leg == "E" and (mx + phase) % 2 == 0:
                    cells[y][x] = ("▓", tc((255, 255, 255), C.BRIGHT_WHITE))
    CACHE[key] = cells
    return cells


# ------------------------------------------------------------------ flames
def draw_flames_up(renderer, cx, y_top, frame_idx, kind):
    """Engine flames ABOVE the ship (enemies fly nose-down). y_top grows up."""
    stacks, leg = STACKS[kind]
    length = FLAME_LEN[frame_idx % len(FLAME_LEN)]
    ch, rgb, fb = STYLES[kind][leg]
    col = tc(rgb, fb)
    tip = tc((200, 220, 255), C.WHITE)
    for dx in stacks:
        x = int(cx + dx)
        for i in range(length):
            y = int(y_top - i)
            c = col if i < length - 1 else tip
            renderer.put(x, y, "▓" if i == 0 else "∙", c)


def draw_muzzle_down(renderer, cx, y_nose, kind, big=True):
    ch, rgb, fb = PROJECTILE.get(kind, PROJECTILE["fighter"])[:3]
    col = tc(rgb, fb)
    renderer.put(int(cx), int(y_nose + 1), "*" if big else "∙", col)
    if big:
        renderer.put(int(cx), int(y_nose + 2), "∙", col)


# ------------------------------------------------------------------ wrecks
def destroy_frame(kind, stage):
    """4 tinted breakup stages sized to the body. stage 0..3."""
    key = ("wreck", kind, stage)
    if key in CACHE:
        return CACHE[key]
    import math
    import random
    w, h = SIZES[kind]
    cx, cy = w // 2, h // 2
    core_rgb, spark_rgb = WRECK_TINT[kind]
    if stage == 0:
        cells = _materialize(kind, damage=True)
        rng = random.Random(hash(kind) % 999 + 1)
        for _ in range(max(6, w)):
            x = cx + rng.randint(-w // 2, w // 2)
            y = rng.randint(0, h - 1)
            if 0 <= x < w:
                cells[y][x] = ("*", tc(spark_rgb, C.BRIGHT_YELLOW))
    elif stage == 1:
        cells = _materialize(kind, damage=True)
        rng = random.Random(hash(kind) % 999 + 41)
        for _ in range(max(10, w * 2)):
            x = cx + rng.randint(-w // 2, w // 2)
            y = cy + rng.randint(-h // 2, h // 2)
            if 0 <= x < w and 0 <= y < h:
                cells[y][x] = (rng.choice(["█", "▓", "*"]), tc(core_rgb, C.YELLOW))
    elif stage == 2:
        cells = _blank(w, h)
        rng = random.Random(hash(kind) % 999 + 77)
        r = max(2.5, w / 3.2)
        for y in range(h):
            for x in range(w):
                d = math.hypot(x - cx, (y - cy) * 1.6)
                if d < r * 0.45:
                    cells[y][x] = ("█", tc((255, 255, 255), C.BRIGHT_WHITE))
                elif d < r * 0.8:
                    cells[y][x] = (rng.choice(["█", "▓"]), tc(core_rgb, C.YELLOW))
                elif d < r and rng.random() < 0.7:
                    cells[y][x] = (rng.choice(["▓", "*", "∙"]), tc(spark_rgb, C.RED))
    else:
        cells = _blank(w, h)
        rng = random.Random(hash(kind) % 999 + 99)
        for _ in range(max(8, w)):
            x = cx + rng.randint(-w // 2, w // 2)
            y = rng.randint(0, h - 1)
            cells[y][x] = (rng.choice(["·", "∙", "░"]), tc((120, 130, 150), C.BRIGHT_BLACK))
    CACHE[key] = cells
    return cells


def wreck_particles(particles, x, y, kind):
    import random
    core_rgb, spark_rgb = WRECK_TINT[kind]
    for _ in range(18):
        particles.spawn(
            x + random.uniform(-4, 4), y + random.uniform(-3, 3),
            vx=random.uniform(-22, 22), vy=random.uniform(-14, 14),
            life=random.uniform(0.3, 0.8),
            char=random.choice(["*", "x", "∙", "▓"]),
            color=tc(random.choice([core_rgb, spark_rgb]), C.YELLOW))


def dims(kind):
    return SIZES[kind]
