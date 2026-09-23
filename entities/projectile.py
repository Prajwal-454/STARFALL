"""Projectiles for both sides. Data-only + helpers."""

from rendering import colors as C


class Projectile:
    __slots__ = ("x", "y", "vx", "vy", "friendly", "damage", "char",
                 "color", "life", "radius", "trail_t", "grazed", "source")

    def __init__(self, x, y, vx, vy, friendly=True, damage=10.0,
                 char="|", color="", life=3.0, radius=0.9, source=""):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.friendly = friendly
        self.damage = float(damage)
        self.char = char
        self.color = color or (C.BULLET_PLAYER if friendly else C.BULLET_ENEMY)
        self.life = float(life)
        self.radius = float(radius)
        self.trail_t = 0.0
        self.grazed = False  # bullet-graze bonus claimed once
        self.source = source  # e.g. "FIGHTER", "BOSS LASER" (death recap)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.trail_t += dt
        return self.life > 0

    def draw(self, renderer):
        # muzzle glow: brighter head char
        head = "!" if self.friendly and abs(self.vy) > 40 else self.char
        renderer.put(self.x, self.y, head, self.color)


def player_shots(x, y, weapon_level, damage_mult=1.0, speed=55.0, damage=12.0):
    """Aurora gun streams for the compact 7x5 hull.

    Guns (rel ship center): nose (0,-3), wings (-2,0)/(+2,0). All streams
    stay within ~2 cells of the hull so shots visibly leave the ship.
    """
    from rendering import aurora as A
    dmg = damage * damage_mult
    nose = A.GUNS[0]          # (0, -3)
    left = A.GUNS[1]          # (-2, 0)
    right = A.GUNS[2]         # (+2, 0)
    shots = []

    def stream(gx, gy, vx=0.0, mult=1.0, char="|", color="", spd=1.0):
        shots.append(Projectile(x + gx, y + gy, vx, -speed * spd, True,
                                dmg * mult, char,
                                color or C.BULLET_PLAYER))

    if weapon_level <= 1:
        stream(*nose, char="!", color=C.BRIGHT_YELLOW)
    elif weapon_level == 2:
        stream(*left)
        stream(*right)
    elif weapon_level == 3:
        stream(*nose, char="!", color=C.BRIGHT_YELLOW, spd=1.1)
        stream(*left, vx=-6, mult=0.8, char="/")
        stream(*right, vx=6, mult=0.8, char="\\")
    elif weapon_level == 4:
        stream(nose[0] - 1, nose[1], char="!", color=C.BRIGHT_YELLOW, spd=1.1)
        stream(nose[0] + 1, nose[1], char="!", color=C.BRIGHT_YELLOW, spd=1.1)
        stream(*left, vx=-10, mult=0.8, char="/")
        stream(*right, vx=10, mult=0.8, char="\\")
    else:
        stream(*nose, char="!", color=C.BRIGHT_WHITE, spd=1.25, mult=1.2)
        stream(left[0], left[1], vx=0, char="|", color=C.BRIGHT_YELLOW)
        stream(right[0], right[1], vx=0, char="|", color=C.BRIGHT_YELLOW)
        stream(*left, vx=-12, mult=0.8, char="/")
        stream(*right, vx=12, mult=0.8, char="\\")
    return shots
