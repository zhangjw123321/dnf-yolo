import sys
import threading
import queue
import cv2
import numpy as np
import time
import random
import os
import subprocess
import hashlib
import win32gui
import win32con
import win32api
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QHBoxLayout, QMessageBox, QComboBox, QTextEdit, QCheckBox)
from PyQt5.QtCore import QTimer
from pathlib import Path
import json
import requests
from datetime import datetime
import mss
import pygetwindow as gw
from pynput.keyboard import Key, Controller as KeyboardController
from ctypes import *
from ultralytics import YOLO

# 游戏区域和随机延迟定义
region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
random1_time = round(random.uniform(0.1311, 0.1511), 4)
random5_time = round(random.uniform(0.4011, 0.6011), 4)
random6_time = round(random.uniform(2.0111, 2.3011), 4)

def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发和 PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def get_machine_code():
    try:
        # 使用 MAC 地址和系统信息生成唯一标识
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 48, 8)])
        system_info = platform.node() + platform.platform()
        unique_id = mac + system_info
        return hashlib.md5(unique_id.encode('utf-8')).hexdigest()
    except Exception as e:
        print(f"获取机器码失败: {e}")
        return "DEFAULT_MACHINE_CODE_12345"

class Utils:
    def __init__(self, input_controller):
        self.input_controller = input_controller
        self.last_activate_time = 0
        self.activate_cooldown = 5

    def activate_window(self, game_window):
        current_time = time.time()
        if current_time - self.last_activate_time < self.activate_cooldown:
            print("窗口激活冷却中，跳过")
            return
        try:
            win32gui.ShowWindow(game_window._hWnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(game_window._hWnd)
            win32gui.SetActiveWindow(game_window._hWnd)
            time.sleep(1)
            current_foreground = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            print(f"当前前台窗口: {current_foreground}")
            if "地下城与勇士：创新世纪" in current_foreground:
                print("已激活窗口: 地下城与勇士：创新世纪")
                self.last_activate_time = current_time
            else:
                print("窗口激活可能失败")
        except Exception as e:
            print(f"激活窗口失败: {e}")

    def detect_template(self, gray_frame, template, threshold=0.9):
        if template is None:
            print("模板为空，无法检测")
            return []

        result = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        h, w = template.shape
        return [(pt[0], pt[1], pt[0] + w, pt[1] + h) for pt in zip(*locations[::-1])]

    def press_key(self, key, duration=0.5):
        self.input_controller.press_key(key, duration)

    def hold_key(self, key):
        self.input_controller.hold_key(key)

    def release_key(self, key):
        self.input_controller.release_key(key)

    def click(self, x, y, button="left"):
        self.input_controller.click(x, y, button)

class InputController:
    def press_key(self, key, duration=0.5):
        raise NotImplementedError

    def hold_key(self, key):
        raise NotImplementedError

    def release_key(self, key):
        raise NotImplementedError

    def click(self, x, y, button="left"):
        raise NotImplementedError

class DefaultInputController(InputController):
    def __init__(self):
        try:
            self.keyboard = KeyboardController()
            self.function_key_map = {
                121: Key.f10,      # F10
                123: Key.f12,      # F12
                86: 'v',           # V
                88: 'x',           # X
                37: Key.left,      # Left
                38: Key.up,        # Up
                39: Key.right,     # Right
                40: Key.down,      # Down
                32: Key.space,     # Space
                17: Key.ctrl_l     # Ctrl (左 Ctrl，使用 Key.ctrl_l)
            }
        except Exception as e:
            print(f"初始化 pynput KeyboardController 失败: {str(e)}")
            raise RuntimeError(f"初始化 pynput KeyboardController 失败: {str(e)}")

    def press_key(self, key, duration=0.5):
        if key is None:
            print("默认: 键码为 None，无法按下")
            return
        key_char = chr(key).lower() if 65 <= key <= 90 or 48 <= key <= 57 else None
        if key_char:
            self.keyboard.press(key_char)
            time.sleep(duration)
            self.keyboard.release(key_char)
            print(f"默认: 按下并释放键 {key_char}，持续时间: {duration} 秒")
        elif key in self.function_key_map:
            mapped_key = self.function_key_map[key]
            self.keyboard.press(mapped_key)
            time.sleep(duration)
            self.keyboard.release(mapped_key)
            print(f"默认: 按下并释放功能键 {mapped_key} (键码 {key})，持续时间: {duration} 秒")
        else:
            print(f"默认: 不支持的键码 {key}")

    def hold_key(self, key):
        if key is None:
            print("默认: 键码为 None，无法持续按住")
            return
        if key in self.function_key_map:
            mapped_key = self.function_key_map[key]
            self.keyboard.press(mapped_key)
            print(f"默认: 持续按住功能键 {mapped_key} (键码 {key})")
        else:
            key_char = chr(key).lower() if 65 <= key <= 90 or 48 <= key <= 57 else None
            if key_char:
                self.keyboard.press(key_char)
                print(f"默认: 持续按住键 {key_char}")
            else:
                print(f"默认: 不支持的键码 {key} 用于持续按住")

    def release_key(self, key):
        if key is None:
            print("默认: 键码为 None，无需释放")
            return
        key_char = chr(key).lower() if 65 <= key <= 90 or 48 <= key <= 57 else None
        if key_char:
            self.keyboard.release(key_char)
            print(f"默认: 释放键 {key_char}")
        elif key in self.function_key_map:
            mapped_key = self.function_key_map[key]
            self.keyboard.release(mapped_key)
            print(f"默认: 释放功能键 {mapped_key} (键码 {key})")
        else:
            print(f"默认: 不支持的键码 {key}")

    def click(self, x, y, button="left"):
        win32api.SetCursorPos((x, y))
        if button == "left":
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            time.sleep(random1_time)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            print(f"默认: 左键点击已执行: ({x}, {y})")
        elif button == "right":
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            time.sleep(random1_time)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            print(f"默认: 右键点击已执行: ({x}, {y})")

class GhostInputController(InputController):
    def __init__(self):
        try:
            self.dll = cdll.LoadLibrary('./gbild64.dll')
            print(f"Open device: {self.dll.opendevice(0)}")
            print(f"Connected: {self.dll.isconnected()}")
            print(f"Model: {self.dll.getmodel()}")
        except Exception as e:
            raise RuntimeError(f"加载幽灵键鼠 DLL 失败: {e}")

    def press_key(self, key, duration=0.5):
        if key is None:
            print("幽灵: 键码为 None，无法按下")
            return
        print(self.dll.presskeybyvalue(key))
        time.sleep(duration)
        print(self.dll.releasekeybyvalue(key))
        print(f"幽灵: 按下并释放键 {key}，持续时间: {duration} 秒")

    def hold_key(self, key):
        if key is None:
            print("幽灵: 键码为 None，无法持续按住")
            return
        print(self.dll.presskeybyvalue(key))
        print(f"幽灵: 持续按住键 {key}")

    def release_key(self, key):
        if key is None:
            print("幽灵: 键码为 None，无需释放")
            return
        print(self.dll.releasekeybyvalue(key))
        print(f"幽灵: 释放键 {key}")

    def click(self, x, y, button="left"):
        print(self.dll.movemouseto(int(x), int(y)))
        if button == "left":
            print(self.dll.pressmousebutton(1))
            time.sleep(random1_time)
            print(self.dll.releasemousebutton(1))
            print(f"幽灵: 左键点击已执行: ({x}, {y})")
        elif button == "right":
            win32api.SetCursorPos((x, y))
            time.sleep(random1_time)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            time.sleep(random1_time)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            print(f"幽灵: 右键点击已执行 (win32api): ({x}, {y})")

class SceneNavigator:
    def __init__(self, game_title="地下城与勇士：创新世纪", input_controller=None):
        self.game_title = game_title
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
            'xuanzejuese_jiemian': cv2.imread(resource_path('image/xuanzejuese_jiemian.png'), 0)
        }
        for key, template in self.templates.items():
            if template is None:
                print(f"模板加载失败: {key} (路径: {resource_path(f'image/{key}.png')})")
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
        game_window = gw.getWindowsWithTitle(self.game_title)[0]
        current_time = time.time()
        town_detected = False

        sailiya_locations = self.utils.detect_template(gray_frame, self.templates['sailiya'])
        print(f"检测到塞利亚房间: {len(sailiya_locations)} 个位置")
        for x1, y1, x2, y2 in sailiya_locations:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"塞丽亚: ({x1},{y1})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
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
            town_detected = True

        if self.clicked_youxicaidan and not self.clicked_shijieditu:
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
                time.sleep(random6_time)
            town_detected = True

        diedang_locations = self.utils.detect_template(gray_frame, self.templates['diedangquandao_menkou'])
        print(f"检测到跌宕群岛门口: {len(diedang_locations)} 个位置")
        for x1, y1, x2, y2 in diedang_locations:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, f"跌宕群岛门口: ({x1},{y1})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            print("已经移动到跌宕群岛门口")
            self.utils.activate_window(game_window)
            time.sleep(random6_time)
            self.utils.click(45, 315, "right")
            town_detected = True

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

class MonsterAttack:
    def __init__(self, utils, yolo_model_path, monsters_data, skill_keys):
        self.utils = utils
        self.yolo_model = YOLO(yolo_model_path)
        self.monsters = monsters_data
        self.skill_keys = skill_keys
        self.skill_key_map = {
            'a': 65, 's': 83, 'd': 68, 'f': 70, 'g': 71, 'h': 72,
            'q': 81, 'w': 87, 'e': 69, 'r': 82, 't': 84, 'x': 88
        }
        self.current_direction = None

    def get_positions(self, gray_frame):
        renwu_locations = self.utils.detect_template(gray_frame, self.monsters['renwu']['template'])
        if renwu_locations:
            rx1, ry1, rx2, ry2 = renwu_locations[0]
            renwu_x = rx1 + (rx2 - rx1) // 2
            renwu_y = ry1 + 80
            return renwu_x, renwu_y
        return None, None

    def move_to_fixed_point(self, target_x=1060, target_y=369, direction=39):
        frame_counter = 0
        update_interval = 3

        with mss.mss() as sct:
            self.current_direction = None
            try:
                self.utils.press_key(direction, 0.2)
                print(f"第一次按下方向键 {'right' if direction == 39 else 'left' if direction == 37 else 'up' if direction == 38 else 'down'} 并释放")
            except Exception as e:
                print(f"第一次按键失败: {str(e)}")

            time.sleep(0.2)
            try:
                self.utils.hold_key(direction)
                self.current_direction = direction
                print(f"第二次按下方向键 {'right' if direction == 39 else 'left' if direction == 37 else 'up' if direction == 38 else 'down'} 并持续按住")
            except Exception as e:
                print(f"第二次按键失败: {str(e)}")

            while True:
                if frame_counter % update_interval == 0:
                    screenshot = sct.grab(region)
                    frame_rgb = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2RGB)
                    yolo_results = self.yolo_model.predict(frame_rgb)
                    for result in yolo_results:
                        for box in result.boxes:
                            cls_name = result.names[int(box.cls)]
                            if cls_name in ['small_monster', 'boss']:
                                if self.current_direction is not None:
                                    self.utils.release_key(self.current_direction)
                                    self.current_direction = None
                                print(f"检测到 {cls_name}，停止奔跑")
                                return True

                frame_counter += 1
                time.sleep(0.01)

    def move_to_target(self, target_x, target_y, stop_offset=50):
        direction = None
        with mss.mss() as sct:
            while True:
                screenshot = sct.grab(region)
                gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
                renwu_x, renwu_y = self.get_positions(gray_frame)
                if renwu_x is None or renwu_y is None:
                    print("未检测到 renwu，停止奔跑")
                    if direction:
                        self.utils.release_key(direction)
                    break

                print(f"renwu: ({renwu_x}, {renwu_y}), 目标: ({target_x}, {target_y})")
                dx = abs(renwu_x - target_x)
                dy = abs(renwu_y - target_y)

                new_direction = 39 if target_x > renwu_x else 37
                if direction != new_direction:
                    if direction:
                        self.utils.release_key(direction)
                    self.utils.press_key(new_direction, random.uniform(0.1311, 0.1511))
                    time.sleep(random.uniform(0.01011, 0.03011))
                    direction = new_direction

                if dx <= 100 and dy <= 50:
                    self.utils.release_key(direction)
                    print("到达目标位置，松开方向键")
                    return True
                time.sleep(0.05)
        return False

    def face_monster(self, renwu_x, monster_x):
        direction = 39 if monster_x > renwu_x else 37
        self.utils.press_key(direction, random.uniform(0.1311, 0.1511))
        print(f"调整方向朝 {'right' if direction == 39 else 'left'}")

    def attack_small_or_elite(self, frame, x1, y1, x2, y2):
        monster_x = x1 + (x2 - x1) // 2
        monster_y = y1 + (y2 - y1) // 2
        print(f"检测到普通怪物位置: ({monster_x}, {monster_y})")
        return self._attack_monster(frame, monster_x, monster_y, is_boss=False)

    def attack_boss(self, frame, x1, y1, x2, y2):
        monster_x = x1 + (x2 - x1) // 2
        monster_y = y1 + (y2 - y1) // 2
        print(f"检测到 Boss 位置: ({monster_x}, {monster_y})")
        return self._attack_monster(frame, monster_x, monster_y, is_boss=True)

    def _attack_monster(self, frame, monster_x, monster_y, is_boss=False):
        try:
            self.utils.activate_window(gw.getWindowsWithTitle("地下城与勇士：创新世纪")[0])
            print("游戏窗口已激活")
        except Exception as e:
            print(f"激活窗口失败: {e}")

        renwu_x, renwu_y = self.get_positions(cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY))
        if renwu_x is not None and renwu_y is not None:
            print(f"renwu 初始位置: ({renwu_x}, {renwu_y})")
            self.move_to_target(monster_x, monster_y)
        else:
            print("初始未检测到 renwu，但因检测到怪物，继续尝试移动并攻击")

        with mss.mss() as sct:
            while True:
                screenshot = sct.grab(region)
                gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
                renwu_x, renwu_y = self.get_positions(gray_frame)
                if renwu_x is not None and renwu_y is not None:
                    self.face_monster(renwu_x, monster_x)
                    print(f"renwu 当前位置: ({renwu_x}, {renwu_y})，开始攻击")
                else:
                    print("未检测到 renwu，默认朝怪物方向攻击")

                skill_count = random.randint(2, 3)
                print(f"计划释放 {skill_count} 个技能")
                for i in range(skill_count):
                    qianjin_locations = self.utils.detect_template(gray_frame, self.monsters['qianjin']['template'])
                    if qianjin_locations:
                        print("检测到 qianjin，表示小怪已死，立即停止攻击")
                        return True
                    skill_key = random.choice(self.skill_keys)
                    key_code = self.skill_key_map[skill_key]
                    print(f"释放技能 {skill_key} (第 {i+1}/{skill_count})")
                    self.utils.press_key(key_code, random.uniform(0.1311, 0.1511))
                    time.sleep(random.uniform(0.1011, 0.1511))
                    screenshot = sct.grab(region)
                    gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)

                qianjin_locations = self.utils.detect_template(gray_frame, self.monsters['qianjin']['template'])
                if qianjin_locations:
                    print("检测到 qianjin，表示小怪已死，立即停止攻击")
                    return True
                print("技能释放完毕，执行一次普通攻击 X")
                self.utils.press_key(88, random.uniform(0.01011, 0.03011))  # X 键普通攻击
                time.sleep(random.uniform(0.01011, 0.03011))
                screenshot = sct.grab(region)
                gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)

                current_frame_rgb = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2RGB)
                monster_still_exists = False
                monster_type = 'boss' if is_boss else 'elite_monster' if 'template' in self.monsters.get('elite_monster', {}) else 'small_monster'
                if monster_type == 'elite_monster':
                    locations = self.utils.detect_template(gray_frame, self.monsters['elite_monster']['template'])
                    monster_still_exists = any(abs(monster_x - (loc[0] + (loc[2] - loc[0]) // 2)) < 50 for loc in locations)
                else:
                    yolo_results = self.yolo_model.predict(current_frame_rgb)
                    for result in yolo_results:
                        for box in result.boxes:
                            if result.names[int(box.cls)] == monster_type:
                                mx1, my1, mx2, my2 = map(int, box.xyxy[0])
                                if abs(monster_x - (mx1 + (mx2 - mx1) // 2)) < 50:
                                    monster_still_exists = True
                                    break

                if not monster_still_exists:
                    print("怪物已消失，停止攻击")
                    return False

                renwu_x, renwu_y = self.get_positions(gray_frame)
                if renwu_x is None or renwu_y is None:
                    print("一轮攻击后未检测到 renwu，随机移动以尝试脱离遮挡")
                    direction = random.choice([37, 39])
                    self.utils.press_key(direction, random.uniform(0.4011, 0.6011))
                    time.sleep(random.uniform(0.4011, 0.6011))

class MonsterFighterA:
    def __init__(self, input_controller):
        self.utils = Utils(input_controller)
        self.monsters = {
            'small_monster': {'action': self.attack_small_or_elite, 'type': 'small'},
            'elite_monster': {'template': cv2.imread(resource_path('image/elite_monster.png'), 0), 'action': self.attack_small_or_elite, 'type': 'elite'},
            'boss': {'action': self.attack_boss, 'type': 'boss'},
            'qianjin': {'template': cv2.imread(resource_path('image/qianjin.png'), 0), 'action': self.run_to_qianjin, 'type': 'qianjin'},
            'renwu': {'template': cv2.imread(resource_path('image/renwu.png'), 0), 'type': 'player'},
            'shifoujixu': {'template': cv2.imread(resource_path('image/shifoujixu.png'), 0), 'action': self.pickup_boss_drops, 'type': 'pickup'},
            'zhongmochongbaizhe': {'template': cv2.imread(resource_path('image/zhongmochongbaizhe.png'), 0), 'type': 'map'}
        }
        self.retry_button_template = cv2.imread(resource_path('image/retry_button.png'), 0)
        if self.retry_button_template is None:
            print("加载失败: retry_button (路径: image/retry_button.png)")
        for name, data in self.monsters.items():
            if 'template' in data:
                if data['template'] is None:
                    print(f"加载失败: {name} (路径: image/{name}.png)")
                else:
                    height, width = data['template'].shape
                    print(f"模板加载成功: {name}, 尺寸: {width}x{height}")
        if any('template' in m and m['template'] is None for m in self.monsters.values()):
            raise ValueError("无法加载模板图像，请检查路径！")
        self.skill_keys = ['a', 's', 'd', 'f', 'g', 'h', 'q', 'w', 'e', 'r', 't']
        self.boss_skill = 'y'
        self.qianjin_reached = False
        self.boss_dead = False
        self.shifoujixu_detected_time = None
        self.attacker = MonsterAttack(self.utils, resource_path('models/best15.pt'), self.monsters, self.skill_keys)
        self.last_display_time = 0
        self.has_applied_buff = False  # 新增：buff 状态变量

    def run_to_qianjin(self, frame, x1, y1, x2, y2):
        game_window = gw.getWindowsWithTitle("地下城与勇士：创新世纪")[0]
        self.utils.activate_window(game_window)
        qianjin_x = x1 + (x2 - x1) // 2
        qianjin_y = y1 + (y2 - y1) // 2
        target_x = 1060
        target_y = 369

        if qianjin_x < target_x:
            direction = 39  # 向右
        else:
            direction = 37  # 向左

        print(f"检测到 qianjin，开始奔向固定坐标 (1060, 369)，方向: {'right' if direction == 39 else 'left' if direction == 37 else 'up' if direction == 38 else 'down'}")
        self.attacker.move_to_fixed_point(target_x=1060, target_y=369, direction=direction)
        self.qianjin_reached = True
        print("到达固定坐标或检测到小怪/Boss，停止奔跑")

    def attack_small_or_elite(self, frame, x1, y1, x2, y2):
        should_run_to_qianjin = self.attacker.attack_small_or_elite(frame, x1, y1, x2, y2)
        if should_run_to_qianjin:
            self.run_to_qianjin(frame, x1, y1, x2, y2)

    def attack_boss(self, frame, x1, y1, x2, y2):
        should_run_to_qianjin = self.attacker.attack_boss(frame, x1, y1, x2, y2)
        if should_run_to_qianjin:
            self.run_to_qianjin(frame, x1, y1, x2, y2)

    def is_gray(self, roi):
        mean_color = np.mean(roi, axis=(0, 1))
        b, g, r = mean_color
        color_diff = max(abs(r - g), abs(g - b), abs(b - r))
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mean_hsv = np.mean(roi_hsv, axis=(0, 1))
        saturation = mean_hsv[1]
        print(f"按钮颜色 - RGB: [{b:.1f}, {g:.1f}, {r:.1f}], 差异: {color_diff:.1f}, 饱和度: {saturation:.1f}")
        return color_diff < 10 and saturation < 100

    def pickup_boss_drops(self, frame, x1, y1, x2, y2):
        print("检测到 shifoujixu.png，Boss 已死，开始拾取")
        if self.attacker.current_direction is not None:
            self.utils.release_key(self.attacker.current_direction)
            self.attacker.current_direction = None
            print("检测到 shifoujixu，强制停止奔跑")
        game_window = gw.getWindowsWithTitle("地下城与勇士：创新世纪")[0]
        self.utils.activate_window(game_window)
        self.utils.press_key(86, random.uniform(0.1311, 0.1511))  # V
        print("按下 V 键聚集掉落物品")
        start_time = time.time()
        while time.time() - start_time < 3:
            self.utils.press_key(88, random.uniform(0.1311, 0.1511))  # X
        print("拾取完成")

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
        else:
            print("再次挑战按钮为灰色，当前角色刷图完成，退出并切换角色")
            self.utils.press_key(123, random.uniform(0.1311, 0.1511))  # F12
            return True
        time.sleep(random.uniform(0.4011, 0.6011))
        return False

    def process_frame(self, frame, gray_frame):
        start_time = time.time()
        detected_monsters = []
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
        yolo_results = self.attacker.yolo_model.predict(frame_rgb)
        for result in yolo_results:
            for box in result.boxes:
                cls_name = result.names[int(box.cls)]
                if cls_name in ['small_monster', 'boss']:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    detected_monsters.append((cls_name, x1, y1, x2, y2))

        for monster_name, monster_data in self.monsters.items():
            if 'template' in monster_data and monster_data['template'] is not None:
                locations = self.utils.detect_template(gray_frame, monster_data['template'], threshold=0.8)
                print(f"检测 {monster_name}，找到 {len(locations)} 个匹配，位置: {locations}")
                for x1, y1, x2, y2 in locations:
                    detected_monsters.append((monster_name, x1, y1, x2, y2))

        print(f"Process frame time: {time.time() - start_time:.3f} seconds")
        return detected_monsters

    def apply_buff(self):
        """施加 buff：按下 Ctrl 键"""
        print("施加 buff：按下 Ctrl 键")
        self.utils.press_key(17, random.uniform(0.1311, 0.1511))  # Ctrl 键（键码 17）
        print("Buff 施加完成")
        self.has_applied_buff = True

    def fight_monsters(self, frame, gray_frame):
        start_time = time.time()
        detected_monsters = self.process_frame(frame, gray_frame)
        should_pickup = False
        in_zhongmochongbaizhe = False
        shifoujixu_confirmed = False

        print(f"检测到的所有怪物: {detected_monsters}")

        in_zhongmochongbaizhe = any(
            monster_name == 'zhongmochongbaizhe' for monster_name, _, _, _, _ in detected_monsters)
        if not in_zhongmochongbaizhe:
            print("未检测到 zhongmochongbaizhe 地图，跳过怪物检测")
            return frame, False
        else:
            print("检测到 zhongmochongbaizhe 地图，继续处理怪物逻辑")
            if not self.has_applied_buff:
                self.apply_buff()

        shifoujixu_detected = any(monster_name == 'shifoujixu' for monster_name, _, _, _, _ in detected_monsters)
        if shifoujixu_detected:
            for monster_name, x1, y1, x2, y2 in detected_monsters:
                if monster_name == 'shifoujixu':
                    print("检测到 shifoujixu，停止所有刷怪操作并休眠 1.5 秒")
                    if self.attacker.current_direction is not None:
                        self.utils.release_key(self.attacker.current_direction)
                        self.attacker.current_direction = None
                        print("已释放方向键，停止移动")

                    sleep_start = time.time()
                    shifoujixu_start_time = None
                    shifoujixu_duration = 0.0
                    with mss.mss() as sct:
                        while time.time() - sleep_start < 1.5:
                            screenshot = sct.grab(region)
                            temp_gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
                            shifoujixu_locations = self.utils.detect_template(temp_gray_frame,
                                                                              self.monsters['shifoujixu']['template'],
                                                                              threshold=0.8)
                            if shifoujixu_locations:
                                if shifoujixu_start_time is None:
                                    shifoujixu_start_time = time.time()
                                    print(f"休眠期间首次检测到 shifoujixu，位置: {shifoujixu_locations[0]}")
                                shifoujixu_duration = time.time() - shifoujixu_start_time
                                print(f"shifoujixu 持续检测时间: {shifoujixu_duration:.2f} 秒")
                            else:
                                if shifoujixu_start_time is not None:
                                    print(f"shifoujixu 检测中断，持续时间: {shifoujixu_duration:.2f} 秒")
                                    shifoujixu_start_time = None
                            time.sleep(0.05)

                    if shifoujixu_duration >= 0.5:
                        print("shifoujixu 在 1.5 秒内持续存在超过 0.5 秒，确认 Boss 已死，开始拾取")
                        should_pickup = self.monsters['shifoujixu']['action'](frame, x1, y1, x2, y2)
                        shifoujixu_confirmed = True
                    else:
                        print("shifoujixu 在 1.5 秒内持续存在少于 0.5 秒，判定为误检测，继续刷怪")
                    break

        if shifoujixu_confirmed:
            print("shifoujixu 处理完成，跳过其他怪物操作")
            return frame, should_pickup

        for monster_name, x1, y1, x2, y2 in detected_monsters:
            if monster_name == 'zhongmochongbaizhe':
                continue

            color = (255, 255, 0) if monster_name in ['small_monster', 'elite_monster'] else (
                255, 0, 0) if monster_name == 'boss' else (0, 255, 255) if monster_name == 'qianjin' else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{monster_name}: ({x1},{y1})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            print(f"检测到 {monster_name}")

            if monster_name == 'qianjin':
                self.monsters[monster_name]['action'](frame, x1, y1, x2, y2)
            elif monster_name in ['small_monster', 'elite_monster', 'boss']:
                if self.qianjin_reached and not any(m[0] == 'qianjin' for m in detected_monsters):
                    print("qianjin 消失，进入打怪模式")
                    self.monsters[monster_name]['action'](frame, x1, y1, x2, y2)
                else:
                    self.monsters[monster_name]['action'](frame, x1, y1, x2, y2)

        current_time = time.time()
        if current_time - self.last_display_time >= 0.033:
            self.last_display_time = current_time

        print(f"Fight monsters time: {time.time() - start_time:.3f} seconds")
        return frame, should_pickup

class GameAutomationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.thread = None
        self.frame_queue = queue.Queue()
        self.is_verified = False
        self.current_role = 0
        self.total_roles = 1
        self.initUI()

    def initUI(self):
        self.setWindowTitle("DNF Automation")
        self.setGeometry(0, 600, 1067, 200)

        main_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        self.mode_label = QLabel("选择模式:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["深渊地图", "妖气追踪"])
        self.mode_combo.setCurrentIndex(0)

        self.input_label = QLabel("键鼠控制:")
        self.input_combo = QComboBox()
        self.input_combo.addItems(["默认", "幽灵键鼠"])
        self.input_combo.setCurrentIndex(0)

        self.role_label = QLabel("角色数量:")
        self.role_combo = QComboBox()
        self.role_combo.addItems([str(i) for i in range(1, 51)])
        self.role_combo.setCurrentIndex(0)

        left_layout.addWidget(self.mode_label)
        left_layout.addWidget(self.mode_combo)
        left_layout.addWidget(self.input_label)
        left_layout.addWidget(self.input_combo)
        left_layout.addWidget(self.role_label)
        left_layout.addWidget(self.role_combo)
        left_layout.addStretch()

        middle_layout = QVBoxLayout()
        self.start_button = QPushButton("开始")
        self.start_button.setEnabled(False)
        self.end_button = QPushButton("结束")
        self.end_button.setEnabled(False)
        self.status_label = QLabel("状态: 未运行")

        middle_layout.addWidget(self.start_button)
        middle_layout.addWidget(self.end_button)
        middle_layout.addWidget(self.status_label)
        middle_layout.addStretch()

        right_layout = QVBoxLayout()
        self.login_label = QLabel("请输入卡密:")
        self.key_input = QLineEdit()
        self.remember_checkbox = QCheckBox("记住密码")
        self.login_button = QPushButton("登录验证")

        config_file = Path.home() / ".game_script_config" / "config.json"
        try:
            with open(config_file, 'r', encoding='utf-8') as f:  # 指定编码为 UTF-8
                content = f.read().strip()  # 读取并去除首尾空白
                if content:  # 检查文件是否为空
                    config = json.loads(content)  # 使用 loads 解析字符串
                    if config.get('remember', False):
                        self.key_input.setText(config.get('key', ''))
                        self.remember_checkbox.setChecked(True)
                else:
                    print(f"配置文件 {config_file} 为空，跳过加载")
        except FileNotFoundError:
            print(f"配置文件 {config_file} 不存在，跳过加载")
        except json.JSONDecodeError as e:
            print(f"配置文件 {config_file} 格式错误: {e}，跳过加载")
        except Exception as e:
            print(f"读取配置文件 {config_file} 时发生未知错误: {e}，跳过加载")

        right_layout.addWidget(self.login_label)
        right_layout.addWidget(self.key_input)
        right_layout.addWidget(self.remember_checkbox)
        right_layout.addWidget(self.login_button)
        right_layout.addStretch()

        main_layout.addLayout(left_layout)
        main_layout.addLayout(middle_layout)
        main_layout.addLayout(right_layout)
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 1)
        main_layout.setStretch(2, 1)

        overall_layout = QVBoxLayout()
        overall_layout.addLayout(main_layout)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(80)
        overall_layout.addWidget(self.log_text)

        self.setLayout(overall_layout)

        self.start_button.clicked.connect(self.start_automation)
        self.end_button.clicked.connect(self.stop_automation)
        self.login_button.clicked.connect(self.verify_key)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(33)

    def log(self, message):
        self.log_text.append(f"{time.strftime('%H:%M:%S')} - {message}")

    def verify_key(self):
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, '错误', '请输入有效卡密')
            return

        machine_code = get_machine_code()
        try:
            response = requests.post(
                'http://139.196.94.227:5000/verify',
                json={'card': key, 'device_id': machine_code},  # 修改为 'card' 和 'device_id' 以匹配 server.py
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                message = data.get('message')
                expiry_date = data.get('expiry_date')

                config_file = Path.home() / ".game_script_config" / "config.json"
                config_dir = config_file.parent
                if not config_dir.exists():
                    config_dir.mkdir(parents=True)

                if status == "success":
                    with open(config_file, 'w') as f:
                        json.dump({
                            'key': key,
                            'expire': expiry_date,
                            'machine_code': machine_code,
                            'remember': self.remember_checkbox.isChecked()
                        }, f)
                    expire_time = datetime.strptime(expiry_date, "%Y-%m-%d %H:%M:%S")
                    if expire_time > datetime.now():
                        self.is_verified = True
                        self.start_button.setEnabled(True)
                        self.log(f"登录成功！有效期至：{expiry_date}")
                        QMessageBox.information(self, '成功', f'{message}！有效期至：{expiry_date}')
                    else:
                        self.log("卡密已过期，请更换有效卡密")
                        QMessageBox.warning(self, '错误', '卡密已过期，请更换有效卡密')
                else:
                    self.log(f"验证失败: {message}")
                    QMessageBox.warning(self, '错误', message)
            else:
                error_msg = response.json().get('message', '未知错误')
                self.log(f"服务器返回错误: {error_msg}")
                QMessageBox.critical(self, '错误', f'服务器返回错误: {error_msg}')
        except requests.exceptions.RequestException as e:
            self.log(f"连接服务器失败: {str(e)}")
            QMessageBox.critical(self, '错误', f'连接服务器失败: {str(e)}')

    def start_automation(self):
        if not self.is_verified:
            QMessageBox.warning(self, "提示", "请先通过卡密验证！")
            return
        if self.thread and self.thread.is_alive():
            QMessageBox.information(self, "提示", "自动化已在运行中！")
            return

        input_mode = self.input_combo.currentText()
        try:
            if input_mode == "默认":
                input_controller = DefaultInputController()
                self.log("使用默认键鼠控制 (pynput & win32api)")
            else:
                input_controller = GhostInputController()
                self.log("使用幽灵键鼠控制 (gbild64.dll)")
        except Exception as e:
            error_msg = f"初始化键鼠控制失败: {str(e)}"
            print(error_msg)
            self.log(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            return

        self.navigator = SceneNavigator(input_controller=input_controller)
        self.fighter = MonsterFighterA(input_controller=input_controller)

        self.stop_event.clear()
        self.start_button.setEnabled(False)
        self.end_button.setEnabled(True)
        self.status_label.setText("状态: 运行中")
        self.log("自动化开始")

        mode = self.mode_combo.currentText()
        if mode == "深渊地图":
            self.thread = threading.Thread(target=self.run_shenyuan_map, daemon=True)
        elif mode == "妖气追踪":
            self.thread = threading.Thread(target=self.run_yaoqi_tracking, daemon=True)
        self.thread.start()

    def stop_automation(self):
        if not self.thread or not self.thread.is_alive():
            QMessageBox.information(self, "提示", "自动化未运行！")
            return

        self.stop_event.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            self.log("线程未正常结束，可能需要强制关闭程序")
        self.start_button.setEnabled(True)
        self.end_button.setEnabled(False)
        self.status_label.setText("状态: 已停止")
        self.log("自动化停止")
        cv2.destroyAllWindows()

    def run_shenyuan_map(self):
        game_window = gw.getWindowsWithTitle("地下城与勇士：创新世纪")[0]
        game_window.moveTo(0, 0)
        self.navigator.utils.activate_window(game_window)
        time.sleep(1)

        self.total_roles = int(self.role_combo.currentText())
        self.current_role = 0

        with mss.mss() as sct:
            while not self.stop_event.is_set() and self.current_role < self.total_roles:
                try:
                    screenshot = sct.grab(region)
                    frame = np.array(screenshot)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    in_town = self.navigator.move_to_shenyuan_map(frame, gray_frame)
                    zhongmo_locations = self.navigator.utils.detect_template(gray_frame, self.navigator.templates['zhongmochongbaizhe'], threshold=0.8)
                    self.log(f"检测到 zhongmochongbaizhe: {len(zhongmo_locations)} 个位置")
                    in_monster_map = bool(zhongmo_locations)

                    if in_monster_map:
                        self.log("检测到 zhongmochongbaizhe.png，进入刷怪模式")
                        yincangshangdian_locations = self.navigator.utils.detect_template(gray_frame, self.navigator.templates['yincangshangdian'])
                        if yincangshangdian_locations:
                            self.log("检测到 yincangshangdian.png，暂停刷怪操作")
                            if self.fighter.attacker.current_direction is not None:
                                self.navigator.utils.release_key(self.fighter.attacker.current_direction)
                                self.fighter.attacker.current_direction = None
                                self.log("已释放方向键，暂停移动")
                            self.navigator.utils.activate_window(game_window)
                            self.navigator.utils.click(373, 39, "left")
                            self.log("已点击隐藏商店按钮 (373, 39)")
                            time.sleep(1)
                            self.log("隐藏商店操作完成，继续刷怪")

                        frame, should_pickup = self.fighter.fight_monsters(frame, gray_frame)
                        if should_pickup:
                            self.current_role += 1
                            self.log(f"角色 {self.current_role}/{self.total_roles} 已刷完，开始切换角色")
                            self.switch_role(game_window, sct)
                    elif in_town:
                        self.log("在城镇，继续导航")
                    else:
                        self.log("未检测到明确场景，跳过刷怪逻辑")

                    self.frame_queue.put(frame)
                    time.sleep(0.033)
                except Exception as e:
                    self.log(f"运行中发生错误: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(1)

    def switch_role(self, game_window, sct):
        time.sleep(3)
        screenshot = sct.grab(region)
        gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
        youxicaidan_locations = self.navigator.utils.detect_template(gray_frame, self.navigator.templates['youxicaidan'])
        self.log(f"检测到游戏菜单: {len(youxicaidan_locations)} 个位置")
        for yx1, yy1, yx2, yy2 in youxicaidan_locations:
            click_x = yx1 + (yx2 - yx1) // 2
            click_y = yy1 + (yy2 - yy1) // 2
            self.log(f"检测到 youxicaidan.png，点击坐标 ({click_x}, {click_y})")
            self.navigator.utils.activate_window(game_window)
            self.navigator.utils.click(click_x, click_y, "left")
            time.sleep(1)
            break
        else:
            self.log("未检测到 youxicaidan.png，切换可能失败")

        screenshot = sct.grab(region)
        gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
        xuanzejuese_locations = self.navigator.utils.detect_template(gray_frame, self.navigator.templates['xuanzejuese'])
        self.log(f"检测到选择角色按钮: {len(xuanzejuese_locations)} 个位置")
        for xx1, xy1, xx2, xy2 in xuanzejuese_locations:
            click_x = xx1 + (xx2 - xx1) // 2
            click_y = xy1 + (xy2 - xy1) // 2
            self.log(f"检测到 xuanzejuese.png，点击坐标 ({click_x}, {click_y})")
            self.navigator.utils.activate_window(game_window)
            self.navigator.utils.click(click_x, click_y, "left")
            time.sleep(1)
            break
        else:
            self.log("未检测到 xuanzejuese.png，切换可能失败")

        screenshot = sct.grab(region)
        gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
        xuanzejuese_jiemian_locations = self.navigator.utils.detect_template(gray_frame, self.navigator.templates['xuanzejuese_jiemian'])
        self.log(f"检测到选择角色界面: {len(xuanzejuese_jiemian_locations)} 个位置")
        if xuanzejuese_jiemian_locations:
            self.log("检测到 xuanzejuese_jiemian.png，切换角色")
            self.navigator.utils.press_key(39, random.uniform(0.1311, 0.1511))
            time.sleep(0.1)
            self.navigator.utils.press_key(32, random.uniform(0.1311, 0.1511))
            time.sleep(2)

            screenshot = sct.grab(region)
            gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
            sailiya_locations = self.navigator.utils.detect_template(gray_frame, self.navigator.templates['sailiya'])
            self.log(f"检测到塞利亚: {len(sailiya_locations)} 个位置")
            if sailiya_locations:
                self.log("检测到 sailiya.png，角色切换成功，重置状态")
                self.navigator.clicked_youxicaidan = False
                self.navigator.clicked_shijieditu = False
                self.fighter.qianjin_reached = False
                self.fighter.boss_dead = False
                self.fighter.has_applied_buff = False  # 重置 buff 状态
            else:
                self.log("未检测到 sailiya.png，切换可能失败")
        else:
            self.log("未检测到 xuanzejuese_jiemian.png，切换失败")

    def run_yaoqi_tracking(self):
        self.log("妖气追踪功能尚未实现")
        while not self.stop_event.is_set():
            time.sleep(1)
            self.log("等待妖气追踪逻辑...")

    def update_frame(self):
        try:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get_nowait()
                cv2.imshow('Game Automation', frame)
                if cv2.waitKey(1) == 27:
                    self.stop_automation()
        except queue.Empty:
            pass

def main():
    app = QApplication(sys.argv)
    main_window = GameAutomationWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()