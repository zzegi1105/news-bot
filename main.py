#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 미리보기 링크 100% 제거 + 모든 오류 해결 버전

import os
import sys
import re
from datetime import datetime, timedelta

print("=== 뉴스 봇 시작 (미리보기 제거 버전) ===")

# 1. requests 자동 설치
try:
    import requests
    print("✓ requests 모듈 확인")
except ImportError:
    print("❌ requests 없음. 설치...")
    os.system("pip install requests")
    import requests
    print("✓ requests 설치 완료")

# 2. 환경변수 확인
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_1", "").strip()
print(f"DISCORD_WEBHOOK_1 길이: {len(DISCORD_WEBHOOK_URL) if DISCORD_WEBHOOK_URL else 0}")

if not DISCORD_WEBHOOK_URL or len(DISCORD_WEBHOOK_URL) < 20:
    print("❌ DISCORD_WEBHOOK_1 설정 필요!")
    print("Settings → Secrets → Actions → DISCORD_WEBHOOK_1 등록")
    sys.exit(1)

# 3. 한국시간
def get_kst_now():
    utc_now = datetime.utcnow()
    return utc_now + timedelta(hours=9)

def safe_request(url, timeout=10):
    try:
        print(f"요청: {url[:60]}...")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        print(f"✓ 성공: {len(response.text)} bytes")
        return response.text
    except Exception as e:
        print(f"❌ HTTP 오류: {e}")
        return None

def fetch_news(mode, max_items=30):
    print(f"\n--- {mode} 뉴스 수집 ---")
    
    if mode == "MORNING":
        query = "뉴욕증시+OR+국제유가+OR+환율+OR+미국+CPI+OR+연준+금리"
    else:
        query = "공시+OR+수주+OR+분기실적+OR+장마감+OR+특징주+OR+공급계약+체결"
    
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    xml_text = safe_request(rss_url)
    if not xml_text:
        return []
    
    items = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>', xml_text, re.DOTALL)
    print(f"RSS: {len(items)}개")
    
    news_list = []
    for title, link in items[:max_items]:
        title = (re.sub(r'<![CDATA|\]\]>', '', title)
                .replace('\n', ' ')
                .split(' - ')[0]
                .strip())
        link = link.strip()
        
        if len(title) > 5 and len(link) > 10:
            news_list.append({"title": title[:100], "link": link})
    
    print(f"수집: {len(news_list)}개")
    return news_list

def filter_news(news_list, max_count=10):
    if not news_list:
        return []
    
    # 노이즈 제거: 특징주 포함
    noise_words = ["특징주", "카더라", "일까", "조짐", "추측", "포착", "전망은"]
    
    filtered = []
    for item in news_list:
        title = item['title']
        if not any(n in title for n in noise_words):
            filtered.append(item)
            if len(filtered) >= max_count:
                break
    
    print(f"필터링: {len(filtered)}개")
    return filtered

def send_discord(articles):
    """🔒 미리보기 100% 제거"""
    if not articles:
        print("❌ 뉴스 없음")
        return False
    
    now_kst = get_kst_now()
    title = f"📰 **[{now_kst.strftime('%m/%d %H시')}] 세계+국내 Top{len(articles)}**"
    
    message = f"{title}\n\n"
    for i, article in enumerate(articles, 1):
        # ⚠️ 미리보기 완전 차단: <URL> 형식
        message += f"{i}. **{article['title']}**\n🔗 <{article['link']}>\n\n"
    
    if len(message) > 1900:
        message = message[:1900] + "\n..."
    
    try:
        print("디스코드 전송...")
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={
                "content": message,
                "embeds": []  # 임베드 강제 비활성화
            },
            timeout=10
        )
        print(f"응답: {response.status_code}")
        
        if response.status_code in [200, 204]:
            print("✅ 🎉 디스코드 전송 성공! (미리보기 제거)")
            return True
        else:
            print(f"❌ 웹훅 오류: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ 전송 실패: {e}")
        return False

# === 메인 실행 ===
print("\n🚀 뉴스 수집 시작!")
print(f"실행 시간: {get_kst_now().strftime('%Y-%m-%d %H:%M:%S KST')}")

world_news = fetch_news("MORNING")
domestic_news = fetch_news("AFTERNOON")

world_filtered = filter_news(world_news, 10)
domestic_filtered = filter_news(domestic_news, 10)
all_news = world_filtered + domestic_filtered

print(f"\n📊 최종 {len(all_news)}개 뉴스")

success = send_discord(all_news)
print(f"\n🎯 완료: {'성공' if success else '실패'}")

sys.exit(0 if success else 1)
