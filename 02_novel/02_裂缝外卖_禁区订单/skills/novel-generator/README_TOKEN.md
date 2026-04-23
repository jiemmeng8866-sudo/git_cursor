# Token 超限问题解决方案

## 问题描述
在使用 `novel-generator` 技能生成小说章节时，遇到 API 错误：
```
API Error: 400 {"error":{"message":"This model's maximum context length is 131072 tokens..."}}
```

## 根本原因
- Claude 模型最大支持 **131,072 tokens**
- 生成小说章节时，需要引用历史章节来保持连贯性
- 随着章节增多，引用的历史内容超过 token 限制

## 解决方案概览

### 1. 立即缓解措施
```bash
# 清理当前对话历史
/clear

# 应用优化配置
python scripts/apply_config.py --strategy conservative
```

### 2. 长期预防措施
- 限制历史章节引用数量
- 使用章节摘要替代全文
- 定期清理对话历史

## 工具集说明

### 📊 `token_manager.py` - Token 估算工具
```bash
# 估算章节目录的token使用
python scripts/token_manager.py --estimate --dir ./output

# 生成章节摘要
python scripts/token_manager.py --summary 5 --dir ./output

# 生成历史章节引用摘要
python scripts/token_manager.py --references 10 --ref-limit 3 --dir ./output
```

### ⚙️ `apply_config.py` - 配置应用工具
```bash
# 应用保守策略（推荐）
python scripts/apply_config.py --strategy conservative

# 应用激进策略（章节很多时）
python scripts/apply_config.py --strategy aggressive

# 应用最小策略（严重超限时）
python scripts/apply_config.py --strategy minimal

# 自定义配置
python scripts/apply_config.py --limit 2 --use-summary --summary-length 150
```

## 配置策略对比

| 策略 | 引用限制 | 使用摘要 | 适用场景 |
|------|----------|----------|----------|
| **保守** | 3章 | 是 | 默认推荐，平衡连贯性和性能 |
| **激进** | 2章 | 是 | 章节较多时（10+章） |
| **最小** | 1章 | 是 | 严重超限，紧急恢复时 |

## 工作流程优化

### 推荐工作流程
1. **开始新小说**
   ```bash
   python scripts/apply_config.py --strategy conservative
   /clear
   ```

2. **每生成3-5章后**
   ```bash
   # 检查token使用
   python scripts/token_manager.py --estimate --dir ./output --limit 5
   
   # 如果接近限制，清理对话
   /clear
   ```

3. **遇到超限错误时**
   ```bash
   # 立即清理对话
   /clear
   
   # 应用更严格的配置
   python scripts/apply_config.py --strategy aggressive
   
   # 重新生成当前章节
   ```

## 章节引用优化示例

### 优化前（可能超限）
```markdown
# 生成第15章

## 历史章节引用
第1章：全文内容...
第2章：全文内容...
...
第14章：全文内容...
```

### 优化后（安全）
```markdown
# 生成第15章

## 历史章节摘要引用
第12章：《初露锋芒》  
摘要：主角在学院大比中击败强敌，获得第一名...

第13章：《秘境探险》  
摘要：主角进入上古秘境，获得神秘传承...

第14章：《宗门危机》  
摘要：敌对宗门来袭，主角挺身而出...
```

## 性能预估

| 章节数 | 全文引用token | 摘要引用token | 节省比例 |
|--------|---------------|---------------|----------|
| 5章 | ~75,000 | ~3,000 | 96% |
| 10章 | ~150,000 | ~6,000 | 96% |
| 20章 | ~300,000 | ~12,000 | 96% |

## 常见问题

### Q1: 摘要会影响故事连贯性吗？
**A**: 轻微影响。摘要保留了关键情节和角色状态变化，足以维持基本连贯性。对于复杂的情节线，可以手动补充细节。

### Q2: 需要每次都运行配置脚本吗？
**A**: 不需要。配置一次后持续生效，除非修改技能文件。

### Q3: 如何监控token使用？
**A**: 使用 `token_manager.py --estimate` 定期检查，或设置每N章后自动检查。

### Q4: 还有其他优化方法吗？
**A**: 有：
1. 拆分长章节为多个文件
2. 减少无关的元数据
3. 压缩对话历史中的非必要信息

## 紧急恢复步骤

如果完全无法继续生成：

1. **备份当前文件**
   ```bash
   cp -r ./output ./output_backup_$(date +%Y%m%d)
   ```

2. **清理所有状态**
   ```bash
   /clear
   python scripts/apply_config.py --strategy minimal
   ```

3. **重新开始生成**
   - 开启新对话
   - 从最近成功生成的章节继续

## 技术支持

如果问题持续：
1. 检查 `.learnings/ERRORS.md` 中的错误记录
2. 提供 `token_manager.py` 的输出
3. 描述具体操作步骤和错误信息

---
*最后更新：2026-04-22*  
*相关文件：`token-config.md`, `QUICK_TOKEN_GUIDE.md`*