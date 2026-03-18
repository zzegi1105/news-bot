import os
import requests
import re
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_1")

def fetch_macro_news():
    """🌍 글로벌 거시경제 뉴스"""
    query = "뉴욕증시+OR+국제유가+OR+환율+OR+미국+CPI+OR+연준+금리+OR+도트플롯+OR+국채수익률+OR+빅테크"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        response = requests.get(rss_url, timeout=15)
        items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
        news = []
        for item in items[:120]:
            title_match = re.search(r'<title>(.*?)</title>', item)
            link_match = re.search(r'<link>(.*?)</link>', item)
            if title_match and link_match:
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0]
                news.append({"title": title, "link": link_match.group(1), "type": "🌍 글로벌"})
        print(f"✅ 글로벌 거시 {len(news)}개")
        return news
    except:
        return []

def fetch_domestic_macro_news():
    """📈 국내 거시경제 뉴스 (금융정책, 환율, 금리, 주가지수 등)"""
    # 거시경제적 관점의 국내 뉴스만
    query = "한국은행+OR+금리+OR+환율+OR+코스피+OR+코스닥+OR+원화+OR+채권+OR+국고채+OR+소비자물가+OR+생산자물가+OR+수출입+OR+경상수지+OR+무역수지"
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        response = requests.get(rss_url, timeout=15)
        items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
        news = []
        for item in items[:120]:
            title_match = re.search(r'<title>(.*?)</title>', item)
            link_match = re.search(r'<link>(.*?)</link>', item)
            if title_match and link_match:
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0]
                # 기업 공시/개별 종목 뉴스 제외
                if all(x not in title for x in ["공시", "수주", "실적", "특징주", "계약"]):
                    news.append({"title": title, "link": link_match.group(1), "type": "📈 국내거시"})
        print(f"✅ 국내 거시 {len(news)}개")
        return news
    except:
        return []

def simple_filter(news_list, max_count=10):
    """상위 N개 선정"""
    filtered = []
    seen_titles = set()
    for item in news_list:
        if item['title'] not in seen_titles and len(filtered) < max_count:
            filtered.append(item)
            seen_titles.add(item['title'])
    return filtered

def send_to_discord(articles):
    if not articles or not DISCORD_WEBHOOK_URL:
        print("❌ 전송 불가")
        return
    
    title = f"📰 **[{datetime.now().strftime('%m/%d %H:%M')}] 거시경제 시그널 TOP {len(articles)}**"
    msg = f"{title}\n\n"
    
    for i, article in enumerate(articles, 1):
        msg += f"{i}. **{article['title']}** {article['type']}\n🔗 [기사보기](<{article['link']}>)\n\n"
        if len(msg) > 1800:
            break
    
    msg += "────────────"
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": msg}, timeout=10)
        print(f"✅ 전송: Status {response.status_code}")
    except Exception as e:
        print(f"❌ 전송실패: {e}")

# 실행
print(f"🚀 거시경제 봇 {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}")
global_news = fetch_macro_news()
domestic_macro = fetch_domestic_macro_news()

global_final = simple_filter(global_news, 12)
domestic_final = simple_filter(domestic_macro, 8)
final_news = global_final + domestic_final

print(f"📊 최종: 글로벌 {len(global_final)} + 국내거시 {len(domestic_final)} = {len(final_news)}개")
send_to_discord(final_news)
print("✅ 완료!")
