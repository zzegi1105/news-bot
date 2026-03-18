#!/usr/bin/env python3
import os
import sys
import re
import requests
from datetime import datetime, timedelta
from urllib.parse import quote

print("=== KST 7AM 뉴스 봇 시작 ===")

# 환경변수 확인
webhook = os.getenv("DISCORD_WEBHOOK_1")
if not webhook:
    print("❌ DISCORD_WEBHOOK_1 없음")
    sys.exit(1)
print(f"✓ Webhook 준비됨 ({len(webhook)}자)")

def kst_now():
    return datetime.utcnow() + timedelta(hours=9)

def get_news(query, max_items=20):
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        
        items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
        news = []
        for item in items[:max_items]:
            title = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            link = re.search(r'<link>(.*?)</link>', item)
            if title and link:
                t = title.group(1).split(' - ')[0].strip()
                l = link.group(1).strip()
                if len(t) > 10:
                    news.append({"title": t[:120], "link": l})
        print(f"✓ {len(news)}개 뉴스 수집")
        return news
    except:
        print("❌ 뉴스 수집 실패")
        return []

def filter_news(news):
    noise = ["특징주", "카더라", "일까", "추측", "포착"]
    good = []
    for n in news:
        if not any(x in n['title'] for x in noise):
            good.append(n)
            if len(good) >= 10: break
    return good

# 뉴스 수집
print("📡 뉴스 수집 중...")
world = get_news("뉴욕증시 OR 국제유가 OR 환율 OR 미국 CPI OR 연준 금리")
korea = get_news("공시 OR 수주 OR 분기실적 OR 장마감 OR 공급계약")

world_ok = filter_news(world)
korea_ok = filter_news(korea)
all_news = world_ok + korea_ok

if not all_news:
    print("❌ 뉴스 없음")
    sys.exit(1)

# 디스코드 전송 (미리보기 완전 제거)
now = kst_now()
title = f"📰 [{now.strftime('%m/%d %H시')}] 세계+국내 Top{len(all_news)}"
msg = f"{title}\n\n"

for i, n in enumerate(all_news, 1):
    msg += f"{i}. **{n['title']}**\n🔗 <{n['link']}>\n\n"

if len(msg) > 1900:
    msg = msg[:1900] + "..."

print("📤 디스코드 전송...")
try:
    r = requests.post(webhook, json={"content": msg, "embeds": []}, timeout=10)
    if r.status_code in [200, 204]:
        print("✅ 성공!")
        sys.exit(0)
    else:
        print(f"❌ 실패: {r.status_code}")
        sys.exit(1)
except:
    print("❌ 전송 오류")
    sys.exit(1)
