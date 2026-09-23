"""Circle-ish collision helpers tuned for terminal cell aspect ratio.

Cells are ~2x taller than wide visually; weight dx slightly so hitboxes
feel fair. All functions are pure and headless-testable.
"""

X_WEIGHT = 0.55


def dist2(ax, ay, bx, by):
    dx = (ax - bx) * X_WEIGHT
    dy = (ay - by)
    return dx * dx + dy * dy


def collides(ax, ay, ar, bx, by, br):
    r = ar + br
    return dist2(ax, ay, bx, by) <= r * r


def point_in_enemy(px, py, enemy):
    return collides(px, py, 0.5, enemy.x, enemy.y, enemy.radius)


def point_in_boss(px, py, boss):
    # boss is wide: use ellipse-ish test (31x12 capital ship)
    dx = abs(px - boss.x)
    dy = abs(py - boss.y)
    return dx < 15 and dy < 6
