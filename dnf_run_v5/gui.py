import threading
import queue
import cv2
import numpy as np
import time
from PyQt5.QtWidgets import (QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                             QHBoxLayout, QMessageBox, QComboBox, QTextEdit, QCheckBox)
from PyQt5.QtCore import QTimer
import mss
from scene_navigator import SceneNavigator
from monster_fighter import MonsterFighterA
from input_controller import DefaultInputController, GhostInputController
from config import load_config, save_config, verify_key
from constants import REGION
import pygetwindow as gw
import random
import sys
sys.stdout.reconfigure(encoding='utf-8')

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

        config = load_config()
        if config.get('remember', False):
            self.key_input.setText(config.get('key', ''))
            self.remember_checkbox.setChecked(True)

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

        success, message, expiry_date = verify_key(key)
        if success:
            save_config(key, expiry_date, self.remember_checkbox.isChecked())
            self.is_verified = True
            self.start_button.setEnabled(True)
            self.log(f"登录成功！有效期至：{expiry_date}")
            QMessageBox.information(self, '成功', f'{message}！有效期至：{expiry_date}')
        else:
            self.log(f"验证失败: {message}")
            QMessageBox.warning(self, '错误', message)

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
                    screenshot = sct.grab(REGION)
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
        screenshot = sct.grab(REGION)
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

        screenshot = sct.grab(REGION)
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

        screenshot = sct.grab(REGION)
        gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
        xuanzejuese_jiemian_locations = self.navigator.utils.detect_template(gray_frame, self.navigator.templates['xuanzejuese_jiemian'])
        self.log(f"检测到选择角色界面: {len(xuanzejuese_jiemian_locations)} 个位置")
        if xuanzejuese_jiemian_locations:
            self.log("检测到 xuanzejuese_jiemian.png，切换角色")
            self.navigator.utils.press_key(39, random.uniform(0.1311, 0.1511))
            time.sleep(0.1)
            self.navigator.utils.press_key(32, random.uniform(0.1311, 0.1511))
            time.sleep(2)

            screenshot = sct.grab(REGION)
            gray_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
            sailiya_locations = self.navigator.utils.detect_template(gray_frame, self.navigator.templates['sailiya'])
            self.log(f"检测到塞利亚: {len(sailiya_locations)} 个位置")
            if sailiya_locations:
                self.log("检测到 sailiya.png，角色切换成功，重置状态")
                self.navigator.clicked_youxicaidan = False
                self.navigator.clicked_shijieditu = False
                self.fighter.qianjin_reached = False
                self.fighter.boss_dead = False
                self.fighter.has_applied_buff = False
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