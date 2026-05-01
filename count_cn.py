import re, os, glob

base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '02_novel', '02_第三本_神庙', '03_Drafts')
total = 0

for vol_name in os.listdir(base):
    vol_dir = os.path.join(base, vol_name)
    if not os.path.isdir(vol_dir):
        continue
    vol_sum = 0
    for f in sorted(glob.glob(os.path.join(vol_dir, '*.md'))):
        text = open(f, encoding='utf-8').read()
        cn = re.findall(r'[一-鿿]', text)
        count = len(cn)
        total += count
        vol_sum += count
        print(f'{count:>6}  {os.path.basename(f)}')
    print(f'--- {vol_name}: {vol_sum} ---')
    print()

print(f'TOTAL Chinese chars: {total}')
