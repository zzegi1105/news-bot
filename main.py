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

# 2. 환경 변수 (DISCORD_WEBHOOK_2는 완전히 제거됨)
DISCORD_WEBHOOK_1 = os.getenv("DISCORD_WEBHOOK_1")

def fetch_news(mode, limit=15):
    """뉴스 수집 및 링크 추출"""
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
            t = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
            l = re.search(r"<link>(.*?)</link>", item, re.DOTALL)

            if t:
                # 제목 정제 및 Markdown 예약어 처리
                title = t.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0].strip()
                title = title.replace("[", "【").replace("]", "】")
                link = l.group(1) if l else None
                
                # 구글 뉴스 미리보기 파라미터 필터링
                is_invalid = link and any(p in link for p in ["?hl=ko", "preview", "amp;"])

                if len(title) > 3:
                    collected_news.append({
                        "title": title,
                        "link": link if link and not is_invalid else None,
                    })
            if len(collected_news) >= limit: break
        return collected_news, title_prefix
    except Exception as e:
        print(f"❌ 뉴스 수집 오류: {e}")
        return [], ""

def filter_news(news_list):
    """지표 중심 필터링"""
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "특징주", "급등주"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "금리", "상승", "하락", "실적"]
    
    filtered = []
    for item in news_list:
        title = item["title"]
        if len(title) < 8: continue
        if any(w in title for w in signal_words) or not any(w in title for w in noise_words):
            filtered.append(item)
        if len(filtered) >= 10: break
    return filtered

def send_to_discord(articles, title_prefix):
    """[미리보기 삭제 핵심] <link> 형식을 적용하여 Embed 차단"""
    if not articles or not DISCORD_WEBHOOK_1:
        print("📭 전송 대상이 없거나 Webhook 설정이 누락되었습니다.")
        return

    messages = []
    current_message = f"{title_prefix}\n\n"
    
    for i, article in enumerate(articles, 1):
        title = article["title"]
        link = article.get("link")

        # [수정] < > 괄호로 링크를 감싸면 디스코드 미리보기 박스가 생기지 않습니다.
        if link:
            line = f"{i}. [{title}](<{link}>)\n\n"
        else:
            line = f"{i}. {title}\n\n"

        if len((current_message + line).encode("utf-8")) > 1800:
            messages.append(current_message)
            current_message = f"{title_prefix}\n\n{line}"
        else:
            current_message += line

    # 마지막 남은 메시지 추가
    if current_message.strip():
        messages.append(current_message)

    # 실제 전송
    for msg in messages:
        try:
            res = requests.post(DISCORD_WEBHOOK_1, json={"content": msg}, timeout=10)
            if res.status_code not in [200, 204]:
                print(f"⚠️ 전송 실패: {res.status_code}")
        except Exception as e:
            print(f"❌ 네트워크 오류: {e}")

def main():
    print(f"🚀 뉴스봇 작동 시작 (KST: {now_kst.strftime('%H:%M')})")
    current_hour = now_kst.hour
    
    # GitHub Actions 환경 또는 정기 실행 시간(07시) 확인
    is_triggered = os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("GITHUB_RUN_ID") or current_hour == 7

    if is_triggered:
        for mode in ["WORLD", "DOMESTIC"]:
            raw_news, prefix = fetch_news(mode)
            filtered = filter_news(raw_news)
            send_to_discord(filtered, prefix)
    else:
        print(f"⏭️ 실행 시간 아님 (현재 {current_hour}시)")

if __name__ == "__main__":
    main()
