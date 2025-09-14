# LeafView 枫叶相册

LeafView是一个功能丰富的图像处理与管理工具，专注于提供便捷的图片浏览、分类整理、EXIF元数据编辑和文字识别等功能。

## 功能特性

### 1. 图片管理
- 支持添加多个文件夹进行图片管理
- 支持包含子文件夹的递归扫描
- 拖放功能添加文件夹
- 媒体文件自动检测

### 2. 智能分类整理
- 按时间（年份、月份、日、星期、时间）分类
- 按位置、品牌等标签分类
- 支持复制或移动操作

### 3. 去重功能
- 基于相似度的图片分组
- 缩略图预览
- 自动选择保留最大文件
- 支持移动/删除选中图片
- 多级相似度阈值控制（1-4级）

### 4. EXIF元数据编辑
- 星级评分系统
- 相机品牌/型号选择
- 拍摄时间设置
- 位置信息获取（基于IP或地址）
- 批量处理文件夹中的图片文件
- 自动标记功能（通过API分析图像内容）

### 5. 文字识别
- 批量识别图片中的文字（支持中英文）
- 基于识别结果自动整理图片
- 识别进度实时显示

## 安装指南

### 系统要求
- Windows、macOS或Linux操作系统
- Python 3.8或更高版本

### 安装步骤

1. 克隆或下载项目代码

```bash
git clone https://your-repository-url/LeafView.git
cd LeafView
```

2. 安装依赖项

```bash
pip install -r requirements.txt
```

3. 安装Tesseract OCR引擎（用于文字识别功能）

- **Windows**: 从[GitHub](https://github.com/UB-Mannheim/tesseract/wiki)下载安装包
- **macOS**: 使用Homebrew安装 `brew install tesseract tesseract-lang`
- **Linux**: 使用包管理器安装 `sudo apt install tesseract-ocr tesseract-ocr-chi-sim`

4. 配置环境变量（用于API访问）

```bash
# Windows PowerShell
$env:STONEDT_SECRET_ID="your_secret_id"
$env:STONEDT_SECRET_KEY="your_secret_key"
$env:AMAP_API_KEY="your_amap_api_key"

# macOS/Linux
# 在.bashrc或.zshrc中添加
# export STONEDT_SECRET_ID="your_secret_id"
# export STONEDT_SECRET_KEY="your_secret_key"
# export AMAP_API_KEY="your_amap_api_key"
```

## 使用说明

### 启动应用

```bash
python App.py
```

### 基本操作

1. **添加文件夹**
   - 点击"添加文件夹"按钮
   - 选择要管理的文件夹
   - 可以选择是否包含子文件夹

2. **智能分类**
   - 切换到"分类整理"选项卡
   - 选择分类维度（年份、月份等）
   - 选择目标文件夹
   - 点击"开始分类"按钮

3. **图片去重**
   - 切换到"图片去重"选项卡
   - 选择相似度阈值
   - 点击"开始扫描"按钮
   - 可以手动选择或自动选择保留的图片

4. **编辑EXIF信息**
   - 切换到"EXIF编辑"选项卡
   - 填写或选择要修改的信息
   - 点击"开始"按钮批量处理

5. **文字识别与整理**
   - 切换到"文字识别"选项卡
   - 点击"识别图片文字"按钮开始识别
   - 识别完成后，点击"按文字整理"按钮整理图片

## 注意事项

1. 使用自动标记和位置信息功能需要配置相应的API密钥
2. 处理大量图片时可能需要较长时间，请耐心等待
3. 进行文件移动或删除操作前，请确保已备份重要数据
4. 文字识别准确率受图片质量、光照条件等因素影响

## 许可证

[MIT License](LICENSE)

## 更新日志

### 最新版本
- 修复了API密钥硬编码问题
- 实现了完整的文字识别功能
- 改进了代码结构和错误处理
- 添加了详细的使用文档

## 开发者信息

如有问题或建议，请联系开发者：[作者信息]