"""
actions.py - 完整的攻击和移动系统
整合了yaoqi_attack.py, advanced_movement.py, speed_calculator.py的功能
"""

import cv2
import numpy as np
import mss
import time
import random
import math
import os
import re
from ultralytics import YOLO
import pygetwindow as gw
from input_controllers import create_input_controller
import easyocr


def get_random_delay():
    """获取随机延迟时间"""
    return round(random.uniform(0.1311, 0.1511), 4)


class SpeedCalculator:
    """移动速度计算器"""
    
    def __init__(self):
        """初始化速度计算器 - 参考advanced_movement.py的方向性速度"""
        # 参考advanced_movement.py中的方向性速度设置
        self.X_SPEED = 480  # x轴速度480像素每秒
        self.Y_SPEED = 168  # y轴速度168像素每秒  
        self.DIAGONAL_SPEED = 300  # 斜向速度300像素每秒
        
        # 保持向后兼容的基础速度
        self.BASE_RUNNING_SPEED = 480   # 与X_SPEED保持一致
        self.BASE_WALKING_SPEED = 300   # 参考DIAGONAL_SPEED
        
        # 移动相关参数
        self.ACCELERATION_TIME = 0.05   # 减少加速时间
        self.MIN_MOVE_TIME = 0.05      # 最小移动时间
        self.MAX_MOVE_TIME = 2.0       # 最大移动时间
        
        print(f"SpeedCalculator初始化完成（参考advanced_movement速度配置）")
        print(f"X轴速度: {self.X_SPEED} 像素/秒")
        print(f"Y轴速度: {self.Y_SPEED} 像素/秒") 
        print(f"斜向速度: {self.DIAGONAL_SPEED} 像素/秒")
    
    def calculate_actual_speed(self, speed_percentage, is_running=True):
        """计算实际移动速度 - 参考advanced_movement.py的方向性速度"""
        # 使用方向性速度计算 - 参考advanced_movement.py的速度配置
        if is_running:
            # 奔跑状态：使用X_SPEED作为基础速度
            base_speed = self.X_SPEED
        else:
            # 行走状态：使用DIAGONAL_SPEED作为基础速度
            base_speed = self.DIAGONAL_SPEED
        
        # 实际速度 = 基础速度 * (识别的speed百分比 / 100)
        actual_speed = base_speed * (speed_percentage / 100.0)
        return actual_speed
    
    def calculate_move_time(self, distance, speed_percentage, is_running=True):
        """
        计算移动时间 - 基于移动方向的不同移速（参考advanced_movement.py）
        """
        if distance <= 0:
            return 0
        
        # 使用方向性速度计算 - 参考advanced_movement.py的速度配置
        if is_running:
            # 奔跑状态：使用X_SPEED作为基础速度
            base_speed = self.X_SPEED
        else:
            # 行走状态：使用DIAGONAL_SPEED作为基础速度
            base_speed = self.DIAGONAL_SPEED
        
        # 根据识别的速度百分比调整实际速度
        actual_speed = base_speed * (speed_percentage / 100.0)
        
        # 基础移动时间：距离 / 实际速度
        base_time = distance / actual_speed
        
        # 简化加速时间处理
        if distance < 50:
            # 极短距离，稍微增加时间
            move_time = base_time + 0.02
        else:
            # 正常距离，最小加速时间
            move_time = base_time + 0.01
        
        # 限制移动时间范围
        move_time = max(self.MIN_MOVE_TIME, min(move_time, self.MAX_MOVE_TIME))
        
        # 调试信息
        move_type = "奔跑" if is_running else "行走"
        print(f"📊 移动时间计算（参考advanced_movement速度）:")
        print(f"   ├─ 距离: {distance:.1f} 像素")
        print(f"   ├─ 识别移速: {speed_percentage:.1f}%")
        print(f"   ├─ 基础速度: {base_speed} 像素/秒 ({move_type})")
        print(f"   ├─ 实际速度: {actual_speed:.1f} 像素/秒")
        print(f"   ├─ 基础时间: {base_time:.3f} 秒")
        print(f"   └─ 最终时间: {move_time:.3f} 秒")
        
        return move_time
    
    def calculate_optimal_move_time(self, distance, speed_percentage, target_type="fixed"):
        """计算最优移动时间"""
        # 根据距离和目标类型决定移动策略
        if target_type == "monster":
            # 追怪物：距离较近用行走，距离远用奔跑
            if distance < 80:
                # 近距离用行走，更精确
                use_run = False
                move_time = self.calculate_move_time(distance, speed_percentage, False)
            else:
                # 远距离用奔跑，更快
                use_run = True
                move_time = self.calculate_move_time(distance, speed_percentage, True)
        else:
            # 固定目标：距离超过150像素就用奔跑
            if distance < 150:
                use_run = False
                move_time = self.calculate_move_time(distance, speed_percentage, False)
            else:
                use_run = True
                move_time = self.calculate_move_time(distance, speed_percentage, True)
        
        return move_time, use_run


class AdvancedMovementController:
    """高级移动控制器 - 支持8方向精确移动"""
    
    def __init__(self, input_controller=None):
        """初始化高级移动控制器"""
        self.input_controller = input_controller or create_input_controller("默认")
        self.speed_calculator = SpeedCalculator()
        
        # 方向键映射
        self.key_map = {
            'right': 39, 'left': 37, 'up': 38, 'down': 40
        }
        
        # 移动参数 - 添加缺失的属性
        self.min_move_distance = 30  # 最小移动距离
        self.diagonal_threshold = 45  # 斜向移动阈值角度
        
        print("AdvancedMovementController初始化完成")
    
    def calculate_angle(self, dx, dy):
        """计算移动角度 - 添加调试信息"""
        if dx == 0 and dy == 0:
            return 0
        
        angle = math.degrees(math.atan2(dy, dx))
        # 标准化到0-360度范围
        if angle < 0:
            angle += 360
            
        print(f"🧮 角度计算: dx={dx}, dy={dy} → angle={angle:.1f}°")
        return angle
    
    def get_movement_for_angle(self, angle):
        """根据角度返回移动方向键组合 - 修复斜向移动判断"""
        # 将角度标准化到0-360范围
        angle = angle % 360
        
        print(f"🔍 角度判断: {angle:.1f}°")
        
        # 定义斜向移动的角度范围（更宽松的判断）
        if 30 <= angle <= 60:      # 右下
            print(f"📐 判断结果: 右下斜向移动")
            return ['right', 'down']
        elif 120 <= angle <= 150:  # 左下
            print(f"📐 判断结果: 左下斜向移动")
            return ['left', 'down']
        elif 210 <= angle <= 240:  # 左上
            print(f"📐 判断结果: 左上斜向移动")
            return ['left', 'up']
        elif 300 <= angle <= 330:  # 右上
            print(f"📐 判断结果: 右上斜向移动")
            return ['right', 'up']
        
        # 单方向移动
        if 330 < angle or angle <= 30:
            print(f"📐 判断结果: 单向右移动")
            return ['right']
        elif 60 < angle <= 120:
            print(f"📐 判断结果: 单向下移动")
            return ['down']
        elif 150 < angle <= 210:
            print(f"📐 判断结果: 单向左移动")
            return ['left']
        elif 240 < angle <= 300:
            print(f"📐 判断结果: 单向上移动")
            return ['up']
        else:
            print(f"📐 判断结果: 默认右移动")
            return ['right']
    
    def execute_single_direction_movement(self, direction_key, duration, use_run=False):
        """执行单方向移动 - 优化双击奔跑"""
        try:
            key_code = self.key_map[direction_key]
            
            if use_run:
                # 优化的双击奔跑效果
                print(f"🏃‍♂️ 奔跑移动: {direction_key}, 时间: {duration:.3f}秒")
                return self._optimized_double_tap_movement(key_code, duration)
            else:
                # 普通移动
                print(f"🚶‍♂️ 行走移动: {direction_key}, 时间: {duration:.3f}秒")
                self.input_controller.press_key(key_code, duration)
            
            return True
        except Exception as e:
            print(f"单方向移动失败: {e}")
            return False
    
    def _optimized_double_tap_movement(self, key_code, duration):
        """优化的双击奔跑效果"""
        try:
            # 第一次按键（极短按）- 初始化移动
            self.input_controller.press_key(key_code, 0.01)
            print(f"第一次按下方向键 {key_code} 0.01秒")
            
            # 极短间隔
            time.sleep(0.02)
            
            # 第二次按键（按住）- 触发奔跑并持续移动
            self.input_controller.hold_key(key_code)
            print(f"第二次按下并按住方向键 {key_code}")
            
            # 保持移动指定时间
            time.sleep(duration)
            
            # 释放按键
            self.input_controller.release_key(key_code)
            print(f"释放方向键 {key_code}")
            
            return True
        except Exception as e:
            print(f"优化双击奔跑失败: {e}")
            return False
    
    def execute_diagonal_movement(self, movement_keys, duration, use_run=False, method="v2"):
        """执行斜向移动"""
        try:
            if len(movement_keys) != 2:
                print("斜向移动需要2个方向键")
                return False
            
            key1, key2 = movement_keys[0], movement_keys[1]
            key_code1, key_code2 = self.key_map[key1], self.key_map[key2]
            
            move_type = "奔跑" if use_run else "行走"
            print(f"🏃‍♂️ 斜向{move_type}: {key1}+{key2}, 时间: {duration:.3f}秒, 方案: {method}")
            
            if use_run:
                # 使用流畅的斜向奔跑
                success = self._execute_smooth_diagonal_run(key_code1, key_code2, duration, method)
            else:
                # 普通斜向移动
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
            if method == "v1":
                # 方案1: 快速连续双击 - 几乎同时启动两个方向
                self.input_controller.press_key(key_code1, 0.01)
                time.sleep(0.01)
                self.input_controller.hold_key(key_code1)
                
                time.sleep(0.005)  # 只有5毫秒间隔
                self.input_controller.press_key(key_code2, 0.01)
                time.sleep(0.01)
                self.input_controller.hold_key(key_code2)
                
            elif method == "v2":
                # 方案2: 预启动奔跑 - 先启动奔跑状态再转斜向（推荐）
                # 阶段1: 主方向双击启动奔跑
                self.input_controller.press_key(key_code1, 0.01)
                time.sleep(0.02)
                self.input_controller.hold_key(key_code1)
                
                # 阶段2: 短暂单向奔跑(让奔跑状态稳定)
                time.sleep(0.05)
                
                # 阶段3: 添加第二个方向键，形成斜向
                self.input_controller.hold_key(key_code2)
                
            elif method == "v3":
                # 方案3: 微妙错位双击 - 两个方向键微妙的时间差
                self.input_controller.press_key(key_code1, 0.01)
                time.sleep(0.003)  # 3毫秒错位
                self.input_controller.press_key(key_code2, 0.01)
                
                time.sleep(0.02)
                self.input_controller.hold_key(key_code1)
                time.sleep(0.001)  # 1毫秒错位
                self.input_controller.hold_key(key_code2)
                
            else:  # v4 - 传统同时按下
                # 方案4: 传统游戏风格 - 真正的同时按下
                self.input_controller.press_key(key_code1, 0.01)
                self.input_controller.press_key(key_code2, 0.01)
                
                time.sleep(0.02)
                self.input_controller.hold_key(key_code1)
                self.input_controller.hold_key(key_code2)
            
            # 保持移动指定时间
            time.sleep(duration)
            
            # 释放所有按键
            self._stop_all_movement()
            
            return True
            
        except Exception as e:
            print(f"流畅斜向奔跑失败: {e}")
            return False
    
    def _execute_smooth_diagonal_walk(self, key_code1, key_code2, duration):
        """执行流畅的斜向行走"""
        try:
            # 行走比较简单，直接同时按下即可
            self.input_controller.hold_key(key_code1)
            time.sleep(0.01)
            self.input_controller.hold_key(key_code2)
            
            # 保持移动指定时间
            time.sleep(duration)
            
            # 释放按键
            self.input_controller.release_key(key_code1)
            self.input_controller.release_key(key_code2)
            
            return True
            
        except Exception as e:
            print(f"斜向行走失败: {e}")
            return False
    
    def _stop_all_movement(self):
        """停止所有移动 - 释放所有方向键"""
        try:
            # 释放所有可能的方向键
            all_direction_keys = [37, 38, 39, 40]  # left, up, right, down
            for key_code in all_direction_keys:
                self.input_controller.release_key(key_code)
            
            print("✅ 已停止所有移动")
            
        except Exception as e:
            print(f"停止移动失败: {e}")
    
    def analyze_movement_strategy(self, dx, dy, distance, target_type="monster"):
        """分析移动策略 - 详细的角度和象限分析"""
        angle = self.calculate_angle(dx, dy)
        movement_keys = self.get_movement_for_angle(angle)
        
        # 象限判断
        quadrant = ""
        strategy = ""
        
        if 0 <= angle < 90:
            quadrant = "第一象限"
            if 15 <= angle <= 75:
                strategy = "斜向移动(右下)"
            else:
                strategy = "单向移动"
        elif 90 <= angle < 180:
            quadrant = "第二象限"
            if 105 <= angle <= 165:
                strategy = "斜向移动(左下)"
            else:
                strategy = "单向移动"
        elif 180 <= angle < 270:
            quadrant = "第三象限"
            if 195 <= angle <= 255:
                strategy = "斜向移动(左上)"
            else:
                strategy = "单向移动"
        else:  # 270 <= angle < 360
            quadrant = "第四象限"
            if 285 <= angle <= 345:
                strategy = "斜向移动(右上)"
            else:
                strategy = "单向移动"
        
        print(f"🧭 角度分析: {angle:.1f}° ({quadrant})")
        print(f"📐 移动策略: {strategy}")
        print(f"🎯 移动方向: {' + '.join(movement_keys)}")
        
        return movement_keys, strategy
    
    def move_to_target_with_smart_method(self, current_x, current_y, target_x, target_y, speed_percentage=100, target_type="monster"):
        """使用优化的象限角度判断的移动到目标位置"""
        try:
            # 计算移动向量
            dx = target_x - current_x
            dy = target_y - current_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            print(f"🧮 移动向量计算: dx={dx}, dy={dy}, distance={distance:.1f}")
            
            # 检查是否需要移动
            min_distance = 30
            if distance < min_distance:
                print(f"目标距离太近 ({distance:.1f}像素)，无需移动")
                return True
            
            # 手动进行角度和象限分析
            angle = self.calculate_angle(dx, dy)
            movement_keys = self.get_movement_for_angle(angle)
            
            # 详细的象限分析
            quadrant_info = ""
            strategy_info = ""
            
            if 0 <= angle < 90:
                quadrant_info = "第一象限(右下区域)"
                if 15 <= angle <= 75:
                    strategy_info = "斜向移动(右下)"
                else:
                    strategy_info = "单向移动(偏右)"
            elif 90 <= angle < 180:
                quadrant_info = "第二象限(左下区域)"
                if 105 <= angle <= 165:
                    strategy_info = "斜向移动(左下)"
                else:
                    strategy_info = "单向移动(偏下或偏左)"
            elif 180 <= angle < 270:
                quadrant_info = "第三象限(左上区域)"
                if 195 <= angle <= 255:
                    strategy_info = "斜向移动(左上)"
                else:
                    strategy_info = "单向移动(偏左或偏上)"
            else:  # 270 <= angle < 360
                quadrant_info = "第四象限(右上区域)"
                if 285 <= angle <= 345:
                    strategy_info = "斜向移动(右上)"
                else:
                    strategy_info = "单向移动(偏上或偏右)"
            
            print(f"🧭 角度分析: {angle:.1f}° ({quadrant_info})")
            print(f"📐 移动策略: {strategy_info}")
            print(f"🎯 移动方向: {' + '.join(movement_keys)}")
            
            # 使用修复后的移动时间计算
            move_time, use_run = self.speed_calculator.calculate_optimal_move_time(
                distance, speed_percentage, target_type
            )
            
            move_type = "奔跑" if use_run else "行走"
            print(f"📍 智能移动: ({current_x}, {current_y}) -> ({target_x}, {target_y})")
            print(f"📏 距离: {distance:.1f}像素, 移速: {speed_percentage}%, 目标: {target_type}")
            print(f"⏱️ 移动时间: {move_time:.3f}秒 ({move_type})")
            
            # 执行移动
            if len(movement_keys) == 1:
                # 单方向移动
                success = self.execute_single_direction_movement(
                    movement_keys[0], move_time, use_run
                )
                print(f"✅ 单向移动完成: {movement_keys[0]}")
            else:
                # 斜向移动 - 使用智能方案选择
                optimal_method = self.select_optimal_diagonal_method(dx, dy, distance)
                print(f"🧠 选择斜向移动方案: {optimal_method}")
                
                success = self.execute_diagonal_movement(
                    movement_keys, move_time, use_run, optimal_method
                )
                print(f"✅ 斜向移动完成: {' + '.join(movement_keys)}")
            
            return success
            
        except Exception as e:
            print(f"智能移动失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def select_optimal_diagonal_method(self, dx, dy, distance):
        """智能选择最佳斜向移动方案 - 基于象限角度优化"""
        abs_dx, abs_dy = abs(dx), abs(dy)
        angle = self.calculate_angle(dx, dy)
        
        if distance < 50:
            return "v2"  # 距离太近，使用默认方案
        
        # 根据角度范围选择最佳方案
        if 15 <= angle <= 75 or 195 <= angle <= 255:
            # 第一象限(右下)或第三象限(左上) - 主要是对角线移动
            if abs(abs_dx - abs_dy) < 50:  # 接近45度角
                return "v2"  # 预启动奔跑，最流畅
            else:
                return "v1"  # 快速响应
                
        elif 105 <= angle <= 165 or 285 <= angle <= 345:
            # 第二象限(左下)或第四象限(右上) - 主要是对角线移动
            if abs(abs_dx - abs_dy) < 50:  # 接近45度角
                return "v2"  # 预启动奔跑，最流畅
            else:
                return "v3"  # 精确控制
        else:
            # 其他角度，使用默认方案
            return "v2"  # 传统同时按下


class YaoqiAttacker:
    """妖气攻击器 - 完整的攻击系统"""
    
    def __init__(self, input_controller=None, yolo_model_path='models/best.pt', yolo_model=None):
        """初始化攻击器"""
        self.input_controller = input_controller or create_input_controller("默认")
        
        # 优先使用传入的YOLO模型，避免重复加载
        if yolo_model is not None:
            self.yolo_model = yolo_model
            print("YaoqiAttacker使用共享YOLO模型")
        else:
            # 只有在没有传入模型时才加载新模型
            try:
                self.yolo_model = YOLO(yolo_model_path)
                print("YaoqiAttacker独立加载YOLO模型")
            except Exception as e:
                print(f"YaoqiAttacker YOLO模型加载失败: {e}")
                self.yolo_model = None
        
        # 技能键位配置
        self.skill_keys = ['a', 's', 'd', 'f', 'g', 'h', 'q', 'w', 'e', 'r', 't', 'y']
        self.skill_key_map = {
            'a': 65, 's': 83, 'd': 68, 'f': 70, 'g': 71, 'h': 72,
            'q': 81, 'w': 87, 'e': 69, 'r': 82, 't': 84, 'x': 88, 'y': 89
        }
        
        # 游戏区域配置
        self.region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
        
        # 移动相关
        self.current_direction = None
        self.speed = 100  # 默认移动速度
        self.speed_detected = False
        self.current_map = None  # 当前地图
        self.map_confirmed = False  # 地图是否已确认
        
        # 技能区域配置
        self.skill_regions = self._get_skill_key_regions()
        
        # 初始化速度计算器
        self.speed_calculator = SpeedCalculator()
        
        # 初始化高级移动控制器（替换原有的移动控制器）
        try:
            from advanced_movement import AdvancedMovementController
            self.advanced_movement = AdvancedMovementController(self.input_controller)
            # 同时保持原有的movement_controller作为后备
            self.movement_controller = self.advanced_movement
            print("高级移动控制器初始化成功")
        except ImportError:
            print("高级移动模块未找到，使用基础移动控制器")
            self.advanced_movement = None
            # 保持原有的movement_controller
            self.movement_controller = AdvancedMovementController(self.input_controller)
        
        # 初始化EasyOCR（优先使用CPU提高稳定性）
        try:
            self.ocr_reader = easyocr.Reader(['en'], gpu=False)
            print("EasyOCR 使用 CPU 模式（稳定性优化）")
        except Exception as e:
            print(f"EasyOCR 初始化失败: {e}")
            self.ocr_reader = None
        
        print("YaoqiAttacker初始化完成")
    
    def _get_skill_key_regions(self):
        """获取技能键位区域"""
        SKILL_AREA_X1, SKILL_AREA_Y1 = 434, 534
        SKILL_AREA_X2, SKILL_AREA_Y2 = 619, 593
        
        skill_width = (SKILL_AREA_X2 - SKILL_AREA_X1) // 6
        skill_height = (SKILL_AREA_Y2 - SKILL_AREA_Y1) // 2
        convergence_y = 9
        convergence_x = 4

        skill_regions = {}
        row1_keys = ['q', 'w', 'e', 'r', 't', 'y']
        for i, key in enumerate(row1_keys):
            x1 = SKILL_AREA_X1 + i * skill_width + convergence_x
            y1 = SKILL_AREA_Y1 + convergence_y
            x2 = SKILL_AREA_X1 + (i + 1) * skill_width - convergence_x
            y2 = SKILL_AREA_Y1 + skill_height - convergence_y
            skill_regions[key] = (x1, y1, x2, y2)

        row2_keys = ['a', 's', 'd', 'f', 'g', 'h']
        for i, key in enumerate(row2_keys):
            x1 = SKILL_AREA_X1 + i * skill_width + convergence_x
            y1 = SKILL_AREA_Y1 + skill_height + convergence_y
            x2 = SKILL_AREA_X1 + (i + 1) * skill_width - convergence_x
            y2 = SKILL_AREA_Y2 - convergence_y
            skill_regions[key] = (x1, y1, x2, y2)

        return skill_regions
    
    def _is_skill_available(self, frame, region, target_color=(106, 230, 248), tolerance=20):
        """检查技能是否可用"""
        try:
            x1, y1, x2, y2 = region
            
            if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
                return False
                
            if y2 > frame.shape[0] or x2 > frame.shape[1]:
                return False
                
            skill_patch = frame[y1:y2, x1:x2]
            
            if skill_patch.size == 0:
                return False
                
            lower_color = np.array([max(0, c - tolerance) for c in target_color])
            upper_color = np.array([min(255, c + tolerance) for c in target_color])

            for py in range(skill_patch.shape[0]):
                for px in range(skill_patch.shape[1]):
                    bgr_value = skill_patch[py, px]
                    if (lower_color[0] <= bgr_value[0] <= upper_color[0] and
                        lower_color[1] <= bgr_value[1] <= upper_color[1] and
                        lower_color[2] <= bgr_value[2] <= upper_color[2]):
                        return True
            return False
        except Exception as e:
            print(f"技能检测错误: {e}")
            return False
    
    def get_available_skills(self, frame):
        """获取可用技能列表"""
        available_skills = []
        try:
            for skill_key in self.skill_keys:
                if skill_key in self.skill_regions:
                    region = self.skill_regions[skill_key]
                    if self._is_skill_available(frame, region):
                        available_skills.append(skill_key)
            print(f"可用技能: {available_skills}")
        except Exception as e:
            print(f"获取可用技能错误: {e}")
        return available_skills
    
    def get_positions(self, frame_rgb):
        """获取角色位置"""
        if self.yolo_model is not None:
            results = self.yolo_model.predict(frame_rgb)
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls)
                    if cls_id in result.names:
                        cls_name = result.names[cls_id]
                        # 兼容Intel模型和YOLO模型的chenghao检测
                        if cls_name in ['chenghao', 'cheng_hao']:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cheng_hao_x = x1 + (x2 - x1) // 2
                            cheng_hao_y = y1 + (y2 - y1) // 2 + 80
                            return cheng_hao_x, cheng_hao_y
        return None, None
    
    def calculate_distance(self, pos1, pos2):
        """计算两点之间的距离"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def face_monster(self, cheng_hao_x, monster_x):
        """面向怪物方向"""
        direction = 39 if monster_x > cheng_hao_x else 37
        direction_name = 'right' if direction == 39 else 'left'
        face_duration = 0.1
        
        print(f"🎯 面向怪物方向: {direction_name}")
        self.input_controller.press_key(direction, face_duration)
    
    def move_to_monster(self, monster_x, monster_y, cheng_hao_x, cheng_hao_y):
        """移动到怪物位置 - 使用计算时间的移动方法"""
        try:
            # 计算移动向量
            dx = monster_x - cheng_hao_x
            dy = monster_y - cheng_hao_y
            distance = math.sqrt(dx * dx + dy * dy)
            
            # 检查是否需要移动 - 使用固定的最小移动距离
            min_distance = 30  # 最小移动距离
            if distance < min_distance:
                print(f"目标距离太近 ({distance:.1f}像素)，无需移动")
                return True
            
            print(f"🎯 移动到怪物: 角色({cheng_hao_x}, {cheng_hao_y}) -> 怪物({monster_x}, {monster_y})")
            print(f"📏 移动距离: {distance:.1f}像素")
            
            # 使用高级移动控制器的智能移动方法
            success = self.movement_controller.move_to_target_with_smart_method(
                cheng_hao_x, cheng_hao_y, monster_x, monster_y, 
                speed_percentage=self.speed, target_type="monster"
            )
            
            if success:
                print("✅ 移动到怪物位置成功")
            else:
                print("⚠️ 移动失败，但继续攻击")
            
            return True
                
        except Exception as e:
            print(f"移动失败: {e}")
            return False
    
    def move_to_fixed_point(self, target_x=1060, target_y=369, direction=39):
        """移动到固定点 - 使用计算时间的移动方法"""
        try:
            print(f"🎯 开始移动到固定点: ({target_x}, {target_y})")
            
            # 获取当前角色位置
            with mss.mss() as sct:
                screenshot = sct.grab(self.region)
                frame_rgb = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2RGB)
                current_x, current_y = self.get_positions(frame_rgb)
            
            if current_x is not None and current_y is not None:
                # 使用高级移动控制器的智能移动方法
                success = self.movement_controller.move_to_target_with_smart_method(
                    current_x, current_y, target_x, target_y,
                    speed_percentage=self.speed, target_type="fixed"
                )
                
                if success:
                    print(f"✅ 智能移动到固定点成功")
                else:
                    print("⚠️ 智能移动失败，使用简单移动作为后备")
                    # 后备方案：简单移动
                    duration = 1.5
                    self.input_controller.press_key(direction, duration)
            else:
                print("⚠️ 未检测到角色位置，使用简单移动")
                # 后备方案：简单移动
                duration = 1.5
                self.input_controller.press_key(direction, duration)
            
            return True
            
        except Exception as e:
            print(f"移动到固定点失败: {e}")
            return False
    
    def detect_monsters(self, frame_rgb):
        """检测怪物"""
        monsters = []
        
        if self.yolo_model is not None:
            results = self.yolo_model.predict(frame_rgb)
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls)
                    if cls_id in result.names:
                        cls_name = result.names[cls_id]
                        if cls_name in ['monster', 'boss']:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            monster_x = x1 + (x2 - x1) // 2
                            monster_y = y1 + (y2 - y1) // 2
                            monsters.append({
                                'type': cls_name,
                                'x': monster_x,
                                'y': monster_y,
                                'bbox': (x1, y1, x2, y2)
                            })
        
        return monsters

    def find_nearest_monster(self, frame_rgb, character_x, character_y):
        """找到最近的怪物"""
        try:
            monsters = self.detect_monsters(frame_rgb)
            if not monsters:
                return None
            
            nearest_monster = None
            min_distance = float('inf')
            
            for monster in monsters:
                distance = math.sqrt((monster['x'] - character_x)**2 + (monster['y'] - character_y)**2)
                if distance < min_distance:
                    min_distance = distance
                    nearest_monster = monster
            
            if nearest_monster:
                print(f"🎯 找到最近怪物: 类型={nearest_monster['type']}, 位置=({nearest_monster['x']}, {nearest_monster['y']}), 距离={min_distance:.1f}px")
            
            return nearest_monster
            
        except Exception as e:
            print(f"寻找最近怪物失败: {e}")
            return None

    def attack_nearest_monster(self, frame):
        """攻击最近的怪物"""
        try:
            # 激活游戏窗口
            try:
                game_window = gw.getWindowsWithTitle("地下城与勇士：创新世纪")[0]
                game_window.activate()
            except Exception as e:
                print(f"激活窗口失败: {e}")
            
            # 获取角色位置
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cheng_hao_x, cheng_hao_y = self.get_positions(frame_rgb)
            
            if cheng_hao_x is None or cheng_hao_y is None:
                print("⚠️ 未检测到角色位置，但继续攻击")
                return self._execute_attack(frame, 500, 300, False)  # 使用默认位置
            
            # 找到最近的怪物
            nearest_monster = self.find_nearest_monster(frame_rgb, cheng_hao_x, cheng_hao_y)
            
            if nearest_monster:
                monster_x = nearest_monster['x']
                monster_y = nearest_monster['y']
                is_boss = nearest_monster['type'] == 'boss'
                
                print(f"🤖 角色位置: ({cheng_hao_x}, {cheng_hao_y})")
                print(f"📍 最近怪物: ({monster_x}, {monster_y})")
                
                distance = self.calculate_distance((cheng_hao_x, cheng_hao_y), (monster_x, monster_y))
                print(f"📏 距离: {distance:.1f}像素")
                
                if distance > 50:
                    success = self.move_to_monster(monster_x, monster_y, cheng_hao_x, cheng_hao_y)
                    if not success:
                        print("⚠️ 移动失败，但继续攻击")
                
                return self._execute_attack(frame, monster_x, monster_y, is_boss)
            else:
                print("⚠️ 未找到怪物，执行默认攻击")
                return self._execute_attack(frame, 500, 300, False)
            
        except Exception as e:
            print(f"攻击最近怪物失败: {e}")
            return False
    
    def attack_monster(self, frame, monster_x=None, monster_y=None, is_boss=False):
        """攻击怪物 - 优先攻击最近怪物"""
        if monster_x is None or monster_y is None:
            # 如果没有指定怪物位置，自动寻找最近的怪物
            return self.attack_nearest_monster(frame)
        else:
            # 攻击指定位置的怪物（保持向后兼容）
            try:
                game_window = gw.getWindowsWithTitle("地下城与勇士：创新世纪")[0]
                game_window.activate()
            except Exception as e:
                print(f"激活窗口失败: {e}")
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cheng_hao_x, cheng_hao_y = self.get_positions(frame_rgb)
            
            if cheng_hao_x is not None and cheng_hao_y is not None:
                print(f"🤖 角色位置: ({cheng_hao_x}, {cheng_hao_y})")
                print(f"📍 目标怪物: ({monster_x}, {monster_y})")
                
                distance = self.calculate_distance((cheng_hao_x, cheng_hao_y), (monster_x, monster_y))
                print(f"📏 距离: {distance:.1f}像素")
                
                if distance > 50:
                    self.move_to_monster(monster_x, monster_y, cheng_hao_x, cheng_hao_y)
            else:
                print("⚠️ 未检测到角色位置，但继续攻击")
            
            return self._execute_attack(frame, monster_x, monster_y, is_boss)  # 攻击指定位置的怪物
    
    def _execute_attack(self, frame, monster_x, monster_y, is_boss=False):
        """执行攻击循环"""
        with mss.mss() as sct:
            attack_rounds = 0
            max_attack_rounds = 10  # 最大攻击轮数
            
            while attack_rounds < max_attack_rounds:
                attack_rounds += 1
                
                # 获取当前截图
                screenshot = sct.grab(self.region)
                frame_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
                frame_rgb = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2RGB)
                
                # 检查角色位置
                cheng_hao_x, cheng_hao_y = self.get_positions(frame_rgb)
                if cheng_hao_x is not None and cheng_hao_y is not None:
                    current_distance = self.calculate_distance((cheng_hao_x, cheng_hao_y), (monster_x, monster_y))
                    self.face_monster(cheng_hao_x, monster_x)
                    print(f"🤖 角色位置: ({cheng_hao_x}, {cheng_hao_y}), 距离: {current_distance:.1f}像素")
                else:
                    print("未检测到角色位置，默认攻击")
                
                # 获取可用技能
                available_skills = self.get_available_skills(frame_bgr)
                
                # 释放技能
                skill_count = random.randint(2, 3)
                print(f"计划释放 {skill_count} 个技能")
                used_skills = []
                
                for i in range(skill_count):
                    if available_skills:
                        skill_key = random.choice(available_skills)
                        available_skills.remove(skill_key)
                        used_skills.append(skill_key)
                    else:
                        skill_key = random.choice(self.skill_keys)
                    
                    key_code = self.skill_key_map[skill_key]
                    press_duration = random.uniform(0.1311, 0.1511)
                    sleep_duration = random.uniform(0.1011, 0.1511)
                    
                    print(f"⚔️ 释放技能 {skill_key} (第 {i+1}/{skill_count})")
                    self.input_controller.press_key(key_code, press_duration)
                    time.sleep(sleep_duration)
                
                # 普通攻击
                x_press_duration = random.uniform(0.01011, 0.03011)
                x_sleep_duration = random.uniform(0.01011, 0.03011)
                print("🗡️ 执行普通攻击 X")
                self.input_controller.press_key(88, x_press_duration)  # X键
                time.sleep(x_sleep_duration)
                
                # 检查怪物是否还存在
                current_frame_rgb = cv2.cvtColor(np.array(sct.grab(self.region)), cv2.COLOR_BGRA2RGB)
                monster_still_exists = self._check_monster_exists(current_frame_rgb, monster_x, monster_y, is_boss)
                
                if not monster_still_exists:
                    print("怪物已消失，停止攻击")
                    return True
                
                # 短暂休息
                time.sleep(0.5)
            
            print(f"攻击轮数达到上限({max_attack_rounds})，停止攻击")
            return False
    
    def _check_monster_exists(self, frame_rgb, monster_x, monster_y, is_boss=False):
        """检查怪物是否还存在"""
        if self.yolo_model is not None:
            results = self.yolo_model.predict(frame_rgb)
            monster_type = 'boss' if is_boss else 'monster'
            
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls)
                    if cls_id in result.names and result.names[cls_id] == monster_type:
                        mx1, my1, mx2, my2 = map(int, box.xyxy[0])
                        detected_x = mx1 + (mx2 - mx1) // 2
                        detected_y = my1 + (my2 - my1) // 2
                        
                        # 检查是否是同一个怪物（位置相近）
                        if abs(monster_x - detected_x) < 100 and abs(monster_y - detected_y) < 100:
                            return True
        
        return False


if __name__ == "__main__":
    # 测试代码
    print("Actions 模块测试完成")
    attacker = YaoqiAttacker()
    movement = AdvancedMovementController()
    calculator = SpeedCalculator()
    print("所有组件初始化完成")