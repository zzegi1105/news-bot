import os
import requests
import re
from datetime import datetime

print("🔥 === 자동 뉴스 봇 완전 디버깅 모드 ===")
print(f"⏰ 실행시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S KST')}")

# 1. 웹후크 URL 디버깅
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_1")
print(f"🔗 WEBHOOK_1: {'✅ 설정됨' if DISCORD_WEBHOOK_URL else '❌ 미설정'} (길이: {len(DISCORD_WEBHOOK_URL) if DISCORD_WEBHOOK_URL else 0})")

def test_webhook():
    """웹후크 연결 테스트"""
    if not DISCORD_WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_1 없음. Settings > Secrets에서 설정하세요")
        return False
    
    test_payload = {
        "content": f"🧪 **테스트 성공!**\n봇이 정상 작동합니다. ({datetime.now().strftime('%H:%M:%S')})"
    }
    try:
        print("📡 웹후크 테스트 전송 중...")
        response = requests.post(DISCORD_WEBHOOK_URL, json=test_payload, timeout=10)
        print(f"✅ 테스트 결과: Status={response.status_code}, Response={response.text[:100]}")
        if response.status_code == 204:
            print("🎉 웹후크 정상!")
            return True
        else:
            print("❌ 웹후크 응답 비정상")
            return False
    except Exception as e:
        print(f"💥 웹후크 연결 실패: {e}")
        return False

def fetch_news(query, news_type):
    """뉴스 수집"""
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        print(f"📥 {news_type} 수집 중...")
        response = requests.get(rss_url, timeout=15)
        items = re.findall(r'<item>(.*?)</item>', response.text, re.DOTALL)
        news_list = []
        for item in items[:150]:
            title_match = re.search(r'<title>(.*?)</title>', item)
            link_match = re.search(r'<link>(.*?)</link>', item)
            if title_match and link_match:
                title = title_match.group(1).replace("<![CDATA[", "").replace("]]>", "").split(" - ")[0]
                link = link_match.group(1)
                news_list.append({"title": title, "link": link, "type": news_type})
        print(f"✅ {news_type} {len(news_list)}개 수집")
        return news_list
    except Exception as e:
        print(f"❌ {news_type} 수집 실패: {e}")
        return []

def simple_filter(news_list, max_count=10):
    """간단 필터링 (중복/노이즈 제거)"""
    if not news_list:
        return []
    
    # 상위 N개만 (시간 절약)
    filtered = news_list[:max_count]
    print(f"✅ {len(filtered)}개 선정 (간단 필터링)")
    return filtered

# === 메인 실행 ===
print("\n🚀 1. 웹후크 테스트")
if not test_webhook():
    print("\n💥 웹후크 문제로 중단")
    exit(1)

print("\n🚀 2. 뉴스 수집")
macro_news = fetch_news("뉴욕증시+OR+국제유가+OR+환율+OR+미국+CPI+OR+연준+금리", "🌍 거시경제")
domestic_news = fetch_news("공시+OR+수주+OR+분기실적+OR+장마감+특징주", "📊 국내경제")

print("\n🚀 3. 필터링")
macro_final = simple_filter(macro_news, 10)
domestic_final = simple_filter(domestic_news, 10)
final_news = macro_final + domestic_final

print(f"\n📊 최종 결과: 거시 {len(macro_final)} + 국내 {len(domestic_final)} = 총 {len(final_news)}개")

if not final_news:
    print("❌ 뉴스 0개 - 종료")
    exit(0)

# 4. 실제 전송
print("\n🚀 4. 디스코드 전송")
title = f"📰 **[{datetime.now().strftime('%m/%d %H:%M')}] 종합 경제 TOP {len(final_news)}**"
messages = []
current_msg = f"{title}\n\n"

for i, article in enumerate(final_news, 1):
    line = f"{i}. **{article['title']}** {article['type']}\n🔗 [기사보기](<{article['link']}>)\n\n"
    if len(current_msg + line) > 1800:
        messages.append(current_msg)
        current_msg = line
    else:
        current_msg += line

messages.append(current_msg + "─────")

for i, msg in enumerate(messages, 1):
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": msg}, timeout=10)
        print(f"✅ 메시지 {i}/{len(messages)} 전송: {resp.status_code}")
    except Exception as e:
        print(f"❌ 메시지 {i} 실패: {e}")

print("\n🎉 모든 작업 완료!")
