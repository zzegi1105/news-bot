def send_to_discord(articles, title_prefix, webhook_url=None):
    """Discord 전송: 기사 앞에 번호, 각 기사 한 줄씩 출력 (Markdown 링크)"""
    if not articles:
        print("📭 전송할 뉴스가 없습니다.")
        return

    # 타겟 webhook 결정: DISCORD_WEBHOOK_2 제거
    targets = []
    if webhook_url and webhook_url.strip():
        targets = [webhook_url]
    else:
        if DISCORD_WEBHOOK_1:
            targets.append(DISCORD_WEBHOOK_1)
        # DISCORD_WEBHOOK_2는 더 이상 사용하지 않음

    if not targets:
        print("❌ Discord Webhook URL이 설정되지 않았습니다.")
        return

    # 1개 메시지 안에 모든 기사 한 줄씩, 번호 붙여서 넣기
    lines = []
    for i, article in enumerate(articles, 1):
        title = article["title"]
        link = article.get("link")
        if link:
            line = f"{i}. [{title}](<{link}>)"
        else:
            line = f"{i}. {title}"
        lines.append(line)

    content = f"{title_prefix}\n\n" + "\n".join(lines)

    # 길이 체크 (1800바이트 초과 시 분할)
    if len(content.encode("utf-8")) > 1800:
        print("⚠️ 메시지 길이 초과로 전송하지 않습니다. (1800바이트 제한)")
        return

    # 전송
    for webhook_url in targets:
        try:
            response = requests.post(
                webhook_url,
                json={"content": content},
                timeout=10,
                headers={"User-Agent": "NewsBot/1.0"},
            )
            if response.status_code in [200, 204]:
                print(f"✅ Discord 전송 완료: {webhook_url[:30]}...")
            else:
                print(f"⚠️ HTTP {response.status_code}: {response.text[:100]}")
        except Exception as e:
            print(f"❌ 전송 실패: {webhook_url[:30]}... {str(e)[:100]}")
