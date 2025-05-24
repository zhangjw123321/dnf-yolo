import cv2
import time
import numpy as np
import pygetwindow as gw
from utils import Utils, resource_path
from constants import RANDOM1_TIME, RANDOM6_TIME

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
                time.sleep(RANDOM6_TIME)
            town_detected = True

        diedang_locations = self.utils.detect_template(gray_frame, self.templates['diedangquandao_menkou'])
        print(f"检测到跌宕群岛门口: {len(diedang_locations)} 个位置")
        for x1, y1, x2, y2 in diedang_locations:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            cv2.putText(frame, f"跌宕群岛门口: ({x1},{y1})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            print("已经移动到跌宕群岛门口")
            self.utils.activate_window(game_window)
            time.sleep(RANDOM6_TIME)
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