import os
import requests
import re
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_1")

def fetch_news(query, category, limit=150):
    """뉴스 수집 - 확실히 많이"""
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        response = requests.get(rss_url, timeout=20)
        items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
        news = []
        for item in items[:limit]:
            title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            link_match = re.search(r'<link>(.*?)</link>', item)
            if title_match and link_match:
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0].strip()
                link = link_match.group(1)
                news.append({"title": title, "link": link, "type": category})
        return news
    except:
        return []

def clean_news(news_list):
    """깔끔한 뉴스만 선별"""
    noise = ["카더라", "일까", "조짐", "추측", "설마", "전망"]
    clean = []
    seen = set()
    for item in news_list:
        title = item['title']
        if any(n in title for n in noise):
            continue
        # 제목 해시로 중복제거
        title_hash = hash(title[:50])
        if title_hash not in seen:
            clean.append(item)
            seen.add(title_hash)
    return clean

def get_macro_news():
    """세계거시경제 10개"""
    queries = [
        "뉴욕증시+OR+나스닥+OR+S&P500",
        "연준+OR+금리+OR+CPI+OR+도트플롯", 
        "국제유가+OR+WTI+OR+브렌트",
        "달러인덱스+OR+환율+OR+엔화"
    ]
    all_news = []
    for q in queries:
        all_news.extend(fetch_news(q, "🌍 세계거시", 50))
    cleaned = clean_news(all_news)
    return cleaned[:10]

def get_domestic_macro():
    """국내거시경제 10개"""
    queries = [
        "한국은행+OR+한은+OR+금리결정",
        "코스피+OR+코스닥+지수",
        "소비자물가+OR+생산자물가+OR+PPI",
        "원달러+OR+환율+OR+무역수지"
    ]
    all_news = []
    for q in queries:
        all_news.extend(fetch_news(q, "📈 국내거시", 50))
    cleaned = clean_news(all_news)
    return cleaned[:10]

def send_to_discord(news_list):
    """디스코드 전송"""
    if not news_list or not DISCORD_WEBHOOK_URL:
        print("❌ 전송불가")
        return
    
    title = f"📰 **[{datetime.now().strftime('%m/%d %H:%M')}] 거시경제 TOP 20**"
    msg = f"{title}\n\n**🌍 세계거시경제 (10)**\n"
    
    # 세계거시 1-10
    world_news = [n for n in news_list if n['type'] == "🌍 세계거시"][:10]
    for i, article in enumerate(world_news, 1):
        msg += f"{i}. **{article['title']}**\n🔗 {article['link']}\n\n"
    
    msg += "**📈 국내거시경제 (10)**\n"
    # 국내거시 11-20
    domestic_news = [n for n in news_list if n['type'] == "📈 국내거시"][:10]
    for i, article in enumerate(domestic_news, 11):
        msg += f"{i}. **{article['title']}**\n🔗 {article['link']}\n\n"
    
    msg += "────────────"
    
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": msg[:1900]}, timeout=10)
        print(f"✅ 전송완료: {resp.status_code}")
    except Exception as e:
        print(f"❌ 전송오류: {e}")

# ===== 실행 =====
print(f"🚀 거시경제봇 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

world_macro = get_macro_news()
domestic_macro = get_domestic_macro()
all_macro = world_macro + domestic_macro

print(f"📊 세계거시:{len(world_macro)} + 국내거시:{len(domestic_macro)} = 총{len(all_macro)}개")
send_to_discord(all_macro)
print("✅ 완료!")
