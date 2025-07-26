"""
utils.py - 游戏工具类
提供游戏相关的通用工具函数
"""

import cv2
import numpy as np
import time
import os
import pygetwindow as gw
from pathlib import Path

class GameUtils:
    """游戏工具类"""
    
    def __init__(self):
        """初始化游戏工具"""
        self.game_title = "地下城与勇士：创新世纪"
        self.game_region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
        
    def find_game_window(self):
        """查找游戏窗口"""
        try:
            windows = gw.getWindowsWithTitle(self.game_title)
            return windows[0] if windows else None
        except Exception as e:
            print(f"查找游戏窗口失败: {e}")
            return None
    
    def activate_game_window(self):
        """激活游戏窗口"""
        try:
            game_window = self.find_game_window()
            if game_window:
                game_window.activate()
                time.sleep(0.2)
                return True
            return False
        except Exception as e:
            print(f"激活游戏窗口失败: {e}")
            return False
    
    def load_template(self, template_path):
        """加载模板图像"""
        try:
            if os.path.exists(template_path):
                template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    return template
                else:
                    print(f"模板加载失败: {template_path}")
            else:
                print(f"模板文件不存在: {template_path}")
            return None
        except Exception as e:
            print(f"加载模板时发生错误: {e}")
            return None
    
    def match_template(self, frame, template, threshold=0.8):
        """模板匹配"""
        try:
            if template is None:
                return None, 0
            
            # 转换为灰度图
            if len(frame.shape) == 3:
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray_frame = frame
            
            # 模板匹配
            result = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                # 计算中心点
                h, w = template.shape
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return (center_x, center_y), max_val
            
            return None, max_val
            
        except Exception as e:
            print(f"模板匹配时发生错误: {e}")
            return None, 0
    
    def wait_for_element(self, frame, template, timeout=10, threshold=0.8):
        """等待元素出现"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            match_pos, confidence = self.match_template(frame, template, threshold)
            if match_pos:
                return match_pos, confidence
            time.sleep(0.1)
        
        return None, 0
    
    def is_color_in_range(self, pixel_bgr, target_bgr, tolerance=20):
        """检查颜色是否在范围内"""
        try:
            for i in range(3):
                if abs(pixel_bgr[i] - target_bgr[i]) > tolerance:
                    return False
            return True
        except Exception:
            return False
    
    def find_color_regions(self, frame, target_color_bgr, tolerance=20, min_area=10):
        """查找指定颜色的区域"""
        try:
            # 创建颜色掩码
            lower_color = np.array([max(0, c - tolerance) for c in target_color_bgr])
            upper_color = np.array([min(255, c + tolerance) for c in target_color_bgr])
            
            mask = cv2.inRange(frame, lower_color, upper_color)
            
            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            regions = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area >= min_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    regions.append({
                        'center': (x + w // 2, y + h // 2),
                        'bbox': (x, y, w, h),
                        'area': area
                    })
            
            return regions
            
        except Exception as e:
            print(f"查找颜色区域时发生错误: {e}")
            return []
    
    def save_debug_image(self, image, filename_prefix="debug"):
        """保存调试图像"""
        try:
            debug_dir = "debug_images"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            timestamp = int(time.time())
            filename = f"{filename_prefix}_{timestamp}.png"
            filepath = os.path.join(debug_dir, filename)
            
            cv2.imwrite(filepath, image)
            print(f"调试图像已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"保存调试图像失败: {e}")
            return None
    
    def calculate_distance(self, pos1, pos2):
        """计算两点间距离"""
        try:
            dx = pos1[0] - pos2[0]
            dy = pos1[1] - pos2[1]
            return (dx * dx + dy * dy) ** 0.5
        except Exception:
            return float('inf')
    
    def get_screen_center(self):
        """获取屏幕中心点"""
        return (self.game_region['width'] // 2, self.game_region['height'] // 2)
    
    def is_point_in_region(self, point, region):
        """检查点是否在区域内"""
        try:
            x, y = point
            x1, y1, w, h = region
            return x1 <= x <= x1 + w and y1 <= y <= y1 + h
        except Exception:
            return False
    
    def create_templates_dict(self, templates_dir="templates"):
        """创建模板字典"""
        templates = {}
        
        if not os.path.exists(templates_dir):
            print(f"模板目录不存在: {templates_dir}")
            return templates
        
        try:
            for filename in os.listdir(templates_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    template_name = os.path.splitext(filename)[0]
                    template_path = os.path.join(templates_dir, filename)
                    template = self.load_template(template_path)
                    if template is not None:
                        templates[template_name] = template
                        print(f"加载模板: {template_name}")
            
            print(f"总共加载了 {len(templates)} 个模板")
            return templates
            
        except Exception as e:
            print(f"创建模板字典失败: {e}")
            return templates


def test_game_utils():
    """测试游戏工具类"""
    print("=== 测试游戏工具类 ===")
    
    utils = GameUtils()
    
    # 测试查找游戏窗口
    print("\n1. 查找游戏窗口...")
    game_window = utils.find_game_window()
    if game_window:
        print(f"找到游戏窗口: {game_window.title}")
        print(f"窗口位置: ({game_window.left}, {game_window.top})")
        print(f"窗口大小: {game_window.width}x{game_window.height}")
    else:
        print("未找到游戏窗口")
    
    # 测试激活游戏窗口
    print("\n2. 测试激活游戏窗口...")
    success = utils.activate_game_window()
    print(f"激活结果: {'成功' if success else '失败'}")
    
    # 测试模板加载
    print("\n3. 测试模板加载...")
    templates = utils.create_templates_dict()
    print(f"加载的模板数量: {len(templates)}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_game_utils()