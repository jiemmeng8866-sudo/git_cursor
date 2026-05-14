"""为 BatchFileMaster 生成丰富的测试文件集，覆盖所有功能场景。"""
import os
import struct
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def touch(path, size_kb=1):
    """创建指定大小的通用文件（填随机字节）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(os.urandom(size_kb * 1024))

def create_jpg(path):
    """创建最小合法 JPEG（2x2 灰）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ihdr = b'\x49\x48\x44\x52' + struct.pack('>II', 2, 2) + b'\x08\x02\x00\x00\x00'
    raw_data = b'\x00\x80\x80\x80\x80\x80\x80\x80\x80\x80\x80'
    import zlib
    compressed = zlib.compress(raw_data)
    ihdr_crc = struct.pack('>I', zlib.crc32(ihdr) & 0xFFFFFFFF)
    idat_crc = struct.pack('>I', zlib.crc32(b'IDAT' + compressed) & 0xFFFFFFFF)
    iend_crc = struct.pack('>I', zlib.crc32(b'IEND') & 0xFFFFFFFF)
    data = b'\x89PNG\r\n\x1a\n' + ihdr + ihdr_crc + b'IDAT' + compressed + idat_crc + b'IEND' + iend_crc
    with open(path, 'wb') as f:
        f.write(data)

def create_mp3_header(path):
    """创建一个极简 MP3 文件头（无实际音频，仅用于测试）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        # MPEG1 Layer3 128kbps 44100Hz 帧头
        f.write(b'\xff\xfb\x90\x00' + b'\x00' * 413)

def main():
    print("=== 开始生成测试文件 ===")

    # ==================== 1. 基础重命名场景 ====================
    # ---- 相机照片（序号+前后缀测试） ----
    for i in range(1, 31):
        create_jpg(os.path.join(BASE_DIR, f'DSC_{i:04d}.jpg'))          # Nikon 风格
    for i in range(1, 21):
        create_jpg(os.path.join(BASE_DIR, f'IMG_{20240501 + i:08d}.jpg'))  # 手机风格

    # ---- 截图文件（前缀替换测试） ----
    for i in range(1, 16):
        touch(os.path.join(BASE_DIR, f'Screenshot_{2024 + (i%3)}_{(i%12)+1:02d}_{i:02d}.png'), size_kb=2)

    # ---- 不同扩展名（扩展名覆写测试） ----
    extensions = ['txt', 'md', 'csv', 'json', 'xml', 'html', 'css', 'js', 'py', 'log',
                  'docx', 'xlsx', 'pptx', 'pdf', 'zip', 'rar', '7z',
                  'bmp', 'gif', 'webp', 'tiff', 'svg', 'ico',
                  'wav', 'flac', 'ogg', 'm4a', 'aac', 'wma',
                  'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm']
    for i, ext in enumerate(extensions):
        touch(os.path.join(BASE_DIR, f'sample_file_{i+1:02d}.{ext}'), size_kb=3)

    # ---- 文件名包含特定文字（替换功能测试） ----
    for i in range(1, 11):
        touch(os.path.join(BASE_DIR, f'old_project_v{i}.txt'), size_kb=1)
    for i in range(1, 11):
        touch(os.path.join(BASE_DIR, f'draft_chapter_{i}.md'), size_kb=2)

    # ---- 前后缀测试 ----
    for i in range(1, 11):
        touch(os.path.join(BASE_DIR, f'chapter_{i}.txt'), size_kb=1)

    # ---- 大小写测试 ----
    case_names = [
        'UPPERCASE_FILE.TXT', 'lowercase_file.txt', 'Mixed_Case_File.TXT',
        'CamelCaseFile.js', 'snake_case_variable.py', 'kebab-case-file.css',
        'ALL_CAPS_WITH_UNDERSCORE.XML', 'random_MIXED_Case.TxT'
    ]
    for name in case_names:
        touch(os.path.join(BASE_DIR, name), size_kb=1)

    # ---- 中文文件名 ----
    chinese_names = [
        '工作报告_2024年度总结.docx', '财务报表_第一季度.xlsx', '会议纪要_20240520.txt',
        '产品设计稿_v3.png', '用户反馈汇总.csv', '技术文档-API接口.md',
        '个人简历-张三.pdf', '旅游照片_大理洱海.png', '学习笔记_Python进阶.py',
        '项目计划甘特图.xlsx', '需求规格说明书_v2.1.docx', '测试报告_单元测试.txt',
    ]
    for name in chinese_names:
        if name.endswith(('.png', '.jpg')):
            create_jpg(os.path.join(BASE_DIR, name.replace('.png', '.jpg') if name.endswith('.png') else name))
        else:
            touch(os.path.join(BASE_DIR, name), size_kb=2)

    # ---- 文件名含空格、括号、特殊符号 ----
    special_names = [
        'My Document (final version).docx',
        '[Backup] old_config.json',
        'photo - copy (3).jpg',
        'report [2024-Q4] final.pdf',
        'untitled (1).txt',
        'data_v1.0_release.zip',
        'budget_$2024$_估算.xlsx',
        'image #1 - edited.png',
        'song_title_(remix).mp3',
        'archive ~ backup.tar.gz',
    ]
    for name in special_names:
        if name.endswith(('.jpg', '.png')):
            create_jpg(os.path.join(BASE_DIR, name))
        elif name.endswith('.mp3'):
            create_mp3_header(os.path.join(BASE_DIR, name))
        else:
            touch(os.path.join(BASE_DIR, name), size_kb=2)

    # ---- 同名冲突测试（不同目录下同名文件） ----
    for d in ['project_a', 'project_b', 'project_c']:
        for i in range(1, 6):
            touch(os.path.join(BASE_DIR, d, f'config.json'), size_kb=1)
            touch(os.path.join(BASE_DIR, d, f'readme.md'), size_kb=1)
            touch(os.path.join(BASE_DIR, d, f'report_{i}.txt'), size_kb=1)

    # ---- 长文件名 ----
    long_prefix = 'a' * 50
    touch(os.path.join(BASE_DIR, f'{long_prefix}_very_long_filename_test.txt'), size_kb=1)
    touch(os.path.join(BASE_DIR, f'very_long_file_name_with_many_words_in_it_for_testing_truncation_{"x"*30}.txt'), size_kb=1)

    # ---- 空文件名/只有扩展名 ----
    touch(os.path.join(BASE_DIR, '.gitignore'), size_kb=1)
    touch(os.path.join(BASE_DIR, '.env'), size_kb=1)
    touch(os.path.join(BASE_DIR, '.hidden_config'), size_kb=1)

    # ==================== 2. 精确截取测试场景 ====================
    # 固定前缀需要裁剪
    for i in range(1, 16):
        touch(os.path.join(BASE_DIR, f'PREFIX_REMOVE_ME_file_{i:03d}.txt'), size_kb=1)
    # 固定后缀需要裁剪
    for i in range(1, 16):
        touch(os.path.join(BASE_DIR, f'file_{i:03d}_SUFFIX_DELETE.txt'), size_kb=1)

    # ==================== 3. 音视频场景 ====================
    audio_dir = os.path.join(BASE_DIR, 'music_library')
    for artist in ['Artist_A', 'Artist_B', 'Artist_C']:
        for track in range(1, 6):
            create_mp3_header(os.path.join(audio_dir, artist, f'track_{track}.mp3'))
    # 视频目录
    video_dir = os.path.join(BASE_DIR, 'video_archive')
    for season in range(1, 4):
        for ep in range(1, 6):
            touch(os.path.join(video_dir, f'Season_{season}', f'S{season:02d}E{ep:02d}.mp4'), size_kb=50)

    # ==================== 4. 多层嵌套目录（去套娃测试） ====================
    # 已有的 flatten_src，我再充实几层
    deep_dir = os.path.join(BASE_DIR, 'deep_nest_test')
    path = deep_dir
    for level in range(1, 6):
        path = os.path.join(path, f'level_{level}')
        for i in range(1, 4):
            touch(os.path.join(path, f'nested_file_L{level}_{i}.txt'), size_kb=1)

    # 更复杂的嵌套：每个目录下都有文件
    complex_nest = os.path.join(BASE_DIR, 'complex_nest')
    for a in ['category_a', 'category_b', 'category_c']:
        for b in ['sub_1', 'sub_2']:
            for c in ['deep_1', 'deep_2']:
                for i in range(1, 4):
                    touch(os.path.join(complex_nest, a, b, c, f'file_{a}_{b}_{c}_{i}.txt'), size_kb=1)
        # 每层也有直接文件
        touch(os.path.join(complex_nest, a, f'{a}_root.txt'), size_kb=1)
        for b in ['sub_1', 'sub_2']:
            touch(os.path.join(complex_nest, a, b, f'{a}_{b}_dir_file.txt'), size_kb=1)

    # ==================== 5. 批量大批量序号测试 ====================
    batch_dir = os.path.join(BASE_DIR, 'batch_rename')
    for i in range(1, 101):
        touch(os.path.join(batch_dir, f'raw_data_{i:04d}.csv'), size_kb=1)
    for i in range(1, 51):
        create_jpg(os.path.join(batch_dir, f'photo_{i:05d}.jpg'))

    # ==================== 6. 子文件夹结构（保留已有 subfolder_a/b） ====================
    # subfolder_c: 混合文件类型
    for i in range(1, 11):
        touch(os.path.join(BASE_DIR, 'subfolder_c', f'doc_{i}.docx'), size_kb=2)
        touch(os.path.join(BASE_DIR, 'subfolder_c', f'sheet_{i}.xlsx'), size_kb=2)
    # subfolder_d/sub: 两层
    for i in range(1, 6):
        touch(os.path.join(BASE_DIR, 'subfolder_d', 'inner', f'internal_{i}.txt'), size_kb=1)
        touch(os.path.join(BASE_DIR, 'subfolder_d', f'outer_{i}.txt'), size_kb=1)

    # ==================== 7. 模拟真实场景 ====================
    # 照片导入（相机+手机混合）
    for cam in ['A7M3', 'R5', 'XT5']:
        for i in range(1, 9):
            create_jpg(os.path.join(BASE_DIR, f'{cam}_{i:04d}.jpg'))

    # 文档归档
    for year in [2022, 2023, 2024]:
        for month in range(1, 13):
            touch(os.path.join(BASE_DIR, f'report_{year}_{month:02d}.pdf'), size_kb=3)

    # 项目文件
    for proj in ['alpha', 'beta', 'gamma']:
        touch(os.path.join(BASE_DIR, f'project_{proj}_spec.md'), size_kb=2)
        touch(os.path.join(BASE_DIR, f'project_{proj}_budget.xlsx'), size_kb=2)
        touch(os.path.join(BASE_DIR, f'project_{proj}_timeline.pdf'), size_kb=2)
        touch(os.path.join(BASE_DIR, f'project_{proj}_assets.zip'), size_kb=10)

    print("=== 全部测试文件生成完毕！ ===")

    # 统计
    file_count = 0
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            if f != 'generate_test_files.py':
                file_count += 1
    print(f"总计生成 {file_count} 个测试文件（不含本脚本）")


if __name__ == '__main__':
    main()
