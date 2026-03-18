import os
import requests
import re
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_1")

def fetch_macro_news():
    query = "뉴욕증시+OR+국제유가+OR+환율+OR+미국+CPI+OR+연준+금리"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        response = requests.get(rss_url, timeout=15)
        xml_text = response.text
        items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
        macro_news = []
        for item in items:
            title_match = re.search(r'<title>(.*?)</title>', item)
            link_match = re.search(r'<link>(.*?)</link>', item)
            if title_match and link_match:
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0]
                link = link_match.group(1)
                macro_news.append({"title": title, "link": link, "type": "🌍 거시경제"})
            if len(macro_news) >= 150: break
        print(f"✅ 거시경제 뉴스 {len(macro_news)}개 수집")
        return macro_news
    except Exception as e:
        print(f"❌ 거시경제 뉴스 수집 오류: {e}")
        return []

def fetch_domestic_news():
    query = "공시+OR+수주+OR+분기실적+OR+장마감+특징주+OR+공급계약+체결"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        response = requests.get(rss_url, timeout=15)
        xml_text = response.text
        items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
        domestic_news = []
        for item in items:
            title_match = re.search(r'<title>(.*?)</title>', item)
            link_match = re.search(r'<link>(.*?)</link>', item)
            if title_match and link_match:
                title
