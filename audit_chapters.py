"""Audit Ch53-62 for AI-writing indicators."""
import re, os
from collections import Counter

BASE = "d:/00_cursor/02_novel/02_第三本_神庙/03_Drafts/第2卷_东海龙眼，大乾皇朝"
OUTPUT = "d:/00_cursor/audit_result.txt"

files = sorted([f for f in os.listdir(BASE) if f.endswith('.md') and f[:3] in ['053','054','055','056','057','058','059','060','061','062']])

banned_words = {
    '情绪类': ['五味杂陈','百感交集','心如刀绞','肝肠寸断','悲喜交加','欣喜若狂','怒不可遏','忐忑不安','惴惴不安','如释重负','心有余悸','不知所措','措手不及','无地自容','羞愧难当'],
    '动作类': ['缓缓','悠然','从容不迫地','优雅地','潇洒地','踌躇满志','蹑手蹑脚','小心翼翼'],
    '程度类': ['极其','万分','异常','颇为','甚为','尤为','格外','分外'],
    '转折类': ['然而','殊不知','岂料','不料','谁知','却不曾想'],
    '描写类': ['修长的','白皙的','深邃的','璀璨的','精致的','优美的'],
}

def load_chapter(fname):
    with open(os.path.join(BASE, fname), 'r', encoding='utf-8') as f:
        return f.read()

out_lines = []

def p(s=''):
    out_lines.append(s)

# Process each chapter
all_ratings = []

for fname in files:
    text = load_chapter(fname)
    ch_num = int(fname[:3])
    ch_name = fname[4:-3]

    p(f"\n{'='*60}")
    p(f"## Ch{ch_num}: {ch_name}")
    p(f"{'='*60}")

    issue_count = 0

    # 1. Banned words
    p("\n### 1. 禁用词:")
    banned_found = []
    for cat, words in banned_words.items():
        for w in words:
            for m in re.finditer(re.escape(w), text):
                line_no = text[:m.start()].count('\n') + 1
                ctx = text[max(0,m.start()-15):m.end()+15].replace('\n',' ').strip()
                banned_found.append((w, line_no, ctx))
    p(f"  [N={len(banned_found)}处]")
    for w, ln, ctx in banned_found:
        p(f"  - [{w}] L{ln}: ...{ctx}...")
    issue_count += len(banned_found)

    # 2. Banned sentence patterns
    p("\n### 2. 禁止句式:")
    # 仿佛
    fangfu = [(text[:m.start()].count('\n')+1, text[max(0,m.start()-10):m.end()+10].replace('\n',' ').strip()) for m in re.finditer(r'仿佛', text)]
    # 在...的...下 (adverbial)
    zaixia_raw = list(re.finditer(r'在.{2,40}的.{0,10}下', text))
    zaixia = [(text[:m.start()].count('\n')+1, text[max(0,m.start()-5):m.end()+15].replace('\n',' ').strip()) for m in zaixia_raw if '的' in text[m.start():m.end()]]
    # 此时此刻
    cishicike = [(text[:m.start()].count('\n')+1, '') for m in re.finditer(r'此时此刻', text)]
    # 殊不知
    shubuzhi = [(text[:m.start()].count('\n')+1, '') for m in re.finditer(r'殊不知', text)]
    # 让她 (causal)
    rangta = [(text[:m.start()].count('\n')+1, text[max(0,m.start()-10):m.end()+10].replace('\n',' ').strip()) for m in re.finditer(r'让她', text)]

    patterns = [
        ('仿佛', fangfu),
        ('在...的...下(状语)', zaixia),
        ('此时此刻', cishicike),
        ('殊不知', shubuzhi),
        ('让她(因果句)', rangta),
    ]
    pat_total = 0
    for pname, matches in patterns:
        n = len(matches)
        pat_total += n
        if n > 0:
            p(f"  [{pname}]: {n}处")
            for ln, ctx in matches[:3]:
                p(f"    L{ln}: {ctx}")
        else:
            p(f"  [{pname}]: 0处")
    p(f"  禁止句式总计: {pat_total}处")
    issue_count += pat_total

    # 3. Idioms (四字成语)
    p("\n### 3. 成语 (四字格):")
    cjk_4 = re.findall(r'[一-鿿]{4}', text)
    idiom_counter = Counter(cjk_4)
    # Top 15
    top15 = idiom_counter.most_common(15)
    p(f"  [前15高频]: {', '.join([f'{w}({c})' for w,c in top15])}")
    p(f"  四字组合总数(去重): {len(idiom_counter)}")

    # 4. Dialogue tags
    p("\n### 4. 对话标签AI化:")
    dt_patterns = ['地说','说道','回答道','追问道','苦笑着说','淡淡地说','冷冷地说']
    dt_found = []
    for dt in dt_patterns:
        for m in re.finditer(re.escape(dt), text):
            line_no = text[:m.start()].count('\n') + 1
            ctx = text[max(0,m.start()-10):m.end()+10].replace('\n',' ').strip()
            dt_found.append((dt, line_no, ctx))
    p(f"  [N={len(dt_found)}处]")
    for dt, ln, ctx in dt_found:
        p(f"  - [{dt}] L{ln}: ...{ctx}...")
    issue_count += len(dt_found)

    # 5. Psychological exposition words
    p("\n### 5. 心理直白词:")
    psych_words = ['感到','觉得','心想','意识到','明白了一个道理','不禁','不由得']
    psych_found = []
    for pw in psych_words:
        for m in re.finditer(re.escape(pw), text):
            line_no = text[:m.start()].count('\n') + 1
            ctx = text[max(0,m.start()-10):m.end()+10].replace('\n',' ').strip()
            psych_found.append((pw, line_no, ctx))
    p(f"  [N={len(psych_found)}处]")
    for pw, ln, ctx in psych_found:
        p(f"  - [{pw}] L{ln}: ...{ctx}...")
    issue_count += len(psych_found)

    # 6. Exclamation marks
    exc_count = text.count('！')
    p(f"\n### 6. 感叹号: {exc_count}个")
    if exc_count > 3:
        issue_count += exc_count

    # 7. Long paragraphs (>4 sentences)
    p("\n### 7. 超长段落 (>4句):")
    paras_raw = text.split('\n\n')
    long_paras = []
    for i, ptext in enumerate(paras_raw):
        pt = ptext.strip()
        if not pt or pt.startswith('#') or pt == '***' or pt == '---' or pt.startswith('>'):
            continue
        sc = len(re.findall(r'[。！？]', pt))
        if sc > 4:
            # estimate line number
            pre_text = '\n\n'.join(paras_raw[:i])
            line_no = pre_text.count('\n') + 1
            preview = pt[:120].replace('\n', ' ')
            long_paras.append((sc, line_no, preview))
    p(f"  [N={len(long_paras)}段]")
    for sc, ln, prev in long_paras:
        p(f"  - L{ln}: [{sc}句] {prev}...")
    issue_count += len(long_paras)

    # 8. Summary ending
    p("\n### 8. 总结性结尾:")
    is_summary = False
    if paras_raw:
        last_p = [p.strip() for p in paras_raw if p.strip() and not p.strip().startswith('#') and p.strip() != '***']
        if last_p:
            lp = last_p[-1]
            summary_kw = ['接下来','这一路','从此','通过这次','总的来说','卷终']
            is_summary = any(kw in lp for kw in summary_kw)
            p(f"  {'有' if is_summary else '无'} (末段: {lp[:100]}...)")
    if is_summary:
        issue_count += 1

    # 9. Punctuation abuse
    p("\n### 9. 标点滥用:")
    ellipsis = text.count('……')
    dash = text.count('——')
    p(f"  省略号: {ellipsis}个, 破折号: {dash}个")
    abuse = (ellipsis > 5 or dash > 50)
    p(f"  滥用判定: {'有' if abuse else '无'}")
    if abuse:
        issue_count += 1

    # 10. Long sentences (>40 Chinese chars)
    p("\n### 10. 超长句 (>40字):")
    sentences = re.split(r'[。！？]', text)
    long_sents = []
    for s_text in sentences:
        s_text = s_text.strip()
        if not s_text or s_text.startswith('#'):
            continue
        cn_chars = len(re.findall(r'[一-鿿]', s_text))
        if cn_chars > 40:
            # find approximate line number
            idx = text.find(s_text)
            line_no = text[:idx].count('\n') + 1 if idx >= 0 else 0
            preview = s_text[:100]
            long_sents.append((cn_chars, line_no, preview))
    p(f"  [N={len(long_sents)}句]")
    for cc, ln, prev in long_sents[:5]:
        p(f"  - L{ln}: [{cc}字] {prev}...")
    issue_count += len(long_sents)

    # 11. Direct emotion words
    p("\n### 11. 直白抒情词:")
    emotion_words = ['绝望','痛苦','悲伤','孤独','空虚','悲惨']
    emo_found = []
    for ew in emotion_words:
        for m in re.finditer(re.escape(ew), text):
            line_no = text[:m.start()].count('\n') + 1
            ctx = text[max(0,m.start()-10):m.end()+10].replace('\n',' ').strip()
            emo_found.append((ew, line_no, ctx))
    p(f"  [N={len(emo_found)}处]")
    for ew, ln, ctx in emo_found:
        p(f"  - [{ew}] L{ln}: ...{ctx}...")
    issue_count += len(emo_found)

    # 12. Light-wave combat
    p("\n### 12. 光波战斗:")
    light_patterns = ['光束','光柱','光波','能量波']
    light_found = []
    for lp in light_patterns:
        for m in re.finditer(re.escape(lp), text):
            line_no = text[:m.start()].count('\n') + 1
            ctx = text[max(0,m.start()-10):m.end()+20].replace('\n',' ').strip()
            light_found.append((m.group(), line_no, ctx))
    p(f"  {'有' if light_found else '无'} ({len(light_found)}处)")
    if light_found:
        issue_count += len(light_found)
        for w, ln, ctx in light_found:
            p(f"  - [{w}] L{ln}: ...{ctx}...")

    # 13. Cardboard NPCs
    p("\n### 13. 纸片人NPC:")
    npc_patterns = ['面无表情','冷笑','淡漠','毫无感情','机械地','模板化']
    npc_found = []
    for np in npc_patterns:
        for m in re.finditer(re.escape(np), text):
            line_no = text[:m.start()].count('\n') + 1
            npc_found.append((np, line_no))
    p(f"  {'有' if npc_found else '无'} ({len(npc_found)}处)")
    if npc_found:
        issue_count += len(npc_found)
        for w, ln in npc_found:
            p(f"  - [{w}] L{ln}")

    # 14. Modern internet slang
    p("\n### 14. 现代网络用语:")
    slang_patterns = ['卧槽','牛逼','666','给力','也是醉了','绝绝子','内卷','摆烂','PUA','emo']
    slang_found = []
    for sl in slang_patterns:
        for m in re.finditer(re.escape(sl), text, re.IGNORECASE):
            line_no = text[:m.start()].count('\n') + 1
            slang_found.append((sl, line_no))
    p(f"  {'有' if slang_found else '无'} ({len(slang_found)}处)")
    if slang_found:
        issue_count += len(slang_found)

    # AI-flavor score
    p("\n### AI味综合评级:")
    if issue_count <= 3:
        rating = "无"
    elif issue_count <= 8:
        rating = "轻微"
    elif issue_count <= 15:
        rating = "中等"
    else:
        rating = "严重"
    p(f"  问题总数: {issue_count}, 评级: {rating}")
    all_ratings.append((ch_num, ch_name, rating, issue_count))

# Summary
p(f"\n\n{'='*60}")
p(f"## 汇总: Ch53-62 AI味严重程度排序")
p(f"{'='*60}")
all_ratings.sort(key=lambda x: x[3], reverse=True)
for i, (num, name, rating, count) in enumerate(all_ratings, 1):
    p(f"  {i}. Ch{num} {name}: {rating} ({count}个问题)")

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out_lines))
print(f"Done. Output written to {OUTPUT}")
