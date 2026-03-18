import os
import requests
import re
from datetime import datetime

# 설정 확인
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_1")
print(f"🚀 뉴스봇 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}")
print(f"🔗 웹후크: {'✅' if DISCORD_WEBHOOK_URL else '❌'}")

def fetch_news(query, news_type, max_items=100):
    """뉴스 RSS 수집"""
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        resp = requests.get(rss_url, timeout=15)
        items = re.findall(r'<item>(.*?)</item>', resp.text, re.DOTALL)
        news = []
        for item in items[:max_items]:
            title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            link_match = re.search(r'<link>(.*?)</link>', item)
            if title_match and link_match:
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0].strip()
                link = link_match.group(1)
                news.append({"title": title, "link": link, "type": news_type})
        print(f"✅ {news_type}: {len(news)}개 수집")
        return news
    except Exception as e:
        print(f"❌ {news_type} 오류: {e}")
        return []

def filter_news(news_list, max_count=10):
    """중복/노이즈 제거 + 상위 N개 선정"""
    noise_words = ["카더라", "일까", "조짐", "추측", "전망", "?", "특징주"]
    filtered = []
    seen_keywords = []
    
    for item in news_list:
        title = item['title']
        # 노이즈 제거
        if any(noise in title for noise in noise_words):
            continue
        # 중복 제거 (키워드 3개 이상 겹치면 제외)
        keywords = re.findall(r'[가-힣a-zA-Z0-9]{2,}', title)
        keywords = [w for w in keywords if w not in ['오늘', '내일', '뉴스', '속보']]
        
        is_duplicate = False
        for existing in seen_keywords:
            common = set(keywords) & set(existing)
            if len(common) >= 3:
                is_duplicate = True
                break
        if not is_duplicate and len(filtered) < max_count:
            filtered.append(item)
            seen_keywords.append(keywords)
    
    return filtered

def send_discord(articles):
    """디스코드 전송"""
    if not articles or not DISCORD_WEBHOOK_URL:
        print("❌ 전송 불가: 뉴스없음 또는 웹후크없음")
        return
    
    # 제목
    title = f"📰 **[{datetime.now().strftime('%m/%d %H:%M')}] 거시경제 TOP {len(articles)}**"
    message = f"{title}\n\n"
    
    # 뉴스 목록
    for i, article in enumerate(articles, 1):
        line = f"{i}. **{article['title']}** {article['type']}\n🔗 [기사보기](<{article['link']}>)\n\n"
        if len(message + line) < 1900:
            message += line
        else:
            break
    
    message += "────────────"
    
    # 전송
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=10)
        print(f"✅ 전송완료: Status={resp.status_code}")
    except Exception as e:
        print(f"❌ 전송실패: {e}")

# ===== 메인 실행 =====
print("📡 1. 글로벌 거시경제 수집")
global_news = fetch_news("뉴욕증시+OR+국제유가+OR+환율+OR+연준+OR+금리+OR+CPI+OR+도트플롯", "🌍 글로벌", 120)

print("📡 2. 국내 거시경제 수집") 
domestic_news = fetch_news("한국은행+OR+코스피+OR+코스닥+OR+원화+OR+환율+OR+소비자물가+OR+무역수지+OR+국고채", "📈 국내거시", 120)

# 필터링 (각각 10개)
print("🔍 3. 필터링")
global_final = filter_news(global_news, 10)
domestic_final = filter_news(domestic_news, 10)
final_news = global_final + domestic_final

print(f"📊 4. 최종선정: 글로벌{len(global_final)}+국내{len(domestic_final)}={len(final_news)}개")

# 전송
send_discord(final_news)
print("🎉 완료!")
