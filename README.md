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

## 국내(KCI) 수집 구조 — PC 경유

KCI 오픈API는 **신청 시 등록한 IP에서만** 키를 인정하므로(GitHub Actions의 유동 IP에서는
"등록되지 않은 key" 응답), 국내 수집은 등록된 PC가 담당합니다:

1. PC의 [kci_fetch.ps1](kci_fetch.ps1)이 매일 **07:00**에 KCI를 조회해 `data/kci.json`을 커밋·푸시
   (작업 스케줄러 작업 이름: `ResearchPaperAlert-KCI`, 키 파일: `%USERPROFILE%\.kci_api_key`)
2. **07:30** GitHub Actions(papers.py)가 `data/kci.json`을 해외분과 병합해 대시보드 갱신
3. PC가 꺼져 있던 날에도 이미 병합된 국내 논문은 대시보드에 그대로 유지됩니다
   (놓친 실행은 다음 로그인 시 자동 보충 실행)

> 인터넷 회선이 바뀌어 공인 IP가 달라지면 [KCI 오픈API](https://open.kci.go.kr)에서 IP 변경을
> 신청해야 합니다. 수동 실행: 저장소 폴더에서 `powershell -File kci_fetch.ps1`

## 이메일 다이제스트 켜는 법

매일 07:30 갱신 직후, 지난 하루 새 논문 요약 + 대시보드 링크를 dkaskdlry@gmail.com 으로 발송합니다
([send_email.py](send_email.py), 새 논문이 없는 날은 발송 안 함).

1. Google 계정에 2단계 인증이 켜져 있어야 함
2. https://myaccount.google.com/apppasswords 에서 **앱 비밀번호** 생성 (16자리)
3. 저장소 **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `GMAIL_APP_PASSWORD`, Secret: 생성한 16자리 (띄어쓰기 제거)
4. 등록 즉시 다음 실행부터 발송. 끄려면 시크릿 삭제.

### (선택) Springer 초록 보충

Quality & Quantity 등 Springer 학술지는 무료 API에 초록을 제공하지 않는 경우가 많습니다.
[dev.springernature.com](https://dev.springernature.com)에서 무료 키를 발급받아 `SPRINGER_API_KEY` 시크릿으로 등록하면 자동 보충됩니다.

## 학술지·주제 조정

[papers.py](papers.py) 상단 `TOPICS`에서:

- **해외 학술지 추가**: `https://api.openalex.org/sources?search=학술지명` 으로 ID(S로 시작) 확인 후 `openalex_sources`에 추가
- **국내 학술지 추가**: `kci_journals` 목록에 학술지명 추가
- 주제 자체를 추가하려면 `TOPICS`에 항목을 하나 더 만들면 됩니다

## 다른 컴퓨터에서 이어받기

대시보드·이메일·브리핑은 클라우드에서 돌므로 PC와 무관하게 계속 작동합니다.
새 컴퓨터에서 개발을 이어가거나 **국내(KCI) 수집 담당 PC를 옮길 때**만 아래가 필요합니다:

```bash
gh auth login
```
```bash
gh repo clone changwoong-Moon/research-paper-alert
```

KCI 수집 PC를 옮기는 경우 추가로:
1. 키 파일 만들기: `%USERPROFILE%\.kci_api_key` (내용은 KCI 키 한 줄)
2. 새 PC의 공인 IP를 [KCI 오픈API](https://open.kci.go.kr)에 추가/변경 신청 (같은 집 와이파이면 불필요)
3. 작업 스케줄러 등록 (PowerShell, 저장소 폴더 경로만 맞게 수정):
```powershell
Register-ScheduledTask -TaskName "ResearchPaperAlert-KCI" -Action (New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\경로\research-paper-alert\kci_fetch.ps1"') -Trigger (New-ScheduledTaskTrigger -Daily -At "07:00") -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable) -Force
```

Claude Code로 작업할 때는 저장소 폴더에서 열면 [CLAUDE.md](CLAUDE.md)가 맥락을 자동으로 제공합니다.

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
