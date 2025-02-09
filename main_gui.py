import sys
import io
import time
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QRadioButton, 
                            QPushButton, QTextEdit, QGroupBox, QButtonGroup,
                            QMessageBox, QStatusBar, QScrollBar, QDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon
from main import USDTAddressGenerator
from playsound import playsound
import os
import json
from datetime import datetime
import glob

class GeneratorThread(QThread):
    """生成器线程"""
    progress = pyqtSignal(str)  # 进度信号
    finished = pyqtSignal()     # 完成信号
    error = pyqtSignal(str)     # 错误信号

    def __init__(self, generator, patterns, count):
        super().__init__()
        self.generator = generator
        self.patterns = patterns
        self.count = count
        self.is_running = True

    def run(self):
        try:
            self.generator.generate_addresses(self.patterns, self.count)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

class RedirectText(io.StringIO):
    def __init__(self, signal, speed_signal):
        super().__init__()
        self.signal = signal
        self.speed_signal = speed_signal

    def write(self, text):
        if text.startswith('\r'):
            # 速度信息以\r开头，发送到速度标签
            self.speed_signal.emit(text.strip())
        else:
            # 其他信息发送到日志区域
            self.signal.emit(text)

class ResultDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 获取主窗口的文件路径
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('生成结果')
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)

        # 关闭按钮
        close_button = QPushButton('关闭')
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.load_results()

    def load_results(self):
        try:
            results = []
            
            # 只检查一个统一的结果文件
            file = self.main_window.result_file
            
            # 检查文件是否存在且不为空
            if not os.path.exists(file) or os.path.getsize(file) == 0:
                self.result_text.setText("当前没有靓号信息")
                return

            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.strip().split('\n')
                    
                    for line in lines:
                        try:
                            wallet = json.loads(line.strip())
                            results.append(wallet)
                        except json.JSONDecodeError as e:
                            continue
                        except Exception as e:
                            continue

                if not results:
                    self.result_text.setText("当前没有靓号信息")
                    return

                # 格式化显示结果
                text = f"所有生成的靓号：\n\n"
                for i, wallet in enumerate(results, 1):
                    text += f"=== 靓号 {i} ===\n"
                    text += f"地址: {wallet['address']}\n"
                    if wallet.get('mnemonic'):  # 只有在有助记词时才显示
                        text += f"助记词: {wallet['mnemonic']}\n"
                    text += f"私钥: {wallet['private_key']}\n"
                    if 'generate_time' in wallet:
                        text += f"生成时间: {wallet['generate_time']}\n"
                    text += "="*50 + "\n\n"

                self.result_text.setText(text)

            except Exception as e:
                self.result_text.setText("当前没有靓号信息")

        except Exception as e:
            self.result_text.setText("当前没有靓号信息")

class MainWindow(QMainWindow):
    update_text = pyqtSignal(str)
    update_speed = pyqtSignal(str)  # 添加速度更新信号

    def __init__(self):
        super().__init__()
        self.generator = None
        self.generator_thread = None
        self.init_ui()
        
        # 获取当前目录的绝对路径
        current_dir = os.path.abspath(os.path.dirname(__file__))
        
        # 更新文件路径为统一的found_addresses.json
        self.result_file = os.path.join(current_dir, 'found_addresses.json')
        
        self.update_file_paths()
        
        # 重定向标准输出
        sys.stdout = RedirectText(self.update_text, self.update_speed)
        self.update_text.connect(self.append_text)
        self.update_speed.connect(self.update_speed_label)
        
        # 声音文件路径
        self.sound_file = os.path.join(os.path.dirname(__file__), 'complete.mp3')
        # 如果声音文件不存在，使用默认的系统提示音
        if not os.path.exists(self.sound_file):
            self.sound_file = {
                'darwin': '/System/Library/Sounds/Glass.aiff',  # macOS
                'win32': 'SystemAsterisk',                      # Windows
                'linux': '/usr/share/sounds/freedesktop/stereo/complete.oga'  # Linux
            }.get(sys.platform, None)

    def init_ui(self):
        self.setWindowTitle('USDT靓号生成器')
        self.setMinimumSize(800, 600)

        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 标题
        title_label = QLabel('USDT靓号生成器')
        title_label.setFont(QFont('Arial', 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # 设置组
        settings_group = QGroupBox('设置')
        settings_layout = QVBoxLayout()

        # 模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel('生成模式:')
        self.mode_group = QButtonGroup()
        self.mnemonic_radio = QRadioButton('助记词模式')
        self.privatekey_radio = QRadioButton('私钥模式')
        self.mnemonic_radio.setChecked(True)
        self.mode_group.addButton(self.mnemonic_radio)
        self.mode_group.addButton(self.privatekey_radio)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mnemonic_radio)
        mode_layout.addWidget(self.privatekey_radio)
        mode_layout.addStretch()
        settings_layout.addLayout(mode_layout)

        # 靓号模式输入
        pattern_layout = QHBoxLayout()
        pattern_label = QLabel('靓号模式:')
        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText('多个模式用逗号分隔，如: 888,666,999')
        self.pattern_input.setText('888,666,999')
        pattern_layout.addWidget(pattern_label)
        pattern_layout.addWidget(self.pattern_input)
        settings_layout.addLayout(pattern_layout)

        # 生成数量输入
        count_layout = QHBoxLayout()
        count_label = QLabel('生成数量:')
        self.count_input = QLineEdit()
        self.count_input.setPlaceholderText('请输入需要生成的数量')
        self.count_input.setText('1')
        count_layout.addWidget(count_label)
        count_layout.addWidget(self.count_input)
        settings_layout.addLayout(count_layout)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_button = QPushButton('开始生成')
        self.stop_button = QPushButton('停止生成')
        self.view_results_button = QPushButton('查看结果')  # 新增查看结果按钮
        
        self.start_button.clicked.connect(self.start_generation)
        self.stop_button.clicked.connect(self.stop_generation)
        self.view_results_button.clicked.connect(self.view_results)  # 连接查看结果功能
        
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.view_results_button)
        main_layout.addLayout(button_layout)

        # 在控制按钮下方添加速度显示
        speed_frame = QGroupBox('运行状态')
        speed_layout = QHBoxLayout()
        
        # 创建状态标签
        self.speed_label = QLabel('当前速度: <span style="color: red">0</span> 个/秒')
        self.total_label = QLabel('已尝试: <span style="color: red">0</span> 个')
        self.found_label = QLabel('已找到: <span style="color: red">0/0</span> 个')
        
        # 设置字体和样式
        font = QFont('Arial', 14, QFont.Weight.Bold)  # 增大字体到14号
        self.speed_label.setFont(font)
        self.total_label.setFont(font)
        self.found_label.setFont(font)
        
        # 设置样式表
        style = """
            QLabel {
                padding: 8px;
                margin: 3px;
                background-color: #f8f9fa;
                border-radius: 4px;
            }
        """
        self.speed_label.setStyleSheet(style)
        self.total_label.setStyleSheet(style)
        self.found_label.setStyleSheet(style)
        
        # 启用富文本
        self.speed_label.setTextFormat(Qt.TextFormat.RichText)
        self.found_label.setTextFormat(Qt.TextFormat.RichText)
        self.total_label.setTextFormat(Qt.TextFormat.RichText)
        
        # 添加到布局
        speed_layout.addWidget(self.speed_label)
        speed_layout.addWidget(self.total_label)
        speed_layout.addWidget(self.found_label)
        speed_frame.setLayout(speed_layout)
        
        # 添加到主布局
        main_layout.addWidget(speed_frame)

        # 在速度显示框架下方添加文件路径显示
        file_frame = QGroupBox('保存位置')
        file_layout = QVBoxLayout()
        
        # 创建文件路径标签
        self.mnemonic_path_label = QLabel('结果保存位置: ')
        self.privatekey_path_label = QLabel('私钥模式文件: ')
        
        # 设置字体
        path_font = QFont('Arial', 10)
        self.mnemonic_path_label.setFont(path_font)
        self.privatekey_path_label.setFont(path_font)
        
        # 设置样式
        path_style = """
            QLabel {
                padding: 5px;
                color: #0066cc;
            }
        """
        self.mnemonic_path_label.setStyleSheet(path_style)
        self.privatekey_path_label.setStyleSheet(path_style)
        
        # 添加到布局
        file_layout.addWidget(self.mnemonic_path_label)
        file_layout.addWidget(self.privatekey_path_label)
        file_frame.setLayout(file_layout)
        
        # 添加到主布局
        main_layout.addWidget(file_frame)

        # 输出区域
        output_group = QGroupBox('运行日志')
        output_layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)

        # 状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage('就绪')

    def append_text(self, text):
        """当输出包含"找到靓号地址"时更新文件路径显示"""
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.output_text.setTextCursor(cursor)
        self.output_text.insertPlainText(text)
        self.output_text.ensureCursorVisible()
        
        # 当找到新的靓号时，更新文件路径显示
        if "找到靓号地址" in text:
            self.update_file_paths()

    def validate_inputs(self):
        """验证输入"""
        patterns = self.pattern_input.text().strip()
        if not patterns:
            QMessageBox.warning(self, '错误', '请输入靓号模式')
            return False

        try:
            count = int(self.count_input.text())
            if count <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, '错误', '请输入有效的生成数量（正整数）')
            return False

        return True

    def start_generation(self):
        if not self.validate_inputs():
            return

        # 获取输入值
        patterns = self.pattern_input.text().split(',')
        count = int(self.count_input.text())
        mode = 'mnemonic' if self.mnemonic_radio.isChecked() else 'privatekey'

        # 更新界面状态
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.statusBar.showMessage('正在生成中...')
        self.output_text.clear()

        try:
            # 创建生成器实例
            self.generator = USDTAddressGenerator(mode=mode)
            
            # 创建并启动生成线程
            self.generator_thread = GeneratorThread(self.generator, patterns, count)
            self.generator_thread.finished.connect(self.generation_finished)
            self.generator_thread.error.connect(self.generation_error)
            self.generator_thread.start()

        except Exception as e:
            self.statusBar.showMessage(f'错误: {str(e)}')
            self.stop_generation()

    def stop_generation(self):
        if self.generator:
            self.generator.stop()
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.statusBar.showMessage('已停止')

    def play_complete_sound(self):
        """播放完成提示音"""
        try:
            print('\a')  # 输出系统蜂鸣声
            sys.stdout.flush()
        except:
            pass

    def generation_finished(self):
        self.statusBar.showMessage('完成')
        self.stop_generation()
        # 更新文件路径显示（包含文件大小）
        self.update_file_paths()
        # 播放完成提示音
        self.play_complete_sound()
        # 如果窗口最小化了，恢复窗口
        if self.isMinimized():
            self.showNormal()
        # 将窗口置于前台
        self.activateWindow()

    def generation_error(self, error_msg):
        self.statusBar.showMessage(f'错误: {error_msg}')
        self.stop_generation()

    def closeEvent(self, event):
        if self.generator:
            self.generator.stop()
        event.accept()

    def update_speed_label(self, text):
        """更新速度标签"""
        try:
            # 解析速度信息
            parts = text.split('|')
            if len(parts) >= 3:
                # 提取数字并设置带颜色的文本
                speed_text = parts[0].strip()
                found_text = parts[1].strip()
                total_text = parts[2].strip()
                
                # 将数字部分用红色显示
                speed_num = speed_text.split(':')[1].strip()
                found_nums = found_text.split(':')[1].strip()
                total_num = total_text.split(':')[1].strip()
                
                # 格式化数字（保留两位小数）
                try:
                    speed_formatted = f"{float(speed_num.split()[0]):.2f}"
                except:
                    speed_formatted = speed_num
                
                self.speed_label.setText(f"当前速度: <span style='color: red'>{speed_formatted}</span> 个/秒")
                self.found_label.setText(f"已找到: <span style='color: red'>{found_nums}</span>")
                self.total_label.setText(f"已尝试: <span style='color: red'>{total_num}</span>")
        except:
            pass

    def view_results(self):
        """显示结果对话框"""
        dialog = ResultDialog(self)
        dialog.exec()

    def update_file_paths(self):
        """更新文件路径显示"""
        # 统一显示一个文件路径
        file_info = f'结果保存位置: {self.result_file}'
        
        # 检查文件是否存在并显示大小
        try:
            if os.path.exists(self.result_file):
                size = os.path.getsize(self.result_file) / 1024  # KB
                file_info += f' ({size:.1f} KB)'
        except:
            pass
            
        self.mnemonic_path_label.setText(file_info)
        self.privatekey_path_label.hide()  # 隐藏不需要的标签

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MainWindow()
    
    # 将窗口居中显示
    screen = app.primaryScreen().geometry()
    x = (screen.width() - window.width()) // 2
    y = (screen.height() - window.height()) // 2
    window.move(x, y)
    
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 