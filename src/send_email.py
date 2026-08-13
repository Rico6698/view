"""send_email.py - 读取 data/latest_result.json，通过 Resend API 发送 HTML 邮件"""

import json
import os
import sys

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_JSON = os.path.join(PROJECT_DIR, "data", "latest_result.json")

RESEND_URL = "https://api.resend.com/emails"
FROM_ADDR = "低价股利好新闻 <onboarding@resend.dev>"


def generate_html(data):
    matches = data.get("matches", [])
    crawled_at = data.get("crawled_at", "")
    low_count = data.get("low_stock_count", 0)
    match_count = data.get("match_count", 0)

    if not matches:
        return f"""<html><body style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;max-width:600px;margin:0 auto;padding:16px;background:#f5f5f7">
<h2 style="color:#1a1a1a;text-align:center;margin-bottom:4px">📈 低价股利好新闻</h2>
<p style="text-align:center;color:#8c8c8c;font-size:13px;margin-bottom:16px">{crawled_at} · 暂无命中</p>
<div style="background:#fff;border-radius:12px;padding:24px;margin-bottom:10px;text-align:center;color:#8c8c8c">
今日暂无 5 元以下股票的利好新闻命中。
</div>
<p style="text-align:center;font-size:11px;color:#8c8c8c;margin-top:16px;line-height:1.6">本邮件由 GitHub Actions 自动爬取生成，仅供信息参考，不构成任何投资建议。</p>
</body></html>"""

    cards = ""
    for m in matches:
        n = m.get("news", {})
        stocks = m.get("related_stocks", [])
        stock_tags = "".join(
            f'<span style="background:#e6f4ff;color:#1677ff;padding:2px 8px;border-radius:4px;font-size:11px;margin:2px;display:inline-block">{s.get("name","")} {s.get("code","")}</span>'
            for s in stocks
        )
        source_badge = f'<span style="background:#f5f5f5;color:#595959;padding:2px 8px;border-radius:4px;font-size:11px">{n.get("source","")}</span>'
        time_text = n.get("time", "")
        summary = n.get("summary", "") or ""
        url = n.get("url", "")
        cards += f"""
        <div style="background:#fff;border-radius:12px;padding:16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">
          <div style="font-size:15px;font-weight:600;margin-bottom:6px">{n.get("title","")}</div>
          <div style="margin-bottom:8px">{source_badge} <span style="color:#8c8c8c;font-size:11px">{time_text}</span></div>
          <div style="margin-bottom:8px">{stock_tags}</div>
          <div style="color:#595959;font-size:13px;line-height:1.5;margin-bottom:6px">{summary[:200]}</div>
          <div><a href="{url}" style="color:#1677ff;font-size:12px">阅读原文 →</a></div>
        </div>"""

    return f"""<html><body style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;max-width:600px;margin:0 auto;padding:16px;background:#f5f5f7">
<h2 style="color:#1a1a1a;text-align:center;margin-bottom:4px">📈 低价股利好新闻</h2>
<p style="text-align:center;color:#8c8c8c;font-size:13px;margin-bottom:16px">{crawled_at} · 5元以下 {low_count} 只 · 命中 {match_count} 条</p>
{cards}
<p style="text-align:center;font-size:11px;color:#8c8c8c;margin-top:16px;line-height:1.6">本邮件由 GitHub Actions 自动爬取生成，仅供信息参考，不构成任何投资建议。</p>
</body></html>"""


def send_email(html_content, subject, to_addr):
    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        print("!!! RESEND_API_KEY 环境变量未设置，跳过发送")
        return False
    try:
        resp = requests.post(
            RESEND_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": FROM_ADDR,
                "to": [to_addr],
                "subject": subject,
                "html": html_content,
            },
            timeout=30,
        )
    except Exception as exc:
        print(f"!!! Resend 请求异常: {exc}")
        return False
    if resp.status_code >= 400:
        print(f"!!! Resend 发送失败: {resp.status_code} {resp.text}")
        return False
    try:
        rid = resp.json().get("id", "")
    except Exception:
        rid = ""
    print(f">>> 邮件已发送至 {to_addr} (id={rid})")
    return True


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_path = OUTPUT_JSON

    if not os.path.exists(results_path):
        print(f"!!! 结果文件不存在: {results_path}")
        return 1

    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)

    html = generate_html(data)
    match_count = data.get("match_count", 0)
    crawled_at = data.get("crawled_at", "")
    subject = f"低价股利好新闻 {crawled_at} | 命中 {match_count} 条"

    to_addr = os.environ.get("MAIL_TO_ADDR", "3405947985@qq.com")

    ok = send_email(html, subject, to_addr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
