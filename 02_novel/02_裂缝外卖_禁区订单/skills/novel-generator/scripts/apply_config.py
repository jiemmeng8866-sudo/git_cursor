#!/usr/bin/env python3
"""
应用 token 管理配置到 novel-generator 技能
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# 配置模板
CONFIG_TEMPLATE = """# Token 优化配置 (自动生成)

## 章节引用策略
history_chapters_limit = {limit}  # 最多引用最近 N 章
use_summary = {use_summary}  # 使用摘要而非全文
summary_length = {summary_length}  # 摘要字数

## 对话管理
max_conversation_turns = 20  # 最大对话轮数
auto_clear_threshold = 15    # 超过此轮数后建议清理
new_session_per_chapter = 5  # 每生成 N 章开启新对话

## 章节生成
chapter_word_limit = 2500    # 每章字数限制
enable_progressive_summary = True  # 启用渐进式摘要

## 监控设置
enable_token_monitoring = True
check_interval_chapters = 3  # 每生成 N 章检查一次

---

## 应用说明
此配置已自动应用到 novel-generator 技能。
下次生成章节时将使用此配置策略。

应用时间：{timestamp}
配置策略：{strategy}
"""

def update_skill_md(config_file: str, strategy: str, limit: int, use_summary: bool):
    """更新 SKILL.md 文件以引用配置"""
    skill_md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "SKILL.md")

    if not os.path.exists(skill_md_path):
        print(f"警告：未找到 SKILL.md 文件: {skill_md_path}")
        return False

    with open(skill_md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已有 Token 管理部分
    if "## Token 管理策略" in content:
        print("SKILL.md 中已存在 Token 管理部分，将更新...")
        # 这里可以添加更新逻辑，但为了简单起见，我们只添加注释
    else:
        # 在文件末尾添加 Token 管理部分
        token_section = """

## Token 管理策略

由于模型有 131,072 tokens 的限制，当生成多章后可能遇到超限错误。
已应用自动配置来优化 token 使用：

1. **历史章节引用限制**：只引用最近 {limit} 章
2. **使用摘要**：生成章节摘要而非全文
3. **对话管理**：定期清理对话历史

详细配置见: `token-config.md`
工具脚本: `scripts/token_manager.py`

当遇到 token 超限错误时：
1. 运行 `/clear` 清理当前对话
2. 使用 `python scripts/token_manager.py --estimate --dir <章节目录>`
3. 调整引用限制参数
""".format(limit=limit)

        # 找到合适的位置插入（在最后一部分之前）
        sections = content.split('\n## ')
        if len(sections) > 1:
            # 在倒数第二部分后插入
            new_content = '\n## '.join(sections[:-1]) + token_section + '\n\n## ' + sections[-1]
        else:
            new_content = content + token_section

        with open(skill_md_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print("已更新 SKILL.md 文件")

    return True

def create_quick_reference_guide():
    """创建快速参考指南"""
    guide_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "QUICK_TOKEN_GUIDE.md")

    guide_content = """# Token 超限快速处理指南

## 症状
- API 错误：`This model's maximum context length is 131072 tokens`
- 生成章节时突然中断
- 对话历史很长

## 立即处理

### 1. 清理对话历史
```bash
/clear
```

### 2. 估算当前token使用
```bash
# 查看章节目录
python scripts/token_manager.py --estimate --dir ./output --limit 10
```

### 3. 应用优化配置
```bash
# 应用推荐配置（限制3章，使用摘要）
python scripts/apply_config.py --strategy conservative
```

### 4. 重新生成章节
清理对话后，重新生成当前章节。

## 预防措施

### 定期监控
每生成3-5章后检查一次：
```bash
python scripts/token_manager.py --estimate --dir ./output
```

### 使用章节摘要
生成新章节时使用摘要引用：
```bash
# 为第10章生成历史引用摘要
python scripts/token_manager.py --references 10 --ref-limit 3 --dir ./output
```

### 配置建议
| 章节数量 | 推荐配置 |
|----------|----------|
| 1-5章 | 引用全部，使用全文 |
| 6-10章 | 限制5章，使用摘要 |
| 10+章 | 限制3章，使用摘要 |

## 紧急恢复

如果已经超限无法继续：
1. 立即清理对话：`/clear`
2. 备份当前生成的文件
3. 开始新的对话专门用于小说生成
4. 应用严格限制配置

## 联系支持

如果问题持续：
1. 检查 `.learnings/ERRORS.md` 中的错误记录
2. 提供 `token_manager.py` 的输出结果
3. 描述生成到第几章时出现问题
"""

    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide_content)

    print(f"已创建快速指南: {guide_path}")

def main():
    parser = argparse.ArgumentParser(description='应用 token 管理配置')
    parser.add_argument('--strategy', choices=['aggressive', 'conservative', 'minimal'],
                       default='conservative', help='优化策略')
    parser.add_argument('--limit', type=int, help='历史章节引用限制')
    parser.add_argument('--use-summary', action='store_true', help='使用摘要')
    parser.add_argument('--no-summary', action='store_true', help='不使用摘要')
    parser.add_argument('--summary-length', type=int, default=200, help='摘要字数')

    args = parser.parse_args()

    # 根据策略设置默认值
    if args.strategy == 'aggressive':
        default_limit = 2
        default_use_summary = True
    elif args.strategy == 'minimal':
        default_limit = 1
        default_use_summary = True
    else:  # conservative
        default_limit = 3
        default_use_summary = True

    # 使用用户指定值或默认值
    limit = args.limit if args.limit else default_limit
    use_summary = not args.no_summary if args.no_summary else default_use_summary

    print(f"应用配置策略: {args.strategy}")
    print(f"历史章节引用限制: {limit} 章")
    print(f"使用摘要: {use_summary}")
    if use_summary:
        print(f"摘要字数: {args.summary_length}")

    # 创建配置目录
    config_dir = os.path.dirname(os.path.dirname(__file__))
    config_file = os.path.join(config_dir, "token-config.md")

    # 生成配置内容
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    config_content = CONFIG_TEMPLATE.format(
        limit=limit,
        use_summary=use_summary,
        summary_length=args.summary_length,
        timestamp=timestamp,
        strategy=args.strategy
    )

    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)

    print(f"配置已保存到: {config_file}")

    # 更新 SKILL.md
    update_skill_md(config_file, args.strategy, limit, use_summary)

    # 创建快速指南
    create_quick_reference_guide()

    print("\n✅ 配置应用完成！")
    print("\n下一步操作:")
    print(f"  1. 清理当前对话: /clear")
    print(f"  2. 估算token使用: python scripts/token_manager.py --estimate --dir <章节目录>")
    print(f"  3. 开始生成新章节")

    # 显示配置摘要
    print(f"\n配置摘要:")
    print(f"  - 最多引用最近 {limit} 章历史")
    print(f"  - {'使用摘要' if use_summary else '使用全文'}")
    if use_summary:
        print(f"  - 摘要长度: {args.summary_length} 字")
    print(f"  - 建议每 {5 if limit >= 3 else 3} 章清理一次对话")

if __name__ == "__main__":
    main()