import sys
import os
import time
import cv2
import numpy as np
import win32gui
import win32con
import subprocess
import hashlib

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