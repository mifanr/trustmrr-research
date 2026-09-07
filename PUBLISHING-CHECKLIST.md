# 转公开之前

大部分事已经做完。剩下的只有一件需要你决定。

## 已经处理好的

- 原始数据不入库。`data/startups.jsonl`、`data/head_freshness.json`、`data/census-report.txt`
  已加入 `.gitignore`，git 历史已重写，这三个文件从未存在过。
  仓库发的是 `anonymize.py` 产出的脱敏版，`--check` 断言它能精确复现六个关键数字。
- `census-report.txt` 里点名了三位 MRR 为 0 的创始人，该文件已整体移出仓库，
  结论已被 `data/report_v2.txt` 取代。
- `.env` 从未进过历史。README 中英双份，英文为主。

## 需要你决定的一件事

**要不要就这样公开。**脱敏版意味着：

- 任何人能复现文章里的每一个数字，不需要 API key
- 没有人能查到某个具体产品或某位创始人赚了多少
- 想要带名字的字段，读者用自己的 key 跑 `fetch.py` 一小时就能拿到

代价是读者不能直接验证「Stan 那条冻住了」这类具体断言，只能自己去 trustmrr.com 上看。
文章里点名的几个产品都给了链接，这部分可以人工核对。

## 转公开的命令

```bash
gh repo edit mifanr/trustmrr-research --visibility public --accept-visibility-change-consequences
```

之后把 mifanr 仓库里文章的 `repo` 字段填成
`https://github.com/mifanr/trustmrr-research`，重新部署，
确认文章末尾的「数据与复现」区块渲染出来了。

## 可选

给 TrustMRR 发一条消息说明这份数据集的存在。曾发过展示许可请求，未回复。
脱敏版的暴露面比原始数据小得多，这一步不是必须的。
