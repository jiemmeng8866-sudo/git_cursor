"""
全局版"不是X是Y"清理脚本
目标：全五卷保留不超过9处，其余全部用直接肯定改写
"""
import re, os, sys
from pathlib import Path
from collections import defaultdict

BASE = Path(r"D:\00_cursor\02_novel\02_第二本_记忆\03_Drafts")
GLOBAL_KEEP = 9  # 全五卷总共保留数

# === 评分逻辑 ===

def is_multi_negation(text, match_start):
    start = max(0, match_start - 150)
    context = text[start:match_start]
    return len(re.findall(r'不是', context)) >= 2

def is_dialogue(text, match_start):
    before = text[:match_start]
    line_start = before.rfind('\n', 0, match_start)
    if line_start == -1:
        line_start = 0
    line_before = before[line_start:match_start]
    return bool(re.search(r'[「「"][^」」"]*$', line_before))

def is_emotional_climax(text, match_start, chapter_length):
    return match_start / max(chapter_length, 1) > 0.75

def is_worldbuilding(text, match_start):
    before = text[:match_start]
    recent = before[-200:] if len(before) > 200 else before
    worldbuilding_words = ['法则', '定律', '琥珀', '契约', '合约', '典当', '守门', '渊', '门扇', '铜制凹槽',
                           '门后不是空的', '代价', '记忆', '代码']
    return any(w in recent for w in worldbuilding_words)

def score_instance(x_part, text, match_start, match_full, chapter_length):
    score = 0
    if is_multi_negation(text, match_start):
        score += 50
    if is_dialogue(text, match_start):
        score += 30
    if is_emotional_climax(text, match_start, chapter_length):
        score += 20
    if is_worldbuilding(text, match_start):
        score += 15
    emotional_words = ['怕', '恨', '爱', '死', '冷', '热', '疼', '等', '在',
                       '习惯', '记忆', '认识', '知道', '忘了', '看见', '听见']
    for w in emotional_words:
        if w in x_part:
            score += 10
            break
    if '不' in x_part[1:] or '没' in x_part[1:]:
        score += 10
    if len(x_part) <= 6:
        score += 5
    return score

# === 模式匹配 ===

def find_all_instances(text):
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

    # Pattern 4: 不是X,是Y (English comma)
    for m in re.finditer(r'不是([^,\n]{1,40}?),是', text):
        # avoid duplicating pattern 3
        instances.append({
            'match': m.group(0),
            'x_part': m.group(1),
            'start': m.start(),
            'end': m.end(),
            'type': 'eng_comma',
            'separator': ',是'
        })

    return sorted(instances, key=lambda x: x['start'])

# === 获取Y部分 ===

def get_y_part(text, inst):
    after = text[inst['end']:]
    y_end = len(after)
    for i, ch in enumerate(after):
        if ch in '。——\n，,;；' and i > 0:
            y_end = i
            break
    return after[:y_end]

# === 替换逻辑 ===

def build_replacement(inst, y_part, text):
    """根据上下文构建最自然的替换文本"""

    # Y部分去掉前导的"是"
    y_clean = y_part
    if y_clean.startswith('是'):
        y_clean = y_clean[1:]

    # 获取替换前的完整原文片段
    old_full = inst['match'] + y_part

    if inst['type'] == 'dash':
        # 不是X——是Y → Y（直接肯定）
        # 但要检查Y是否本身完整
        if y_clean.strip():
            replacement = y_part  # 保留"是Y"或"Y"
        else:
            replacement = inst['x_part']  # fallback: 用X的正面表述
    elif inst['type'] == 'period':
        # 不是X。是Y → Y（或 是Y）
        if y_clean.strip():
            replacement = y_part
        else:
            replacement = inst['x_part']
    else:
        # 不是X，是Y → Y
        if y_clean.strip():
            replacement = y_part
        else:
            replacement = inst['x_part']

    return replacement, old_full

# === 全局主流程 ===

def collect_all():
    """扫描所有章节，收集全局实例列表"""
    all_instances = []  # [(vol, ch, filepath, text, inst_dict)]

    vols = sorted([d for d in os.listdir(BASE) if d.startswith('第') and os.path.isdir(BASE / d)])

    for vol in vols:
        vol_path = BASE / vol
        chapters = sorted([f for f in os.listdir(vol_path) if f.startswith('第') and f.endswith('.md')])

        for ch in chapters:
            fp = vol_path / ch
            text = fp.read_text(encoding='utf-8')
            instances = find_all_instances(text)

            for inst in instances:
                inst['vol'] = vol
                inst['ch'] = ch
                inst['fp'] = fp
                inst['text_len'] = len(text)
                inst['y_part'] = get_y_part(text, inst)
                inst['score'] = score_instance(
                    inst['x_part'], text, inst['start'], inst['match'], len(text)
                )
                all_instances.append(inst)

    return all_instances

def apply_replacements(all_instances, keep_starts):
    """按文件分组，从后往前替换"""

    # 按文件分组
    by_file = defaultdict(list)
    for inst in all_instances:
        by_file[inst['fp']].append(inst)

    stats = {'total': len(all_instances), 'kept': 0, 'deleted': 0}
    results = []

    for fp, insts in by_file.items():
        text = fp.read_text(encoding='utf-8')

        # 筛选该文件中要保留的
        to_delete = [i for i in insts if i['start'] not in keep_starts]
        to_keep = [i for i in insts if i['start'] in keep_starts]

        stats['kept'] += len(to_keep)
        stats['deleted'] += len(to_delete)

        if not to_delete:
            continue

        # 从后往前替换
        for inst in sorted(to_delete, key=lambda x: x['start'], reverse=True):
            # 重新获取Y部分（文本可能已被前面的替换改变）
            # 由于是从后往前，不会影响
            y = inst['y_part']
            replacement, old_full = build_replacement(inst, y, text)

            # 执行替换
            end_pos = inst['start'] + len(old_full)
            text = text[:inst['start']] + replacement + text[end_pos:]

        fp.write_text(text, encoding='utf-8')

        # 记录
        results.append({
            'vol': insts[0]['vol'],
            'ch': insts[0]['ch'],
            'deleted': len(to_delete),
            'kept': len(to_keep),
            'kept_instances': [
                {'x': i['x_part'][:30], 'y': i['y_part'][:30], 'score': i['score']}
                for i in to_keep
            ]
        })

    return stats, results

def main(dry_run=True):
    print("=" * 60)
    print("全局扫描所有章节...")
    print("=" * 60)

    all_instances = collect_all()
    print(f"\n全五卷共发现 {len(all_instances)} 处 '不是X是Y' 模式")

    # 按分数排序
    sorted_inst = sorted(all_instances, key=lambda x: x['score'], reverse=True)

    # 预览Top N
    print(f"\n{'='*60}")
    print(f"全局保留前 {GLOBAL_KEEP} 处（按重要性排序）:")
    print(f"{'='*60}")

    keep_starts = set()
    for i, inst in enumerate(sorted_inst[:GLOBAL_KEEP]):
        keep_starts.add(inst['start'])
        print(f"\n  #{i+1} [分数:{inst['score']}] {inst['vol']}/{inst['ch']}")
        print(f"    不是{inst['x_part'][:40]}...")
        print(f"    → 是{inst['y_part'][:50]}...")

    # 统计每个文件将被改多少
    print(f"\n{'='*60}")
    print(f"将被删除的: {len(all_instances) - GLOBAL_KEEP} 处")
    print(f"将被保留的: {GLOBAL_KEEP} 处")
    print(f"{'='*60}")

    if dry_run:
        print("\n[DRY RUN] 以上为预览，未实际修改。")
        print("如需执行，请运行: python global_remove_bushi.py --apply")
        return

    # 执行替换
    stats, results = apply_replacements(all_instances, keep_starts)

    print(f"\n{'='*60}")
    print("替换完成!")
    print(f"{'='*60}")
    print(f"总计: {stats['total']} → {stats['kept']} (删除{stats['deleted']}处)")

    # 按卷输出
    by_vol = defaultdict(list)
    for r in results:
        by_vol[r['vol']].append(r)

    for vol in sorted(by_vol.keys()):
        items = by_vol[vol]
        v_deleted = sum(i['deleted'] for i in items)
        v_kept = sum(i['kept'] for i in items)
        print(f"\n  {vol}: 删{v_deleted}处, 保留{v_kept}处")
        for item in items:
            if item['kept'] > 0:
                for k in item['kept_instances']:
                    print(f"    [{k['score']}分] 不是{k['x']}...")

if __name__ == '__main__':
    dry = '--apply' not in sys.argv
    main(dry_run=dry)
