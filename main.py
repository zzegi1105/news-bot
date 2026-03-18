import os
import requests
import re
from datetime import datetime, timezone, timedelta

# 1. KST 시간 계산 (Python 3.12+ 대응)
def get_kst_now():
    utc_now = datetime.now(timezone.utc)
    kst_offset = timedelta(hours=9)
    return utc_now + kst_offset

now_kst = get_kst_now()

# 2. 환경 변수 (WEBHOOK_2는 완전히 삭제됨)
DISCORD_WEBHOOK_1 = os.getenv("DISCORD_WEBHOOK_1")

def fetch_news(mode, limit=15):
    """뉴스 수집 및 링크 필터링 로직"""
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
                # Markdown 예약어([]) 치환 (링크 깨짐 방지)
                title = title.replace("[", "【").replace("]", "】")
                
                link = link_match.group(1) if link_match else None
                
                # [기능] 미리보기 및 불필요 파라미터 링크 제외
                is_invalid = link and any(p in link for p in ["?hl=ko", "preview", "amp;"])

                if len(title) > 3:
                    collected_news.append({
                        "title": title,
                        "link": link if link and not is_invalid else None,
                    })
            if len(collected_news) >= limit: break
        return collected_news, title_prefix
    except Exception as e:
        print(f"❌ 뉴스 파싱 오류 ({mode}): {e}")
        return [], ""

def filter_news(news_list):
    """지표 중심 필터링"""
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "특징주", "급등주", "테마주"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "금리", "상승", "하락", "실적", "공시"]
    
    filtered = []
    for item in news_list:
        title = item["title"]
        if len(title) < 8: continue
        
        has_noise = any(word in title for word in noise_words)
        has_signal = any(word in title for word in signal_words)

        if has_signal or not has_noise:
            filtered.append(item)
        if len(filtered) >= 10: break
    return filtered

def send_to_discord(articles, title_prefix, webhook_url=None):
    """안정적인 메시지 분할 전송 (오류 수정 완료)"""
    if not articles:
        print("📭 전송할 뉴스가 없습니다.")
        return

    # 우선순위: 인자로 전달된 URL > 환경 변수 URL
    target_url = webhook_url if webhook_url and webhook_url.strip() else DISCORD_WEBHOOK_1

    if not target_url:
        print("❌ Discord Webhook URL이 설정되지 않았습니다.")
        return

    messages = []
    current_message = f"{title_prefix}\n\n"
    
    for i, article in enumerate(articles, 1):
        title = article["title"]
        link = article.get("link")

        # 제목 클릭 시 기사 이동 (Markdown)
        line = f"{i}. [{title}]({link})\n\n" if link else f"{i}. {title}\n\n"

        # 디스코드 글자수 제한(2000자) 대응 (여유 있게 1800자)
        if len((current_message + line).encode("utf-8")) > 1800:
            messages.append(current_message)
            current_message = f"{title_prefix}\n\n{line}"
        else:
            current_message += line

    # [수정] 마지막 남은 메시지 덩어리를 반드시 추가
    if current_message.strip():
        messages.append(current_message)

    # 전송 실행
    for msg in messages:
        try:
            res = requests.post(
                target_url, 
                json={"content": msg}, 
                timeout=10,
                headers={"User-Agent": "NewsBot/1.0"}
            )
            if res.status_code in [200, 204]:
                print(f"✅ 전송 성공: {target_url[:30]}...")
            else:
                print(f"⚠️ 전송 실패 ({res.status_code}): {res.text[:100]}")
        except Exception as e:
            print(f"❌ 네트워크 오류: {e}")

def main():
    print(f"🚀 뉴스봇 작동 (KST: {now_kst.strftime('%Y-%m-%d %H:%M')})")
    current_hour = now_kst.hour

    # 실행 조건: 07시 정기 알림 OR GitHub Actions 수동 실행 환경
    is_github = os.getenv("GITHUB_ACTIONS") == "true" or os.getenv("GITHUB_RUN_ID")
    is_scheduled = current_hour == 7

    if is_github or is_scheduled:
        for mode in ["WORLD", "DOMESTIC"]:
            raw_news, prefix = fetch_news(mode)
            filtered = filter_news(raw_news)
            send_to_discord(filtered, prefix)
    else:
        print(f"⏭️ 실행 시간 아님 (현재 {current_hour}시).")

if __name__ == "__main__":
    main()
