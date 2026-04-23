# 《裂缝外卖：修真命契版》

> 修真玄幻 × 命契物流 × 裂隙副本 × 热血爽文

---

## 书名备选

- 《裂缝外卖：我只送禁区订单》
- 《禁区速递：我送的货签收要人命》
- 《高武快递：这单终点在裂缝里》

---

## 一句话 Logline

底层散修签下命契法帖，专送带条款的裂隙法货；送不到会被因果反噬，送到了——全城都要为结果买单。

---

## 核心机制（写作铁律）

1. **货单即规则**：每单附带临时条款；以封签打印与手环公证为准，不听客户口述。
2. **履约掠夺**：完美/超额履约可得碎片；必有身体或精神代价。
3. **双层城市**：表城讲法律，里界讲封签；冲突即戏剧。

---

## 设定文档索引（从这里进）

| 文件 | 用途 |
|---|---|
| `settings/world.md` | 世界观单一事实源：空间分层、规则、经济、势力、武力用法 |
| `settings/architecture.md` | 全书叙事支柱、四卷功能、线索排布、反派阶梯 |
| `settings/orders.md` | 订单色标、条款模板、掠夺约束、截单套路 |
| `settings/characters.md` | 人物定名与关系、弧光、台词调性 |
| `settings/timeline.md` | 四卷总览 + 第一卷 1～20 章功能表 + 伏笔清单 |
| `settings/glossary.md` | 术语表，防前后称呼漂移 |
| `settings/writer_style.md` | **写作风格**：视角、句段、感官、对话、爽点、钩子、去 AI 味清单 |
| `settings/reality_hooks.md` | **现实代入**：平台倒计时/算法焦虑等情绪如何化用；附公开背景链接与合规提醒 |

---

## ClawHub 技能（已下载）

- 页面：[novel-generator @ ClawHub](https://clawhub.ai/ityhg/novel-generator)  
- **唯一合并目录**：`skills/novel-generator/`（ClawHub 版 + 原 `.claude` 内 Token/脚本已并入）  
- **全局路径**：`D:\00_cursor\.claude\skills\novel-generator` 为指向该目录的 **Junction**，勿重复维护两套文件夹。  
- 使用说明：`skills/README.md`  

## 目录结构

```text
02_裂缝外卖_禁区订单/
├── readme.md
├── skills/
│   ├── README.md
│   └── novel-generator/    # ClawHub 爽文生成技能（SKILL.md + 模板 + .learnings）
├── settings/
│   ├── world.md
│   ├── architecture.md
│   ├── orders.md
│   ├── characters.md
│   ├── timeline.md
│   ├── glossary.md
│   ├── writer_style.md
│   └── reality_hooks.md
├── drafts/
├── published/
└── prompts/
    └── chapter_prompt.md   # 本书专用章节提示约束
```

---

## 第一卷目标（不变）

- 立住陆野「认账、话少、撕条款」人设。
- 用 3～5 单禁区单，扯开「速递行—截单帮—财团甲方」三角。
- 抛出父亲旧编号与「姓名写入封签」之谜。

---

## 工作流程（定稿与记忆）

### drafts → published

1. 在 `drafts/chapter_XXX.md` 改到满意（可反复改）。  
2. 定稿后复制到 `published/`，命名建议：`第XXX章_短标题.md`（与番茄章节名一致更好检索）。  
3. 在 `settings/timeline.md` 或另建 `settings/canon.md` 记一行「本章已锁定事实」（可选，长篇后很有用）。  

### 设定唯一事实源

- **剧情与世界观以 `settings/` 为准**（尤其 `world.md`、`characters.md`）。  
- `skills/novel-generator/.learnings/` 仅作跑技能模板时的草稿；从技能里得到的新设定，**务必抄回 `settings/`**，避免两套记忆打架。  

### 写新章前

- 填 `prompts/chapter_prompt.md` 里的「本章填写」；有单先按 `settings/orders.md` 订单模板列条款再写。  

---

## 番茄向提醒

- 一章尽量围绕「一单」或「一条条款」推进。
- **字数**：单章以 **3000～3500 字** 为主目标；过渡章最低 **2500 字**（见 `settings/writer_style.md`「章节体量」）。
- 章末卡在：倒计时、追加条款、截单者、甲方现真身。
- 解释设定用动作验证，不用讲课。

---

## 正文进度

- `drafts/chapter_001.md`～`chapter_005.md`：入行、首单履约、掠夺代价、回行结算、财团单加压（详见各章梗概）。
