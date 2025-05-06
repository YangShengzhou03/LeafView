明白了，我会确保所有先前提供的信息都包含在内，并进一步丰富内容，以确保 `README.md` 文件尽可能详尽和全面。

---

# 🍁 LeafView（枫叶相册）V1.2 免费公测版

> **智能媒体整理软件 | 管理照片 & 视频更高效**

[![GitHub stars](https://img.shields.io/github/stars/yourusername/leafview)](https://github.com/yourusername/leafview)  
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 📚 目录

- [介绍](#介绍)
- [主要功能](#主要功能)
- [技术架构](#技术架构)
- [项目文件结构解析](#项目文件结构解析)
- [开发环境与依赖](#开发环境与依赖)
- [安装指南](#安装指南)
  - [Windows 用户](#windows-用户)
  - [Linux/macOS 用户](#linuxmacos-用户)
- [运行 LeafView](#运行-leafview)
- [使用说明](#使用说明)
- [安全与隐私保护](#安全与隐私保护)
- [参与贡献](#参与贡献)
  - [如何部署](#如何部署)
  - [常见问题及解决方案](#常见问题及解决方案)
  - [代码风格和提交规范](#代码风格和提交规范)
- [下载地址](#下载地址)
- [常见问题](#常见问题)
- [联系方式](#联系方式)
- [许可协议](#许可协议)

---

## 🌟 介绍

**LeafView（枫叶相册）** 是一款专为个人用户和摄影师设计的多媒体管理工具，利用先进的图像识别技术和多线程处理能力，帮助用户高效整理、分类和管理本地的照片与视频文件。它采用 Python + PyQt6 构建图形界面，结合多线程处理机制（QThread），支持大规模图片/视频文件的快速处理。所有操作均在本地完成，保障用户数据安全。

---

## 🔧 主要功能

### 1. 图像识别

#### 功能概述
LeafView 使用深度学习模型对图片进行分类。它可以自动识别并归类图像内容，如风景、人物、宠物等，并根据这些分类将图片存放到相应的文件夹中。

#### 支持的格式
- 图片：JPG, JPEG, PNG, BMP, WEBP
- 视频：MP4, MOV（视频仅支持基本元数据处理）

#### 使用场景
假设你有一大批旅行照片，LeafView 可以自动识别出哪些是风景照，哪些是人像照，并分别存放在不同的文件夹中，例如 `Scenery` 和 `Portraits`。

#### 示例
```bash
# 自动分类图片到指定目录
LeafView.exe --classify /path/to/images
```

### 2. 智能整理

#### 功能概述
智能整理功能允许用户根据拍摄时间、地点或其他自定义属性创建多层级文件夹结构。你可以选择是否移动或复制文件，以及是否递归扫描子文件夹。

#### 支持的操作
- 创建多级文件夹结构（如 `{年}/{月}_{地点}`）
- 移动或复制文件
- 递归扫描子文件夹
- 自动删除空文件夹

#### 使用场景
如果你有一堆散乱的照片，LeafView 可以帮助你根据拍摄日期和地点自动创建一个有序的文件夹结构，便于后续查找和管理。

#### 示例
```bash
# 根据拍摄时间和地点整理图片
LeafView.exe --organize /path/to/images --structure "{year}/{month}_{location}"
```

### 3. 智能重命名

#### 功能概述
智能重命名功能可以将拍摄时间和地点嵌入文件名中，增强文件的可读性和检索性。用户还可以自定义命名模板，包括时间戳、地理位置、相机型号等信息，甚至添加个性化标签或注释。

#### 支持的模板变量
- `{year}`: 拍摄年份
- `{month}`: 拍摄月份
- `{day}`: 拍摄日
- `{hour}`: 拍摄小时
- `{minute}`: 拍摄分钟
- `{second}`: 拍摄秒
- `{location}`: 拍摄地点（通过逆地理编码获取）
- `{camera}`: 相机型号

#### 使用场景
假设你有一张在巴黎埃菲尔铁塔拍摄的照片，你可以将其重命名为 `2023-10-01_巴黎_EiffelTower.jpg`，这样不仅便于记忆，也方便后续查找。

#### 示例
```bash
# 批量重命名图片
LeafView.exe --rename /path/to/images --template "{year}-{month}-{day}_{location}_{landmark}"
```

### 4. 文件去重

#### 功能概述
文件去重功能利用感知哈希算法（pHash）快速检测相似或重复的图片，并提供四种相似度阈值供用户选择。

#### 支持的格式
- JPG, PNG, BMP, HEIC 等常见图片格式

#### 四种相似度阈值
- 完全一致（0）：表示两张图片完全相同。
- 比较相似（8）：图片之间有轻微差异，但整体内容相似。
- 部分相似（24）：图片显示出明显的不同，但仍有一些共同元素。
- 明显差异（32）：图片之间存在显著的不同。

#### 使用场景
如果你有大量的照片库，LeafView 可以帮助你快速找到并移除重复的照片，节省存储空间。

#### 示例
```bash
# 查找并移除重复图片
LeafView.exe --deduplicate /path/to/images --threshold 8
```

### 5. EXIF 属性写入

#### 功能概述
通过 LeafView，用户可以直接编辑照片的 EXIF 数据，包括丰富的元数据（如拍摄日期、拍摄地点、相机设备型号、版权信息、作者、星级等），为每一张作品添加详尽的信息。

#### 支持的操作
- 编辑拍摄时间
- 编辑拍摄地点
- 添加版权信息
- 添加作者信息
- 添加星级评价

#### 使用场景
对于摄影师来说，确保每一张照片都有完整的元数据记录非常重要。LeafView 可以帮助你批量修改照片的拍摄时间和地点信息，并添加版权信息。

#### 示例
```bash
# 修改照片的拍摄时间和地点信息
LeafView.exe --write-exif /path/to/images --time "2023-10-01 10:00:00" --location "Paris, France"
```

### 6. 多线程处理

#### 功能概述
LeafView 利用 PyQt6 的 QThread 机制实现后台任务处理，确保在执行耗时操作（如图像识别、文件整理、去重等）时，UI 仍然保持响应性。

#### 支持的任务
- 图像识别
- 文件整理
- 文件去重
- EXIF 属性写入

#### 使用场景
当你处理大量照片时，LeafView 会利用多线程技术，确保你在等待过程中仍能与应用程序交互，查看进度条和其他状态提示。

#### 示例
```bash
# 启动多线程处理任务
LeafView.exe --process /path/to/images --threads 4
```

---

## 🏗️ 技术架构

### 架构概述

LeafView 基于 Python 开发，采用 PyQt6 实现图形用户界面，并通过 QThread 提供后台任务处理能力，确保应用程序在执行耗时操作时保持响应性。

### 关键组件

- **UI**: PyQt6 + Qt Designer
- **Backend**: OpenCV, PIL, exifread, geopy
- **Threading**: PyQt6 的 QThread 机制用于后台任务处理

### 整体架构图

```
+----------------------------+
|        用户界面 (UI)        |
|   PyQt6 + Qt Designer      |
+---------+------------------+
          |
          v
+---------v------------------+
|     控制逻辑层 (App.py)    |
|   MainWindow, Dialogs,     |
|   页面跳转、事件绑定等     |
+---------+------------------+
          |
          v
+---------v------------------+
|    功能模块 (Threads)      |
|   - ReadThread             |
|   - ClassificationThread   |
|   - ContrastThread         |
|   - WriteExifThread        |
+---------+------------------+
          |
          v
+---------v------------------+
|     数据处理核心           |
|   - Read.py                |
|   - Classification.py      |
|   - Contrast.py            |
|   - WriteExif.py           |
+---------+------------------+
          |
          v
+---------v------------------+
|     第三方库与系统调用     |
|   - OpenCV                 |
|   - Pillow                 |
|   - exifread               |
|   - geopy                  |
|   - PyInstaller打包        |
+----------------------------+
```

---

## 📁 项目文件结构解析

```bash
.
├── App.py                        # 主程序入口
├── App.spec                      # PyInstaller 打包配置文件
├── common.py                     # 公共函数模块
├── license.txt                   # MIT License 文本
├── LeafView_version_info.txt     # 版本信息
├── LeafView封装脚本.iss          # Inno Setup 安装脚本（Windows）
├── resources/                    # 资源文件（图标、图片等）
├── .idea/                        # IDE 配置文件（PyCharm）
│
├── UI_UpdateDialog.ui            # 更新对话框 UI 设计文件
├── Ui_MainWindow.ui              # 主窗口 UI 设计文件
├── UpdateDialog.py               # 更新对话框类
├── UI_UpdateDialog.py            # UI 对话框转换后的代码
├── Ui_MainWindow.py              # 主窗口转换后的代码
│
├── MainWindow.py                 # 主窗口逻辑
├── FolderPage.py                 # 文件夹选择页逻辑
│
├── ReadThread.py                 # 图片读取线程
├── Read.py                       # 图片读取核心逻辑
│
├── ClassificationThread.py       # 分类线程
├── Classification.py             # 图像分类核心逻辑
│
├── ContrastThread.py             # 去重线程
├── Contrast.py                   # 图像去重核心逻辑
│
├── WriteExifThread.py            # EXIF写入线程
├── WriteExif.py                  # EXIF写入核心逻辑
│
├── README.md                     # 项目说明文档
```

---

## 🛠️ 开发环境与依赖

### 开发语言

- Python 3.10+

### GUI框架

- PyQt6

### 并行处理

- QThread（Qt 内置线程机制）

### 图像处理

- OpenCV
- Pillow (PIL)
- ExifRead

### 地理编码

- Geopy（逆地理编码）

### 打包工具

- PyInstaller（生成 `.exe` 可执行文件）
- Inno Setup（Windows 安装包）

### 依赖库清单（requirements.txt）

```txt
PyQt6
opencv-python
pillow
exifread
geopy
numpy
```

---

## 💻 安装指南

### Windows 用户（推荐方式）

1. 下载压缩包或安装包：
   - 百度网盘：[下载地址]
   - 蓝奏云：提取码 `c9d7`
   - 123网盘：[下载地址]

2. 解压后运行 `LeafView.exe`

### 开发者模式（任意平台）

1. 克隆仓库：
   ```bash
   git clone https://github.com/yourusername/leafview.git
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 启动应用：
   ```bash
   python App.py
   ```

4. 打包为可执行文件（Windows）：
   ```bash
   pyinstaller App.spec
   ```

### 如何部署

#### 常见部署问题及解决方案

- **问题：找不到模块**
  - **解决方案**：确保所有依赖项已正确安装。可以尝试重新安装依赖：
    ```bash
    pip install --upgrade --force-reinstall -r requirements.txt
    ```
- **问题：UI界面无法正常显示**
  - **解决方案**：检查是否正确安装了PyQt6及其相关组件。确保您的Python环境中没有冲突的版本。
- **问题：打包后的应用程序无法启动**
  - **解决方案**：确保打包时包含所有必要的资源文件（如图标、配置文件等）。检查`App.spec`文件中的`datas`部分，确保添加了所有需要的资源路径。

### 二次开发注意事项

- **代码风格**：请遵循PEP8标准编写代码，并使用`black`进行代码格式化。
- **测试用例**：新增功能需附带单元测试，以保证代码质量。
- **文档更新**：修改或添加新功能后，请同步更新相关文档，确保其他开发者能够轻松理解并使用新特性。

---

## 📖 使用说明

### 快速上手

1. 打开软件后，点击【导入文件夹】选择目标路径。
2. 勾选【包含子文件夹】以扫描所有子目录。
3. 选择操作类型（图像识别 / 整理 / 重命名 / 去重 / 属性写入）。
4. 设置参数并点击【开始】执行任务。

### 操作示例

#### 示例 1：按时间和地点整理照片
- 选择“智能整理”
- 设置目标文件夹结构为 `{年}/{月}_{地点}`
- 勾选“使用拍摄时间”
- 点击“开始”

#### 示例 2：去除重复照片
- 选择“文件去重”
- 设置相似度阈值为“比较相似”
- 点击“开始”，等待结果展示
- 使用“智能选择”保留最佳图片
- 执行删除或移动操作

---

## 🔒 安全与隐私保护

- **本地处理**：所有操作均在本地完成，不上传任何数据。
- **网络请求**：仅在使用 AI 自动打标签时连接服务器（当前已停用）。
- **备份建议**：重要操作前请备份原始文件。
- **回收站机制**：删除操作默认移至回收站，可恢复。

---

## 🤝 参与贡献

我们欢迎所有形式的贡献！无论是代码优化、Bug修复、翻译还是文档完善，都欢迎提交 PR！

### 提交流程

1. Fork 本仓库。
2. 新建分支，例如 `feat-image-classification`。
3. 修改代码并提交。
4. 创建 Pull Request，并描述修改内容。
5. 经审核通过后合并进主分支。

### 贡献方向建议

- 添加新功能（如 RAW 格式支持、OCR识别等）
- 优化现有模块性能
- 提供更多语言版本（zh / en / ja / ko）
- 编写测试用例
- 丰富文档与示例

### 代码风格和提交规范

- **代码风格**：请遵循PEP8标准编写代码，并使用`black`进行代码格式化。
- **提交信息格式**：请按照以下格式填写提交信息：
  ```
  <type>(<scope>): <subject>

  <body>

  <footer>
  ```
  其中 `<type>` 可以为 feat, fix, docs, style, refactor, perf, test, chore；`<scope>` 表示修改的部分；`<subject>` 简短描述改动点；`<body>` 和 `<footer>` 分别是详细描述和备注。

---

## ⬇️ 下载地址

| 平台       | 类型         | 下载链接                                  |
|------------|--------------|-------------------------------------------|
| Windows    | 免费公测版   | 百度网盘：[下载地址]                      |
|            |              | 蓝奏云：提取码 `c9d7`                     |
|            |              | 123网盘：[下载地址]                       |
| GitHub     | 源代码       | [GitHub 仓库地址]                         |

---

## ❓ 常见问题

### Q1：为什么有些图片无法识别地理位置？
A：目前使用的逆地理编码服务有每日调用次数限制（5000次），超出后将无法获取位置信息。

### Q2：如何提高图像识别准确率？
A：确保图片清晰、主题明确；未来版本将提供模型更新选项。

### Q3：可以取消正在进行的操作吗？
A：当前版本暂不支持中断操作，请谨慎操作。

### Q4：是否支持 RAW 格式？
A：目前不支持 RAW，后续版本将考虑添加支持。

---

## 📞 联系方式

- 作者：Yangshengzhou  
- 博客：[CSDN 文章链接](https://blog.csdn.net/Yang_shengzhou/article/details/145328307)  
- GitHub：[github.com/yourusername/leafview](https://github.com/yourusername/leafview)  
- 邮箱：yangshengzhou@xxx.com  

---

## 📜 许可协议

该项目采用 [MIT License](LICENSE)，您可以自由使用、修改和分发，但需保留原版权声明及许可声明。

---

## ❤️ 感谢

感谢每一位使用 LeafView 的用户和开发者社区的支持！

> “让每一张照片都有归属，让每一次回忆都值得珍藏。”

---

希望这份详细的 `README.md` 文件能够帮助您更好地理解和使用 LeafView。如果您有任何进一步的问题或需要更多细节，请随时联系我们！欢迎您一起参与到这个项目中来，共同完善 LeafView，让它变得更好！

特别感谢所有为这个项目做出贡献的人，无论是通过代码提交、问题报告还是文档改进，每一个贡献都是宝贵的。让我们一起打造一个更好的 LeafView！