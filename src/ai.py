from game import GameManager
# from const import *
from units import *
import copy
import random
import math
import os
import pickle
import subprocess
import tempfile
import pygame
from ai_worker import get_all_possible_actions, execute_action, minimax, Counter

"""TODOs

"""

WORKER_THRESHOLD = 30  # 并行搜索的阈值，如果根行动数小于这个值，使用单线程版本
WORKER_SPLIT = 15  # 每个工作进程处理的行动数量阈值，用于动态计算最优工作进程数

class GameAI:
    def __init__(self, gm, render_func, search_depth=3):
        self.gm: GameManager = gm
        self.player_id = gm.ai_id
        self.render_func = render_func
        self.enemy_id = 1 - self.player_id  # 假设只有两个玩家
        self.search_depth = search_depth  # 对抗搜索的深度
        self.max_workers = min(10, os.cpu_count() or 1)  # 最大并行工作进程数

    def play_turn(self):
        """AI执行一回合的行动"""
        player = self.gm.players[self.player_id]
                
        # 排序单位列表，优先执行更强的单位
        units_to_process = player.units + [build for build in player.builds if build.attack]
        units_to_process.sort(key=lambda unit: (-unit.attack, -unit.movement)) 
        units_to_process += [unit for unit in player.units if hasattr(unit, 'blitz')]  # blitz 单位多考虑一次 --- [SPECIAL]

        # 为每个单位计算最佳行动并执行
        self.render_func(True)
        skip_units = []
        for unit in units_to_process:
            start_time = pygame.time.get_ticks()
            if unit.moved and unit.attacked:
                continue  # 跳过已经行动过的单位
            if unit in skip_units:
                continue
            best_action = self._search_best_action(unit)
            if best_action:
                execute_action(unit, best_action, self.gm, False)
            if hasattr(unit, 'blitz') and not unit.attacked:  # blitz 单位如果没有攻击就不会有下一轮 --- [SPECIAL]
                skip_units.append(unit)
                continue
            self._move_view(unit)  # 移动视角
            end_time = pygame.time.get_ticks()
            pygame.time.delay(300 - end_time + start_time)  # 短暂延迟
            self.render_func(True)  # 渲染更新

        print('-------AI End------')
        # 购买新单位
        self._try_purchase_units()
        self.render_func(True)
        pygame.time.delay(300)
        # 3. 结束回合
        self.gm.next_turn()
    
    def _search_best_action(self, unit):
        """
        并行版本的最佳行动搜索，使用多个进程同时计算
        """
        
        # 获取所有可能的行动
        root_actions = get_all_possible_actions(unit, self.gm)
        if not root_actions:
            return None
        
        # 如果行动数量少于阈值，使用非并行版本
        if len(root_actions) < WORKER_THRESHOLD:
            print('single\n')
            return self._search_best_action_non_parallel(unit, root_actions)
        
        # 创建临时目录存放进程间通信文件
        _dir = os.path.join(tempfile.gettempdir(), "tinywar")
        os.makedirs(_dir, exist_ok=True)
        temp_dir = tempfile.mkdtemp(dir=_dir)
        
        # 准备游戏状态数据
        game_state_data = pickle.dumps(copy.deepcopy(self.gm))
        unit_data = pickle.dumps(unit)
        
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
            action_count = len(actions)
            num_workers = max(1, min(self.max_workers, (action_count + WORKER_SPLIT - 1) // WORKER_SPLIT))
            print(f'{num_workers=}\n')
        
        # 只有一个工作进程时直接返回
        if num_workers <= 1:
            return [actions]
            
        # 创建空组
        result = [[] for _ in range(num_workers)]
        # 简单地按顺序分配所有行动
        for i, action in enumerate(actions):
            result[i % num_workers].append(action)
        return result

    def _search_best_action_non_parallel(self, unit, root_actions):
        """
        为指定 unit 计算最佳行动，使用 Alpha-Beta 剪枝优化的 minimax 递归。
        返回格式：{'unit': unit, 'action': action, 'score': score} 或 None（如果无可行动）。
        """
        if not root_actions:
            return None
            
        # 从根节点开始调用 minimax，初始 alpha=-inf, beta=inf
        root_state = copy.deepcopy(self.gm)
        # counter = Counter()
        best, score = minimax(root_state, unit, 0, True, float('-inf'), float('inf'), 
                             self.search_depth, self.player_id, self.enemy_id, None)
        # counter.print()
        if not best:
            return None
        best['score'] = score
        return best
    
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

