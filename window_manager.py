"""
window_manager.py - 游戏窗口管理工具
负责检测和移动游戏窗口到指定位置
"""

import pygetwindow as gw
import time

class WindowManager:
    """游戏窗口管理器"""
    
    def __init__(self):
        self.game_window_title = "地下城与勇士：创新世纪"
        self.target_position = (0, 0)  # 目标位置：左上角
        
    def find_game_window(self):
        """查找游戏窗口"""
        try:
            windows = gw.getWindowsWithTitle(self.game_window_title)
            if windows:
                return windows[0]
            else:
                return None
        except Exception as e:
            print(f"查找游戏窗口时发生错误: {e}")
            return None
    
    def move_window_to_top_left(self, window):
        """将窗口移动到左上角"""
        try:
            print(f"原始窗口位置: ({window.left}, {window.top})")
            print(f"原始窗口大小: {window.width}x{window.height}")
            
            # 激活窗口
            window.activate()
            time.sleep(0.2)
            
            # 移动到左上角
            window.moveTo(self.target_position[0], self.target_position[1])
            time.sleep(0.2)
            
            print(f"窗口已移动到: ({window.left}, {window.top})")
            return True
            
        except Exception as e:
            print(f"移动窗口时发生错误: {e}")
            return False
    
    def check_and_move_game_window(self):
        """检查游戏窗口并移动到左上角"""
        game_window = self.find_game_window()
        
        if game_window is None:
            return False, "请先登陆游戏"
        
        # 检查窗口是否已经在正确位置
        if game_window.left == self.target_position[0] and game_window.top == self.target_position[1]:
            print("游戏窗口已在正确位置")
            return True, "游戏窗口已在正确位置"
        
        # 移动窗口
        success = self.move_window_to_top_left(game_window)
        
        if success:
            return True, f"游戏窗口已移动到左上角 ({self.target_position[0]}, {self.target_position[1]})"
        else:
            return False, "移动游戏窗口失败"
    
    def get_game_window_info(self):
        """获取游戏窗口信息"""
        game_window = self.find_game_window()
        
        if game_window is None:
            return None
        
        return {
            'title': game_window.title,
            'left': game_window.left,
            'top': game_window.top,
            'width': game_window.width,
            'height': game_window.height,
            'isActive': game_window.isActive,
            'isMaximized': game_window.isMaximized
        }
    
    def ensure_window_ready(self):
        """确保游戏窗口就绪"""
        game_window = self.find_game_window()
        
        if game_window is None:
            return False, "游戏窗口未找到，请先登陆游戏"
        
        try:
            # 如果窗口最小化，先恢复
            if game_window.isMinimized:
                game_window.restore()
                time.sleep(0.5)
            
            # 激活窗口
            game_window.activate()
            time.sleep(0.3)
            
            # 移动到左上角
            if game_window.left != self.target_position[0] or game_window.top != self.target_position[1]:
                success = self.move_window_to_top_left(game_window)
                if not success:
                    return False, "无法移动游戏窗口到指定位置"
            
            return True, "游戏窗口已就绪"
            
        except Exception as e:
            return False, f"准备游戏窗口时发生错误: {e}"


def test_window_manager():
    """测试窗口管理器"""
    print("=== 测试窗口管理器 ===")
    
    wm = WindowManager()
    
    # 测试查找游戏窗口
    print("\n1. 查找游戏窗口...")
    window_info = wm.get_game_window_info()
    
    if window_info:
        print("找到游戏窗口:")
        for key, value in window_info.items():
            print(f"  {key}: {value}")
    else:
        print("未找到游戏窗口")
        return
    
    # 测试移动窗口
    print("\n2. 移动游戏窗口到左上角...")
    success, message = wm.check_and_move_game_window()
    print(f"结果: {message}")
    
    if success:
        print("\n3. 验证窗口位置...")
        time.sleep(1)
        updated_info = wm.get_game_window_info()
        if updated_info:
            print(f"当前窗口位置: ({updated_info['left']}, {updated_info['top']})")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_window_manager()