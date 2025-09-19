import os
from mutagen.mp4 import MP4
from datetime import datetime


def convert_to_mp4_date(date_str):
    """将日期字符串转换为MP4格式的日期时间"""
    try:
        # 尝试解析常见日期格式
        date_formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S', '%Y/%m/%d']
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                continue
        # 如果所有格式都失败，返回原始字符串
        return date_str
    except Exception as e:
        print(f"日期格式转换错误: {e}")
        return date_str


def write_video_metadata(file_path, metadata):
    """
    为MP4/MOV文件写入扩展元数据属性，包括GPS和拍摄时间等

    参数:
        file_path: 视频文件路径
        metadata: 包含要写入的属性字典
    """
    try:
        # 打开视频文件
        video = MP4(file_path)

        # 定义扩展的元数据映射关系（MP4标签 -> 自定义标签）
        tag_mapping = {
            # 基本信息
            'title': '\xa9nam',  # 标题
            'rating': 'rtng',  # 分级
            'comment': '\xa9cmt',  # 备注
            'subtitle': '\xa9des',  # 副标题
            'tag': '\xa9gen',  # 标记
            'description': 'desc',  # 详细描述
            'keywords': 'keyw',  # 关键词

            # 日期时间信息
            'creation_date': 'cday',  # 创建日期
            'modification_date': 'mdat',  # 修改日期
            'shooting_date': 'shoo',  # 拍摄日期
            'release_date': '\xa9dat',  # 发布日期

            # 人员信息
            'director': '\xa9dir',  # 导演
            'producer': 'prod',  # 制作人
            'creator': '\xa9wrt',  # 创作人
            'publisher': '\xa9pub',  # 发布者
            'provider': 'prov',  # 内容提供商
            'performer': '\xa9ART',  # 表演者/演员
            'composer': '\xa9wrt',  # 作曲者
            'author': '\xa9aut',  # 作者
            'copyright_holder': '\xa9cpy',  # 版权持有者

            # 技术信息
            'encoder': '\xa9enc',  # 编码器
            'language': '\xa9lan',  # 语言
            'genre': '\xa9gen',  # 类型
            'duration': 'dur ',  # 时长(秒)

            # GPS信息
            'gps_latitude': 'gpsLat',  # 纬度
            'gps_longitude': 'gpsLon',  # 经度
            'gps_altitude': 'gpsAlt',  # 海拔
            'gps_speed': 'gpsSpd',  # 速度
            'gps_timestamp': 'gpsTme',  # GPS时间戳
            'location': 'loc ',  # 位置描述

            # 版权与法律信息
            'copyright': '\xa9cpy',  # 版权声明
            'license': 'lics',  # 许可证
            'rights': 'rght',  # 权利信息

            # 内容相关
            'album': '\xa9alb',  # 专辑/系列
            'episode': 'epis',  # 集数
            'season': 'seas',  # 季数
            'track_number': 'trkn',  # 轨道号
            'network': 'netw',  # 网络/频道
            'studio': 'stud',  # 工作室
        }

        # 写入元数据
        for key, value in metadata.items():
            if key in tag_mapping and value:
                mp4_tag = tag_mapping[key]

                # 特殊处理不同类型的标签
                if key == 'rating':
                    # 分级是数值类型
                    video[mp4_tag] = [int(value)]
                elif key in ['shooting_date', 'creation_date', 'modification_date', 'release_date', 'gps_timestamp']:
                    # 日期时间格式转换
                    video[mp4_tag] = convert_to_mp4_date(value)
                elif key in ['gps_latitude', 'gps_longitude', 'gps_altitude', 'gps_speed']:
                    # GPS坐标处理为浮点数
                    try:
                        video[mp4_tag] = [float(value)]
                    except ValueError:
                        print(f"警告: {key} 的值 {value} 不是有效的数值，将以字符串形式存储")
                        video[mp4_tag] = value
                elif key == 'track_number':
                    # 轨道号格式为 (当前, 总数)
                    if isinstance(value, tuple) and len(value) == 2:
                        video[mp4_tag] = [(value[0], value[1])]
                    else:
                        print(f"警告: track_number 格式应为元组 (当前, 总数)，将跳过此标签")
                else:
                    # 普通文本标签
                    video[mp4_tag] = value

        # 保存修改
        video.save()
        print(f"成功写入元数据: {os.path.basename(file_path)}")
        return True

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {str(e)}")
    return False


def process_video_folder(folder_path, default_metadata):
    """
    处理文件夹中的所有MP4和MOV文件

    参数:
        folder_path: 文件夹路径
        default_metadata: 默认元数据字典
    """
    if not os.path.exists(folder_path):
        print(f"错误: 文件夹 {folder_path} 不存在")
        return

    # 获取文件夹中所有MP4和MOV文件
    video_extensions = ('.mp4', '.mov', '.MP4', '.MOV')
    video_files = [
        f for f in os.listdir(folder_path)
        if f.endswith(video_extensions)
    ]

    if not video_files:
        print(f"在 {folder_path} 中未找到MP4/MOV文件")
        return

    print(f"找到 {len(video_files)} 个视频文件，开始处理...")

    # 处理每个视频文件
    for file_name in video_files:
        file_path = os.path.join(folder_path, file_name)
        # 可以根据文件名自定义元数据，这里使用默认元数据
        write_video_metadata(file_path, default_metadata)


if __name__ == "__main__":
    # 视频文件所在文件夹
    video_folder = r"D:\待分类\视频"

    # 要写入的默认元数据（包含GPS和拍摄时间等扩展属性）
    default_metadata = {
        # 基本信息
        'title': '视频标题',
        'subtitle': '视频副标题',
        'description': '这是一段详细的视频描述信息',
        'comment': '这是一段视频备注',
        'tag': '视频标记',
        'keywords': '关键词1,关键词2,关键词3',
        'rating': '4',  # 分级，1-5的数值

        # 日期时间信息
        'creation_date': '2023-01-01 12:00:00',
        'modification_date': '2023-01-02 15:30:00',
        'shooting_date': '2023-01-01 10:15:30',
        'release_date': '2023-01-10',

        # 人员信息
        'director': '张导演',
        'producer': '李制片',
        'creator': '王创作',
        'publisher': '某某发行公司',
        'provider': '内容提供商名称',
        'performer': '主要演员A,主要演员B',
        'composer': '赵作曲',
        'author': '刘作者',
        'copyright_holder': '版权所有公司',

        # 技术信息
        'encoder': 'H.264编码器 v1.0',
        'language': 'zh-CN',
        'genre': '纪录片',
        'duration': '1200',  # 时长(秒)

        # GPS信息
        'gps_latitude': '39.9087',  # 纬度（例如：北京纬度）
        'gps_longitude': '116.3975',  # 经度（例如：北京经度）
        'gps_altitude': '43.5',  # 海拔(米)
        'gps_speed': '0.0',  # 速度(米/秒)
        'gps_timestamp': '2023-01-01 10:15:30',
        'location': '北京市中心',

        # 版权与法律信息
        'copyright': '© 2023 版权所有',
        'license': '保留所有权利',
        'rights': '未经许可不得转载',

        # 内容相关
        'album': '城市风光系列',
        'episode': '3',
        'season': '1',
        'track_number': (3, 10),  # (当前轨道号, 总轨道数)
        'network': '城市电视台',
        'studio': '光影工作室'
    }

    # 处理文件夹中的视频文件
    process_video_folder(video_folder, default_metadata)
    print("处理完成")
