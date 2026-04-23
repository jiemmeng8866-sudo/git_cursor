#!/usr/bin/env python3
"""
Token 管理工具
用于估算和优化 novel-generator 技能的 token 使用
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

def count_tokens_approx(text: str) -> int:
    """
    粗略估算文本的 token 数量
    中文：约 1.5 token/字符
    英文：约 0.75 token/单词
    """
    # 中文字符数
    chinese_chars = len(re.findall(r'[一-鿿]', text))

    # 英文单词数（简单估算）
    english_words = len(re.findall(r'[a-zA-Z]+', text))

    # 标点和其他字符
    other_chars = len(text) - chinese_chars

    # 估算 token 数
    tokens = chinese_chars * 1.5 + english_words * 0.75 + other_chars * 0.3
    return int(tokens)

def get_chapter_files(directory: str) -> List[str]:
    """获取目录中的所有章节文件"""
    chapter_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.md') and ('chapter' in file.lower() or '第' in file):
                chapter_files.append(os.path.join(root, file))

    # 按修改时间排序（最近修改的在前）
    chapter_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return chapter_files

def estimate_directory_tokens(directory: str, limit: int = None) -> Dict:
    """估算目录中章节文件的 token 总数"""
    chapter_files = get_chapter_files(directory)

    if limit and limit > 0:
        chapter_files = chapter_files[:limit]

    total_tokens = 0
    file_tokens = []

    for file_path in chapter_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tokens = count_tokens_approx(content)
            total_tokens += tokens
            file_tokens.append({
                'file': os.path.basename(file_path),
                'tokens': tokens,
                'size_kb': os.path.getsize(file_path) / 1024
            })
        except Exception as e:
            print(f"警告：无法读取文件 {file_path}: {e}")

    return {
        'total_tokens': total_tokens,
        'file_count': len(chapter_files),
        'files': file_tokens,
        'average_tokens': total_tokens // len(file_tokens) if file_tokens else 0
    }

def generate_chapter_summary(file_path: str, max_words: int = 200) -> str:
    """生成章节摘要"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取标题（第一行）
        lines = content.split('\n')
        title = lines[0].strip('# ') if lines else os.path.basename(file_path)

        # 寻找概要行
        summary = ""
        for line in lines:
            if '本章概要' in line or '核心事件' in line or '摘要' in line:
                # 清理标记
                clean_line = re.sub(r'> \*\*.*?\*\*：', '', line).strip('> ')
                if clean_line:
                    summary = clean_line
                    break

        # 如果没有找到概要，生成简单摘要
        if not summary:
            # 取前3个段落
            paragraphs = content.split('\n\n')
            text_content = []
            for para in paragraphs:
                if not para.strip().startswith('#') and not para.strip().startswith('>'):
                    text_content.append(para.strip())
                if len(text_content) >= 3:
                    break

            summary = ' '.join(text_content)[:max_words * 3] + "..."

        # 限制摘要长度
        if len(summary) > max_words * 3:
            summary = summary[:max_words * 3] + "..."

        return f"《{title}》\n摘要：{summary}"

    except Exception as e:
        return f"无法生成摘要：{str(e)}"

def create_reference_summary(directory: str, current_chapter: int, limit: int = 3) -> str:
    """创建历史章节引用摘要"""
    chapter_files = get_chapter_files(directory)

    # 过滤出当前章节之前的章节
    previous_chapters = []
    for file_path in chapter_files:
        filename = os.path.basename(file_path)

        # 尝试提取章节号
        chapter_num = None
        match = re.search(r'第(\d+)章', filename)
        if match:
            chapter_num = int(match.group(1))
        else:
            match = re.search(r'chapter[_\s]*(\d+)', filename, re.IGNORECASE)
            if match:
                chapter_num = int(match.group(1))

        if chapter_num and chapter_num < current_chapter:
            previous_chapters.append((chapter_num, file_path))

    # 按章节号排序
    previous_chapters.sort(key=lambda x: x[0], reverse=True)

    # 限制数量
    if limit and limit > 0:
        previous_chapters = previous_chapters[:limit]

    # 生成摘要
    references = []
    for chapter_num, file_path in previous_chapters:
        summary = generate_chapter_summary(file_path)
        references.append(f"## 第{chapter_num}章\n{summary}\n")

    return "\n".join(references)

def main():
    parser = argparse.ArgumentParser(description='Token 管理工具')
    parser.add_argument('--dir', default='./output', help='章节目录路径')
    parser.add_argument('--estimate', action='store_true', help='估算token使用')
    parser.add_argument('--limit', type=int, default=5, help='估算时限制章节数量')
    parser.add_argument('--summary', type=int, help='生成章节摘要，指定章节号')
    parser.add_argument('--references', type=int, help='生成历史章节引用摘要，指定当前章节号')
    parser.add_argument('--ref-limit', type=int, default=3, help='历史章节引用限制')

    args = parser.parse_args()

    # 确保目录存在
    directory = args.dir
    if not os.path.exists(directory):
        print(f"错误：目录不存在 {directory}")
        sys.exit(1)

    if args.estimate:
        print(f"估算目录: {directory}")
        print(f"限制章节数: {args.limit if args.limit else '无限制'}")
        print("-" * 50)

        result = estimate_directory_tokens(directory, args.limit)

        print(f"总章节数: {result['file_count']}")
        print(f"估算总token: {result['total_tokens']:,}")
        print(f"平均每章token: {result['average_tokens']:,}")
        print(f"模型限制: 131,072 tokens")
        print(f"剩余空间: {131072 - result['total_tokens']:,} tokens")
        print()

        print("章节详情:")
        for file_info in result['files'][:10]:  # 只显示前10个
            print(f"  {file_info['file']}: {file_info['tokens']:,} tokens ({file_info['size_kb']:.1f} KB)")

        if result['total_tokens'] > 131072:
            print("\n⚠️  警告：超过模型token限制！")
            print("建议:")
            print("  1. 使用 --references 生成摘要而非全文")
            print("  2. 限制历史章节引用数量")
            print("  3. 清理对话历史")

    elif args.summary:
        # 查找指定章节的文件
        chapter_files = get_chapter_files(directory)
        target_file = None

        for file_path in chapter_files:
            filename = os.path.basename(file_path)
            if f"第{args.summary}章" in filename or f"chapter_{args.summary:03d}" in filename:
                target_file = file_path
                break

        if target_file:
            summary = generate_chapter_summary(target_file)
            print(f"章节摘要 (第{args.summary}章):")
            print("-" * 50)
            print(summary)
        else:
            print(f"未找到第{args.summary}章")

    elif args.references:
        summary = create_reference_summary(directory, args.references, args.ref_limit)
        print(f"历史章节引用摘要 (当前第{args.references}章，限制{args.ref_limit}章):")
        print("-" * 50)
        print(summary)

        # 估算token
        tokens = count_tokens_approx(summary)
        print(f"\n摘要token数: {tokens:,}")
        print(f"节省空间: 相比全文引用节省约 {tokens/1000:.1f}K tokens")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()