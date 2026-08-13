"""主入口：抓取低价股 + 多源利好新闻筛选"""

import json
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from config import (
    OUTPUT_JSON,
    OUTPUT_LOG,
    OUTPUT_MD,
    PRICE_THRESHOLD,
)
from eastmoney import fetch_low_price_stocks
from news import extract_stock_codes, fetch_all_news, is_positive

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_LOG, encoding="utf-8"),
    ],
)
log = logging.getLogger("crawler")


def main() -> int:
    log.info("=== 开始抓取 ===")

    low_stocks = fetch_low_price_stocks()
    log.info(f"5 元以下股票数量: {len(low_stocks)}")
    low_by_code = {s["code"]: s for s in low_stocks}
    low_by_name = {s["name"]: s for s in low_stocks}

    news_items = fetch_all_news()
    log.info(f"抓取新闻总数: {len(news_items)}")

    def match_stocks(text: str, title: str) -> list:
        """优先匹配股票代码，再匹配股票名称"""
        codes = extract_stock_codes(text)
        related = [low_by_code[c] for c in codes if c in low_by_code]
        if related:
            return related
        for name, s in low_by_name.items():
            if name and name in title:
                related.append(s)
        return related

    matched = []
    for item in news_items:
        title = item.title or ""
        summary = item.summary or ""
        content = item.content or ""
        if not is_positive(title, summary):
            continue
        text = f"{title} {summary} {content}"
        related = match_stocks(text, f"{title} {summary}")
        if not related and item.extra_codes:
            related = [low_by_code[c] for c in item.extra_codes if c in low_by_code]
        # 若没有代码，保留标题含"利好/预增"等强信号的通用新闻
        if not related and any(
            kw in f"{title}{summary}" for kw in ("利好", "预增", "业绩预增", "增持", "回购")
        ):
            related = [{"code": "N/A", "name": "通用利好", "price": None}]
        if not related:
            continue
        matched.append(
            {
                "news": item.to_dict(),
                "related_stocks": related,
            }
        )

    # 去重（按标题）
    seen = set()
    unique = []
    for m in matched:
        key = m["news"]["title"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(m)

    result = {
        "crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "price_threshold": PRICE_THRESHOLD,
        "low_stock_count": len(low_stocks),
        "news_count": len(news_items),
        "match_count": len(unique),
        "matches": unique,
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    write_markdown(result)
    log.info(f"命中利好新闻: {len(unique)} 条 -> 已写入 {OUTPUT_JSON}")
    return 0


def write_markdown(result: dict) -> None:
    lines = [
        f"# 低价股利好新闻报告",
        f"",
        f"- 抓取时间: {result['crawled_at']}",
        f"- 5 元以下股票: {result['low_stock_count']} 只",
        f"- 抓取新闻: {result['news_count']} 条",
        f"- 命中利好: {result['match_count']} 条",
        f"",
        f"## 利好新闻",
        f"",
    ]
    for m in result["matches"]:
        n = m["news"]
        stocks = "、".join(f"{s['name']}({s['code']})" for s in m["related_stocks"])
        lines.append(f"### {n['title']}")
        lines.append(f"- 来源: {n['source']} | 时间: {n['time']}")
        if stocks:
            lines.append(f"- 相关低价股: {stocks}")
        if n["summary"]:
            lines.append(f"- 摘要: {n['summary'][:200]}")
        if n["url"]:
            lines.append(f"- 链接: {n['url']}")
        lines.append("")
    if not result["matches"]:
        lines.append("暂无命中。")
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
