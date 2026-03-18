import os
import requests
import re
from datetime import datetime, timezone, timedelta


# Python 3.12 완전 호환 KST 시간 계산
def get_kst_now():
    utc_now = datetime.now(timezone.utc)
    kst_offset = timedelta(hours=9)
    kst_now = utc_now + kst_offset
    return kst_now


now_kst = get_kst_now()

# 환경변수 로드
DISCORD_WEBHOOK_1 = os.getenv("DISCORD_WEBHOOK_1")


def fetch_news(mode, limit=15):
    """세계/국내 뉴스 수집"""
    if mode == "WORLD":
        query = "세계+경제+OR+미국+CPI+OR+연준+금리+OR+뉴욕증시+OR+국제유가+OR+환율"
        title_prefix = f"🌍 **[{now_kst.strftime('%m/%d %H:%M')}] 세계거시경제 TOP 10**"
    else:  # DOMESTIC
        query = (
            "한국+경제+OR+韩國+经济"
            "+OR+한국은행+OR+BOK+한은"
            "+OR+금융위원회+OR+금융감독원+OR+금감원"
            "+OR+소비자물가+OR+CPI+물가지수"
            "+OR+고용+OR+실업률+OR+경제활동인구"
            "+OR+수출+OR+수입+OR+무역수지+OR+국제수지"
            "+OR+경기지수+OR+景氣指數+OR+景氣지수"
            "+OR+국내총생산+OR+GDP+성장률"
        )
        title_prefix = f"🇰🇷 **[{now_kst.strftime('%m/%d %H:%M')}] 국내거시경제 TOP 10**"

    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"

    try:
        print(f"📡 {mode} 뉴스 RSS 요청: {rss_url[:80]}...")
        response = requests.get(rss_url, timeout=15)
        response.raise_for_status()
        xml_text = response.text
        items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL)

        collected_news = []
        for item in items:
            title_match = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
            link_match = re.search(r"<link>(.*?)</link>", item, re.DOTALL)

            if title_match:
                title = title_match.group(1)
                title = title.replace("<![CDATA[", "").replace("]]>", "")
                if " - " in title:
                    title = title.split(" - ", 1)[0]
                title = title.strip()

                link = link_match.group(1) if link_match else None
                has_preview = link and (
                    "?hl=ko&gl=KR&ceid=KR:ko" in link
                    or "preview" in link
                    or "amp;" in link
                )

                if len(title) > 3:
                    collected_news.append({
                        "title": title,
                        "link": link if link and not has_preview else None,
                    })

            if len(collected_news) >= limit:
                break

        print(f"✅ {mode} 뉴스 수집: {len(collected_news)}개")
        return collected_news, title_prefix
    except Exception as e:
        print(f"❌ 뉴스 파싱 오류 ({mode}): {e}")
        return [], ""


def get_core_keywords(text):
    """핵심 키워드 추출"""
    words = re.findall(r"[가-힣a-zA-Z0-9]{2,}", text)
    stop_words = {"오늘", "내일", "뉴스", "기사", "게시판", "분석", "이유", "속보", "중계"}
    return {w for w in words if w not in stop_words}


def is_duplicate_issue(new_title, seen_keyword_sets):
    """중복 체크"""
    new_keywords = get_core_keywords(new_title)
    if len(new_keywords) < 2:
        return True

    for existing_keywords in seen_keyword_sets:
        common = new_keywords.intersection(existing_keywords)
        if len(common) >= 3:
            return True
        if len(new_keywords) <= 4 and len(common) >= 2:
            return True
    return False


def filter_news(news_list):
    """특징주 제거 포함 필터링"""
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "포착", "전망은", "특징주", "급등주", "테마주", "상한가주", "떡상주"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "달러", "금리", "상승", "하락", "공시", "체결", "실적", "FOMC", "CPI"]

    filtered = []
    seen_keyword_sets = []

    for item in news_list:
        title = item["title"]
        if len(title) < 10:
            continue

        has_noise = any(word in title for word in noise_words)
        has_signal = any(word in title for word in signal_words)

        if has_signal or not has_noise:
            if not is_duplicate_issue(title, seen_keyword_sets):
                filtered.append(item)
                seen_keyword_sets.append(get_core_keywords(title))
        if len(filtered) >= 10:
            break

    print(f"✅ 필터링 후: {len(filtered)}개")
    return filtered


def send_to_discord(articles, title_prefix, webhook_url=None):
    """Discord 전송"""
    if not articles:
        print("📭 전송할 뉴스가 없습니다.")
        return

    # 타겟 webhook 결정
    targets = []
    if webhook_url and webhook_url.strip():
        targets = [webhook_url]
    elif DISCORD_WEBHOOK_1:
        targets = [DISCORD_WEBHOOK_1]
    else:
        print("❌ DISCORD_WEBHOOK_1 환경변수 누락")
        return

    print(f"📤 Discord 전송 대상: {len(targets)}개 webhook")

    # 메시지 분할 (수정: 백슬래시 제거)
    current_message = f"{title_prefix}\n\n"
    messages = []

    for i, article in enumerate(articles, 1):
        title = article["title"]
        link = article.get("link")

        if link:
            line = f"{i}. [{title}]({link})\n\n"
        else:
            line = f"{i}. {title}\n\n"

        new_msg = current_message + line
        if len(new_msg.encode("utf-8")) > 1800:
            messages.append(current_message)
            current_message = f"{title_prefix}\n\n{line}"
        else:
            current_message = new_msg

    if current_message.strip():
        messages.append(current_message)

    print(f"📤 분할 메시지: {len(messages)}개")

    # 전송
    for webhook_url in targets:
        success_count = 0
        print(f"🔗 Webhook 테스트: {webhook_url[:40]}...")
        
        try:
            for idx, msg in enumerate(messages, 1):
                print(f"📤 메시지 {idx}/{len(messages)} 전송 시도...")
                response = requests.post(
                    webhook_url,
                    json={"content": msg},
                    timeout=10,
                    headers={"User-Agent": "NewsBot/1.0"},
                )
                print(f"   HTTP {response.status_code}: {response.text[:100]}")
                
                if response.status_code in [200, 204]:
                    success_count += 1
                else:
                    print(f"⚠️ 전송 실패: {response.status_code}")
            
            print(f"✅ Discord 전송 완료 ({success_count}/{len(messages)})")
        except Exception as e:
            print(f"❌ 전송 예외 발생: {str(e)[:100]}")


def main():
    """메인 실행 로직"""
    print(f"🚀 [{now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}] 뉴스봇 시작")
    print(f"🔍 DISCORD_WEBHOOK_1: {'설정됨' if DISCORD_WEBHOOK_1 else '누락됨'}")
    if DISCORD_WEBHOOK_1:
        print(f"🔍 Webhook 길이: {len(DISCORD_WEBHOOK_1)}자")
    
    current_hour = now_kst.hour
    print(f"🕐 현재 시간: {current_hour}시")

    # 1. 오전 7시 정기알림
    if current_hour == 7:
        print("🕐 [정기알림] 오전 7시 KST")
        world_news, world_prefix = fetch_news("WORLD")
        domestic_news, domestic_prefix = fetch_news("DOMESTIC")

        world_filtered = filter_news(world_news)
        domestic_filtered = filter_news(domestic_news)

        print(f"🌍 세계뉴스: {len(world_filtered)}개, 🇰🇷 국내뉴스: {len(domestic_filtered)}개")

        if DISCORD_WEBHOOK_1:
            send_to_discord(world_filtered, world_prefix, DISCORD_WEBHOOK_1)
            send_to_discord(domestic_filtered, domestic_prefix, DISCORD_WEBHOOK_1)
        return

    # 2. GitHub Actions 수동 실행
    if os.getenv("FORCE_RUN") == "true" or os.getenv("GITHUB_RUN_ID"):
        print("🔥 [GitHub Actions] 수동실행 모드")
        world_news, world_prefix = fetch_news("WORLD")
        domestic_news, domestic_prefix = fetch_news("DOMESTIC")

        world_filtered = filter_news(world_news)
        domestic_filtered = filter_news(domestic_news)

        print(f"🌍 세계뉴스: {len(world_filtered)}개, 🇰🇷 국내뉴스: {len(domestic_filtered)}개")

        send_to_discord(world_filtered, world_prefix)
        send_to_discord(domestic_filtered, domestic_prefix)
        return

    print(f"⏭️ 실행시간 아님 ({current_hour}시) - 매일 07:00에 자동실행")
    return


if __name__ == "__main__":
    main()
