import cv2
import numpy as np
import time
import random
import mss
import pygetwindow as gw
from ultralytics import YOLO
from utils import Utils, resource_path
from constants import REGION, RANDOM1_TIME, RANDOM5_TIME

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
                    screenshot = sct.grab(REGION)
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
                screenshot = sct.grab(REGION)
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
                screenshot = sct.grab(REGION)
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
                    screenshot = sct.grab(REGION)
                    gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)

                qianjin_locations = self.utils.detect_template(gray_frame, self.monsters['qianjin']['template'])
                if qianjin_locations:
                    print("检测到 qianjin，表示小怪已死，立即停止攻击")
                    return True
                print("技能释放完毕，执行一次普通攻击 X")
                self.utils.press_key(88, random.uniform(0.01011, 0.03011))  # X 键普通攻击
                time.sleep(random.uniform(0.01011, 0.03011))
                screenshot = sct.grab(REGION)
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
        self.has_applied_buff = False

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
                            screenshot = sct.grab(REGION)
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