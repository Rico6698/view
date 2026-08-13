# 低价股利好新闻爬虫

自动爬取**东方财富、新浪财经、同花顺**三大财经数据源，筛选出**股价低于 5 元**的股票相关**利好新闻**。

## 功能

- 从东方财富行情接口抓取全部 A 股，筛出价格 < 5 元的股票
- 抓取三源最新财经新闻 / 公告 / 快讯
- 关键词匹配利好新闻（增持、回购、预增、中标、重组等）
- 将新闻与 5 元以下股票代码关联
- 输出 JSON 与 Markdown 报告
- 定时运行：每天 10:00 与 17:00（GitHub Actions cron）

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 输出

- `data/latest_result.json` — 结构化结果
- `data/latest_result.md` — 人类可读报告
- `data/crawler.log` — 运行日志

## 定时任务

使用 cron-job.org 外部调度触发 `.github/workflows/cron.yml` 的 `workflow_dispatch`，每天 10:00 与 17:00（Asia/Shanghai）自动运行并提交结果到仓库。
