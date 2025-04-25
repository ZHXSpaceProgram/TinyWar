from game import GameManager
from const import *
from units import *
import copy
import random
import math
import os
import pickle
import subprocess
import tempfile
import time
import pygame

"""TODOs

"""

class GameAI:
    def __init__(self, gm, render_func, search_depth=3):
        self.gm: GameManager = gm
        self.player_id = gm.ai_id
        self.render_func = render_func
        self.enemy_id = 1 - self.player_id  # 假设只有两个玩家
        self.search_depth = search_depth  # 对抗搜索的深度
        self.max_workers = min(12, os.cpu_count() or 1)  # 最大并行工作进程数

    def play_turn(self):
        """AI执行一回合的行动"""
        player = self.gm.players[self.player_id]
                
        # 排序单位列表，优先执行更强的单位
        units_to_process = player.units + [build for build in player.builds if build.attack]
        units_to_process.sort(key=lambda unit: (-unit.attack, -unit.movement)) 
        units_to_process += [unit for unit in player.units if hasattr(unit, 'blitz')]  # blitz 单位多考虑一次 --- [SPECIAL]
        
        # DEBUG
        # self.counter = Counter()

        # 为每个单位计算最佳行动并执行
        skip_units = []
        for unit in units_to_process:
            # start_time = pygame.time.get_ticks()
            if unit.moved and unit.attacked:
                continue  # 跳过已经行动过的单位
            if unit in skip_units:
                continue
            best_action = self._search_best_action_parallel(unit)
            if best_action:
                self._execute_action(unit, best_action)
            if hasattr(unit, 'blitz') and not unit.attacked:  # blitz 单位如果没有攻击就不会有下一轮 --- [SPECIAL]
                skip_units.append(unit)
                continue
            self._move_view(unit)  # 移动视角
            self.render_func(True)  # 渲染更新
            # end_time = pygame.time.get_ticks()
            # pygame.time.delay(500 - end_time + start_time)  # 短暂延迟

        print('-------AI End------')
        # DEBUG
        # self.counter.print()

        pygame.time.delay(500)

        # 购买新单位
        self._try_purchase_units()
        # 3. 结束回合
        self.gm.next_turn()
    
    def _search_best_action_parallel(self, unit):
        """
        并行版本的最佳行动搜索，使用多个进程同时计算
        """
        # DEBUG:
        # return self._search_best_action(unit)
        
        # 获取所有可能的行动
        root_actions = self._get_all_possible_actions(unit)
        if not root_actions:
            return None
        
        # 如果行动数量少于阈值，使用单线程版本
        if len(root_actions) <= 60:
            return self._search_best_action(unit)
        
        # 创建临时目录存放进程间通信文件
        temp_dir = tempfile.mkdtemp(dir=os.path.join(os.getcwd()))
        
        # 准备游戏状态数据
        game_state_data = pickle.dumps(copy.deepcopy(self.gm))
        unit_data = pickle.dumps(unit)
        
        # 将行动分组，每组由一个工作进程处理
        # action_groups = self._split_actions(root_actions, min(self.max_workers, len(root_actions)))

        # 将行动分组，每组由一个工作进程处理
        action_groups = self._split_actions(root_actions)

        processes = []
        input_files = []
        output_files = []
        
        # 启动工作进程
        for i, action_group in enumerate(action_groups):
            input_file = os.path.join(temp_dir, f"input_{i}.pkl")
            output_file = os.path.join(temp_dir, f"output_{i}.pkl")
            
            # 准备输入数据
            input_data = {
                'game_state': game_state_data,
                'unit': unit_data,
                'player_id': self.player_id,
                'enemy_id': self.enemy_id,
                'search_depth': self.search_depth,
                'actions': action_group
            }
            
            # 写入输入文件
            with open(input_file, 'wb') as f:
                pickle.dump(input_data, f)
            
            # 启动工作进程
            cmd = f"python {os.path.join(os.path.dirname(__file__), 'ai_worker.py')} {input_file} {output_file}"
            process = subprocess.Popen(cmd, shell=True)
            
            processes.append(process)
            input_files.append(input_file)
            output_files.append(output_file)
        
        # 等待所有进程完成
        for process in processes:
            process.wait()
        
        # 收集结果
        best_action = None
        best_score = float('-inf')
        
        for output_file in output_files:
            try:
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    with open(output_file, 'rb') as f:
                        action = pickle.loads(f.read())
                        if action and action.get('score', float('-inf')) > best_score:
                            best_score = action['score']
                            best_action = action
            except Exception as e:
                print(f"Error reading result: {e}")
        
        # 清理临时文件
        for file in input_files + output_files:
            if os.path.exists(file):
                os.remove(file)
        os.rmdir(temp_dir)
        
        return best_action
    
    def _split_actions(self, actions, num_workers=None):
        """
        将行动列表分成多个组，尽量均匀分配工作量
        如果未指定num_groups，则根据行动数量动态计算最优工作进程数
        """
        # 如果未指定工作进程数，则动态计算
        if num_workers is None:
            C = 20  # 每个工作进程处理的行动数阈值
            action_count = len(actions)
            num_workers = max(1, min(self.max_workers, (action_count + C - 1) // C))
            print(f'{num_workers=}')
        
        # 只有一个工作进程时直接返回
        if num_workers <= 1:
            return [actions]
            
        # 创建空组
        result = [[] for _ in range(num_workers)]
        # 简单地按顺序分配所有行动
        for i, action in enumerate(actions):
            result[i % num_workers].append(action)
        return result

    def _search_best_action(self, unit):
        """
        为指定 unit 计算最佳行动，使用 Alpha-Beta 剪枝优化的 minimax 递归。
        depth 参数表示当前已搜索深度，从 0 开始，达到 self.search_depth 时终止。
        返回格式：{'unit': unit, 'action': action, 'score': score} 或 None（如果无可行动）。
        """
        def minimax(game_state, current_depth, is_maximizing, alpha, beta, root_unit=None):
            # 终止条件：达到最大搜索深度或游戏结束
            if current_depth >= self.search_depth or game_state.check_game_over():
                return None, self._evaluate_state(game_state)
            
            player_id = self.player_id if is_maximizing else self.enemy_id
            best_score = float('-inf') if is_maximizing else float('inf')
            best_action = None

            # 根节点只针对传入的 unit；递归节点针对当前玩家所有单位
            units = [root_unit] if current_depth == 0 else game_state.players[player_id].units
            
            for unit in units:
                if unit.moved and unit.attacked:
                    continue
                
                # Optimization
                # 深度为2时只考虑距离根单位一定距离内的
                # if current_depth == 2 and abs(unit.x - root_unit.x) + abs(unit.y - root_unit.y) > 3:
                #     continue
                
                possible = root_actions if (current_depth == 0) else self._get_all_possible_actions(unit, game_state)
                for action in possible:
                    # Optimization
                    # 如果action是移动，跳过
                    # if current_depth==2 and action['type'] == 'move':
                    #     continue
                    
                    # DEBUG
                    # self.counter.increment(f"{unit.type}-{current_depth}-{action['type']}")

                    # 模拟执行行动
                    # Optimization: do not copy the map
                    memo = {id(game_state.map): game_state.map}
                    next_state = copy.deepcopy(game_state, memo)
                    self._execute_action(unit, action, next_state)
                    next_state.next_turn()
                    
                    # 递归，并传递 alpha, beta
                    _, score = minimax(next_state, current_depth + 1, not is_maximizing, alpha, beta, root_unit=root_unit)
                                    
                    if is_maximizing:
                        if score > best_score:
                            best_score, best_action = score, action
                        alpha = max(alpha, best_score)
                    else:
                        if score < best_score:
                            best_score, best_action = score, None
                        beta = min(beta, best_score)
                    # 行为层剪枝
                    if beta <= alpha:
                        break
                # 单位层剪枝
                if beta <= alpha:
                    break
            # 如果没有任何可行分支，则直接评估当前状态
            if best_action is None and best_score in (float('-inf'), float('inf')):
                return None, self._evaluate_state(game_state)
            return best_action, best_score

        root_actions = self._get_all_possible_actions(unit)
        if not root_actions:
            return None
        # 从根节点开始调用 minimax，初始 alpha=-inf, beta=inf
        root_state = copy.deepcopy(self.gm)
        best, score = minimax(root_state, 0, True, float('-inf'), float('inf'), root_unit=unit)
        if not best:
            return None
        best['score'] = score
        return best

    def _get_all_possible_actions(self, unit, game_state=None):
        """
        获得单位所有可能的移动和攻击行动
        - unit：要生成行动的单位对象
        - game_state：要在其上生成行动的游戏状态，默认为 self.gm
        返回：
            actions: 包含所有 {'type': 'move'/'attack', ...} 的列表，每个 action 均带有初始 score=0
        """
        # 选择使用的状态对象
        state = game_state if game_state is not None else self.gm

        # ---- 1. 计算可能的移动和攻击 ----
        # 设定当前选中单位并计算可达格子，第二个参数控制是否允许跨越攻击范围 >1
        # 建筑的移动会被跳过
        state.selected_unit = unit
        override_movement = 1 if hasattr(unit, 'blitz') and unit.attacked else None # blitz 单位override_movement --- [SPECIAL]
        state._calculate_possible_moves(unit.moved, unit.attack_range[0]>1, override_movement)

        # Optimzation 优先考虑攻击
        # ---- 2. 收集所有由 GM 预先计算出的攻击行动 ----
        actions = []
        for from_pos, to_pos, target in state.possible_attacks:
            actions.append({
                'type': 'attack',
                'from_position': from_pos,
                'target_position': to_pos,
                'target': target,
                # 'score': 0
            })
        # ---- 3. 收集所有移动行动 ----\
        for move_pos in state.possible_moves:
            actions.append({
                'type': 'move',
                'position': move_pos,
                # 'score': 0
            })
        # 这里不能加deselect，因为执行的时候还会检查 possible_moves 和 possible_attacks
        return actions

    def _execute_action(self, unit, action, game_copy=None):
        """
        在真实环境或复制环境中执行一次行动。
        如果 game_copy 为 None，则在 self.gm（真实环境）上执行；否则在 game_copy（模拟环境）上执行。
        """
        # 选择要操作的 GameManager
        is_simulation = game_copy is not None
        gm = game_copy or self.gm

        player_id = gm.cur_player_id if is_simulation else self.player_id
        # ——1) 选中单位——
        if is_simulation:
            # 模拟环境里需要根据坐标去复制对象列表里找对应的 unit_copy
            player = gm.players[player_id]
            unit_copy = next(
                (u for u in player.units + player.builds
                if u.x == unit.x and u.y == unit.y),
                None
            )
            if not unit_copy:
                return  # 单位没找到，无法模拟
            gm.selected_unit = unit_copy
        else:
            # 真实环境中直接用传进来的 unit
            gm.selected_unit = unit
        # ——2) 执行动作——
        type = action.get('type')
        if type == 'move':
            x, y = action['position']
            gm.move_selected_unit(x, y, is_simulation)

        elif type == 'attack':
            # 可能要先移动
            fx, fy = action['from_position']
            if (fx, fy) != (unit.x, unit.y):
                gm.move_selected_unit(fx, fy, is_simulation)

            # 再执行攻击
            tx, ty = action['target_position']
            gm.attack(tx, ty, is_simulation)
  
    # def _evaluate_state(self, game_state):
    #     """评估模拟状态的分数"""
    #     my_player = game_state.players[self.player_id]
    #     enemy_player = game_state.players[self.enemy_id]
        
    #     score = 0

    #     # 1. 单位数量和健康状况
    #     my_unit_value = sum(unit.health / unit.max_health * Unit.PROPERTIES[unit.type]['price'] 
    #                        for unit in my_player.units)
    #     enemy_unit_value = sum(unit.health / unit.max_health * Unit.PROPERTIES[unit.type]['price'] 
    #                           for unit in enemy_player.units)
    #     score += my_unit_value - enemy_unit_value
        
    #     # 2. 建筑控制
    #     my_build_value = sum(5 for build in my_player.builds)
    #     enemy_build_value = sum(5 for build in enemy_player.builds)
    #     score += (my_build_value - enemy_build_value) * 10
        
    #     # 3. 经济状况
    #     score += (my_player.money - enemy_player.money) * 0.5
        
    #     # 4. 战略位置控制
    #     # 这里可以添加对关键位置控制的评估
        
    #     return score

    def _try_purchase_units(self):
        """尝试在可用的建筑中购买单位"""
        player: Player = self.gm.cur_player()
        
        # 获取所有可以购买单位的建筑
        factories = [build for build in player.builds if build.shop_type != SHOP_TYPE.NONE]
        
        for factory in factories:
            # 根据建筑类型确定可购买的单位类型
            available_units = shop_available_units[factory.shop_type]
            
            # 按性价比排序
            available_units.sort(key=lambda unit_type: 
                                Unit.PROPERTIES[unit_type]['attack'] / Unit.PROPERTIES[unit_type]['price'])
            
            # 尝试购买最好的单位
            for unit_type in available_units:
                self.gm.buy_item(unit_type, factory.x, factory.y)
                break  # 每个建筑每回合只购买一个单位

    def _move_view(self, unit):
        if unit.x < self.gm.map_x:
            self.gm.map_x = unit.x
        elif unit.x >= self.gm.map_x + MAP_VIEW_SIZE:
            self.gm.map_x = unit.x - MAP_VIEW_SIZE + 1
        if unit.y < self.gm.map_y:
            self.gm.map_y = unit.y
        elif unit.y >= self.gm.map_y + MAP_VIEW_SIZE:
            self.gm.map_y = unit.y - MAP_VIEW_SIZE + 1

