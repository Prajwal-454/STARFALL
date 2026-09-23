"""THE AURORA — authoritative player-ship sprite module.

Compact interceptor (7 wide x 5 tall) built PROCEDURALLY with mirrored
construction so symmetry is guaranteed by construction. Same identity as
before — pointed nose, blue canopy, swept wings, side pods, THREE exhausts,
amber lights, cyan edges — but ~40% smaller on screen.

Why small (shmup readability theory):
  * Old 11x8 hull covered ~9% of a 120-col field and ~23% of field height,
    hiding bullets behind the sprite and making the visual dwarf the
    hitbox (half-width 5 vs hit radius 2.0) — hits felt unfair.
  * New 7x5 hull (~6% width, ~14% height) keeps the hitbox (r=1.5) close
    to the visual, leaves bullet lanes visible around the wings, and still
    reads bigger than minions (5x3) but smaller than fighters (9x7).
Flames are short (1-3 cells) so the ship+flame stack never exceeds ~8 rows.
"""

import os

from rendering import colors as C

BODY_W, BODY_H = 7, 5
CX, CY = 3, 2  # body center in cells

# ------------------------------------------------------------------ color
# True-color RGB where supported, 16-color ANSI fallback otherwise.
# Override with STARFALL_16COLOR=1 (legacy conhost without 24-bit support).


def _truecolor_wanted():
    if os.environ.get("STARFALL_16COLOR") == "1":
        return False
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return True
    if os.environ.get("WT_SESSION") or os.environ.get("TERM_PROGRAM"):
        return True
    term = os.environ.get("TERM", "")
    if "256color" in term or "truecolor" in term:
        return True
    # Windows Terminal / modern conhost handle 24-bit fine; default on.
    return True


TRUECOLOR = _truecolor_wanted()


def tc(rgb, fallback):
    if TRUECOLOR:
        r, g, b = rgb
        return f"\x1b[38;2;{r};{g};{b}m"
    return fallback


PAL = {
    "hot":    tc((255, 255, 255), C.BRIGHT_WHITE),    # nose tip / white-hot
    "hull":   tc((232, 238, 247), C.BRIGHT_WHITE),    # white armor
    "hullsh": tc((154, 167, 196), C.WHITE),           # silver shading
    "line":   tc((27, 35, 64), C.BRIGHT_BLACK),       # dark navy outline
    "cock":   tc((14, 99, 230), C.BLUE),              # deep blue glass
    "cockhi": tc((127, 231, 255), C.BRIGHT_CYAN),     # canopy shine
    "edge":   tc((39, 230, 255), C.BRIGHT_CYAN),      # cyan edge lighting
    "wing":   tc((220, 228, 242), C.WHITE),           # wing surface
    "wingsh": tc((139, 152, 184), C.BRIGHT_BLACK),    # wing shade
    "pod":    tc((228, 234, 246), C.BRIGHT_WHITE),    # pod housing
    "podsh":  tc((147, 160, 190), C.WHITE),           # pod shade
    "amber":  tc((255, 154, 31), C.YELLOW),           # orange/amber lights
    "amberhi": tc((255, 205, 120), C.BRIGHT_YELLOW),
    "nozzle": tc((91, 107, 140), C.BRIGHT_BLACK),     # engine nozzle metal
    "muzzle": tc((255, 255, 255), C.BRIGHT_WHITE),
    "core":   tc((255, 255, 255), C.BRIGHT_WHITE),    # flame white core
    "mid":    tc((84, 232, 255), C.BRIGHT_CYAN),      # flame cyan
    "outer":  tc((30, 107, 255), C.BLUE),             # flame blue
    "tip":    tc((159, 220, 255), C.CYAN),            # flame tip fade
    "flash":  tc((255, 255, 255), C.BRIGHT_WHITE),
    "spark":  tc((255, 59, 48), C.BRIGHT_RED),
    "fire1":  tc((255, 228, 94), C.BRIGHT_YELLOW),
    "fire2":  tc((255, 154, 31), C.YELLOW),
    "fire3":  tc((255, 77, 0), C.RED),
    "fire4":  tc((120, 20, 0), C.RED),
    "smoke":  tc((120, 130, 150), C.BRIGHT_BLACK),
    "shield": tc((60, 220, 255), C.BRIGHT_CYAN),
    "shield2": tc((20, 110, 255), C.BLUE),
}

# Legend -> (display char, palette key). All block/geo chars, no emoji.
# (Cell grids are typed as plain `list` so layered (char, color) tuples blit cleanly.)
GLYPH = {
    "A": ("█", "hot"),
    "H": ("█", "hull"),
    "h": ("▓", "hullsh"),
    "D": ("▓", "line"),
    "C": ("█", "cock"),
    "c": ("█", "cockhi"),
    "E": ("▓", "edge"),
    "W": ("█", "wing"),
    "w": ("▒", "wingsh"),
    "P": ("█", "pod"),
    "p": ("▓", "podsh"),
    "O": ("█", "amber"),
    "V": ("█", "nozzle"),
}

# Fuselage half-width (each side, inclusive) per body row 0..4.
# Row 3 stays widest so wing roots + side pods read clearly.
HULL_PROFILE = [0, 1, 1, 2, 1]
POD_X = (2,)                # engine pod column (right side; mirrored left)
POD_ROWS = range(2, 4)
# Swept wing: right-side (col -> top row) + bottom row. Tips low/outboard.
# Columns overlap row-wise so the surface is solid (no transparent holes).
WING_TOP = {2: 2, 3: 3}
WING_BOT = {2: 3, 3: 4}
AMBER_CELLS = [(2, 2)]   # (right-x, row) pod flank
EXHAUST_X = (-2, 0, 2)  # three main engines, rel to center
GUNS = [(0, -3), (-2, 0), (2, 0)]        # (dx, dy) rel ship center
NOSE = (0, -3)


def _blank() -> list:
    return [[None] * BODY_W for _ in range(BODY_H)]


def _set(grid, x, y, legend):
    if 0 <= x < BODY_W and 0 <= y < BODY_H and legend:
        grid[y][x] = legend


def _build_base():
    """Symmetric hull + canopy + wings + pods + nozzles (no lights)."""
    g = _blank()
    # -- wings first (under everything)
    for side in (1, -1):
        for rx, top in WING_TOP.items():
            bot = WING_BOT[rx]
            x = CX + side * rx
            for y in range(top, bot + 1):
                _set(g, x, y, "W")
            _set(g, x, top, "E")                    # cyan leading edge
            _set(g, x, bot, "w")                    # shaded trailing edge
    # -- engine pods (over wings)
    for side in (1, -1):
        for i, rx in enumerate(POD_X):
            x = CX + side * rx
            for y in POD_ROWS:
                _set(g, x, y, "P")
            _set(g, x, POD_ROWS.start, "E")         # pod intake glow
            _set(g, x, POD_ROWS.stop - 1, "p")      # pod shade aft
    # -- fuselage (over wing roots)
    for y, hw in enumerate(HULL_PROFILE):
        for dx in range(-hw, hw + 1):
            _set(g, CX + dx, y, "H")
        _set(g, CX - hw, y, "D")                    # dark navy outline
        _set(g, CX + hw, y, "D")
    _set(g, CX, 0, "A")                             # pointed nose tip
    _set(g, CX, 1, "H")
    # -- canopy: deep-blue glass, bright shine (compact 2-row version)
    _set(g, CX, 1, "c")
    for dx in (-1, 0, 1):
        _set(g, CX + dx, 2, "C")
    _set(g, CX, 2, "c")                             # shine sweep center
    # -- engine nozzles: center + under each pod (tail row)
    for dx in EXHAUST_X:
        _set(g, CX + dx, BODY_H - 1, "V")
    return g


_BASE = _build_base()


def _materialize(grid, idle_phase=0, damage=False):
    """Legend grid -> cell grid with per-frame lighting.

    idle_phase 0..3: canopy shimmer, cyan edge pulse, amber blink.
    damage: hull flashes white/red.
    """
    cells: list = [[None] * BODY_W for _ in range(BODY_H)]
    amber_on = (idle_phase % 2 == 0)
    edge_bright = (idle_phase in (0, 1))
    for y in range(BODY_H):
        for x in range(BODY_W):
            leg = grid[y][x]
            if leg is None:
                continue
            ch, key = GLYPH[leg]
            if damage:
                if leg in ("H", "W", "P", "h", "w", "p"):
                    mx = min(x, BODY_W - 1 - x)  # mirror-safe checkerboard
                    key = "flash" if (mx + y + idle_phase) % 2 == 0 else "spark"
                elif leg in ("C", "c", "E"):
                    key = "flash"
            else:
                if leg == "O":
                    key = "amberhi" if amber_on else "amber"
                elif leg == "E" and not edge_bright:
                    key = "shield2"  # dimmer cyan on off-phase
                elif leg == "c" and idle_phase == 2:
                    key = "cock"     # canopy shimmer sweep
            cells[y][x] = (ch, PAL[key])
    return cells


def _shear(cells, bank):
    """Bank left/right: shift rows progressively, dim raised wingtip."""
    out: list = [[None] * BODY_W for _ in range(BODY_H)]
    for y in range(BODY_H):
        off = int(round((y - CY) * 0.30 * bank))
        for x in range(BODY_W):
            cell = cells[y][x]
            if cell is None:
                continue
            nx = x + off
            if 0 <= nx < BODY_W:
                ch, col = cell
                # dim the lifted wing side slightly
                if bank != 0 and ((bank < 0 and nx > CX + 3) or
                                  (bank > 0 and nx < CX - 3)):
                    col = PAL["wingsh"] if "255" not in col and "38;2" not in col else col
                out[y][nx] = (ch, col)
    return out


def _amber_points(grid):
    pts = []
    for rx, y in AMBER_CELLS:
        for side in (1, -1):
            pts.append((CX + side * rx, y))
    return pts


def _with_lights(cells, idle_phase):
    out = [row[:] for row in cells]
    on = (idle_phase % 2 == 0)
    for x, y in _amber_points(_BASE):
        out[y][x] = ("█", PAL["amberhi" if on else "amber"])
    # wingtip tip lights (outer bottom corners of the 7-wide hull)
    for side in (1, -1):
        out[BODY_H - 2][CX + side * 3] = ("▓", PAL["edge"])
    return out


# ------------------------------------------------------------- frame cache
CACHE = {}


def _key(kind, phase):
    return (kind, phase)


def body_frame(kind="idle", phase=0):
    """Return cached 7x5 cell grid. kind: idle/left/right/shoot/dmg."""
    k = _key(kind, phase)
    if k in CACHE:
        return CACHE[k]
    if kind in ("left", "right"):
        bank = -1 if kind == "left" else 1
        cells = _materialize(_BASE, idle_phase=phase % 4)
        cells = _shear(cells, bank)
    elif kind == "dmg":
        cells = _materialize(_BASE, idle_phase=phase % 2, damage=True)
    else:  # idle / shoot share the hull; muzzle handled at draw time
        cells = _materialize(_BASE, idle_phase=phase % 4)
    cells = _with_lights(cells, phase)
    CACHE[k] = cells
    return cells


# ------------------------------------------------------------- engine flames
FLAME_BASE = [1, 2, 4, 2, 3, 2]  # 6-frame cycle lengths (short: ship is small)


def flame_length(frame_idx, thrust=0):
    """thrust: -1 (descend) / 0 / +1 (climb)."""
    return max(1, FLAME_BASE[frame_idx % 6] + (1 if thrust > 0 else 0))


def draw_flames(renderer, cx, cy_top, frame_idx, thrust=0):
    """Draw the 3 exhaust flames; cy_top = first flame row (below nozzles)."""
    length = flame_length(frame_idx, thrust)
    for dx in EXHAUST_X:
        x0 = int(cx + dx)
        for i in range(length):
            y = int(cy_top + i)
            frac = i / max(1, length - 1)
            if i == 0:
                ch, col = "█", PAL["core"]
            elif frac < 0.5:
                ch, col = "█", PAL["mid"] if i % 2 == 0 else PAL["core"]
            elif frac < 0.8:
                ch, col = "▓", PAL["mid"] if dx == 0 else PAL["outer"]
            else:
                ch, col = "∙", PAL["tip"]
            # compact single-column flame: matches the 7-wide hull
            renderer.put(x0, y, ch, col)
        # fading ember below tip
        renderer.put(x0, cy_top + length, "·", PAL["tip"])


def exhaust_world(cx, cy):
    """World coords of the 3 exhaust mouths (for particles)."""
    return [(cx + dx, cy + 2) for dx in EXHAUST_X]


# ------------------------------------------------------------- muzzle flash
def draw_muzzle(renderer, cx, cy, big=True):
    for dx, dy in GUNS:
        x, y = int(cx + dx), int(cy + dy - 1)
        if big:
            renderer.put(x, y, "*", PAL["muzzle"])
            renderer.put(x, y - 1, "▀", PAL["mid"])
        else:
            renderer.put(x, y, "∙", PAL["mid"])


# ------------------------------------------------------------- shield bubble
def draw_shield(renderer, cx, cy, t):
    """Transparent pulsing bubble sized to the 7x5 hull (ship stays visible)."""
    rx, ry = 4.5, 3.2
    phase = int(t * 6) % 3
    for i in range(64):
        import math
        a = (i / 64) * 2 * math.pi
        # marching dashes: only a rotating subset of the ellipse
        if (i + phase) % 3 != 0:
            continue
        x = int(cx + math.cos(a) * rx)
        y = int(cy + math.sin(a) * ry * 0.62)
        ch = "o" if i % 2 == 0 else "·"
        col = PAL["shield"] if (i // 3) % 2 == 0 else PAL["shield2"]
        renderer.put(x, y, ch, col)


# ------------------------------------------------------------- destruction
def destroy_frame(stage):
    """4 breakup stages; stage 0..3. Returns cell grid (7x5)."""
    hw = BODY_W // 2
    k = ("destroy", stage)
    if k in CACHE:
        return CACHE[k]
    if stage == 0:
        # damage flash + cracks + sparks erupting
        cells = _materialize(_BASE, idle_phase=0, damage=True)
        cells = _with_lights(cells, 0)
        import random
        rng = random.Random(7)
        for _ in range(8):
            x = CX + rng.randint(-hw, hw)
            y = rng.randint(1, BODY_H - 2)
            if 0 <= x < BODY_W:
                cells[y][x] = ("*", PAL["spark"] if _ % 2 else PAL["amberhi"])
    elif stage == 1:
        # halves shear apart, fire at the core
        cells: list = [[None] * BODY_W for _ in range(BODY_H)]
        base = _materialize(_BASE, idle_phase=1, damage=True)
        for y in range(BODY_H):
            for x in range(BODY_W):
                cell = base[y][x]
                if cell is None:
                    continue
                nx = x + (-1 if x < CX else 1)
                if 0 <= nx < BODY_W:
                    cells[y][nx] = cell
        import random
        rng = random.Random(11)
        for _ in range(14):
            x = CX + rng.randint(-2, 2)
            y = CY + rng.randint(-2, 2)
            if 0 <= x < BODY_W and 0 <= y < BODY_H:
                key = rng.choice(["fire1", "fire2", "fire3"])
                cells[y][x] = (rng.choice(["█", "▓", "*"]), PAL[key])
    elif stage == 2:
        # fireball blob with white-hot core + debris (scaled to 7x5)
        import math
        import random
        rng = random.Random(21)
        cells: list = [[None] * BODY_W for _ in range(BODY_H)]
        for y in range(BODY_H):
            for x in range(BODY_W):
                d = math.hypot(x - CX, (y - CY) * 1.6)
                if d < 0.8:
                    cells[y][x] = ("█", PAL["flash"])
                elif d < 1.6:
                    cells[y][x] = (rng.choice(["█", "▓"]), PAL["fire1"])
                elif d < 2.6:
                    cells[y][x] = (rng.choice(["▓", "▒", "*"]), PAL["fire2"])
                elif d < 3.2 and rng.random() < 0.6:
                    cells[y][x] = (rng.choice(["*", "∙", "x"]), PAL["fire3"])
        for _ in range(6):  # hull debris
            x = CX + rng.randint(-hw, hw)
            y = rng.randint(0, BODY_H - 1)
            if 0 <= x < BODY_W:
                cells[y][x] = (rng.choice(["◤", "◢", "x", "▓"]), PAL["hullsh"])
    else:
        # fading embers + smoke
        import random
        rng = random.Random(33)
        cells: list = [[None] * BODY_W for _ in range(BODY_H)]
        for _ in range(12):
            x = CX + rng.randint(-hw, hw)
            y = rng.randint(0, BODY_H - 1)
            cells[y][x] = (rng.choice(["·", "∙", "░"]),
                           PAL["smoke"] if _ % 3 == 0 else PAL["fire4"])
    CACHE[k] = cells
    return cells


# ------------------------------------------------------------- particles
def exhaust_particles(particles, cx, cy, thrust=0):
    """Spawn one tick of triple-engine exhaust (call every frame)."""
    import random
    for i, (ex, ey) in enumerate(exhaust_world(cx, cy)):
        n = 2 if thrust >= 0 else 1
        for _ in range(n):
            vy = 14 + thrust * 5 + random.uniform(0, 8)
            particles.spawn(
                ex + random.uniform(-0.8, 0.8), ey,
                vx=random.uniform(-2.5, 2.5), vy=vy,
                life=random.uniform(0.2, 0.45),
                char=random.choice(["█", "▓", "∙", "|"]),
                color=random.choice([PAL["core"], PAL["mid"], PAL["outer"]]),
            )


def damage_sparks(particles, cx, cy):
    import random
    for _ in range(12):
        particles.spawn(
            cx + random.uniform(-2, 2), cy + random.uniform(-1.5, 1.5),
            vx=random.uniform(-20, 20), vy=random.uniform(-14, 14),
            life=random.uniform(0.25, 0.6),
            char=random.choice(["*", "x", "∙", "'"]),
            color=random.choice([PAL["spark"], PAL["amberhi"], PAL["flash"]]),
        )


def muzzle_particles(particles, cx, cy):
    import random
    for dx, dy in GUNS:
        particles.spawn(cx + dx, cy + dy - 1,
                        vx=random.uniform(-2, 2), vy=random.uniform(-16, -8),
                        life=random.uniform(0.1, 0.25),
                        char=random.choice(["*", "∙", "▀"]),
                        color=random.choice([PAL["muzzle"], PAL["mid"]]))
