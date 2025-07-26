"""
input_controllers.py - 多种键鼠控制器实现
支持默认控制器和幽灵键鼠控制器
"""

import time
import random
import win32api
import win32con
from ctypes import cdll
from pynput.keyboard import Key, Controller as KeyboardController


# 随机延迟时间
def get_random_delay():
    """获取随机延迟时间"""
    return round(random.uniform(0.1311, 0.1511), 4)


class InputController:
    """输入控制器基类"""
    
    def press_key(self, key, duration=0.5):
        raise NotImplementedError
    
    def hold_key(self, key):
        raise NotImplementedError
    
    def release_key(self, key):
        raise NotImplementedError
    
    def click(self, x, y, button="left"):
        raise NotImplementedError


class DefaultInputController(InputController):
    """默认输入控制器 - 使用 pynput + win32api"""
    
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
                17: Key.ctrl_l,    # Ctrl (左 Ctrl，使用 Key.ctrl_l)
                78: 'n',           # N
                27: Key.esc,       # ESC
            }
            print("DefaultInputController 初始化成功")
        except Exception as e:
            print(f"初始化 pynput KeyboardController 失败: {str(e)}")
            raise RuntimeError(f"初始化 pynput KeyboardController 失败: {str(e)}")

    def press_key(self, key, duration=0.5):
        """按键方法"""
        if key is None:
            print("默认: 键码为 None，无法按下")
            return
        
        # 如果是字符键
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
            # 使用win32api作为后备
            win32api.keybd_event(key, 0, 0, 0)  # 按下
            time.sleep(duration)
            win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)  # 释放
            print(f"默认: 使用win32api按下键码 {key}，持续时间: {duration} 秒")

    def hold_key(self, key):
        """持续按住键"""
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
        """释放键"""
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
        """点击方法"""
        win32api.SetCursorPos((x, y))
        if button == "left":
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
            time.sleep(get_random_delay())
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
            print(f"默认: 左键点击已执行: ({x}, {y})")
        elif button == "right":
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            time.sleep(get_random_delay())
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            print(f"默认: 右键点击已执行: ({x}, {y})")


class GhostInputController(InputController):
    """幽灵键鼠控制器 - 使用 gbild64.dll 硬件模拟"""
    
    def __init__(self):
        try:
            print("正在加载幽灵键鼠DLL...")
            self.dll = cdll.LoadLibrary('./gbild64.dll')
            print("DLL加载成功，正在初始化设备...")
            print(f"Open device: {self.dll.opendevice(0)}")
            print(f"Connected: {self.dll.isconnected()}")
            print(f"Model: {self.dll.getmodel()}")
            print("幽灵键鼠初始化完成")
        except Exception as e:
            print(f"加载幽灵键鼠 DLL 失败: {e}")
            raise RuntimeError(f"加载幽灵键鼠 DLL 失败: {e}")

    def press_key(self, key, duration=0.5):
        """按键方法"""
        if key is None:
            print("幽灵: 键码为 None，无法按下")
            return
        print(self.dll.presskeybyvalue(key))
        time.sleep(duration)
        print(self.dll.releasekeybyvalue(key))
        print(f"幽灵: 按下并释放键 {key}，持续时间: {duration} 秒")

    def hold_key(self, key):
        """持续按住键"""
        if key is None:
            print("幽灵: 键码为 None，无法持续按住")
            return
        print(self.dll.presskeybyvalue(key))
        print(f"幽灵: 持续按住键 {key}")

    def release_key(self, key):
        """释放键"""
        if key is None:
            print("幽灵: 键码为 None，无需释放")
            return
        print(self.dll.releasekeybyvalue(key))
        print(f"幽灵: 释放键 {key}")

    def click(self, x, y, button="left"):
        """点击方法"""
        print(self.dll.movemouseto(int(x), int(y)))
        if button == "left":
            print(self.dll.pressmousebutton(1))
            time.sleep(get_random_delay())
            print(self.dll.releasemousebutton(1))
            print(f"幽灵: 左键点击已执行: ({x}, {y})")
        elif button == "right":
            win32api.SetCursorPos((x, y))
            time.sleep(get_random_delay())
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, x, y, 0, 0)
            time.sleep(get_random_delay())
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, x, y, 0, 0)
            print(f"幽灵: 右键点击已执行 (win32api): ({x}, {y})")


def create_input_controller(controller_type="默认"):
    """
    创建指定类型的输入控制器
    
    Args:
        controller_type: 控制器类型 ("默认" 或 "幽灵键鼠")
        
    Returns:
        InputController: 输入控制器实例
    """
    try:
        if controller_type == "默认":
            return DefaultInputController()
        elif controller_type == "幽灵键鼠":
            return GhostInputController()
        else:
            print(f"未知的控制器类型: {controller_type}，使用默认控制器")
            return DefaultInputController()
    except Exception as e:
        print(f"创建 {controller_type} 控制器失败: {e}")
        print("回退到默认控制器")
        return DefaultInputController()


def get_available_controllers():
    """
    获取可用的控制器列表
    
    Returns:
        list: 可用控制器名称列表
    """
    controllers = ["默认"]
    
    # 检查是否有幽灵键鼠DLL
    try:
        cdll.LoadLibrary('./gbild64.dll')
        controllers.append("幽灵键鼠")
        print("检测到幽灵键鼠DLL，添加到可用控制器列表")
    except Exception as e:
        print(f"未检测到幽灵键鼠DLL: {e}")
    
    return controllers


if __name__ == "__main__":
    # 测试代码
    print("=== 输入控制器测试 ===")
    
    available = get_available_controllers()
    print(f"可用控制器: {available}")
    
    # 测试默认控制器
    try:
        print("\n测试默认控制器...")
        default_controller = create_input_controller("默认")
        print("默认控制器创建成功")
    except Exception as e:
        print(f"默认控制器测试失败: {e}")
    
    # 测试幽灵键鼠控制器（如果可用）
    if "幽灵键鼠" in available:
        try:
            print("\n测试幽灵键鼠控制器...")
            ghost_controller = create_input_controller("幽灵键鼠")
            print("幽灵键鼠控制器创建成功")
        except Exception as e:
            print(f"幽灵键鼠控制器测试失败: {e}")