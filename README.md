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
      <img src="https://img.shields.io/badge/Pillow-10.3.0-orange?style=for-the-badge&logo=pypi" alt="Pillow Version">
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

## ✨ 项目概述
枫叶相册 (LeafView) 是一款基于 **Python** 和 **PyQt6** 构建的**开源图片与媒体管理工具**，为用户提供直观、高效的图片浏览和管理体验。系统采用单例模式设计，支持多种图片格式，并提供智能整理、去重、EXIF信息编辑等功能。

**💡 适用场景**
- 个人图片库管理
- 摄影爱好者的照片整理
- 图片批量处理与重命名
- 图片元数据编辑
- 重复图片检测与清理

## 🚀 技术架构

### 🔧 技术栈
| 技术                | 描述                                                         |
|---------------------|--------------------------------------------------------------|
| **Python 3.11**     | 主要编程语言，提供强大的后端处理能力                         |
| **PyQt6**           | 跨平台GUI框架，用于构建直观、美观的用户界面                  |
| **Pillow**          | Python图像处理库，支持各种图片格式的读写和处理              |
| **pillow-heif**     | HEIF格式支持，扩展Pillow对HEIC等格式的兼容性                 |
| **piexif**          | 用于读取和写入EXIF元数据信息                                |
| **pytesseract**     | OCR文字识别引擎，提供图片文字识别功能                        |
| **requests**        | HTTP客户端库，用于检查更新和网络请求                        |
| **send2trash**      | 安全删除文件到回收站的工具                                   |

## 🌟 核心功能

### 📷 **图片管理**
- 支持多种图片格式：JPG、PNG、HEIC、TIFF、BMP、WEBP、GIF等
- 文件夹导入与浏览，支持拖拽操作
- 缩略图预览与大图查看

### 🧹 **智能整理**
- 按时间分类：年份、月份、日期、星期等
- 自定义文件夹结构
- 批量重命名，支持多种命名规则和分隔符
- 移动或复制到目标目录

### 🔍 **去重功能**
- 检测重复图片
- 智能对比相似度
- 一键删除重复图片

### 📝 **EXIF编辑**
- 查看和编辑图片元数据
- 修改拍摄日期、设备信息等
- 批量处理多张图片

### 🔤 **文字识别**
- 从图片中提取文字
- 支持多语言识别
- 复制识别结果

## 💻 安装部署

### 🔧 环境准备
- Python 3.8 及以上版本
- PyQt6 库
- 其他依赖库（详见requirements.txt）

### 🚀 安装步骤
1. 克隆项目到本地环境
   ```bash
   git clone https://github.com/YangShengzhou03/LeafView.git
   cd LeafView
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 运行应用程序
   ```bash
   python App.py
   ```

### 📦 打包为可执行文件
项目包含App.spec文件，可使用PyInstaller打包为独立可执行文件：
```bash
pyinstaller App.spec
```

## 📖 使用说明

### 🔑 基本操作
1. **启动程序**：运行App.py或双击打包后的可执行文件
2. **导入文件夹**：点击界面上的导入按钮或直接拖拽文件夹到程序窗口
3. **浏览图片**：在左侧导航栏选择功能模块，在主界面浏览图片

### 📝 功能使用

1. **智能整理**：
   - 选择要整理的文件夹
   - 设置分类结构（年份、月份等）
   - 选择文件名结构和分隔符
   - 点击"开始整理"按钮执行操作

2. **去重操作**：
   - 选择要检查重复的文件夹
   - 设置相似度阈值
   - 点击"开始对比"查找重复图片
   - 选择要删除的重复图片

3. **EXIF编辑**：
   - 选择要编辑EXIF信息的图片
   - 输入新的EXIF信息
   - 点击"应用"保存更改

4. **文字识别**：
   - 选择包含文字的图片
   - 点击"开始识别"提取文字
   - 复制或保存识别结果

## 📁 目录结构
```
LeafView/
├── AddFolder.py               # 文件夹导入功能
├── App.py                     # 应用程序入口
├── App.spec                   # PyInstaller打包配置
├── MainWindow.py              # 主窗口实现
├── RemoveDuplication.py       # 去重功能界面
├── RemoveDuplicationThread.py # 去重功能线程
├── SmartArrange.py            # 智能整理功能界面
├── SmartArrangeThread.py      # 智能整理功能线程
├── TextRecognition.py         # 文字识别功能
├── Ui_MainWindow.py           # UI界面代码（自动生成）
├── Ui_MainWindow.ui           # UI设计文件
├── WriteExif.py               # EXIF编辑功能界面
├── WriteExifThread.py         # EXIF编辑功能线程
├── common.py                  # 公共函数和工具
├── requirements.txt           # 项目依赖
└── resources/                 # 资源文件夹
    ├── img/                   # 图片资源
    ├── json/                  # JSON配置文件
    ├── cv2_date/              # OpenCV相关资源
    └── stylesheet/            # 样式表
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

### 🎯 贡献指南

#### 代码规范
- 遵循 PEP 8 Python 代码风格指南
- 使用有意义的变量名和函数名
- 添加适当的注释和文档字符串
- 确保代码通过静态检查工具（如flake8、pylint）

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

<div align="center">
  <sub>Built with ❤️ using Python and PyQt6</sub>
</div>