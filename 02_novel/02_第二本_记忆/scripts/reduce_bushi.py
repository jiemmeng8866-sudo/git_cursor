"""
减少"不是X是Y"句式脚本
规则：删除冗余的"不是X"，保留"是Y"
保留：多连否定 / X和Y不同维度 / 语义必需的排除
"""
import re, os, sys

VOL5 = r"D:\00_cursor\02_novel\02_第二本_记忆\03_Drafts\第5卷_雨停之后"

# 必须保留的关键词——否定部分如果包含这些，说明X和Y是不同维度
KEEP_NEGATION_WORDS = ['冷', '热', '疼', '死', '怕', '恨', '爱', '等', '在',
                       '宣告', '斗争', '复仇', '纪念', '代价', '习惯', '安慰',
                       '知道', '想', '认识', '记得', '忘了', '看见', '听见',
                       '补偿', '释放', '赎', '典当', '问', '告诉', '回答',
                       '物质', '物理', '化学', '生物', '逻辑', '语法',
                       '草', '树', '花', '虫', '鸟', '鱼',
                       '古董', '废渣', '变异', '病毒', '木马', '后门',
                       '遗', '体', '还', '放', '拿', '给', '要']

def should_keep_negation(x_part, y_part, full_context):
    """判断这个'不是X'是否应该保留"""
    # 规则1：多连否定（前面有连续的"不是"）
    # 在上下文中找
    recent = full_context[-200:] if len(full_context) > 200 else full_context
    not_count = len(re.findall(r'不是', recent[-100:]))
    if not_count >= 3:
        return True

    # 规则2：X包含保留关键词（X和Y是不同维度）
    for w in KEEP_NEGATION_WORDS:
        if w in x_part:
            return True

    # 规则3：X和Y长短差异大（说明X是一个详细描述，删除会丢信息）
    if len(x_part) > 15 and len(y_part) < 5:
        return True

    # 规则4：X包含"不"或"没"（X本身有内部否定结构，语义复杂）
    if '不' in x_part[1:] or '没' in x_part[1:]:  # 跳过开头的"不"
        return True

    # 规则5：Y极短（1-3字）且X也极短——短对仗保留
    if len(y_part) <= 3 and len(x_part) <= 5:
        return True

    return False

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    original = text
    changes = []

    # Pattern 1: 不是X——是Y
    # 匹配 "不是" 后面跟着非破折号内容，然后 "——是"
    pattern1 = re.compile(r'不是([^——\n]{1,60}?)——是')

    def replace_p1(m):
        x_part = m.group(1)
        # Get context: what comes after 是
        pos = m.end()
        remaining = text[:pos]  # for context
        y_part = original[pos:pos+30] if pos < len(original) else ''

        if should_keep_negation(x_part, y_part, remaining):
            return m.group(0)  # keep as-is

        changes.append(f'  删除: 不是{x_part}——→是')
        return '是'

    text = pattern1.sub(replace_p1, text)

    # Pattern 2: 不是X。是Y  (negation with period)
    pattern2 = re.compile(r'不是([^。\n]{1,40}?)。是')

    def replace_p2(m):
        x_part = m.group(1)
        pos = m.end()
        remaining = text[:pos]
        y_part = original[pos:pos+30] if pos < len(original) else ''

        if should_keep_negation(x_part, y_part, remaining):
            return m.group(0)

        changes.append(f'  删除: 不是{x_part}。→是')
        return '是'

    text = pattern2.sub(replace_p2, text)

    # Pattern 3: 不是X，是Y
    pattern3 = re.compile(r'不是([^，\n]{1,40}?)，是')

    def replace_p3(m):
        x_part = m.group(1)
        pos = m.end()
        remaining = text[:pos]
        y_part = original[pos:pos+30] if pos < len(original) else ''

        if should_keep_negation(x_part, y_part, remaining):
            return m.group(0)

        changes.append(f'  删除: 不是{x_part}，→是')
        return '是'

    text = pattern3.sub(replace_p3, text)

    # Only save if there are changes
    if text != original:
        # Count
        old_count = len(re.findall(r'不是.{0,30}?——是', original))
        new_count = len(re.findall(r'不是.{0,30}?——是', text))
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        return changes, old_count, new_count
    return [], 0, 0


def main():
    files = sorted([f for f in os.listdir(VOL5) if f.startswith('第') and f.endswith('.md')])

    total_deleted = 0
    total_old = 0
    total_new = 0

    for fname in files:
        fp = os.path.join(VOL5, fname)
        changes, old, new = process_file(fp)
        if changes:
            print(f'\n{fname}: 删 {old-new} 处 (共{old}→剩{new})')
            for c in changes:
                print(c)
            total_deleted += old - new
        else:
            print(f'{fname}: 无改动')
        total_old += old
        total_new += new

    print(f'\n===== 第5卷汇总 =====')
    print(f'原总计: {total_old} 处')
    print(f'现剩余: {total_new} 处')
    print(f'已删除: {total_deleted} 处 ({total_deleted/total_old*100:.0f}%)')

if __name__ == '__main__':
    main()
