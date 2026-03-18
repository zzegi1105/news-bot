import os
import sys
import requests
import re
from datetime import datetime

# 디스코드 웹후크 주소 (GitHub Secrets에서 가져옴)
DISCORD_WEBHOOK_URLS = [
    os.getenv("DISCORD_WEBHOOK_1")
]


def fetch_macro_news():
    """거시경제 뉴스 수집"""
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
            
            if len(macro_news) >= 150:
                break
        
        return macro_news
    except Exception as e:
        print(f"거시경제 뉴스 수집 오류: {e}")
        return []


def fetch_domestic_news():
    """국내경제 뉴스 수집"""
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
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0]
                link = link_match.group(1)
                domestic_news.append({"title": title, "link": link, "type": "📊 국내경제"})
            
            if len(domestic_news) >= 150:
                break
        
        return domestic_news
    except Exception as e:
        print(f"국내경제 뉴스 수집 오류: {e}")
        return []


def get_core_keywords(text):
    words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text)
    stop_words = ['오늘', '내일', '뉴스', '기사', '게시판', '분석', '이유', '속보']
    return set([w for w in words if w not in stop_words])


def is_duplicate_issue(new_title, seen_keyword_sets):
    new_keywords = get_core_keywords(new_title)
    if not new_keywords:
        return True
    for existing_keywords in seen_keyword_sets:
        common = new_keywords.intersection(existing_keywords)
        if len(common) >= 3 or (len(new_keywords) <= 4 and len(common) >= 2):
            return True
    return False


def filter_top_news(all_news):
    """총 20개 한정으로 최고 신호성 뉴스 선별"""
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "포착", "전망은"]
    signal_words = [
        "발표", "확정", "지표", "미국", "국제", "달러", "금리", "상승", "하락",
        "공시", "체결", "실적", "종가", "공급", "계약", "특징주", "상한가"
    ]
    
    filtered = []
    seen_keyword_sets = []
    
    for item in all_news:
        title = item['title']
        has_noise = any(word in title for word in noise_words)
        has_signal = any(word in title for word in signal_words)
        
        if has_signal or not has_noise:
            if not is_duplicate_issue(title, seen_keyword_sets):
                filtered.append(item)
                seen_keyword_sets.append(get_core_keywords(title))
        
        if len(filtered) >= 20:
            break
    
    return filtered


def send_to_discord(articles):
    if not articles:
        print("전송할 뉴스가 없습니다.")
        return

    title_prefix = f"📰 **[{datetime.now().strftime('%m/%d %H:%M')}] 종합 경제 뉴스 TOP {len(articles)}**"
    messages = []
    current_message = f"{title_prefix}\n\n"
    
    for i, article in enumerate(articles, 1):
        line = f"{i}. **{article['title']}** {article['type']}\n🔗 [기사보기](<{article['link']}>)\n\n"
        if len(current_message + line) > 1900:
            messages.append(current_message)
            current_message = f"{i}. **{article['title']}** {article['type']}\n🔗 [기사보기](<{article['link']}>)\n\n"
        else:
            current_message += line
    
    if current_message.strip():
        messages.append(current_message + "-------------")

    for webhook_url in DISCORD_WEBHOOK_URLS:
        if not webhook_url:
            continue
        try:
            for msg in messages:
                requests.post(webhook_url, json={"content": msg}, timeout=10)
            print(f"✅ 웹후크 전송 성공: {webhook_url[:30]}...")
        except Exception as e:
            print(f"❌ 전송 실패: {webhook_url[:30]}... 오류: {e}")


# --- 실행 구간 ---
if __name__ == "__main__":
    print(f"🚀 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}] 종합 경제 뉴스 봇 시작!")
    
    print("📥 거시경제 뉴스 수집 중...")
    macro_news = fetch_macro_news()
    
    print("📥 국내경제 뉴스 수집 중...")
    domestic_news = fetch_domestic_news()
    
    all_news = macro_news + domestic_news
    print(f"📊 총 {len(all_news)}개 기사 수집 완료")
    
    top_news = filter_top_news(all_news)
    print(f"🎯 TOP {len(top_news)}개 선별 완료")
    
    send_to_discord(top_news)
    print("✅ 모든 작업 완료!")
