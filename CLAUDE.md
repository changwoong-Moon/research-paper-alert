# 연구동향 알리미 — Claude Code 작업 안내

사회과학방법론·행정학·계량경제통계 신규 논문을 매일 수집해 대시보드·이메일·Claude 브리핑으로 전달하는 시스템.
이 파일은 어떤 컴퓨터에서든 Claude Code가 맥락을 이어받기 위한 안내서다.

## 구성 요소와 실행 위치

| 구성 | 실행 위치 | 일정 |
|---|---|---|
| kci_fetch.ps1 — 국내(KCI) 논문 수집 → data/kci.json 푸시 | **사용자 PC** (작업 스케줄러 `ResearchPaperAlert-KCI`) | 매일 07:00 KST |
| papers.py — 해외(OpenAlex) 수집 + kci.json 병합 + 번역 + index.html/papers.json 생성 | GitHub Actions (update.yml) | 매일 07:30 KST |
| send_email.py — 새 논문 요약 메일 (dkaskdlry@gmail.com) | GitHub Actions (같은 워크플로) | ~07:35 KST |
| Claude 아침 브리핑 (claude.ai 루틴 trig_01SFLtfbKbG6SZW92kjVp42b) | Anthropic 클라우드 | 매일 08:30 KST |

- 대시보드: https://changwoong-moon.github.io/research-paper-alert/
- 주제 4개: 행정학 연구동향(SSCI PA 전체+지역학+국내), 사회과학방법론, 계량경제·통계,
  AI·머신러닝(2026-08-23 신설: AI 거버넌스·정책 14종 + 계산사회과학 8종 + 핵심 ML 7종 + 국내 6종)
  — papers.py 상단 `TOPICS`에서 조정

## 꼭 알아야 할 제약 (하드코딩된 이유들)

1. **KCI 오픈API는 등록 IP에서만 작동** ("등록되지 않은 key"). 등록 IP는 사용자 집 회선.
   그래서 GitHub Actions가 아닌 PC에서 수집한다. 키 파일: `%USERPROFILE%\.kci_api_key` (저장소에 절대 커밋 금지).
   회선이 바뀌면 open.kci.go.kr에서 IP 변경 신청.
2. **KCI dateFrom/dateTo는 발행년월 YYYYMM 6자리** (YYYYMMDD 아님). journal 파라미터는 부분일치라
   유사 학술지(한국자치행정학보 등)도 같이 들어옴 — 의도적으로 유지 중.
3. **번역은 무키 Google 엔드포인트** (translate_a/single?client=gtx, POST). IP당 ~130건에서 장시간 제한이
   걸리므로 실행당 그 이상은 불가 — 대량 백필은 워크플로를 여러 번 실행(실행마다 러너 IP가 바뀜).
   상한은 workflow_dispatch 입력 `translate_cap`으로 조절.
4. **주제를 새로 추가할 때는 조치 불필요** — state.json에 기록이 없는 주제는 첫 수집이 자동
   소급 처리되어 NEW 배지·이메일·브리핑에서 빠진다(`fresh_topics`). 반면 **기존 주제에 저널만
   대량 추가할 때는** 여전히 workflow_dispatch 입력 `backdate=1`이 필요하다.
   또한 **주제당 수집 상한은 1,600편**(200편 x 8페이지)이다. 저널을 추가하기 전에 90일 물량을
   `https://api.openalex.org/works?filter=primary_location.source.id:<ID>,from_publication_date:<날짜>,type:article|review&per-page=1`
   의 `meta.count`로 실측할 것. 종합지(PNAS Nexus 등)는 주제와 무관한 논문이 대량 유입되므로 피한다.
   OpenAlex는 IP당 일일 쿼터가 있어 대량 조회 후 429가 뜰 수 있다(Retry-After 수 시간) — 이때는
   PC에서 돌리지 말고 GitHub Actions(러너 IP가 매번 다름)에 맡길 것.
5. Wiley/Springer 일부는 공개 API에 초록 미제공. Crossref→SemanticScholar 보충 후에도 없으면
   "초록 미제공" 표시가 정상. Springer는 SPRINGER_API_KEY 시크릿(선택) 등록 시 보충 가능.
6. state.json의 `first_seen`이 NEW 배지(3일)·이메일(26시간)·브리핑(26시간)의 기준.
7. GitHub 저장소 시크릿: KCI_API_KEY(등록 IP에서만 유효), GMAIL_APP_PASSWORD(발송용).
   비밀번호·키는 채팅으로 받지 말고 사용자가 직접 등록하게 안내할 것.

## 자주 하는 작업

- 학술지 추가/삭제: papers.py `TOPICS` 수정 → 커밋·푸시 → Actions 실행 (`backdate=1` 권장)
  - OpenAlex ID 확인: `https://api.openalex.org/sources?search=학술지명`
- 즉시 갱신: Actions 탭 → update-papers → Run workflow (또는 `gh workflow run update.yml`)
- 브리핑 루틴 수정: claude.ai/code/routines 또는 RemoteTrigger API
- 다른 컴퓨터 초기 설정: README의 "다른 컴퓨터에서 이어받기" 절 참고
