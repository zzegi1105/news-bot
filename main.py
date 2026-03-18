import os
import requests
import re
from datetime import datetime, timezone, timedelta

# 1. KST 시간 계산 (Python 3.12+ 호환)
def get_kst_now():
    utc_now = datetime.now(timezone.utc)
    kst_offset = timedelta(hours=9)
    return utc_now + kst_offset

now_kst = get_kst_now()

# 2. 환경 변수 설정 (WEBHOOK_2 제거)
DISCORD_WEBHOOK_1 = os.getenv("DISCORD_WEBHOOK_1")

def fetch_news(mode, limit=15):
    """구글 뉴스 RSS를 통한 뉴스 수집"""
    if mode == "WORLD":
        query = "세계+경제+OR+미국+CPI+OR+연준+금리+OR+뉴욕증시+OR+국제유가+OR+환율"
        title_prefix = f"🌍 **[{now_kst.strftime('%m/%d %H:%M')}] 세계거시경제 TOP 10**"
    else:
        query = (
            "한국+경제+OR+한은+금리+OR+금융위원회+OR+소비자물가+OR+수출입+OR+GDP+성장률"
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
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "")
                if " - " in title:
                    title = title.split(" - ", 1)[0]
                title = title.strip()

                link = link_match.group(1) if link_match else None
                # 불필요한 파라미터가 포함된 링크 필터링
                is_invalid_link = link and ("?hl=ko" in link or "preview" in link or "amp;" in link)

                if len(title) > 3:
                    collected_news.append({
                        "title": title,
                        "link": link if link and not is_invalid_link else None,
                    })

            if len(collected_news) >= limit:
                break
        return collected_news, title_prefix
    except Exception as e:
        print(f"❌ 뉴스 수집 오류 ({mode}): {e}")
        return [], ""

def get_core_keywords(text):
    """중복 체크를 위한 키워드 추출"""
    words = re.findall(r"[가-힣a-zA-Z0-9]{2,}", text)
    stop_words = {"오늘", "내일", "뉴스", "기사", "분석", "속보"}
    return {w for w in words if w not in stop_words}

def is_duplicate_issue(new_title, seen_keyword_sets):
    """키워드 기반 중복 뉴스 필터링"""
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
    """노이즈 제거 및 유의미한 지표 중심 필터링"""
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "특징주", "급등주"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "금리", "상승", "하락", "실적", "CPI"]

    filtered = []
    seen_keyword_sets = []

    for item in news_list:
        title = item
