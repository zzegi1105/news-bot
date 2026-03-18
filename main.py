import os
import requests
import re
from datetime import datetime, timezone, timedelta

# 1. KST 시간 계산
def get_kst_now():
    utc_now = datetime.now(timezone.utc)
    kst_offset = timedelta(hours=9)
    return utc_now + kst_offset

now_kst = get_kst_now()

# 2. 환경 변수 (WEBHOOK_2 관련 변수 완전 삭제)
DISCORD_WEBHOOK_1 = os.getenv("DISCORD_WEBHOOK_1")

def fetch_news(mode, limit=15):
    """뉴스 수집 로직 (기존과 동일)"""
    if mode == "WORLD":
        query = "세계+경제+OR+미국+CPI+OR+연준+금리+OR+뉴욕증시+OR+국제유가+OR+환율"
        title_prefix = f"🌍 **[{now_kst.strftime('%m/%d %H:%M')}] 세계거시경제 TOP 10**"
    else:
        query = (
            "한국+경제+OR+한은+금리+OR+금융위원회+OR+소비자물가+OR+CPI+물가지수"
            "+OR+수출+OR+수입+OR+무역수지+OR+국제총생산+OR+GDP+성장률"
        )
        title_prefix = f"🇰🇷 **[{now_kst.strftime('%m/%d %H:%M')}] 국내거시경제 TOP 10**"

    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"

    try:
        response = requests.get(rss_url, timeout=15)
        response.raise_for_status()
        items = re.findall(r"<item>(.*?)</item>", response.text, re.DOTALL)

        collected_news = []
        for item in items:
            title_match = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
            link_match = re.search(r"<link>(.*?)</link>", item, re.DOTALL)

            if title_match:
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0].strip()
                link = link_match.group(1) if link_match else None
                if len(title) > 3:
                    collected_news.append({"title": title, "link": link})
            if len(collected_news) >= limit: break
        return collected_news, title_prefix
    except Exception as e:
        print(f"❌ 뉴스 파싱 오류: {e}")
        return [], ""

def filter_news(news_list):
    """기존 필터링 로직 유지"""
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "특징주", "급등주"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "금리", "상승", "하락", "실적"]
    
    filtered = []
    seen_keywords = []
    for item in news_list:
        title = item["title"]
        if len(title) < 10: continue
        if any(w in title for w in signal_words) or not any(w in title for w in noise_words):
            filtered.append(item)
        if len(filtered) >= 10: break
    return filtered

def send_to_discord(articles, title_prefix, webhook_url=None):
    """[핵심 수정] 기존 알림 성공 로직으로 복구"""
    if not articles:
        print("📭 전송할 뉴스가 없습니다.")
        return

    # 전송 대상 리스트화 (기존 성공 로직 구조)
    targets = []
    if webhook_url and webhook_url.strip():
        targets = [webhook_url]
    elif DISCORD_WEBHOOK_1:
        targets = [DISCORD_WEBHOOK_1]

    if not targets:
        print("❌ Discord Webhook URL이 설정되지 않았습니다.")
        return

    # 메시지 분할 생성
    current_message = f"{title_prefix}\n\n"
    messages = []
    for i, article in enumerate(articles, 1):
        line = f"{i}. {article['title']}\n\n"
        if len((current_message + line).encode("utf-8")) > 1800:
            messages.append(current_message)
            current_message = f"{title_prefix}\n\n{line}"
        else:
            current_message += line
    if current_message.strip():
        messages.append(current_message)

    # 루프를 통한 실제 전송 (기존 성공 방식)
    for target in targets:
        try:
            for msg in messages:
                requests.post(target, json={"content": msg}, timeout=10)
            print(f"✅ 전송 완료: {target[:30]}...")
        except Exception as e:
            print(f"❌ 전송 실패: {e}")

def main():
    print(f"🚀 뉴스봇 시작 (KST: {now_kst.strftime('%H:%M')})")
    current_hour = now_kst.hour

    # 1. 07시 정기 알림
    if current_hour == 7:
        world_news, world_pref = fetch_news("WORLD")
        dom_news, dom_pref = fetch_news("DOMESTIC")
        
        if DISCORD_WEBHOOK_1:
            send_to_discord(filter_news(world_news), world_pref, DISCORD_WEBHOOK_1)
            send_to_discord(filter_news(dom_news), dom_pref, DISCORD_WEBHOOK_1)
        return

    # 2. 수동 실행 (GitHub Actions용)
    if os.getenv("FORCE_RUN") == "true" or os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("GITHUB_RUN_ID"):
        world_news, world_pref = fetch_news("WORLD")
        dom_news, dom_pref = fetch_news("DOMESTIC")
        send_to_discord(filter_news(world_news), world_pref)
        send_to_discord(filter_news(dom_news), dom_pref)
        return

    print(f"⏭️ 실행 조건 아님 (현재 {current_hour}시)")

if __name__ == "__main__":
    main()
