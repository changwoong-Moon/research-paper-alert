# ============================================================
# 연구동향 알리미 — KCI 국내 논문 수집 (등록 IP인 이 PC에서 실행)
#
# KCI 오픈API는 신청 시 등록한 IP에서만 키를 인정하므로
# GitHub Actions 대신 이 PC에서 수집해 data/kci.json 으로 푸시한다.
# 매일 07:30 GitHub Actions(papers.py)가 이 파일을 대시보드에 병합한다.
#
# 키 파일: %USERPROFILE%\.kci_api_key  (키 한 줄만)
# 자동 실행: 작업 스케줄러 "ResearchPaperAlert-KCI" (매일 07:00)
# 학술지 목록: data/kci_config.json (papers.py TOPICS에서 자동 생성)
# ============================================================
$ErrorActionPreference = "Continue"
$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$KeyFile = Join-Path $env:USERPROFILE ".kci_api_key"
if (-not (Test-Path $KeyFile)) { Write-Output "키 파일이 없습니다: $KeyFile"; exit 1 }
$Key = (Get-Content $KeyFile -Raw).Trim()
$From = (Get-Date).AddDays(-90).ToString("yyyyMM")
$To = (Get-Date).ToString("yyyyMM")

# 원격의 최신 코드/설정 받기 (Actions 커밋과 충돌 방지)
git -C $RepoDir pull --rebase origin main | Out-Null

# 학술지 목록: kci_config.json 우선, 없으면 내장 기본값
$topics = $null
$cfgPath = Join-Path $RepoDir "data\kci_config.json"
if (Test-Path $cfgPath) {
  try { $topics = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $topics = $null }
}
if ($null -eq $topics) {
  $topics = @(
    [pscustomobject]@{ topic = "public-admin"; journals = @("한국행정학보", "한국정책학회보", "행정논총", "한국사회와 행정연구", "정부학연구", "지방정부연구", "한국조직학회보", "한국인사행정학회보", "한국행정연구") },
    [pscustomobject]@{ topic = "methodology"; journals = @("조사연구") }
  )
}

$all = New-Object System.Collections.ArrayList
foreach ($t in $topics) {
  foreach ($j in $t.journals) {
    $enc = [uri]::EscapeDataString($j)
    $uri = "https://open.kci.go.kr/po/openapi/openApiSearch.kci?apiCode=articleSearch&key=$Key&journal=$enc&dateFrom=$From&dateTo=$To&displayCount=100&page=1"
    try {
      $resp = Invoke-WebRequest -Uri $uri -TimeoutSec 60 -UseBasicParsing
      [xml]$x = $resp.Content
      $msgNode = $x.SelectSingleNode("//resultMsg")
      if ($msgNode) { Write-Output ("{0}: 안내 - {1}" -f $j, $msgNode.InnerText) }
      $records = @($x.SelectNodes("//record"))
      $cnt = 0
      foreach ($r in $records) {
        $ai = $r.SelectSingleNode(".//articleInfo")
        if ($null -eq $ai) { continue }
        $artId = $ai.GetAttribute("article-id")
        $tn = $r.SelectSingleNode(".//article-title[@lang='original']")
        if ($null -eq $tn) { $tn = $r.SelectSingleNode(".//article-title") }
        if ($null -eq $tn) { continue }
        $title = $tn.InnerText.Trim()
        if (-not $title) { continue }
        $an = $r.SelectSingleNode(".//abstract[@lang='original']")
        if ($null -eq $an) { $an = $r.SelectSingleNode(".//abstract") }
        $abstract = ""
        if ($an) { $abstract = ($an.InnerText -replace '\s+', ' ').Trim() }
        $authors = New-Object System.Collections.ArrayList
        foreach ($a in $r.SelectNodes(".//author")) {
          $nm = ($a.InnerText -replace '\([^)]*\)', '').Trim()
          if ($nm -and $authors.Count -lt 10) { [void]$authors.Add($nm) }
        }
        $jnNode = $r.SelectSingleNode(".//journal-name")
        $jn = ""
        if ($jnNode) { $jn = $jnNode.InnerText.Trim() }
        if (-not $jn) { $jn = $j }
        $yNode = $r.SelectSingleNode(".//pub-year")
        $mNode = $r.SelectSingleNode(".//pub-mon")
        $date = ""
        if ($yNode) {
          $date = $yNode.InnerText.Trim()
          if ($mNode) { $date += "-" + $mNode.InnerText.Trim().PadLeft(2, "0") }
        }
        $uNode = $r.SelectSingleNode(".//url")
        $dNode = $r.SelectSingleNode(".//doi")
        $url = ""
        if ($uNode) { $url = $uNode.InnerText.Trim() }
        $doi = ""
        if ($dNode) { $doi = $dNode.InnerText.Trim() -replace '^https://doi\.org/', '' }
        if (-not $artId) { if ($doi) { $artId = $doi } else { $artId = $title } }
        if (-not $url -and $artId -like "ART*") {
          $url = "https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=$artId"
        }
        if (-not $url) { $url = "https://www.kci.go.kr/" }
        [void]$all.Add([ordered]@{
          id = "kci:$artId"; topic = $t.topic; origin = "KCI"; title = $title
          authors = @($authors); journal = $jn; date = $date
          abstract = $abstract; url = $url; doi = $doi; pdf = ""
        })
        $cnt++
      }
      Write-Output ("{0}: {1}건" -f $j, $cnt)
    } catch {
      Write-Output ("{0}: 실패 - {1}" -f $j, $_.Exception.Message)
    }
    Start-Sleep -Seconds 1
  }
}

if ($all.Count -eq 0) { Write-Output "수집 0건 — kci.json을 갱신하지 않습니다."; exit 1 }

$payload = [ordered]@{
  fetched_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss+09:00")
  records    = @($all)
}
$json = ConvertTo-Json -InputObject $payload -Depth 6
$outPath = Join-Path $RepoDir "data\kci.json"
New-Item -ItemType Directory -Force (Join-Path $RepoDir "data") | Out-Null
[System.IO.File]::WriteAllText($outPath, $json, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("총 {0}건 저장: {1}" -f $all.Count, $outPath)

# 커밋 & 푸시
git -C $RepoDir add data/kci.json
git -C $RepoDir diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  git -C $RepoDir commit -m "data: KCI 국내 논문 수집 (PC)" | Out-Null
  git -C $RepoDir push origin main
  if ($LASTEXITCODE -ne 0) {
    git -C $RepoDir pull --rebase origin main
    git -C $RepoDir push origin main
  }
  Write-Output "푸시 완료"
} else {
  Write-Output "변경 없음"
}
