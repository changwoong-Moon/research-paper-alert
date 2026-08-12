# 📚 연구동향 알리미

**사회과학방법론 · 행정학 연구동향** 분야의 새 논문(제목·저자·초록·링크)을 매일 자동 수집해 보여주는 대시보드.

- **대시보드**: https://changwoong-moon.github.io/research-paper-alert/
- 매일 **07:30 KST** 자동 갱신 (GitHub Actions)
- 최근 90일 발행분 표시, 새로 발견된 논문에는 **NEW** 배지 (3일간)

## 데이터 출처

| 출처 | 대상 | 상태 |
|---|---|---|
| [OpenAlex](https://openalex.org) | 해외 학술지 (JPART, PAR, Governance, SMR, Political Analysis 등 22종) | ✅ 즉시 작동 |
| [KCI 오픈API](https://open.kci.go.kr) | 국내 학술지 (한국행정학보, 한국정책학회보, 조사연구 등) | 🔑 키 등록 필요 |
| Crossref / Semantic Scholar | 누락 초록 보충 | ✅ 자동 |
| Springer Meta API | Springer(Quality & Quantity 등) 초록 보충 | 🔑 선택 |

## 국내(KCI) 논문 수집 켜는 법

1. [KCI 오픈API](https://open.kci.go.kr) 접속 → 회원가입/로그인 → **오픈API 신청** 메뉴에서 키 발급 신청
2. 키가 나오면 이 저장소의 **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `KCI_API_KEY`, Secret: 발급받은 키
3. 다음 자동 실행부터 국내 논문이 합류합니다. (Actions 탭에서 `update-papers` → `Run workflow`로 즉시 실행 가능)

> 참고: KCI 응답 규격은 키 발급 후 첫 실행에서 확인됩니다. 첫 실행 로그에 `[KCI] ... 0건`이 찍히면 파싱 조정이 필요할 수 있습니다.

### (선택) Springer 초록 보충

Quality & Quantity 등 Springer 학술지는 무료 API에 초록을 제공하지 않는 경우가 많습니다.
[dev.springernature.com](https://dev.springernature.com)에서 무료 키를 발급받아 `SPRINGER_API_KEY` 시크릿으로 등록하면 자동 보충됩니다.

## 학술지·주제 조정

[papers.py](papers.py) 상단 `TOPICS`에서:

- **해외 학술지 추가**: `https://api.openalex.org/sources?search=학술지명` 으로 ID(S로 시작) 확인 후 `openalex_sources`에 추가
- **국내 학술지 추가**: `kci_journals` 목록에 학술지명 추가
- 주제 자체를 추가하려면 `TOPICS`에 항목을 하나 더 만들면 됩니다

## 구조

```
papers.py                    # 수집 + index.html/papers.json 생성 (표준 라이브러리만)
.github/workflows/update.yml # 매일 07:30 KST 실행
index.html                   # 대시보드 (자동 생성)
data/papers.json             # 기계용 데이터 — Claude 아침 브리핑이 읽음
data/state.json              # 관측 이력 (NEW 판정용)
```

---
🤖 [Claude Code](https://claude.com/claude-code)로 제작
