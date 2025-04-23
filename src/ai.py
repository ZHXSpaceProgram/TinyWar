from const import *
import random
import math
import copy
from units import Unit, Build
from game import GameManager

class GameAI:
    def __init__(self, game_manager, player_id, search_depth=2):
        self.gm = game_manager
        self.player_id = player_id
        self.enemy_id = 1 - player_id  # 假设只有两个玩家
        self.search_depth = search_depth  # 对抗搜索的深度
        
    def make_move(self):
        """AI执行一回合的行动"""
        player = self.gm.players[self.player_id]
        
        # 1. 购买新单位（如果有工厂/机场/船厂）
        self._try_purchase_units()
        
        # 2. 为每个单位计算最佳行动
        units_to_process = player.units.copy()
        
        # 优先处理攻击型单位
        units_to_process.sort(key=lambda unit: (-unit.attack, -unit.movement))
        
        for unit in units_to_process:
            if unit.moved and unit.attacked:
                continue  # 跳过已经行动过的单位
                
            best_action = self._get_best_action_with_adversarial_search(unit)
            if best_action:
                self._execute_action(unit, best_action)
        
        # 3. 结束回合
        self.gm.next_turn()
    
    def _try_purchase_units(self):
        """尝试在可用的建筑中购买单位"""
        player = self.gm.players[self.player_id]
        
        # 获取所有可以购买单位的建筑
        factories = [build for build in player.builds 
                    if build.type in ["factory", "airport", "shipyard"]]
        
        for factory in factories:
            # 根据建筑类型确定可购买的单位类型
            available_units = []
            if factory.type == "factory":
                available_units = ["commando", "tank", "mortar"]
            elif factory.type == "airport":
                available_units = ["fighter", "bomber"]
            elif factory.type == "shipyard":
                available_units = ["destroyer", "submarine", "battleship", "cruiser"]
            
            # 按性价比排序
            available_units.sort(key=lambda unit_type: 
                                Unit.PROPERTIES[unit_type]['attack'] / 
                                Unit.PROPERTIES[unit_type]['price'])
            
            # 尝试购买最好的单位
            for unit_type in available_units:
                price = Unit.PROPERTIES[unit_type]['price']
                if player.money >= price:
                    # 检查周围是否有空位
                    for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                        nx, ny = factory.x + dx, factory.y + dy
                        if self._is_valid_position(nx, ny):
                            # 购买单位
                            player.money -= price
                            player.add_unit(nx, ny, unit_type)
                            break
                    break  # 每个建筑每回合只购买一个单位

    def _is_valid_position(self, x, y):
        """检查位置是否有效且没有被占用"""
        # 检查是否在地图范围内
        if not (0 <= x < self.gm.map.width and 0 <= y < self.gm.map.height):
            return False
            
        # 检查是否被单位占用
        for player in self.gm.players:
            for unit in player.units:
                if unit.x == x and unit.y == y:
                    return False
            for build in player.builds:
                if build.x == x and build.y == y and not build.stackable:
                    return False
                    
        # 检查中立建筑
        for build in self.gm.neutral_player.builds:
            if build.x == x and build.y == y:
                return False
                
        # 检查地形是否可通行
        terrain = self.gm.map.terrain[y][x]
        return True  # 简化版，实际应检查具体单位类型对应的地形通行性
    
    def _get_best_action_with_adversarial_search(self, unit):
        """使用对抗性搜索为单位计算最佳行动"""
        # 获取所有可能的行动
        possible_actions = self._get_all_possible_actions(unit)
        
        if not possible_actions:
            return None
            
        # 为每个行动进行对抗性搜索评分
        for action in possible_actions:
            # 创建游戏状态的深拷贝用于模拟
            game_copy = self._create_game_copy()
            
            # 在复制的游戏状态中执行当前行动
            self._simulate_action(game_copy, unit, action)
            
            # 进行对抗性搜索评分
            action['score'] = self._adversarial_search(game_copy, self.search_depth, False)
        
        # 选择得分最高的行动
        possible_actions.sort(key=lambda a: a['score'], reverse=True)
        return possible_actions[0]
    
    def _get_all_possible_actions(self, unit):
        """获取单位所有可能的行动"""
        self.gm.selected_unit = unit
        self.gm._calculate_possible_moves()
        
        possible_actions = []
        
        # 1. 收集所有可能的移动
        for move_pos in self.gm.possible_moves:
            action = {
                'type': 'move',
                'position': move_pos,
                'score': 0
            }
            possible_actions.append(action)
            
        # 2. 收集所有可能的攻击
        for attack in self.gm.possible_attacks:
            from_pos, to_pos, target = attack
            action = {
                'type': 'attack',
                'from_position': from_pos,
                'target_position': to_pos,
                'target': target,
                'score': 0
            }
            possible_actions.append(action)
        
        return possible_actions
    
    def _create_game_copy(self):
        """创建游戏状态的深拷贝"""
        # 注意：这里使用简化版的游戏状态复制，实际应用中可能需要更完整的复制
        game_copy = {
            'players': [],
            'neutral_player': None,
            'map': self.gm.map,  # 地图通常不会变化，可以直接引用
            'cur_player_id': self.gm.cur_player_id,
            'turn': self.gm.turn
        }
        
        # 复制玩家信息
        for player in self.gm.players:
            player_copy = {
                'id': player.id,
                'money': player.money,
                'units': copy.deepcopy(player.units),
                'builds': copy.deepcopy(player.builds)
            }
            game_copy['players'].append(player_copy)
        
        # 复制中立玩家信息
        game_copy['neutral_player'] = {
            'id': self.gm.neutral_player.id,
            'builds': copy.deepcopy(self.gm.neutral_player.builds)
        }
        
        return game_copy
    
    def _simulate_action(self, game_copy, unit, action):
        """在复制的游戏状态中模拟执行行动"""
        # 找到复制状态中对应的单位
        player = game_copy['players'][self.player_id]
        unit_copy = None
        for u in player['units']:
            if u.x == unit.x and u.y == unit.y:
                unit_copy = u
                break
        
        if not unit_copy:
            return  # 单位不存在，无法模拟
        
        if action['type'] == 'move':
            # 模拟移动
            unit_copy.x, unit_copy.y = action['position']
            unit_copy.moved = True
            
        elif action['type'] == 'attack':
            # 模拟攻击
            target_player_id = action['target'].player_id
            target_x, target_y = action['target_position']
            
            # 找到目标单位
            target_copy = None
            if target_player_id == -1:
                for b in game_copy['neutral_player']['builds']:
                    if b.x == target_x and b.y == target_y:
                        target_copy = b
                        break
            else:
                target_player = game_copy['players'][target_player_id]
                for u in target_player['units']:
                    if u.x == target_x and u.y == target_y:
                        target_copy = u
                        break
                if not target_copy:
                    for b in target_player['builds']:
                        if b.x == target_x and b.y == target_y:
                            target_copy = b
                            break
            
            if target_copy:
                # 模拟伤害计算
                damage = self._estimate_damage(unit_copy, target_copy)
                target_copy.health -= damage
                
                # 如果目标死亡
                if target_copy.health <= 0:
                    if target_player_id == -1:
                        game_copy['neutral_player']['builds'].remove(target_copy)
                    elif isinstance(target_copy, Build):
                        game_copy['players'][target_player_id]['builds'].remove(target_copy)
                    else:
                        game_copy['players'][target_player_id]['units'].remove(target_copy)
                else:
                    # 模拟反击
                    if self._can_counterattack(target_copy, unit_copy):
                        counter_damage = self._estimate_damage(target_copy, unit_copy)
                        unit_copy.health -= counter_damage
                        
                        # 如果自己死亡
                        if unit_copy.health <= 0:
                            player['units'].remove(unit_copy)
            
            # 标记为已攻击
            unit_copy.attacked = True
            
            # 如果有blitz特性，攻击后可以移动
            if hasattr(unit_copy, 'blitz'):
                unit_copy.moved = False
            else:
                unit_copy.moved = True
    
    def _adversarial_search(self, game_state, depth, is_maximizing):
        """
        对抗性搜索评估函数
        game_state: 游戏状态的复制
        depth: 当前搜索深度
        is_maximizing: 是否是最大化玩家(AI)的回合
        """
        # 基本情况：达到搜索深度或游戏结束
        if depth == 0 or self._is_game_over(game_state):
            return self._evaluate_state(game_state)
        
        current_player_id = self.player_id if is_maximizing else self.enemy_id
        
        if is_maximizing:
            max_eval = float('-inf')
            # 为AI的每个单位生成可能的行动
            for unit in game_state['players'][current_player_id]['units']:
                if unit.moved and unit.attacked:
                    continue
                
                possible_actions = self._generate_actions_for_unit(game_state, unit)
                
                for action in possible_actions:
                    # 创建游戏状态的副本
                    next_state = copy.deepcopy(game_state)
                    
                    # 模拟执行行动
                    self._simulate_action(next_state, unit, action)
                    
                    # 递归评估
                    eval = self._adversarial_search(next_state, depth - 1, False)
                    max_eval = max(max_eval, eval)
            
            return max_eval if max_eval != float('-inf') else self._evaluate_state(game_state)
        
        else:
            min_eval = float('inf')
            # 为敌方的每个单位生成可能的行动
            for unit in game_state['players'][current_player_id]['units']:
                if unit.moved and unit.attacked:
                    continue
                
                possible_actions = self._generate_actions_for_unit(game_state, unit)
                
                for action in possible_actions:
                    # 创建游戏状态的副本
                    next_state = copy.deepcopy(game_state)
                    
                    # 模拟执行行动
                    self._simulate_action(next_state, unit, action)
                    
                    # 递归评估
                    eval = self._adversarial_search(next_state, depth - 1, True)
                    min_eval = min(min_eval, eval)
            
            return min_eval if min_eval != float('inf') else self._evaluate_state(game_state)
    
    def _generate_actions_for_unit(self, game_state, unit):
        """为模拟状态中的单位生成可能的行动"""
        # 简化版：只考虑基本的移动和攻击
        actions = []
        
        # 生成移动行动
        for dx, dy in [(0,0), (0,1), (1,0), (0,-1), (-1,0)]:
            nx, ny = unit.x + dx, unit.y + dy
            if self._is_valid_move(game_state, unit, nx, ny):
                actions.append({
                    'type': 'move',
                    'position': (nx, ny)
                })
        
        # 生成攻击行动
        for player_id, player in enumerate(game_state['players']):
            if player_id == unit.player_id:
                continue
                
            for target in player['units'] + player['builds']:
                dist = abs(unit.x - target.x) + abs(unit.y - target.y)
                if unit.attack_range[0] <= dist <= unit.attack_range[1]:
                    actions.append({
                        'type': 'attack',
                        'from_position': (unit.x, unit.y),
                        'target_position': (target.x, target.y),
                        'target': target
                    })
        
        # 检查中立建筑
        for target in game_state['neutral_player']['builds']:
            dist = abs(unit.x - target.x) + abs(unit.y - target.y)
            if unit.attack_range[0] <= dist <= unit.attack_range[1]:
                actions.append({
                    'type': 'attack',
                    'from_position': (unit.x, unit.y),
                    'target_position': (target.x, target.y),
                    'target': target
                })
        
        return actions
    
    def _is_valid_move(self, game_state, unit, nx, ny):
        """检查在模拟状态中移动是否有效"""
        # 检查是否在地图范围内
        if not (0 <= nx < self.gm.map.width and 0 <= ny < self.gm.map.height):
            return False
            
        # 检查是否被单位占用
        for player in game_state['players']:
            for other_unit in player['units']:
                if other_unit.x == nx and other_unit.y == ny:
                    return False
            for build in player['builds']:
                if build.x == nx and build.y == ny and not build.stackable:
                    return False
                    
        # 检查中立建筑
        for build in game_state['neutral_player']['builds']:
            if build.x == nx and build.y == ny:
                return False
                
        # 检查移动距离
        dist = abs(unit.x - nx) + abs(unit.y - ny)
        if dist > unit.movement:
            return False
            
        return True
    
    def _is_game_over(self, game_state):
        """检查模拟状态中游戏是否结束"""
        # 简化版：如果任一玩家没有单位，游戏结束
        for player in game_state['players']:
            if len(player['units']) == 0:
                return True
        return False
    
    def _evaluate_state(self, game_state):
        """评估模拟状态的分数"""
        my_player = game_state['players'][self.player_id]
        enemy_player = game_state['players'][self.enemy_id]
        
        score = 0
        
        # 1. 单位数量和健康状况
        my_unit_value = sum(unit.health / unit.max_health * Unit.PROPERTIES[unit.type]['price'] 
                           for unit in my_player['units'])
        enemy_unit_value = sum(unit.health / unit.max_health * Unit.PROPERTIES[unit.type]['price'] 
                              for unit in enemy_player['units'])
        score += my_unit_value - enemy_unit_value
        
        # 2. 建筑控制
        my_build_value = sum(5 for build in my_player['builds'])
        enemy_build_value = sum(5 for build in enemy_player['builds'])
        score += (my_build_value - enemy_build_value) * 10
        
        # 3. 经济状况
        score += (my_player['money'] - enemy_player['money']) * 0.5
        
        # 4. 战略位置控制
        # 这里可以添加对关键位置控制的评估
        
        return score
    
    def _execute_action(self, unit, action):
        """执行选定的行动"""
        self.gm.selected_unit = unit
        
        if action['type'] == 'move':
            # 移动到指定位置
            self.gm.move_selected_unit(action['position'][0], action['position'][1])
            
        elif action['type'] == 'attack':
            # 如果需要先移动再攻击
            if action['from_position'] != (unit.x, unit.y):
                self.gm.move_selected_unit(action['from_position'][0], action['from_position'][1])
                
            # 攻击目标
            self.gm.attack(action['target_position'][0], action['target_position'][1])
    
    def _estimate_damage(self, source, target):
        """估算攻击造成的伤害"""
        # 简化版的伤害计算，实际应使用游戏内的公式
        health_percentage = source.health / source.max_health
        terrain_factor = 1 - Terrain.PROPERTIES[self.gm.map.terrain[target.y][target.x]]['defence_factor']
        
        weapon_diff = source.weapon_type - target.armor_type
        if weapon_diff > 0:
            armor_factor = 1 + 0.0 * weapon_diff
        else:
            armor_factor = 1 + 0.15 * weapon_diff
            
        global_factor = 1.0 if source.attack_range[0] > 1 else 1.1
        
        # 特殊单位类型的伤害修正
        if not isinstance(target, Build):
            if source.move_type == MoveType.Air and target.move_type != MoveType.Air and hasattr(target, 'anti_air'):
                global_factor *= 0.8
            if source.move_type < 3 and target.move_type == MoveType.Sea:
                global_factor *= 0.1
                
        return health_percentage * source.attack * terrain_factor * armor_factor * global_factor
    
    def _can_counterattack(self, unit, attacker):
        """检查单位是否能够反击"""
        if isinstance(unit, Build):
            return False  # 建筑不能反击
            
        if unit.attack_range[1] < 1:
            return False  # 无法攻击的单位不能反击
            
        dist = abs(unit.x - attacker.x) + abs(unit.y - attacker.y)
        return unit.attack_range[0] <= dist <= unit.attack_range[1]


""" How to Integrate
# 在导入部分添加
from ai import GameAI

# 在初始化部分
gm = GameManager(level)
ai_enabled = True
ai_player_id = 1
ai = GameAI(gm, ai_player_id)

# 在游戏主循环中
while running:
    # 处理事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F2:
                ai_enabled = not ai_enabled
                info_string = [f"AI {'已启用' if ai_enabled else '已禁用'}", ""]
    
    # 游戏逻辑
    if gm.state == GameState.PLAYING:
        if gm.cur_player_id == ai_player_id and ai_enabled:
            pygame.time.delay(500)  # 短暂延迟，让玩家看清AI的行动
            ai.make_move()
            # AI已经调用了next_turn，所以这里不需要再次调用
    
    # 绘制界面
    # ...其他绘制代码...
    
    # 显示AI状态
    if gm.state == GameState.PLAYING:
        font = pygame.font.SysFont('Calibri', 20)
        ai_text = font.render(f"AI: {'开启' if ai_enabled else '关闭'} (F2切换)", True, WHITE)
        screen.blit(ai_text, (SCREEN_WIDTH - ai_text.get_width() - 10, 10))
    
    pygame.display.flip()
"""