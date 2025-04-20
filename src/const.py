import os
import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_MARGIN = 48
TILE_SIZE = 32
FPS = 60
MAP_VIEW_SIZE = 14

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PINK = (255, 100, 100)

# SHOP
SHOP_MARGIN = 50
SHOP_LINE_H = 30
SHOP_LINE_W = 200
SHOP_IMG_X, SHOP_IMG_Y = SCREEN_WIDTH - SHOP_MARGIN - TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE - 36

# Counters
RIGHT_CLICK_VIEW_COUNTER_DEF = FPS * 1.5
HINT_COUNTER_DEF = FPS * 1.5
SHOP_OPEN_DELAY_COUNTER_DEF = 2

# Info Strings
# use tuple to avoid unexpected modification
# example: `info_string = list(DEFAULT_INFO_STRING)`
DEFAULT_INFO_STRING = ('Welcome to TinyWar!', 'Press [H] for help.')

HELP_STRING = ['[WSAD] Move Map  [Space|Middle Click] Next Turn  [Right Click] View Attack Range',
               '[F5] Save  [F9] Load  [F1] New Game  [Esc] Quit  [H] Next Page',
                '1', 
                '2' ]

SHOP_DEFAULT_STRING = ('{type}',
                       '[Left Click] Buy  [Right Click] Exit'
                       )

class HINTS:
    INVALID_LEVEL = 'Invalid level number.'
    NO_FILE = 'Game save not found.'
    FILE_ERROR = 'Level file error.'
    SAVE = 'Game Saved'
    LOAD = 'Game Loaded'

class GameState:
    MENU = 0
    PLAYING = 1
    GAME_OVER = 2
    SHOP = 3


class EffectType:
    Death = 0

PlayerNameDict = {
    0: 'Red',
    1: 'Blue',
}

class SHOP_TYPE:
    NONE = 0
    GROUND = 1
    AIR = 2
    SEA = 3

class MoveType:
    Feet = 0
    Wheel = 1
    Track = 2
    Air = 3
    Sea = 4
    Sub = 5
"""
用-1表示不可移动
"""
class Terrain:
    PLAIN = 0
    HILL = 1
    FOREST = 2
    MOUNTAIN = 3
    ROAD = 4

    CHAR_MAP = {
        'P': PLAIN,
        'H': HILL,
        'F': FOREST,
        'M': MOUNTAIN,
        'R': ROAD
    }

    PROPERTIES = {
        PLAIN: {
            'defence_factor': 0,
            'move_cost_0': 1,
            'move_cost_1': 1.5,
            'move_cost_2': 1.5,
            'move_cost_3': 1,
        },
        HILL: {
            'defence_factor': 0.1,
            'move_cost_0': 1,
            'move_cost_1': 1.5,
            'move_cost_2': 2,
            'move_cost_3': 1,
        },
        FOREST: {
            'defence_factor': 0.2,
            'move_cost_0': 2,
            'move_cost_1': 3,
            'move_cost_2': 5,
            'move_cost_3': 1,
        },
        MOUNTAIN: {
            'defence_factor': 0.4,
            'move_cost_0': 4,
            'move_cost_1': -1,
            'move_cost_2': -1,
            'move_cost_3': 1,
        },
        ROAD: {
            'defence_factor': 0,
            'move_cost_0': 1,
            'move_cost_1': 0.9,
            'move_cost_2': 0.9,
            'move_cost_3': 1,
        }
    }

"""Functions"""


def capital_words(string):
    return ' '.join([word.capitalize() for word in string.split()])


"""Preload"""

preload_unit_imgs = {}
for png in os.listdir('assets/unit'):
    if png.endswith('.png'):
        preload_unit_imgs[png] = pygame.image.load(f'assets/unit/{png}')
preload_terrain_imgs = {}
for png in os.listdir('assets/terrain'):
    if png.endswith('.png'):
        preload_terrain_imgs[png] = pygame.image.load(f'assets/terrain/{png}')
