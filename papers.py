#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""연구동향 알리미 — 사회과학방법론 · 행정학 연구동향 신규 논문 수집기.

- 해외: OpenAlex API (키 불필요)
- 국내: KCI 오픈API (환경변수 KCI_API_KEY 등록 시 자동 활성화)
- 초록 보충: Crossref → Semantic Scholar → Springer(선택, SPRINGER_API_KEY)
- 출력: index.html(대시보드), data/papers.json(브리핑용), data/state.json(상태)

표준 라이브러리만 사용. GitHub Actions에서 매일 실행.
학술지 목록·주제 조정은 아래 TOPICS 만 수정하면 됨.
"""
import json
import os
import re
import sys
import time
import html
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
TODAY = NOW.date()

FETCH_DAYS = 90      # 최근 N일 발행분 수집
NEW_DAYS = 3         # 처음 발견 후 N일 동안 NEW 배지
PRUNE_DAYS = 220     # 상태 파일에서 오래된 항목 제거
ABS_LOOKUP_CAP = 40  # 실행당 초록 보충 조회 상한
# 실행당 해외 초록 한국어 번역 상한 (workflow_dispatch 입력으로 일시 상향 가능)
TRANSLATE_CAP = int(os.environ.get("TRANSLATE_CAP") or "150")
# 1이면 이번 실행에서 새로 발견된 논문을 NEW로 표시하지 않음 (저널 대량 추가 시 배지 폭주 방지)
BACKDATE_NEW = bool(os.environ.get("BACKDATE_NEW", "").strip())
MAILTO = "dkaskdlry@gmail.com"

KCI_API_KEY = os.environ.get("KCI_API_KEY", "").strip()
SPRINGER_API_KEY = os.environ.get("SPRINGER_API_KEY", "").strip()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_PATH = os.path.join(DATA_DIR, "state.json")
JSON_PATH = os.path.join(DATA_DIR, "papers.json")
HTML_PATH = os.path.join(BASE_DIR, "index.html")

DASHBOARD_URL = "https://changwoong-moon.github.io/research-paper-alert/"
REPO_URL = "https://github.com/changwoong-Moon/research-paper-alert"

# ---------------------------------------------------------------- 주제 설정
TOPICS = [
    {
        "key": "public-admin",
        "name": "행정학 연구동향",
        # OpenAlex source ID: 학술지 이름 (ID는 https://api.openalex.org/sources?search=학술지명 으로 확인)
        # SSCI Public Administration 카테고리 전체 + 지역학(Area Studies) 행정·정책지
        "openalex_sources": {
            "S169433491": "J. of Public Administration Research and Theory",
            "S76877748": "Public Administration Review",
            "S62375027": "Governance",
            "S37623806": "Public Management Review",
            "S5465880": "Administration & Society",
            "S106702950": "American Review of Public Administration",
            "S201221823": "Public Administration",
            "S63571029": "International Public Management Journal",
            "S25370267": "J. of Policy Analysis and Management",
            "S119514724": "Policy Studies Journal",
            "S136809933": "Public Performance & Management Review",
            "S16140064": "International Review of Administrative Sciences",
            "S2735938357": "Perspectives on Public Management and Governance",
            "S108218269": "Regulation & Governance",
            "S197895017": "Policy Sciences",
            "S17167983": "Policy & Politics",
            "S76906069": "Journal of Public Policy",
            "S17185278": "Public Policy and Administration",
            "S114598798": "Policy Studies",
            "S77082647": "J. of Comparative Policy Analysis",
            "S87681011": "Public Money & Management",
            "S171234518": "Local Government Studies",
            "S51277951": "Review of Public Personnel Administration",
            "S38942948": "Public Personnel Management",
            "S71588376": "Canadian Public Administration",
            "S128357121": "Australian J. of Public Administration",
            "S31120751": "Social Policy & Administration",
            "S178021067": "Journal of Social Policy",
            "S187013691": "J. of European Social Policy",
            "S136009100": "International J. of Social Welfare",
            "S26544713": "Social Service Review",
            "S168572994": "Nonprofit and Voluntary Sector Quarterly",
            "S80347152": "VOLUNTAS",
            "S70709366": "Nonprofit Management and Leadership",
            "S1650206": "Milbank Quarterly",
            "S192655146": "J. of Health Politics, Policy and Law",
            "S78689143": "Health Economics, Policy and Law",
            "S4210168539": "Science and Public Policy",
            "S129664799": "Policy and Society",
            "S2170549": "Policy & Internet",
            "S4210205184": "Behavioural Public Policy",
            "S4210206727": "J. of Behavioral Public Administration",
            "S39541053": "International J. of Public Administration",
            "S20798355": "J. of Environmental Policy & Planning",
            "S2764352865": "Transylvanian Review of Administrative Sciences",
            "S22371039": "J. of European Public Policy",
            "S4210228320": "European Policy Analysis",
            "S13135386": "NISPAcee J. of Public Administration and Policy",
            "S189395249": "Public Administration and Development",
            "S143207802": "J. of Asian Public Policy",
            "S4210170541": "Asia Pacific J. of Public Administration",
            "S4210183829": "J. of Chinese Governance",
            "S2764770023": "International Review of Public Administration",
            "S122892125": "Asian Politics & Policy",
            "S2738535301": "Asia & the Pacific Policy Studies",
            "S4210231999": "Chinese Public Administration Review",
            "S4387279324": "J. of Policy Studies",
            "S4210225381": "Public Administration and Policy",
            "S167828324": "Latin American Policy",
            "S2764645683": "Indian J. of Public Administration",
        },
        # KCI 학술지명 (부분일치 검색)
        "kci_journals": [
            "한국행정학보",
            "한국정책학회보",
            "행정논총",
            "한국사회와 행정연구",
            "정부학연구",
            "지방정부연구",
            "한국조직학회보",
            "한국인사행정학회보",
            "한국행정연구",
        ],
    },
    {
        "key": "methodology",
        "name": "사회과학방법론",
        "openalex_sources": {
            "S9536269": "Sociological Methods & Research",
            "S29331042": "Political Analysis",
            "S45419345": "Psychological Methods",
            "S4210173062": "Advances in Methods and Practices in Psychological Science",
            "S133599136": "Organizational Research Methods",
            "S3162283": "Journal of Mixed Methods Research",
            "S83253694": "Field Methods",
            "S102399824": "Quality & Quantity",
            "S125130336": "International J. of Social Research Methodology",
            "S181883320": "Sociological Methodology",
            "S186480540": "Psychometrika",
            "S78020522": "Structural Equation Modeling",
            "S64250036": "Multivariate Behavioral Research",
            "S53135262": "J. of Educational and Behavioral Statistics",
            "S190099528": "British J. of Mathematical and Statistical Psychology",
            "S137478622": "Behavior Research Methods",
            "S94663699": "Applied Psychological Measurement",
            "S176831015": "Educational and Psychological Measurement",
            "S135539873": "Public Opinion Quarterly",
            "S18835586": "Evaluation Review",
            "S25376279": "American J. of Evaluation",
            "S4210204360": "J. of Survey Statistics and Methodology",
            "S79505318": "J. of Official Statistics",
        },
        "kci_journals": [
            "조사연구",
        ],
    },
    {
        "key": "econ-stats",
        "name": "계량경제·통계",
        "openalex_sources": {
            "S95464858": "Econometrica",
            "S127742747": "Journal of Econometrics",
            "S49389958": "Econometric Theory",
            "S85739584": "J. of Applied Econometrics",
            "S18095783": "J. of Business & Economic Statistics",
            "S134988049": "Econometric Reviews",
            "S33519306": "The Econometrics Journal",
            "S156003414": "Quantitative Economics",
            "S4210169353": "Journal of Causal Inference",
            "S180061323": "Review of Economics and Statistics",
            "S207154782": "J. of Financial Econometrics",
            "S2898363556": "Econometrics and Statistics",
            "S4394736638": "J. of the American Statistical Association",
            "S185328345": "J. Royal Statistical Society A",
            "S145009937": "J. Royal Statistical Society B",
            "S2764642956": "J. Royal Statistical Society C",
            "S119757635": "Annals of Statistics",
            "S112778392": "Annals of Applied Statistics",
            "S12967704": "Statistical Science",
            "S4179095": "The American Statistician",
            "S172180718": "Biometrika",
            "S8265502": "Biometrics",
            "S127898559": "Bayesian Analysis",
            "S5437875": "Statistics and Computing",
            "S167961193": "Journal of Statistical Software",
            "S76159266": "J. of Computational and Graphical Statistics",
        },
        "kci_journals": [],
    },
    {
        "key": "ai-ml",
        "name": "AI·머신러닝",
        # 2026-08-23 신설. 학술지별 90일 물량을 OpenAlex로 실측해 선별함(주석의 편수는 실측 당시 기준).
        # 선별 기준: (1) AI/ML이 주력인 학술지만 — 종합지(PNAS Nexus·Nature Human Behaviour)는
        # AI 아닌 논문이 대량 유입되어 제외 (2) 공학 중심 고물량지 제외 — Neural Networks(385),
        # Information Fusion(214), Applied Intelligence(122), MLST(113), AI Review(95),
        # ACM Computing Surveys(85), IEEE TKDE(73), J. of Big Data(74) (3) 학회 프로시딩
        # (NeurIPS·ICML·ICLR·AAAI·ACL)·arXiv는 색인되면 물량 폭주 위험이라 제외.
        # 주제당 수집 상한은 1,600편(200편 x 8페이지)이므로 합계가 이에 근접하면 오래된 논문부터 잘림.
        "openalex_sources": {
            # --- AI 거버넌스·정책·윤리 (행정학 적합도 최상) 약 588편
            "S4210190517": "AI & Society",                        # 191
            "S4210170699": "AI and Ethics",                       # 167
            "S23735784": "Philosophy & Technology",               # 54
            "S120991925": "Telecommunications Policy",            # 46
            "S2736409588": "Big Data & Society",                  # 41
            "S160466889": "Minds and Machines",                   # 15
            "S201710173": "Government Information Quarterly",     # 15
            "S13096939": "Ethics and Information Technology",     # 13
            "S4210186663": "J. of Responsible Technology",        # 12
            "S2181421": "Science, Technology & Human Values",     # 11
            "S2764374723": "Information Polity",                  # 10
            "S4210232200": "Digital Government: Research and Practice",  # 7
            "S4210177192": "Internet Policy Review",              # 4
            "S4210198237": "Data & Policy",                       # 2
            # --- 계산사회과학·데이터과학 (방법론 적용) 약 239편
            "S2492086750": "ACM Trans. on Intelligent Systems and Technology",  # 58
            "S98984247": "Computational Economics",               # 46
            "S4210198061": "Patterns",                            # 39
            "S121920818": "Data Mining and Knowledge Discovery",  # 32
            "S2504380752": "EPJ Data Science",                    # 27
            "S127118166": "Social Science Computer Review",       # 13
            "S4306511929": "Harvard Data Science Review",         # 13
            "S4210196583": "J. of Computational Social Science",  # 11
            # --- 핵심 AI/ML 저널 (연구동향 파악) 약 207편
            "S62148650": "Machine Learning",                      # 70
            "S2912241403": "Nature Machine Intelligence",         # 52
            "S139930977": "J. of Artificial Intelligence Research",  # 49
            "S196139623": "Artificial Intelligence",              # 21
            "S163019073": "AI Magazine",                          # 약 10
            # IEEE 2종은 OpenAlex 색인 지연으로 실제 유입이 거의 없음(TPAMI 2편·TNNLS 3편) —
            # 넣어둬도 부담은 없으나 "커버된다"고 기대하면 안 됨
            "S199944782": "IEEE Trans. on Pattern Analysis and Machine Intelligence",
            "S4210175523": "IEEE Trans. on Neural Networks and Learning Systems",
        },
        # KCI 부분일치 실측(2026-08-23, 최근 90일): 정보화정책 10편(정보통신정책연구 포함),
        # 지능정보연구 17편, 과학기술학연구 13편, 한국지역정보화학회지 6편,
        # 한국빅데이터 15편, 인공지능 34편(인공지능윤리연구·AI와 인간사회 등 5종) — 합계 약 95편
        "kci_journals": [
            "정보화정책",
            "지능정보연구",
            "과학기술학연구",
            "한국지역정보화학회지",
            "한국빅데이터",
            "인공지능",
        ],
    },
]

SKIP_TITLE_PREFIXES = (
    "supplemental material", "correction to", "correction:", "erratum",
    "retraction", "editorial board", "issue information", "front matter",
    "back matter", "list of reviewers", "reviewer acknowledg",
)


# ---------------------------------------------------------------- HTTP 공통
def http_get(url, timeout=60, retries=3, headers=None):
    """GET 요청. 429/5xx는 지수 백오프로 재시도. 실패 시 None."""
    hdrs = {"User-Agent": "research-paper-alert (mailto:%s)" % MAILTO}
    if headers:
        hdrs.update(headers)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = 8 * (attempt + 1)
                print("  HTTP %d, %d초 후 재시도: %s" % (e.code, wait, url[:120]))
                time.sleep(wait)
                continue
            print("  HTTP 오류 %d: %s" % (e.code, url[:120]))
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            print("  요청 실패: %s (%s)" % (url[:120], e))
            return None
    return None


def http_get_json(url, **kw):
    raw = http_get(url, **kw)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        print("  JSON 파싱 실패: %s" % url[:120])
        return None


# ---------------------------------------------------------------- OpenAlex
def invert_abstract(inv):
    """OpenAlex abstract_inverted_index → 본문 텍스트."""
    if not inv:
        return ""
    try:
        pairs = []
        for word, positions in inv.items():
            for p in positions:
                pairs.append((p, word))
        pairs.sort(key=lambda x: x[0])
        return " ".join(w for _, w in pairs).strip()
    except Exception:
        return ""


def fetch_openalex(topic):
    """주제별 학술지 목록에서 최근 FETCH_DAYS일 발행 논문 수집."""
    ids = "|".join(topic["openalex_sources"].keys())
    date_from = (TODAY - timedelta(days=FETCH_DAYS)).isoformat()
    select = ("id,doi,display_name,publication_date,authorships,"
              "primary_location,open_access,abstract_inverted_index,type")
    records = []
    page = 1
    while page <= 8:
        params = urllib.parse.urlencode({
            "filter": "primary_location.source.id:%s,from_publication_date:%s" % (ids, date_from),
            "select": select,
            "per-page": "200",
            "page": str(page),
            "sort": "publication_date:desc",
            "mailto": MAILTO,
        })
        data = http_get_json("https://api.openalex.org/works?" + params)
        if not data or not data.get("results"):
            break
        for w in data["results"]:
            rec = openalex_record(w, topic)
            if rec:
                records.append(rec)
        if len(data["results"]) < 200:
            break
        page += 1
        time.sleep(1.5)
    print("[OpenAlex] %s: %d건" % (topic["name"], len(records)))
    return records


def openalex_record(w, topic):
    title = (w.get("display_name") or "").strip()
    if not title:
        return None
    low = title.lower()
    if any(low.startswith(p) for p in SKIP_TITLE_PREFIXES):
        return None
    if w.get("type") not in ("article", "review", None):
        return None
    doi = (w.get("doi") or "").strip()
    if doi.endswith(".supp"):
        return None
    wid = (w.get("id") or "").rsplit("/", 1)[-1]
    if not wid:
        return None
    authors = []
    for a in (w.get("authorships") or [])[:10]:
        name = ((a.get("author") or {}).get("display_name") or "").strip()
        if name:
            authors.append(name)
    src = ((w.get("primary_location") or {}).get("source") or {})
    journal = (src.get("display_name") or "").strip()
    if not journal:
        journal = topic["openalex_sources"].get(src.get("id", "").rsplit("/", 1)[-1], "")
    oa = w.get("open_access") or {}
    url = doi or ((w.get("primary_location") or {}).get("landing_page_url") or "")
    return {
        "id": "oa:" + wid,
        "topic": topic["key"],
        "origin": "OpenAlex",
        "title": title,
        "authors": authors,
        "journal": journal,
        "date": w.get("publication_date") or "",
        "abstract": invert_abstract(w.get("abstract_inverted_index")),
        "url": url or ("https://openalex.org/" + wid),
        "doi": doi.replace("https://doi.org/", "") if doi else "",
        "pdf": (oa.get("oa_url") or "") if oa.get("is_oa") else "",
    }


# ---------------------------------------------------------------- KCI
def _findtext_any(el, names):
    """태그명이 names(소문자) 중 하나인 첫 자손 요소의 텍스트."""
    for node in el.iter():
        tag = node.tag.split("}")[-1].lower()
        if tag in names and (node.text or "").strip():
            return node.text.strip()
    return ""


def fetch_kci(topic):
    """KCI 오픈API articleSearch. 키가 없으면 빈 목록.

    주의: KCI 응답 규격은 키 발급 후 첫 실행에서 확인 필요.
    파싱 실패 시 Actions 로그에 원문 일부를 남긴다.
    """
    records = []
    if not KCI_API_KEY:
        return records, "미등록"
    # KCI dateFrom/dateTo는 발행년월 YYYYMM 6자리 형식
    date_from = (TODAY - timedelta(days=FETCH_DAYS)).strftime("%Y%m")
    date_to = TODAY.strftime("%Y%m")
    errors = []
    for journal in topic["kci_journals"]:
        params = urllib.parse.urlencode({
            "apiCode": "articleSearch",
            "key": KCI_API_KEY,
            "journal": journal,
            "dateFrom": date_from,
            "dateTo": date_to,
            "displayCount": "100",
            "page": "1",
        })
        raw = http_get("https://open.kci.go.kr/po/openapi/openApiSearch.kci?" + params)
        time.sleep(1.0)
        if raw is None:
            errors.append("%s: 요청 실패" % journal)
            continue
        try:
            root = ET.fromstring(raw.encode("utf-8"))
        except ET.ParseError as e:
            errors.append("%s: XML 파싱 실패" % journal)
            print("  [KCI] %s 응답 파싱 실패(%s). 응답 앞부분: %s" % (journal, e, raw[:300]))
            continue
        found = 0
        for node in root.iter():
            if node.tag.split("}")[-1].lower() != "record":
                continue
            art = None
            for child in node.iter():
                if child.tag.split("}")[-1].lower() == "articleinfo":
                    art = child
                    break
            base = art if art is not None else node
            art_id = ""
            if art is not None:
                for k, v in art.attrib.items():
                    if k.split("}")[-1].lower() in ("article-id", "articleid", "id"):
                        art_id = v.strip()
                        break
            title = _findtext_any(base, {"article-title", "articletitle", "title-kor", "title"})
            if not title:
                continue
            jname = _findtext_any(node, {"journal-name", "journalname", "journal"}) or journal
            year = _findtext_any(node, {"pub-year", "pubyear", "publication-year"})
            mon = _findtext_any(node, {"pub-mon", "pubmon", "publication-month"})
            date = ""
            if year:
                date = year
                if mon:
                    date += "-" + mon.zfill(2)
            auths = []
            for a in node.iter():
                if a.tag.split("}")[-1].lower() == "author" and (a.text or "").strip():
                    # "이영규(건국대학교 시민정치연구소)" → "이영규"
                    name = re.sub(r"\([^)]*\)", "", a.text).strip()
                    if name:
                        auths.append(name)
            abstract = _findtext_any(base, {"abstract", "abstract-kor", "abstractkor"})
            url = _findtext_any(base, {"url"})
            doi = _findtext_any(base, {"doi"})
            if not art_id:
                art_id = doi or hashlib.md5((title + jname).encode("utf-8")).hexdigest()[:16]
            if not url and art_id.startswith("ART"):
                url = ("https://www.kci.go.kr/kciportal/ci/sereArticleSearch/"
                       "ciSereArtiView.kci?sereArticleSearchBean.artiId=" + art_id)
            records.append({
                "id": "kci:" + art_id,
                "topic": topic["key"],
                "origin": "KCI",
                "title": title,
                "authors": auths[:10],
                "journal": jname,
                "date": date,
                "abstract": abstract,
                "url": url or "https://www.kci.go.kr/",
                "doi": doi.replace("https://doi.org/", "") if doi else "",
                "pdf": "",
            })
            found += 1
        if found == 0:
            m = re.search(r"<resultMsg>([^<]*)</resultMsg>", raw)
            msg = m.group(1).strip() if m else ""
            if "등록되지 않은" in msg:
                # KCI는 등록 IP에서만 키를 인정 → 이 환경에서는 호출 불가.
                # 국내 수집은 PC의 kci_fetch.ps1이 data/kci.json으로 공급한다.
                errors.append("IP 제한")
                print("  [KCI] %s → 이 환경에서 직접 호출 불가, 나머지 생략" % msg)
                break
            mo = re.search(r"<outputData>.*?</outputData>", raw, re.S)
            snippet = re.sub(r"\s+", " ", mo.group(0) if mo else raw)[:400]
            print("  [KCI] %s: 0건 (outputData: %s)" % (journal, snippet))
    status = "정상" if not errors else "일부 오류(" + "; ".join(errors[:3]) + ")"
    n = len(records)
    print("[KCI] %s: %d건 (%s)" % (topic["name"], n, status))
    return records, status


# ---------------------------------------------------------------- 초록 보충
def strip_jats(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def lookup_abstract(doi):
    """Crossref → Semantic Scholar → Springer 순으로 초록 조회."""
    # 1) Crossref
    data = http_get_json("https://api.crossref.org/works/%s?mailto=%s"
                         % (urllib.parse.quote(doi), MAILTO), retries=2)
    if data:
        abs_ = strip_jats((data.get("message") or {}).get("abstract") or "")
        if len(abs_) > 40:
            return abs_
    time.sleep(1.0)
    # 2) Semantic Scholar
    data = http_get_json("https://api.semanticscholar.org/graph/v1/paper/DOI:%s?fields=abstract"
                         % urllib.parse.quote(doi), retries=2)
    if data and data.get("abstract"):
        abs_ = re.sub(r"\s+", " ", data["abstract"]).strip()
        if len(abs_) > 40:
            return abs_
    time.sleep(1.0)
    # 3) Springer (선택)
    if SPRINGER_API_KEY and doi.startswith("10.1007/"):
        data = http_get_json("https://api.springernature.com/meta/v2/json?q=doi:%s&api_key=%s"
                             % (urllib.parse.quote(doi), SPRINGER_API_KEY), retries=2)
        if data and data.get("records"):
            abs_ = data["records"][0].get("abstract") or ""
            if isinstance(abs_, dict):
                abs_ = " ".join(str(v) for v in abs_.values())
            abs_ = strip_jats(str(abs_))
            if len(abs_) > 40:
                return abs_
    return ""


def enrich_abstracts(state):
    """초록 없는 논문에 대해 보충 조회 (실행당 ABS_LOOKUP_CAP건, 논문당 최대 3회 시도)."""
    done = 0
    for rec in state["papers"].values():
        if done >= ABS_LOOKUP_CAP:
            break
        if rec.get("abstract") or not rec.get("doi"):
            continue
        if rec.get("abs_tries", 0) >= 3:
            continue
        abs_ = lookup_abstract(rec["doi"])
        rec["abs_tries"] = rec.get("abs_tries", 0) + 1
        done += 1
        if abs_:
            rec["abstract"] = abs_
            rec["abs_src"] = "보충"
        time.sleep(1.5)
    if done:
        print("[초록 보충] %d건 조회" % done)


def google_translate_ko(text):
    """무키 Google 번역 엔드포인트. 실패 시 예외 발생."""
    base = ("https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=auto&tl=ko&dt=t")
    body = urllib.parse.urlencode({"q": text}).encode("utf-8")
    req = urllib.request.Request(base, data=body, headers={
        "User-Agent": "Mozilla/5.0 (research-paper-alert)",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    segs = data[0] if data and isinstance(data, list) else []
    return "".join(s[0] for s in segs if s and s[0]).strip()


def translate_abstracts(state):
    """해외(영문) 초록에 한국어 자동 번역을 붙인다 — 최신 논문 우선, 실행당 상한."""
    todo = [r for r in state["papers"].values()
            if r.get("origin") == "OpenAlex" and r.get("abstract")
            and not r.get("abstract_ko") and r.get("ko_tries", 0) < 3]
    todo.sort(key=lambda r: r.get("first_seen", ""), reverse=True)
    done = ok = fails = cooldowns = 0
    for rec in todo:
        if done >= TRANSLATE_CAP:
            break
        if fails >= 3:
            # 연속 실패 = IP 단위 속도 제한. 러너 IP는 실행마다 바뀌므로
            # 한 번만 재시도해보고 안 되면 다음 실행으로 넘긴다.
            if cooldowns >= 1:
                break
            cooldowns += 1
            print("  번역 연속 실패 — 60초 쿨다운 후 재개 (%d/1)" % cooldowns)
            time.sleep(60)
            fails = 0
        done += 1
        try:
            ko = google_translate_ko(rec["abstract"][:1500])
            if len(ko) > 20:
                rec["abstract_ko"] = ko
                ok += 1
                fails = 0
            else:
                rec["ko_tries"] = rec.get("ko_tries", 0) + 1
        except Exception as e:
            fails += 1
            rec["ko_tries"] = rec.get("ko_tries", 0) + 1
            print("  번역 실패(연속 %d): %s" % (fails, e))
        time.sleep(1.0)
    if done:
        print("[번역] %d건 시도, %d건 성공 (남은 대기 %d건)"
              % (done, ok, max(0, len(todo) - done)))


def load_kci_file():
    """PC(등록 IP)에서 수집해 커밋한 data/kci.json — KCI IP 제한 우회 경로."""
    path = os.path.join(DATA_DIR, "kci.json")
    if not os.path.exists(path):
        return [], None
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
        recs = [r for r in data.get("records", []) if r.get("id") and r.get("title")]
        return recs, data.get("fetched_at")
    except Exception as e:
        print("kci.json 읽기 실패: %s" % e)
        return [], None


def write_kci_config():
    """PC 수집 스크립트(kci_fetch.ps1)가 읽는 학술지 목록 — TOPICS와 자동 동기화."""
    cfg = [{"topic": t["key"], "name": t["name"], "journals": t["kci_journals"]}
           for t in TOPICS]
    with open(os.path.join(DATA_DIR, "kci_config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- 상태 관리
def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("상태 파일 읽기 실패, 새로 시작: %s" % e)
    return {"papers": {}}


def merge_records(state, records, backdate, fresh_topics=()):
    """backdate가 참이거나 레코드의 주제가 fresh_topics(이번에 새로 추가된 주제)에 속하면
    first_seen을 소급 기록해 NEW 배지·이메일·브리핑에서 제외한다."""
    now_iso = NOW.isoformat(timespec="seconds")
    backdated = (NOW - timedelta(days=NEW_DAYS + 1)).isoformat(timespec="seconds")
    added = 0
    for rec in records:
        old = state["papers"].get(rec["id"])
        if old is None:
            back = backdate or rec.get("topic") in fresh_topics
            rec["first_seen"] = backdated if back else now_iso
            state["papers"][rec["id"]] = rec
            added += 1
        else:
            first_seen = old.get("first_seen", now_iso)
            abs_tries = old.get("abs_tries", 0)
            old_abs = old.get("abstract", "")
            old_abs_src = old.get("abs_src", "")
            old_ko = old.get("abstract_ko", "")
            ko_tries = old.get("ko_tries", 0)
            old.update(rec)
            old["first_seen"] = first_seen
            old["abs_tries"] = abs_tries
            if not old.get("abstract") and old_abs:
                old["abstract"] = old_abs
                if old_abs_src:
                    old["abs_src"] = old_abs_src
            # 초록이 그대로면 기존 번역 유지, 내용이 바뀌었으면 재번역 대상
            if old.get("abstract", "") == old_abs:
                if old_ko:
                    old["abstract_ko"] = old_ko
                old["ko_tries"] = ko_tries
            else:
                old["ko_tries"] = 0
    return added


def prune_state(state):
    cutoff = (TODAY - timedelta(days=PRUNE_DAYS)).isoformat()
    drop = []
    for pid, rec in state["papers"].items():
        d = rec.get("date") or ""
        if d and len(d) >= 7 and (d + "-01")[:10] < cutoff:
            drop.append(pid)
    for pid in drop:
        del state["papers"][pid]


# ---------------------------------------------------------------- 출력
def paper_sort_key(rec):
    return (rec.get("date") or "0000", rec.get("first_seen") or "")


def build_outputs(state, kci_status):
    new_cut = (NOW - timedelta(days=NEW_DAYS)).isoformat(timespec="seconds")
    show_cut = (TODAY - timedelta(days=FETCH_DAYS + 30)).isoformat()
    topics_out = []
    for topic in TOPICS:
        papers = []
        for rec in state["papers"].values():
            if rec.get("topic") != topic["key"]:
                continue
            d = rec.get("date") or ""
            d_full = (d + "-01-01")[:10] if d else ""
            if d_full and d_full < show_cut:
                continue
            item = dict(rec)
            item["is_new"] = rec.get("first_seen", "") >= new_cut
            item.pop("abs_tries", None)
            item.pop("ko_tries", None)
            papers.append(item)
        papers.sort(key=paper_sort_key, reverse=True)
        topics_out.append({
            "key": topic["key"],
            "name": topic["name"],
            "count": len(papers),
            "new_count": sum(1 for p in papers if p["is_new"]),
            "papers": papers,
        })
    out = {
        "generated_at": NOW.isoformat(timespec="seconds"),
        "generated_at_display": NOW.strftime("%Y-%m-%d %H:%M KST"),
        "dashboard": DASHBOARD_URL,
        "kci_status": kci_status,
        "topics": topics_out,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    write_html(out)
    return out


def esc(s):
    return html.escape(s or "", quote=True)


def render_card(p):
    badges = []
    if p["is_new"]:
        badges.append('<span class="badge new">NEW</span>')
    badges.append('<span class="badge origin">%s</span>' % esc(p["origin"]))
    authors = ", ".join(p.get("authors") or [])
    if len(p.get("authors") or []) >= 10:
        authors += " 외"
    meta_bits = [b for b in (esc(p.get("journal")), esc(p.get("date")), esc(authors)) if b]
    abstract = (p.get("abstract") or "").strip()
    if len(abstract) > 1800:
        abstract = abstract[:1800].rsplit(" ", 1)[0] + " …"
    ko = (p.get("abstract_ko") or "").strip()
    if len(ko) > 1800:
        ko = ko[:1800].rsplit(" ", 1)[0] + " …"
    if abstract and ko:
        abs_html = ('<details><summary>초록 보기</summary>'
                    '<p class="abslabel">한국어 자동 번역</p><p class="abstract">%s</p>'
                    '<p class="abslabel">원문</p><p class="abstract orig">%s</p>'
                    '</details>' % (esc(ko), esc(abstract)))
    elif abstract:
        abs_html = ('<details><summary>초록 보기</summary>'
                    '<p class="abstract">%s</p></details>' % esc(abstract))
    else:
        abs_html = '<p class="noabs">초록 미제공 — 원문 링크에서 확인</p>'
    links = ['<a href="%s" target="_blank" rel="noopener">원문 페이지</a>' % esc(p.get("url"))]
    if p.get("pdf"):
        links.append('<a href="%s" target="_blank" rel="noopener">무료 전문(PDF) 🔓</a>' % esc(p["pdf"]))
    return (
        '<article class="card%s" data-j="%s">'
        '<div class="badges">%s</div>'
        '<h3><a href="%s" target="_blank" rel="noopener">%s</a></h3>'
        '<p class="meta">%s</p>'
        '%s'
        '<p class="links">%s</p>'
        '</article>'
    ) % (
        " isnew" if p["is_new"] else "",
        esc(p.get("journal")),
        "".join(badges),
        esc(p.get("url")), esc(p.get("title")),
        " · ".join(meta_bits),
        abs_html,
        " · ".join(links),
    )


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>연구동향 알리미</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📚</text></svg>">
<style>
:root { --bg:#f6f7f9; --card:#ffffff; --ink:#1c2733; --sub:#5a6b7b; --line:#e3e8ee;
        --accent:#2563eb; --new:#dc2626; --chip:#eef2f7; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#10161d; --card:#1a232e; --ink:#e8eef4; --sub:#94a6b8; --line:#2a3645;
          --accent:#60a5fa; --new:#f87171; --chip:#243040; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font-family:'Malgun Gothic','Apple SD Gothic Neo',system-ui,sans-serif; }
.wrap { max-width:860px; margin:0 auto; padding:16px 14px 60px; }
header h1 { font-size:1.45rem; margin:6px 0 2px; }
header .sub { color:var(--sub); font-size:.85rem; margin:0 0 14px; }
.tabs { display:flex; gap:8px; margin:0 0 10px; flex-wrap:wrap; }
.tabs button { flex:1; min-width:180px; padding:10px 12px; border-radius:10px;
  border:1px solid var(--line); background:var(--card); color:var(--ink);
  font-size:.95rem; cursor:pointer; }
.tabs button.active { border-color:var(--accent); color:var(--accent); font-weight:700; }
.tabs .cnt { color:var(--sub); font-weight:400; font-size:.85rem; }
.tabs .newcnt { color:var(--new); font-weight:700; font-size:.85rem; }
#q { width:100%; padding:11px 14px; border-radius:10px; border:1px solid var(--line);
     background:var(--card); color:var(--ink); font-size:.95rem; margin:0 0 14px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px;
        padding:14px 16px; margin:0 0 10px; }
.card.isnew { border-left:4px solid var(--new); }
.card h3 { margin:6px 0 6px; font-size:1.02rem; line-height:1.45; }
.card h3 a { color:var(--ink); text-decoration:none; }
.card h3 a:hover { color:var(--accent); }
.badges { display:flex; gap:6px; }
.badge { font-size:.7rem; padding:2px 8px; border-radius:99px; background:var(--chip); color:var(--sub); }
.badge.new { background:var(--new); color:#fff; font-weight:700; }
.meta { color:var(--sub); font-size:.83rem; margin:0 0 6px; }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin:0 0 12px; }
.chip { font-size:.78rem; padding:5px 10px; border-radius:99px; border:1px solid var(--line);
        background:var(--card); color:var(--sub); cursor:pointer; }
.chip.active { background:var(--accent); border-color:var(--accent); color:#fff; font-weight:700; }
details summary { cursor:pointer; color:var(--accent); font-size:.87rem; margin:4px 0; }
.abslabel { font-size:.72rem; color:var(--sub); font-weight:700; margin:8px 0 0; }
.abstract { font-size:.88rem; line-height:1.6; color:var(--ink); margin:6px 0; }
.abstract.orig { color:var(--sub); }
.noabs { color:var(--sub); font-size:.83rem; margin:6px 0; }
.links { font-size:.85rem; margin:8px 0 0; }
.links a { color:var(--accent); text-decoration:none; }
.empty { color:var(--sub); text-align:center; padding:40px 0; }
footer { color:var(--sub); font-size:.78rem; margin-top:26px; line-height:1.7;
         border-top:1px solid var(--line); padding-top:14px; }
footer a { color:var(--accent); }
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>📚 연구동향 알리미</h1>
  <p class="sub">마지막 갱신: __UPDATED__ · 매일 아침 자동 갱신 · 최근 __DAYS__일 발행분</p>
</header>
<div class="tabs">__TABS__</div>
<input id="q" type="search" placeholder="제목·저자·학술지·초록 검색…">
__SECTIONS__
<footer>
  데이터: OpenAlex(해외 학술지) · KCI 오픈API(국내 학술지 — 상태: __KCI__)<br>
  __KCI_HINT__
  초록이 없는 논문은 출판사가 공개 API에 초록을 제공하지 않는 경우입니다(원문 페이지에서 확인 가능).<br>
  해외 논문 초록의 한국어 번역은 자동 번역 결과이므로 참고용으로만 이용하세요.<br>
  <a href="__REPO__" target="_blank" rel="noopener">GitHub 저장소</a> ·
  <a href="data/papers.json" target="_blank" rel="noopener">papers.json</a> ·
  학술지 목록 조정: papers.py 상단 TOPICS
</footer>
</div>
<script>
var tabs = document.querySelectorAll(".tabs button");
var secs = document.querySelectorAll("section.topic");
function show(key) {
  tabs.forEach(function(b){ b.classList.toggle("active", b.dataset.key === key); });
  secs.forEach(function(s){ s.style.display = (s.dataset.key === key) ? "" : "none"; });
  filter();
}
tabs.forEach(function(b){ b.addEventListener("click", function(){ show(b.dataset.key); }); });
var q = document.getElementById("q");
function filter() {
  var t = q.value.trim().toLowerCase();
  secs.forEach(function(s){
    if (s.style.display === "none") return;
    var chip = s.querySelector(".chip.active");
    var j = chip ? chip.dataset.j : "";
    var n = 0;
    s.querySelectorAll("article.card").forEach(function(c){
      var hit = (!t || c.textContent.toLowerCase().indexOf(t) !== -1) &&
                (!j || c.dataset.j === j);
      c.style.display = hit ? "" : "none";
      if (hit) n++;
    });
    var e = s.querySelector("p.empty:last-of-type");
    if (e) e.style.display = n ? "none" : "";
  });
}
q.addEventListener("input", filter);
document.querySelectorAll(".chips .chip").forEach(function(ch){
  ch.addEventListener("click", function(){
    ch.closest(".chips").querySelectorAll(".chip").forEach(function(x){ x.classList.remove("active"); });
    ch.classList.add("active");
    filter();
  });
});
if (tabs.length) show(tabs[0].dataset.key);
</script>
</body>
</html>
"""


def write_html(out):
    tabs = []
    sections = []
    for t in out["topics"]:
        newtxt = ' <span class="newcnt">+%d</span>' % t["new_count"] if t["new_count"] else ""
        tabs.append('<button data-key="%s">%s <span class="cnt">%d편</span>%s</button>'
                    % (esc(t["key"]), esc(t["name"]), t["count"], newtxt))
        jcounts = {}
        for p in t["papers"]:
            j = p.get("journal") or "기타"
            jcounts[j] = jcounts.get(j, 0) + 1
        chips = ['<button class="chip active" data-j="">전체 %d</button>' % t["count"]]
        for j, n in sorted(jcounts.items(), key=lambda x: (-x[1], x[0])):
            chips.append('<button class="chip" data-j="%s">%s %d</button>'
                         % (esc(j), esc(j), n))
        cards = "".join(render_card(p) for p in t["papers"])
        sections.append('<section class="topic" data-key="%s">'
                        '<div class="chips">%s</div>%s'
                        '<p class="empty" style="display:none">조건에 맞는 논문이 없습니다.</p></section>'
                        % (esc(t["key"]), "".join(chips),
                           cards or '<p class="empty">표시할 논문이 없습니다.</p>'))
    kci_hint = ""
    if out["kci_status"] == "미등록":
        kci_hint = ("국내 학술지 수집은 KCI API 키 등록 후 자동 시작됩니다 "
                    "(README 참고).<br>")
    page = (HTML_TEMPLATE
            .replace("__UPDATED__", esc(out["generated_at_display"]))
            .replace("__DAYS__", str(FETCH_DAYS))
            .replace("__TABS__", "".join(tabs))
            .replace("__SECTIONS__", "".join(sections))
            .replace("__KCI__", esc(out["kci_status"]))
            .replace("__KCI_HINT__", kci_hint)
            .replace("__REPO__", REPO_URL))
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(page)


# ---------------------------------------------------------------- main
def main():
    state = load_state()
    bootstrap = not state["papers"]
    if bootstrap:
        print("첫 실행: NEW 배지 없이 초기 목록만 구축합니다.")
    backdate = bootstrap or BACKDATE_NEW
    if BACKDATE_NEW:
        print("BACKDATE_NEW: 이번 실행의 신규 논문은 NEW로 표시하지 않습니다.")
    # TOPICS에 주제를 새로 추가하면 첫 수집에서 수백 편이 한꺼번에 NEW로 잡혀
    # 배지·이메일·브리핑이 폭주한다. 상태 파일에 기록이 없는 주제는 자동으로 소급 처리한다.
    known_topics = set(r.get("topic") for r in state["papers"].values())
    fresh_topics = set(t["key"] for t in TOPICS if t["key"] not in known_topics)
    if fresh_topics and not backdate:
        print("새 주제 %s: 첫 수집이므로 NEW로 표시하지 않습니다."
              % ", ".join(sorted(fresh_topics)))
    total_added = 0
    kci_live_total = 0
    for topic in TOPICS:
        recs = fetch_openalex(topic)
        total_added += merge_records(state, recs, backdate, fresh_topics)
        time.sleep(1.5)
        kci_recs, _ = fetch_kci(topic)
        kci_live_total += len(kci_recs)
        total_added += merge_records(state, kci_recs, backdate, fresh_topics)
    kci_file_recs, kci_fetched_at = load_kci_file()
    if kci_file_recs:
        total_added += merge_records(state, kci_file_recs, backdate, fresh_topics)
    if kci_live_total:
        kci_status = "정상(직접 호출)"
    elif kci_file_recs:
        stamp = (kci_fetched_at or "")[:16].replace("T", " ")
        kci_status = "정상 — PC 수집 %d건 (%s)" % (len(kci_file_recs), stamp)
    elif KCI_API_KEY:
        kci_status = "키 등록됨 · PC 수집 대기 중"
    else:
        kci_status = "미등록"
    enrich_abstracts(state)
    translate_abstracts(state)
    prune_state(state)
    os.makedirs(DATA_DIR, exist_ok=True)
    write_kci_config()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    out = build_outputs(state, kci_status)
    print("신규 %d건 · 전체 %d건 · 생성 완료(%s)"
          % (total_added, sum(t["count"] for t in out["topics"]), out["generated_at_display"]))


if __name__ == "__main__":
    main()
