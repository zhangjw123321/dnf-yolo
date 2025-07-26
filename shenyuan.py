"""
shenyuan.py - 深渊地图完整模块（zhongmochongbaizhe）
整合了深渊地图导航和跑图逻辑，包含完整的自动化功能：
- EasyOCR速度检测系统
- buff应用逻辑（Ctrl键 + 速度检测）
- 完整的YOLO怪物检测和攻击系统
- boss掉落拾取和重试按钮检测
- 角色切换逻辑（F10重试，F12切换角色）
- 智能8方向移动系统
- 优先级处理（shifoujixu > qianjin > monster/boss）
"""

import sys
import os
import time
import cv2
import numpy as np
import mss
import pygetwindow as gw
import random
import math
import re
import win32gui
import win32con
import win32api
import easyocr
from ultralytics import YOLO
from input_controllers import create_input_controller
from advanced_movement import AdvancedMovementController
 

def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# 时间变量
random1_time = random.uniform(0.0311, 0.0511)
random2_time = random.uniform(0.1011, 0.1511)
random3_time = random.uniform(0.2011, 0.3011)
random4_time = random.uniform(0.4011, 0.6011)
random5_time = random.uniform(0.5011, 0.7011)
random6_time = random.uniform(0.6011, 0.8011)


class Utils:
    """工具类"""
    def __init__(self, input_controller=None):
        self.input_controller = input_controller or create_input_controller("默认")

    def activate_window(self, game_window):
        try:
            win32gui.ShowWindow(game_window._hWnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(game_window._hWnd)
            win32gui.SetActiveWindow(game_window._hWnd)
            time.sleep(0.5)
        except Exception as e:
            print(f"激活窗口失败: {e}")

    def press_key(self, key, duration=0.1):
        """按键方法"""
        self.input_controller.press_key(key, duration)

    def click(self, x, y, button="left"):
        """点击方法"""
        self.input_controller.click(x, y, button)
    
    def release_key(self, key):
        """释放按键方法"""
        if hasattr(self.input_controller, 'release_key'):
            self.input_controller.release_key(key)
        else:
            # 如果没有release_key方法，就不做任何操作
            pass

    def detect_template(self, gray_frame, template, threshold=0.7):
        """模板匹配检测"""
        if template is None:
            return []
        
        result = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        
        matches = []
        for pt in zip(*locations[::-1]):
            x1, y1 = pt
            x2, y2 = x1 + template.shape[1], y1 + template.shape[0]
            matches.append((x1, y1, x2, y2))
        
        return matches


class SceneNavigator:
    """场景导航器"""
    def __init__(self, input_controller=None):
        self.game_title = "地下城与勇士：创新世纪"
        self.utils = Utils(input_controller)
        self.templates = {
            'sailiya': cv2.imread(resource_path('image/sailiya.png'), 0),
            'shenyuan': cv2.imread(resource_path('image/shenyuan.png'), 0),
            'diedangquandao_menkou': cv2.imread(resource_path('image/diedangqundao_menkou.png'), 0),
            'shenyuan_xuanze': cv2.imread(resource_path('image/shenyuan_xuanze.png'), 0),
            'zhongmochongbaizhe': cv2.imread(resource_path('image/zhongmochongbaizhe.png'), 0),
            'youxicaidan': cv2.imread(resource_path('image/youxicaidan.png'), 0),
            'shijieditu': cv2.imread(resource_path('image/shijieditu.png'), 0),
            'yincangshangdian': cv2.imread(resource_path('image/yincangshangdian.png'), 0),
            'xuanzejuese': cv2.imread(resource_path('image/xuanzejuese.png'), 0),
            'xuanzejuese_jiemian': cv2.imread(resource_path('image/xuanzejuese_jiemian.png'), 0),
            'yaoqizhuizongxuanze': cv2.imread(resource_path('image/yaoqizhuizongxuanze.png'), 0),
            'yaoqizhuizongpindao': cv2.imread(resource_path('image/yaoqizhuizongpindao.png'), 0)
        }
        
        for key, template in self.templates.items():
            if template is None:
                print(f"模板加载失败: {key}")
            else:
                print(f"模板加载成功: {key}, 尺寸: {template.shape}")
        
        if any(t is None for t in self.templates.values()):
            raise ValueError("无法加载模板图像，请检查路径！")
        
        self.last_right_press_time = 0
        self.right_key_duration = 5
        self.right_key_active = False
        self.last_shenyuan_click_time = 0
        self.shenyuan_click_cooldown = 3
        self.in_town = True
        self.clicked_youxicaidan = False
        self.clicked_shijieditu = False

    def move_to_shenyuan_map(self, frame, gray_frame):
        """移动到深渊地图"""
        game_window = gw.getWindowsWithTitle(self.game_title)[0]
        current_time = time.time()
        town_detected = False

        # 菜单导航逻辑 - 独立于塞利亚房间检测，添加可视化标注
        if not self.clicked_youxicaidan:
            youxicaidan_locations = self.utils.detect_template(gray_frame, self.templates['youxicaidan'])
            print(f"检测到游戏菜单: {len(youxicaidan_locations)} 个位置")
            
            for yx1, yy1, yx2, yy2 in youxicaidan_locations:
                cv2.rectangle(frame, (yx1, yy1), (yx2, yy2), (255, 255, 0), 2)
                cv2.putText(frame, f"游戏菜单: ({yx1},{yy1})", (yx1, yy1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                click_x = yx1 + (yx2 - yx1) // 2
                click_y = yy1 + (yy2 - yy1) // 2
                print(f"检测到 youxicaidan.png，点击坐标 ({click_x}, {click_y})")
                self.utils.activate_window(game_window)
                self.utils.click(click_x, click_y, "left")
                self.clicked_youxicaidan = True
                time.sleep(1)
                break
                
        elif self.clicked_youxicaidan and not self.clicked_shijieditu:
            shijieditu_locations = self.utils.detect_template(gray_frame, self.templates['shijieditu'])
            print(f"检测到世界地图: {len(shijieditu_locations)} 个位置")
            
            for sx1, sy1, sx2, sy2 in shijieditu_locations:
                cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), (0, 255, 255), 2)
                cv2.putText(frame, f"世界地图: ({sx1},{sy1})", (sx1, sy1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                click_x = sx1 + (sx2 - sx1) // 2
                click_y = sy1 + (sy2 - sy1) // 2
                print(f"检测到 shijieditu.png，点击坐标 ({click_x}, {click_y})")
                self.utils.activate_window(game_window)
                self.utils.click(click_x, click_y, "left")
                self.clicked_shijieditu = True
                time.sleep(1)
                break

        # 检测塞利亚房间 - 仅用于可视化标注
        sailiya_locations = self.utils.detect_template(gray_frame, self.templates['sailiya'])
        print(f"检测到塞利亚房间: {len(sailiya_locations)} 个位置")
        
        for x1, y1, x2, y2 in sailiya_locations:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"塞丽亚: ({x1},{y1})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            town_detected = True

        # 检测深渊入口
        shenyuan_locations = self.utils.detect_template(gray_frame, self.templates['shenyuan'])
        print(f"检测到深渊: {len(shenyuan_locations)} 个位置")
        
        for x1, y1, x2, y2 in shenyuan_locations:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, f"深渊: ({x1},{y1})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            if current_time - self.last_shenyuan_click_time >= self.shenyuan_click_cooldown:
                click_x = x1 + (x2 - x1) // 2
                click_y = y1 + (y2 - y1) // 2
                print(f"检测到 shenyuan.png，点击坐标 ({click_x}, {click_y})")
                self.utils.activate_window(game_window)
                self.utils.click(click_x, click_y, "left")
                self.last_shenyuan_click_time = current_time
                time.sleep(1)
                town_detected = True

        # 检测跌宕群岛门口
        diedang_locations = self.utils.detect_template(gray_frame, self.templates['diedangquandao_menkou'])
        print(f"检测到跌宕群岛门口: {len(diedang_locations)} 个位置")
        
        for x1, y1, x2, y2 in diedang_locations:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, f"跌宕群岛门口: ({x1},{y1})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            print("已经移动到跌宕群岛门口")
            self.utils.activate_window(game_window)
            time.sleep(1)
            
            # 在右击前先按下右方向键0.5秒
            print("按下右方向键0.5秒调整位置")
            if hasattr(self.utils, 'press_key'):
                self.utils.press_key(39, 0.5)  # 39是右方向键
            time.sleep(0.1)  # 短暂等待
            
            self.utils.click(45, 315, "right")
            print("右键点击跌宕群岛门口")
            town_detected = True

        # 检测深渊选择
        shenyuan_xuanze_locations = self.utils.detect_template(gray_frame, self.templates['shenyuan_xuanze'])
        print(f"检测到深渊选择: {len(shenyuan_xuanze_locations)} 个位置")
        
        for x1, y1, x2, y2 in shenyuan_xuanze_locations:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, f"深渊选择: ({x1},{y1})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            print("检测到 shenyuan_xuanze.png，左击 (717, 471)")
            self.utils.activate_window(game_window)
            self.utils.click(717, 471, "left")
            town_detected = True

        self.in_town = town_detected
        return self.in_town


class MonsterFighterA:
    """怪物战斗类 - 使用advanced_movement移动系统"""
    def __init__(self, input_controller, yolo_model=None):
        self.game_title = "地下城与勇士：创新世纪"
        self.utils = Utils(input_controller)
        self.input_controller = input_controller
        self.yolo_model = yolo_model

        # 初始化高级移动控制器
        self.movement_controller = AdvancedMovementController(input_controller)

        # 模板加载
        self.monsters = {
            'monster': {'action': self.attack_monster_advanced, 'type': 'monster'},
            'boss': {'action': self.attack_boss_advanced, 'type': 'boss'},
            'qianjin': {'template': cv2.imread(resource_path('image/qianjin.png'), 0), 'action': self.run_to_qianjin, 'type': 'qianjin'},
            'chenghao': {'action': None, 'type': 'player'},
            'shifoujixu': {'template': cv2.imread(resource_path('image/shifoujixu.png'), 0), 'action': self.pickup_boss_drops, 'type': 'pickup'},
            'zhongmochongbaizhe': {'template': cv2.imread(resource_path('image/zhongmochongbaizhe.png'), 0), 'type': 'map'}
        }

        # 检查模板加载
        for name, data in self.monsters.items():
            if 'template' in data:
                if data['template'] is None:
                    print(f"加载失败: {name}")
                else:
                    height, width = data['template'].shape
                    print(f"模板加载成功: {name}, 尺寸: {width}x{height}")

        self.qianjin_reached = False
        self.boss_dead = False
        self.shifoujixu_detected_time = None
        self.has_applied_buff = False  # buff 状态变量

        # 速度识别相关
        self.speed = None  # 存储角色移动速度
        self.speed_detected = False  # 标志位，记录是否已检测速度
        self.character_switched = False  # 角色切换标志

        # 初始化EasyOCR
        try:
            self.ocr_reader = easyocr.Reader(['en'], gpu=False)
            print("EasyOCR 使用 CPU 模式（稳定性优化）")
        except Exception as e:
            print(f"EasyOCR 初始化失败: {e}")
            self.ocr_reader = None

        # 重试按钮模板
        self.retry_button_template = cv2.imread(resource_path('image/retry_button.png'), 0)
        if self.retry_button_template is None:
            print("加载失败: retry_button")
        else:
            print("模板加载成功: retry_button")

        # 技能键列表 
        self.skill_keys = ['a', 's', 'd', 'f', 'g', 'h', 'q', 'w', 'e', 'r', 't', 'y']
        self.boss_skill = 'y'
        self.current_direction = None  # 当前移动方向
        
        # 初始化技能区域
        self.skill_regions = self._get_skill_key_regions()

        print("MonsterFighterA初始化完成（使用advanced_movement系统）")

        # 速度识别相关
        self.speed = None
        self.speed_detected = False
        self.character_switched = False

    def attack_monster_advanced(self, frame, x1, y1, x2, y2):
        """攻击小怪 - 使用advanced_movement移动系统"""
        try:
            # 计算怪物中心位置
            monster_x = x1 + (x2 - x1) // 2
            monster_y = y1 + (y2 - y1) // 2
            
            # 获取真实的chenghao位置
            character_x, character_y = self._get_chenghao_position(frame)

            print(f"🗡️ 使用advanced_movement攻击小怪，位置: ({monster_x}, {monster_y})")
            print(f"📍 角色位置: ({character_x}, {character_y})")

            # 同步速度到movement_controller
            if hasattr(self.movement_controller, 'speed'):
                self.movement_controller.speed = self.speed or 100
            
            # 使用advanced_movement移动到怪物位置
            move_success = self.movement_controller.move_to_target_with_smart_method(
                character_x, character_y, monster_x, monster_y, 
                speed_percentage=self.speed or 100, target_type="monster"
            )

            if move_success:
                # 移动完成后释放技能攻击
                print("移动到怪物位置，开始攻击")
                self._perform_attack_combo(frame, is_boss=False)
                print("✅ 小怪攻击完成")
                return True
            else:
                print("⚠️ 移动到怪物位置失败")
                return False

        except Exception as e:
            print(f"❌ advanced_movement攻击小怪失败: {e}")
            return False

    def attack_boss_advanced(self, frame, x1, y1, x2, y2):
        """攻击Boss - 使用advanced_movement移动系统"""
        try:
            # 计算Boss中心位置
            boss_x = x1 + (x2 - x1) // 2
            boss_y = y1 + (y2 - y1) // 2
            
            # 获取真实的chenghao位置
            character_x, character_y = self._get_chenghao_position(frame)

            print(f"👹 使用advanced_movement攻击Boss，位置: ({boss_x}, {boss_y})")
            print(f"📍 角色位置: ({character_x}, {character_y})")

            # 同步速度到movement_controller
            if hasattr(self.movement_controller, 'speed'):
                self.movement_controller.speed = self.speed or 100
            
            # 使用advanced_movement移动到Boss位置
            move_success = self.movement_controller.move_to_target_with_smart_method(
                character_x, character_y, boss_x, boss_y, 
                speed_percentage=self.speed or 100, target_type="boss"
            )

            if move_success:
                # 移动完成后释放技能攻击Boss
                print("移动到Boss位置，开始攻击")
                self._perform_attack_combo(frame, is_boss=True)
                self.boss_dead = True
                print("✅ Boss攻击完成")
                return True
            else:
                print("⚠️ 移动到Boss位置失败")
                return False

        except Exception as e:
            print(f"❌ advanced_movement攻击Boss失败: {e}")
            return False

    def _perform_attack_combo(self, frame, is_boss=False):
        """执行随机技能攻击 - 随机释放可用技能，间隔0.1秒"""
        try:
            # 获取当前可用技能
            available_skills = self.get_available_skills(frame)
            
            if available_skills:
                # 随机选择一个可用技能
                import random
                skill_to_use = random.choice(available_skills)
                
                if is_boss:
                    print(f"🎯 随机释放Boss技能: {skill_to_use}")
                else:
                    print(f"⚔️ 随机释放攻击技能: {skill_to_use}")
                
                # 释放技能
                self.utils.press_key(ord(skill_to_use.lower()) - ord('a') + 65, 0.1)
                time.sleep(0.1)  # 间隔0.1秒
                
                print(f"✅ 技能 {skill_to_use} 释放完成")
            else:
                print("⚠️ 暂无可用技能，跳过攻击")
                    
        except Exception as e:
            print(f"技能攻击失败: {e}")

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

    def _get_chenghao_position(self, frame):
        """获取chenghao的真实位置"""
        try:
            # 使用YOLO检测chenghao
            if self.yolo_model is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = self.yolo_model.predict(frame_rgb)
                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls)
                        if cls_id in result.names:
                            cls_name = result.names[cls_id]

                            
                            if cls_name == 'chenghao':
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                # 计算chenghao中心位置
                                center_x = x1 + (x2 - x1) // 2
                                center_y = y1 + (y2 - y1) // 2 + 80
                                return center_x, center_y
            
            # 如果没有检测到chenghao，使用屏幕中心作为备用
            print("⚠️ 未检测到chenghao，使用屏幕中心坐标")
            return 533, 300
            
        except Exception as e:
            print(f"获取chenghao位置失败: {e}")
            # 出错时使用屏幕中心作为备用
            return 533, 300

    # 保留旧方法名以保持兼容性
    def attack_monster(self, frame, x1, y1, x2, y2):
        """攻击小怪 - 兼容性方法"""
        return self.attack_monster_advanced(frame, x1, y1, x2, y2)

    def attack_boss(self, frame, x1, y1, x2, y2):
        """攻击Boss - 兼容性方法"""
        return self.attack_boss_advanced(frame, x1, y1, x2, y2)

    def run_to_qianjin(self, frame, x1, y1, x2, y2):
        """移动到前进点 - 使用advanced_movement智能移动系统"""
        try:
            game_window = gw.getWindowsWithTitle(self.game_title)[0]
            self.utils.activate_window(game_window)

            # 固定目标坐标
            target_x = 1067
            target_y = 230
            
            # 获取真实的chenghao位置
            character_x, character_y = self._get_chenghao_position(frame)

            print(f"检测到 qianjin，开始使用advanced_movement移动到固定坐标 ({target_x}, {target_y})")
            print(f"📍 角色位置: ({character_x}, {character_y})")

            # 同步速度到movement_controller
            if hasattr(self.movement_controller, 'speed'):
                self.movement_controller.speed = self.speed or 100
            
            # 使用advanced_movement智能移动到目标点
            move_success = self.movement_controller.move_to_target_with_smart_method(
                character_x, character_y, target_x, target_y, 
                speed_percentage=self.speed or 100, target_type="qianjin"
            )

            if move_success:
                self.qianjin_reached = True
                print("✅ 成功移动到qianjin固定坐标")
            else:
                print("⚠️ 移动到qianjin失败，使用备用方案")
                # 备用方案：简单方向移动
                qianjin_x = x1 + (x2 - x1) // 2
                if qianjin_x < target_x:
                    self.utils.press_key(39, 2.0)  # 向右
                else:
                    self.utils.press_key(37, 2.0)  # 向左
                self.qianjin_reached = True

        except Exception as e:
            print(f"移动到qianjin失败: {e}")
            self.qianjin_reached = True  # 即使失败也设置为True，避免卡住

    def pickup_boss_drops(self, frame, x1, y1, x2, y2):
        """拾取Boss掉落物 - 完整版本"""
        print("检测到 shifoujixu.png，Boss 已死，开始拾取")

        # 停止所有移动
        if self.current_direction is not None:
            self.utils.release_key(self.current_direction)
            self.current_direction = None
            print("检测到 shifoujixu，强制停止奔跑")
        
        # 停止advanced_movement的所有移动
        self.movement_controller.stop_all_movement()

        # 激活游戏窗口
        try:
            game_window = gw.getWindowsWithTitle(self.game_title)[0]
            self.utils.activate_window(game_window)
        except Exception as e:
            print(f"激活游戏窗口失败: {e}")

        # 按V键聚集掉落物品
        self.utils.press_key(86, random.uniform(0.1311, 0.1511))  # V键
        print("按下 V 键聚集掉落物品")

        # 连续按X键拾取，持续3秒
        start_time = time.time()
        while time.time() - start_time < 3:
            self.utils.press_key(88, random.uniform(0.1311, 0.1511))  # X键
        print("拾取完成")

        # 检查重试按钮状态
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        retry_locations = self.utils.detect_template(gray_frame, self.retry_button_template)
        retry_button_gray = False

        for rx1, ry1, rx2, ry2 in retry_locations:
            padding = 5
            roi = frame[ry1 + padding:ry2 - padding, rx1 + padding:rx2 - padding]
            if roi.size == 0:
                roi = frame[ry1:ry2, rx1:rx2]
            retry_button_gray = self.is_gray(roi)
            print(f"再次挑战按钮状态: {'灰色（不可用）' if retry_button_gray else '彩色（可用）'}")
            break

        if not retry_button_gray:
            print("再次挑战按钮可用，点击重试")
            self.utils.press_key(121, random.uniform(0.1311, 0.1511))  # F10
            self.qianjin_reached = False
            self.boss_dead = False
            print("已离开 Boss 房间")
            return False
        else:
            print("再次挑战按钮为灰色，当前角色刷图完成，退出并切换角色")
            self.utils.press_key(123, random.uniform(0.1311, 0.1511))  # F12
            return True

    def is_gray(self, roi):
        """检查区域是否为灰色"""
        mean_color = np.mean(roi, axis=(0, 1))
        b, g, r = mean_color
        color_diff = max(abs(r - g), abs(g - b), abs(b - r))
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mean_hsv = np.mean(roi_hsv, axis=(0, 1))
        saturation = mean_hsv[1]
        print(f"按钮颜色 - RGB: [{b:.1f}, {g:.1f}, {r:.1f}], 差异: {color_diff:.1f}, 饱和度: {saturation:.1f}")
        return color_diff < 10 and saturation < 100

    def reset_speed_detection(self):
        """重置速度检测状态（角色切换时调用）"""
        self.speed = None
        self.speed_detected = False
        self.character_switched = True
        self.has_applied_buff = False  # 重置buff状态
        print("角色切换，重置速度检测状态")

    def capture_speed_panel_region(self, game_window):
        """截取速度面板区域"""
        try:
            # 尝试多个可能的速度面板位置
            positions = [
                {"x_offset": 330, "y_offset": 465, "width": 46, "height": 14},
                {"x_offset": 320, "y_offset": 460, "width": 80, "height": 25},
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

    def detect_speed(self, game_window):
        """检测角色移动速度"""
        if not self.speed_detected:
            print("🚀 开始进行角色速度检测...")

            # 确保游戏窗口激活
            try:
                self.utils.activate_window(game_window)
                print("游戏窗口已激活")
            except Exception as e:
                print(f"激活游戏窗口失败: {e}")

            # 尝试打开角色面板（按M键）
            print("尝试打开角色面板（按M键）...")
            self.utils.press_key(77, 0.1)  # M键，键码77
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
                    self.speed = speed_value
                    self.speed_detected = True
                    # 同步速度值到movement_controller
                    if hasattr(self.movement_controller, 'speed'):
                        self.movement_controller.speed = self.speed
                    print(f"检测到角色移动速度：{self.speed:.2f}%")

                    # 关闭角色面板（再按M键）
                    print("关闭角色面板...")
                    self.utils.press_key(77, 0.1)  # M键关闭面板

                    return self.speed
                else:
                    print("未能提取到有效速度数值")
            else:
                print("无法截取速度面板图像")

            # 如果识别失败，关闭可能打开的面板
            print("速度识别失败，关闭可能打开的面板...")
            self.utils.press_key(77, 0.1)  # M键关闭面板

        else:
            print(f"已缓存移速: {self.speed:.2f}%，跳过速度检测")

        return self.speed

    def apply_buff(self):
        """施加 buff：按下 Ctrl 键"""
        print("施加 buff：按下 Ctrl 键")
        self.utils.press_key(17, random.uniform(0.1311, 0.1511))  # Ctrl 键（键码 17）
        print("Buff 施加完成")
        self.has_applied_buff = True

        # 加buff后立即进行速度识别（每个角色只识别一次）
        if not self.speed_detected:
            print("开始进行速度识别...")
            try:
                game_window = gw.getWindowsWithTitle(self.game_title)[0]
                print(f"找到游戏窗口: {game_window.title}")

                # 等待一下让buff界面稳定
                time.sleep(0.5)

                detected_speed = self.detect_speed(game_window)
                if detected_speed:
                    print(f"✅ 速度检测完成！当前速度: {detected_speed:.1f}%")
                    # 同步速度到movement_controller
                    if hasattr(self.movement_controller, 'speed'):
                        self.movement_controller.speed = detected_speed
                else:
                    print("✗ Buff后速度识别失败，将使用默认速度100%")
            except Exception as e:
                print(f"✗ Buff后速度识别出错: {e}")
        else:
            print(f"速度已检测过：{self.speed:.2f}%，跳过重复检测")

    def fight_monsters(self, frame, gray_frame):
        """完整的怪物战斗逻辑 - 严格优先级控制"""
        start_time = time.time()
        detected_monsters = []
        should_pickup = False
        in_zhongmochongbaizhe = False

        # 使用YOLO检测怪物
        if self.yolo_model is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.yolo_model.predict(frame_rgb)
            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls)
                    if cls_id in result.names:
                        cls_name = result.names[cls_id]
                        # 处理Intel模型的类别名称映射
                        if cls_name == 'cheng_hao':
                            cls_name = 'chenghao'

                        if cls_name in ['monster', 'boss', 'chenghao']:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            # 对chenghao的y轴坐标进行偏移调整
                            if cls_name == 'chenghao':
                                y1 += 80
                                y2 += 80
                            detected_monsters.append((cls_name, x1, y1, x2, y2))

        # 使用模板检测其他对象
        for monster_name, monster_data in self.monsters.items():
            if 'template' in monster_data and monster_data['template'] is not None:
                locations = self.utils.detect_template(gray_frame, monster_data['template'], threshold=0.8)
                print(f"检测 {monster_name}，找到 {len(locations)} 个匹配")
                for x1, y1, x2, y2 in locations:
                    detected_monsters.append((monster_name, x1, y1, x2, y2))

        print(f"检测到的所有对象: {detected_monsters}")

        # 检查是否在zhongmochongbaizhe地图中
        in_zhongmochongbaizhe = any(
            monster_name == 'zhongmochongbaizhe' for monster_name, _, _, _, _ in detected_monsters)

        if not in_zhongmochongbaizhe:
            print("未检测到 zhongmochongbaizhe 地图，跳过怪物检测")
            return frame, False
        else:
            print("检测到 zhongmochongbaizhe 地图，继续处理怪物逻辑")
            if not self.has_applied_buff:
                self.apply_buff()

        # === 严格优先级控制：shifoujixu > qianjin > monster/boss ===

        # 优先级1：shifoujixu（Boss死亡拾取）- 最高优先级，立即停止所有其他操作
        for monster_name, x1, y1, x2, y2 in detected_monsters:
            if monster_name == 'shifoujixu':
                print("🚨 检测到 shifoujixu - 最高优先级！立即停止所有操作并拾取")

                # 停止所有移动操作
                self._stop_all_current_actions()

                color = (0, 128, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"PICKUP: ({x1},{y1})", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                should_pickup = self.monsters[monster_name]['action'](frame, x1, y1, x2, y2)
                return frame, should_pickup  # 立即返回，不处理任何其他对象

        # 优先级2：qianjin - 第二优先级，立即停止打怪操作
        for monster_name, x1, y1, x2, y2 in detected_monsters:
            if monster_name == 'qianjin':
                print("🎯 检测到 qianjin - 第二优先级！立即停止打怪并移动")

                # 停止所有攻击操作
                self._stop_all_attack_actions()

                color = (0, 255, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"QIANJIN: ({x1},{y1})", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                print("开始移动到 qianjin 固定点")
                self.monsters[monster_name]['action'](frame, x1, y1, x2, y2)
                return frame, False  # 立即返回，不处理monster/boss

        # 优先级3：monster/boss - 最低优先级，只有在没有shifoujixu和qianjin时才执行
        monsters_to_attack = [(name, x1, y1, x2, y2) for name, x1, y1, x2, y2 in detected_monsters if name in ['monster', 'boss']]
        
        if monsters_to_attack:
            # 分别处理monster和boss
            regular_monsters = [(name, x1, y1, x2, y2) for name, x1, y1, x2, y2 in monsters_to_attack if name == 'monster']
            bosses = [(name, x1, y1, x2, y2) for name, x1, y1, x2, y2 in monsters_to_attack if name == 'boss']
            
            # 优先攻击Boss，如果没有Boss则攻击monster
            target_monsters = bosses if bosses else regular_monsters
            
            if len(target_monsters) == 1:
                # 只有一个目标，直接攻击
                monster_name, x1, y1, x2, y2 = target_monsters[0]
                color = (255, 255, 0) if monster_name == 'monster' else (255, 0, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{monster_name.upper()}: ({x1},{y1})", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                print(f"🗡️ 攻击单个 {monster_name}（无更高优先级对象）")
                self.monsters[monster_name]['action'](frame, x1, y1, x2, y2)
            
            elif len(target_monsters) > 1:
                # 多个目标，计算中心点攻击
                print(f"🎯 检测到 {len(target_monsters)} 个 {target_monsters[0][0]}，计算中心点攻击")
                
                # 计算所有怪物的边界
                all_x1 = [x1 for _, x1, y1, x2, y2 in target_monsters]
                all_y1 = [y1 for _, x1, y1, x2, y2 in target_monsters]
                all_x2 = [x2 for _, x1, y1, x2, y2 in target_monsters]
                all_y2 = [y2 for _, x1, y1, x2, y2 in target_monsters]
                
                # 计算中心点坐标
                center_x = (min(all_x1) + max(all_x2)) // 2
                center_y = (min(all_y1) + max(all_y2)) // 2
                
                print(f"📍 多怪物中心点: ({center_x}, {center_y})")
                
                # 绘制所有怪物的检测框
                monster_name = target_monsters[0][0]  # 取第一个怪物的类型
                color = (255, 255, 0) if monster_name == 'monster' else (255, 0, 0)
                
                for _, x1, y1, x2, y2 in target_monsters:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"{monster_name.upper()}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # 绘制中心点
                cv2.circle(frame, (center_x, center_y), 8, (0, 255, 255), -1)  # 黄色实心圆
                cv2.putText(frame, "CENTER", (center_x - 20, center_y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 2)
                
                # 使用中心点坐标攻击
                print(f"🗡️ 攻击多个 {monster_name} 的中心点")
                # 创建虚拟边界框用于攻击
                virtual_x1, virtual_y1 = center_x - 50, center_y - 50
                virtual_x2, virtual_y2 = center_x + 50, center_y + 50
                self.monsters[monster_name]['action'](frame, virtual_x1, virtual_y1, virtual_x2, virtual_y2)

        print(f"Fight monsters time: {time.time() - start_time:.3f} seconds")
        return frame, should_pickup

    def _stop_all_current_actions(self):
        """停止所有当前操作（移动、攻击等）"""
        try:
            print("🛑 停止所有当前操作")

            # 停止当前移动
            if self.current_direction is not None:
                self.utils.release_key(self.current_direction)
                self.current_direction = None
                print("已停止当前移动")

            # 停止advanced_movement的所有移动
            self.movement_controller.stop_all_movement()

        except Exception as e:
            print(f"停止操作失败: {e}")

    def _stop_all_attack_actions(self):
        """停止所有攻击操作"""
        try:
            print("⚔️ 停止所有攻击操作")

            # 停止移动到怪物的操作
            if self.current_direction is not None:
                self.utils.release_key(self.current_direction)
                self.current_direction = None
                print("已停止移动到怪物")

            # 停止advanced_movement的所有移动
            self.movement_controller.stop_all_movement()

        except Exception as e:
            print(f"停止攻击操作失败: {e}")


class ShenyuanAutomator:
    """深渊地图自动化器"""
    
    def __init__(self, input_controller=None):
        self.game_title = "地下城与勇士：创新世纪"
        self.input_controller = input_controller or create_input_controller("默认")
        
        # 初始化YOLO模型（共享给战斗系统使用）
        try:
            self.yolo_model = YOLO('models/best.pt')
            print("ShenyuanAutomator YOLO模型加载成功")
        except Exception as e:
            print(f"ShenyuanAutomator YOLO模型加载失败: {e}")
            self.yolo_model = None
        
        self.navigator = SceneNavigator(input_controller=self.input_controller)
        self.fighter = MonsterFighterA(input_controller=self.input_controller, yolo_model=self.yolo_model)
        self.stop_event = None
        self.log = print
        print("ShenyuanAutomator初始化完成（集成复杂攻击系统）")
        
    def get_game_window(self):
        """获取游戏窗口"""
        try:
            return gw.getWindowsWithTitle(self.game_title)[0]
        except IndexError:
            print(f"未找到窗口: {self.game_title}")
            return None
    
    def _check_zhongmochongbaizhe_map(self, gray_frame):
        """检查是否在zhongmochongbaizhe地图中"""
        try:
            zhongmo_template = cv2.imread(resource_path('image/zhongmochongbaizhe.png'), 0)
            if zhongmo_template is not None:
                locations = self.navigator.utils.detect_template(gray_frame, zhongmo_template, threshold=0.8)
                return len(locations) > 0
        except Exception as e:
            print(f"检查zhongmochongbaizhe地图失败: {e}")
        return False

    def run_automation(self, stop_event, log_func):
        """运行深渊地图自动化 - 完整的zhongmochongbaizhe实现"""
        self.stop_event = stop_event
        self.log = log_func
        
        self.log("开始深渊地图自动化（zhongmochongbaizhe）")
        
        game_window = self.get_game_window()
        if not game_window:
            self.log("无法找到游戏窗口")
            return

        region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
        character_switch_requested = False
        
        while not stop_event.is_set():
            try:
                with mss.mss() as sct:
                    screenshot = sct.grab(region)
                    frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 首先检查是否在zhongmochongbaizhe地图中
                zhongmo_detected = self._check_zhongmochongbaizhe_map(gray_frame)
                
                if zhongmo_detected:
                    # 在zhongmochongbaizhe地图中，直接进行战斗逻辑，跳过城镇检测
                    self.log("在zhongmochongbaizhe地图中，执行战斗逻辑")
                    frame_with_detections, should_switch_character = self.fighter.fight_monsters(frame, gray_frame)
                    
                    if should_switch_character:
                        self.log("检测到角色切换请求")
                        character_switch_requested = True
                        
                        # 重置战斗器的速度检测状态，为下一个角色准备
                        self.fighter.reset_speed_detection()
                        self.log("已重置速度检测状态，等待新角色")
                        
                        # 等待角色切换完成
                        time.sleep(3)
                        character_switch_requested = False
                else:
                    # 不在zhongmochongbaizhe地图中，进行导航逻辑
                    in_town = self.navigator.move_to_shenyuan_map(frame, gray_frame)
                    if in_town:
                        self.log("在城镇中，继续导航...")
                
                time.sleep(1)
                
            except Exception as e:
                self.log(f"深渊地图自动化错误: {e}")
                import traceback
                self.log(f"详细错误信息: {traceback.format_exc()}")
                time.sleep(2)
        
        self.log("深渊地图自动化结束")
    
    def fight_monsters_with_yolo(self, frame):
        """使用YOLO检测并攻击怪物"""
        try:
            if self.yolo_model is None:
                return
            
            # 转换为RGB格式供YOLO使用
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 检测怪物
            monsters = self.fighter.attacker.detect_monsters(frame_rgb)
            
            if monsters:
                # 优先攻击Boss
                bosses = [m for m in monsters if m['type'] == 'boss']
                regular_monsters = [m for m in monsters if m['type'] == 'monster']
                
                if bosses:
                    for boss in bosses:
                        self.log(f"检测到Boss，位置: ({boss['x']}, {boss['y']})")
                        x1, y1, x2, y2 = boss['bbox']
                        self.fighter.attack_boss_advanced(frame, x1, y1, x2, y2)
                        break  # 一次只攻击一个Boss
                        
                elif regular_monsters:
                    # 选择最近的怪物
                    closest_monster = min(regular_monsters, 
                                        key=lambda m: (m['x'] - 533)**2 + (m['y'] - 300)**2)  # 屏幕中心大约是(533, 300)
                    
                    self.log(f"检测到小怪，位置: ({closest_monster['x']}, {closest_monster['y']})")
                    x1, y1, x2, y2 = closest_monster['bbox']
                    self.fighter.attack_monster_advanced(frame, x1, y1, x2, y2)
                    
        except Exception as e:
            self.log(f"YOLO战斗检测错误: {e}")


if __name__ == "__main__":
    # 测试代码
    automator = ShenyuanAutomator()
    print("深渊地图模块测试完成")