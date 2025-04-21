from const import *
from units import Unit, Build
import pygame
import random
import math
import pickle

class GameMap:
    # 从文件中读取地形信息
    def __init__(self, file):
        # 注意：terrain[y][x] 先行后列
        self.terrain = []
        with open(file, 'r') as f:
            for line in f:
                self.terrain.append([Terrain.CHAR_MAP[c] for c in line.strip().split('\t')])
        self.width = len(self.terrain[0])
        self.height = len(self.terrain)

    def draw(self, screen, map_x , map_y):
        for y in range(max(map_y, 0), min(map_y + MAP_VIEW_SIZE, self.height)):
            for x in range(max(map_x, 0), min(map_x + MAP_VIEW_SIZE, self.width)):
                rect = pygame.Rect(
                    (x-map_x) * TILE_SIZE+SCREEN_MARGIN, (y-map_y) * TILE_SIZE+SCREEN_MARGIN, 
                    TILE_SIZE, TILE_SIZE
                    )
                # 绘制地形
                terrain = self.terrain[y][x]
                # terrain_img = pygame.image.load(f"assets/terrain/{terrain}.png")
                terrain_img = preload_terrain_imgs[f"{terrain}.png"]
                terrain_img = pygame.transform.scale(terrain_img, (TILE_SIZE, TILE_SIZE))
                # 道路旋转
                if terrain == Terrain.ROAD:
                    h = (x > 0 and self.terrain[y][x-1] == Terrain.ROAD) or \
                        (x < self.width-1 and self.terrain[y][x+1] == Terrain.ROAD)
                    v = (y > 0 and self.terrain[y-1][x] == Terrain.ROAD) or \
                        (y < self.height-1 and self.terrain[y+1][x] == Terrain.ROAD)
                    if not h and v:
                        terrain_img = pygame.transform.rotate(terrain_img, 90)
                screen.blit(terrain_img, rect.topleft)
                # 绘制网格线
                pygame.draw.rect(screen, (20, 20, 20), rect, 1)
            # end for x
        # end for y

        # 显示可移动距离指示
        font = pygame.font.SysFont(None, 20)
        # 上方距离指示（可向上移动的格子数）
        up_distance = (map_y+3) // 4
        if up_distance > 0:
            up_text = font.render('^', True, WHITE)
            screen.blit(up_text, (SCREEN_MARGIN + TILE_SIZE*MAP_VIEW_SIZE//2 - up_text.get_width()//2, SCREEN_MARGIN // 2 - up_text.get_height()//2))
        # 下方距离指示（可向下移动的格子数）
        down_distance = (self.height - (map_y + MAP_VIEW_SIZE)+3) // 4
        if down_distance > 0:
            down_text = font.render('v', True, WHITE)
            screen.blit(down_text, (SCREEN_MARGIN + TILE_SIZE*MAP_VIEW_SIZE//2 - down_text.get_width()//2, SCREEN_MARGIN + MAP_VIEW_SIZE * TILE_SIZE + SCREEN_MARGIN // 2 - down_text.get_height()//2))
        # 左侧距离指示（可向左移动的格子数）
        left_distance = (map_x+3) // 4
        if left_distance > 0:
            left_text = font.render('<', True, WHITE)
            screen.blit(left_text, (SCREEN_MARGIN // 2 - left_text.get_width()//2, SCREEN_MARGIN + TILE_SIZE*MAP_VIEW_SIZE//2 - left_text.get_height()//2))
        # 右侧距离指示（可向右移动的格子数）
        right_distance = (self.width - (map_x + MAP_VIEW_SIZE)+3) // 4
        if right_distance > 0:
            right_text = font.render('>', True, WHITE)
            screen.blit(right_text, (SCREEN_MARGIN + MAP_VIEW_SIZE * TILE_SIZE + SCREEN_MARGIN // 2 - right_text.get_width()//2, SCREEN_MARGIN + TILE_SIZE*MAP_VIEW_SIZE//2 - right_text.get_height()//2))


class Player:
    def __init__(self, id):
        self.id = id
        if id == -1:
            self.name = 'Neutral'
        else:
            self.name = PlayerNameDict[id]
        self.units = [] # 不包含 Build
        self.builds = []
        self.money = 50
    
    
    def add_unit(self, x, y, unit_type, tired=False):
        new_unit = Unit(x, y, unit_type, self.id)
        if tired:
            new_unit.moved = True
            new_unit.attacked = True
        self.units.append(new_unit)
        return new_unit
    
    def add_build(self, x, y, build_type):
        new_build = Build(x, y, build_type, self.id)
        self.builds.append(new_build)
        return new_build
        
    def reset_units(self, fresh_for_display=False):
        for unit in self.units:
            if fresh_for_display:
                unit.attacked = True
            else:
                unit.moved = False
                unit.attacked = False
        for build in self.builds:
            if fresh_for_display:
                build.attacked = True
            else:
                build.attacked = False
    
    def buy_item(self, item, x, y) -> bool:
        if item in Unit.PROPERTIES.keys():
            if self.money < Unit.PROPERTIES[item]['price']:
                return False
            self.add_unit(x, y, item, True)
            self.money -= Unit.PROPERTIES[item]['price']
            return True
        else:
            print(f"{item} not found in shop.")
            return False


class GameManager:
    def __init__(self, level=1):
        self.level = level
        self.map = GameMap(f"assets/map/map{level}.txt")
        self._init_view() 
        self.players = [Player(0), Player(1)]
        self.neutral_player = Player(-1)
        self.cur_player_id = 0
        self.turn = 1
        self.selected_unit: Unit = None
        self.possible_moves = set()
        self.possible_attacks = []
        self.read_units(f"assets/map/unit{level}.txt")
        for i, player in enumerate(self.players):
            if i != self.cur_player_id:
                player.reset_units(True)
        self.effects = []

    def _init_view(self):
        # 初始化地图位置（大地图左侧，小地图居中）
        if self.map.width < MAP_VIEW_SIZE: 
            self.map_x = self.map.width // 2 - MAP_VIEW_SIZE // 2
        else:
            self.map_x = 0
        self.map_y = self.map.height // 2 - MAP_VIEW_SIZE // 2  
    def cur_player(self) -> Player:
        """返回当前玩家"""
        return self.players[self.cur_player_id]

    def read_units(self, file):
        """从文件中读取单位信息"""
        with open(file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): # 跳过注释行和空行
                    continue
                x, y, unit_type, player_id = line.split()
                x, y, player_id = int(x), int(y), int(player_id)
                if player_id != -1:
                    if unit_type in Unit.PROPERTIES:
                        self.players[player_id].add_unit(x, y, unit_type)
                    elif unit_type in Build.PROPERTIES:
                        self.players[player_id].add_build(x, y, unit_type)
                else:
                    self.neutral_player.add_build(x, y, unit_type)

    def save(self, filename='savegame.pkl'):
        """Serialize this GameManager (and all its maps/units/players) to disk."""
        with open(filename, 'wb') as f:
            pickle.dump(self, f)
        print(f"[Saved] Game state written to {filename}")

    @classmethod
    def load(cls, filename='savegame.pkl'):
        """Load a GameManager instance from disk (returns the loaded object)."""
        with open(filename, 'rb') as f:
            gm = pickle.load(f)
        gm._init_view()
        print(f"[Loaded] Game state read from {filename}")
        return gm
    
    def next_turn(self):
        self.players[self.cur_player_id].reset_units(True)
        self.cur_player_id = (self.cur_player_id + 1) % len(self.players)
        if self.cur_player_id == 0:
            self.turn += 1
        self.players[self.cur_player_id].reset_units()
        self.deselect()

    def select_unit(self, x, y, right_click=False):
        """根据坐标判断能否选中，如果可以就执行（优先选择单位）"""
        for player in self.players:
            for unit in player.units:
                if unit.x == x and unit.y == y:
                    self.selected_unit = unit
                    # 远程兵种（最小范围大于1）移动后不能攻击
                    self.calculate_possible_moves(right_click or unit.moved, unit.attack_range[0]>1)
                    print(f"DEBUG {unit.x=}, {unit.y=}, {unit.attacked=}, {unit.moved=}, {unit.type=}, {unit.health=}")
                    return True
            for build in player.builds:
                if build.x == x and build.y == y:
                    self.selected_unit = build
                    if build.attack_range[1] > 0:
                        self.calculate_possible_moves(True, True)
                    return True
        return False
    
    def move_selected_unit(self, x, y):
        """根据坐标判断能否移动，如果可以就执行"""
        if (x, y) in self.possible_moves:
            self.selected_unit.x = x
            self.selected_unit.y = y
            self.selected_unit.moved = True

            play_sound(f"assets/sound/effect/move_{self.selected_unit.move_type}_{random.randint(0, 1)}.mp3")

            # 从possible_attacks中检查是否有从当前位置的攻击
            for pair in self.possible_attacks:
                if pair[0] == (x, y):
                    if self.selected_unit.attack_range[0] > 1:
                        self.selected_unit.attacked = True # 远程兵种（最大范围大于1）移动后不能攻击
                    return True
            self.selected_unit.attacked = True # 如果移动后无法攻击，直接把attacked设置为True，表示无法选中
        return False

    def _can_attack(self, source, target, skip_dist=None):
        # 计算距离
        if not skip_dist:
            manhattan_dist = abs(source.x - target.x) + abs(source.y - target.y)
            if manhattan_dist < source.attack_range[0] or manhattan_dist > source.attack_range[1]:
                return False
        # 如果目标是建筑
        if isinstance(target, Build):
            if target.build_stacked:  # 不能攻击被堆叠的建筑
                return False
            elif source.move_type == MoveType.Feet:  #占领建筑时不能移动
                if abs(source.x - target.x) + abs(source.y - target.y) > 1:
                    return False
        # 如果是单位
        else:
            # 陆地单位在水上不能攻击
            if source.move_type < 3:
                if self.map.terrain[source.y][source.x] == Terrain.WATER:
                    return False
            # 防空
            if target.move_type == MoveType.Air and not hasattr(source, 'anti_air'):
                return False
            # 反潜
            if target.move_type == MoveType.Sub and not hasattr(source, 'anti_sub'):
                return False
        return True

    def unit_death(self, target: Unit):
        self.effects.append(Effect(target.x, target.y, EffectType.Death))
        if target.player_id == -1:
            self.neutral_player.builds.remove(target)
        elif isinstance(target, Build):
            self.players[target.player_id].builds.remove(target)
        else:
            self.players[target.player_id].units.remove(target)

    """根据坐标判断能否攻击，如果可以就执行"""
    def attack(self, x, y):
        for pair in self.possible_attacks:
            # 移动和攻击分两步，不支持一步到位
            if pair[1] == (x, y) and pair[0] == (self.selected_unit.x, self.selected_unit.y):

                play_sound(f"assets/sound/effect/attack_{random.randint(0, 2)}.mp3")

                source: Unit = self.selected_unit
                source.moved = True # 攻击后不能再移动
                source.attacked = True
                target: Unit = pair[2]
                # 占领
                if isinstance(target, Build) and target.capturable and\
                    source.move_type == MoveType.Feet and target.player_id != source.player_id:
                    # 敌方建筑变成中立，中立建筑变成我方
                    if target.player_id >= 0:
                        self.neutral_player.builds.append(target)
                        self.players[target.player_id].builds.remove(target)
                        target.player_id = -1
                    else:
                        self.players[source.player_id].builds.append(target)
                        self.neutral_player.builds.remove(target)
                        target.player_id = source.player_id
                    return True
                damage = self.calculate_damage(source, target)
                target.health -= damage
                if target.health <= 0:
                    self.unit_death(target)
                else: # 反击
                    if self._can_attack(target, source):
                        damage = self.calculate_damage(target, source)
                        source.health -= damage
                        if source.health <= 0:
                            self.unit_death(target)
                return True
        return False

    def check_game_over(self):
        winners = []
        flag = False
        for i, player in enumerate(self.players):
            if len(player.units) == 0:
                flag = True
            else:
                winners.append(i)
        if flag:
            return winners
        else:
            return None

    def deselect(self):
        self.selected_unit = None
        self.possible_moves = set()
        self.possible_attacks = []

    def calculate_damage(self, source: Unit, target: Unit):
        health_percentage = math.ceil(source.health / source.max_health * 10) / 10
        luck = random.randint(0, 9) # 幸运系数
        terrain_factor = 1-Terrain.PROPERTIES[self.map.terrain[target.y][target.x]]['defence_factor']
        weapon_diff = source.weapon_type-target.armor_type
        if weapon_diff > 0:
            armor_factor = 1 + 0.0 * weapon_diff # 强打弱增益系数
        else:
            armor_factor = 1 + 0.15 * weapon_diff # 弱打强衰减系数
        global_factor = 1.0 if source.attack_range[0] > 1 else 1.1 # 全局系数，远程近程区别对待
        if not isinstance(target, Build):
        # 飞机打非空中的防空单位衰减伤害
            if source.move_type == MoveType.Air and target.move_type != MoveType.Air and hasattr(target, 'anti_air'):
                global_factor *= 0.8
            # 非海军单位打海军单位衰减伤害
            if source.move_type != MoveType.Sea and target.move_type == MoveType.Sea:
                global_factor *= 0.8
        return health_percentage * (source.attack + luck) * (terrain_factor * armor_factor) * global_factor


    """
    搜索所有可能的移动和攻击位置
    """
    def calculate_possible_moves(self, skip_move=False, attack_without_move=False):
        # self.possible_moves 里是所有可到达的点（不含起点）
        # self.possible_attacks 里是列表，元素是 ((from_x,from_y), (to_x,to_y), target_unit) 的元组
        self.possible_moves = set()
        self.possible_attacks = []

        unit = self.selected_unit
        movement = unit.movement
        attack_range = unit.attack_range

        # 1. Dijkstra 搜索最佳路径
        if not skip_move:
            queue = [(unit.x, unit.y, movement)]
            best_remain = {(unit.x, unit.y): movement}
            occupied = [
                (other.x, other.y)
                for player in self.players
                for other in player.units
            ]
            occupied += [
                (build.x, build.y)
                for player in self.players
                for build in player.builds if not build.stackable or build.player_id != unit.player_id
            ]
            occupied += [
                (build.x, build.y)
                for build in self.neutral_player.builds
            ]

            while queue:
                x, y, remain_movement = queue.pop(0)
                if remain_movement < best_remain.get((x, y), 0):
                    continue                
                # 跳过起点本身加入移动列表（但后面计算攻击时仍会把它考虑进去）
                if (x, y) != (unit.x, unit.y):
                    self.possible_moves.add((x, y))
                # 如果移动力不足，不能再扩展
                if remain_movement <= 0:
                    continue
                for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                    nx, ny = x + dx, y + dy
                    # 如果超出地图边界，跳过
                    if not (0 <= nx < self.map.width and 0 <= ny < self.map.height):
                        continue
                    # 如果已被占用，跳过
                    if (nx, ny) in occupied:
                        continue
                    cost = Terrain.PROPERTIES[self.map.terrain[ny][nx]][f'move_cost_{unit.move_type}']
                    if cost < 0:
                        continue  # 无法通行
                    # print(f"DEBUG: {nx=}, {ny=}, {cost=}, {remain_movement=}")
                    new_remain = remain_movement - cost
                    if new_remain > best_remain.get((nx, ny), -0.1): # 调整这个值让最后一步可以欠费
                        best_remain[(nx, ny)] = new_remain
                        queue.append((nx, ny, new_remain))

        # 把起始位置也当作“移动”点，允许原地攻击
        all_moves: set = {(unit.x, unit.y)} if attack_without_move else {(unit.x, unit.y)} | self.possible_moves

        # 2. 对每个移动点，计算所有满足曼哈顿距离的攻击目标
        for (mx, my) in all_moves:
            # 在攻击范围内的所有相对偏移
            min_range, max_range = attack_range
            for dx in range(-max_range, max_range + 1):
                for dy in range(-max_range, max_range + 1):
                    manhattan_dist = abs(dx) + abs(dy)
                    # 检查是否在最小和最大攻击范围之间
                    if manhattan_dist < min_range or manhattan_dist > max_range:
                        continue
                    tx, ty = mx + dx, my + dy
                    # 检查是否在地图边界内
                    if not (0 <= tx < self.map.width and 0 <= ty < self.map.height):
                        continue
                    # 如果该格有敌方单位，则记录一次"从 mx,my 攻击 tx,ty"
                    for i, player in enumerate(self.players + [self.neutral_player]):
                        if i == unit.player_id:
                            continue
                        for enemy in (player.units+player.builds):  # 优先选择单位作为目标
                            if (enemy.x, enemy.y) == (tx, ty) and self._can_attack(unit, enemy, True):
                                # 记录格式：((移动点x, 移动点y), (目标点x, 目标点y), 目标单位)
                                pair = ((mx, my), (tx, ty), enemy)
                                if pair not in self.possible_attacks:
                                    self.possible_attacks.append(pair)
                                break
                    # [END] for i, player
                # [END] for dy
            # [END] for dx
        # [END] for mx, my


class Effect:
    def __init__(self, x, y, type, duration=10):
        self.x = x
        self.y = y
        self.type = type
        self.duration = duration

    def update(self):
        self.duration -= 1
        if self.duration <= 0:
            return False  # Effect expired
        return True  # Effect still active

    def draw(self, screen, map_x, map_y):
        # 单位击杀效果
        if self.type == EffectType.Death:
            # draw a cross at the center of the tile
            x = self.x - map_x
            y = self.y - map_y
            rect = pygame.Rect(
                SCREEN_MARGIN + x * TILE_SIZE + 10,
                SCREEN_MARGIN + y * TILE_SIZE + 10,
                TILE_SIZE -20,
                TILE_SIZE -20
            )
            pygame.draw.line(screen, RED, rect.topleft, rect.bottomright, 3)
            pygame.draw.line(screen, RED, rect.topright, rect.bottomleft, 3)

class Shop:
    def __init__(self, build: Build):
        self.items = []
        self.x = build.x
        self.y = build.y
        self.shop_type = build.shop_type
        self.build = build
        self._last_got_item_ind: int = -1
        for unit in Unit.PROPERTIES.keys():
            self.items.append(unit)
        # DEBUG: Add test items
        for i in range(45 - len(self.items)):
            self.items.append(f'')
    def draw(self, screen, money):
        font = pygame.font.SysFont('Calibri', 20)  # 18
        font_b = pygame.font.SysFont('Calibri', 20, True)
        for i, item in enumerate(self.items):
            price = -1
            greyed = False
            if item in Unit.PROPERTIES:
                price = Unit.PROPERTIES[item]['price']
                if price > money:
                    greyed = True
                    text1 = font.render(capital_words(item), True, GREY)
                    text2 = font.render(f"{price}", True, GREY)
                else:
                    text1 = font.render(capital_words(item), True, WHITE)
                    text2 = font_b.render(f"{price}", True, WHITE)
            else:
                text1 = font.render(capital_words(item), True, WHITE)
            rect = pygame.Rect(
                SHOP_X_MARGIN + i // 15 * 250,
                SHOP_Y_MARGIN + i % 15 * SHOP_LINE_H,
                SHOP_LINE_W, SHOP_LINE_H
            )
            # 绘制边框和悬停背景
            pygame.draw.rect(screen, (30, 30, 30), rect, 1)
            if self._last_got_item_ind == i:
                pygame.draw.rect(screen, (60, 60, 0) if greyed else (90, 90, 0), rect, 0)
            # 绘制商品文字
            screen.blit(text1, (rect.x + 12, rect.y+SHOP_LINE_H//2-8))
            if price != -1:
                screen.blit(text2, (rect.x + 178 - text2.get_width(), rect.y+SHOP_LINE_H//2-8))

    """根据鼠标的位置，返回对应的物品"""
    def get_item(self, x, y):
        x -= SHOP_X_MARGIN
        y -= SHOP_Y_MARGIN
        if x % 250 > SHOP_LINE_W:
            self._last_got_item_ind = -1
            return None
        col = x // 250
        row = y // SHOP_LINE_H
        index = col * 15 + row
        if 0 <= row < 15:
            if 0 <= index < len(self.items):
                self._last_got_item_ind = index
                return self.items[index]
        self._last_got_item_ind = -1
        return None

        


"""Helpers"""

def play_sound(file, volume=0.5):
    try:
        sound = pygame.mixer.Sound(file)
        sound.set_volume(volume)
        sound.play()
    except Exception as e:
        print(f"Error playing sound: {e}")