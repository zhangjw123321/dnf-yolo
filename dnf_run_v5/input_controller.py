import time
from pynput.keyboard import Key, Controller as KeyboardController
import win32api
import win32con
from ctypes import cdll
from constants import RANDOM1_TIME

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
                17: Key.ctrl_l     # Ctrl (左 Ctrl)
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
            time.sleep(RANDOM1_TIME)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            print(f"默认: 左键点击已执行: ({x}, {y})")
        elif button == "right":
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            time.sleep(RANDOM1_TIME)
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
            time.sleep(RANDOM1_TIME)
            print(self.dll.releasemousebutton(1))
            print(f"幽灵: 左键点击已执行: ({x}, {y})")
        elif button == "right":
            win32api.SetCursorPos((x, y))
            time.sleep(RANDOM1_TIME)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            time.sleep(RANDOM1_TIME)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            print(f"幽灵: 右键点击已执行 (win32api): ({x}, {y})")