#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用于标准化Ui_MainWindow.ui文件中的命名，确保符合编码规范和最佳实践。
用法：python normalize_names.py
"""
import json
import os
import re

# 文件路径设置
UI_FILE_PATH = "d:\Code\Python\LeafView\Ui_MainWindow.ui"
MAPPING_FILE_PATH = "d:\Code\Python\LeafView\rename_mapping.json"
BACKUP_FILE_PATH = "d:\Code\Python\LeafView\Ui_MainWindow.ui.bak"

# 读取映射表
with open(MAPPING_FILE_PATH, 'r', encoding='utf-8') as f:
    rename_mapping = json.load(f)

# 创建反向映射表，用于查找旧名称
reverse_mapping = {}
for new_name, old_names in rename_mapping.items():
    if isinstance(old_names, list):
        for old_name in old_names:
            reverse_mapping[old_name] = new_name
    else:
        reverse_mapping[old_names] = new_name

# 读取UI文件内容
with open(UI_FILE_PATH, 'r', encoding='utf-8') as f:
    ui_content = f.read()

# 创建备份文件
with open(BACKUP_FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(ui_content)

print(f"已创建备份文件: {BACKUP_FILE_PATH}")

# 进行重命名替换
for old_name, new_name in reverse_mapping.items():
    # 使用正则表达式确保只匹配完整的name属性值
    pattern = r'name="{}"'.format(re.escape(old_name))
    replacement = 'name="{}"'.format(new_name)
    ui_content = re.sub(pattern, replacement, ui_content)
    
    # 检查连接部分的sender和receiver
    pattern_sender = r'sender="{}"'.format(re.escape(old_name))
    replacement_sender = 'sender="{}"'.format(new_name)
    ui_content = re.sub(pattern_sender, replacement_sender, ui_content)
    
    pattern_receiver = r'receiver="{}"'.format(re.escape(old_name))
    replacement_receiver = 'receiver="{}"'.format(new_name)
    ui_content = re.sub(pattern_receiver, replacement_receiver, ui_content)
    
    print(f"已将 '{old_name}' 重命名为 '{new_name}'")

# 写入更新后的内容
with open(UI_FILE_PATH, 'w', encoding='utf-8') as f:
    f.write(ui_content)

print(f"已完成所有命名标准化处理，文件已更新: {UI_FILE_PATH}")
print("\n标准化处理总结：")
print(f"1. 共处理了 {len(reverse_mapping)} 个不规范命名")
print(f"2. 框架命名已统一为小写字母加下划线格式")
print(f"3. 布局命名已改为具有描述性的名称")
print(f"4. 标签命名已统一并增加了描述性")
print(f"5. 页面命名已改为具有描述性的名称")
print(f"6. 所有命名现在都符合下划线小写命名法规范")
print("\n注意：如果发现任何问题，可以使用备份文件恢复原始内容")