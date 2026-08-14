#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""새 논문 이메일 다이제스트 — data/papers.json 기반.

- GMAIL_APP_PASSWORD 시크릿이 있을 때만 발송 (없으면 조용히 통과)
- 지난 26시간 내 처음 발견된 논문이 있을 때만 발송
- 표준 라이브러리만 사용. papers.py 실행·커밋 후 워크플로에서 호출.
"""
import html
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
MAIL_ADDR = "dkaskdlry@gmail.com"   # 발신·수신 겸용 (본인 Gmail)
DASHBOARD = "https://changwoong-moon.github.io/research-paper-alert/"
PER_TOPIC = 12  # 이메일에 싣는 주제당 최대 논문 수


def esc(s):
    return html.escape(s or "", quote=True)


def build_items(news):
    items = []
    for p in news[:PER_TOPIC]:
        gist = (p.get("abstract_ko") or p.get("abstract") or "").strip()
        if len(gist) > 170:
            gist = gist[:170].rsplit(" ", 1)[0] + " …"
        authors = ", ".join((p.get("authors") or [])[:3])
        meta = " · ".join(x for x in (p.get("journal"), p.get("date"), authors) if x)
        gist_html = ('<div style="color:#444;font-size:13px;line-height:1.5;'
                     'margin:4px 0 0">%s</div>' % esc(gist)) if gist else ""
        items.append(
            '<li style="margin:0 0 14px">'
            '<a href="%s" style="color:#2563eb;text-decoration:none;'
            'font-weight:700;font-size:14px;line-height:1.5">%s</a>'
            '<div style="color:#777;font-size:12px;margin:2px 0 0">%s</div>%s</li>'
            % (esc(p.get("url")), esc(p.get("title")), esc(meta), gist_html))
    return "".join(items)


def main():
    # 앱 비밀번호는 "xxxx xxxx xxxx xxxx" 형태로 복사되는 경우가 많아 공백 전부 제거
    pw = "".join(os.environ.get("GMAIL_APP_PASSWORD", "").split())
    if not pw:
        print("GMAIL_APP_PASSWORD 미설정 — 이메일 발송 건너뜀")
        return
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "data", "papers.json"), encoding="utf-8") as f:
        data = json.load(f)
    cutoff = (NOW - timedelta(hours=26)).isoformat(timespec="seconds")

    sections = []
    plain_lines = []
    total = 0
    for t in data.get("topics", []):
        news = [p for p in t.get("papers", []) if p.get("first_seen", "") >= cutoff]
        if not news:
            continue
        total += len(news)
        more = ("<div style='color:#777;font-size:12px'>외 %d편은 대시보드에서 확인</div>"
                % (len(news) - PER_TOPIC)) if len(news) > PER_TOPIC else ""
        sections.append(
            '<h2 style="font-size:16px;margin:22px 0 10px;color:#1c2733">'
            '%s <span style="color:#dc2626">%d편</span></h2>'
            '<ul style="margin:0;padding:0 0 0 18px">%s</ul>%s'
            % (esc(t["name"]), len(news), build_items(news), more))
        plain_lines.append("[%s] 새 논문 %d편" % (t["name"], len(news)))
        for p in news[:PER_TOPIC]:
            plain_lines.append("- %s (%s) %s" % (p.get("title"), p.get("journal"), p.get("url")))

    if total == 0:
        print("지난 26시간 새 논문 없음 — 이메일 발송 안 함")
        return

    subject = "📚 연구동향 알리미 — 새 논문 %d편 (%s)" % (total, NOW.strftime("%m/%d"))
    html_body = (
        '<div style="max-width:640px;margin:0 auto;font-family:\'Malgun Gothic\','
        '\'Apple SD Gothic Neo\',sans-serif;padding:8px">'
        '<h1 style="font-size:19px;color:#1c2733;margin:8px 0">📚 연구동향 알리미</h1>'
        '<p style="color:#5a6b7b;font-size:13px;margin:0 0 6px">%s 기준, 지난 하루 새로 발견된 논문입니다.</p>'
        '%s'
        '<p style="margin:26px 0"><a href="%s" style="background:#2563eb;color:#fff;'
        'padding:12px 22px;border-radius:8px;text-decoration:none;font-weight:700;'
        'font-size:14px">전체 대시보드 열기 →</a></p>'
        '<p style="color:#98a6b5;font-size:11px;line-height:1.6">해외 논문 요지는 자동 번역(참고용).'
        ' 매일 아침 자동 발송 · GitHub Actions</p></div>'
        % (NOW.strftime("%Y-%m-%d %H:%M"), "".join(sections), DASHBOARD))
    plain = "연구동향 알리미 — 새 논문 %d편\n\n%s\n\n대시보드: %s" % (
        total, "\n".join(plain_lines), DASHBOARD)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = "연구동향 알리미 <%s>" % MAIL_ADDR
    msg["To"] = MAIL_ADDR
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(MAIL_ADDR, pw)
        s.send_message(msg)
    print("이메일 발송 완료: 새 논문 %d편 → %s" % (total, MAIL_ADDR))


if __name__ == "__main__":
    main()
