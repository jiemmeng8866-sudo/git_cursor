#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re
from collections import defaultdict

drafts_dir = "D:/00_cursor/02_novel/00_第2本/drafts"
out_path = "D:/00_cursor/02_novel/00_第2本/_scan_remains.txt"
open(out_path, "w", encoding="utf-8").close()

def log(msg=""):
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

chapter_files = []
for root, dirs, files in os.walk(drafts_dir):
    for f in files:
        if f.endswith(".md") and not f.startswith("故事大纲") and not f.startswith("第0章"):
            chapter_files.append(os.path.join(root, f))
chapter_files.sort()

file_lines = {}
file_shortnames = {}
for fp in chapter_files:
    with open(fp, "r", encoding="utf-8") as fh:
        content = fh.read()
        lines = content.split("\n")
        file_lines[fp] = lines
        rel = os.path.relpath(fp, drafts_dir)
        file_shortnames[fp] = rel

# Scan 1: 3-line block repeats (should be dramatically reduced)
log("=== 3-LINE BLOCK REPEATS (CROSS-FILE) ===")
block_map = defaultdict(list)
for fp, lines in file_lines.items():
    for i in range(len(lines) - 2):
        block = tuple(lines[i:i+3])
        block_text = "\n".join(block).strip()
        if not block_text or block_text == "---" or block_text.startswith("# "):
            continue
        if all(len(l.strip()) <= 1 for l in block):
            continue
        block_map[block].append((file_shortnames[fp], i+1))

repeated = {k: v for k, v in block_map.items() if len(set(l[0] for l in v)) >= 2}
if repeated:
    sorted_r = sorted(repeated.items(), key=lambda x: -len(x[1]))
    log(f"REMAINING: {len(sorted_r)} blocks\n")
    for block, locations in sorted_r[:40]:
        files_set = set(l[0] for l in locations)
        log(f"[{len(locations)}次 in {len(files_set)}个文件]:")
        for line in block:
            if line.strip():
                log(f"  |{line.strip()[:70]}")
        for loc in locations[:5]:
            log(f"  -> {loc[0]}:{loc[1]}")
        log("")
else:
    log("NONE REMAINING!")

# Scan 2: specific template keywords
log("\n=== KEYWORD SCAN ===")
checks = {
    "成亲了": "Wedding scene",
    "废除后宫制": "Abolish harem",
    "赴汤蹈火，在所不辞": "Loyalty oath",
    "您累了——退朝吧": "Retire suggestion",
    "谁反对——谁就滚": "Emperor dismissal",
    "瑟瑟发抖": "Fear description",
    "是彼此的命": "Fate tag",
    "是……传奇": "Legend tag",
    "他们懂": "They understand",
    "值得": "Worth it (selective)",
}
for pattern, desc in checks.items():
    matches = []
    for fp, lines in file_lines.items():
        for i, line in enumerate(lines):
            if pattern in line:
                matches.append((file_shortnames[fp], i+1, line.strip()[:70]))
    if len(matches) >= 2:
        log(f"\n[{desc}] '{pattern}' -> {len(matches)}次:")
        for m in matches[:10]:
            log(f"   {m[0]}:{m[1]} | {m[2]}")

# Scan 3: "值得" dialogue check
log("\n=== '值得' DIALOGUE CHECK ===")
for fp, lines in file_lines.items():
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped in ('"值得。"', '"值得。"楚惊微说。', '"值得。"萧铎说。', '"值得。"楚惊微说。"值得。"萧铎说。'):
            log(f"  {file_shortnames[fp]}:{i+1} | {stripped[:70]}")

log("\nDone.")
log(f"Results at: {out_path}")
