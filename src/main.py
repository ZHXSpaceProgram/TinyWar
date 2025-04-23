from pygame.locals import *
from random import randint
from const import *
from game import *
import pygame
import ctypes
import sys
import os

# region Initialization ------------------------------------------------  Initialization ------------------

pygame.init()

# 创建无边框全屏窗口
screen = pygame.display.set_mode((0, 0), pygame.NOFRAME)
display_info = pygame.display.Info()
window_width, window_height = display_info.current_w, display_info.current_h

# 创建实际用于游戏逻辑的画布 surface，尺寸为固定的 SCREEN_WIDTH/SCREEN_HEIGHT
game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("TinyWar")

# 自动切换英文输入法
try:
    original_hkl = ctypes.windll.user32.GetKeyboardLayout(0)
    KLF_SETFORPROCESS = 0x100
    HKL_EN_US = 0x04090409
    _ = ctypes.windll.user32.ActivateKeyboardLayout(HKL_EN_US, KLF_SETFORPROCESS)
except: pass

"""Global Variables"""

is_debug = len(sys.argv) > 1 and sys.argv[1] == 'debug'

gm: GameManager = None
frameclock = pygame.time.Clock()
cur_state = GameState.PLAYING if is_debug else GameState.MENU
bgm_list = os.listdir('assets/sound/bgm')
bgm_index = randint(0, len(bgm_list) - 1)

# UI
info_string: list = list(DEFAULT_INFO_STRING)
overlay = None
hint_counter = 0

# Shop
shop: Shop = None
shop_last_ope_item = None # 检查鼠标所在的物品有没有变化
shop_open_delay_counter = 0

# 边框起始位置
start_x = (window_width - SCREEN_WIDTH) // 2
start_y = (window_height - SCREEN_HEIGHT) // 2
winners = None

# 右键预览
right_click_view_bool = False
right_click_view_coordinates = None
right_click_remove_counter = 0

# 鼠标拖动
is_dragging = False
drag_start_pos = None
drag_start_map_pos = None

# 音乐
pygame.mixer.init()
pygame.mixer.music.set_volume(0.05)

# 搜索可用关卡
available_levels = []
for file in os.listdir("assets/map"):
    if file.startswith("map") and file.endswith(".txt"):
        level_str = file[3:-4]  # 提取关卡数字
        if os.path.exists(f"assets/map/unit{level_str}.txt"):
            available_levels.append(level_str)


"""
------------  Functions  -------------------------------------------------------  Functions  --------------
"""

def show_help_string():
    global info_string
    for i in range(0, len(HELP_STRING), 2):
        if info_string == HELP_STRING[i:i+2]:
            info_string = HELP_STRING[i+2:i+4] if i + 2 < len(HELP_STRING) else list(DEFAULT_INFO_STRING)
            break
    else:
        info_string = HELP_STRING[0:2]

"""str should be in HINTS"""
def show_hint(str, time=HINT_COUNTER_DEF):
    global info_string, hint_counter
    if str in HINTS.__dict__.values():
        info_string = [str, '']
        if time != -1:
            hint_counter = time


def play_bgm():
    global bgm_index
    if not pygame.mixer.music.get_busy():
        try:
            pygame.mixer.music.load(f'assets/sound/bgm/{bgm_list[bgm_index]}')
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error loading BGM: {e}")
        bgm_index += 1
        if bgm_index >= len(bgm_list):
            bgm_index = 0

def selected_is_shop():
    selected = gm.selected_unit
    return selected and isinstance(selected, Build) \
        and selected.player_id == gm.cur_player_id and selected.shop_type!=0

def select_and_interact(grid_x, grid_y):
    """
    - 调用GameManager的select_unit方法尝试选择单位
    - 如果成功,检查是否打开交互（如商店）
    - 返回选择是否成功
    """
    global shop, shop_open_delay_counter, info_string
    if gm.select_unit(grid_x, grid_y):
        if selected_is_shop():
            shop = Shop(gm.selected_unit)
            shop_open_delay_counter = SHOP_OPEN_DELAY_COUNTER_DEF
            info_string = ['','']
        return True
    else:
        return False

def quit_game():
    try:
        ctypes.windll.user32.ActivateKeyboardLayout(original_hkl, KLF_SETFORPROCESS)
    except: pass
    finally:
        pygame.quit()
        sys.exit()

"""
-----------  Classes  -------------------------------------------------------  Classes  -----------------
"""


class Typing:
    """abstrct class, no instance"""
    typed_string = None # None 表示未处于输入状态，空字符串表示刚开始输入
    cur_state: str = None # 目前在输入的字段
    StateDict = {
        'level': {
            'info_string': ('Please type the number of map:', f"{', '.join(sorted(available_levels))}"),
            'enter_func': lambda: Typing._typing_level_enter_func()
        }, 
        'ai': {
            'info_string': ('Do you want to play with AI?', '[Y/N]'),
            'enter_func': lambda: Typing._typing_ai_enter_func()
        }
    }

    def is_typing():
        return Typing.typed_string != None

    def enter_typing(state):
        global info_string
        info_string = list(Typing.StateDict[state]['info_string'])
        Typing.cur_state = state
        Typing.typed_string = ''

    def exit_typing():
        global info_string
        info_string = list(DEFAULT_INFO_STRING)
        Typing.typed_string = None
        Typing.cur_state = None
    def handle_event(event):
        global info_string
        if event.type == KEYDOWN:
            # 输入字符
            if event.unicode.isalnum() or event.unicode in '_':
                if Typing.typed_string:
                    Typing.typed_string += event.unicode
                else:
                    Typing.typed_string = event.unicode
                info_string[0] = Typing.typed_string + '  '*(7-len(Typing.typed_string)) + \
                    ' ([Enter] to confirm, [Backspace|Right Click] to exit)'
            # 退格键退出
            elif event.key == K_BACKSPACE:
                Typing.exit_typing()
            # 回车键确认
            elif event.key == K_RETURN and Typing.typed_string:
                Typing.StateDict[Typing.cur_state]['enter_func']()
        elif event.type == MOUSEBUTTONDOWN:
            # 右键退出
            if event.button == 3:
                Typing.exit_typing()
    
    def _typing_level_enter_func():
        global gm
        if Typing.typed_string in available_levels:
            try:
                gm = GameManager(Typing.typed_string)
                # show_hint(HINTS.LOAD)
                Typing.enter_typing('ai')
            except Exception as e:
                print(f"Error loading level: {e}")
                show_hint(HINTS.FILE_ERROR)
                Typing.typed_string = None
        else:
            show_hint(HINTS.INVALID_LEVEL)
            Typing.typed_string = None
    
    def _typing_ai_enter_func():
        global gm
        if Typing.typed_string.lower() == 'y':
            gm.ai_enabled = True
            show_hint(HINTS.LOAD)
            Typing.typed_string = None
        elif Typing.typed_string.lower() == 'n':
            show_hint(HINTS.LOAD)
            Typing.typed_string = None
        else:
            show_hint(HINTS.INVALID_YN)
            Typing.typed_string = None

try:
    gm = GameManager.load()
    show_hint(HINTS.LOAD)
except:
    gm = GameManager()

# endregion Initialization

# region Main Loop ------------------------------------------------------  MainLoop ------------------
while True:
    # 播放背景音乐
    play_bgm()
    
    # region Handling Events -------------------------------------------  Handling Events ----------------
    for event in pygame.event.get():
        if event.type == QUIT:
            quit_game()
        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                quit_game()
        if cur_state == GameState.MENU:
            if event.type == KEYDOWN or event.type == MOUSEBUTTONDOWN:
                cur_state = GameState.PLAYING
                pygame.time.delay(200)
        elif cur_state == GameState.PLAYING:
            # 如果处于输入关卡状态
            if Typing.is_typing():
                Typing.handle_event(event)
                continue
            if event.type == KEYDOWN:
                # WSAD移动地图
                if gm.map.height > MAP_VIEW_SIZE:
                    if event.key == K_w:
                        gm.map_y = max(0, gm.map_y - 4)
                    elif event.key == K_s:
                        gm.map_y = min(gm.map.height - MAP_VIEW_SIZE, gm.map_y + 4)
                if gm.map.width > MAP_VIEW_SIZE:
                    if event.key == K_a:
                        gm.map_x = max(0, gm.map_x - 4)
                    elif event.key == K_d:
                        gm.map_x = min(gm.map.width - MAP_VIEW_SIZE, gm.map_x + 4)
                if event.key == K_SPACE:
                    gm.next_turn()
                elif event.key == K_h:
                    show_help_string()
                elif event.key == K_F5:
                    gm.save()
                    show_hint(HINTS.SAVE)
                elif event.key == K_F9:
                    try:
                        gm = GameManager.load()
                        show_hint(HINTS.LOAD)
                    except FileNotFoundError:
                        print("Game save not found.")
                        show_hint(HINTS.NO_FILE)
                elif event.key == K_F1:
                    Typing.enter_typing('level')
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                grid_x, grid_y = (mouse_x - start_x - SCREEN_MARGIN) // TILE_SIZE, (mouse_y - start_y - SCREEN_MARGIN) // TILE_SIZE
                # 如果在地图显示范围内
                if 0 <= grid_x < MAP_VIEW_SIZE and 0 <= grid_y < MAP_VIEW_SIZE:
                    grid_x += gm.map_x
                    grid_y += gm.map_y
                    # 左键
                    if event.button == 1:
                        selected = gm.selected_unit
                        # 选择了我方单位
                        if selected and selected.player_id == gm.cur_player_id:
                            res1, res2 = False, False
                            # 尝试移动
                            if not selected.moved and selected.movement > 0:
                                res1 = gm.move_selected_unit(grid_x, grid_y)
                            # 尝试攻击
                            if not selected.attacked and selected.attack_range[1] > 0:
                                res2 = gm.attack(grid_x, grid_y)
                                if gm.selected_unit.attacked:
                                    winners = gm.check_game_over()
                                    if winners:
                                        cur_state = GameState.GAME_OVER
                            # 如果两个函数都没有要求保持选中状态，就取消选择
                            if not res1 and not res2:
                                gm.deselect()
                                # 如果攻击失败，并且点击了不同的地块，尝试选择新的单位（支持连点选择）
                                if not selected.attacked and (grid_x != selected.x or grid_y != selected.y):  
                                    select_and_interact(grid_x, grid_y)
                        # 选择了敌方单位
                        elif gm.selected_unit:
                            # 如果点击了不同的地块，尝试选择新的单位（支持连点选择）
                            if grid_x != gm.selected_unit.x or grid_y != gm.selected_unit.y:
                                gm.deselect()
                                select_and_interact(grid_x, grid_y)
                            # 如果再次点击相同的单位，取消选择
                            else: gm.deselect()
                        # 没有选中单位
                        elif not select_and_interact(grid_x, grid_y):  # 如果选择失败，尝试拖动地图（点击空地拖动地图）
                            is_dragging = True
                            drag_start_pos = (mouse_x, mouse_y)
                            drag_start_map_pos = (gm.map_x, gm.map_y)
                    # 右键
                    elif event.button == 3:
                        # 显示原地的可能攻击位置
                        gm.select_unit(grid_x, grid_y, True)
                        right_click_view_coordinates = (grid_x, grid_y)
                        right_click_view_bool = True
                if event.button == 2:
                    gm.next_turn()
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    is_dragging = False
                elif event.button == 3:
                    right_click_remove_counter = RIGHT_VIEW_REMOVE_COUNTER_DEF
            elif event.type == pygame.MOUSEMOTION:
                if is_dragging:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    dx = (drag_start_pos[0] - mouse_x) // TILE_SIZE
                    dy = (drag_start_pos[1] - mouse_y) // TILE_SIZE
                    # 计算新的地图位置
                    new_map_x = drag_start_map_pos[0] + dx
                    new_map_y = drag_start_map_pos[1] + dy
                    # 确保地图位置在有效范围内
                    if gm.map.width > MAP_VIEW_SIZE:
                        gm.map_x = max(0, min(gm.map.width - MAP_VIEW_SIZE, new_map_x))
                    if gm.map.height > MAP_VIEW_SIZE:
                        gm.map_y = max(0, min(gm.map.height - MAP_VIEW_SIZE, new_map_y))
                elif right_click_view_bool:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    grid_x, grid_y = (mouse_x - start_x - SCREEN_MARGIN) // TILE_SIZE, (mouse_y - start_y - SCREEN_MARGIN) // TILE_SIZE
                    # 如果在地图显示范围内
                    if 0 <= grid_x < MAP_VIEW_SIZE and 0 <= grid_y < MAP_VIEW_SIZE:
                        grid_x += gm.map_x
                        grid_y += gm.map_y
                        right_click_view_coordinates = (grid_x, grid_y)
        elif cur_state == GameState.GAME_OVER:
            if event.type == KEYDOWN or event.type == MOUSEBUTTONDOWN:
                cur_state = GameState.PLAYING
                pygame.time.delay(200)
        elif cur_state == GameState.SHOP:
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    item = shop.get_item(event.pos[0]-start_x, event.pos[1]-start_y)
                    if item:
                        res = gm.buy_item(item, shop.x, shop.y)
                        shop.build.attacked = True
                        if res:
                            shop = None
                            cur_state = GameState.PLAYING
                        else:
                            info_string = [f'No enough money to buy {item}.', '']
                            shop_last_ope_item = item
                elif event.button == 3:
                    shop = None
                    info_string = list(DEFAULT_INFO_STRING)
                    cur_state = GameState.PLAYING
            # 鼠标悬停
            elif event.type == MOUSEMOTION:
                item = shop.get_item(event.pos[0]-start_x, event.pos[1]-start_y)
                if item:
                    if shop_last_ope_item != item:
                        # item 字符串中的单词首字母大写
                        info_string = [capital_words(item), '']
                        if item in Unit.PROPERTIES:
                            info_string[1] = f"{Unit.PROPERTIES[item]['description']}"
                else:
                    info_string[0] = SHOP_DEFAULT_STRING[0].format(type = capital_words(shop.build.type))
                    info_string[1] = SHOP_DEFAULT_STRING[1]
                shop_last_ope_item = item

    # endregion Handling Events

    # region Rendering -------------------------------------------------  Rendering ----------------

    if cur_state == GameState.MENU:
        cover_img = pygame.image.load("assets/cover.png")
        cover_img = pygame.transform.scale(cover_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        game_surface.blit(cover_img, (0, 0))
    elif cur_state == GameState.PLAYING:
        game_surface.fill((20, 20, 20))
        # 绘制地图
        gm.map.draw(game_surface, gm.map_x, gm.map_y)
        # 绘制单位
        for player in gm.players:
            for build in player.builds:
                # 更新重叠状态
                if build.stackable:
                    build.build_stacked = False
                    for unit in player.units:
                        if unit.x == build.x and unit.y == build.y:
                            build.build_stacked = True
                build.draw(game_surface, gm.map_x, gm.map_y)
            for unit in player.units:
                unit.draw(game_surface, gm.map_x, gm.map_y)
        for unit in gm.neutral_player.builds:
            unit.draw(game_surface, gm.map_x, gm.map_y)
        # 绘制和选择相关的内容
        if gm.selected_unit:
            selected = gm.selected_unit
            # 绘制可能的移动位置
            if not selected.moved or selected.player_id != gm.cur_player_id:
                if selected.movement and not right_click_view_bool:
                    for (x, y) in gm.possible_moves:
                        x-= gm.map_x
                        y-= gm.map_y
                        if x<0 or x>=MAP_VIEW_SIZE or y<0 or y>=MAP_VIEW_SIZE:
                            continue
                        move_rect = draw_select_tile_rect(x, y, 4)
                        pygame.draw.rect(game_surface, GREEN, move_rect, 4)
            # 绘制右键预览攻击范围
            if right_click_view_bool:
                if selected.attack_range[1] > 0: 
                    x0 = right_click_view_coordinates[0] - gm.map_x
                    y0 = right_click_view_coordinates[1] - gm.map_y
                    # 绘制原点
                    if right_click_view_coordinates in gm.possible_moves:
                        pygame.draw.circle(game_surface, GREEN, 
                        (x0*TILE_SIZE+SCREEN_MARGIN+TILE_SIZE//2, y0*TILE_SIZE+SCREEN_MARGIN+TILE_SIZE//2), 3)
                    else:
                        pygame.draw.circle(game_surface, GREY,
                        (x0*TILE_SIZE+SCREEN_MARGIN+TILE_SIZE//2, y0*TILE_SIZE+SCREEN_MARGIN+TILE_SIZE//2), 3)
                    # 绘制敌人攻击范围预警
                    warn_list = gm.get_warning_list(right_click_view_coordinates)
                    warn_list = [(a-gm.map_x, b-gm.map_y) for a, b in warn_list]
                    for pair in warn_list:
                        if 0 <= pair[0] < MAP_VIEW_SIZE and 0 <= pair[1] < MAP_VIEW_SIZE:
                            # 绘制感叹号
                            center_x = pair[0]*TILE_SIZE+SCREEN_MARGIN+TILE_SIZE//2
                            center_y = pair[1]*TILE_SIZE+SCREEN_MARGIN+TILE_SIZE//2
                            # 绘制圆点（感叹号底部）
                            pygame.draw.circle(game_surface, RED, (center_x, center_y+5), 2)
                            # 绘制线段（感叹号上部）
                            pygame.draw.line(game_surface, RED, (center_x, center_y-8), (center_x, center_y), 3)
                    for dy in range(-gm.selected_unit.attack_range[1], gm.selected_unit.attack_range[1] + 1):
                        for dx in range(-gm.selected_unit.attack_range[1], gm.selected_unit.attack_range[1] + 1):
                            manhattan_distance = abs(dx) + abs(dy)
                            if manhattan_distance < gm.selected_unit.attack_range[0] or manhattan_distance > gm.selected_unit.attack_range[1]:
                                continue
                            x = x0 + dx
                            y = y0 + dy
                            if x < 0 or x >= MAP_VIEW_SIZE or y < 0 or y >= MAP_VIEW_SIZE or (x, y) in warn_list:
                                continue
                            pygame.draw.circle(game_surface, RED, (x*TILE_SIZE+SCREEN_MARGIN+TILE_SIZE//2, y*TILE_SIZE+SCREEN_MARGIN+TILE_SIZE//2), 3)
                        
            # 绘制可能的攻击位置
            if not gm.selected_unit.attacked or gm.selected_unit.player_id != gm.cur_player_id:
                if selected.attack_range[1] > 0:
                    drawn = set() # 优先绘制当前位置可以攻击的目标
                    for pair in gm.possible_attacks:
                        x, y = pair[1]
                        x -= gm.map_x
                        y -= gm.map_y
                        if x < 0 or x >= MAP_VIEW_SIZE or y < 0 or y >= MAP_VIEW_SIZE:
                            continue
                        attack_rect = draw_select_tile_rect(x, y, 2)
                        if pair[1] in drawn:
                            continue
                        if not right_click_view_bool and pair[0] == (gm.selected_unit.x, gm.selected_unit.y) or \
                            right_click_view_bool and pair[0] == right_click_view_coordinates:
                            pygame.draw.rect(game_surface, PINK, attack_rect, 4)
                            drawn.add(pair[1]) # 优先级
                        else:
                            pygame.draw.rect(game_surface, LIGHT_PINK, attack_rect, 4)
                            
            # 绘制选中单位边框
            x = gm.selected_unit.x - gm.map_x
            y = gm.selected_unit.y - gm.map_y
            if 0 <= x < MAP_VIEW_SIZE and 0 <= y < MAP_VIEW_SIZE:
                select_rect = draw_select_tile_rect(x, y, 0)
                if right_click_view_bool:
                    pygame.draw.rect(game_surface, WHITE, select_rect, 1)
                else:
                    pygame.draw.rect(game_surface, YELLOW, select_rect, 3)
        # 绘制特效
        for effect in gm.effects:
            if not effect.update():
                gm.effects.remove(effect)
            effect.draw(game_surface, gm.map_x, gm.map_y)

        # 绘制UI信息
        font = pygame.font.SysFont('Calibri', 20, True)
        turn_text = font.render(f"Turn {gm.turn:<3} {gm.players[gm.cur_player_id].name:<4}", True, WHITE)
        game_surface.blit(turn_text, (20, 18))

        # 绘制多行文本, 在右边
        multiline_string = [f'Map {gm.level}']
        for player in gm.players:
            multiline_string.append('')
            multiline_string.append(f"— Player {player.name:<4} — <" if player.id == gm.cur_player_id else
                                    f"— Player {player.name:<4} —")
            multiline_string.append(f"Money: {player.money}")
        font = pygame.font.SysFont('Calibri', 20)
        for i, line in enumerate(multiline_string):
            text = font.render(line, True, WHITE)
            game_surface.blit(text, (SCREEN_WIDTH - 250, SCREEN_MARGIN + i * 25))

        # 底部info
        if info_string[0] and info_string[0][-1]=='!':
            font = pygame.font.SysFont('Calibri', 20, True)
        info_text = [font.render(i, True, WHITE) for i in info_string]
        game_surface.blit(info_text[0], (20, SCREEN_HEIGHT - 63))
        game_surface.blit(info_text[1], (20, SCREEN_HEIGHT - 38))
    elif cur_state == GameState.GAME_OVER:
        # 半透明遮罩
        if not overlay:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(92)
            game_surface.blit(overlay, (0, 0))
        # 文字
        font = pygame.font.SysFont(None, 72)
        win_text = ', '.join([PlayerNameDict[winner] for winner in winners])
        info_string = [win_text+" won!", '']
        win_text += f" Win{'s' if len(winners)== 1 else ''}!"
        game_over_text = font.render(win_text, True, RED if 0 in winners else BLUE)
        game_surface.blit(game_over_text, (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2,
                                           SCREEN_HEIGHT // 2 - font.get_height() // 2))
    elif cur_state == GameState.SHOP:
        game_surface.fill((20, 20, 20))
        shop.draw(game_surface, gm.cur_player().money)
        font = pygame.font.SysFont('Calibri', 20)
        font_b = pygame.font.SysFont('Calibri', 20, True)
        font_b_l = pygame.font.SysFont('Calibri', 24, True)
        # 底部info
        info_text1 = font.render(info_string[1], True, WHITE)
        if len(info_string[0]) < 23: # 不是提示信息就加粗
            info_text0 = font_b.render(info_string[0], True, WHITE)
        else:
            info_text0 = font.render(info_string[0], True, WHITE)
        game_surface.blit(info_text0, (SHOP_MARGIN, SCREEN_HEIGHT - SHOP_MARGIN - 25))
        game_surface.blit(info_text1, (SHOP_MARGIN, SCREEN_HEIGHT - SHOP_MARGIN))
        # Money
        usable_width = (SCREEN_WIDTH - 2 * SHOP_MARGIN - TILE_SIZE) // 10
        if len(info_string[1]) <= usable_width - 15:
            money_text1 = font.render(f"Money:", True, GREY)
            money_text2 = font_b_l.render(f"{gm.cur_player().money}", True, WHITE)
            game_surface.blit(money_text1, (SCREEN_WIDTH - TILE_SIZE - 151 - money_text2.get_width(),
                                            MONEY_Y))
            game_surface.blit(money_text2, (SCREEN_WIDTH - TILE_SIZE - 80 - money_text2.get_width(), 
                                            MONEY_Y - 3))
        # Image
        if len(info_string[1]) <= usable_width:
            if shop_last_ope_item in Unit.PROPERTIES:
                pygame.draw.rect(game_surface, (220, 220, 220), 
                    (SHOP_IMG_X, SHOP_IMG_Y, TILE_SIZE, TILE_SIZE), 0) # 背景
                unit_img = preload_unit_imgs[f'{shop_last_ope_item}_{gm.cur_player_id}.png']
                unit_img = pygame.transform.scale(unit_img, (TILE_SIZE, TILE_SIZE))
                game_surface.blit(unit_img, (SHOP_IMG_X, SHOP_IMG_Y))
            else:
                pygame.draw.rect(game_surface, (128, 128, 128), 
                    (SHOP_IMG_X, SHOP_IMG_Y, TILE_SIZE, TILE_SIZE), 0) # 背景

    # game_surface边框
    border_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
    pygame.draw.rect(game_surface, WHITE, border_rect, 1)

    # 将游戏画面绘制到全屏中心
    screen.blit(game_surface, (start_x, start_y))

    # endregion Rendering

    # Counters
    if right_click_remove_counter > 0:
        right_click_remove_counter -= 1
        if right_click_remove_counter == 0:
            right_click_view_bool = False
            right_click_view_coordinates = None
            if gm.selected_unit and gm.selected_unit.player_id != gm.cur_player_id:
                gm.deselect()
    if hint_counter > 0:
        hint_counter -= 1
        if hint_counter == 0 and info_string[0] in HINTS.__dict__.values():
            info_string = list(DEFAULT_INFO_STRING)
    if selected_is_shop():
        if shop_open_delay_counter > 0:
            shop_open_delay_counter -= 1
        else:
            cur_state = GameState.SHOP
            gm.deselect()
    else:
        shop_open_delay_counter = 0

    # if is_debug:
    #     Frame_Timer.print()

    pygame.display.flip()
    frameclock.tick(FPS)

# endregion Main Loop