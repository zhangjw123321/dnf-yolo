"""
main_run.py - 主UI界面和控制器
专注于UI界面和模块调用，不包含具体的检测逻辑
"""

import sys
import threading
import time
import os
import subprocess
import hashlib
import json
import requests
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QHBoxLayout, QMessageBox, QComboBox, QTextEdit, QCheckBox, QGroupBox, QFrame)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QImage
import cv2
import numpy as np
import mss
from window_manager import WindowManager
from input_controllers import get_available_controllers, create_input_controller


def get_machine_code():
    """获取机器码"""
    try:
        cmd = 'wmic cpu get ProcessorId'
        output = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        return hashlib.sha256(output.encode()).hexdigest()
    except Exception as e:
        print(f"获取机器码失败: {e}")
        return "default_machine_code"


class GameAutomationWindow(QWidget):
    """游戏自动化主窗口"""
    
    def __init__(self):
        super().__init__()
        print("初始化GameAutomationWindow...")
        
        # 状态变量
        self.stop_event = threading.Event()
        self.automation_thread = None
        self.detection_thread = None
        
        # 自动化模块（延迟导入）
        self.zhongmo_automator = None
        self.yaoqi_automator = None
        
        # 验证状态
        self.is_verified = False
        
        # 窗口管理器
        self.window_manager = WindowManager()
        
        # 初始化UI
        print("开始初始化UI...")
        self.init_ui()
        print("UI初始化完成")
        
        # 初始化时检查游戏窗口
        self.check_game_window_on_startup()
        
        # 设置定时器用于UI更新
        print("设置定时器...")
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)  # 每秒更新一次
        print("定时器启动完成")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("DNF自动化工具")
        self.setGeometry(100, 100, 900, 700)
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                font-family: 'Microsoft YaHei', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #333;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("DNF自动化工具")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                border-radius: 10px;
                text-align: center;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 卡密验证区域
        auth_layout = QHBoxLayout()
        
        self.login_label = QLabel("请输入卡密:")
        auth_layout.addWidget(self.login_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("请输入您的卡密")
        auth_layout.addWidget(self.key_input)
        
        self.remember_checkbox = QCheckBox("记住密码")
        auth_layout.addWidget(self.remember_checkbox)
        
        self.login_button = QPushButton("登录验证")
        self.login_button.clicked.connect(self.verify_key)
        self.login_button.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-size: 12px; padding: 8px; }")
        auth_layout.addWidget(self.login_button)
        
        main_layout.addLayout(auth_layout)
        
        # 加载保存的配置
        self.load_saved_config()
        
        # 配置选择和控制按钮区域（合并布局）
        config_and_control_layout = QHBoxLayout()
        config_and_control_layout.setContentsMargins(0, 0, 0, 0)
        
        # 左侧配置选择区域
        config_container = QVBoxLayout()
        config_container.setSpacing(10)
        
        # 模式选择区域
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        
        mode_label = QLabel("选择模式:")
        mode_label.setMinimumWidth(80)
        mode_label.setAlignment(Qt.AlignLeft)
        mode_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["妖气追踪", "深渊地图"])
        self.mode_combo.setCurrentText("深渊地图")  # 默认选择深渊地图
        self.mode_combo.setMinimumWidth(120)
        mode_layout.addWidget(self.mode_combo)
        
        # 添加说明标签
        mode_layout.addStretch()
        config_container.addLayout(mode_layout)
        
        # 角色数量设置
        role_layout = QHBoxLayout()
        role_layout.setContentsMargins(0, 0, 0, 0)
        
        role_label = QLabel("角色数量:")
        role_label.setMinimumWidth(80)
        role_label.setAlignment(Qt.AlignLeft)
        role_layout.addWidget(role_label)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems([str(i) for i in range(1, 11)])
        self.role_combo.setMinimumWidth(120)
        role_layout.addWidget(self.role_combo)
        
        role_layout.addStretch()
        config_container.addLayout(role_layout)
        
        # 键鼠控制方法选择
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        input_label = QLabel("键鼠控制:")
        input_label.setMinimumWidth(80)
        input_label.setAlignment(Qt.AlignLeft)
        input_layout.addWidget(input_label)
        
        self.input_combo = QComboBox()
        available_controllers = get_available_controllers()
        self.input_combo.addItems(available_controllers)
        self.input_combo.setCurrentIndex(0)  # 默认选择第一个（通常是"默认"）
        self.input_combo.setMinimumWidth(120)
        input_layout.addWidget(self.input_combo)
        
        # 添加说明标签
        info_label = QLabel("(幽灵键鼠需要gbild64.dll)")
        info_label.setStyleSheet("font-size: 10px; color: #666; margin-left: 10px;")
        input_layout.addWidget(info_label)
        
        input_layout.addStretch()
        config_container.addLayout(input_layout)
        
        # 将配置区域添加到主水平布局的左侧
        config_and_control_layout.addLayout(config_container)
        
        # 添加间隔
        config_and_control_layout.addSpacing(50)
        
        # 右侧控制按钮区域（垂直排列）
        button_container = QVBoxLayout()
        button_container.setSpacing(8)
        
        # 开始自动化按钮
        self.start_button = QPushButton("开始自动化")
        self.start_button.clicked.connect(self.start_automation)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 13px;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.start_button.setEnabled(False)  # 默认禁用，需要验证后启用
        button_container.addWidget(self.start_button)
        
        # 停止自动化按钮
        self.stop_button = QPushButton("停止自动化")
        self.stop_button.clicked.connect(self.stop_automation)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 13px;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        button_container.addWidget(self.stop_button)
        
        # 实时检测按钮
        self.detection_button = QPushButton("开始实时检测")
        self.detection_button.clicked.connect(self.toggle_detection)
        self.detection_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 13px;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        button_container.addWidget(self.detection_button)
        
        # 将按钮区域添加到主水平布局的右侧
        config_and_control_layout.addLayout(button_container)
        
        # 添加弹性空间，使整个区域左对齐
        config_and_control_layout.addStretch()
        
        main_layout.addLayout(config_and_control_layout)
        
        # 窗口管理按钮
        window_layout = QHBoxLayout()
        
        self.window_check_button = QPushButton("检查游戏窗口")
        self.window_check_button.clicked.connect(self.check_and_move_window)
        self.window_check_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-size: 12px;
                padding: 8px 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        window_layout.addWidget(self.window_check_button)
        
        self.window_status_label = QLabel("窗口状态: 未检查")
        self.window_status_label.setStyleSheet("font-size: 12px; color: #666; margin-left: 15px;")
        window_layout.addWidget(self.window_status_label)
        
        window_layout.addStretch()
        main_layout.addLayout(window_layout)
        
        
        # 日志区域
        log_label = QLabel("运行日志:")
        log_label.setStyleSheet("font-weight: bold; margin-top: 20px;")
        main_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        main_layout.addWidget(self.log_text)
        
        # 状态显示区域
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("状态: 就绪")
        self.status_label.setStyleSheet("font-weight: bold; color: green;")
        status_layout.addWidget(self.status_label)
        
        self.current_role_label = QLabel("当前角色: 0/1")
        status_layout.addWidget(self.current_role_label)
        
        main_layout.addLayout(status_layout)
        
        # 实时检测显示区域
        self.detection_label = QLabel("实时检测窗口")
        self.detection_label.setMinimumHeight(300)
        self.detection_label.setStyleSheet("border: 1px solid gray; background-color: black;")
        main_layout.addWidget(self.detection_label)
        
        self.setLayout(main_layout)
    
    def log(self, message):
        """添加日志信息"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_text.append(log_message)
        print(log_message)  # 同时输出到控制台
        
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def load_saved_config(self):
        """加载保存的配置"""
        try:
            config_file = Path.home() / ".game_script_config" / "config.json"
            print(f"🔍 尝试加载配置文件: {config_file}")
            
            if config_file.exists():
                print("✅ 配置文件存在，开始加载")
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"📋 配置内容: remember={config.get('remember', False)}, key存在={bool(config.get('key', ''))}")
                    
                    # 先设置记住密码复选框的状态
                    remember = config.get('remember', False)
                    self.remember_checkbox.setChecked(remember)
                    print(f"🔘 设置记住密码复选框: {remember}")
                    
                    # 如果选择了记住密码，则加载卡密
                    if remember:
                        saved_key = config.get('key', '')
                        if saved_key:
                            self.key_input.setText(saved_key)
                            # 隐藏显示卡密
                            display_key = saved_key[:4] + "*" * (len(saved_key) - 4) if len(saved_key) > 4 else "*" * len(saved_key)
                            print(f"🔑 已加载保存的卡密: {display_key}")
                        else:
                            print("⚠️  记住密码已勾选，但没有保存的卡密")
                    else:
                        print("📝 记住密码未勾选，不加载卡密")
            else:
                print("📋 配置文件不存在，使用默认设置")
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            import traceback
            traceback.print_exc()
    
    def save_config(self):
        """保存配置"""
        try:
            config_dir = Path.home() / ".game_script_config"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "config.json"
            
            remember = self.remember_checkbox.isChecked()
            key_text = self.key_input.text()
            
            config = {
                'key': key_text if remember else '',
                'remember': remember
            }
            
            print(f"💾 保存配置到: {config_file}")
            print(f"📋 保存内容: remember={remember}, key存在={bool(key_text)}")
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            if remember and key_text:
                display_key = key_text[:4] + "*" * (len(key_text) - 4) if len(key_text) > 4 else "*" * len(key_text)
                print(f"✅ 配置保存成功，卡密: {display_key}")
            else:
                print("✅ 配置保存成功，未保存卡密")
                
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            import traceback
            traceback.print_exc()
    
    def verify_key(self):
        """验证卡密"""
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, '错误', '请输入有效卡密')
            return

        machine_code = get_machine_code()
        self.login_button.setEnabled(False)
        self.login_button.setText("验证中...")
        
        try:
            response = requests.post(
                'http://139.196.94.227:5000/verify',
                json={'card': key, 'device_id': machine_code},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                message = data.get('message', '')
                
                if status == 'success':
                    expiry_date = data.get('expiry_date', '')
                    try:
                        expire_time = datetime.strptime(expiry_date, '%Y-%m-%d %H:%M:%S')
                        if expire_time > datetime.now():
                            self.is_verified = True
                            self.start_button.setEnabled(True)
                            self.log(f"登录成功！有效期至：{expiry_date}")
                            QMessageBox.information(self, '成功', f'{message}！有效期至：{expiry_date}')
                            
                            # 保存配置
                            self.save_config()
                            
                            # 更新UI
                            self.login_button.setText("已验证")
                            self.login_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 12px; padding: 8px; }")
                            self.key_input.setEnabled(False)
                        else:
                            self.log("卡密已过期，请更换有效卡密")
                            QMessageBox.warning(self, '错误', '卡密已过期，请更换有效卡密')
                    except ValueError:
                        self.log(f"验证成功: {message}")
                        self.is_verified = True
                        self.start_button.setEnabled(True)
                        QMessageBox.information(self, '成功', message)
                        self.save_config()
                        self.login_button.setText("已验证")
                        self.login_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 12px; padding: 8px; }")
                        self.key_input.setEnabled(False)
                else:
                    self.log(f"验证失败: {message}")
                    QMessageBox.warning(self, '错误', message)
            else:
                error_msg = response.json().get('message', '未知错误')
                self.log(f"服务器错误: {error_msg}")
                QMessageBox.warning(self, '错误', f'服务器错误: {error_msg}')
        except requests.exceptions.RequestException as e:
            self.log(f"网络连接失败: {e}")
            QMessageBox.critical(self, '错误', f'网络连接失败: {e}')
        except Exception as e:
            self.log(f"验证过程中发生错误: {e}")
            QMessageBox.critical(self, '错误', f'验证过程中发生错误: {e}')
        finally:
            self.login_button.setEnabled(True)
            if not self.is_verified:
                self.login_button.setText("登录验证")

    def start_automation(self):
        """开始自动化"""
        if not self.is_verified:
            QMessageBox.warning(self, "提示", "请先通过卡密验证！")
            return
            
        if self.automation_thread and self.automation_thread.is_alive():
            self.log("自动化已在运行中")
            return
        
        # 开始自动化前检查游戏窗口
        self.log("🔍 检查游戏窗口位置...")
        success, message = self.window_manager.ensure_window_ready()
        if not success:
            if "请先登陆游戏" in message or "游戏窗口未找到" in message:
                QMessageBox.warning(self, "提示", "请先登陆游戏")
            else:
                QMessageBox.warning(self, "错误", f"游戏窗口准备失败: {message}")
            return
        else:
            self.log(f"✅ {message}")
            self.window_status_label.setText(f"窗口状态: 已就绪")
            self.window_status_label.setStyleSheet("font-size: 12px; color: green;")
            
        try:
            # 重置停止事件
            self.stop_event.clear()
            
            # 获取选择的模式、角色数量和键鼠控制方法
            selected_mode = self.mode_combo.currentText()
            total_roles = int(self.role_combo.currentText())
            input_method = self.input_combo.currentText()
            
            self.log(f"开始 {selected_mode} 自动化，角色数量: {total_roles}，键鼠控制: {input_method}")
            
            # 创建选择的输入控制器
            try:
                input_controller = create_input_controller(input_method)
                self.log(f"✅ {input_method} 键鼠控制器初始化成功")
            except Exception as e:
                self.log(f"❌ {input_method} 键鼠控制器初始化失败: {e}")
                QMessageBox.critical(self, "错误", f"键鼠控制器初始化失败: {e}")
                return
            
            # 根据模式启动相应的自动化
            if selected_mode == "妖气追踪":
                self.start_yaoqi_automation(total_roles, input_controller)
            elif selected_mode == "深渊地图":
                self.start_shenyuan_automation(total_roles, input_controller)
            
            # 更新UI状态
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("状态: 运行中")
            self.status_label.setStyleSheet("font-weight: bold; color: blue;")
            
        except Exception as e:
            self.log(f"启动自动化失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动自动化失败: {str(e)}")
    
    def start_yaoqi_automation(self, total_roles, input_controller):
        """启动妖气追踪自动化"""
        try:
            # 导入新的妖气追踪模块
            from yaoqi import YaoqiAutomator
            
            self.yaoqi_automator = YaoqiAutomator(input_controller=input_controller)
            
            # 在新线程中运行
            self.automation_thread = threading.Thread(
                target=self.yaoqi_automator.run_automation,
                args=(self.stop_event, total_roles, self.log),
                daemon=True
            )
            self.automation_thread.start()
            
        except Exception as e:
            self.log(f"启动妖气追踪自动化失败: {str(e)}")
            raise
    
    def start_shenyuan_automation(self, total_roles, input_controller):
        """启动深渊地图自动化"""
        try:
            # 导入新的深渊地图模块
            from shenyuan import ShenyuanAutomator
            
            self.shenyuan_automator = ShenyuanAutomator(input_controller=input_controller)
            
            # 在新线程中运行
            self.automation_thread = threading.Thread(
                target=self.shenyuan_automator.run_automation,
                args=(self.stop_event, self.log),
                daemon=True
            )
            self.automation_thread.start()
            
        except Exception as e:
            self.log(f"启动深渊地图自动化失败: {str(e)}")
            raise
    
    def stop_automation(self):
        """停止自动化"""
        try:
            self.log("正在停止自动化...")
            
            # 设置停止事件
            self.stop_event.set()
            
            # 等待线程结束
            if self.automation_thread and self.automation_thread.is_alive():
                self.automation_thread.join(timeout=5)
            
            # 清理单例实例，释放内存
            try:
                from singletons import disable_singletons, reset_all
                disable_singletons()
                reset_all()
                self.log("单例实例已清理")
            except ImportError:
                pass  # 如果没有单例管理器，继续正常运行
                
            self.log("自动化已停止")
            
            # 更新UI状态
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status_label.setText("状态: 已停止")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            
        except Exception as e:
            self.log(f"停止自动化时出错: {str(e)}")
    
    def toggle_detection(self):
        """切换实时检测"""
        if self.detection_thread and self.detection_thread.isRunning():
            self.stop_detection()
        else:
            self.start_detection()
    
    def start_detection(self):
        """开始实时检测"""
        try:
            self.detection_thread = DetectionThread()
            self.detection_thread.frame_ready.connect(self.update_detection_display)
            self.detection_thread.start()
            
            self.detection_button.setText("停止实时检测")
            self.detection_button.setStyleSheet("QPushButton { background-color: #ff9800; color: white; font-size: 14px; padding: 10px; }")
            self.log("实时检测已开始")
            
        except Exception as e:
            self.log(f"启动实时检测失败: {str(e)}")
    
    def stop_detection(self):
        """停止实时检测"""
        try:
            if self.detection_thread:
                self.detection_thread.stop()
                self.detection_thread.wait()
                
            self.detection_button.setText("开始实时检测")
            self.detection_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-size: 14px; padding: 10px; }")
            self.log("实时检测已停止")
            
        except Exception as e:
            self.log(f"停止实时检测时出错: {str(e)}")
    
    def update_detection_display(self, frame):
        """更新检测显示"""
        try:
            # 将OpenCV图像转换为Qt图像
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            
            # 缩放图像以适应标签
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.detection_label.size(), aspectRatioMode=1)
            self.detection_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"更新检测显示时出错: {e}")
    
    def update_status(self):
        """更新状态信息"""
        try:
            # 更新当前角色信息
            if hasattr(self, 'yaoqi_automator') and self.yaoqi_automator:
                current_role = getattr(self.yaoqi_automator, 'current_role', 0)
                total_roles = getattr(self.yaoqi_automator, 'total_roles', 1)
                self.current_role_label.setText(f"当前角色: {current_role + 1}/{total_roles}")
                
        except Exception as e:
            pass  # 静默处理状态更新错误
    
    def check_game_window_on_startup(self):
        """启动时检查游戏窗口"""
        try:
            success, message = self.window_manager.check_and_move_game_window()
            if success:
                self.window_status_label.setText(f"窗口状态: {message}")
                self.window_status_label.setStyleSheet("font-size: 12px; color: green;")
                self.log(f"✅ {message}")
            else:
                self.window_status_label.setText(f"窗口状态: {message}")
                self.window_status_label.setStyleSheet("font-size: 12px; color: red;")
                if "请先登陆游戏" in message:
                    self.log(f"⚠️ {message}")
                else:
                    self.log(f"❌ {message}")
        except Exception as e:
            error_msg = f"检查游戏窗口失败: {e}"
            self.window_status_label.setText(f"窗口状态: {error_msg}")
            self.window_status_label.setStyleSheet("font-size: 12px; color: red;")
            self.log(f"❌ {error_msg}")
    
    def check_and_move_window(self):
        """检查并移动游戏窗口"""
        try:
            self.window_check_button.setEnabled(False)
            self.window_check_button.setText("检查中...")
            
            success, message = self.window_manager.check_and_move_game_window()
            
            if success:
                self.window_status_label.setText(f"窗口状态: {message}")
                self.window_status_label.setStyleSheet("font-size: 12px; color: green;")
                self.log(f"✅ {message}")
                
                # 显示窗口信息
                window_info = self.window_manager.get_game_window_info()
                if window_info:
                    self.log(f"📋 窗口信息: 位置({window_info['left']}, {window_info['top']}), 大小{window_info['width']}x{window_info['height']}")
            else:
                self.window_status_label.setText(f"窗口状态: {message}")
                self.window_status_label.setStyleSheet("font-size: 12px; color: red;")
                if "请先登陆游戏" in message:
                    self.log(f"⚠️ {message}")
                    QMessageBox.warning(self, "提示", message)
                else:
                    self.log(f"❌ {message}")
                    
        except Exception as e:
            error_msg = f"检查游戏窗口失败: {e}"
            self.window_status_label.setText(f"窗口状态: {error_msg}")
            self.window_status_label.setStyleSheet("font-size: 12px; color: red;")
            self.log(f"❌ {error_msg}")
        finally:
            self.window_check_button.setEnabled(True)
            self.window_check_button.setText("检查游戏窗口")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 停止所有运行中的线程
            self.stop_automation()
            self.stop_detection()
            
            # 等待线程结束
            if self.automation_thread and self.automation_thread.is_alive():
                self.automation_thread.join(timeout=3)
                
            if self.detection_thread and self.detection_thread.isRunning():
                self.detection_thread.wait(3000)
                
            event.accept()
            
        except Exception as e:
            print(f"关闭窗口时出错: {e}")
            event.accept()



class DetectionThread(QThread):
    """实时检测线程"""
    
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.show_connections = True  # 控制是否显示连线
        
    def run(self):
        """运行检测线程 - 优化版本"""
        self.running = True
        error_count = 0
        max_errors = 5
        
        try:
            # 延迟导入YOLO和相关模块
            from ultralytics import YOLO
            from actions import YaoqiAttacker
            
            # 加载模型（使用CPU模式提高稳定性）
            model = YOLO('models/best.pt')
            # 优化YOLO设置，减少资源占用
            model.overrides['verbose'] = False
            model.overrides['max_det'] = 20  # 进一步降低最大检测数量
            model.overrides['device'] = 'cpu'  # 强制使用CPU模式
            
            # 小地图区域配置
            MAP_X1, MAP_Y1, MAP_X2, MAP_Y2 = 929, 53, 1059, 108
            
            # 只初始化攻击器用于基本检测，移除复杂的小地图检测
            attacker = YaoqiAttacker(yolo_model=model)
            
            with mss.mss() as sct:
                region = {'left': 0, 'top': 0, 'width': 1067, 'height': 600}
                
                while self.running:
                    try:
                        screenshot = sct.grab(region)
                        frame = np.array(screenshot)
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # 使用YOLO检测怪物和角色
                        monsters = attacker.detect_monsters(frame_rgb)
                        character_x, character_y = attacker.get_positions(frame_rgb)
                        
                        # 检测chenghao位置和door位置
                        chenghao_box = None
                        doors = []
                        try:
                            if model is not None:
                                results = model.predict(frame_rgb, verbose=False)
                                for result in results:
                                    for box in result.boxes:
                                        cls_id = int(box.cls)
                                        if cls_id in result.names:
                                            cls_name = result.names[cls_id]
                                            if cls_name == 'chenghao':
                                                chenghao_box = list(map(int, box.xyxy[0]))
                                                # 调整chenghao边界框的y轴坐标
                                                chenghao_box[1] += 80  # y1
                                                chenghao_box[3] += 80  # y2
                                            elif cls_name == 'door':
                                                door_box = list(map(int, box.xyxy[0]))
                                                door_center_x = door_box[0] + (door_box[2] - door_box[0]) // 2
                                                door_center_y = door_box[1] + (door_box[3] - door_box[1]) // 2
                                                doors.append({
                                                    'bbox': door_box,
                                                    'x': door_center_x,
                                                    'y': door_center_y
                                                })
                        except Exception:
                            pass
                        
                        # 简化检测，移除小地图高级检测避免冲突
                        character_grid, door_states, boss_grid = None, {}, None
                        
                        # 绘制怪物检测结果并添加连线
                        for monster in monsters:
                            try:
                                x1, y1, x2, y2 = monster['bbox']
                                monster_center_x = monster['x']
                                monster_center_y = monster['y']
                                color = (0, 0, 255) if monster['type'] == 'boss' else (0, 255, 0)  # Boss红色，小怪绿色
                                
                                # 绘制怪物检测框
                                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                                cv2.putText(frame, monster['type'], (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                                
                                # 如果检测到chenghao且启用连线显示，绘制连线
                                if self.show_connections and chenghao_box is not None and character_x is not None and character_y is not None:
                                    # 计算连线颜色（根据怪物类型）
                                    line_color = (0, 0, 255) if monster['type'] == 'boss' else (0, 255, 0)
                                    line_thickness = 3 if monster['type'] == 'boss' else 2  # Boss连线更粗
                                    
                                    # 绘制从chenghao到怪物的连线
                                    cv2.line(frame, (character_x, character_y), (monster_center_x, monster_center_y), line_color, line_thickness)
                                    
                                    # 只在距离较远时显示距离信息（减少文字渲染）
                                    distance = ((character_x - monster_center_x)**2 + (character_y - monster_center_y)**2)**0.5
                                    if distance > 80:  # 只在距离较远时显示
                                        mid_x = (character_x + monster_center_x) // 2
                                        mid_y = (character_y + monster_center_y) // 2
                                        
                                        # 绘制距离标签（小字体，半透明背景）
                                        distance_text = f"{int(distance)}"
                                        text_size = cv2.getTextSize(distance_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                                        cv2.rectangle(frame, (mid_x - text_size[0]//2 - 1, mid_y - text_size[1] - 1), 
                                                    (mid_x + text_size[0]//2 + 1, mid_y + 1), (0, 0, 0), -1)
                                        cv2.putText(frame, distance_text, (mid_x - text_size[0]//2, mid_y), 
                                                  cv2.FONT_HERSHEY_SIMPLEX, 0.35, line_color, 1)
                                    
                            except Exception:
                                continue  # 跳过有问题的怪物
                        
                        # 绘制角色位置
                        if character_x is not None and character_y is not None:
                            try:
                                cv2.circle(frame, (character_x, character_y), 10, (255, 0, 0), 2)
                                cv2.putText(frame, "Player", (character_x-20, character_y-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                            except Exception:
                                pass
                        
                        # 绘制chenghao检测框
                        if chenghao_box is not None:
                            try:
                                x1, y1, x2, y2 = chenghao_box
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 3)  # 黄色框，加粗
                                cv2.putText(frame, "chenghao", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                                
                                # 在chenghao中心绘制一个十字准星
                                center_x = (x1 + x2) // 2
                                center_y = (y1 + y2) // 2
                                cv2.line(frame, (center_x-5, center_y), (center_x+5, center_y), (255, 255, 0), 2)
                                cv2.line(frame, (center_x, center_y-5), (center_x, center_y+5), (255, 255, 0), 2)
                            except Exception:
                                pass
                        
                        # 绘制door检测结果并添加连线
                        for door in doors:
                            try:
                                door_box = door['bbox']
                                x1, y1, x2, y2 = door_box
                                door_center_x = door['x']
                                door_center_y = door['y']
                                
                                # 绘制door检测框（紫色）
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
                                cv2.putText(frame, "door", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
                                
                                # 如果棆测到chenghao且启用连线显示，绘制连线
                                if self.show_connections and chenghao_box is not None and character_x is not None and character_y is not None:
                                    # 绘制从chenghao到door的连线（紫色虚线）
                                    self.draw_dotted_line(frame, (character_x, character_y), (door_center_x, door_center_y), (255, 0, 255), 2)
                                    
                                    # 只在距离较远时显示距离信息
                                    distance = ((character_x - door_center_x)**2 + (character_y - door_center_y)**2)**0.5
                                    if distance > 60:  # door的距离阈值较小一些
                                        mid_x = (character_x + door_center_x) // 2
                                        mid_y = (character_y + door_center_y) // 2
                                        
                                        # 绘制距离标签（紫色背景）
                                        distance_text = f"{int(distance)}"
                                        text_size = cv2.getTextSize(distance_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)[0]
                                        cv2.rectangle(frame, (mid_x - text_size[0]//2 - 1, mid_y - text_size[1] - 1), 
                                                    (mid_x + text_size[0]//2 + 1, mid_y + 1), (128, 0, 128), -1)
                                        cv2.putText(frame, distance_text, (mid_x - text_size[0]//2, mid_y), 
                                                  cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
                                    
                            except Exception:
                                continue  # 跳过有问题的door
                        
                        # 绘制小地图边界和连线区域标识
                        MAP_X1, MAP_Y1, MAP_X2, MAP_Y2 = 929, 53, 1059, 108
                        cv2.rectangle(frame, (MAP_X1, MAP_Y1), (MAP_X2, MAP_Y2), (128, 128, 128), 1)
                        cv2.putText(frame, "MiniMap", (MAP_X1, MAP_Y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
                        
                        # 绘制连线区域标识和控制信息（右上角）
                        if self.show_connections:
                            cv2.putText(frame, "Connection Lines: ON", (850, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                            cv2.putText(frame, "Green: Monster", (850, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                            cv2.putText(frame, "Red: Boss", (850, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
                            cv2.putText(frame, "Purple: Door (dotted)", (850, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
                        else:
                            cv2.putText(frame, "Connection Lines: OFF", (850, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                            cv2.putText(frame, "Press 'C' to toggle", (850, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (128, 128, 128), 1)
                        
                        # 优化状态信息显示
                        try:
                            # 计算连线数量和状态
                            connection_count = 0
                            if self.show_connections and chenghao_box is not None and character_x is not None and character_y is not None:
                                connection_count = len(monsters) + len(doors)
                            
                            # 计算总检测数量
                            total_targets = len(monsters) + len(doors)
                            
                            # 定义状态符号
                            check_mark = '✓'
                            cross_mark = '✗'
                            
                            status_lines = [
                                f"Targets: {total_targets} (M:{len(monsters)} D:{len(doors)}) | Character: {'Found' if character_x else 'Missing'}",
                                f"Connections: {connection_count}/{total_targets} | Lines: {'ON' if self.show_connections else 'OFF'} | FPS: ~7",
                                f"Chenghao: {check_mark if chenghao_box else cross_mark} | Detection: Running | Mode: Enhanced"
                            ]
                            
                            # 绘制状态信息背景
                            status_bg_height = len(status_lines) * 25 + 10
                            cv2.rectangle(frame, (5, 5), (600, status_bg_height), (0, 0, 0), -1)
                            cv2.rectangle(frame, (5, 5), (600, status_bg_height), (255, 255, 255), 1)
                            
                            for i, status_text in enumerate(status_lines):
                                y_pos = 25 + i * 20
                                cv2.putText(frame, status_text, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                        except Exception:
                            pass
                        
                        # 发送帧到UI
                        self.frame_ready.emit(frame)
                        
                        # 重置错误计数
                        error_count = 0
                        
                        # 控制帧率，降低到更稳定的频率
                        self.msleep(150)  # 约7 FPS，进一步减少资源消耗
                        
                    except Exception as e:
                        error_count += 1
                        print(f"检测线程中发生错误 ({error_count}/{max_errors}): {e}")
                        
                        if error_count >= max_errors:
                            print("检测线程错误过多，停止运行")
                            break
                        
                        # 逐渐增加等待时间
                        wait_time = min(error_count * 200, 2000)  # 增加等待时间
                        self.msleep(wait_time)
                        
                        # 尝试释放资源
                        try:
                            from memory_manager import optimize_memory
                            optimize_memory()
                        except ImportError:
                            import gc
                            gc.collect()
                        
        except Exception as e:
            print(f"检测线程启动失败: {e}")
        finally:
            # 清理资源
            try:
                from memory_manager import optimize_memory
                optimize_memory()
            except ImportError:
                import gc
                gc.collect()
            except:
                pass
    
    def draw_dotted_line(self, img, pt1, pt2, color, thickness=1, gap=10):
        """绘制虚线"""
        try:
            x1, y1 = pt1
            x2, y2 = pt2
            
            # 计算线段长度
            length = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
            if length == 0:
                return
            
            # 计算单位向量
            dx = (x2 - x1) / length
            dy = (y2 - y1) / length
            
            # 绘制虚线段
            current_pos = 0
            while current_pos < length:
                # 绘制线段
                start_x = int(x1 + dx * current_pos)
                start_y = int(y1 + dy * current_pos)
                
                end_pos = min(current_pos + gap//2, length)
                end_x = int(x1 + dx * end_pos)
                end_y = int(y1 + dy * end_pos)
                
                cv2.line(img, (start_x, start_y), (end_x, end_y), color, thickness)
                current_pos += gap
        except Exception:
            # 如果虚线绘制失败，使用实线作为后备
            cv2.line(img, pt1, pt2, color, thickness)
    
    def stop(self):
        """停止检测线程"""
        self.running = False


def main():
    """主程序入口"""
    try:
        print("开始初始化应用程序...")
        
        # 创建QApplication
        app = QApplication(sys.argv)
        print("QApplication 初始化成功")
        
        print("开始初始化主窗口...")
        # 创建主窗口
        window = GameAutomationWindow()
        print("主窗口初始化成功")
        
        print("显示主窗口...")
        # 显示窗口
        window.show()
        print("应用程序启动完成")
        
        # 运行应用程序
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"应用程序启动失败: {e}")
        return 1


if __name__ == "__main__":
    main()