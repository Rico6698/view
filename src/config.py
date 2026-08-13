"""配置模块"""

PRICE_THRESHOLD = 5.0

POSITIVE_KEYWORDS = [
    "利好", "大涨", "涨停", "增持", "回购", "中标", "签订合同", "业绩预增",
    "业绩增长", "扭亏为盈", "分红", "送转", "重组", "并购", "获批", "专利",
    "突破", "订单", "合作", "超预期", "利好公告", "重大合同", "股东增持",
    "机构买入", "评级买入", "推荐", "高景气", "涨价", "提价", "扩产",
    "产能释放", "新产品", "大订单", "预盈", "预增", "上修",
]

POSITIVE_TITLES = [
    "净利", "净利润", "营收增长", "预增", "预盈", "增持", "回购", "中标",
    "合同", "合作", "重组", "收购", "注入", "分红", "高送转", "获批",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://finance.eastmoney.com/",
}

TIMEOUT = 15

OUTPUT_JSON = "data/latest_result.json"
OUTPUT_MD = "data/latest_result.md"
OUTPUT_LOG = "data/crawler.log"
