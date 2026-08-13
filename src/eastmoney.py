"""行情抓取：优先东方财富，失败自动回退新浪，筛出价格 < 5 元的股票"""

import time
import requests

from config import HEADERS, PRICE_THRESHOLD, TIMEOUT

CLIST_URL = (
    "https://push2.eastmoney.com/api/qt/clist/get"
    "?pn={page}&pz={size}&po=1&np=1&fltt=2&invt=2"
    "&fid=f2&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
    "&fields=f2,f3,f12,f14,f15,f16,f17,f18,f20"
)

SINA_URL = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "Market_Center.getHQNodeData?page={page}&num={size}&sort=symbol&asc=1&node=hs_a"
)


def fetch_page_with_retry(url: str, headers: dict, retries: int = 3) -> requests.Response:
    last_exc = None
    for i in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(1.5 * (i + 1))
    raise last_exc


def _eastmoney_stocks(page_count: int, size: int) -> list:
    stocks = []
    for page in range(1, page_count + 1):
        resp = fetch_page_with_retry(CLIST_URL.format(page=page, size=size), HEADERS)
        data = resp.json()
        diff = (data.get("data") or {}).get("diff") or []
        if not diff:
            break
        stocks.extend(diff)
        time.sleep(0.4)
    return stocks


def _sina_stocks(page_count: int, size: int) -> list:
    headers = {
        **HEADERS,
        "Referer": "https://finance.sina.com.cn/",
        "Accept-Encoding": "gzip, deflate",
    }
    stocks = []
    for page in range(1, page_count + 1):
        resp = fetch_page_with_retry(SINA_URL.format(page=page, size=size), headers)
        data = resp.json()
        if not data:
            break
        stocks.extend(data)
        time.sleep(0.4)
    return stocks


def _to_low_stock_list(stocks: list, source: str) -> list:
    low_stocks = []
    for s in stocks:
        if source == "eastmoney":
            price = s.get("f2")
            code, name, market = s.get("f12"), s.get("f14"), s.get("f13")
            change_pct, total_value = s.get("f3"), s.get("f20")
        else:  # sina
            price = s.get("trade")
            code, name = s.get("code"), s.get("name")
            market = s.get("symbol", "").split(s.get("code", ""))[0] if s.get("symbol") else None
            change_pct, total_value = s.get("changepercent"), s.get("marketvalue")
        if not code or not name:
            continue
        try:
            price = float(price)
        except (TypeError, ValueError):
            continue
        if 0 < price < PRICE_THRESHOLD:
            low_stocks.append(
                {
                    "code": str(code),
                    "name": str(name),
                    "price": price,
                    "change_pct": change_pct,
                    "market": market,
                    "total_value": total_value,
                }
            )
    return low_stocks


def fetch_low_price_stocks(page_count: int = 30, size: int = 200) -> list:
    """抓取全部 A 股，筛出价格 < PRICE_THRESHOLD 的股票"""
    try:
        stocks = _eastmoney_stocks(page_count, size)
        if stocks:
            return _to_low_stock_list(stocks, "eastmoney")
    except requests.RequestException as exc:
        print(f"[行情] 东方财富接口失败，回退新浪: {exc}")

    try:
        stocks = _sina_stocks(page_count, size)
        return _to_low_stock_list(stocks, "sina")
    except requests.RequestException as exc:
        print(f"[行情] 新浪接口失败: {exc}")
    return []


if __name__ == "__main__":
    result = fetch_low_price_stocks(page_count=5)
    print(f"5元以下股票数量: {len(result)}")
    for item in result[:10]:
        print(item)
