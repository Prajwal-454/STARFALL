"""Game states + shared mutable run data."""

from enum import Enum, auto


class GameState(Enum):
    MENU = auto()
    BRIEFING = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    CONTROLS = auto()
    SCORES = auto()


class RunStats:
    def __init__(self):
        self.kills = 0
        self.shots = 0
        self.hits = 0
        self.novas = 0
        self.powerups = 0
        self.damage_taken = 0.0
        self.time_alive = 0.0

    def accuracy(self):
        return (self.hits / self.shots * 100.0) if self.shots else 0.0
