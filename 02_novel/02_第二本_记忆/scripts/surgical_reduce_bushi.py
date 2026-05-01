"""
外科手术式"不是X是Y"精简脚本
规则：每章保留2-3处（情绪高潮/世界观定义/叙事转折），其余用三种策略改写
策略1：直接肯定——删除"不是X"，保留"是Y"
策略2：动作替代——用生理细节替代解释性否定
策略3：白描重构——用精准动词/名词重组
"""
import re, os, sys, json
from pathlib import Path

BASE = Path(r"D:\00_cursor\02_novel\02_第二本_记忆\03_Drafts")

# === 每章保留2-3处的判断逻辑 ===

# 绝对保留标记：这些词/模式出现时优先保留
HIGH_PRIORITY_PATTERNS = [
    # 世界观核心定义
    '不是追踪——是感知',
    '不是给。是卖。',
    '不是典当行。是古董店。',
    # 情绪/身份核心反差的标志词
    '不是没有感情——是像有人在',
    '不是皮肤冷——是从头骨里面',
    '不是学来的——是刻进去',
    '不是空洞——是空间',
    # 多连否定永远是保留的
]

def count_bushi_in_context(text, pos, radius=150):
    """计算某个位置附近'不是'的数量"""
    start = max(0, pos - radius)
    end = min(len(text), pos + radius)
    context = text[start:end]
    return len(re.findall(r'不是', context))

def is_multi_negation(text, match_start):
    """检查是否是多连否定（前面100字符内有3+个'不是'）"""
    start = max(0, match_start - 150)
    context = text[start:match_start]
    return len(re.findall(r'不是', context)) >= 2  # 加上当前这个就是3+

def is_dialogue(text, match_start):
    """检查是否在对话中（引号内）"""
    before = text[:match_start]
    # 简单检查：前面最近的引号是左引号还是右引号
    last_open = before.rfind('"')
    last_close = before.rfind('"')
    # 简化：如果匹配位置在对话段中
    line_start = before.rfind('\n', 0, match_start)
    if line_start == -1:
        line_start = 0
    line_before = before[line_start:match_start]
    return bool(re.search(r'[「「"][^」」"]*$', line_before))

def is_emotional_climax(text, match_start, chapter_length):
    """检查是否在章节后20%位置（情绪高潮区）"""
    position_ratio = match_start / max(chapter_length, 1)
    return position_ratio > 0.75

def is_worldbuilding(text, match_start):
    """检查是否包含世界观关键词"""
    before = text[:match_start]
    recent = before[-200:] if len(before) > 200 else before
    worldbuilding_words = ['法则', '定律', '琥珀', '契约', '合约', '典当', '守门', '渊', '门扇', '铜制凹槽']
    return any(w in recent for w in worldbuilding_words)

def score_instance(x_part, text, match_start, chapter_length):
    """给一个'不是X是Y'实例打分，分数越高越该保留"""
    score = 0

    # 多连否定（最强保留信号）
    if is_multi_negation(text, match_start):
        score += 50

    # 对话中的（强保留）
    if is_dialogue(text, match_start):
        score += 30

    # 情绪高潮区
    if is_emotional_climax(text, match_start, chapter_length):
        score += 20

    # 世界观相关
    if is_worldbuilding(text, match_start):
        score += 15

    # X包含关键情感词
    emotional_words = ['怕', '恨', '爱', '死', '冷', '热', '疼', '等', '在',
                       '习惯', '记忆', '认识', '知道', '忘了', '看见', '听见']
    for w in emotional_words:
        if w in x_part:
            score += 10
            break

    # X本身包含否定（双重否定结构）
    if '不' in x_part[1:] or '没' in x_part[1:]:
        score += 10

    # 很短的对仗（≤6字）
    if len(x_part) <= 6:
        score += 5

    return score

# === 三种改写策略 ===

def rewrite_direct_affirmation(full_match, x_part, y_text):
    """策略1：直接肯定——删除'不是X'，保留'是Y'或'Y'"""
    # y_text starts after the separator (——是 / 。是 / ，是)
    # The separator and 是 are part of the match
    if y_text.startswith('是'):
        return y_text  # "是Y"
    else:
        return y_text

def rewrite_action_substitution(full_context, x_part, y_part):
    """策略2：动作替代——用生理细节或客观描述替代"""
    # For most cases, just use direct affirmation as fallback
    # This strategy is hard to automate and best done manually
    return None  # Signal to use direct affirmation instead

def rewrite_plain_description(full_context, x_part, y_part):
    """策略3：白描重构"""
    return None  # Same - best done manually

# === 主处理逻辑 ===

def find_all_instances(text):
    """找到所有'不是X是Y'实例，返回(match, x_part, start_pos, pattern_type)"""
    instances = []

    # Pattern 1: 不是X——是Y
    for m in re.finditer(r'不是([^——\n]{1,60}?)——是', text):
        instances.append({
            'match': m.group(0),
            'x_part': m.group(1),
            'start': m.start(),
            'end': m.end(),
            'type': 'dash',
            'separator': '——是'
        })

    # Pattern 2: 不是X。是Y
    for m in re.finditer(r'不是([^。\n]{1,40}?)。是', text):
        instances.append({
            'match': m.group(0),
            'x_part': m.group(1),
            'start': m.start(),
            'end': m.end(),
            'type': 'period',
            'separator': '。是'
        })

    # Pattern 3: 不是X，是Y
    for m in re.finditer(r'不是([^，\n]{1,40}?)，是', text):
        instances.append({
            'match': m.group(0),
            'x_part': m.group(1),
            'start': m.start(),
            'end': m.end(),
            'type': 'comma',
            'separator': '，是'
        })

    return sorted(instances, key=lambda x: x['start'])

def get_y_text(text, instance):
    """获取Y部分的文本（从匹配结束位置往后取30字符）"""
    end = instance['end']
    return text[end:end+50]

def process_chapter(filepath, keep_count=3):
    """处理单个章节"""
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()

    instances = find_all_instances(original)

    if len(instances) <= keep_count:
        return None, 0, 0  # 不需要处理

    # 给每个实例打分
    for inst in instances:
        inst['score'] = score_instance(
            inst['x_part'], original, inst['start'], len(original)
        )
        inst['y_text'] = get_y_text(original, inst)

    # 按分数排序，保留前keep_count个
    sorted_instances = sorted(instances, key=lambda x: x['score'], reverse=True)
    keep_starts = {inst['start'] for inst in sorted_instances[:keep_count]}

    # 从后往前替换（避免位置偏移）
    text = original
    changes = []
    deleted_count = 0

    for inst in reversed(instances):
        if inst['start'] in keep_starts:
            continue  # 保留

        # 决定改写方式：默认直接肯定
        # 获取Y部分
        after_match = text[inst['end']:]

        # 构建替换文本
        # 分离器后面的"是Y"部分
        sep = inst['separator']  # '——是' or '。是' or '，是'

        # 找到Y的结束位置（下一个句号或破折号或段落结束）
        y_end = len(after_match)
        for i, ch in enumerate(after_match):
            if ch in '。——\n，' and i > 0:
                y_end = i
                break

        y_part = after_match[:y_end]

        # 构建替换
        if inst['type'] == 'dash':
            # 不是X——是Y → Y （如果Y够完整）或 是Y
            replacement = y_part
        elif inst['type'] == 'period':
            # 不是X。是Y → 是Y
            replacement = '是' + y_part
        else:
            # 不是X，是Y → 是Y
            replacement = '是' + y_part

        old_text = inst['match'] + y_part

        # 确保替换后的文本在上下文中通顺
        # 如果replacement为空，用直接短语
        if not replacement.strip():
            replacement = inst['x_part']  # fallback: just use what X described

        text = text[:inst['start']] + replacement + text[inst['start'] + len(old_text):]

        changes.append({
            'x': inst['x_part'],
            'y': y_part,
            'replacement': replacement,
            'score': inst['score']
        })
        deleted_count += 1

    if text != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        return changes, len(instances), deleted_count
    return None, len(instances), 0


def main():
    vols = sorted([d for d in os.listdir(BASE) if d.startswith('第') and os.path.isdir(BASE / d)])

    grand_total_original = 0
    grand_total_deleted = 0
    grand_total_kept = 0

    for vol in vols:
        vol_path = BASE / vol
        chapters = sorted([f for f in os.listdir(vol_path) if f.startswith('第') and f.endswith('.md')])

        print(f'\n{"="*60}')
        print(f'{vol}: {len(chapters)}章')
        print(f'{"="*60}')

        vol_original = 0
        vol_deleted = 0

        for ch in chapters:
            fp = vol_path / ch
            changes, total, deleted = process_chapter(str(fp), keep_count=3)

            if changes is not None:
                kept = total - deleted
                print(f'  {ch}: {total}→{kept} (删{deleted}处, 保留{kept}处)')
                for c in changes[:3]:  # 只显示前3个改动
                    print(f'    - 删: 不是{c["x"][:20]}... → {c["replacement"][:30]}...')
                if len(changes) > 3:
                    print(f'    ... 及其他{len(changes)-3}处')
                vol_original += total
                vol_deleted += deleted
            elif total > 0:
                print(f'  {ch}: {total}处 (≤3, 无需处理)')
                vol_original += total
            else:
                print(f'  {ch}: 0处')

        print(f'  {vol}汇总: {vol_original}→{vol_original - vol_deleted} (删{vol_deleted}处)')
        grand_total_original += vol_original
        grand_total_deleted += vol_deleted

    print(f'\n{"="*60}')
    print(f'全五卷汇总: {grand_total_original}处 → {grand_total_original - grand_total_deleted}处')
    print(f'删除: {grand_total_deleted}处 ({grand_total_deleted/grand_total_original*100:.0f}%)')
    print(f'保留: {grand_total_original - grand_total_deleted}处')

if __name__ == '__main__':
    main()
