import os
import requests
import re
from datetime import datetime

KST = timezone(timedelta(hours=9))

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_1")  # 단일 변수로 변경

def fetch_news(mode):
    if mode == "MORNING":
        query = "뉴욕증시+OR+국제유가+OR+환율+OR+미국+CPI+OR+연준+금리"
        title_prefix = f"🌍 **[{datetime.now(KST).strftime('%m/%d')}] 글로벌 매크로 시그널 (오전)**"
    else:
        query = "공시+OR+수주+OR+분기실적+OR+장마감+OR+특징주+OR+공급계약+체결"
        title_prefix = f"📊 **[{datetime.now(KST).strftime('%m/%d')}] 국내 시장 핵심 이슈 (오후)**"
        
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        response = requests.get(rss_url, timeout=15)
        xml_text = response.text
        items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
        
        collected_news = []
        for item in items:
            title_match = re.search(r'<title>(.*?)</title>', item)
            link_match = re.search(r'<link>(.*?)</link>', item)
            
            if title_match and link_match:
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0]
                link = link_match.group(1)
                collected_news.append({"title": title, "link": link})
            
            if len(collected_news) >= 300: break 
            
        return collected_news, title_prefix
    except Exception as e:
        print(f"뉴스 수집 중 오류: {e}")
        return [], ""

def get_core_keywords(text):
    words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text)
    stop_words = ['오늘', '내일', '뉴스', '기사', '게시판', '분석', '이유', '속보']
    return set([w for w in words if w not in stop_words])

def is_duplicate_issue(new_title, seen_keyword_sets):
    new_keywords = get_core_keywords(new_title)
    if not new_keywords: return True
    for existing_keywords in seen_keyword_sets:
        common = new_keywords.intersection(existing_keywords)
        if len(common) >= 3 or (len(new_keywords) <= 4 and len(common) >= 2):
            return True
    return False

def filter_signals(news_list):
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "포착", "전망은", "특징주"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "달러", "금리", "상승", "하락", 
                    "공시", "체결", "실적", "종가", "공급", "계약", "특징주", "상한가"]
    filtered = []
    seen_keyword_sets = []
    for item in news_list:
        title = item['title']
        has_noise = any(word in title for word in noise_words)
        has_signal = any(word in title for word in signal_words)
        if has_signal and not has_noise and not is_duplicate_issue(title, seen_keyword_sets):
            filtered.append(item)
            seen_keyword_sets.append(get_core_keywords(title))
        if len(filtered) >= 20: break
    return filtered

def send_to_discord(articles, title_prefix):
    if not articles:
        print("전송할 뉴스가 없습니다.")
        return

    # 🔍 웹훅 URL 안전성 검사
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_1 환경변수가 설정되지 않았습니다!")
        return

    messages = []
    current_message = f"{title_prefix}\n\n"
    
    for i, article in enumerate(articles, 1):
        line = f"{i}. **{article['title']}**\n🔗 {article['link']}\n\n"
        if len(current_message + line) > 1900:
            messages.append(current_message)
            current_message = f"{i}. **{article['title']}**\n🔗 {article['link']}\n\n"
        else:
            current_message += line
    
    messages.append(current_message + "-------------")

    # 안전한 웹훅 전송
    try:
        for i, msg in enumerate(messages, 1):
            response = requests.post(DISCORD_WEBHOOK_URL, json={"content": msg}, timeout=10)
            print(f"메시지 {i} 전송: {response.status_code}")
            if response.status_code not in [200, 204]:
                print(f"❌ 웹훅 오류: {response.text}")
                return
        print("✅ 모든 메시지 전송 성공!")
    except Exception as e:
        print(f"❌ 웹훅 전송 실패: {e}")

# --- 실행 구간 (테스트 + 실제 모두 동작) ---
now_kst = datetime.now(KST)
current_hour = now_kst.hour

print(f"[{now_kst.strftime('%Y-%m-%d %H:%M:%S')}] 실행 시작 (KST)...")
print(f"DISCORD_WEBHOOK_1 설정됨: {'O' if DISCORD_WEBHOOK_URL else 'X'}")

# 테스트용 + 실제 운영 모두 동작
if current_hour == 7 or True:  # True로 설정하여 언제나 실행 (테스트 후 False로 변경)
    print(f"[{now_kst.strftime('%Y-%m-%d %H:%M:%S')}] 뉴스 수집 중...")
    
    world_news, _ = fetch_news("MORNING")
    domestic_news, _ = fetch_news("AFTERNOON")
    
    combined = filter_signals(world_news)[:10] + filter_signals(domestic_news)[:10]
    combined_prefix = f"📰 **[{now_kst.strftime('%m/%d %H시')}] 세계+국내 매크로 Top20**"
    
    send_to_discord(combined, combined_prefix)
else:
    print(f"[{now_kst.strftime('%Y-%m-%d %H:%M')}] 오전 7시 외 실행 스킵")
