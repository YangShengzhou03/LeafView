<div align="center">
  <h1>🍁 枫叶相册 - LeafView</h1>
  
  <p>
    <em>基于 PyQt6 构建的现代化图片与媒体管理工具</em>
  </p>

  <div>
    <a href="https://github.com/YangShengzhou03/LeafView/stargazers">
      <img src="https://img.shields.io/github/stars/YangShengzhou03/LeafView?style=for-the-badge&logo=github&color=ffd33d&labelColor=000000" alt="GitHub Stars">
    </a>
    <a href="https://github.com/YangShengzhou03/LeafView/forks">
      <img src="https://img.shields.io/github/forks/YangShengzhou03/LeafView?style=for-the-badge&logo=github&color=green&labelColor=000000" alt="GitHub Forks">
    </a>
    <a href="https://opensource.org/licenses/MIT">
      <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge&logo=open-source-initiative&color=blue&labelColor=000000" alt="MIT License">
    </a>
    <a href="https://github.com/YangShengzhou03/LeafView/issues">
      <img src="https://img.shields.io/github/issues/YangShengzhou03/LeafView?style=for-the-badge&logo=github&color=purple&labelColor=000000" alt="GitHub Issues">
    </a>
  </div>

  <div>
    <a href="https://www.python.org/">
      <img src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python" alt="Python Version">
    </a>
    <a href="https://www.riverbankcomputing.com/software/pyqt/">
      <img src="https://img.shields.io/badge/PyQt6-6.4.2-green?style=for-the-badge&logo=qt" alt="PyQt6 Version">
    </a>
    <a href="https://pillow.readthedocs.io/en/stable/">
      <img src="https://img.shields.io/badge/Pillow-11.3.0-orange?style=for-the-badge&logo=pypi" alt="Pillow Version">
    </a>
  </div>

  <br />
  
  [![Star History Chart](https://api.star-history.com/svg?repos=YangShengzhou03/LeafView&type=Date)](https://star-history.com/#YangShengzhou03/LeafView&Date)

</div>

## 目录
1. [✨ 项目概述](#-项目概述)
2. [🚀 技术架构](#-技术架构)
3. [🌟 核心功能](#-核心功能)
4. [💻 安装部署](#-安装部署)
5. [📖 使用说明](#-使用说明)
6. [📁 目录结构](#-目录结构)
7. [🤝 参与贡献](#-参与贡献)
8. [📜 开源许可](#-开源许可)
9. [🔄 更新日志](#-更新日志)

## ✨ 项目概述
枫叶相册 (LeafView) 是一款基于 **Python** 和 **PyQt6** 构建的**开源图片与媒体管理工具**，为用户提供直观、高效的图片浏览和管理体验。系统采用单例模式设计，支持多种图片格式，并提供智能整理、去重、EXIF信息编辑等功能。

### 🎯 设计理念
- **用户友好**：简洁直观的界面设计，降低使用门槛
- **高效管理**：批量处理能力，提高工作效率
- **智能分析**：基于图像哈希和EXIF数据的智能分类与整理
- **安全可靠**：提供预览和确认机制，防止误操作

### 💡 适用场景
- 个人图片库管理
- 摄影爱好者的照片整理
- 图片批量处理与重命名
- 图片元数据编辑
- 重复图片检测与清理
- 图片文字识别与分类

## 🚀 技术架构

### 🔧 技术栈
| 技术                | 版本      | 描述                                                         |
|---------------------|-----------|--------------------------------------------------------------|
| **Python 3.11**     | 3.11+     | 主要编程语言，提供强大的后端处理能力                         |
| **PyQt6**           | 6.4.2+    | 跨平台GUI框架，用于构建直观、美观的用户界面                  |
| **Pillow**          | 11.3.0    | Python图像处理库，支持各种图片格式的读写和处理              |
| **pillow-heif**     | 1.1.0     | HEIF格式支持，扩展Pillow对HEIC等格式的兼容性                 |
| **piexif**          | 1.1.3     | 用于读取和写入EXIF元数据信息                                |
| **pytesseract**     | 0.3.10    | OCR文字识别引擎，提供图片文字识别功能                        |
| **requests**        | 2.31.0    | HTTP客户端库，用于检查更新和网络请求                        |
| **send2trash**      | 1.8.2     | 安全删除文件到回收站的工具                                   |
| **numpy**           | 1.26.4    | 科学计算库，用于图像数据处理                                |
| **exifread**        | 3.0.0     | EXIF数据读取库                                              |
| **moviepy**         | 1.0.3     | 视频处理库，支持媒体文件处理                                |

### 🏗️ 系统架构
```
┌─────────────────────────────────────────────────────────────┐
│                    枫叶相册 - LeafView                      │
├─────────────────────────────────────────────────────────────┤
│                    用户界面层 (UI Layer)                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │ 主窗口      │ │ 智能整理    │ │ 去重对比    │ │ EXIF编辑 │ │
│  │ MainWindow  │ │ SmartArrange│ │RemoveDupli..│ │WriteExif │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
│  ┌─────────────┐ ┌─────────────┐                         │
│  │ 文字识别    │ │ 设置对话框  │                         │
│  │TextRecogni..│ │SettingsDial.│                         │
│  └─────────────┘ └─────────────┘                         │
├─────────────────────────────────────────────────────────────┤
│                    业务逻辑层 (Business Layer)              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │ 文件夹管理  │ │ 整理线程    │ │ 去重线程    │ │ EXIF线程│ │
│  │ AddFolder   │ │SmartArrange.│ │RemoveDupli..│ │WriteExif│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
│  ┌─────────────┐ ┌─────────────┐                         │
│  │ 识别线程    │ │ 更新检查    │                         │
│  │TextRecogni..│ │UpdateDialog │                         │
│  └─────────────┘ └─────────────┘                         │
├─────────────────────────────────────────────────────────────┤
│                    数据处理层 (Data Layer)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │
│  │ 图像处理    │ │ EXIF数据    │ │ 哈希计算    │ │ OCR引擎 │ │
│  │   Pillow    │ │   piexif    │ │   感知哈希  │ │tesseract│ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │
│  ┌─────────────┐ ┌─────────────┐                         │
│  │ 配置管理    │ │ 公共工具    │                         │
│  │configManager│ │   common    │                         │
│  └─────────────┘ └─────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## 🌟 核心功能

### 📷 **图片管理**
- **多格式支持**：JPG、PNG、HEIC、TIFF、BMP、WEBP、GIF等主流图片格式
- **文件夹导入**：支持拖拽操作，可递归导入子文件夹
- **缩略图预览**：高效生成和缓存缩略图，支持快速浏览
- **大图查看**：高质量图像渲染，支持缩放和导航
- **媒体类型检测**：自动识别文件类型，过滤非媒体文件

### 🧹 **智能整理**
- **多级分类结构**：支持按年份、月份、日期、星期、时间、品牌、位置等多维度分类
- **自定义文件夹结构**：灵活配置分类层级，满足不同整理需求
- **批量重命名**：支持多种命名规则和分隔符，可组合使用多种标签
- **文件操作**：支持移动或复制到目标目录，保留原始文件结构
- **实时预览**：整理前预览目标路径结构，避免误操作
- **操作确认**：执行前提供详细操作说明和确认机制

### 🔍 **去重功能**
- **智能检测**：基于感知哈希算法检测重复图片
- **相似度控制**：可调节相似度阈值，从完全一致到部分相似
- **可视化展示**：相似图片分组展示，直观对比
- **批量操作**：支持批量选择和操作（移动、删除）重复图片
- **安全删除**：使用回收站机制，防止误删重要文件
- **多线程处理**：提高处理性能，支持大量图片处理

### 📝 **EXIF编辑**
- **全面元数据支持**：查看和编辑图片EXIF信息
- **星级评分系统**：1-5星评分，便于图片筛选和管理
- **设备信息编辑**：支持修改相机品牌、型号、镜头等信息
- **时间调整**：修改拍摄日期和时间，支持批量调整
- **地理位置**：编辑GPS坐标信息，支持反向地理编码
- **批量处理**：一次性处理多张图片，提高效率

### 🔤 **文字识别**
- **OCR引擎**：基于Tesseract的高精度文字识别
- **多语言支持**：支持中文、英文等多种语言识别
- **批量处理**：一次识别多张图片中的文字
- **智能整理**：根据识别的文字内容自动分类整理
- **结果导出**：支持复制或保存识别结果
- **进度显示**：实时显示识别进度和统计信息

### ⚙️ **系统功能**
- **单例模式**：确保同一时间只有一个应用实例运行
- **自动更新**：内置更新检查机制，及时获取最新版本
- **设置管理**：个性化配置界面，自定义使用体验
- **日志记录**：详细操作日志，便于问题排查
- **无边框界面**：现代化UI设计，支持自定义主题

## 💻 安装部署

### 🔧 环境准备
- **操作系统**：Windows 10/11、macOS 10.14+、Linux (Ubuntu 18.04+)
- **Python**：3.8 及以上版本
- **内存**：建议 4GB 以上 RAM
- **存储**：至少 500MB 可用空间
- **其他**：Tesseract OCR引擎（用于文字识别功能）

### 🚀 安装步骤

#### 方法一：从源码安装

1. **克隆项目到本地环境**
   ```bash
   git clone https://github.com/YangShengzhou03/LeafView.git
   cd LeafView
   ```

2. **创建虚拟环境（推荐）**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **安装Tesseract OCR（文字识别功能需要）**
   
   **Windows:**
   ```bash
   # 下载并安装Tesseract-OCR
   # https://github.com/UB-Mannheim/tesseract/wiki
   # 确保将Tesseract添加到系统PATH环境变量中
   ```
   
   **macOS:**
   ```bash
   brew install tesseract
   brew install tesseract-lang  # 安装语言包
   ```
   
   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt update
   sudo apt install tesseract-ocr
   sudo apt install libtesseract-dev  # 开发文件
   ```

5. **运行应用程序**
   ```bash
   python App.py
   ```

#### 方法二：使用预编译可执行文件

1. **下载最新版本**
   - 访问 [GitHub Releases](https://github.com/YangShengzhou03/LeafView/releases) 页面
   - 下载对应操作系统的最新版本安装包

2. **安装应用程序**
   - **Windows**: 运行 `.exe` 安装程序，按提示完成安装
   - **macOS**: 打开 `.dmg` 文件，将应用拖拽到应用程序文件夹
   - **Linux**: 解压 `.tar.gz` 文件，运行其中的可执行文件

### 📦 打包为可执行文件

如果您需要自行打包应用程序，可以使用PyInstaller：

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包应用程序
pyinstaller App.spec

# 打包完成后，可执行文件位于dist目录中
```

### 🔧 常见问题解决

1. **导入错误：ModuleNotFoundError**
   ```bash
   # 确保所有依赖已正确安装
   pip install -r requirements.txt --upgrade
   ```

2. **OCR功能无法使用**
   ```bash
   # 确保Tesseract OCR已正确安装并添加到PATH
   # Windows下检查Tesseract安装路径
   where tesseract
   
   # 验证Tesseract是否可用
   tesseract --version
   ```

3. **HEIC/HEIF格式图片无法打开**
   ```bash
   # 确保pillow-heif已正确安装
   pip install pillow-heif --upgrade
   ```

## 📖 使用说明

### 🔑 基本操作

1. **启动程序**
   - 从源码运行：执行 `python App.py`
   - 从可执行文件运行：双击应用程序图标

2. **导入文件夹**
   - 点击界面上的"导入文件夹"按钮
   - 或直接拖拽文件夹到程序窗口
   - 可选择是否包含子文件夹

3. **浏览图片**
   - 在左侧导航栏选择功能模块
   - 在主界面浏览图片
   - 使用缩略图或大图模式查看

### 📝 功能使用

#### 1. **智能整理**

智能整理功能可以帮助您按照多种规则自动整理图片文件。

**操作步骤：**
1. 选择要整理的文件夹
2. 设置分类结构（最多5级分类）
3. 选择文件名结构和分隔符
4. 选择操作类型（移动或复制）
5. 点击"开始整理"按钮执行操作

**分类选项：**
- **时间分类**：年份、月份、日期、星期、时间
- **设备分类**：相机品牌、相机型号
- **位置分类**：拍摄地点（需要GPS信息）
- **自定义分类**：根据用户需求自定义分类规则

**文件名标签：**
- **原文件名**：保留原始文件名
- **时间标签**：年份、月份、日期、星期、时间
- **设备标签**：品牌、型号
- **位置标签**：拍摄地点
- **自定义标签**：用户自定义文本

**操作类型：**
- **移动**：将文件移动到新位置，原位置不再保留
- **复制**：在新位置创建文件副本，原文件保留

#### 2. **去重操作**

去重功能可以帮助您查找并处理重复或相似的图片。

**操作步骤：**
1. 选择要检查重复的文件夹
2. 调整相似度阈值滑块（0-100%）
3. 点击"开始对比"查找重复图片
4. 查看分组结果，选择要处理的图片
5. 选择操作类型（移动或删除）

**相似度级别：**
- **完全一致 (100%)**：文件完全相同
- **高度相似 (75-99%)**：内容几乎相同，可能有轻微压缩差异
- **部分相似 (50-74%)**：内容相似，但有明显差异
- **略有相似 (25-49%)**：只有部分内容相似
- **巨大差异 (0-24%)**：相似度很低

**批量操作：**
- **自动选择**：根据规则自动选择重复图片
- **移动**：将选中的图片移动到指定文件夹
- **删除**：将选中的图片移至回收站

#### 3. **EXIF编辑**

EXIF编辑功能允许您查看和修改图片的元数据信息。

**操作步骤：**
1. 选择要编辑EXIF信息的图片
2. 设置各项EXIF参数
3. 点击"应用"保存更改

**可编辑项目：**
- **星级评分**：1-5星评分
- **相机信息**：品牌、型号、镜头信息
- **拍摄时间**：日期和时间
- **地理位置**：经纬度坐标
- **其他参数**：曝光、光圈、ISO等

**批量处理：**
1. 选择多张图片
2. 设置要修改的EXIF项
3. 点击"批量应用"按钮
4. 确认操作并等待处理完成

#### 4. **文字识别**

文字识别功能可以从图片中提取文字内容，并根据文字内容进行整理。

**操作步骤：**
1. 选择包含文字的图片
2. 点击"识别图片文字"按钮
3. 等待识别完成
4. 查看识别结果
5. 可选择"按文字整理"进行分类

**识别选项：**
- **语言选择**：中文、英文或多语言混合
- **预处理**：自动优化图像以提高识别率
- **批量处理**：一次识别多张图片

**整理选项：**
- **按内容分类**：根据识别的文字内容创建文件夹
- **关键词提取**：自动提取关键词作为分类依据
- **自定义规则**：用户可自定义分类规则

### ⚙️ **设置选项**

通过设置对话框，您可以自定义应用程序的行为：

1. **界面设置**
   - 主题颜色
   - 语言选择
   - 界面缩放

2. **功能设置**
   - 默认操作类型
   - 相似度阈值
   - 文件命名规则

3. **高级设置**
   - 缓存大小
   - 线程数量
   - 日志级别

## 📁 目录结构
```
LeafView/
├── AddFolder.py               # 文件夹导入功能
├── App.py                     # 应用程序入口，实现单例模式
├── App.spec                   # PyInstaller打包配置
├── MainWindow.py              # 主窗口实现，协调各功能模块
├── RemoveDuplication.py       # 去重功能界面
├── RemoveDuplicationThread.py # 去重功能线程处理
├── SmartArrange.py            # 智能整理功能界面
├── SmartArrangeThread.py      # 智能整理功能线程处理
├── TextRecognition.py         # 文字识别功能
├── Ui_MainWindow.py           # UI界面代码（自动生成）
├── Ui_MainWindow.ui           # UI设计文件
├── WriteExif.py               # EXIF编辑功能界面
├── WriteExifThread.py         # EXIF编辑功能线程处理
├── common.py                  # 公共函数和工具
├── config_manager.py          # 配置管理器
├── requirements.txt           # 项目依赖
├── SettingsDialog.py          # 设置对话框
├── UpdateDialog.py            # 更新检查对话框
├── UI_UpdateDialog.py         # UI更新对话框
└── resources/                 # 资源文件夹
    ├── img/                   # 图片资源
    │   ├── icon.ico           # 应用程序图标
    │   ├── page_0/            # 页面0资源
    │   ├── page_1/            # 页面1资源
    │   ├── page_2/            # 页面2资源
    │   ├── page_3/            # 页面3资源
    │   ├── page_4/            # 页面4资源
    │   ├── 头标/              # 标题栏资源
    │   └── 窗口控制/          # 窗口控制按钮资源
    ├── json/                  # JSON配置文件
    │   ├── camera_brand_model.json      # 相机品牌型号数据
    │   ├── camera_lens_mapping.json     # 相机镜头映射数据
    │   ├── lens_model.json             # 镜头型号数据
    │   ├── City_Reverse_Geocode.json    # 城市反向地理编码数据
    │   └── Province_Reverse_Geocode.json # 省份反向地理编码数据
    ├── cv2_date/              # OpenCV相关资源
    │   └── haarcascade_frontalface_alt2.xml  # 人脸检测级联文件
    └── stylesheet/            # 样式表
        ├── author.dialog.setStyleSheet.css  # 作者对话框样式
        └── close_button.setStyleSheet.css    # 关闭按钮样式
```

## 🤝 参与贡献
我们欢迎所有开发者参与项目改进与功能扩展，共同提升系统质量。贡献流程如下：

1. **Fork 仓库**：将项目复制到个人GitHub空间
2. **创建特性分支**：基于main分支创建新分支，命名规范建议使用"feat/功能名称"或"fix/问题描述"
3. **提交规范化代码**：遵循项目代码风格，提交信息使用规范格式（如"feat: 添加图片批量旋转功能"）
4. **推送分支**：将本地分支推送到个人远程仓库
5. **创建 Pull Request**：提交合并请求到原仓库，描述修改内容与目的，等待审核

### 👥 核心贡献者

<div align="center">
  <table>
    <tr>
      <td align="center">
        <a href="https://github.com/YangShengzhou03">
          <img src="https://avatars.githubusercontent.com/u/YangShengzhou03" width="100px;" alt="YangShengzhou03"/><br />
          <sub><b>YangShengzhou03</b></sub>
        </a><br />
        <sub>项目创始人 & 核心开发者</sub>
      </td>
    </tr>
  </table>
</div>

### 💖 特别鸣谢
感谢以下开发者为项目做出的贡献：

- **UI/UX 设计团队** - 提供精美的界面设计和用户体验优化
- **测试团队** - 进行全面的功能测试和性能优化
- **社区贡献者** - 提供宝贵的反馈和建议
- **开源项目** - 感谢以下开源项目为本项目提供支持：
  - [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI框架
  - [Pillow](https://python-pillow.org/) - 图像处理库
  - [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - OCR引擎
  - [PyInstaller](https://www.pyinstaller.org/) - 打包工具

### 🎯 贡献指南

#### 代码规范
- 遵循 PEP 8 Python 代码风格指南
- 使用有意义的变量名和函数名
- 添加适当的注释和文档字符串
- 确保代码通过静态检查工具（如flake8、pylint）
- 函数和类应包含完整的文档字符串，说明参数和返回值

#### 提交信息规范
```
类型(范围): 简短描述

详细描述（可选）

BREAKING CHANGE: 重大变更说明（可选）
```

**类型说明**:
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

**范围说明**:
- `ui`: 用户界面相关更改
- `core`: 核心功能相关更改
- `perf`: 性能优化相关更改
- `docs`: 文档相关更改

#### 开发环境设置
1. 克隆项目到本地
2. 创建并激活虚拟环境
3. 安装开发依赖：`pip install -r requirements.txt`
4. 安装开发工具：`pip install flake8 pylint pytest`
5. 运行代码检查：`flake8 .` 和 `pylint *.py`
6. 运行测试：`pytest tests/`

#### 功能开发流程
1. 在GitHub Issues中创建新的功能请求或确认现有问题
2. 基于main分支创建功能分支：`git checkout -b feat/feature-name`
3. 开发功能并编写测试
4. 确保所有测试通过：`pytest`
5. 提交代码并推送到个人仓库
6. 创建Pull Request并关联对应的Issue

## 📜 开源许可
本项目采用 [MIT License](https://opensource.org/licenses/MIT) 授权。

---

<div align="center">
  <p>
    <strong>🍁 枫叶相册 - 让图片管理更简单 🍁</strong>
  </p>
  <p>
    如果这个项目对您有帮助，请给个 ⭐ Star 支持一下！
  </p>
</div>

```
MIT License

Copyright (c) 2024 YangShengzhou03

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🔄 更新日志

### v1.0.0 (2024-XX-XX)
#### ✨ 新增功能
- 初始版本发布
- 实现基本的图片浏览和管理功能
- 智能整理功能：支持按时间、设备等多维度分类
- 去重功能：基于感知哈希算法检测重复图片
- EXIF编辑功能：查看和修改图片元数据
- 文字识别功能：基于Tesseract OCR引擎
- 单例模式：确保同一时间只有一个应用实例运行

#### 🐛 修复问题
- 修复HEIC/HEIF格式图片无法打开的问题
- 修复大文件处理时的内存泄漏问题
- 修复多线程处理中的竞态条件

#### 🚀 性能优化
- 优化缩略图生成和缓存机制
- 改进大批量文件处理性能
- 减少内存占用，提高运行稳定性

#### 📝 文档更新
- 完善用户手册和使用说明
- 添加开发者贡献指南
- 更新API文档和代码注释

---

<div align="center">
  <sub>Built with ❤️ using Python and PyQt6</sub>
</div>