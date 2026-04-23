# Token 管理配置

## 问题诊断
在使用 novel-generator 技能生成小说章节时遇到 token 超限错误：
- 模型限制：131,072 tokens
- 当前使用：131,408 tokens (超出 336 tokens)
- 主要消耗：历史章节全文引用

## 配置参数

### 1. 历史章节引用限制
```yaml
# 章节引用策略
history_chapters_limit: 3  # 最多引用最近 N 章
include_full_text: false   # 是否包含全文 (true/false)
summary_length: 200        # 摘要字数 (当 include_full_text=false 时)
```

### 2. 对话管理
```yaml
# 对话管理策略
max_conversation_turns: 20  # 最大对话轮数
auto_clear_threshold: 15    # 超过此轮数后建议清理
new_session_per_chapter: 5  # 每生成 N 章开启新对话
```

### 3. 章节生成优化
```yaml
# 章节生成参数
chapter_word_limit: 2500    # 每章字数限制
section_break_threshold: 500 # 超过此字数强制分段
enable_progressive_summary: true # 启用渐进式摘要
```

## 实现方案

### 方案 A：引用限制 (推荐)
```python
def get_chapter_references(chapter_dir, current_chapter_num, limit=3):
    """
    获取需要引用的历史章节
    - 只引用最近 `limit` 章
    - 生成摘要而非全文
    - 排除当前章节
    """
    chapters = sorted([f for f in os.listdir(chapter_dir) if f.endswith('.md')])
    recent_chapters = chapters[-limit-1:-1] if len(chapters) > limit else chapters
    
    references = []
    for chap in recent_chapters:
        if f"chapter_{current_chapter_num:03d}.md" in chap:
            continue
        summary = generate_summary(os.path.join(chapter_dir, chap), 200)
        references.append(f"## {chap}\n{summary}\n")
    
    return "\n".join(references)
```

### 方案 B：对话分段
```bash
# 每生成5章后清理对话
/clear
# 重新开始小说生成会话
```

### 方案 C：章节摘要生成
```python
def generate_summary(file_path, max_words=200):
    """生成章节摘要"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取关键信息：标题、概要、关键事件
    lines = content.split('\n')
    title = lines[0] if lines else ""
    summary_line = ""
    for line in lines:
        if "本章概要" in line or "核心事件" in line:
            summary_line = line
            break
    
    # 如果找不到概要，生成简单摘要
    if not summary_line:
        # 取前3段作为摘要
        paragraphs = content.split('\n\n')
        summary = ' '.join(paragraphs[:3])[:max_words*2] + "..."
    else:
        summary = summary_line.replace("> **本章概要**：", "").strip()
    
    return f"{title}\n摘要：{summary}"
```

## 配置使用指南

### 1. 快速应用配置
```bash
# 应用默认配置
python apply_token_config.py --strategy limit --limit 3 --use-summary
```

### 2. 监控token使用
```bash
# 估算token使用量
python estimate_tokens.py --dir ./02_novel/01_第一本/drafts
```

### 3. 清理对话历史
```bash
# 清理当前对话，开始新会话
/clear
echo "开始新的小说生成会话..."
```

## 性能优化建议

### 优先级排序
1. **立即实施**：限制历史章节引用为最近3章
2. **短期优化**：启用章节摘要生成
3. **长期策略**：实现对话分段管理

### 预期效果
| 策略 | Token 减少 | 质量影响 | 实施难度 |
|------|------------|----------|----------|
| 引用限制 | 40-60% | 轻微 | 低 |
| 使用摘要 | 70-80% | 中等 | 中 |
| 对话分段 | 90%+ | 无 | 低 |

## 紧急处理流程

### 遇到 token 超限时：
1. 立即清理对话历史：`/clear`
2. 应用引用限制配置
3. 重新开始生成当前章节
4. 记录错误到 `.learnings/ERRORS.md`

### 预防措施：
- 每生成3章后检查token使用
- 定期清理对话历史
- 使用章节摘要替代全文

## 配置验证

### 验证当前配置：
```bash
python validate_config.py --config token-config.md
```

### 测试token估算：
```bash
python test_token_usage.py --chapters 5 --strategy summary
```

---

*最后更新：2026-04-22*
*适用版本：novel-generator v1.0.0+*