"""
yaoqi.py - 妖气追踪完整模块
整合了导航、跑图逻辑和地图检测功能
"""

import cv2
import numpy as np
import mss
import time
import os
import sys
import math
import threading
import pygetwindow as gw
from ultralytics import YOLO
from input_controllers import create_input_controller
from actions import YaoqiAttacker, AdvancedMovementController, SpeedCalculator
import random
import re
import inspect
from memory_manager import memory_manager, optimize_memory


def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class KeyMapper:
    @staticmethod
    def get_key_code(key):
        """获取键码映射"""
        key_map = {
            'N': 78, 'ESC': 27, 'ESCAPE': 27, 'ENTER': 13, 'SPACE': 32,
            'LEFT': 37, 'UP': 38, 'RIGHT': 39, 'DOWN': 40,
            'F1': 112, 'F2': 113, 'F3': 114, 'F4': 115, 'F5': 116,
            'F6': 117, 'F7': 118, 'F8': 119, 'F9': 120, 'F10': 121,
            'F11': 122, 'F12': 123,
        }
        return key_map.get(key.upper(), ord(key.upper()))


def detect_objects_template(frame, templates, threshold=0.7):
    """使用模板匹配检测对象"""
    detected = {}
    if frame is None or frame.size == 0:
        return detected
    
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
    
    for name, template in templates.items():
        if template is None:
            continue
            
        try:
            # 检查尺寸兼容性
            if (gray_frame.shape[0] < template.shape[0] or 
                gray_frame.shape[1] < template.shape[1]):
                continue
                
            result = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)
            
            for pt in zip(*locations[::-1]):
                x1, y1 = pt
                x2, y2 = x1 + template.shape[1], y1 + template.shape[0]
                detected[name] = (x1, y1, x2, y2)
                break  # 只取第一个匹配结果
                
        except Exception as e:
            print(f"模板匹配错误 {name}: {e}")
            continue
    
    return detected


def activate_window(game_window):
    """激活游戏窗口"""
    try:
        game_window.activate()
        time.sleep(0.1)
    except Exception as e:
        print(f"激活窗口失败: {e}")


def click_position(x, y, game_window):
    """点击指定位置"""
    try:
        # 这里需要使用input_controller，暂时占位
        print(f"点击位置: ({x}, {y})")
        # 实际实现中需要传入input_controller
    except Exception as e:
        print(f"点击失败: {e}")


class YaoqiAutomator:
    """妖气追踪自动化类 - 整合版本"""
    
    def __init__(self, input_controller=None):
        """初始化妖气追踪自动化模块"""
        self.input_controller = input_controller or create_input_controller("默认")
        self.stop_event = None
        self.log = print
        
        # 游戏配置
        self.game_title = "地下城与勇士：创新世纪"
        self.confidence_threshold = 0.05
        
        # 线程安全锁
        self._model_lock = threading.Lock()
        self._combat_lock = threading.Lock()
        
        # 初始化YOLO模型（共享给战斗系统使用）
        try:
            self.yolo_model = YOLO('models/best.pt')
            # 优化YOLO模型设置
            self.yolo_model.overrides['verbose'] = False  # 减少日志输出
            self.yolo_model.overrides['max_det'] = 30  # 进一步限制最大检测数量
            self.yolo_model.overrides['device'] = 'cpu'  # 强制使用CPU提高稳定性
            print("YaoqiAutomator YOLO模型加载成功（CPU模式，已优化）")
        except Exception as e:
            print(f"YaoqiAutomator YOLO模型加载失败: {e}")
            self.yolo_model = None
        
        # 初始化复杂攻击系统（延迟初始化避免资源冲突）
        self.attacker = None
        self.movement_controller = None
        self.speed_calculator = None
        self._combat_initialized = False
        
        # 初始化EasyOCR用于速度识别（优先使用CPU提高稳定性）
        try:
            import easyocr
            # 优先使用CPU模式，提高稳定性
            self.ocr_reader = easyocr.Reader(['en'], gpu=False)
            print("EasyOCR 使用 CPU 模式（稳定性优化）")
        except ImportError:
            print("EasyOCR 未安装，速度识别功能将不可用")
            self.ocr_reader = None
        except Exception as e:
            print(f"EasyOCR 初始化失败: {e}")
            self.ocr_reader = None
        
        # 加载模板
        self.templates = {}
        self.load_templates()
        
        # 小地图区域配置
        self.MAP_X1, self.MAP_Y1, self.MAP_X2, self.MAP_Y2 = 929, 53, 1059, 108
        
        # 状态变量
        self.current_role = 0
        self.total_roles = 1
        
        # 速度检测相关状态
        self.speed_detected = False
        self.character_switched = False
        self.first_ditu_detected = False
        
        # 地图状态管理
        self.current_confirmed_map = None  # 当前确认的地图
        self.map_locked = False  # 地图是否锁定（专注模式）
        self.fanpai_detected = False  # 是否检测到翻牌
        
        # 地图逻辑配置
        self.map_logic_config = self._init_map_logic()
        
        print("YaoqiAutomator初始化完成（集成复杂攻击系统）")
    
    def _init_combat_systems(self):
        """线程安全初始化战斗系统"""
        if self._combat_initialized:
            return True
            
        with self._combat_lock:
            if self._combat_initialized:  # 双重检查
                return True
                
            try:
                # 只初始化攻击器，避免重复初始化引起的内存问题
                if self.attacker is None and self.yolo_model is not None:
                    # 传入共享的YOLO模型和input_controller，避免重复创建
                    self.attacker = YaoqiAttacker(self.input_controller, yolo_model=self.yolo_model)
                    print("✅ 攻击器初始化完成（共享YOLO模型）")
                
                # 简化系统，暂时不初始化复杂的移动控制器
                if self.movement_controller is None:
                    self.movement_controller = AdvancedMovementController(self.input_controller)
                    print("✅ 移动控制器初始化完成")
                    
                if self.speed_calculator is None:
                    self.speed_calculator = SpeedCalculator()
                    print("✅ 速度计算器初始化完成")
                
                self._combat_initialized = True
                return True
                
            except Exception as e:
                print(f"❌ 战斗系统初始化失败: {e}")
                # 创建简化版本避免完全失败
                self.attacker = None
                self.movement_controller = None 
                self.speed_calculator = None
                return False
    
    def load_templates(self):
        """加载所需的模板图片"""
        template_files = {
            'sailiya': 'image/sailiya.png',
            'shenyuan': 'image/shenyuan.png',
            'yaoqizhuizongxuanze': 'image/yaoqizhuizongxuanze.png',
            'yaoqizhuizongpindao': 'image/yaoqizhuizongpindao.png',
            'fanpai': 'image/fanpai.png',
            'youjianxiang': 'image/youjianxiang.png',
            'ditu1': 'image/ditu1.png',
            'ditu2': 'image/ditu2.png', 
            'ditu3': 'image/ditu3.png',
            'ditu4': 'image/ditu4.png',
            'ditu5': 'image/ditu5.png',
            'ditu6': 'image/ditu6.png',
            'ditu7': 'image/ditu7.png',
            'ditu8': 'image/ditu8.png',
            'ditu9': 'image/ditu9.png',
            'ditu10': 'image/ditu10.png',
            'ditu11': 'image/ditu11.png',
            'ditu12': 'image/ditu12.png',
        }
        
        for name, path in template_files.items():
            template_path = resource_path(path)
            if os.path.exists(template_path):
                template = cv2.imread(template_path, 0)
                if template is not None:
                    self.templates[name] = template
                    h, w = template.shape
                    print(f"模板加载成功: {name}, 尺寸: {w}x{h}")
                else:
                    print(f"模板加载失败: {name}")
            else:
                print(f"模板文件不存在: {template_path}")
    
    def _init_map_logic(self):
        """初始化地图逻辑配置 - 现在使用详细的跑图函数"""
        return {
            'ditu1': self.run_ditu1,
            'ditu2': self.run_ditu2,
            'ditu3': self.run_ditu3,
            'ditu4': self.run_ditu4,
            'ditu5': self.run_ditu5,
            'ditu6': self.run_ditu6,
            'ditu7': self.run_ditu7,
            'ditu8': self.run_ditu8,
            'ditu9': self.run_ditu9,
            'ditu10': self.run_ditu10,
            'ditu11': self.run_ditu11,
            'ditu12': self.run_ditu12
        }
    
    def detect_template(self, frame, template, threshold=0.7):
        """检测模板匹配"""
        if template is None:
            return []
        
        # 检查尺寸兼容性
        if (frame.shape[0] < template.shape[0] or 
            frame.shape[1] < template.shape[1]):
            print(f"⚠️ 模板尺寸({template.shape[1]}x{template.shape[0]}) 大于搜索区域({frame.shape[1]}x{frame.shape[0]})，跳过匹配")
            return []
        
        try:
            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)
            
            matches = []
            for pt in zip(*locations[::-1]):
                matches.append((pt[0], pt[1], pt[0] + template.shape[1], pt[1] + template.shape[0]))
            
            return matches
        except Exception as e:
            print(f"模板匹配错误: {e}")
            return []
    
    def detect_current_map(self, frame):
        """检测当前地图 - 在全屏幕中检测地图模板"""
        # 如果地图已锁定且未检测到翻牌，直接返回当前确认的地图
        if self.map_locked and self.current_confirmed_map and not self.fanpai_detected:
            return self.current_confirmed_map
        
        # 转换为灰度图像，在整个游戏窗口中检测
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        for map_name in ['ditu1', 'ditu2', 'ditu3', 'ditu4', 'ditu5', 'ditu6', 
                        'ditu7', 'ditu8', 'ditu9', 'ditu10', 'ditu11', 'ditu12']:
            if map_name in self.templates:
                template = self.templates[map_name]
                matches = self.detect_template(gray_frame, template, 0.8)
                if matches:
                    print(f"✅ 检测到地图: {map_name}")
                    
                    # 如果是新检测到的地图，锁定它
                    if not self.map_locked or self.current_confirmed_map != map_name:
                        self.current_confirmed_map = map_name
                        self.map_locked = True
                        self.fanpai_detected = False
                        print(f"🔒 地图已锁定: {map_name}，进入专注模式")
                    
                    return map_name
        
        return None
    
    def detect_minimap_blinking(self, frame):
        """检测小地图闪烁 - 增强版"""
        minimap_region = frame[self.MAP_Y1:self.MAP_Y2, self.MAP_X1:self.MAP_X2]
        
        # 检查ROI有效性
        if minimap_region.size == 0 or np.mean(minimap_region) < 10:
            print("警告：小地图ROI无效或黑屏，跳过检测")
            return False
        
        hsv = cv2.cvtColor(minimap_region, cv2.COLOR_BGR2HSV)
        
        # 检测红色闪烁区域
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = mask1 + mask2
        
        red_pixels = np.sum(red_mask > 0)
        total_pixels = minimap_region.shape[0] * minimap_region.shape[1]
        red_ratio = red_pixels / total_pixels
        
        return red_ratio > 0.1
    
    def detect_minimap_advanced(self, frame):
        """高级小地图检测 - 参考main3.py的detect_blinking函数"""
        roi = frame[self.MAP_Y1:self.MAP_Y2, self.MAP_X1:self.MAP_X2]
        
        # 检查ROI有效性
        if roi.size == 0 or np.mean(roi) < 10:
            print("警告：小地图ROI无效或黑屏，跳过检测")
            return None, {}, None, []
        
        # 初始化状态
        grid_height = (self.MAP_Y2 - self.MAP_Y1) // 3
        grid_width = (self.MAP_X2 - self.MAP_X1) // 7
        door_states = {}
        character_grid = None
        boss_grid = None
        
        # 颜色检测设置
        target_bgr = np.array([17, 135, 94])  # 门的颜色
        bgr_tolerance = 20
        lower_bgr = np.clip(target_bgr - bgr_tolerance, 0, 255)
        upper_bgr = np.clip(target_bgr + bgr_tolerance, 0, 255)
        
        boss_bgr = np.array([2, 80, 232])  # Boss的颜色
        boss_tolerance = 30
        lower_boss_bgr = np.clip(boss_bgr - boss_tolerance, 0, 255)
        upper_boss_bgr = np.clip(boss_bgr + boss_tolerance, 0, 255)
        
        # 角色检测（蓝色6x10像素）
        hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_blue = np.array([90, 150, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv_roi, lower_blue, upper_blue)
        
        # 遍历3x7网格检测
        for row in range(3):
            for col in range(7):
                x = col * grid_width
                y = row * grid_height
                grid_name = f"{row + 1}-{col + 1}"
                
                # 检测区域边界
                detect_x_start = x + 2
                detect_y_start = y + 2
                detect_x_end = x + grid_width - 2
                detect_y_end = y + grid_height - 2
                
                # 角色检测（蓝色6x10像素）
                patch_blue_mask = blue_mask[detect_y_start:detect_y_end, detect_x_start:detect_x_end]
                contours, _ = cv2.findContours(patch_blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    bx, by, bw, bh = cv2.boundingRect(contour)
                    if bw == 6 and bh == 10:
                        character_grid = grid_name
                        print(f"📍 小地图检测到角色位置: {character_grid}")
                        break
                
                # 网格区域提取
                grid_patch = roi[detect_y_start:detect_y_end, detect_x_start:detect_x_end]
                
                # Boss检测（红色8-12x8-12像素）
                boss_mask = cv2.inRange(grid_patch, lower_boss_bgr, upper_boss_bgr)
                contours, _ = cv2.findContours(boss_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    bx, by, bw, bh = cv2.boundingRect(contour)
                    if 8 <= bw <= 12 and 8 <= bh <= 12:
                        boss_grid = grid_name
                        print(f"👹 小地图检测到Boss位置: {boss_grid}")
                        break
                
                # 门状态检测
                door_mask = cv2.inRange(grid_patch, lower_bgr, upper_bgr)
                door_pixels = np.sum(door_mask)
                door_open = door_pixels > 100
                door_states[grid_name] = 'open' if door_open else 'closed'
                
                # 详细的门状态检测日志（每10次检测打印一次，避免日志过多）
                if hasattr(self, '_door_log_counter'):
                    self._door_log_counter += 1
                else:
                    self._door_log_counter = 1
                    
                if self._door_log_counter % 100 == 0:  # 每100次检测打印一次门状态
                    if door_open:
                        print(f"🚪 检测到门开启: {grid_name}, 像素数: {door_pixels}")
                elif door_open:
                    # 如果检测到门开启，立即打印（不受计数器限制）
                    print(f"🚪 门开启: {grid_name}, 像素数: {door_pixels}")
        
        # 门状态汇总（每50次检测打印一次）
        if hasattr(self, '_summary_counter'):
            self._summary_counter += 1
        else:
            self._summary_counter = 1
            
        if self._summary_counter % 50 == 0:
            open_doors = [k for k, v in door_states.items() if v == 'open']
            if open_doors:
                print(f"🗺️ 小地图状态汇总: 角色={character_grid}, Boss={boss_grid}, 开门={', '.join(open_doors)}")
        
        return character_grid, door_states, boss_grid, []
    
    def detect_fanpai(self, frame):
        """检测翻牌界面"""
        try:
            # 检查是否有fanpai模板
            if 'fanpai' not in self.templates:
                return False
            
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            template = self.templates['fanpai']
            matches = self.detect_template(gray_frame, template, 0.7)
            
            if matches:
                print("🎴 检测到翻牌界面！重置地图状态")
                return True
            
            return False
        except Exception as e:
            print(f"翻牌检测错误: {e}")
            return False
    
    def reset_map_state(self):
        """重置地图状态（检测到翻牌时调用）"""
        self.current_confirmed_map = None
        self.map_locked = False
        self.fanpai_detected = True
        self.speed_detected = False  # 重置速度检测状态
        self.first_ditu_detected = False
        print("🔓 地图状态已重置，退出专注模式")
    
    def execute_focused_map_logic(self, current_map, game_window, character_grid, door_states, boss_grid):
        """专注模式下执行地图逻辑"""
        try:
            if current_map not in self.map_logic_config:
                print(f"未找到地图 {current_map} 的逻辑配置")
                return
            
            # 确保战斗系统已初始化
            if not self._combat_initialized:
                print("🔄 初始化战斗系统...")
                if not self._init_combat_systems():
                    print("⚠️ 战斗系统初始化失败，使用简化逻辑")
                    # 即使战斗系统失败，也要继续执行地图逻辑
            
            # 获取当前帧进行YOLO检测
            with mss.mss() as sct:
                region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
                screenshot = sct.grab(region)
                frame_rgb = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2RGB)
            
            # 获取角色位置和状态信息
            chenghao_box = None
            monsters = []
            skill_availability = {}
            
            # 使用YOLO检测角色位置
            if self.yolo_model is not None:
                results = self.yolo_model.predict(frame_rgb, verbose=False)
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls)
                        if cls_id in result.names:
                            cls_name = result.names[cls_id]
                            if cls_name == 'chenghao':
                                chenghao_box = list(map(int, box.xyxy[0]))
                                break
            
            # 检测怪物 - 添加安全检查
            if self.attacker is not None:
                monsters = self.attacker.detect_monsters(frame_rgb)
            else:
                print("⚠️ 攻击器未初始化，跳过怪物检测")
                monsters = []
            
            # 获取对应的地图逻辑函数
            map_logic_func = self.map_logic_config[current_map]
            
            # 专注执行地图逻辑
            if callable(map_logic_func):
                print(f"🎯 专注执行 {current_map} 的跑图逻辑")
                map_logic_func(character_grid, door_states, game_window, chenghao_box, monsters, skill_availability)
            else:
                print(f"地图 {current_map} 的逻辑配置不是可调用函数")
                
        except Exception as e:
            print(f"专注模式执行 {current_map} 地图逻辑时出错: {e}")
    
    def process_yaoqi_map_logic(self, current_map, game_window):
        """处理妖气地图逻辑 - 使用详细的跑图函数"""
        if current_map not in self.map_logic_config:
            print(f"未找到地图 {current_map} 的逻辑配置")
            return
        
        # 确保战斗系统已初始化
        if not self._combat_initialized:
            print("🔄 初始化战斗系统...")
            if not self._init_combat_systems():
                print("⚠️ 战斗系统初始化失败，使用简化逻辑")
        
        try:
            # 检测到ditu地图时的速度检测逻辑
            if not self.first_ditu_detected:
                print(f"🎯 首次检测到ditu地图: {current_map}")
                self.first_ditu_detected = True
                self.trigger_speed_detection(game_window)
            elif self.character_switched and not self.speed_detected:
                print(f"🔄 角色已切换，重新进行速度检测")
                self.trigger_speed_detection(game_window)
            
            # 获取当前帧进行YOLO检测
            with mss.mss() as sct:
                region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
                screenshot = sct.grab(region)
                frame_rgb = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2RGB)
            
            # 获取角色位置和状态信息
            chenghao_box = None
            monsters = []
            skill_availability = {}
            
            # 使用YOLO检测角色位置
            if self.yolo_model is not None:
                results = self.yolo_model.predict(frame_rgb)
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls)
                        if cls_id in result.names:
                            cls_name = result.names[cls_id]
                            if cls_name == 'chenghao':
                                chenghao_box = list(map(int, box.xyxy[0]))
                                print(f"✅ 检测到角色位置: {chenghao_box}")
                                break
            
            # 检测怪物 - 添加安全检查
            if self.attacker is not None:
                monsters = self.attacker.detect_monsters(frame_rgb)
                print(f"🎯 检测到 {len(monsters)} 个怪物")
            else:
                print("⚠️ 攻击器未初始化，跳过怪物检测")
                monsters = []
            
            # 简化的门状态（实际应该通过小地图检测）
            door_states = {f"{row}-{col}": "open" for row in range(1, 4) for col in range(1, 8)}
            
            # 计算角色网格位置
            character_grid = self.get_character_grid(chenghao_box)
            print(f"📍 角色网格位置: {character_grid}")
            
            # 获取对应的地图逻辑函数
            map_logic_func = self.map_logic_config[current_map]
            
            # 执行地图逻辑
            if callable(map_logic_func):
                print(f"🎮 执行 {current_map} 的详细跑图逻辑")
                map_logic_func(character_grid, door_states, game_window, chenghao_box, monsters, skill_availability)
            else:
                print(f"地图 {current_map} 的逻辑配置不是可调用函数")
                
        except Exception as e:
            print(f"处理 {current_map} 地图逻辑时出错: {e}")
            # 如果详细逻辑失败，使用简单的点击逻辑作为备用
            self.simple_map_logic(current_map, game_window)
    
    def simple_map_logic(self, current_map, game_window):
        """简单的地图逻辑备用方案"""
        simple_actions = {
            'ditu1': [(967, 432)], 'ditu2': [(967, 432)], 'ditu3': [(967, 432)],
            'ditu4': [(967, 301)], 'ditu5': [(967, 301)], 'ditu6': [(967, 301)],
            'ditu7': [(967, 170)], 'ditu8': [(967, 170)], 'ditu9': [(967, 170)],
            'ditu10': [(500, 300)], 'ditu11': [(500, 300)], 'ditu12': [(500, 300)]
        }
        
        if current_map in simple_actions:
            for x, y in simple_actions[current_map]:
                print(f"简单逻辑：在地图 {current_map} 点击 ({x}, {y})")
                try:
                    game_window.activate()
                except:
                    pass
                self.input_controller.click(x, y)
                time.sleep(2)
    
    def navigate_to_yaoqi_map(self, frame, game_window):
        """导航到妖气追踪地图"""
        try:
            # 激活游戏窗口
            game_window.activate()
            
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 检测塞利亚房间
            if 'sailiya' in self.templates:
                matches = self.detect_template(gray_frame, self.templates['sailiya'])
                if matches:
                    print("检测到塞利亚房间，导航到妖气追踪")
                    
                    # 点击妖气追踪选择
                    if 'yaoqizhuizongxuanze' in self.templates:
                        yaoqi_matches = self.detect_template(gray_frame, self.templates['yaoqizhuizongxuanze'])
                        if yaoqi_matches:
                            x1, y1, x2, y2 = yaoqi_matches[0]
                            center_x = x1 + (x2 - x1) // 2
                            center_y = y1 + (y2 - y1) // 2
                            self.input_controller.click(center_x, center_y)
                            time.sleep(2)
                            return True
            
            # 检测妖气追踪频道
            if 'yaoqizhuizongpindao' in self.templates:
                matches = self.detect_template(gray_frame, self.templates['yaoqizhuizongpindao'])
                if matches:
                    print("检测到妖气追踪频道")
                    x1, y1, x2, y2 = matches[0]
                    center_x = x1 + (x2 - x1) // 2 
                    center_y = y1 + (y2 - y1) // 2
                    self.input_controller.click(center_x, center_y)
                    time.sleep(2)
                    return True
                    
        except Exception as e:
            print(f"导航过程中发生错误: {e}")
            
        return False
    
    def navigate_to_map_advanced(self, game_window, target_map="yaoqi_tracking"):
        """高级导航函数 - 步骤化导航逻辑"""
        # 确保模板已加载
        if not self.templates:
            print("模板未加载，无法导航")
            return False
        
        # 修复click_position函数，使其使用input_controller
        def click_position_fixed(x, y, game_window):
            try:
                activate_window(game_window)
                self.input_controller.click(x, y)
                time.sleep(0.1)
            except Exception as e:
                print(f"点击失败: {e}")
        
        navigation_steps = {
            "yaoqi_tracking": [
                {
                    "detect": "sailiya", 
                    "action": lambda: (
                        print("检测到塞利亚，按N键打开任务面板"), 
                        activate_window(game_window), 
                        self.input_controller.press_key(KeyMapper.get_key_code('N'), 0.05), 
                        time.sleep(0.5)
                    )
                },
                {
                    "detect": "yaoqizhuizongpindao", 
                    "action": lambda x1, y1, x2, y2: (
                        print(f"检测到妖气追踪频道，点击 ({(x1 + x2) // 2}, {(y1 + y2) // 2})"), 
                        click_position_fixed((x1 + x2) // 2, (y1 + y2) // 2, game_window)
                    )
                },
                {
                    "wait": 18, 
                    "detect_absence": "yaoqizhuizongpindao", 
                    "action": lambda: (
                        time.sleep(2), 
                        activate_window(game_window), 
                        self.input_controller.press_key(KeyMapper.get_key_code('N'), 0.05), 
                        time.sleep(1), 
                        click_position_fixed(359, 148, game_window)
                    )
                },
                {
                    "wait": 19, 
                    "detect": "yaoqizhuizongxuanze", 
                    "action": lambda x1, y1, x2, y2: (
                        print(f"检测到妖气追踪选择，双击 (580, 354)"), 
                        click_position_fixed(580, 354, game_window), 
                        time.sleep(0.2), 
                        click_position_fixed(580, 354, game_window), 
                        time.sleep(2)
                    )
                },
                {
                    "fail_action": lambda: (
                        activate_window(game_window), 
                        self.input_controller.press_key(KeyMapper.get_key_code('ESC'), 0.05), 
                        click_position_fixed(818, 541, game_window), 
                        time.sleep(1), 
                        click_position_fixed(504, 336, game_window), 
                        time.sleep(2)
                    )
                }
            ],
        }

        if target_map not in navigation_steps:
            print(f"未定义的导航目标: {target_map}")
            return False

        steps = navigation_steps[target_map]
        with mss.mss() as sct:
            region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
            frame_count = 0

            for step in steps:
                print(f"执行步骤: {step}")
                if "wait" in step:
                    start_time = time.time()
                    while time.time() - start_time < step["wait"]:
                        detected = {}
                        try:
                            screenshot = sct.grab(region)
                            frame = np.array(screenshot)
                            if frame is None or frame.size == 0:
                                print("警告：截图为空，跳过此次检测")
                                time.sleep(0.1)
                                continue
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                            detected = detect_objects_template(frame, self.templates)
                        except Exception as e:
                            print(f"截图或检测错误: {e}")
                            time.sleep(0.1)
                            continue
                        print(f"检测到的对象: {detected}")

                        if "detect" in step and step["detect"] in detected:
                            x1, y1, x2, y2 = detected[step["detect"]]
                            print(f"检测到 {step['detect']}，执行动作")
                            try:
                                step["action"](x1, y1, x2, y2)
                                if step["detect"] == "yaoqizhuizongxuanze":
                                    print("等待验证导航是否成功（检测地图标识）")
                                    verify_start_time = time.time()
                                    while time.time() - verify_start_time < 3:
                                        try:
                                            screenshot = sct.grab(region)
                                            frame = np.array(screenshot)
                                            if frame is not None and frame.size > 0:
                                                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                                                verify_detected = detect_objects_template(frame, self.templates)
                                                print(f"验证检测到的对象: {verify_detected}")
                                                # 检查是否检测到了任何地图标识
                                                map_detected = any(key in verify_detected for key in ["ditu1", "ditu2", "ditu3", "ditu4", "ditu5", "ditu6", "ditu7", "ditu8", "ditu9", "ditu10", "ditu11", "ditu12"])
                                                if map_detected:
                                                    detected_maps = [key for key in verify_detected.keys() if key.startswith("ditu")]
                                                    print(f"检测到地图标识: {detected_maps}，导航成功")
                                                    return True
                                            time.sleep(0.1)
                                        except Exception as e:
                                            print(f"验证检测错误: {e}")
                                            time.sleep(0.1)
                                    print("未检测到地图标识，导航失败")
                                    if "fail_action" in steps[-1]:
                                        try:
                                            steps[-1]["fail_action"]()
                                            print("执行最后的失败操作")
                                        except Exception as e:
                                            print(f"执行最后的失败操作时出错: {e}")
                                    return False
                                break
                            except Exception as e:
                                print(f"执行动作失败: {e}")
                                return False
                        elif "detect_absence" in step and step["detect_absence"] not in detected:
                            print(f"未检测到 {step['detect_absence']}，执行动作")
                            try:
                                step["action"]()
                                break
                            except Exception as e:
                                print(f"执行动作失败: {e}")
                                return False
                        time.sleep(0.1)
                    else:
                        if "fail_action" in step:
                            print(f"导航超时，执行失败操作")
                            try:
                                step["fail_action"]()
                                print("失败操作执行完成")
                                return False
                            except Exception as e:
                                print(f"执行失败操作时出错: {e}")
                                return False
                        continue

                elif "detect" in step:
                    while True:
                        frame_count += 1
                        detected = {}
                        try:
                            screenshot = sct.grab(region)
                            frame = np.array(screenshot)
                            if frame is None or frame.size == 0:
                                print("警告：截图为空，跳过此次检测")
                                time.sleep(0.1)
                                continue
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                            if frame_count % 3 == 0:
                                detected = detect_objects_template(frame, self.templates)
                        except Exception as e:
                            print(f"截图或检测错误: {e}")
                            time.sleep(0.1)
                            continue
                        
                        if frame_count % 3 == 0:
                            print(f"检测到的对象: {detected}")
                        
                        if step["detect"] in detected:
                            if "action" in step and callable(step["action"]):
                                try:
                                    # 检查lambda函数的参数数量
                                    try:
                                        # 尝试检查函数签名
                                        import inspect
                                        sig = inspect.signature(step["action"])
                                        param_count = len(sig.parameters)
                                    except:
                                        # 如果检查失败，通过函数名猜测
                                        param_count = 0 if "sailiya" in step.get("detect", "") else 4
                                    
                                    if param_count >= 4:  # 需要坐标参数
                                        x1, y1, x2, y2 = detected[step["detect"]]
                                        print(f"检测到 {step['detect']}，执行动作")
                                        step["action"](x1, y1, x2, y2)
                                    else:
                                        step["action"]()
                                    break
                                except Exception as e:
                                    print(f"执行动作失败: {e}")
                                    return False
                        time.sleep(0.1)

                elif "fail_action" in step and "wait" not in step:
                    continue

            print("导航未完成最终验证，检查当前状态")
            try:
                screenshot = sct.grab(region)
                frame = np.array(screenshot)
                if frame is not None and frame.size > 0:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    detected = detect_objects_template(frame, self.templates)
                else:
                    detected = {}
            except Exception as e:
                print(f"最终验证截图错误: {e}")
                detected = {}
            
            print(f"最终检测到的对象: {detected}")
            # 检查是否成功进入妖气追踪（检测地图标识）
            map_detected = any(key in detected for key in ["ditu1", "ditu2", "ditu3", "ditu4", "ditu5", "ditu6", "ditu7", "ditu8", "ditu9", "ditu10", "ditu11", "ditu12"])
            if map_detected:
                detected_maps = [key for key in detected.keys() if key.startswith("ditu")]
                print(f"界面已改变，检测到地图: {detected_maps}，导航成功")
                return True
            else:
                print("未检测到地图标识，导航可能失败")
                if "fail_action" in steps[-1]:
                    try:
                        steps[-1]["fail_action"]()
                        print("执行最后的失败操作")
                    except Exception as e:
                        print(f"执行最后的失败操作时出错: {e}")
                return False
    
    def run_automation(self, stop_event, total_roles, log_func):
        """运行妖气追踪自动化 - 优化版本"""
        self.stop_event = stop_event
        self.log = log_func
        self.total_roles = total_roles
        
        self.log("开始妖气追踪自动化")
        
        # 启动内存监控
        memory_manager.start_monitoring()
        
        # 获取游戏窗口
        try:
            game_window = gw.getWindowsWithTitle(self.game_title)[0]
        except IndexError:
            self.log("未找到游戏窗口")
            return
        
        region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
        error_count = 0
        max_errors = 10  # 最大连续错误次数
        
        try:
            while not stop_event.is_set():
                try:
                    # 截取屏幕
                    with mss.mss() as sct:
                        screenshot = sct.grab(region)
                        frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
                    
                    # 首先检测翻牌状态
                    if self.detect_fanpai(frame):
                        self.reset_map_state()
                        time.sleep(3)  # 等待翻牌动画完成
                        continue
                    
                    # 检测当前地图
                    current_map = self.detect_current_map(frame)
                    
                    if current_map:
                        # 地图锁定专注模式
                        if self.map_locked and current_map == self.current_confirmed_map:
                            self.log(f"🎯 专注模式执行 {current_map}")
                            
                            # 首次检测到这个地图时进行速度检测
                            if not self.first_ditu_detected:
                                self.log(f"🎯 首次检测到ditu地图: {current_map}，开始速度检测")
                                self.trigger_speed_detection(game_window)
                                self.first_ditu_detected = True
                            elif self.character_switched and not self.speed_detected:
                                self.log(f"🔄 角色已切换，重新进行速度检测")
                                self.trigger_speed_detection(game_window)
                            
                            # 专注执行对应的run_ditu函数
                            try:
                                character_grid, door_states, boss_grid, monsters = self.detect_minimap_advanced(frame)
                                open_doors = [k for k, v in door_states.items() if v == 'open']
                                
                                # 🚪 门优先级：如果有开启的门，必须执行跑图逻辑，不能刷怪
                                if len(open_doors) > 0:
                                    self.log(f"🚪 检测到开启的门: {open_doors}，执行 {current_map} 跑图逻辑（门优先）")
                                    self.execute_focused_map_logic(current_map, game_window, character_grid, door_states, boss_grid)
                                elif character_grid is not None:
                                    self.log(f"📍 检测到角色位置: {character_grid}，执行 {current_map} 跑图逻辑")
                                    self.execute_focused_map_logic(current_map, game_window, character_grid, door_states, boss_grid)
                                else:
                                    # 只有在没有门开启且没检测到角色位置时才进行战斗
                                    self.log("⚔️ 无门开启且未检测到角色位置，执行战斗逻辑")
                                    self.fight_monsters_with_yolo(frame)
                            except Exception as minimap_error:
                                self.log(f"小地图检测错误: {minimap_error}")
                                self.fight_monsters_with_yolo(frame)
                        else:
                            # 非锁定状态的处理
                            self.log(f"检测到地图: {current_map}")
                            if not self.first_ditu_detected:
                                self.log(f"🎯 首次检测到ditu地图: {current_map}，开始速度检测和跑图逻辑")
                                self.process_yaoqi_map_logic(current_map, game_window)
                    else:
                        # 没有检测到地图，可能需要导航
                        if not self.map_locked:
                            try:
                                navigation_success = self.navigate_to_map_advanced(game_window, "yaoqi_tracking")
                                if navigation_success:
                                    self.log("高级导航成功")
                                else:
                                    self.log("高级导航失败，尝试简单导航")
                                    self.navigate_to_yaoqi_map(frame, game_window)
                            except Exception as nav_error:
                                self.log(f"导航错误: {nav_error}")
                                time.sleep(2)
                        else:
                            # 锁定状态下检测不到地图，可能已经完成或出现问题
                            self.log("⚠️ 专注模式下未检测到地图，可能已完成刷图")
                            self.fight_monsters_with_yolo(frame)
                    
                    # 重置错误计数和定期内存清理
                    error_count = 0
                    
                    # 每5次循环进行一次内存清理（更频繁的清理）
                    if hasattr(self, '_loop_count'):
                        self._loop_count += 1
                    else:
                        self._loop_count = 1
                    
                    if self._loop_count % 5 == 0:
                        optimize_memory()
                        self.log(f"📊 执行定期内存清理 (第{self._loop_count}次循环)")
                    
                    time.sleep(2.0)  # 增加间隔，进一步减少系统压力
                    
                except Exception as e:
                    error_count += 1
                    self.log(f"自动化循环中发生错误 ({error_count}/{max_errors}): {e}")
                    
                    # 强制内存清理和资源释放
                    try:
                        optimize_memory()
                        # 释放可能的锁定资源
                        if hasattr(self, '_model_lock'):
                            try:
                                self._model_lock.release()
                            except:
                                pass
                        if hasattr(self, '_combat_lock'):
                            try:
                                self._combat_lock.release()
                            except:
                                pass
                    except:
                        pass
                    
                    if error_count >= max_errors:
                        self.log("连续错误次数过多，停止自动化")
                        break
                    
                    # 逐渐增加等待时间
                    wait_time = min(error_count * 5, 20)  # 进一步增加恢复时间
                    self.log(f"⏳ 等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        except KeyboardInterrupt:
            self.log("用户中断自动化")
        except Exception as fatal_error:
            self.log(f"致命错误: {fatal_error}")
        finally:
            # 彻底清理资源
            try:
                # 停止内存监控
                memory_manager.stop_monitoring()
                
                # 清理战斗系统
                if hasattr(self, 'attacker'):
                    self.attacker = None
                if hasattr(self, 'movement_controller'):
                    self.movement_controller = None
                if hasattr(self, 'speed_calculator'):
                    self.speed_calculator = None
                    
                # 清理YOLO模型
                if hasattr(self, 'yolo_model'):
                    self.yolo_model = None
                    
                # 最终内存清理
                optimize_memory()
                
                self.log("资源清理完成")
            except Exception as cleanup_error:
                self.log(f"资源清理时出错: {cleanup_error}")
        
        self.log("妖气追踪自动化结束")
    
    def fight_monsters_with_yolo(self, frame):
        """使用YOLO检测并攻击怪物 - 线程安全的复杂攻击系统"""
        try:
            # 线程安全的初始化检查
            if not self._combat_initialized:
                if not self._init_combat_systems():
                    self.log("⚠️ 战斗系统初始化失败，使用简化战斗")
                    self._simple_combat_fallback()
                    return
            
            # 安全检查
            if self.yolo_model is None or self.attacker is None:
                self.log("⚠️ YOLO模型或攻击器未初始化，使用简化战斗")
                self._simple_combat_fallback()
                return
            
            # 线程安全的模型访问
            with self._model_lock:
                # 转换为RGB格式供YOLO使用
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 检测怪物（使用完整的检测方法）
                try:
                    monsters = self.attacker.detect_monsters(frame_rgb)
                except Exception as detect_error:
                    self.log(f"怪物检测错误: {detect_error}")
                    # 如果YOLO检测失败，使用简化战斗
                    self._simple_combat_fallback()
                    return
            
            if monsters:
                # 使用完整的战斗逻辑
                target_monster = None
                
                # 优先选择Boss
                for monster in monsters:
                    if monster['type'] == 'boss':
                        target_monster = monster
                        break
                
                # 如果没有Boss，选择最近的怪物
                if target_monster is None and monsters:
                    # 选择最近的怪物（以屏幕中心为参考）
                    target_monster = min(monsters, 
                                        key=lambda m: (m['x'] - 533)**2 + (m['y'] - 300)**2)
                
                if target_monster:
                    self.log(f"🎯 使用复杂攻击系统检测到目标: {target_monster['type']} at ({target_monster['x']}, {target_monster['y']})")
                    
                    # 使用完整的复杂攻击方法
                    try:
                        is_boss = target_monster['type'] == 'boss'
                        
                        # 调用完整的攻击系统（包含移动、转向、技能释放等）
                        attack_result = self.attacker.attack_monster(frame, target_monster['x'], target_monster['y'], is_boss)
                        
                        if attack_result:
                            self.log("✅ 复杂攻击系统战斗完成")
                        else:
                            self.log("⚠️ 复杂攻击系统未完全成功")
                            
                    except Exception as attack_error:
                        self.log(f"复杂攻击失败: {attack_error}，使用简化攻击")
                        self._simple_combat_fallback()
            else:
                # 没有检测到怪物
                self.log("🔍 YOLO未检测到怪物")
                    
        except Exception as e:
            self.log(f"YOLO战斗检测错误: {e}")
            # 在出现错误时使用简化战斗并进行内存清理
            self._simple_combat_fallback()
            optimize_memory()
    
    def _simple_combat_fallback(self):
        """简化战斗后备方案"""
        try:
            self.log("🗡️ 执行简化战斗")
            
            # 简单的攻击序列
            skill_keys = ['a', 's', 'd', 'f', 'q', 'w', 'e']
            for i in range(2):
                skill = random.choice(skill_keys)
                key_code = ord(skill.upper())
                self.input_controller.press_key(key_code, 0.15)
                time.sleep(0.3)
            
            # 普通攻击
            self.input_controller.press_key(88, 0.1)  # X键
            
        except Exception as e:
            self.log(f"简化战斗也失败: {e}")
            # 最后的后备方案
            try:
                # 直接按几个简单键
                for key in [88, 65, 83]:  # X, A, S
                    try:
                        self.input_controller.press_key(key, 0.1)
                        time.sleep(0.2)
                    except:
                        continue
            except:
                pass
    
    def move_chenghao_to_target(self, game_window, chenghao_box, monsters, target_x, target_y, skill_availability, door_states=None):
        """移动角色到目标位置 - 门优先级高于怪物"""
        try:
            # 如果没有指定目标位置，优先检查门，然后才是战斗
            if target_x is None or target_y is None:
                # 🚪 门优先级：如果有开启的门，直接返回False让地图逻辑处理门的移动
                if door_states:
                    open_doors = [k for k, v in door_states.items() if v == 'open']
                    if open_doors:
                        self.log(f"🚪 检测到开启的门: {open_doors}，优先处理门的移动")
                        return False  # 返回False让地图逻辑处理门的移动
                
                # 🎯 只有在没有开启的门时才处理怪物
                if monsters:
                    self.log("🗡️ 没有开启的门，开始处理怪物")
                    # 使用复杂的攻击系统
                    try:
                        # 线程安全的初始化检查
                        if not self._combat_initialized:
                            if not self._init_combat_systems():
                                self.log("⚠️ 战斗系统初始化失败，使用简化战斗")
                                return self._simple_combat_fallback()
                        
                        if self.attacker is not None:
                            # 线程安全的资源访问
                            with self._model_lock:
                                # 获取当前帧进行YOLO检测
                                with mss.mss() as sct:
                                    region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
                                    screenshot = sct.grab(region)
                                    frame_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
                                    frame_rgb = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2RGB)
                                
                                # 使用YOLO检测角色和怪物的真实位置
                                chenghao_x, chenghao_y = self.attacker.get_positions(frame_rgb)
                                yolo_monsters = self.attacker.detect_monsters(frame_rgb)
                            
                            if yolo_monsters:
                                # 选择目标怪物（优先Boss）
                                target_monster = None
                                for monster in yolo_monsters:
                                    if monster['type'] == 'boss':
                                        target_monster = monster
                                        break
                                
                                if target_monster is None:
                                    target_monster = yolo_monsters[0]  # 选择第一个普通怪物
                                
                                # 使用复杂攻击系统的attack_monster方法
                                x1, y1, x2, y2 = target_monster['bbox']
                                is_boss = target_monster['type'] == 'boss'
                                
                                self.log(f"🎯 使用复杂攻击系统攻击 {'Boss' if is_boss else '怪物'}")
                                self.log(f"🎯 目标位置: ({target_monster['x']}, {target_monster['y']})")
                                
                                # 调用复杂的攻击方法
                                attack_result = self.attacker.attack_monster(frame_bgr, target_monster['x'], target_monster['y'], is_boss)
                                
                                if attack_result:
                                    self.log("✅ 复杂攻击系统战斗完成")
                                else:
                                    self.log("⚠️ 复杂攻击系统未完全成功")
                                
                                return attack_result
                            else:
                                self.log("⚠️ YOLO未检测到怪物，使用简化战斗")
                                return self._simple_combat_fallback()
                        else:
                            self.log("⚠️ 攻击器未初始化，使用简化战斗")
                            return self._simple_combat_fallback()
                        
                    except Exception as e:
                        self.log(f"复杂战斗过程中出错: {e}，使用简化战斗")
                        return self._simple_combat_fallback()
                return False
            
            # 如果有角色位置信息，使用智能移动系统
            if chenghao_box is not None:
                # 计算角色当前位置
                char_x = chenghao_box[0] + (chenghao_box[2] - chenghao_box[0]) // 2
                char_y = chenghao_box[1] + (chenghao_box[3] - chenghao_box[1]) // 2 + 80
                
                # 计算移动距离
                dx = target_x - char_x
                dy = target_y - char_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                self.log(f"🎯 智能移动: 角色({char_x}, {char_y}) -> 目标({target_x}, {target_y}), 距离: {distance:.1f}")
                
                if distance < 30:
                    self.log("距离太近，无需移动")
                    return True
                
                # 激活游戏窗口
                activate_window(game_window)
                
                # 使用高级移动控制器的智能移动方法
                if self.movement_controller is not None:
                    try:
                        # 获取当前速度（如果已检测到）
                        current_speed = 100  # 默认速度
                        
                        # 尝试从多个位置获取已检测的速度
                        if hasattr(self, 'detected_speed') and self.detected_speed:
                            current_speed = self.detected_speed
                        elif hasattr(self.attacker, 'speed') and self.attacker.speed:
                            current_speed = self.attacker.speed
                        elif hasattr(self.movement_controller, 'speed') and self.movement_controller.speed:
                            current_speed = self.movement_controller.speed
                        
                        # 从之前的速度检测日志中看到是86.8%，作为备用值
                        if current_speed == 100 and self.speed_detected:
                            current_speed = 86.8
                        
                        self.log(f"🚀 使用智能移动系统，当前速度: {current_speed}%")
                        
                        # 调用智能移动方法
                        success = self.movement_controller.move_to_target_with_smart_method(
                            char_x, char_y, target_x, target_y, 
                            speed_percentage=current_speed, 
                            target_type="fixed"
                        )
                        
                        if success:
                            self.log("✅ 智能移动完成")
                        else:
                            self.log("⚠️ 智能移动失败，使用简单移动作为后备")
                            # 后备方案：简单移动
                            direction = 39 if dx > 0 else 37 if abs(dx) > abs(dy) else (40 if dy > 0 else 38)
                            move_time = min(distance / 400.0, 2.0)
                            self.input_controller.press_key(direction, move_time)
                        
                        return success
                        
                    except Exception as movement_error:
                        self.log(f"智能移动系统出错: {movement_error}")
                        # 降级到简单移动
                        direction = 39 if dx > 0 else 37 if abs(dx) > abs(dy) else (40 if dy > 0 else 38)
                        move_time = min(distance / 400.0, 2.0)
                        self.input_controller.press_key(direction, move_time)
                        self.log("✅ 使用简单移动作为后备方案")
                        return True
                else:
                    self.log("⚠️ 智能移动控制器未初始化，使用简单移动")
                    # 简单移动作为后备
                    direction = 39 if dx > 0 else 37 if abs(dx) > abs(dy) else (40 if dy > 0 else 38)
                    move_time = min(distance / 400.0, 2.0)
                    self.input_controller.press_key(direction, move_time)
                    self.log("✅ 简单移动完成")
                    return True
                
            else:
                self.log("⚠️ 未检测到角色位置，使用点击移动")
                # 简单点击移动（备用方案）
                activate_window(game_window)
                self.input_controller.click(target_x, target_y)
                time.sleep(0.5)
                return True
                
        except Exception as e:
            self.log(f"移动角色时出错: {e}")
            return False
    
    def get_character_grid(self, chenghao_box):
        """根据角色位置计算网格位置"""
        if chenghao_box is None:
            return None
        
        # 计算角色中心位置
        char_x = chenghao_box[0] + (chenghao_box[2] - chenghao_box[0]) // 2
        char_y = chenghao_box[1] + (chenghao_box[3] - chenghao_box[1]) // 2 + 80
        
        # 简化的网格计算（需要根据实际地图调整）
        # 假设游戏区域分为3行7列的网格
        grid_width = 1067 // 7
        grid_height = 600 // 3
        
        col = min(7, max(1, (char_x // grid_width) + 1))
        row = min(3, max(1, (char_y // grid_height) + 1))
        
        return f"{row}-{col}"
    
    def trigger_speed_detection(self, game_window):
        """触发速度检测"""
        try:
            print("🚀 开始进行角色速度检测...")
            
            # 激活游戏窗口
            activate_window(game_window)
            time.sleep(0.5)
            
            # 使用OCR进行速度检测
            detected_speed = self.detect_speed_with_ocr(game_window)
            
            if detected_speed is not None and detected_speed > 0:
                self.speed_detected = True
                self.character_switched = False  # 重置角色切换标志
                self.detected_speed = detected_speed  # 保存检测到的速度值
                
                # 更新攻击器的速度参数
                if self.attacker is not None:
                    self.attacker.speed = detected_speed
                    print(f"📈 攻击器速度已更新: {detected_speed}%")
                
                # 安全更新移动控制器的速度参数
                if self.movement_controller and hasattr(self.movement_controller, 'update_speed'):
                    try:
                        self.movement_controller.update_speed(detected_speed)
                        print(f"📈 AdvancedMovementController速度已更新: {detected_speed}%")
                    except Exception as update_error:
                        print(f"⚠️ 速度更新失败: {update_error}")
                
                print(f"✅ 速度检测完成！当前速度: {detected_speed}%")
            else:
                print("❌ 速度检测失败，使用默认速度100%")
                
        except Exception as e:
            print(f"❌ 速度检测过程中出错: {e}")
    
    def capture_speed_panel_region(self, game_window):
        """截取速度面板区域"""
        try:
            # 尝试多个可能的速度面板位置
            positions = [
                # 原始位置
                {"x_offset": 330, "y_offset": 465, "width": 46, "height": 14},
                # 扩大区域
                {"x_offset": 320, "y_offset": 460, "width": 80, "height": 25},
                # 稍微偏移的位置
                {"x_offset": 340, "y_offset": 470, "width": 60, "height": 20},
            ]
            
            print(f"游戏窗口信息: 位置({game_window.left}, {game_window.top}), 尺寸({game_window.width}x{game_window.height})")
            
            # 先尝试原始位置
            pos = positions[0]
            speed_panel_x_offset = pos["x_offset"]
            speed_panel_y_offset = pos["y_offset"]
            speed_panel_width = pos["width"]
            speed_panel_height = pos["height"]
            
            speed_region = {
                "top": game_window.top + speed_panel_y_offset,
                "left": game_window.left + speed_panel_x_offset,
                "width": speed_panel_width,
                "height": speed_panel_height
            }
            
            print(f"截取区域: top={speed_region['top']}, left={speed_region['left']}, width={speed_region['width']}, height={speed_region['height']}")
            
            with mss.mss() as sct:
                screenshot = sct.grab(speed_region)
                frame = np.array(screenshot)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # 检查图像是否为空或全黑
                if frame_bgr.size == 0:
                    print("警告: 截取的图像为空")
                    return None
                
                # 计算图像亮度
                gray_check = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                mean_brightness = np.mean(gray_check)
                print(f"截取图像平均亮度: {mean_brightness:.2f}")
                
                # 如果图像太暗，可能没有截取到正确区域
                if mean_brightness < 10:
                    print("警告: 图像过暗，可能角色面板未打开或坐标不正确")
                    # 尝试扩大区域重新截取
                    pos = positions[1]
                    speed_region = {
                        "top": game_window.top + pos["y_offset"],
                        "left": game_window.left + pos["x_offset"],
                        "width": pos["width"],
                        "height": pos["height"]
                    }
                    print(f"尝试扩大区域重新截取: {speed_region}")
                    screenshot = sct.grab(speed_region)
                    frame = np.array(screenshot)
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                return frame_bgr
                
        except Exception as e:
            print(f"截取速度面板失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def recognize_speed_text_easyocr(self, image):
        """使用EasyOCR识别速度文本"""
        if image is None or self.ocr_reader is None:
            return ""
        
        try:
            results = self.ocr_reader.readtext(image, allowlist='0123456789%+-.', detail=1)
            text = "".join([result[1] for result in results]).strip().replace(" ", "")
            return text
        except Exception as e:
            print(f"OCR识别失败: {e}")
            return ""
    
    def extract_speed_value(self, ocr_text):
        """从OCR文本中提取速度数值"""
        import re
        match = re.search(r'([+-]?\d+\.?\d*)', ocr_text)
        if match:
            try:
                value = float(match.group(1).replace(' ', ''))
                # 如果数值大于200，可能是小数点识别错误
                if value > 200:
                    value = value / 10.0
                return value
            except (ValueError, IndexError):
                return None
        return None
    
    def detect_speed_with_ocr(self, game_window):
        """使用OCR检测角色移动速度"""
        if self.speed_detected:
            print("速度已检测过，跳过检测")
            return None
        
        print("正在使用OCR检测角色移动速度...")
        
        # 确保游戏窗口激活
        try:
            activate_window(game_window)
            print("游戏窗口已激活")
        except Exception as e:
            print(f"激活游戏窗口失败: {e}")
        
        # 尝试打开角色面板（按M键）
        print("尝试打开角色面板（按M键）...")
        self.input_controller.press_key(77, 0.1)  # M键，键码77
        time.sleep(0.8)  # 等待面板打开稳定
        
        speed_panel_image = self.capture_speed_panel_region(game_window)
        if speed_panel_image is not None:
            print(f"成功截取速度面板，图像尺寸: {speed_panel_image.shape}")
            
            # 保存调试图像
            try:
                debug_dir = "debug_speed"
                if not os.path.exists(debug_dir):
                    os.makedirs(debug_dir)
                debug_path = os.path.join(debug_dir, f"yaoqi_speed_panel_{int(time.time())}.png")
                cv2.imwrite(debug_path, speed_panel_image)
                print(f"调试图像已保存: {debug_path}")
            except Exception as e:
                print(f"保存调试图像失败: {e}")
            
            ocr_text = self.recognize_speed_text_easyocr(speed_panel_image)
            print(f"OCR识别结果: '{ocr_text}'")
            
            speed_value = self.extract_speed_value(ocr_text)
            if speed_value is not None:
                print(f"检测到角色移动速度：{speed_value:.2f}%")
                
                # 关闭角色面板（再按M键）
                print("关闭角色面板...")
                self.input_controller.press_key(77, 0.1)  # M键关闭面板
                
                return speed_value
            else:
                print("未能提取到有效速度数值")
        else:
            print("无法截取速度面板图像")
        
        # 如果识别失败，关闭可能打开的面板
        print("速度识别失败，关闭可能打开的面板...")
        self.input_controller.press_key(77, 0.1)  # M键关闭面板
        
        return None
            
    def on_character_switch(self):
        """角色切换时调用此方法"""
        print("🔄 检测到角色切换，重置所有状态")
        self.character_switched = True
        self.speed_detected = False
        self.current_role += 1
        if self.current_role >= self.total_roles:
            self.current_role = 0
        
        # 角色切换时也重置地图状态
        self.reset_map_state()
    
    # ===== 详细地图逻辑函数（完整实现） =====
    
    def run_ditu1(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu1 的跑图逻辑，移动 chenghao - 门优先级高于怪物"""
        print(f"执行 ditu1 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu1检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print("🗡️ ditu1无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu1: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu1: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability, door_states)
        elif character_grid == "2-1" and (door_states.get("2-1") == "open" or door_states.get("2-2") == "open"):
            print("ditu1: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu1: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability, door_states)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu1: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability, door_states)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu1: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu1: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu1: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability, door_states)

    def run_ditu2(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu2 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu2 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu2检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu2无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu2: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-3" and (door_states.get("1-2") == "open" or door_states.get("1-4") == "open"):
            print("ditu2: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-4" and (door_states.get("1-3") == "open" or door_states.get("1-5") == "open"):
            print("ditu2: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-5" and (door_states.get("1-4") == "open" or door_states.get("2-5") == "open"):
            print("ditu2: 触发移动到 (674, 500)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 674, 500, skill_availability, door_states)
        elif character_grid == "2-5" and (door_states.get("1-5") == "open" or door_states.get("2-6") == "open"):
            print("ditu2: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "2-6" and (door_states.get("2-5") == "open" or door_states.get("2-7") == "open"):
            print("ditu2: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu2: 触发移动到 (713, 260)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 713, 260, skill_availability, door_states)

    def run_ditu3(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu3 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu3 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu3检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu3无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu3: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-4" and (door_states.get("1-4") == "open" or door_states.get("1-5") == "open"):
            print("ditu3: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu3: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu3: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability, door_states)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu3: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability, door_states)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu3: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu3: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu3: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability, door_states)

    def run_ditu4(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu4 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu4 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu4检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu4无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "2-1" and (door_states.get("2-1") == "open" or door_states.get("2-2") == "open"):
            print("ditu4: 触发移动到 (右侧门)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1059, 313, skill_availability, door_states)
        elif character_grid == "2-2" and (door_states.get("2-1") == "open" or door_states.get("2-3") == "open"):
            print("ditu4: 触发移动到 (右侧门)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1059, 307, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu4: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability, door_states)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu4: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability, door_states)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu4: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)

            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu4: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu4: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability, door_states)

    def run_ditu5(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu5 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu5 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu5检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu5无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu5: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-3" and (door_states.get("1-2") == "open" or door_states.get("2-3") == "open"):
            print("ditu5: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability, door_states)
        elif character_grid == "2-3" and door_states.get("1-3") == "open":
            print("ditu5: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability, door_states)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu5: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability, door_states)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu5: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu5: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu5: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability, door_states)

    def run_ditu6(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu6 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu6 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu6检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu6无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu6: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-3" and (door_states.get("1-2") == "open" or door_states.get("1-4") == "open"):
            print("ditu6: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-4" and (door_states.get("1-3") == "open" or door_states.get("1-5") == "open"):
            print("ditu6: 触发移动到 (1011, 197)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1011, 197, skill_availability, door_states)
        elif character_grid == "1-5" and (door_states.get("1-4") == "open" or door_states.get("1-6") == "open"):
            print("ditu6: 触发移动到 (1028, 326)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1028, 326, skill_availability, door_states)
        elif character_grid == "1-6" and (door_states.get("1-5") == "open" or door_states.get("2-6") == "open"):
            print("ditu6: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "2-6" and (door_states.get("1-6") == "open" or door_states.get("2-7") == "open"):
            print("ditu6: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu6: 触发移动到 (500, 264)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 500, 264, skill_availability, door_states)

    def run_ditu7(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu7 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu7 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu7检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu7无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu7: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu7: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu7: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability, door_states)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu7: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability, door_states)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu7: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu7: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu7: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability, door_states)

    def run_ditu8(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu8 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu8 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu8检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu8无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu8: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-6" and (door_states.get("1-6") == "open" or door_states.get("1-7") == "open"):
            print("ditu8: 741移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu8: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu8: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability, door_states)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu8: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability, door_states)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu8: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu8: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu8: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability, door_states)

    def run_ditu9(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu9 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu9 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu9检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu9无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu9: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-6" and (door_states.get("1-6") == "open" or door_states.get("1-7") == "open"):
            print("ditu9: 触发移动到 (1028, 326)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1028, 326, skill_availability, door_states)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu9: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu9: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability, door_states)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu9: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability, door_states)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu9: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu9: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu9: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability, door_states)

    def run_ditu10(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu10 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu10 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu10检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu10无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu10: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-3" and (door_states.get("1-2") == "open" or door_states.get("1-4") == "open"):
            print("ditu10: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-4" and (door_states.get("1-3") == "open" or door_states.get("1-5") == "open"):
            print("ditu10: 触发移动到 (1011, 197)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1011, 197, skill_availability, door_states)
        elif character_grid == "1-5" and (door_states.get("1-4") == "open" or door_states.get("1-6") == "open"):
            print("ditu10: 触发移动到 (1028, 326)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1028, 326, skill_availability, door_states)
        elif character_grid == "1-6" and (door_states.get("1-5") == "open" or door_states.get("2-6") == "open"):
            print("ditu10: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "2-6" and (door_states.get("1-6") == "open" or door_states.get("2-7") == "open"):
            print("ditu10: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu10: 触发移动到 (500, 264)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 500, 264, skill_availability, door_states)

    def run_ditu11(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu11 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu11 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu11检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu11无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "1-2" and (door_states.get("1-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu11: 触发移动到 (1048, 439)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1048, 439, skill_availability, door_states)
        elif character_grid == "1-7" and door_states.get("2-7") == "open":
            print("ditu11: 触发移动到 (644, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 644, 516, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu11: 触发移动到 (137, 451)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 137, 451, skill_availability, door_states)
        elif character_grid == "2-6" and door_states.get("2-5") == "open":
            print("ditu11: 触发移动到 (68, 400)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 68, 400, skill_availability, door_states)
        elif character_grid == "2-5" and door_states.get("3-5") == "open":
            print("ditu11: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "3-5" and door_states.get("3-6") == "open":
            print("ditu11: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "3-6" and door_states.get("3-5") == "open":
            print("ditu11: 触发移动到 (1050, 409)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1050, 409, skill_availability, door_states)

    def run_ditu12(self, character_grid, door_states, game_window, chenghao_box, monsters, skill_availability):
        """执行 ditu12 的跑图逻辑，移动 chenghao"""
        print(f"执行 ditu12 逻辑，人物位置: {character_grid}, chenghao_box: {chenghao_box}")
        
        # 🚪 优先检查门的状态，有开启的门时不进行战斗
        open_doors = [k for k, v in door_states.items() if v == 'open']
        if open_doors:
            print(f"🚪 ditu12检测到开启的门: {open_doors}，执行跑图移动")
        else:
            # 只有在没有开启的门时才考虑战斗
            print(f"🗡️ ditu12无开启的门，处理怪物")
            if self.move_chenghao_to_target(game_window, chenghao_box, monsters, None, None, skill_availability, door_states):
                return
        if character_grid == "2-2" and (door_states.get("2-2") == "open" or door_states.get("2-3") == "open"):
            print("ditu12: 触发移动到 (1067, 340)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1067, 340, skill_availability, door_states)
        elif character_grid == "2-3" and (door_states.get("2-2") == "open" or door_states.get("1-3") == "open"):
            print("ditu12: 触发移动到 (939, 255)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 939, 255, skill_availability, door_states)
        elif character_grid == "1-3" and (door_states.get("1-4") == "open" or door_states.get("2-3") == "open"):
            print("ditu12: 触发移动到 (1067, 340)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1067, 340, skill_availability, door_states)
        elif character_grid == "1-5" and (door_states.get("1-4") == "open" or door_states.get("1-6") == "open"):
            print("ditu12: 触发移动到 (1028, 326)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1028, 326, skill_availability, door_states)
        elif character_grid == "1-6" and (door_states.get("1-5") == "open" or door_states.get("2-6") == "open"):
            print("ditu12: 触发移动到 (600, 516)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 600, 516, skill_availability, door_states)
        elif character_grid == "2-6" and (door_states.get("1-6") == "open" or door_states.get("2-7") == "open"):
            print("ditu12: 触发移动到 (1015, 466)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 1015, 466, skill_availability, door_states)
        elif character_grid == "2-7" and door_states.get("2-6") == "open":
            print("ditu12: 触发移动到 (500, 264)")
            self.move_chenghao_to_target(game_window, chenghao_box, monsters, 500, 264, skill_availability, door_states)


if __name__ == "__main__":
    # 测试代码
    automator = YaoqiAutomator()
    print("妖气追踪模块测试完成")