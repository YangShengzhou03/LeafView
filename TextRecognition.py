#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文字识别模块
功能：识别图像中的文字并根据文字内容进行整理
"""
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import pyqtSignal, QThread, QDateTime
import os
import shutil
from datetime import datetime
from PIL import Image
import pytesseract

from common import get_resource_path, detect_media_type


class TextRecognitionThread(QThread):
    progress_updated = pyqtSignal(int)
    log_updated = pyqtSignal(str, str)
    recognition_complete = pyqtSignal(dict)
    
    def __init__(self, image_paths, lang='chi_sim+eng'):
        super().__init__()
        self.image_paths = image_paths
        self.lang = lang
        self._stop_requested = False
    
    def run(self):
        results = {}
        total = len(self.image_paths)
        
        for i, image_path in enumerate(self.image_paths):
            if self._stop_requested:
                self.log_updated.emit('INFO', '您取消了文字识别操作')
                return
                
            try:
                # 检测文件是否为有效图片
                media_info = detect_media_type(image_path)
                if not media_info['valid']:
                    self.log_updated.emit('ERROR', f'{os.path.basename(image_path)} 不是可以识别的图片文件\n\n' 
                                     '请检查文件格式是否正确，文件是否完整')
                    continue
                
                # 执行OCR识别
                text = self._recognize_image_text(image_path)
                results[image_path] = text
                
                # 发送进度更新
                self.progress_updated.emit(int((i + 1) / total * 100))
                
            except Exception as e:
                self.log_updated.emit('ERROR', f'处理 {os.path.basename(image_path)} 时出错了: {str(e)}')
                
        self.recognition_complete.emit(results)
    
    def _recognize_image_text(self, image_path):
        try:
            with Image.open(image_path) as img:
                # 预处理图像：转换为灰度图以提高识别率
                gray_img = img.convert('L')
                # 执行OCR
                text = pytesseract.image_to_string(gray_img, lang=self.lang)
                return text.strip()
        except Exception as e:
            self.log_updated.emit('ERROR', f'识别 {os.path.basename(image_path)} 里的文字失败了: {str(e)}\n\n' 
                             '可能的原因：\n' 
                             '• 图片太模糊或质量不好\n' 
                             '• 电脑上没有正确安装OCR识别软件\n' 
                             '• 缺少识别所需的语言数据包')
            return ''
    
    def stop(self):
        self._stop_requested = True


class TextRecognition(QtWidgets.QWidget):
    log_signal = pyqtSignal(str, str)

    def __init__(self, parent=None, folder_page=None):
        super().__init__(parent)
        self.parent = parent
        self.folder_page = folder_page
        self.recognition_thread = None
        self.recognition_results = {}
        self.log_signal.connect(self.log)
        self.init_page()

    def init_page(self):
        # 初始化UI组件
        layout = QtWidgets.QVBoxLayout()
        
        self.recognize_btn = QtWidgets.QPushButton('识别图片文字')
        self.recognize_btn.clicked.connect(self.recognize_text)
        layout.addWidget(self.recognize_btn)
        
        self.organize_btn = QtWidgets.QPushButton('按文字整理')
        self.organize_btn.clicked.connect(self.organize_by_text)
        self.organize_btn.setEnabled(False)  # 先禁用，识别后启用
        layout.addWidget(self.organize_btn)
        
        # 添加进度条
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 初始化log_text属性
        if hasattr(self.parent, 'textEdit_TextRecognition_Log'):
            self.log_text = self.parent.textEdit_TextRecognition_Log
        else:
            self.log_text = QtWidgets.QTextEdit()
            self.log_text.setReadOnly(True)
            layout.addWidget(QtWidgets.QLabel('识别日志:'))
            layout.addWidget(self.log_text)
        
        self.setLayout(layout)
        
        # 初始化页面，连接信号等
        self._connect_signals()
        self.log("INFO", "欢迎使用文字识别和整理功能")
        
    def _connect_signals(self):
        # 连接按钮信号
        pass
        
    def log(self, level, message):
        """输出日志信息到日志控件"""
        c = {'ERROR': '#FF0000', 'WARNING': '#FFA500', 'DEBUG': '#008000', 'INFO': '#8677FD'}
        if hasattr(self.parent, 'textEdit_TextRecognition_Log'):
            self.parent.textEdit_TextRecognition_Log.append(
                f'<span style="color:{c.get(level, "#000000")}">[{datetime.now().strftime("%H:%M:%S")}]' \
                f' [{level}] {message}</span>')
        else:
            time_str = QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')
            self.log_text.append(f'[{level}] {time_str} {message}')
        
    def recognize_text(self):
        """识别图像上的文字"""
        folders = self.folder_page.get_all_folders() if self.folder_page else []
        if not folders:
            self.log("WARNING", "请先导入一个有图片的文件夹\n\n"
                           "点击\"导入文件夹\"按钮选择包含图片的文件夹")
            return
        
        # 收集所有图片文件
        image_paths = []
        for folder_path, include_sub in folders:
            if os.path.isdir(folder_path):
                self.log('INFO', f'正在查看文件夹: {folder_path}')
                if include_sub:
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            media_info = detect_media_type(file_path)
                            if media_info['valid'] and media_info['type'] == 'image':
                                image_paths.append(file_path)
                else:
                    for file in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, file)
                        if os.path.isfile(file_path):
                            media_info = detect_media_type(file_path)
                            if media_info['valid'] and media_info['type'] == 'image':
                                image_paths.append(file_path)
        
        if not image_paths:
            self.log('WARNING', '没有找到任何可以识别的图片文件\n\n'
                           '请检查：\n'
                           '• 文件夹里有没有.jpg、.jpeg、.png、.webp这些格式的图片\n'
                           '• 您选择的文件夹路径是否正确')
            return
        
        self.log('INFO', f'找到了 {len(image_paths)} 张图片，现在开始识别里面的文字...')
        
        # 启动识别线程
        self.progress_bar.setValue(0)
        self.recognition_thread = TextRecognitionThread(image_paths)
        self.recognition_thread.progress_updated.connect(self.update_progress)
        self.recognition_thread.log_updated.connect(self.log)
        self.recognition_thread.recognition_complete.connect(self.on_recognition_complete)
        self.recognition_thread.start()
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def on_recognition_complete(self, results):
        self.recognition_results = results
        
        # 统计识别结果
        total = len(results)
        success_count = sum(1 for text in results.values() if text)
        
        self.log('INFO', f'文字识别完成啦！\n\n'
                   f'统计一下：\n'
                   f'• 总共有 {total} 张图片\n'
                   f'• 成功识别了 {success_count} 张\n'
                   f'• 识别成功率：{success_count/total*100:.1f}%')
        self.organize_btn.setEnabled(True)
    
    def organize_by_text(self):
        """根据识别到的文字进行整理"""
        if not self.recognition_results:
            self.log('ERROR', '请先执行文字识别\n\n'
                         '点击"识别图片文字"按钮开始识别')
            return
        
        # 让用户选择保存目录
        save_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "选择保存目录", ".")
        if not save_dir:
            self.log('INFO', '⏹️ 用户取消了保存目录选择')
            return
        
        self.log('INFO', f'开始按文字整理图片到目录: {save_dir}')
        
        # 创建基于识别文字的文件夹结构
        success_count = 0
        error_count = 0
        
        for image_path, text in self.recognition_results.items():
            if not text:
                continue
                
            # 提取关键词作为文件夹名（取前几个字符）
            keywords = text.split('\n')[0][:20]  # 取第一行前20个字符
            # 清理文件夹名中的非法字符
            valid_folder_name = "".join(c for c in keywords if c.isalnum() or c in (' ', '-', '_'))
            if not valid_folder_name:
                valid_folder_name = "未命名"
                
            # 创建文件夹
            target_folder = os.path.join(save_dir, valid_folder_name)
            os.makedirs(target_folder, exist_ok=True)
            
            # 复制文件到目标文件夹
            try:
                target_path = os.path.join(target_folder, os.path.basename(image_path))
                shutil.copy2(image_path, target_path)
                self.log('INFO', f'已复制 {os.path.basename(image_path)} 到 {valid_folder_name}')
                success_count += 1
            except Exception as e:
                self.log('ERROR', f'复制文件 {os.path.basename(image_path)} 时出错: {str(e)}')
                error_count += 1
                
        # 显示整理结果
        self.log('INFO', f'按文字整理完成！\n\n'
                   f'统计信息：\n'
                   f'• 成功整理: {success_count} 个文件\n'
                   f'• 失败: {error_count} 个文件\n'
                   f'• 成功率: {success_count/(success_count+error_count)*100:.1f}%')
        
        # 显示完成提示
        QtWidgets.QMessageBox.information(
            self, 
            "操作完成", 
            f"文字识别整理操作已完成！\n\n"
            f"共成功整理 {success_count} 个文件到目标目录。\n\n"
            f"您可以在 {save_dir} 中查看整理后的文件。"
        )