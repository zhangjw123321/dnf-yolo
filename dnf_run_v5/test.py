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

# 游戏区域和随机延迟定义 (保持不变或微调)
region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
random1_time = round(random.uniform(0.1011, 0.1311), 4)  # 可以稍微缩短一些基础操作延时
random5_time = round(random.uniform(0.3011, 0.5011), 4)  # 同上
random6_time = round(random.uniform(1.5111, 1.8011), 4)  # 等待界面加载的时间，如果实际加载快，可以缩短


def resource_path(relative_path):
    """获取资源的绝对路径，适用于开发和 PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def get_machine_code():
    cmd = 'wmic cpu get ProcessorId'
    output = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
    return hashlib.sha256(output.encode()).hexdigest()


class Utils:
    def __init__(self, input_controller):
        self.input_controller = input_controller
        self.last_activate_time = 0
        self.activate_cooldown = 3  # 可以适当减少窗口激活冷却

    def activate_window(self, game_window):
        current_time = time.time()
        # 检查当前前台窗口是否已是目标窗口
        try:
            current_foreground_hwnd = win32gui.GetForegroundWindow()
            if game_window._hWnd == current_foreground_hwnd:
                # print("窗口已经是前台，跳过激活") # 调试用，可注释
                return True  # 返回True表示窗口已是前台或激活成功
        except Exception:
            pass  # 忽略获取窗口句柄的错误，继续尝试激活

        if current_time - self.last_activate_time < self.activate_cooldown:
            # print("窗口激活冷却中，跳过") # 调试用
            return False  # 返回False表示因冷却未激活

        try:
            win32gui.ShowWindow(game_window._hWnd, win32con.SW_RESTORE)  # 尝试恢复窗口
            win32gui.SetForegroundWindow(game_window._hWnd)  # 设置为前景
            # win32gui.SetActiveWindow(game_window._hWnd) # SetActiveWindow有时不可靠
            time.sleep(0.2)  # 给窗口响应一点时间

            # 再次确认
            current_foreground = win32gui.GetWindowText(win32gui.GetForegroundWindow())
            # print(f"当前前台窗口: {current_foreground}")
            if self.input_controller.game_title_keyword in current_foreground:  # 使用关键词判断
                # print(f"已激活窗口: {self.input_controller.game_title_keyword}")
                self.last_activate_time = current_time
                return True
            else:
                print(f"窗口激活可能失败，当前前台: {current_foreground}")
                return False
        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False

    def detect_template(self, gray_frame, template, threshold=0.9):
        if template is None or gray_frame is None:
            # print("模板或图像为空，无法检测") # 减少不必要的打印
            return []
        if gray_frame.shape[0] < template.shape[0] or gray_frame.shape[1] < template.shape[1]:
            # print("图像小于模板，无法检测")
            return []

        result = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)
        h, w = template.shape[:2]  # 注意，灰度图是 shape[0], shape[1]
        return [(pt[0], pt[1], pt[0] + w, pt[1] + h) for pt in zip(*locations[::-1])]

    def press_key(self, key, duration=0.1):  # 默认持续时间可以短一些
        self.input_controller.press_key(key, duration)

    def hold_key(self, key):
        self.input_controller.hold_key(key)

    def release_key(self, key):
        self.input_controller.release_key(key)

    def click(self, x, y, button="left"):
        self.input_controller.click(x, y, button)


class InputController:
    def __init__(self):
        self.game_title_keyword = "地下城与勇士：创新世纪"  # 用于窗口激活判断

    def press_key(self, key, duration=0.1):
        raise NotImplementedError

    def hold_key(self, key):
        raise NotImplementedError

    def release_key(self, key):
        raise NotImplementedError

    def click(self, x, y, button="left"):
        raise NotImplementedError

    def is_key_pressed(self, key_code):
        """检查特定键是否被按下 (需要平台特定实现, win32api GetAsyncKeyState)"""
        # 对于pynput, 内部状态跟踪比较复杂，通常不直接提供
        # 对于硬件模拟，DLL可能有接口
        # 这里用 win32api 尝试实现一个通用检测，主要用于方向键等
        # 注意：这个检测的是物理按键状态，可能不完全符合pynput的模拟状态
        return win32api.GetAsyncKeyState(key_code) & 0x8000 != 0


class DefaultInputController(InputController):
    def __init__(self):
        super().__init__()
        try:
            self.keyboard = KeyboardController()
            self.function_key_map = {
                # ... (保持不变)
                121: Key.f10, 123: Key.f12, 86: 'v', 88: 'x',
                37: Key.left, 38: Key.up, 39: Key.right, 40: Key.down,
                32: Key.space, 17: Key.ctrl_l
            }
            self.held_keys = set()  # 跟踪由 hold_key 按下的键
        except Exception as e:
            # ...
            raise RuntimeError(f"初始化 pynput KeyboardController 失败: {str(e)}")

    def _get_mapped_key(self, key_code):
        if 65 <= key_code <= 90:  # A-Z
            return chr(key_code).lower()
        elif 48 <= key_code <= 57:  # 0-9 (主键盘区)
            return chr(key_code)
        return self.function_key_map.get(key_code)

    def press_key(self, key_code, duration=0.1):
        mapped_key = self._get_mapped_key(key_code)
        if mapped_key:
            # print(f"默认: 按下 {mapped_key} (键码 {key_code})")
            self.keyboard.press(mapped_key)
            time.sleep(duration)  # 确保按键有足够时间被游戏识别
            self.keyboard.release(mapped_key)
            # print(f"默认: 释放 {mapped_key}")
        else:
            print(f"默认: 不支持的键码 {key_code} 用于press_key")

    def hold_key(self, key_code):
        mapped_key = self._get_mapped_key(key_code)
        if mapped_key and mapped_key not in self.held_keys:
            # print(f"默认: 按住 {mapped_key} (键码 {key_code})")
            self.keyboard.press(mapped_key)
            self.held_keys.add(mapped_key)
        elif not mapped_key:
            print(f"默认: 不支持的键码 {key_code} 用于hold_key")

    def release_key(self, key_code):
        mapped_key = self._get_mapped_key(key_code)
        if mapped_key and mapped_key in self.held_keys:
            # print(f"默认: 释放 {mapped_key} (键码 {key_code})")
            self.keyboard.release(mapped_key)
            self.held_keys.remove(mapped_key)
        elif mapped_key and mapped_key not in self.held_keys:
            # 如果尝试释放一个未被记录为按住的键，也尝试释放一下以防万一
            try:
                self.keyboard.release(mapped_key)
            except Exception:  # pynput不允许释放未按下的键
                pass
        elif not mapped_key:
            print(f"默认: 不支持的键码 {key_code} 用于release_key")

    def release_all_held_keys(self):  # 新增：释放所有按住的键，用于状态切换或异常处理
        keys_to_release = list(self.held_keys)
        for key_code_representation in keys_to_release:  # 这里存储的是mapped_key
            # 找到原始键码或直接用mapped_key释放
            # 为了简单，我们直接用 mapped_key (pynput能处理字符或Key对象)
            try:
                print(f"默认: 强制释放 {key_code_representation}")
                self.keyboard.release(key_code_representation)
                self.held_keys.remove(key_code_representation)
            except Exception as e:
                print(f"默认: 强制释放 {key_code_representation} 失败: {e}")

    def click(self, x, y, button="left"):
        # 确保坐标是整数
        x, y = int(x), int(y)
        win32api.SetCursorPos((x, y))
        # time.sleep(0.05) # 轻微延时确保鼠标到位
        if button == "left":
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            time.sleep(random1_time)  # 使用随机延时
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            # print(f"默认: 左键点击已执行: ({x}, {y})")
        elif button == "right":
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            time.sleep(random1_time)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            # print(f"默认: 右键点击已执行: ({x}, {y})")


class GhostInputController(InputController):
    def __init__(self):
        super().__init__()
        try:
            # 确保DLL路径正确
            dll_path = resource_path('gbild64.dll')  # 使用resource_path
            if not os.path.exists(dll_path):
                raise RuntimeError(f"幽灵键鼠 DLL 文件不存在: {dll_path}")
            self.dll = cdll.LoadLibrary(dll_path)
            if not self.dll.opendevice(0):  # 尝试打开设备
                raise RuntimeError(f"幽灵键鼠 Open device 失败: {self.dll.getlasterror()}")
            if not self.dll.isconnected():
                raise RuntimeError(f"幽灵键鼠 未连接: {self.dll.getlasterror()}")
            print(f"幽灵键鼠 Model: {self.dll.getmodel()}")
            self.held_keys_vk = set()  # 存储虚拟键码
        except Exception as e:
            raise RuntimeError(f"加载或初始化幽灵键鼠 DLL 失败: {e}")

    def press_key(self, key_code, duration=0.1):  # key_code 应为虚拟键码
        # print(f"幽灵: 按下键 {key_code}")
        self.dll.presskeybyvalue(key_code)
        time.sleep(duration)
        self.dll.releasekeybyvalue(key_code)
        # print(f"幽灵: 释放键 {key_code}")

    def hold_key(self, key_code):
        if key_code not in self.held_keys_vk:
            # print(f"幽灵: 按住键 {key_code}")
            self.dll.presskeybyvalue(key_code)
            self.held_keys_vk.add(key_code)

    def release_key(self, key_code):
        if key_code in self.held_keys_vk:
            # print(f"幽灵: 释放键 {key_code}")
            self.dll.releasekeybyvalue(key_code)
            self.held_keys_vk.remove(key_code)
        else:  # 即使没记录也尝试释放
            self.dll.releasekeybyvalue(key_code)

    def release_all_held_keys(self):  # 新增
        keys_to_release = list(self.held_keys_vk)
        for vk_code in keys_to_release:
            print(f"幽灵: 强制释放键 {vk_code}")
            self.dll.releasekeybyvalue(vk_code)
            self.held_keys_vk.remove(vk_code)

    def click(self, x, y, button="left"):
        # 幽灵键鼠的坐标系可能需要校准
        self.dll.movemouseto(int(x), int(y))
        # time.sleep(0.05) # 移动后短暂延时
        if button == "left":
            self.dll.pressmousebutton(1)  # 1 通常是左键
            time.sleep(random1_time)
            self.dll.releasemousebutton(1)
            # print(f"幽灵: 左键点击已执行: ({x}, {y})")
        elif button == "right":
            # 查阅 gbild64.dll 的文档看右键是哪个值，通常是 2
            # 如果dll支持 pressmousebutton(2)
            self.dll.pressmousebutton(2)
            time.sleep(random1_time)
            self.dll.releasemousebutton(2)
            # print(f"幽灵: 右键点击已执行 (DLL): ({x}, {y})")
            # 如果DLL不支持，回退到 win32api (但幽灵键鼠的目的就是绕过这个)
            # win32api.SetCursorPos((int(x), int(y)))
            # win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, int(x), int(y), 0, 0)
            # time.sleep(random1_time)
            # win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, int(x), int(y), 0, 0)
            # print(f"幽灵: 右键点击已执行 (win32api fallback): ({x}, {y})")


class SceneNavigator:
    def __init__(self, game_title="地下城与勇士：创新世纪", input_controller=None):
        self.game_title = game_title
        self.utils = Utils(input_controller)
        self.input_controller = input_controller  # 保存一份引用
        self.templates = {
            'sailiya': cv2.imread(resource_path('image/sailiya.png'), 0),
            'shenyuan': cv2.imread(resource_path('image/shenyuan.png'), 0),  # 世界地图上的深渊图标
            'diedangquandao_menkou': cv2.imread(resource_path('image/diedangqundao_menkou.png'), 0),
            'shenyuan_xuanze': cv2.imread(resource_path('image/shenyuan_xuanze.png'), 0),  # 进入副本前的难度选择界面
            'zhongmochongbaizhe': cv2.imread(resource_path('image/zhongmochongbaizhe.png'), 0),  # 副本内的标识
            'youxicaidan': cv2.imread(resource_path('image/youxicaidan.png'), 0),
            'shijieditu': cv2.imread(resource_path('image/shijieditu.png'), 0),  # 菜单里的世界地图按钮
            'yincangshangdian': cv2.imread(resource_path('image/yincangshangdian.png'), 0),
            'xuanzejuese': cv2.imread(resource_path('image/xuanzejuese.png'), 0),  # 菜单里的选择角色按钮
            'xuanzejuese_jiemian': cv2.imread(resource_path('image/xuanzejuese_jiemian.png'), 0)  # 角色选择列表界面
        }
        # ... (模板加载检查)
        self.reset_navigation_state()  # 初始化导航状态

    def reset_navigation_state(self):
        print("导航状态已重置")
        self.last_right_press_time = 0
        # self.right_key_duration = 5 # 这个似乎未使用
        # self.right_key_active = False # 这个似乎未使用
        self.last_shenyuan_click_time = 0
        self.shenyuan_click_cooldown = 2  # 缩短冷却
        self.in_town_phase = "sailiya_room"  # 更细致的城镇状态: sailiya_room, world_map, dungeon_entrance
        self.clicked_youxicaidan = False
        self.clicked_shijieditu = False

    def move_to_shenyuan_map(self, frame, gray_frame, game_window):
        # 返回值: True 表示仍在城镇导航流程中, False 表示可能已进入副本或完成导航到副本门口
        # 激活窗口放在具体操作前

        # 优先检测是否已在目标选择界面或门口，从后往前判断状态
        shenyuan_xuanze_locations = self.utils.detect_template(gray_frame, self.templates['shenyuan_xuanze'], 0.85)
        if shenyuan_xuanze_locations:
            print("检测到 shenyuan_xuanze.png，点击进入深渊 (717, 471)")
            if self.utils.activate_window(game_window):
                self.utils.click(717, 471, "left")
                time.sleep(random6_time)  # 等待进图加载
            self.in_town_phase = "entered_dungeon"  # 标记已进图
            return False  # 导航结束

        diedang_locations = self.utils.detect_template(gray_frame, self.templates['diedangquandao_menkou'], 0.85)
        if diedang_locations:
            print("已在跌宕群岛门口，右键选择深渊")
            if self.utils.activate_window(game_window):
                # 根据实际游戏操作，可能需要先靠近一点
                self.utils.click(45, 315, "right")  # 假设这是选择深渊的操作点
                time.sleep(1.0)  # 等待菜单弹出
            self.in_town_phase = "at_dungeon_entrance"  # 更新状态
            # 下一帧应该能检测到 shenyuan_xuanze
            return True  # 仍在城镇导航 (副本门口也算广义城镇导航)

        shenyuan_map_icon_locations = self.utils.detect_template(gray_frame, self.templates['shenyuan'], 0.85)
        if shenyuan_map_icon_locations and self.in_town_phase == "world_map":
            current_time = time.time()
            if current_time - self.last_shenyuan_click_time >= self.shenyuan_click_cooldown:
                x1, y1, x2, y2 = shenyuan_map_icon_locations[0]
                click_x = x1 + (x2 - x1) // 2
                click_y = y1 + (y2 - y1) // 2
                print(f"世界地图上检测到 shenyuan.png，点击坐标 ({click_x}, {click_y})")
                if self.utils.activate_window(game_window):
                    self.utils.click(click_x, click_y, "left")
                    self.last_shenyuan_click_time = current_time
                    time.sleep(random5_time)  # 等待地图切换或加载
                # 下一帧应该能检测到 diedang_locations
                return True  # 仍在城镇导航

        # 处理赛利亚房间内的逻辑
        sailiya_locations = self.utils.detect_template(gray_frame, self.templates['sailiya'], 0.85)
        if sailiya_locations and self.in_town_phase == "sailiya_room":
            if not self.clicked_youxicaidan:
                youxicaidan_locations = self.utils.detect_template(gray_frame, self.templates['youxicaidan'])
                if youxicaidan_locations:
                    yx1, yy1, yx2, yy2 = youxicaidan_locations[0]
                    click_x = yx1 + (yx2 - yx1) // 2
                    click_y = yy1 + (yy2 - yy1) // 2
                    print(f"检测到 youxicaidan.png，点击 ({click_x}, {click_y})")
                    if self.utils.activate_window(game_window):
                        self.utils.click(click_x, click_y, "left")
                        self.clicked_youxicaidan = True
                        time.sleep(0.5)  # 等待菜单展开
                    return True

            if self.clicked_youxicaidan and not self.clicked_shijieditu:
                shijieditu_locations = self.utils.detect_template(gray_frame, self.templates['shijieditu'])
                if shijieditu_locations:
                    sx1, sy1, sx2, sy2 = shijieditu_locations[0]
                    click_x = sx1 + (sx2 - sx1) // 2
                    click_y = sy1 + (sy2 - sy1) // 2
                    print(f"检测到 shijieditu.png，点击 ({click_x}, {click_y})")
                    if self.utils.activate_window(game_window):
                        self.utils.click(click_x, click_y, "left")
                        self.clicked_shijieditu = True
                        self.in_town_phase = "world_map"  # 更新状态
                        time.sleep(1.0)  # 等待世界地图加载
                    return True

            # 如果在赛利亚房间，但已点击菜单和世界地图，说明逻辑卡住了，重置一下让他重新点
            if self.clicked_youxicaidan and self.clicked_shijieditu:
                print("在赛利亚房间但已标记点击过世界地图，可能卡住，重置导航标记。")
                self.clicked_youxicaidan = False
                self.clicked_shijieditu = False

            return True  # 仍在赛利亚房间处理

        # 如果以上都不是，且之前的状态不是已进图，则认为仍在城镇的某个环节
        if self.in_town_phase != "entered_dungeon":
            # print(f"当前城镇导航阶段: {self.in_town_phase}, 未匹配到特定操作场景, 保持城镇状态")
            return True

        return False  # 默认认为导航已结束或不在城镇导航流程


class MonsterAttack:
    def __init__(self, utils, yolo_model_path, monsters_data, skill_keys, input_controller):
        self.utils = utils
        self.input_controller = input_controller  # 保存引用
        self.yolo_model = YOLO(yolo_model_path)
        self.monsters = monsters_data  # 包含模板
        self.skill_keys = skill_keys
        self.skill_key_map = {  # 确保这些是虚拟键码 (VK_CODE)
            'a': 0x41, 's': 0x53, 'd': 0x44, 'f': 0x46, 'g': 0x47, 'h': 0x48,
            'q': 0x51, 'w': 0x57, 'e': 0x45, 'r': 0x52, 't': 0x54, 'x': 0x58,  # X键
            # 确保其他常用键也在这里，比如 Ctrl (VK_CONTROL = 0x11)
            'ctrl': 0x11, 'space': 0x20, 'f10': 0x79, 'f12': 0x7B, 'v_key': 0x56,  # V键
            'left_arrow': 0x25, 'up_arrow': 0x26, 'right_arrow': 0x27, 'down_arrow': 0x28
        }
        self.current_move_direction = None  # 当前持续按住的方向键 (VK_CODE)

        self.yolo_last_detection_time = 0
        self.yolo_detection_interval = 0.3  # 秒, 降低YOLO调用频率
        self.yolo_results_cache = None

    def get_yolo_detections(self, frame_rgb, force_update=False):
        current_time = time.time()
        # verbose=False to reduce console spam from YOLO
        if force_update or (
                current_time - self.yolo_last_detection_time > self.yolo_detection_interval) or self.yolo_results_cache is None:
            self.yolo_results_cache = self.yolo_model.predict(frame_rgb, verbose=False, conf=0.5)  # 增加conf阈值
            self.yolo_last_detection_time = current_time
        return self.yolo_results_cache

    def get_character_position(self, gray_frame):  # 重命名 get_positions
        # 假设 renwu.png 的中心底部是角色脚底的基准点
        renwu_template = self.monsters.get('renwu', {}).get('template')
        if renwu_template is None: return None

        # 降低检测频率，如果角色位置不经常剧烈变动
        # 或者只在需要时调用
        locations = self.utils.detect_template(gray_frame, renwu_template, threshold=0.80)  # 阈值可能需要调整
        if locations:
            rx1, ry1, rx2, ry2 = locations[0]  # 取第一个匹配的
            char_x = rx1 + (rx2 - rx1) // 2
            char_y = ry2  # 脚底Y坐标
            return char_x, char_y
        return None

    def move_to_fixed_point(self, target_x=1060, target_y=369, move_direction_vk=0x27):  # 默认向右 (VK_RIGHT)
        # 此函数用于长距离跑图，例如 "前进" 后
        # target_x, target_y 可能是象征性的终点，主要靠方向
        # move_direction_vk: 要按住的方向键的虚拟键码

        print(f"开始向固定点移动，方向键: {move_direction_vk}")
        self.utils.hold_key(move_direction_vk)
        self.current_move_direction = move_direction_vk

        start_time = time.time()
        max_run_duration = 8  # 秒，防止无限跑
        last_char_pos_check_time = 0
        char_pos_check_interval = 0.5  # 秒, 每隔多久检查一次角色是否卡住 (如果能获取位置)

        with mss.mss() as sct:
            while True:
                current_time = time.time()
                if current_time - start_time > max_run_duration:
                    print("跑图超时，停止移动")
                    break

                # 降低截图和检测频率
                time.sleep(0.05)  # 主循环延时，减少CPU占用

                # 每隔一小段时间进行一次怪物检测
                # 这里可以不用YOLO那么频繁，或者只用YOLO检测BOSS级的威胁
                screenshot = sct.grab(region)
                frame_arr = np.array(screenshot)
                frame_rgb = cv2.cvtColor(frame_arr, cv2.COLOR_BGRA2RGB)

                # 使用YOLO检测怪物，但不是每帧
                yolo_results = self.get_yolo_detections(frame_rgb)  # 使用带缓存和间隔的函数
                if yolo_results:
                    for result in yolo_results:
                        for box in result.boxes:
                            cls_name = result.names[int(box.cls)]
                            # 如果检测到任何怪物，就停下来让主战斗逻辑处理
                            if cls_name in ['small_monster', 'boss', 'elite_monster_yolo_label']:  # 假设精英怪也有YOLO标签
                                print(f"跑图中检测到怪物 {cls_name}，停止跑图")
                                # self.utils.release_key(self.current_move_direction) # 在外部 fighter 中统一释放
                                # self.current_move_direction = None
                                return True  # 表示遇到怪了

                # 可选：如果能稳定获取角色位置，可以判断是否到达目标点X附近
                # gray_frame_for_char = cv2.cvtColor(frame_arr, cv2.COLOR_BGRA2GRAY)
                # char_pos = self.get_character_position(gray_frame_for_char)
                # if char_pos:
                #     char_x, _ = char_pos
                #     if (move_direction_vk == self.skill_key_map['right_arrow'] and char_x >= target_x - 50) or \
                #        (move_direction_vk == self.skill_key_map['left_arrow'] and char_x <= target_x + 50):
                #         print("已到达固定目标点X附近，停止跑图")
                #         # self.utils.release_key(self.current_move_direction)
                #         # self.current_move_direction = None
                #         return False # 表示到达目标（或接近）

        # 如果循环结束（例如超时），也确保释放按键
        # self.utils.release_key(self.current_move_direction)
        # self.current_move_direction = None
        return False  # 表示跑图结束（可能超时，可能到达）

    def move_to_target(self, target_monster_x, target_monster_y, gray_frame_for_char_pos, stop_offset_x=80):
        # gray_frame_for_char_pos: 当前帧的灰度图，用于获取角色位置
        # stop_offset_x: 离目标多近时停下 (X轴)

        char_pos = self.get_character_position(gray_frame_for_char_pos)
        if not char_pos:
            print("无法获取角色位置，无法精确移动到目标")
            # 尝试基于怪物位置做一个猜测的移动
            # (或者直接返回False，让外部逻辑处理)
            return False

        char_x, _ = char_pos
        dx = target_monster_x - char_x

        if abs(dx) <= stop_offset_x:
            # print(f"角色已在目标X范围内: char_x={char_x}, target_x={target_monster_x}")
            if self.current_move_direction:  # 如果之前在移动，停下来
                self.utils.release_key(self.current_move_direction)
                self.current_move_direction = None
            return True  # 已到达

        needed_direction_vk = self.skill_key_map['right_arrow'] if dx > 0 else self.skill_key_map['left_arrow']

        if self.current_move_direction != needed_direction_vk:
            if self.current_move_direction:
                self.utils.release_key(self.current_move_direction)
            self.utils.hold_key(needed_direction_vk)
            self.current_move_direction = needed_direction_vk
            # print(f"向 {'右' if dx > 0 else '左'} 移动以接近目标")

        # 保持移动状态，此函数只负责“朝向并按住移动键”，不在此处等待到达
        # 返回 False 表示尚未到达，仍在移动中 (或刚开始移动)
        return False

    def face_monster(self, monster_x, gray_frame_for_char_pos):
        # 确保角色朝向怪物
        char_pos = self.get_character_position(gray_frame_for_char_pos)
        if not char_pos: return

        char_x, _ = char_pos
        if monster_x > char_x:  # 怪物在右边
            self.utils.press_key(self.skill_key_map['right_arrow'], duration=0.05)  # 短按调整方向
        else:  # 怪物在左边
            self.utils.press_key(self.skill_key_map['left_arrow'], duration=0.05)
        time.sleep(0.1)  # 等待转向生效

    def _attack_monster_once(self, is_boss):  # 执行一轮攻击
        # 激活窗口应在更高层处理，或在具体按键前检查
        num_skills = random.randint(1, 2) if not is_boss else random.randint(2, 3)
        # print(f"计划释放 {num_skills} 个技能")

        # 可以在这里加入对 "前进" 模板的检测，如果出现则中断攻击
        # screenshot = mss.mss().grab(region)
        # current_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
        # if self.utils.detect_template(current_gray, self.monsters['qianjin']['template'], 0.85):
        #    print("攻击中检测到前进，中断攻击")
        #    return "qianjin_detected" # 返回特殊状态

        for _ in range(num_skills):
            skill_key_char = random.choice(self.skill_keys)  # a,s,d...
            skill_vk = self.skill_key_map.get(skill_key_char)
            if skill_vk:
                # print(f"释放技能 {skill_key_char}")
                self.utils.press_key(skill_vk, duration=random.uniform(0.08, 0.12))
                time.sleep(random.uniform(0.1, 0.2))  # 技能CD或后摇，缩短一点
            # 每次技能后都快速检测 "前进"
            # (这会增加截图开销，需要权衡)

        # print("一轮技能后接普通攻击X")
        self.utils.press_key(self.skill_key_map['x'], duration=random.uniform(0.05, 0.1))
        time.sleep(random.uniform(0.1, 0.15))  # 普攻后摇
        return "attack_done"

    def attack_target(self, target_monster_info, current_frame_rgb, current_gray_frame):
        # target_monster_info: {'name': str, 'box': (x1,y1,x2,y2), 'source': str}
        # 返回: "monster_killed", "monster_still_exists", "qianjin_detected", "error"

        monster_x = target_monster_info['box'][0] + (target_monster_info['box'][2] - target_monster_info['box'][0]) // 2
        monster_y = target_monster_info['box'][1] + (target_monster_info['box'][3] - target_monster_info['box'][1]) // 2
        is_boss = target_monster_info['name'] == 'boss'

        # 1. 移动到怪物附近 (如果需要)
        # move_to_target 现在不阻塞，所以需要一个循环或者状态来管理移动
        # 为简化，这里假设一个简单的移动逻辑：如果不在范围内，移动一步，然后下一帧再判断
        if not self.move_to_target(monster_x, monster_y, current_gray_frame, stop_offset_x=60):
            # print("正在移动向怪物...")
            return "monster_still_exists"  # 表示仍在移动中，怪物自然还存在

        # 到达怪物附近后，停止之前的移动 (如果还在移动)
        if self.current_move_direction:
            self.utils.release_key(self.current_move_direction)
            self.current_move_direction = None
            # print("到达怪物附近，停止移动")

        # 2. 调整朝向
        self.face_monster(monster_x, current_gray_frame)

        # 3. 执行一轮攻击
        attack_result = self._attack_monster_once(is_boss)
        if attack_result == "qianjin_detected":
            return "qianjin_detected"

        # 4. 攻击后，重新获取帧并判断怪物是否死亡 (关键优化点)
        # 这里用传入的帧作为攻击前的状态，攻击后需要新帧来判断
        # 实际应用中，这里应该 grab 一个新帧
        time.sleep(0.2)  # 等待攻击动画和伤害数字出现
        with mss.mss() as sct:  # 获取新帧
            screenshot_after_attack = sct.grab(region)
        frame_after_attack_arr = np.array(screenshot_after_attack)
        rgb_after_attack = cv2.cvtColor(frame_after_attack_arr, cv2.COLOR_BGRA2RGB)
        # gray_after_attack = cv2.cvtColor(frame_after_attack_arr, cv2.COLOR_BGRA2GRAY) # 如果模板匹配也用

        # 使用YOLO判断 (强制刷新缓存)
        yolo_results_after_attack = self.get_yolo_detections(rgb_after_attack, force_update=True)
        monster_still_exists_yolo = False
        if yolo_results_after_attack:
            for res in yolo_results_after_attack:
                for box_data in res.boxes:
                    detected_cls_name = res.names[int(box_data.cls)]
                    if detected_cls_name == target_monster_info['name']:  # 必须是同名怪
                        mx1, my1, mx2, my2 = map(int, box_data.xyxy[0])
                        detected_monster_center_x = mx1 + (mx2 - mx1) // 2
                        # 判断是否是之前攻击的那个怪或其附近 (允许一定范围误差)
                        if abs(monster_x - detected_monster_center_x) < 100:  # X轴100像素内
                            monster_still_exists_yolo = True
                            # print(f"YOLO 在攻击后仍然检测到 {detected_cls_name} 在附近")
                            break
                if monster_still_exists_yolo: break

        if not monster_still_exists_yolo:
            # 如果是精英怪，YOLO可能识别为普通怪，或者YOLO模型对精英怪识别不准，再用模板确认
            if target_monster_info['name'] == 'elite_monster':
                # elite_template = self.monsters.get('elite_monster', {}).get('template')
                # if elite_template is not None:
                #     # 需要用攻击后的灰度图
                #     gray_after_attack = cv2.cvtColor(frame_after_attack_arr, cv2.COLOR_BGRA2GRAY)
                #     locations = self.utils.detect_template(gray_after_attack, elite_template, threshold=0.8)
                #     if any(abs(monster_x - (loc[0] + (loc[2] - loc[0]) // 2)) < 80 for loc in locations):
                #         print("精英怪模板在攻击后仍然检测到")
                #         monster_still_exists_yolo = True # 复用此变量
                pass  # 精英怪逻辑可以更复杂，暂时简化

        if monster_still_exists_yolo:
            # print(f"{target_monster_info['name']} 似乎仍然存在，准备再次攻击或等待")
            return "monster_still_exists"
        else:
            print(f"{target_monster_info['name']} 在攻击后未被检测到，判定为已击杀")
            return "monster_killed"


# --- MonsterFighterA (核心战斗逻辑) ---
class MonsterFighterA:
    def __init__(self, input_controller, utils_instance):  # 传入 utils 实例
        self.utils = utils_instance  # 使用传入的 utils
        self.input_controller = input_controller  # 保存引用
        self.monsters_templates = {  # 只存模板，YOLO标签在MonsterAttack中处理
            'elite_monster': {'template': cv2.imread(resource_path('image/elite_monster.png'), 0), 'type': 'elite'},
            'qianjin': {'template': cv2.imread(resource_path('image/qianjin.png'), 0), 'type': 'navigation'},
            'renwu': {'template': cv2.imread(resource_path('image/renwu.png'), 0), 'type': 'player'},
            'shifoujixu': {'template': cv2.imread(resource_path('image/shifoujixu.png'), 0), 'type': 'event'},
            'zhongmochongbaizhe': {'template': cv2.imread(resource_path('image/zhongmochongbaizhe.png'), 0),
                                   'type': 'map_indicator'}
        }
        self.retry_button_template = cv2.imread(resource_path('image/retry_button.png'), 0)
        # ... (模板加载检查) ...

        # 技能键字符列表，MonsterAttack中会映射到VK_CODE
        skill_keys_chars = ['a', 's', 'd', 'f', 'g', 'h', 'q', 'w', 'e', 'r', 't']

        # MonsterAttack的实例现在由外部创建并传入，或者在这里创建时传入utils和input_controller
        self.attacker = MonsterAttack(self.utils, resource_path('models/best15.pt'), self.monsters_templates,
                                      skill_keys_chars, self.input_controller)

        self.reset_combat_state()

    def reset_combat_state(self):
        print("战斗状态已重置")
        self.qianjin_reached_current_room = False  # 当前房间是否已通过“前进”点
        self.boss_fight_active = False  # 是否正在打Boss
        self.shifoujixu_detected_time = None
        self.has_applied_buff = False
        self.current_target_monster_info = None  # 当前攻击目标的信息
        self.attack_consecutive_failures = 0  # 连续攻击但怪物仍在的次数

        # 确保所有按键都已释放
        if hasattr(self.input_controller, 'release_all_held_keys'):
            self.input_controller.release_all_held_keys()
        self.attacker.current_move_direction = None  # 也重置攻击者内部的移动状态

    def run_to_qianjin(self, frame, qianjin_box, game_window):  # qianjin_box 是 (x1,y1,x2,y2)
        if not self.utils.activate_window(game_window): return

        # qianjin_x_center = qianjin_box[0] + (qianjin_box[2] - qianjin_box[0]) // 2
        # 简单处理：一般“前进”都在屏幕右侧，所以向右跑
        # 也可以根据角色当前位置和 qianjin 图标位置决定方向
        # gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY) # 假设frame是BGRA
        # char_pos = self.attacker.get_character_position(gray_frame)
        # direction_vk = self.attacker.skill_key_map['right_arrow'] # 默认向右
        # if char_pos and char_pos[0] > qianjin_x_center: # 如果角色在前进图标右边（不太可能）
        #    direction_vk = self.attacker.skill_key_map['left_arrow']

        print("检测到 qianjin，开始跑图")
        # move_to_fixed_point 会自己按住方向键
        met_monster_while_running = self.attacker.move_to_fixed_point(
            move_direction_vk=self.attacker.skill_key_map['right_arrow'])

        # 跑图结束后，释放按键（如果 move_to_fixed_point 内部没释放干净）
        if self.attacker.current_move_direction:
            self.utils.release_key(self.attacker.current_move_direction)
            self.attacker.current_move_direction = None

        if met_monster_while_running:
            print("跑图时遇到怪物，由战斗逻辑处理")
        else:
            print("跑图结束（可能到达或超时）")
        self.qianjin_reached_current_room = True  # 标记这个“前进”点已处理

    def is_button_gray(self, button_roi_bgr):  # 判断按钮是否是灰色（不可用）
        if button_roi_bgr is None or button_roi_bgr.size == 0: return True  # 无法判断则认为不可用
        # 简单方法：检查饱和度。灰色饱和度低。
        hsv_roi = cv2.cvtColor(button_roi_bgr, cv2.COLOR_BGR2HSV)
        saturation = hsv_roi[:, :, 1].mean()
        # print(f"按钮区域平均饱和度: {saturation}")
        return saturation < 30  # 饱和度阈值需要调试

    def handle_pickup_and_retry(self, frame_bgr, shifoujixu_box, game_window):  # 返回 True 表示需要切换角色
        print("Boss已死，处理拾取和重试/退出")
        if not self.utils.activate_window(game_window): return False  # 激活失败则不继续

        # 停止所有移动
        if self.attacker.current_move_direction:
            self.utils.release_key(self.attacker.current_move_direction)
            self.attacker.current_move_direction = None

        self.utils.press_key(self.attacker.skill_key_map['v_key'])  # V键聚物
        time.sleep(0.5)
        # 连续按X拾取一段时间
        pickup_start_time = time.time()
        while time.time() - pickup_start_time < 2.5:  # 拾取2.5秒
            self.utils.press_key(self.attacker.skill_key_map['x'], duration=0.1)
            time.sleep(0.15)
        print("拾取动作完成")

        # 检查 "再次挑战" 按钮状态
        # 需要重新截图，因为上面的拾取动作改变了画面
        with mss.mss() as sct:
            screenshot_for_retry = sct.grab(region)
        frame_for_retry_arr = np.array(screenshot_for_retry)
        gray_for_retry = cv2.cvtColor(frame_for_retry_arr, cv2.COLOR_BGRA2GRAY)
        bgr_for_retry = cv2.cvtColor(frame_for_retry_arr, cv2.COLOR_BGRA2BGR)

        retry_locations = self.utils.detect_template(gray_for_retry, self.retry_button_template, threshold=0.8)
        if not retry_locations:
            print("未找到'再次挑战'按钮，可能情况有变，默认尝试退出到角色选择")
            self.utils.press_key(self.attacker.skill_key_map['f12'])  # F12返回角色选择
            time.sleep(random5_time)
            return True  # 需要切换角色

        rx1, ry1, rx2, ry2 = retry_locations[0]
        # 从BGR图中提取按钮ROI来判断颜色
        button_roi = bgr_for_retry[ry1:ry2, rx1:rx2]

        if not self.is_button_gray(button_roi):
            print("'再次挑战'按钮可用，点击重试 (F10)")
            self.utils.press_key(self.attacker.skill_key_map['f10'])
            time.sleep(random6_time)  # 等待重新进图
            self.reset_combat_state()  # 重置战斗状态以刷下一轮
            return False  # 不切换角色，继续刷
        else:
            print("'再次挑战'按钮灰色（不可用），退出到角色选择 (F12)")
            self.utils.press_key(self.attacker.skill_key_map['f12'])
            time.sleep(random5_time)  # 等待返回角色选择界面
            return True  # 需要切换角色

    def process_detected_objects(self, frame_bgr, gray_frame):
        # 返回检测到的所有对象列表: [{'name': str, 'box': (x1,y1,x2,y2), 'source': 'yolo'/'template'}, ...]
        detected_objects = []
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # 1. YOLO检测 (怪物为主)
        yolo_results = self.attacker.get_yolo_detections(frame_rgb)
        if yolo_results:
            for result in yolo_results:
                for box_data in result.boxes:
                    cls_name = result.names[int(box_data.cls)]
                    if cls_name in ['small_monster', 'boss']:  # 按需添加YOLO能识别的其他类型
                        x1, y1, x2, y2 = map(int, box_data.xyxy[0])
                        detected_objects.append({'name': cls_name, 'box': (x1, y1, x2, y2), 'source': 'yolo'})

        # 2. 模板匹配 (关键事件/导航点/特定怪)
        #    只匹配当前状态下最重要的模板，而不是全部
        templates_to_check_in_combat = {
            'zhongmochongbaizhe': 0.8, 'shifoujixu': 0.8, 'qianjin': 0.8,
            'elite_monster': 0.75,  # 精英怪阈值可以稍低，因为它可能被YOLO覆盖
            'renwu': 0.8  # 人物模板，用于定位
        }
        for name, threshold in templates_to_check_in_combat.items():
            template_img = self.monsters_templates.get(name, {}).get('template')
            if template_img is not None:
                locations = self.utils.detect_template(gray_frame, template_img, threshold=threshold)
                for loc in locations:
                    detected_objects.append({'name': name, 'box': loc, 'source': 'template'})

        # 对检测结果进行一些去重或优先级处理 (可选，例如YOLO和模板都检测到同一个怪)
        # 简单起见，暂时不处理复杂去重

        return detected_objects

    def fight_monsters_in_current_view(self, frame_bgr, gray_frame, game_window):
        # 返回: "continue_fighting", "dungeon_cleared_retry", "dungeon_cleared_switch_char", "error_or_stuck"
        # 激活窗口
        if not self.utils.activate_window(game_window):
            print("未能激活游戏窗口，暂停战斗逻辑")
            time.sleep(1)
            return "error_or_stuck"

        # 0. 状态检查与Buff (仅在进入副本时或必要时)
        #    假设 zhongmochongbaizhe 模板是可靠的副本内标识
        #    这个检测应该在 fight_monsters_in_current_view 被调用前完成，以决定是否调用此函数

        if not self.has_applied_buff:  # 只在刚进图时加一次buff
            # 确保在副本内才加buff
            if any(d['name'] == 'zhongmochongbaizhe' for d in
                   self.process_detected_objects(frame_bgr, gray_frame)):  # 重新检测确保在图内
                print("施加Buff (Ctrl)")
                self.utils.press_key(self.attacker.skill_key_map['ctrl'])
                time.sleep(0.5)
                self.has_applied_buff = True

        # 1. 获取当前视图内的所有可交互对象
        detected_objects = self.process_detected_objects(frame_bgr, gray_frame)

        # 调试打印，可以按需开启
        # if detected_objects:
        #    print(f"当前帧检测到对象: {[obj['name'] for obj in detected_objects]}")

        # 2. 优先处理副本结束事件
        shifoujixu_obj = next((obj for obj in detected_objects if obj['name'] == 'shifoujixu'), None)
        if shifoujixu_obj:
            # 确认 shifoujixu 是否稳定出现 (防止误判)
            if self.shifoujixu_detected_time is None:
                self.shifoujixu_detected_time = time.time()
            elif time.time() - self.shifoujixu_detected_time > 0.5:  # 持续检测到超过0.5秒
                print("确认 shifoujixu，处理副本结束")
                if self.handle_pickup_and_retry(frame_bgr, shifoujixu_obj['box'], game_window):
                    return "dungeon_cleared_switch_char"  # 需要换角色
                else:
                    return "dungeon_cleared_retry"  # 继续刷当前角色
            # 如果只是瞬间检测到，则忽略，等待下一帧
            # print("短暂检测到shifoujixu，等待确认...")
            return "continue_fighting"  # 暂时继续当前状态，等待确认
        else:
            self.shifoujixu_detected_time = None  # 如果没检测到，重置计时

        # 3. 处理 "前进" 导航点 (如果当前房间未完成 "前进")
        if not self.qianjin_reached_current_room:
            qianjin_obj = next((obj for obj in detected_objects if obj['name'] == 'qianjin'), None)
            if qianjin_obj:
                self.run_to_qianjin(frame_bgr, qianjin_obj['box'], game_window)
                # run_to_qianjin 后，房间状态会变，下一帧重新评估
                return "continue_fighting"  # 返回让主循环获取新帧

        # 4. 选择攻击目标 (Boss > Elite > Small Monster)
        #    如果当前有正在攻击的目标，优先处理它

        target_to_attack = None
        if self.current_target_monster_info:  # 如果上一帧有目标但没打死
            # 确认这个目标是否还在 (YOLO检测最新帧)
            # 简单处理：直接尝试再次攻击，让 attack_target 内部判断
            target_to_attack = self.current_target_monster_info
            # print(f"继续攻击上一目标: {target_to_attack['name']}")
        else:  # 选择新目标
            bosses = [obj for obj in detected_objects if obj['name'] == 'boss']
            elites = [obj for obj in detected_objects if
                      obj['name'] == 'elite_monster' and obj['source'] == 'template']  # 优先模板精英怪
            # (如果YOLO也能标精英，可以合并)
            smalls_yolo = [obj for obj in detected_objects if
                           obj['name'] == 'small_monster' and obj['source'] == 'yolo']

            if bosses:
                target_to_attack = bosses[0]  # 打最近的或第一个Boss
            elif elites:
                target_to_attack = elites[0]
            elif smalls_yolo:
                target_to_attack = smalls_yolo[0]

        # 5. 执行攻击
        if target_to_attack:
            # print(f"选定攻击目标: {target_to_attack['name']} at {target_to_attack['box']}")
            # 激活窗口应该在具体操作前完成
            # if not self.utils.activate_window(game_window): return "error_or_stuck"

            attack_status = self.attacker.attack_target(target_to_attack, frame_bgr, gray_frame)

            if attack_status == "monster_killed":
                self.current_target_monster_info = None  # 清除当前目标
                self.attack_consecutive_failures = 0
                if target_to_attack['name'] == 'boss':
                    self.boss_fight_active = False  # Boss打完了
                    print("Boss 已击杀，等待 shifoujixu 出现。")
                # 怪物死亡后，可能需要短暂等待掉落物或下一波怪刷新
                time.sleep(0.3)
            elif attack_status == "monster_still_exists":
                self.current_target_monster_info = target_to_attack  # 保持目标，下一帧继续
                self.attack_consecutive_failures += 1
                if self.attack_consecutive_failures > 5:  # 如果连续5次攻击怪物还在
                    print(f"连续攻击 {target_to_attack['name']} 失败次数过多，尝试放弃当前目标或采取其他措施")
                    self.current_target_monster_info = None  # 放弃当前目标，尝试寻找新目标
                    self.attack_consecutive_failures = 0
                    # 可以加入随机移动逻辑以摆脱卡点
                    # random_move_dir = random.choice([self.attacker.skill_key_map['left_arrow'], self.attacker.skill_key_map['right_arrow']])
                    # self.utils.press_key(random_move_dir, duration=0.3)
                    # time.sleep(0.5)

            elif attack_status == "qianjin_detected":
                print("攻击过程中检测到 '前进'，优先处理导航")
                self.current_target_monster_info = None
                self.qianjin_reached_current_room = False  # 重新标记以便处理这个新前进点

            return "continue_fighting"

        # 6. 如果没有可攻击的目标，且已处理过 "前进" (self.qianjin_reached_current_room is True)
        #    或者当前房间就没有 "前进" 点 (例如Boss房前的小房间)
        if self.qianjin_reached_current_room and not target_to_attack:
            # print("当前房间已通过前进点，且无怪物，可能已清空。重置前进状态以寻找下一房间的'前进'。")
            self.qianjin_reached_current_room = False  # 重置，以便检测下一个房间的 "前进"
            # 可能需要一个短暂的“巡逻”或等待，看是否有新的“前进”或Boss出现
            time.sleep(0.5)
            return "continue_fighting"

        if not target_to_attack and not qianjin_obj and not shifoujixu_obj:
            # print("无怪物，无前进，无结束标志。可能在空房间或卡住了。")
            # 可以在这里增加一个“卡住”的计数器和处理逻辑
            # 例如，随机小范围移动一下
            # random_move_dir = random.choice([self.attacker.skill_key_map['left_arrow'], self.attacker.skill_key_map['right_arrow']])
            # self.utils.press_key(random_move_dir, duration=0.2)
            # time.sleep(0.3)
            pass

        return "continue_fighting"  # 默认继续


# --- GameAutomationWindow (主控制类) ---
class GameAutomationWindow(QWidget):
    def __init__(self):
        super().__init__()
        # ... (UI 初始化不变) ...
        self.stop_event = threading.Event()
        self.thread = None
        self.frame_queue = queue.Queue(maxsize=5)  # 限制队列大小防止内存问题
        self.is_verified = False
        self.current_role_index = 0  # 从0开始的索引
        self.total_roles_to_run = 1

        # 初始化控制器和导航器/战斗逻辑类
        # 这些将在 start_automation 中根据用户选择的模式实际创建
        self.input_controller = None
        self.utils_instance = None
        self.navigator = None
        self.fighter = None

        self.current_game_state = "idle"  # 新增：用于跟踪高级游戏状态
        # idle, town_navigation, in_dungeon, switching_char

        self.initUI()  # 调用initUI

    # ... (initUI, log, verify_key 不变) ...

    def start_automation(self):
        if not self.is_verified:
            QMessageBox.warning(self, "提示", "请先通过卡密验证！")
            return
        if self.thread and self.thread.is_alive():
            QMessageBox.information(self, "提示", "自动化已在运行中！")
            return

        input_mode_text = self.input_combo.currentText()
        try:
            if input_mode_text == "默认":
                self.input_controller = DefaultInputController()
                self.log("使用默认键鼠控制 (pynput & win32api)")
            else:  # "幽灵键鼠"
                self.input_controller = GhostInputController()
                self.log("使用幽灵键鼠控制 (gbild64.dll)")
        except Exception as e:
            error_msg = f"初始化键鼠控制失败: {str(e)}"
            self.log(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            return

        self.utils_instance = Utils(self.input_controller)  # 创建Utils实例
        self.navigator = SceneNavigator(input_controller=self.input_controller)
        self.fighter = MonsterFighterA(input_controller=self.input_controller, utils_instance=self.utils_instance)

        self.stop_event.clear()
        self.start_button.setEnabled(False)
        self.end_button.setEnabled(True)
        self.status_label.setText("状态: 运行中")
        self.log("自动化开始")

        self.total_roles_to_run = int(self.role_combo.currentText())
        self.current_role_index = 0  # 重置角色计数

        self.current_game_state = "town_navigation"  # 初始状态
        self.navigator.reset_navigation_state()  # 重置导航状态
        self.fighter.reset_combat_state()  # 重置战斗状态

        mode = self.mode_combo.currentText()
        if mode == "深渊地图":
            self.thread = threading.Thread(target=self.run_shenyuan_map_logic, daemon=True)
        elif mode == "妖气追踪":
            # self.thread = threading.Thread(target=self.run_yaoqi_tracking, daemon=True)
            self.log("妖气追踪模式暂未完全接入新逻辑。")
            QMessageBox.information(self, "提示", "妖气追踪模式正在开发中。")
            self.stop_automation()  # 停止，因为未实现
            return
        self.thread.start()

    def stop_automation(self):
        # ... (原有停止逻辑) ...
        if self.input_controller and hasattr(self.input_controller, 'release_all_held_keys'):
            self.input_controller.release_all_held_keys()  # 确保释放所有按键
        self.current_game_state = "idle"
        cv2.destroyAllWindows()

    def run_shenyuan_map_logic(self):
        try:
            game_window_list = gw.getWindowsWithTitle(self.input_controller.game_title_keyword)
            if not game_window_list:
                self.log(f"错误: 未找到游戏窗口 '{self.input_controller.game_title_keyword}'")
                self.stop_event.set()  # 停止自动化
                return
            game_window = game_window_list[0]
            try:  # 尝试移动和调整窗口大小，如果失败则继续
                game_window.moveTo(0, 0)
                # game_window.resizeTo(region['width'], region['height']) # 如果需要固定大小
            except Exception as e_win:
                self.log(f"调整游戏窗口位置/大小失败: {e_win} (继续执行)")

            if not self.utils_instance.activate_window(game_window):  # 初始激活
                self.log("游戏窗口初始激活失败，请手动激活后重试。")
                # self.stop_event.set() # 可以选择停止
                # return

            time.sleep(0.5)  # 等待激活生效

            with mss.mss() as sct:
                while not self.stop_event.is_set() and self.current_role_index < self.total_roles_to_run:
                    loop_start_time = time.time()

                    screenshot = sct.grab(region)
                    frame_arr = np.array(screenshot)
                    # 确保是 BGR 格式给 OpenCV 使用
                    frame_bgr = cv2.cvtColor(frame_arr, cv2.COLOR_BGRA2BGR)
                    gray_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)  # 转为灰度图

                    # --- 主状态机逻辑 ---
                    if self.current_game_state == "town_navigation":
                        self.log(f"状态: 城镇导航 (角色 {self.current_role_index + 1}/{self.total_roles_to_run})")
                        # move_to_shenyuan_map 返回 True 表示仍在城镇导航, False 表示导航结束（可能进图）
                        is_still_navigating_town = self.navigator.move_to_shenyuan_map(frame_bgr, gray_frame,
                                                                                       game_window)
                        if not is_still_navigating_town:
                            self.log("城镇导航完成或已进入副本，切换到副本内状态。")
                            self.current_game_state = "in_dungeon"
                            self.fighter.reset_combat_state()  # 确保战斗状态干净
                            # fighter.has_applied_buff 会在 fight_monsters_in_current_view 内部处理
                        # 如果仍在导航，下一轮循环继续处理导航

                    elif self.current_game_state == "in_dungeon":
                        # self.log("状态: 副本内战斗") # 这个日志太频繁了
                        # 首先判断是否真的在副本内 (例如通过 zhongmochongbaizhe 模板)
                        # 这个模板也可能在其他地方（如过场动画）出现，需要小心
                        # 为简化，这里假设如果状态是 in_dungeon，就直接尝试战斗逻辑
                        # 专业的做法是有一个更可靠的 "是否在可战斗的副本区域" 的判断

                        # 处理隐藏商店（如果出现）
                        yincangshangdian_locs = self.utils_instance.detect_template(gray_frame,
                                                                                    self.navigator.templates[
                                                                                        'yincangshangdian'], 0.85)
                        if yincangshangdian_locs:
                            self.log("检测到隐藏商店，点击关闭")
                            if self.utils_instance.activate_window(game_window):
                                self.utils_instance.click(373, 39, "left")  # 假设这是关闭按钮坐标
                                time.sleep(0.5)
                            # 点击后，当前帧可能已失效，最好等下一帧处理战斗
                            # continue # 跳过本轮战斗逻辑，下一帧重新评估

                        combat_result = self.fighter.fight_monsters_in_current_view(frame_bgr, gray_frame, game_window)

                        if combat_result == "dungeon_cleared_retry":
                            self.log("副本完成，当前角色重试。")
                            # fighter 内部已重置状态，导航器也应重置回城镇初始
                            self.current_game_state = "town_navigation"
                            self.navigator.reset_navigation_state()
                        elif combat_result == "dungeon_cleared_switch_char":
                            self.log(f"副本完成，角色 {self.current_role_index + 1} 结束。")
                            self.current_role_index += 1
                            if self.current_role_index < self.total_roles_to_run:
                                self.log("切换到下一角色...")
                                self.current_game_state = "switching_char"
                            else:
                                self.log("所有角色已完成。")
                                self.stop_event.set()  # 结束所有自动化
                        elif combat_result == "error_or_stuck":
                            self.log("战斗逻辑报告错误或卡住，尝试重置状态并返回城镇。")
                            self.current_game_state = "town_navigation"  # 尝试回到城镇重新开始
                            self.navigator.reset_navigation_state()
                            self.fighter.reset_combat_state()
                            time.sleep(2)  # 等待一段时间
                        # else "continue_fighting", 则下一轮循环继续

                    elif self.current_game_state == "switching_char":
                        self.log("状态: 切换角色")
                        if self.switch_character_logic(sct, game_window):  # switch_character_logic 返回True表示成功
                            self.log("角色切换成功。")
                            self.current_game_state = "town_navigation"  # 新角色从城镇导航开始
                            self.navigator.reset_navigation_state()
                            self.fighter.reset_combat_state()
                        else:
                            self.log("角色切换失败或仍在进行中，下一轮重试。")
                            time.sleep(1)  # 等待一下再试

                    # --- 显示处理 ---
                    try:
                        # 在 frame_bgr 上绘制调试信息 (可选)
                        # cv2.putText(frame_bgr, f"State: {self.current_game_state}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                        # cv2.putText(frame_bgr, f"Role: {self.current_role_index+1}/{self.total_roles_to_run}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                        if not self.frame_queue.full():
                            self.frame_queue.put(frame_bgr.copy())  # 放入副本以防多线程问题
                        else:
                            pass  # 队列满了，丢弃当前帧以避免阻塞
                    except Exception as e_disp:
                        self.log(f"显示帧处理错误: {e_disp}")

                    # --- 循环延时控制 ---
                    elapsed_time = time.time() - loop_start_time
                    sleep_duration = max(0, 0.033 - elapsed_time)  # 维持约30FPS的主逻辑循环
                    time.sleep(sleep_duration)

        except Exception as e:
            self.log(f"自动化主循环发生严重错误: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.log("自动化线程结束。")
            # 确保在线程结束时，所有按键都已释放
            if self.input_controller and hasattr(self.input_controller, 'release_all_held_keys'):
                self.input_controller.release_all_held_keys()
            # 通知UI更新状态 (如果需要，可以通过信号槽)
            self.start_button.setEnabled(True)  # 允许重新开始
            self.end_button.setEnabled(False)
            self.status_label.setText("状态: 已停止")

    def switch_character_logic(self, sct_instance, game_window):  # 返回True表示切换成功
        # 确保在角色选择界面
        # 1. 按ESC打开菜单 (如果不在菜单) -> 点击"选择角色"
        #    这里简化：假设已通过F12等方式到了角色选择界面，或即将到达

        # 激活窗口
        if not self.utils_instance.activate_window(game_window): return False

        # 尝试检测是否已在角色选择界面
        time.sleep(0.5)  # 等待界面稳定
        current_screen_shot = sct_instance.grab(region)
        gray_current = cv2.cvtColor(np.array(current_screen_shot), cv2.COLOR_BGRA2GRAY)

        if not self.utils_instance.detect_template(gray_current, self.navigator.templates['xuanzejuese_jiemian'], 0.85):
            # 如果不在角色选择界面，尝试通过菜单进入
            self.log("尝试通过菜单进入角色选择...")
            # 按ESC打开游戏菜单
            # self.utils_instance.press_key(VK_ESCAPE) # 假设有VK_ESCAPE键码
            # time.sleep(0.5)
            # current_screen_shot = sct_instance.grab(region) # 更新截图
            # gray_current = cv2.cvtColor(np.array(current_screen_shot), cv2.COLOR_BGRA2GRAY)

            # 点击游戏菜单图标 (如果能看到)
            youxicaidan_locs = self.utils_instance.detect_template(gray_current,
                                                                   self.navigator.templates['youxicaidan'])
            if youxicaidan_locs:
                yx1, yy1, yx2, yy2 = youxicaidan_locs[0]
                self.utils_instance.click(yx1 + (yx2 - yx1) // 2, yy1 + (yy2 - yy1) // 2)
                time.sleep(0.8)
                current_screen_shot = sct_instance.grab(region)  # 更新截图
                gray_current = cv2.cvtColor(np.array(current_screen_shot), cv2.COLOR_BGRA2GRAY)
            else:  # 如果看不到游戏菜单图标，就直接按f12尝试返回角色选择
                self.log("未检测到游戏菜单图标，尝试按F12返回角色选择")
                self.utils_instance.press_key(self.fighter.attacker.skill_key_map['f12'])
                time.sleep(2.0)  # 等待返回
                current_screen_shot = sct_instance.grab(region)  # 更新截图
                gray_current = cv2.cvtColor(np.array(current_screen_shot), cv2.COLOR_BGRA2GRAY)

            # 点击"选择角色"按钮
            xuanzejuese_btn_locs = self.utils_instance.detect_template(gray_current,
                                                                       self.navigator.templates['xuanzejuese'], 0.85)
            if xuanzejuese_btn_locs:
                xx1, xy1, xx2, xy2 = xuanzejuese_btn_locs[0]
                self.utils_instance.click(xx1 + (xx2 - xx1) // 2, xy1 + (xy2 - xy1) // 2)
                time.sleep(1.5)  # 等待进入角色选择界面
                current_screen_shot = sct_instance.grab(region)  # 最后更新截图
                gray_current = cv2.cvtColor(np.array(current_screen_shot), cv2.COLOR_BGRA2GRAY)
            else:
                self.log("未找到'选择角色'按钮，切换角色可能失败。")
                # 再次尝试F12
                self.utils_instance.press_key(self.fighter.attacker.skill_key_map['f12'])
                time.sleep(2.0)
                return False

        # 确认是否在角色选择界面
        if self.utils_instance.detect_template(gray_current, self.navigator.templates['xuanzejuese_jiemian'], 0.85):
            self.log("已在角色选择界面，选择下一角色。")
            # 简单实现：按一下向右键选中下一个角色，然后按空格确认
            # 实际游戏中可能需要多次按键或根据角色列表具体情况调整
            self.utils_instance.press_key(self.fighter.attacker.skill_key_map['right_arrow'])  # VK_RIGHT
            time.sleep(0.3)
            self.utils_instance.press_key(self.fighter.attacker.skill_key_map['space'])  # VK_SPACE
            time.sleep(random6_time)  # 等待角色载入，这个时间可能比较长

            # 验证是否成功进入游戏 (例如，检测到赛利亚房间)
            time.sleep(2.0)  # 额外等待确保加载完毕
            final_check_shot = sct_instance.grab(region)
            gray_final = cv2.cvtColor(np.array(final_check_shot), cv2.COLOR_BGRA2GRAY)
            if self.utils_instance.detect_template(gray_final, self.navigator.templates['sailiya'], 0.8):
                self.log("检测到赛利亚房间，角色切换成功。")
                return True
            else:
                self.log("未检测到赛利亚房间，角色切换可能未完全成功。")
                # 尝试再按一下空格，防止是确认慢了
                self.utils_instance.press_key(self.fighter.attacker.skill_key_map['space'])
                time.sleep(2.0)
                final_check_shot_2 = sct_instance.grab(region)
                gray_final_2 = cv2.cvtColor(np.array(final_check_shot_2), cv2.COLOR_BGRA2GRAY)
                if self.utils_instance.detect_template(gray_final_2, self.navigator.templates['sailiya'], 0.8):
                    return True
                return False
        else:
            self.log("最终未能进入角色选择界面。")
            return False

    def update_frame(self):  # UI 更新逻辑
        try:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get_nowait()
                # 显示前可以缩小图像以适应窗口，或确保窗口大小合适
                # scaled_frame = cv2.resize(frame, (desired_width, desired_height))
                cv2.imshow('DNF Automation Monitor', frame)
                # cv2.waitKey(1) & 0xFF # 不要用 'q' 来停止，用UI按钮
                if cv2.waitKey(1) == 27:  # ESC键关闭预览窗口 (但不会停止自动化)
                    cv2.destroyWindow('DNF Automation Monitor')

        except queue.Empty:
            pass
        except Exception as e:
            # print(f"UI update_frame error: {e}") # 避免在UI线程频繁打印
            pass


def main():
    app = QApplication(sys.argv)
    main_window = GameAutomationWindow()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # 为了调试，可以临时取消卡密验证
    # GameAutomationWindow.is_verified = True # 仅调试用
    main()