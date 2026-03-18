import os
import requests
import re
import sys
from datetime import datetime, timedelta, timezone

# 오류 방지를 위한 안전장치
try:
    KST = timezone(timedelta(hours=9))
except:
    from datetime import timezone
    KST = timezone(timedelta(hours=9))

# 환경변수 안전 확인
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_1")
print(f"DISCORD_WEBHOOK_1 설정됨: {'O' if DISCORD_WEBHOOK_URL else 'X'}")

def safe_request(url, timeout=15):
    """안전한 HTTP 요청"""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"HTTP 요청 실패 {url}: {e}")
        return None

def fetch_news(mode):
    """뉴스 수집"""
    print(f"수집 중: {mode} 모드")
    
    if mode == "MORNING":
        query = "뉴욕증시+OR+국제유가+OR+환율+OR+미국+CPI+OR+연준+금리"
    else:
        query = "공시+OR+수주+OR+분기실적+OR+장마감+OR+특징주+OR+공급계약+체결"
    
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    
    xml_text = safe_request(rss_url)
    if not xml_text:
        return [], ""
    
    items = re.findall(r'<item>(.*?)</item>', xml_text, re.DOTALL)
    print(f"RSS 아이템 수: {len(items)}")
    
    collected_news = []
    for item in items[:50]:  # 300 → 50으로 제한
        title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
        link_match = re.search(r'<link>(.*?)</link>', item)
        
        if title_match and link_match:
            title = (title_match.group(1)
                    .replace("<![CDATA[", "")
                    .replace("]]>", "")
                    .split(" - ")[0]
                    .strip())
            link = link_match.group(1).strip()
            
            if title and link:
                collected_news.append({"title": title, "link": link})
    
    title_prefix = f"**[{datetime.now(KST).strftime('%m/%d')}] {'글로벌' if mode=='MORNING' else '국내'} 뉴스**"
    return collected_news, title_prefix

def filter_signals(news_list, max_count=10):
    """뉴스 필터링"""
    if not news_list:
        return []
    
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "포착", "전망은", "특징주"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "달러", "금리", "상승", "하락", 
                    "공시", "체결", "실적", "종가", "공급", "계약", "특징주", "상한가"]
    
    filtered = []
    for item in news_list:
        title = item['title']
        
        # 노이즈 확인
        has_noise = any(word in title for word in noise_words)
        # 시그널 확인
        has_signal = any(word in title for word in signal_words)
        
        if has_signal and not has_noise:
            filtered.append(item)
            if len(filtered) >= max_count:
                break
    
    print(f"필터링 결과: {len(filtered)}개 뉴스")
    return filtered

def send_to_discord(articles, title_prefix):
    """디스코드 전송"""
    if not articles:
        print("전송할 뉴스가 없습니다.")
        return True
    
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_1이 설정되지 않았습니다!")
        return False

    message = f"{title_prefix}\n\n"
    for i, article in enumerate(articles, 1):
        message += f"{i}. **{article['title']}**\n🔗 {article['link']}\n\n"
    message += "-------------"

    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL, 
            json={"content": message[:2000]},  # Discord 제한
            timeout=10
        )
        print(f"웹훅 응답: {response.status_code}")
        
        if response.status_code in [200, 204]:
            print("✅ 디스코드 전송 성공!")
            return True
        else:
            print(f"❌ 웹훅 실패: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 웹훅 전송 예외: {e}")
        return False

# === 메인 실행 ===
def main():
    print("=== 뉴스 봇 시작 ===")
    
    try:
        now_kst = datetime.now(KST)
        print(f"현재 시간: {now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}")
        
        # 뉴스 수집
        world_news, _ = fetch_news("MORNING")
        domestic_news, _ = fetch_news("AFTERNOON")
        
        # 필터링
        world_filtered = filter_signals(world_news, 10)
        domestic_filtered = filter_signals(domestic_news, 10)
        combined = world_filtered + domestic_filtered
        
        if not combined:
            print("필터링된 뉴스가 없습니다.")
            return
        
        # 전송
        prefix = f"📰 **[{now_kst.strftime('%m/%d %H시')}] 세계+국내 Top{len(combined)}**"
        success = send_to_discord(combined, prefix)
        
        if success:
            print("🎉 전체 프로세스 성공!")
        else:
            print("❌ 디스코드 전송 실패")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
