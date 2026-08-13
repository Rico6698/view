"""新闻抓取：东方财富 + 新浪财经 + 同花顺"""

import json
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config import HEADERS, POSITIVE_KEYWORDS, TIMEOUT


def normalize_time(raw: str) -> str:
    """把各种时间格式归一化为 YYYY-MM-DD HH:MM:SS"""
    if not raw:
        return ""
    raw = str(raw).strip()
    now = datetime.now()
    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}", raw):
        return raw[:19]
    if re.match(r"^\d{2}-\d{2} \d{2}:\d{2}", raw):
        return f"{now.year}-{raw[:14]}"
    if re.match(r"^\d{2}:\d{2}$", raw):
        return now.strftime("%Y-%m-%d ") + raw
    return raw


def is_positive(title: str, summary: str = "") -> bool:
    """判断新闻是否属于利好"""
    text = f"{title} {summary}"
    return any(kw in text for kw in POSITIVE_KEYWORDS)


def extract_stock_codes(text: str) -> list:
    """从文本中提取 A 股代码（6 位数字）"""
    codes = set()
    for m in re.finditer(r"(?<!\d)([036]\d{5})(?!\d)", text):
        codes.add(m.group(1))
    return list(codes)


class NewsItem:
    def __init__(self, source, title, summary, url, time_str, content="", extra_codes=None):
        self.source = source
        self.title = title
        self.summary = summary
        self.url = url
        self.time = normalize_time(time_str)
        self.content = content
        self.extra_codes = extra_codes or []

    def to_dict(self):
        return {
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "time": self.time,
        }


class EastmoneyNews:
    """东方财富 - 全市场新闻/公告流"""

    NAME = "东方财富"

    def fetch(self) -> list:
        items = []
        urls = [
            "https://np-anotice-stock.eastmoney.com/api/security/ann"
            "?sr=-1&page_size=50&page_index=1&ann_type=A&client_source=web",
            "https://finance.eastmoney.com/a/cjdd.html",
        ]
        # 接口一：个股公告（JSON）
        try:
            resp = requests.get(
                urls[0],
                headers=HEADERS,
                timeout=TIMEOUT,
                params={"cb": "jQuery", "client_source": "web"},
            )
            text = resp.text.strip()
            text = re.sub(r"^[^(]*\((.*)\)[^)]*$", r"\1", text)
            data = json.loads(text)
            for ann in (data.get("data") or {}).get("list", []):
                stock_codes = []
                for c in ann.get("codes", []) or []:
                    if isinstance(c, dict) and c.get("stock_code"):
                        stock_codes.append(c["stock_code"])
                title = ann.get("title", "")
                content = ann.get("notice_content", "")
                items.append(
                    NewsItem(
                        self.NAME,
                        title,
                        content,
                        ann.get("art_code", ""),
                        ann.get("notice_date", ""),
                        content,
                        extra_codes=stock_codes,
                    )
                )
        except Exception as exc:
            print(f"[{self.NAME}] 公告接口失败: {exc}")

        # 接口二：财经导读页（HTML）
        try:
            resp = requests.get(urls[1], headers=HEADERS, timeout=TIMEOUT)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.select("div.liveList a, ul.newsList a, a[href*='eastmoney.com']"):
                title = a.get_text(" ", strip=True)
                href = a.get("href", "")
                if title and href:
                    items.append(
                        NewsItem(self.NAME, title, "", href, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
        except Exception as exc:
            print(f"[{self.NAME}] 导读页失败: {exc}")
        return items


class SinaNews:
    """新浪财经 - 滚动新闻"""

    NAME = "新浪财经"

    def fetch(self) -> list:
        items = []
        url = (
            "https://feed.mix.sina.com.cn/api/roll/get"
            "?pageid=153&lid=2516&num=80&page=1"
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            data = resp.json()
            for news in data.get("result", {}).get("data", []):
                items.append(
                    NewsItem(
                        self.NAME,
                        news.get("title", ""),
                        news.get("intro", ""),
                        news.get("url", ""),
                        news.get("ctime", ""),
                    )
                )
        except Exception as exc:
            print(f"[{self.NAME}] 滚动新闻失败: {exc}")

        # 备用：新浪 7x24
        try:
            resp = requests.get(
                "https://zhibo.sina.com.cn/api/zhibo/feed",
                headers=HEADERS,
                timeout=TIMEOUT,
                params={"page": 1, "page_size": 100, "zhibo_id": 152, "tag_id": 0, "dire": "f", "dpc": 1},
            )
            data = resp.json()
            for item in data.get("result", {}).get("data", {}).get("feed", {}).get("list", []):
                items.append(
                    NewsItem(
                        self.NAME,
                        item.get("rich_text", "")[:80],
                        item.get("rich_text", ""),
                        "",
                        item.get("create_time", ""),
                        item.get("rich_text", ""),
                    )
                )
        except Exception as exc:
            print(f"[{self.NAME}] 7x24 失败: {exc}")
        return items


class TonghuashunNews:
    """同花顺 - 财经新闻/快讯"""

    NAME = "同花顺"

    def fetch(self) -> list:
        items = []
        urls = [
            "https://news.10jqka.com.cn/tapp/news/push/stock/?page=1&tag=&track=website&pagesize=50",
            "https://news.10jqka.com.cn/tapp/news/push/notice/?page=1&tag=&track=website&pagesize=50",
        ]
        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                resp.encoding = "utf-8"
                data = resp.json()
                if isinstance(data, dict):
                    inner = data.get("data")
                    if isinstance(inner, dict):
                        news_list = inner.get("list", []) or []
                    elif isinstance(inner, list):
                        news_list = inner
                    else:
                        news_list = []
                elif isinstance(data, list):
                    news_list = data
                else:
                    news_list = []
                for news in news_list:
                    if not isinstance(news, dict):
                        continue
                    ctime = news.get("ctime") or news.get("time") or 0
                    items.append(
                        NewsItem(
                            self.NAME,
                            news.get("title", ""),
                            news.get("summary", ""),
                            news.get("appUrl", "") or news.get("url", ""),
                            datetime.fromtimestamp(int(ctime) / 1000)
                            if ctime
                            else "",
                            news.get("content", ""),
                        )
                    )
            except Exception as exc:
                print(f"[{self.NAME}] 请求失败 {url}: {exc}")
            time.sleep(0.5)
        return items


def fetch_all_news() -> list:
    """并行抓取三个源的全部新闻"""
    sources = [EastmoneyNews(), SinaNews(), TonghuashunNews()]
    items = []
    for src in sources:
        try:
            items.extend(src.fetch())
        except Exception as exc:
            print(f"[{src.NAME}] 抓取异常: {exc}")
    return items
