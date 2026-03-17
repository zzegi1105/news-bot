import requests
import re
from datetime import datetime

# 💡 실제 주소 대신 '금고 열쇠'를 꺼내오도록 수정
DISCORD_WEBHOOK_URLS = [
    os.getenv("DISCORDJI"),
    os.getenv("")
]

def fetch_news(mode):
    if mode == "MORNING":
        query = "뉴욕증시+OR+국제유가+OR+환율+OR+미국+CPI+OR+연준+금리"
        title_prefix = f"🌍 **[{datetime.now().strftime('%m/%d')}] 글로벌 매크로 시그널 (오전)**"
    else:
        query = "공시+OR+수주+OR+분기실적+OR+장마감+특징주+OR+공급계약+체결"
        title_prefix = f"📊 **[{datetime.now().strftime('%m/%d')}] 국내 시장 핵심 이슈 (오후)**"
        
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
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "포착", "전망은"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "달러", "금리", "상승", "하락", 
                    "공시", "체결", "실적", "종가", "공급", "계약", "특징주", "상한가"]
    filtered = []
    seen_keyword_sets = []
    for item in news_list:
        title = item['title']
        has_noise = any(word in title for word in noise_words)
        has_signal = any(word in title for word in signal_words)
        if has_signal or not has_noise:
            if not is_duplicate_issue(title, seen_keyword_sets):
                filtered.append(item)
                seen_keyword_sets.append(get_core_keywords(title))
        if len(filtered) >= 20: break
    return filtered

def send_to_discord(articles, title_prefix):
    if not articles:
        print("전송할 뉴스가 없습니다.")
        return

    messages = []
    current_message = f"{title_prefix}\n\n"
    
    for i, article in enumerate(articles, 1):
        line = f"{i}. **{article['title']}**\n🔗 [기사보기](<{article['link']}>)\n\n"
        if len(current_message + line) > 1900:
            messages.append(current_message)
            current_message = ""
        current_message += line
    
    messages.append(current_message + "------------- ")

    # 🔗 [수정됨] 등록된 모든 웹후크로 루프를 돌며 전송합니다.
    for webhook_url in DISCORD_WEBHOOK_URLS:
        try:
            for msg in messages:
                requests.post(webhook_url, json={"content": msg})
            print(f"웹후크 전송 성공: {webhook_url[:30]}...")
        except Exception as e:
            print(f"전송 실패: {webhook_url[:30]}... 오류: {e}")

# --- 실행 구간 ---
current_hour = datetime.now().hour
current_mode = "MORNING" if current_hour < 12 else "AFTERNOON"

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {current_mode} 뉴스 수집 중...")
news_data, prefix = fetch_news(current_mode)
final_news = filter_signals(news_data)
send_to_discord(final_news, prefix)
