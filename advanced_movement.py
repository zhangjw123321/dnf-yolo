"""
advanced_movement.py - 完整的高级移动控制器
从main_run_backup.py移植的完整斜向移动系统
包含4种不同的流畅斜向移动方案和智能角度计算
"""

import math
import time
from input_controllers import create_input_controller

class AdvancedMovementController:
    """完整的高级移动控制器 - 支持智能8方向移动和多种斜向方案"""
    
    def __init__(self, input_controller=None):
        """初始化高级移动控制器"""
        self.input_controller = input_controller or create_input_controller("默认")
        
        # 方向键映射
        self.key_map = {
            'right': 39, 'left': 37, 'up': 38, 'down': 40
        }
        
        # 移动状态
        self.current_direction = None
        self.current_movement_keys = []
        self.is_moving = False
        
        print("AdvancedMovementController初始化完成")
    
    def calculate_movement_to_45_degree(self, dx, dy):
        """智能角度计算 - 将任意角度转换为8方向移动"""
        # 先计算直线距离用于判断
        euclidean_distance = math.sqrt(dx*dx + dy*dy)
        if euclidean_distance < 30:  # 距离太近
            return None, 0, None, 0
        
        # 计算角度
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        
        # 8方向映射
        directions = [
            (0, ['right']),           # 0°
            (45, ['right', 'down']),  # 45°
            (90, ['down']),           # 90°
            (135, ['left', 'down']),  # 135°
            (180, ['left']),          # 180°
            (225, ['left', 'up']),    # 225°
            (270, ['up']),            # 270°
            (315, ['right', 'up'])    # 315°
        ]
        
        # 找到最接近的方向
        best_direction = None
        min_diff = float('inf')
        
        for target_angle, keys in directions:
            diff = min(abs(angle - target_angle), 360 - abs(angle - target_angle))
            if diff < min_diff:
                min_diff = diff
                best_direction = keys
        
        # 计算实际移动距离（不是直线距离）
        if len(best_direction) == 1:
            # 单方向移动
            if best_direction[0] in ['left', 'right']:
                # 纯x轴移动，距离就是x轴距离
                actual_distance = abs(dx)
            else:
                # 纯y轴移动，距离就是y轴距离
                actual_distance = abs(dy)
        else:
            # 斜向移动，使用斜边距离
            actual_distance = math.sqrt(dx*dx + dy*dy)
        
        # 计算移动时间（基于移动方向的不同移速）
        x_speed = 480  # x轴速度480像素每秒
        y_speed = 168  # y轴速度168像素每秒
        diagonal_speed = 300  # 斜向速度300像素每秒
        speed_percentage = getattr(self, 'speed', 100) / 100.0  # 速度百分比
        
        # 判断移动方向并选择对应速度
        if len(best_direction) == 1:
            # 单方向移动
            if best_direction[0] in ['left', 'right']:
                # 纯x轴移动
                actual_speed = x_speed * speed_percentage
            else:
                # 纯y轴移动
                actual_speed = y_speed * speed_percentage
        else:
            # 斜向移动
            actual_speed = diagonal_speed * speed_percentage
        
        # 计算移动时间（这是从第二次按键开始到结束的时间）
        move_time = min(max(actual_distance / actual_speed, 0.1), 3.0)  # 0.1-3.0秒范围
        
        return best_direction, move_time, None, 0
    
    def smooth_diagonal_movement_v1(self, movement_keys):
        """方案1: 快速连续奔跑 - 优化按键时间"""
        try:
            if len(movement_keys) == 2:
                key1, key2 = movement_keys[0], movement_keys[1]
                key_code1, key_code2 = self.key_map[key1], self.key_map[key2]
                
                print(f"🏃‍♂️ 快速连续奔跑: {key1}+{key2}")
                
                # 第一个方向键触发奔跑
                self.input_controller.press_key(key_code1, 0.01)
                time.sleep(0.003)  # 3毫秒间隔
                self.input_controller.hold_key(key_code1)
                
                # 第二个方向键触发奔跑
                self.input_controller.press_key(key_code2, 0.01)
                time.sleep(0.003)  # 3毫秒间隔
                self.input_controller.hold_key(key_code2)
                
                self.current_movement_keys = [key_code1, key_code2]
                return True
        except Exception as e:
            print(f"快速连续奔跑失败: {e}")
            return False
    
    def smooth_diagonal_movement_v2(self, movement_keys):
        """方案2: 优化斜向奔跑 - 按你的奔跑机制优化"""
        try:
            if len(movement_keys) == 2:
                key1, key2 = movement_keys[0], movement_keys[1]
                key_code1, key_code2 = self.key_map[key1], self.key_map[key2]
                
                print(f"🏃‍♂️ 优化斜向奔跑: {key1}+{key2}")
                
                # 两个方向键同时触发奔跑（0.01秒）
                self.input_controller.press_key(key_code1, 0.01)
                self.input_controller.press_key(key_code2, 0.01)
                
                # 极短间隔
                time.sleep(0.005)
                
                # 同时持续按住两个方向键
                self.input_controller.hold_key(key_code1)
                self.input_controller.hold_key(key_code2)
                
                self.current_movement_keys = [key_code1, key_code2]
                return True
        except Exception as e:
            print(f"优化斜向奔跑失败: {e}")
            return False
    
    def smooth_diagonal_movement_v3(self, movement_keys):
        """方案3: 微妙错位双击 - 两个方向键微妙的时间差"""
        try:
            if len(movement_keys) == 2:
                key1, key2 = movement_keys[0], movement_keys[1]
                key_code1, key_code2 = self.key_map[key1], self.key_map[key2]
                
                print(f"🏃‍♂️ 微妙错位双击: {key1}+{key2}")
                
                # 微妙错位启动
                self.input_controller.press_key(key_code1, 0.01)
                time.sleep(0.003)  # 3毫秒错位
                self.input_controller.press_key(key_code2, 0.01)
                
                time.sleep(0.02)
                self.input_controller.hold_key(key_code1)
                time.sleep(0.001)  # 1毫秒错位
                self.input_controller.hold_key(key_code2)
                
                self.current_movement_keys = [key_code1, key_code2]
                return True
        except Exception as e:
            print(f"微妙错位双击失败: {e}")
            return False
    
    def smooth_diagonal_movement_v4(self, movement_keys):
        """方案4: 传统游戏风格 - 真正的同时按下"""
        try:
            if len(movement_keys) == 2:
                key1, key2 = movement_keys[0], movement_keys[1]
                key_code1, key_code2 = self.key_map[key1], self.key_map[key2]
                
                print(f"🏃‍♂️ 传统同时按下: {key1}+{key2}")
                
                # 传统同时启动
                self.input_controller.press_key(key_code1, 0.01)
                self.input_controller.press_key(key_code2, 0.01)
                
                time.sleep(0.02)
                self.input_controller.hold_key(key_code1)
                self.input_controller.hold_key(key_code2)
                
                self.current_movement_keys = [key_code1, key_code2]
                return True
        except Exception as e:
            print(f"传统同时按下失败: {e}")
            return False
    
    def optimized_double_tap_movement(self, key_code):
        """优化的双击奔跑效果 - 按你的奔跑机制"""
        try:
            print(f"🏃‍♂️ 双击奔跑启动: {key_code}")
            
            # 第一次按键0.01秒触发奔跑
            self.input_controller.press_key(key_code, 0.01)
            time.sleep(0.01)  # 短暂间隔
            
            # 第二次持续按住到目标位置
            self.input_controller.hold_key(key_code)
            
            self.current_direction = key_code
            return True
        except Exception as e:
            print(f"双击奔跑失败: {e}")
            return False
    
    def execute_optimized_movement(self, movement_keys, move_time, smooth_method="v2"):
        """执行优化的移动操作"""
        try:
            print(f"🏃‍♂️ 执行优化移动:")
            print(f"   ├─ 移动方向: {' + '.join(movement_keys)}")
            print(f"   ├─ 移动时间: {move_time:.3f} 秒")
            print(f"   └─ 使用方案: {smooth_method}")
            
            self.is_moving = True
            movement_start_time = time.time()
            
            if len(movement_keys) == 1:
                # 单方向移动
                key_code = self.key_map[movement_keys[0]]
                success = self.optimized_double_tap_movement(key_code)
            else:
                # 斜向移动 - 根据方案选择
                method_map = {
                    "v1": self.smooth_diagonal_movement_v1,
                    "v2": self.smooth_diagonal_movement_v2,
                    "v3": self.smooth_diagonal_movement_v3,
                    "v4": self.smooth_diagonal_movement_v4
                }
                
                method = method_map.get(smooth_method, self.smooth_diagonal_movement_v2)
                success = method(movement_keys)
            
            if success:
                # 保持移动指定时间
                time.sleep(move_time)
                
                # 停止移动
                self.stop_all_movement()
                
                actual_time = time.time() - movement_start_time
                print(f"✅ 移动完成，实际用时: {actual_time:.3f}秒")
                return True
            else:
                print("❌ 移动启动失败")
                return False
                
        except Exception as e:
            print(f"执行移动失败: {e}")
            self.stop_all_movement()
            return False
    
    def move_to_monster_optimized(self, monster_x, monster_y, cheng_hao_x, cheng_hao_y, use_smart_method_selection=True):
        """使用优化的智能角度移动系统移动到怪物位置"""
        try:
            # 计算移动向量
            dx = monster_x - cheng_hao_x
            dy = monster_y - cheng_hao_y
            
            print(f"🧮 移动向量: dx={dx}, dy={dy}")
            
            # 计算距离，如果太近则无需移动
            real_distance = math.sqrt(dx*dx + dy*dy)
            if real_distance < 30:
                print("怪物距离太近，无需移动")
                return True
            
            # 使用智能角度计算
            movement_keys, move_time, _, _ = self.calculate_movement_to_45_degree(dx, dy)
            
            if movement_keys is None:
                print("无需移动")
                return True
            
            # 智能方案选择
            if use_smart_method_selection:
                smooth_method = self.select_optimal_diagonal_method(dx, dy, real_distance)
            else:
                smooth_method = "v2"  # 默认使用推荐方案
            
            print(f"📍 移动到怪物: ({cheng_hao_x}, {cheng_hao_y}) -> ({monster_x}, {monster_y})")
            print(f"📏 距离: {real_distance:.1f}像素, 方向: {movement_keys}")
            
            # 执行移动
            return self.execute_optimized_movement(movement_keys, move_time, smooth_method)
            
        except Exception as e:
            print(f"移动到怪物失败: {e}")
            return False
    
    def select_optimal_diagonal_method(self, dx, dy, distance):
        """智能选择最佳斜向移动方案"""
        abs_dx, abs_dy = abs(dx), abs(dy)
        
        if distance < 50:
            return "v2"  # 距离太近，使用默认方案
        
        if abs_dx > abs_dy:
            # 主要是水平移动
            if abs_dy < abs_dx * 0.5:
                return "v2"  # 接近水平，使用预启动奔跑
            else:
                return "v1"  # 需要快速响应
        else:
            # 主要是垂直移动
            if abs_dx < abs_dy * 0.5:
                return "v2"  # 接近垂直，使用预启动奔跑
            else:
                return "v3"  # 需要精确控制
    
    def stop_all_movement(self):
        """停止所有移动"""
        try:
            # 释放当前移动的所有按键
            if self.current_direction:
                self.input_controller.release_key(self.current_direction)
                self.current_direction = None
            
            for key_code in self.current_movement_keys:
                self.input_controller.release_key(key_code)
            
            # 释放所有可能的方向键（保险起见）
            all_direction_keys = [37, 38, 39, 40]  # left, up, right, down
            for key_code in all_direction_keys:
                self.input_controller.release_key(key_code)
            
            self.current_movement_keys = []
            self.is_moving = False
            print("✅ 已停止所有移动")
            
        except Exception as e:
            print(f"停止移动失败: {e}")
    
    def test_all_diagonal_methods(self):
        """测试所有斜向移动方案"""
        test_movements = [
            (['right', 'down'], "右下"),
            (['left', 'up'], "左上"),
            (['right', 'up'], "右上"),
            (['left', 'down'], "左下")
        ]
        
        methods = ["v1", "v2", "v3", "v4"]
        
        print("\n🎯 开始测试所有斜向移动方案")
        
        for method in methods:
            print(f"\n=== 测试方案 {method} ===")
            for movement_keys, description in test_movements:
                print(f"测试{description}移动...")
                self.execute_optimized_movement(movement_keys, 1.5, method)
                time.sleep(0.5)  # 间隔0.5秒
        
        print("\n🎯 测试完成！")
    
    def move_to_target_with_smart_method(self, current_x, current_y, target_x, target_y, speed_percentage=100, target_type="monster"):
        """使用智能方案选择的移动到目标位置"""
        try:
            # 计算移动向量
            dx = target_x - current_x
            dy = target_y - current_y
            euclidean_distance = math.sqrt(dx * dx + dy * dy)
            
            # 检查是否需要移动
            if euclidean_distance < 30:
                print(f"目标距离太近 ({euclidean_distance:.1f}像素)，无需移动")
                return True
            
            # 使用智能角度计算
            movement_keys, move_time, _, _ = self.calculate_movement_to_45_degree(dx, dy)
            
            if movement_keys is None:
                print("无需移动")
                return True
            
            # 计算实际移动距离用于显示
            if len(movement_keys) == 1:
                if movement_keys[0] in ['left', 'right']:
                    actual_distance = abs(dx)
                else:
                    actual_distance = abs(dy)
            else:
                actual_distance = math.sqrt(dx*dx + dy*dy)
            
            # 智能方案选择
            smooth_method = self.select_optimal_diagonal_method(dx, dy, euclidean_distance)
            
            # 计算实际角度用于显示
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0:
                angle += 360
            
            print(f"📍 智能移动: ({current_x}, {current_y}) -> ({target_x}, {target_y})")
            print(f"📏 距离: {actual_distance:.1f}像素, 移速: {speed_percentage}%, 角度: {angle:.1f}°, 目标: {target_type}")
            print(f"🎯 移动方向: {movement_keys}, 时间: {move_time:.3f}秒, 方案: {smooth_method}")
            
            # 执行移动
            return self.execute_optimized_movement(movement_keys, move_time, smooth_method)
            
        except Exception as e:
            print(f"智能移动失败: {e}")
            return False
    
    def calculate_angle(self, dx, dy):
        """计算移动角度"""
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        return angle
    
    def get_movement_for_angle(self, angle):
        """根据角度获取移动方向键"""
        # 8方向映射
        if 337.5 <= angle or angle < 22.5:
            return ['right']
        elif 22.5 <= angle < 67.5:
            return ['right', 'down']
        elif 67.5 <= angle < 112.5:
            return ['down']
        elif 112.5 <= angle < 157.5:
            return ['left', 'down']
        elif 157.5 <= angle < 202.5:
            return ['left']
        elif 202.5 <= angle < 247.5:
            return ['left', 'up']
        elif 247.5 <= angle < 292.5:
            return ['up']
        elif 292.5 <= angle < 337.5:
            return ['right', 'up']
        else:
            return ['right']  # 默认
    
    def execute_single_direction_movement(self, direction, duration, use_run=False):
        """执行单方向移动"""
        try:
            key_code = self.key_map[direction]
            
            if use_run:
                # 双击奔跑
                success = self.optimized_double_tap_movement(key_code)
                if success:
                    time.sleep(duration)
                    self.stop_all_movement()
                return success
            else:
                # 普通移动
                self.input_controller.hold_key(key_code)
                time.sleep(duration)
                self.input_controller.release_key(key_code)
                return True
                
        except Exception as e:
            print(f"单方向移动失败: {e}")
            return False
    
    def execute_diagonal_movement(self, movement_keys, duration, use_run=False, method="v2"):
        """执行斜向移动"""
        try:
            if len(movement_keys) != 2:
                print("斜向移动需要2个方向键")
                return False
            
            if use_run:
                # 使用流畅的斜向奔跑
                success = self.execute_optimized_movement(movement_keys, duration, method)
            else:
                # 普通斜向移动
                key1, key2 = movement_keys[0], movement_keys[1]
                key_code1, key_code2 = self.key_map[key1], self.key_map[key2]
                
                self.input_controller.hold_key(key_code1)
                self.input_controller.hold_key(key_code2)
                time.sleep(duration)
                self.input_controller.release_key(key_code1)
                self.input_controller.release_key(key_code2)
                success = True
            
            return success
            
        except Exception as e:
            print(f"斜向移动失败: {e}")
            return False
    
    def _execute_smooth_diagonal_run(self, key_code1, key_code2, duration, method="v2"):
        """执行流畅的斜向奔跑"""
        try:
            movement_keys = []
            for key, code in self.key_map.items():
                if code == key_code1:
                    movement_keys.append(key)
                    break
            for key, code in self.key_map.items():
                if code == key_code2:
                    movement_keys.append(key)
                    break
            
            if len(movement_keys) == 2:
                return self.execute_optimized_movement(movement_keys, duration, method)
            else:
                print("无法找到对应的方向键")
                return False
                
        except Exception as e:
            print(f"流畅斜向奔跑失败: {e}")
            return False


def test_advanced_movement():
    """测试高级移动控制器"""
    print("=== 测试高级移动控制器 ===")
    
    controller = AdvancedMovementController()
    
    # 测试智能角度计算
    test_cases = [
        (100, 0, "正右"),
        (100, 100, "右下"),
        (0, 100, "正下"),
        (-100, 100, "左下"),
        (-100, 0, "正左"),
        (-100, -100, "左上"),
        (0, -100, "正上"),
        (100, -100, "右上"),
    ]
    
    print("\n=== 智能角度计算测试 ===")
    for dx, dy, description in test_cases:
        movement_keys, move_time, _, _ = controller.calculate_movement_to_45_degree(dx, dy)
        print(f"  {description:4s} ({dx:4d}, {dy:4d}): {movement_keys} - {move_time:.2f}秒")
    
    # 可选：运行完整测试
    # controller.test_all_diagonal_methods()


if __name__ == "__main__":
    test_advanced_movement()