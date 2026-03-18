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

DISCORD_WEBHOOK_1 = os.getenv("DISCORD_WEBHOOK_1")
DISCORD_WEBHOOK_2 = os.getenv("DISCORD_WEBHOOK_2")


def fetch_news(mode, limit=15):
    """세계/국내 뉴스 수집"""
    if mode == "WORLD":
        query = "세계+경제+OR+미국+CPI+OR+연준+금리+OR+뉴욕증시+OR+국제유가+OR+환율"
        title_prefix = f"🌍 **[{now_kst.strftime('%m/%d %H:%M')}] 세계거시경제 TOP 10**"
    else:  # DOMESTIC (국내거시경제 범위 확장)
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

                # 기사 링크
                link = link_match.group(1) if link_match else None
                # 미리보기/불필요한 파라미터가 있는 링크는 제외
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
    """중복 체크 (3개 이상 공통 키워드면 제외)"""
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
    noise_words = [
        "?",
        "카더라",
        "일까",
        "조짐",
        "추측",
        "포착",
        "전망은",
        "특징주",
        "급등주",
        "테마주",
        "상한가주",
        "떡상주",
    ]
    signal_words = [
        "발표",
        "확정",
        "지표",
        "미국",
        "국제",
        "달러",
        "금리",
        "상승",
        "하락",
        "공시",
        "체결",
        "실적",
        "FOMC",
        "CPI",
    ]

    filtered = []
    seen_keyword_sets = []

    for item in news_list:
        title = item["title"]
        if len(title) =< 10:
            continue

        has_noise = any(word in title for word in noise_words)
        has_signal = any(word in title for word in signal_words)

        if has_signal or not has_noise:
            if not is_duplicate_issue(title, seen_keyword_sets):
                filtered.append(item)
                seen_keyword_sets.append(get_core_keywords(title))
                if len(filtered) >= 10:
                    break

    return filtered


def send_to_discord(articles, title_prefix, webhook_url=None):
    """Discord 전송: Markdown 링크로 기사 링크 연동 (미리보기 제외)"""
    if not articles:
        print("📭 전송할 뉴스가 없습니다.")
        return

    # 타겟 webhook 결정
    targets = []
    if webhook_url and webhook_url.strip():
        targets = [webhook_url]
    else:
        if DISCORD_WEBHOOK_1:
            targets.append(DISCORD_WEBHOOK_1)
        if DISCORD_WEBHOOK_2:
            targets.append(DISCORD_WEBHOOK_2)

    if not targets:
        print("❌ Discord Webhook URL이 설정되지 않았습니다.")
        return

    # 메시지 분할 (Markdown 링크 포함)
    current_message = f"{title_prefix}\n\n"
    messages = []

    for i, article in enumerate(articles, 1):
        title = article["title"]
        link = article.get("link")

        if link:
            line = f"{i}. [{title}](<{link}>)\n\n"
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

    # 전송
    for webhook_url in targets:
        success_count = 0
        try:
            for msg in messages:
                response = requests.post(
                    webhook_url,
                    json={"content": msg},
                    timeout=10,
                    headers={"User-Agent": "NewsBot/1.0"},
                )
                if response.status_code in [200, 204]:
                    success_count += 1
                else:
                    print(f"⚠️ HTTP {response.status_code}: {response.text[:100]}")
            print(f"✅ Discord 전송 완료 ({success_count}/{len(messages)}): {webhook_url[:30]}...")
        except Exception as e:
            print(f"❌ 전송 실패: {webhook_url[:30]}... {str(e)[:100]}")


def main():
    """메인 실행 로직"""
    print(f"🚀 [{now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}] 뉴스봇 시작")
    current_hour = now_kst.hour

    # 1. 오전 7시 정기알림 (WEBHOOK_1만)
    if current_hour == 7:
        print("🕐 [정기알림] 오전 7시 KST - WEBHOOK_1 전용")
        world_news, world_prefix = fetch_news("WORLD")
        domestic_news, domestic_prefix = fetch_news("DOMESTIC")

        world_filtered = filter_news(world_news)
        domestic_filtered = filter_news(domestic_news)

        print(f"🌍 세계뉴스: {len(world_filtered)}개, 🇰🇷 국내뉴스: {len(domestic_filtered)}개")

        if DISCORD_WEBHOOK_1:
            send_to_discord(world_filtered, world_prefix, DISCORD_WEBHOOK_1)
            send_to_discord(domestic_filtered, domestic_prefix, DISCORD_WEBHOOK_1)
        else:
            print("❌ DISCORD_WEBHOOK_1 환경변수 누락")
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
