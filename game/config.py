"""Tuning constants and difficulty curve for STARFALL."""

TARGET_FPS = 60
DT_FIXED = 1.0 / 60.0

HUD_HEIGHT = 7
BOTTOM_RESERVED = 2
MIN_W, MIN_H = 80, 24

# --- player ---
PLAYER_SPEED = 46.0
PLAYER_ACCEL = 260.0
PLAYER_FRICTION = 6.5
PLAYER_MAX_HP = 100.0
PLAYER_MAX_SHIELD = 60.0
PLAYER_MAX_ENERGY = 100.0
PLAYER_FIRE_COOLDOWN = [0.22, 0.19, 0.16, 0.13, 0.10]  # per weapon level 1..5
PLAYER_BULLET_SPEED = 55.0
PLAYER_BULLET_DAMAGE = 12.0
INVULN_TIME = 1.2
SHIELD_REGEN_DELAY = 3.0
SHIELD_REGEN_RATE = 10.0
NOVA_MAX = 3
NOVA_RADIUS = 26.0
NOVA_DAMAGE = 120.0

# --- difficulty curve: multiplier per wave ---
def difficulty_mult(wave):
    return 1.0 + (wave - 1) * 0.14

def enemy_hp_mult(wave):
    return 1.0 + (wave - 1) * 0.18

def enemy_speed_mult(wave):
    return min(1.8, 1.0 + (wave - 1) * 0.05)

# --- score values ---
SCORES = {
    "fighter": 100,
    "interceptor": 250,
    "tank": 500,
    "bomber": 400,
    "elite": 1000,
    "minion": 50,
    "boss": 10000,
}

WIN_WAVE = 11  # defeating the wave-11 boss => VICTORY (endless continues)
