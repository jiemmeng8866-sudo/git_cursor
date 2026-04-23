# ClawHub 技能 · novel-generator（唯一合并副本）

## 来源

- 页面：[novel-generator（ClawHub）](https://clawhub.ai/ityhg/novel-generator)  
- 登记名：`novel-generator`（CLI 安装时使用此 slug，不是 `ityhg/novel-generator`）  
- 本目录安装版本：见 `novel-generator/.clawhub/origin.json`

## 合并说明（已与 `.claude` 副本合一）

- **唯一物理目录**：`02_裂缝外卖_禁区订单/skills/novel-generator/`（含 ClawHub 安装记录 `.clawhub/` + 原 `.claude` 侧 **Token/脚本**：`README_TOKEN.md`、`token-config.md`、`scripts/token_manager.py`、`scripts/apply_config.py`）。
- **全局入口**：`D:\00_cursor\.claude\skills\novel-generator` 为 **目录联接（Junction）**，指向上述路径。请勿在 `.claude` 下再单独改文件，避免与联接目标脱节。

## 本地路径

```text
skills/novel-generator/
├── SKILL.md          ← 技能入口，给 Agent 阅读
├── README.md
├── README_TOKEN.md   ← Token 相关说明（原 .claude 扩展）
├── token-config.md
├── assets/           ← 章节/提示词/记忆模板
├── references/       ← 示例与结构参考
├── scripts/
│   ├── init-novel.sh
│   ├── token_manager.py
│   └── apply_config.py
├── .clawhub/         ← ClawHub 安装元数据
└── .learnings/       ← 技能自带记忆模板（与本书 settings/ 可并行）
```

## 如何与本书配合

- **本书正文**：仍以 `drafts/`、`published/`、`settings/` 为准。  
- **本技能**：适合按 `SKILL.md` 做「提示词扩写、大纲、逐章模板、.learnings 记忆法」；需要新起 `output/` 时，可在本技能目录内运行 `scripts/init-novel.sh`，或手动在本书下建 `output/` 并沿用 `assets/CHAPTER-TEMPLATE.md`。  
- **避免两套设定打架**：长篇以 `settings/world.md` 等为事实源；技能内 `.learnings/` 仅作草稿同步时，记得把定稿抄回 `settings/`。

## 更新

在项目根目录执行：

```bash
npx clawhub update novel-generator --no-input
```

（需已安装 Node；首次使用 ClawHub 可能需要 `npx clawhub login`。）
