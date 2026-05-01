import re, os, glob

draft_dir = r'D:\00_cursor\02_novel\02_第二本_百亿求赎记忆？晚了，你的天赋已被我提取\drafts\第1卷_霓虹之下的泥沼'
files = sorted(glob.glob(os.path.join(draft_dir, '*.md')))

total = 0

for f in files:
    with open(f, 'r', encoding='utf-8') as fh:
        text = fh.read()

    # Remove empty lines
    lines = text.split('\n')
    non_empty = [l for l in lines if l.strip()]
    cleaned = '\n'.join(non_empty)

    # Remove all whitespace
    cleaned = re.sub(r'\s', '', cleaned)

    # Remove Chinese punctuation
    cleaned = re.sub(r'[，。！？：；、（）【】《》""''…—]', '', cleaned)
    # Remove English/markdown punctuation
    cleaned = re.sub(r'[.,!?:;()\[\]{}<>\"\'\-…\*\#｜\/\|@\$%&+=^~\`]', '', cleaned)

    count = len(cleaned)
    basename = os.path.basename(f)
    # Extract chapter number for sorting display
    print(f'{basename}: {count}')
    total += count

print(f'\nTotal: {total}')
