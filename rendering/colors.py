"""ANSI color palette for STARFALL: TERMINAL WAR.

Central place for all escape codes so gameplay code never hard-codes them.
Uses bright variants for a neon arcade feel. Keep color usage meaningful:
  cyan    -> player        red     -> enemies
  yellow  -> projectiles   green   -> health / power-ups
  blue    -> shields       magenta -> special attacks
  white   -> stars / UI    dim     -> distant background
"""

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
BLINK = "\x1b[5m"
REVERSE = "\x1b[7m"

BLACK = "\x1b[30m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
BLUE = "\x1b[34m"
MAGENTA = "\x1b[35m"
CYAN = "\x1b[36m"
WHITE = "\x1b[37m"

BRIGHT_BLACK = "\x1b[90m"
BRIGHT_RED = "\x1b[91m"
BRIGHT_GREEN = "\x1b[92m"
BRIGHT_YELLOW = "\x1b[93m"
BRIGHT_BLUE = "\x1b[94m"
BRIGHT_MAGENTA = "\x1b[95m"
BRIGHT_CYAN = "\x1b[96m"
BRIGHT_WHITE = "\x1b[97m"

BG_BLACK = "\x1b[40m"

# Semantic aliases
PLAYER = BRIGHT_CYAN
PLAYER_ENGINE = BRIGHT_YELLOW
ENEMY = BRIGHT_RED
ENEMY_ELITE = BRIGHT_MAGENTA
BOSS = BRIGHT_RED
BULLET_PLAYER = BRIGHT_YELLOW
BULLET_ENEMY = BRIGHT_RED
POWERUP = BRIGHT_GREEN
SHIELD = BRIGHT_BLUE
NOVA = BRIGHT_MAGENTA
SCORE = BRIGHT_YELLOW
STAR_DIM = BRIGHT_BLACK
STAR_MID = WHITE
STAR_BRIGHT = BRIGHT_WHITE
HUD_BORDER = CYAN
HUD_TEXT = BRIGHT_WHITE
WARNING = BRIGHT_RED
OK = BRIGHT_GREEN
