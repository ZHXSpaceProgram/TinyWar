import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
from units import Unit
import sys
import pickle
import copy

class Counter:
    """用于统计和打印调试信息的计数器类"""
    def __init__(self):
        self.counts = {}
    
    def increment(self, key, amount=1):
        if key not in self.counts:
            self.counts[key] = 0
        self.counts[key] += amount
    
    def print(self):
        print("=== 计数器统计 ===")
        for key, count in sorted(self.counts.items()):
            print(f"{key}: {count}")
        total = sum(self.counts.values())
        print('总计:', total, '次')
        print("==================\n")
counter = Counter()

def minimax(game_state, root_unit, current_depth, is_maximizing, alpha, beta, search_depth, player_id, enemy_id, root_actions, counter=None):
    """
    实现minimax算法的工作函数，用于在独立进程中执行
    """
    # 终止条件：达到最大搜索深度或游戏结束
    if current_depth >= search_depth or game_state.check_game_over():
        return None, evaluate_state(game_state, player_id, enemy_id)
    
    player_id_current = player_id if is_maximizing else enemy_id
    best_score = float('-inf') if is_maximizing else float('inf')
    best_action = None

    # 根节点只针对传入的unit；递归节点针对当前玩家所有单位
    units = [root_unit] if current_depth == 0 else game_state.players[player_id_current].units
    
    for unit_to_process in units:
        if unit_to_process.moved and unit_to_process.attacked:
            continue
        # Optimization
        if current_depth==2 and abs(unit_to_process.x - root_unit.x) + abs(unit_to_process.y - root_unit.y) > 2:
            continue
        considered_targets=set()

        possible_actions = root_actions if root_actions else get_all_possible_actions(unit_to_process, game_state)
        for action in possible_actions:
            
            # Optimization
            if current_depth==2:
                if action['type'] == 'move' or root_unit.movement > 4:
                    continue
                if action['type'] == 'attack':
                    target = action['target']
                    target_id = (target.x, target.y)
                    if target_id in considered_targets:
                        continue
                    considered_targets.add(target_id)
            
            if counter: # DEBUG:
                counter.increment(f'{current_depth}-{root_unit.type}-{action["type"]}', 1)

            # 模拟执行行动
            memo = {id(game_state.map): game_state.map}
            next_state = copy.deepcopy(game_state, memo)
            execute_action(unit_to_process, action, next_state, True)
            next_state.next_turn()
            
            # 递归，并传递alpha, beta
            _, score = minimax(next_state, root_unit, current_depth + 1, not is_maximizing, 
                              alpha, beta, search_depth, player_id, enemy_id, None, counter)
                            
            if is_maximizing:
                if score > best_score:
                    best_score, best_action = score, action
                alpha = max(alpha, best_score)
            else:
                if score < best_score:
                    best_score, best_action = score, action
                beta = min(beta, best_score)
            # 行为层剪枝
            if beta <= alpha:
                break
        # 单位层剪枝
        if beta <= alpha:
            break
    
    # 如果没有任何可行分支，则直接评估当前状态
    if best_action is None and best_score in (float('-inf'), float('inf')):
        return None, evaluate_state(game_state, player_id, enemy_id)
    
    return best_action, best_score

def evaluate_state(game_state, player_id, enemy_id):
    """评估模拟状态的分数"""    
    my_player = game_state.players[player_id]
    enemy_player = game_state.players[enemy_id]
    
    score = 0

    # 1. 单位数量和健康状况
    my_unit_value = sum(unit.health / unit.max_health * Unit.PROPERTIES[unit.type]['price'] 
                       for unit in my_player.units)
    enemy_unit_value = sum(unit.health / unit.max_health * Unit.PROPERTIES[unit.type]['price'] 
                          for unit in enemy_player.units)
    score += my_unit_value - enemy_unit_value
    
    # 2. 建筑控制
    my_build_value = sum(5 for build in my_player.builds)
    enemy_build_value = sum(5 for build in enemy_player.builds)
    score += (my_build_value - enemy_build_value) * 10
    
    # 3. 经济状况
    score += (my_player.money - enemy_player.money) * 0.5

    # DEBUG:
    # for unit in enemy_player.units:
    #     if unit.type == 'fighter':
    #         score -= unit.health * 10
    
    return score

def get_all_possible_actions(unit, game_state=None):
    """
    获得单位所有可能的移动和攻击行动
    - unit：要生成行动的单位对象
    - game_state：要在其上生成行动的游戏状态，默认为 None
    返回：
        actions: 包含所有 {'type': 'move'/'attack', ...} 的列表
    """
    # 选择使用的状态对象
    state = game_state

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
        })
    # ---- 3. 收集所有移动行动 ----
    for move_pos in state.possible_moves:
        actions.append({
            'type': 'move',
            'position': move_pos,
        })
    # 这里不能加deselect，因为执行的时候还会检查 possible_moves 和 possible_attacks
    return actions

def execute_action(unit, action, game_state, is_simulation):
    """
    在真实环境或复制环境中执行一次行动。
    - unit: 要执行行动的单位
    - action: 要执行的行动
    - game_state: 游戏状态对象
    - is_simulation: 是否是模拟环境，默认为False
    """
    # 选择要操作的 GameManager
    gm = game_state

    player_id = gm.cur_player_id
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

def search_task(game_state_data, unit_data, player_id, enemy_id, search_depth, actions=None):
    """工作进程的主函数，接收序列化数据并返回最佳行动"""
    # from game import GameManager
    # from units import Unit
    
    # 反序列化游戏状态和单位
    game_state = pickle.loads(game_state_data)
    unit = pickle.loads(unit_data)
    
    # 使用传入的行动列表，如果没有则重新计算
    root_actions = actions if actions is not None else get_all_possible_actions(unit, game_state)
    if not root_actions:
        return None
    counter = Counter() # DEBUG:
    # 执行minimax搜索
    best_action, score = minimax(game_state, unit, 0, True, float('-inf'), float('inf'), 
                               search_depth, player_id, enemy_id, root_actions, counter)
    counter.print()
    if not best_action:
        return None
    
    best_action['score'] = score
    
    # 序列化结果
    return pickle.dumps(best_action)

if __name__ == "__main__":
    # 从命令行参数获取输入文件路径和输出文件路径
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # 读取输入数据
    with open(input_file, 'rb') as f:
        data = pickle.load(f)
    
    game_state_data = data['game_state']
    unit_data = data['unit']
    player_id = data['player_id']
    enemy_id = data['enemy_id']
    search_depth = data['search_depth']
    actions = data['actions']  # 获取传入的行动列表
    
    # 执行搜索，传入行动列表
    result = search_task(game_state_data, unit_data, player_id, enemy_id, search_depth, actions)
    
    # 写入结果
    with open(output_file, 'wb') as f:
        if result:
            f.write(result)