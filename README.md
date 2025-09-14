# LeafView - 智能媒体管理工具

LeafView是一个基于Python和PyQt6开发的智能媒体管理工具，用于高效整理照片和视频文件。

## 功能特点

- **智能图像分类**：根据EXIF元数据自动分类整理照片
- **批量重命名**：支持自定义规则的批量重命名功能
- **重复文件检测**：智能识别重复的图片和视频文件
- **EXIF元数据编辑**：查看和编辑照片的EXIF信息
- **直观的用户界面**：简洁易用的现代化界面设计

## 项目结构

LeafView采用现代化的Python项目结构，遵循MVC（模型-视图-控制器）架构模式：

```
LeafView/
├── src/                    # 源代码目录
│   └── leafview/           # 主包目录
│       ├── __init__.py     # 包初始化文件
│       ├── main.py         # 应用程序入口点
│       ├── models/         # 数据模型
│       │   ├── __init__.py
│       │   └── media_item.py  # 媒体项模型
│       ├── views/          # 视图组件
│       │   ├── __init__.py
│       │   └── main_window.py  # 主窗口视图
│       ├── controllers/    # 控制器
│       │   ├── __init__.py
│       │   ├── media_controller.py  # 媒体控制器
│       │   └── classification_controller.py  # 分类控制器
│       ├── threads/        # 后台线程
│       │   ├── __init__.py
│       │   └── media_thread.py  # 媒体处理线程
│       └── utils/          # 工具模块
│           ├── __init__.py
│           ├── config.py    # 配置管理
│           └── logger.py    # 日志记录
├── resources/              # 资源文件
│   ├── img/               # 图片资源
│   ├── json/              # JSON数据文件
│   └── stylesheet/        # 样式表文件
├── pyproject.toml         # 项目配置文件
├── requirements.txt       # 依赖列表
└── README.md             # 项目说明文档
```

## 安装指南

### 环境要求

- Python 3.8+
- PyQt6
- Pillow
- OpenCV
- 其他依赖（见requirements.txt）

### 安装步骤

1. 克隆或下载项目代码

```bash
git clone https://github.com/yourusername/LeafView.git
cd LeafView
```

2. 创建并激活虚拟环境（推荐）

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 运行应用程序

```bash
python -m src.leafview.main
```

## 使用教程

### 基本操作

1. **选择文件夹**：点击主界面的"选择文件夹"按钮，选择包含媒体文件的目录
2. **浏览媒体**：程序会自动加载并显示所选目录中的图片和视频
3. **分类整理**：点击"分类"按钮，根据日期自动整理文件
4. **查看详情**：点击媒体项可以查看详细信息，包括EXIF数据

### 高级功能

1. **自定义分类规则**：在设置中可以自定义分类规则，如按年月、按事件等
2. **批量重命名**：选择多个文件，使用批量重命名功能
3. **重复文件检测**：使用重复文件检测功能找出并处理重复的媒体文件

## 开发指南

### 项目架构

LeafView采用MVC架构模式，主要组件包括：

- **模型（Models）**：定义数据结构和业务逻辑，如MediaItem类
- **视图（Views）**：负责用户界面展示，如MainWindow类
- **控制器（Controllers）**：协调模型和视图，处理用户交互
- **线程（Threads）**：处理耗时操作，避免阻塞UI
- **工具（Utils）**：提供通用功能，如配置管理、日志记录等

### 添加新功能

1. 在相应的模块中添加代码
2. 遵循现有的代码风格和架构模式
3. 添加适当的测试和文档
4. 更新requirements.txt（如果添加了新的依赖）

### 代码风格

- 遵循PEP 8 Python代码风格指南
- 使用类型提示提高代码可读性
- 添加适当的文档字符串
- 使用日志记录代替print语句

## 安全与隐私

- LeafView完全在本地运行，不会上传任何用户数据
- 所有处理都在本地完成，保护用户隐私
- 不会收集或传输任何个人信息

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来帮助改进LeafView！

## 联系方式

如有问题或建议，请通过以下方式联系：

- 邮箱：contact@example.com
- GitHub Issues：https://github.com/yourusername/LeafView/issues