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

# 2. 환경 변수 (WEBHOOK_2 관련 완전 제거)
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
                link = link_match.group(1) if link_match else None
                
                # [기능 복구] 미리보기 및 불필요한 파라미터가 있는 링크 제외
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
            if len(collected_news) >= limit: break
        return collected_news, title_prefix
    except Exception as e:
        print(f"❌ 뉴스 파싱 오류: {e}")
        return [], ""

def filter_news(news_list):
    """지표 중심 필터링 (기존 로직 유지)"""
    noise_words = ["?", "카더라", "일까", "조짐", "추측", "특징주", "급등주", "테마주"]
    signal_words = ["발표", "확정", "지표", "미국", "국제", "금리", "상승", "하락", "실적", "공
