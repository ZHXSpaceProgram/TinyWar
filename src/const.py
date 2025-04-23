import os
import pygame


# region View  ----------------------------------------  View  -----------

SCREEN_WIDTH = 1000  # 800
SCREEN_HEIGHT = 800  # 600
MAP_VIEW_SIZE = 13  # 14
TILE_SIZE = 48  # 32

SCREEN_MARGIN = 48
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (100, 255, 100)
YELLOW = (255, 255, 0)
PINK = (255, 100, 120)
LIGHT_PINK = (255, 182, 192)

# SHOP
SHOP_MARGIN = 50
SHOP_LINE_H = min((SCREEN_HEIGHT - 2 * SHOP_MARGIN ) // 150 * 10, 45)
SHOP_LINE_W = 200
SHOP_X_SPACE = 50
SHOP_X_MARGIN  = (SCREEN_WIDTH - 600 -2*SHOP_X_SPACE) // 2
SHOP_Y_MARGIN = max((SCREEN_HEIGHT - 15 * SHOP_LINE_H) // 2 - 30, SHOP_MARGIN)
SHOP_IMG_X, SHOP_IMG_Y = SCREEN_WIDTH - SHOP_MARGIN - TILE_SIZE, SCREEN_HEIGHT - TILE_SIZE - 36
MONEY_Y = SCREEN_HEIGHT - TILE_SIZE // 2 - 42

# Counters
RIGHT_VIEW_REMOVE_COUNTER_DEF = 5
HINT_COUNTER_DEF = FPS * 1.5
SHOP_OPEN_DELAY_COUNTER_DEF = 5

# Info Strings
# use tuple to avoid unexpected modification
# example: `info_string = list(DEFAULT_INFO_STRING)`
DEFAULT_INFO_STRING = ('Welcome to TinyWar!', 'Press [H] for help.')

HELP_STRING = ['[WSAD|Mouse Drag] Move Map  [Space|Middle Click] Next Turn',
               '[F1] New Game  [F5] Save  [F9] Load  [Esc] Quit  [H] Next Page',
                'Tip 1: Select a unit and right-drag the mouse to preview attack ranges for both the selected', ## max length
                'unit (red dots) and enemy units (exclamation marks).' ,
                'Tip 2: ',
                'wewe'
                ]

SHOP_DEFAULT_STRING = ('{type}',
                       '[Left Click] Buy  [Right Click] Exit'
                       )

class HINTS:
    INVALID_LEVEL = 'Invalid level number.'
    INVALID_YN = 'Please enter Y or N.'
    NO_FILE = 'Game save not found.'
    FILE_ERROR = 'Level file error.'
    SAVE = 'Game Saved'
    LOAD = 'Game Loaded'

# endregion View

# region Game  ----------------------------------------  Game  -----------

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
    WATER = 5
    SEA = 6
    REEF = 7
    
    CHAR_MAP = {
        'P': PLAIN,
        'H': HILL,
        'F': FOREST,
        'M': MOUNTAIN,
        'R': ROAD,
        'W': WATER,
        'S': SEA,
        'E': REEF
    }

    PROPERTIES = {
        PLAIN: {
            'defence_factor': 0,
            'move_cost_0': 1,
            'move_cost_1': 1.5,
            'move_cost_2': 1.5,
            'move_cost_3': 1,
            'move_cost_4': -1,
            'move_cost_5': -1,
        },
        HILL: {
            'defence_factor': 0.1,
            'move_cost_0': 1,
            'move_cost_1': 1.5,
            'move_cost_2': 2,
            'move_cost_3': 1,
            'move_cost_4': -1,
            'move_cost_5': -1,
        },
        FOREST: {
            'defence_factor': 0.2,
            'move_cost_0': 2,
            'move_cost_1': 3,
            'move_cost_2': 5,
            'move_cost_3': 1,
            'move_cost_4': -1,
            'move_cost_5': -1,
        },
        MOUNTAIN: {
            'defence_factor': 0.4,
            'move_cost_0': 4,
            'move_cost_1': -1,
            'move_cost_2': -1,
            'move_cost_3': 1,
            'move_cost_4': -1,
            'move_cost_5': -1,
        },
        ROAD: {
            'defence_factor': 0,
            'move_cost_0': 1,
            'move_cost_1': 0.9,
            'move_cost_2': 0.9,
            'move_cost_3': 1,
            'move_cost_4': -1,
            'move_cost_5': -1,
        },
        WATER: {
            'defence_factor': 0,
            'move_cost_0': 2,
            'move_cost_1': 3,
            'move_cost_2': 4,
            'move_cost_3': 1,
            'move_cost_4': 1,
            'move_cost_5': -1,
        },
        SEA: { 
            'defence_factor': 0,
            'move_cost_0': -1,
            'move_cost_1': -1,
            'move_cost_2': -1,
            'move_cost_3': 1,
            'move_cost_4': 1,
            'move_cost_5': 1
        },
        REEF: {
            'defence_factor': 0.2,
            'move_cost_0': -1,
            'move_cost_1': -1,
            'move_cost_2': -1,
            'move_cost_3': 1,
            'move_cost_4': 3,
            'move_cost_5': 3,
        }
    }

class Frame_Timer:
    """
    用于调试的计时器
    单位是毫秒
    """
    CNT = 20 # [SET] 多少帧打印一次
    AVG = 200 # [SET] 最多多少帧计算平均值
    dict = {}
    cur = CNT
    __start_time = None
    def start_timer():
        Frame_Timer.__start_time = pygame.time.get_ticks()  # 获取当前时间戳（毫秒）
    def end_timer(timer_name='default'):
        if timer_name not in Frame_Timer.dict:
            Frame_Timer.dict[timer_name] = []
        end_time = pygame.time.get_ticks()  # 获取当前时间戳（毫秒）
        list = Frame_Timer.dict[timer_name]
        list.append(end_time - Frame_Timer.__start_time)
        if len(list) > Frame_Timer.AVG:
            Frame_Timer.dict[timer_name].pop(0)
    def print():
        if Frame_Timer.cur == 0:
            Frame_Timer.cur = Frame_Timer.CNT
            # 显示实际帧率
            print('\n\n')
            fps = frameclock.get_fps()
            print(f"FPS: {round(fps)}")
            # 打印列表平均值
            for name in Frame_Timer.dict:
                list = Frame_Timer.dict[name]
                if len(list) > 0:
                    print(f"{name}: {sum(list)/len(list):.1f}   ({len(list)})")
        else:
            Frame_Timer.cur -= 1

# endregion Game

"""Functions"""

def capital_words(string):
    return ' '.join([word.capitalize() for word in string.split()])

def draw_select_tile_rect(x, y, width=4):
    return pygame.Rect(x * TILE_SIZE + SCREEN_MARGIN-width//2, y * TILE_SIZE + SCREEN_MARGIN-width//2, TILE_SIZE+width, TILE_SIZE+width)

"""Preload"""

preload_unit_imgs = {}
for png in os.listdir('assets/unit'):
    if png.endswith('.png'):
        preload_unit_imgs[png] = pygame.image.load(f'assets/unit/{png}')

preload_terrain_imgs = {}
for png in os.listdir('assets/terrain'):
    if png.endswith('.png'):
        preload_terrain_imgs[png] = pygame.image.load(f'assets/terrain/{png}')
