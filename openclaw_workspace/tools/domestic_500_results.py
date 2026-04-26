from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

import requests


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
}


def _looks_like_captcha(html: str) -> bool:
    t = html or ""
    return any(k in t for k in ("验证码", "安全验证", "人机验证", "verify", "captcha"))


def build_500_trade_results_url(*, date: Optional[str] = None) -> str:
    base = "https://trade.500.com/jczq/"
    if date:
        return f"{base}?playid=312&g=2&date={date}"
    return f"{base}?playid=312&g=2"


def build_500_zx_results_url() -> str:
    return "https://zx.500.com/jczq/"


def _normalize_kickoff_time(*, date: str, kickoff_raw: str) -> str:
    kickoff_raw = re.sub(r"[\u00a0\s]+", " ", kickoff_raw or "").strip()
    m = re.search(r"(?P<mm>\d{2})-(?P<dd>\d{2})\s+(?P<hh>\d{2}):(?P<mi>\d{2})", kickoff_raw)
    if m:
        year = date.split("-", 1)[0]
        return f"{year}-{m.group('mm')}-{m.group('dd')} {m.group('hh')}:{m.group('mi')}"
    m = re.search(r"(?P<yyyy>\d{4})-(?P<mm>\d{2})-(?P<dd>\d{2})\s+(?P<hh>\d{2}):(?P<mi>\d{2})", kickoff_raw)
    if m:
        return f"{m.group('yyyy')}-{m.group('mm')}-{m.group('dd')} {m.group('hh')}:{m.group('mi')}"
    return f"{date} 00:00"


def _clean_team_name(name: str) -> str:
    t = (name or "").strip()
    t = re.sub(r"\[[^\]]{1,8}\]", "", t)
    t = re.sub(r"^\*+|\*+$", "", t).strip()
    t = re.sub(r"[\u00a0\s]+", " ", t).strip()
    t = re.sub(r"[()（）【】\[\]]", "", t).strip()
    return t


def _extract_score(text: str) -> Optional[str]:
    if not text:
        return None
    for m in re.finditer(r"(?<!\d)(\d{1,2})\s*:\s*(\d{1,2})(?!\d)", text):
        raw = m.group(0).strip()
        if re.fullmatch(r"\d{2}:\d{2}", raw):
            continue
        hg = int(m.group(1))
        ag = int(m.group(2))
        if 0 <= hg <= 10 and 0 <= ag <= 10:
            return f"{hg}-{ag}"

    for m in re.finditer(r"(?<!\d)(\d{1,2})\s*-\s*(\d{1,2})(?!\d)", text):
        raw = m.group(0).strip()
        if re.fullmatch(r"\d{2}-\d{2}", raw):
            continue
        hg = int(m.group(1))
        ag = int(m.group(2))
        if 0 <= hg <= 10 and 0 <= ag <= 10:
            return f"{hg}-{ag}"

    return None


def _extract_ht_score(text: str) -> Optional[str]:
    if not text:
        return None
    for pat in (
        r"(?:半场|半|HT)\s*[:：]?\s*(\d{1,2})\s*[:\-]\s*(\d{1,2})",
        r"\((\d{1,2})\s*[:\-]\s*(\d{1,2})\)",
    ):
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            hg = int(m.group(1))
            ag = int(m.group(2))
            if 0 <= hg <= 50 and 0 <= ag <= 50:
                return f"{hg}-{ag}"
    return None


def _guess_status(text: str) -> str:
    t = (text or "").strip()
    if any(k in t for k in ("取消", "作废", "VOID", "cancel")):
        return "CANCELLED"
    if any(k in t for k in ("延期", "推迟", "POSTPONED")):
        return "POSTPONED"
    if any(k in t for k in ("腰斩", "中止", "ABANDON")):
        return "ABANDONED"
    return "FINISHED"


@dataclass
class _Row:
    cells: List[str]
    links: List[str]


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._rows: List[_Row] = []
        self._in_tr = False
        self._in_cell = False
        self._cell_buf: List[str] = []
        self._cur_cells: List[str] = []
        self._cur_links: List[str] = []

    @property
    def rows(self) -> List[_Row]:
        return self._rows

    def handle_starttag(self, tag: str, attrs):
        if tag == "tr":
            self._in_tr = True
            self._cur_cells = []
            self._cur_links = []
        elif tag in ("td", "th") and self._in_tr:
            self._in_cell = True
            self._cell_buf = []
        elif tag in ("br",) and self._in_cell and self._in_tr:
            self._cell_buf.append("\n")
        elif tag == "a" and self._in_tr:
            href = ""
            for k, v in attrs or []:
                if k == "href":
                    href = str(v or "").strip()
                    break
            if href:
                self._cur_links.append(href)

    def handle_endtag(self, tag: str):
        if tag in ("td", "th") and self._in_tr and self._in_cell:
            raw = "".join(self._cell_buf)
            text = re.sub(r"[\u00a0\s]+", " ", raw).strip()
            self._cur_cells.append(text)
            self._in_cell = False
            self._cell_buf = []
        elif tag == "tr" and self._in_tr:
            if self._cur_cells:
                self._rows.append(_Row(cells=self._cur_cells, links=self._cur_links))
            self._in_tr = False
            self._cur_cells = []
            self._cur_links = []

    def handle_data(self, data: str):
        if self._in_cell and self._in_tr:
            self._cell_buf.append(data)


def _extract_fid_from_links(links: List[str]) -> Optional[str]:
    for link in links or []:
        for pat in (
            r"ouzh[i]?\-(\d{4,12})\.shtml",
            r"fenxi/[a-z]+-(\d{4,12})\.shtml",
            r"fid=(\d{4,12})",
        ):
            m = re.search(pat, link)
            if m:
                return m.group(1)
    return None


def fetch_500_trade_results_html(*, date: Optional[str] = None, timeout_s: float = 4.0) -> Dict[str, Any]:
    url = build_500_trade_results_url(date=date)
    try:
        resp = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout_s)
    except Exception as e:
        return {"ok": False, "html": "", "url": url, "error": f"request_failed:{type(e).__name__}"}
    if resp.status_code != 200:
        return {"ok": False, "html": "", "url": url, "error": f"status:{resp.status_code}"}
    html = resp.text or ""
    if len(html) < 200:
        return {"ok": False, "html": html, "url": url, "error": "empty"}
    if _looks_like_captcha(html):
        return {"ok": False, "html": html, "url": url, "error": "captcha"}
    return {"ok": True, "html": html, "url": url, "error": None}


def fetch_500_zx_results_html(*, timeout_s: float = 5.0) -> Dict[str, Any]:
    url = build_500_zx_results_url()
    headers = {"User-Agent": _DEFAULT_HEADERS["User-Agent"], "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout_s)
    except Exception as e:
        return {"ok": False, "html": "", "url": url, "error": f"request_failed:{type(e).__name__}"}
    if resp.status_code != 200:
        return {"ok": False, "html": "", "url": url, "error": f"status:{resp.status_code}"}
    apparent = getattr(resp, "apparent_encoding", None)
    if apparent and hasattr(resp, "encoding"):
        resp.encoding = apparent
    html = resp.text or ""
    if len(html) < 200:
        return {"ok": False, "html": html, "url": url, "error": "empty"}
    if _looks_like_captcha(html):
        return {"ok": False, "html": html, "url": url, "error": "captcha"}
    return {"ok": True, "html": html, "url": url, "error": None}


def _extract_trade_row(*, date: str, cells: List[str], links: List[str]) -> Optional[Dict[str, Any]]:
    if len(cells) < 4:
        return None
    match_no, league, kickoff_raw, vs_cell = cells[0], cells[1], cells[2], cells[3]
    if not re.match(r"^周[一二三四五六日]\d{3}$", match_no or ""):
        return None
    kickoff_time = _normalize_kickoff_time(date=date, kickoff_raw=kickoff_raw)

    home = ""
    away = ""
    if re.search(r"(?:VS|vs|V\s*S)", vs_cell or ""):
        m = re.search(r"(?P<home>.+?)\s*(?:VS|vs|V\s*S)\s*(?P<away>.+)", vs_cell)
        if not m:
            return None
        home = _clean_team_name(m.group("home"))
        away_raw = re.sub(r"(?<!\d)(\d{1,2})\s*[:\-]\s*(\d{1,2})(?!\d)", "", m.group("away"))
        away = _clean_team_name(away_raw)
    else:
        m = re.search(
            r"(?P<home>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})\s+"
            r"(?P<hg>\d{1,2})\s*[:\-]\s*(?P<ag>\d{1,2})\s+"
            r"(?P<away>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})",
            vs_cell or "",
        )
        if not m:
            return None
        home = _clean_team_name(m.group("home"))
        away = _clean_team_name(m.group("away"))

    if not home or not away or home == away:
        return None

    joined = " ".join(cells)
    score_ft = _extract_score(vs_cell) or _extract_score(joined)
    status = _guess_status(joined)
    if score_ft is None and status == "FINISHED":
        return None
    score_ht = _extract_ht_score(joined)
    fid = _extract_fid_from_links(links)
    return {
        "league": (league or "").strip(),
        "league_name": (league or "").strip(),
        "home_team": home,
        "away_team": away,
        "kickoff_time": kickoff_time,
        "status": status,
        "score_ft": score_ft,
        "score_ht": score_ht,
        "match_no": match_no,
        "fid": fid,
    }


def parse_500_trade_results_html(*, html: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    if not html or "500.com" not in html:
        return []
    parser = _TableParser()
    try:
        parser.feed(html)
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, str, str]] = set()
    for row in parser.rows:
        cells = [c for c in row.cells if c]
        r = _extract_trade_row(date=target_date, cells=cells, links=row.links)
        if not r:
            continue
        if r.get("status") != "FINISHED":
            continue
        key = (str(r.get("league") or ""), str(r.get("kickoff_time") or ""), str(r.get("home_team") or ""), str(r.get("away_team") or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _extract_zx_row(*, date: str, cells: List[str], links: List[str]) -> Optional[Dict[str, Any]]:
    joined = " ".join([c for c in cells if c])
    if not joined:
        return None

    if re.search(r"(?P<y>\d{4})[-/](?P<m>\d{2})[-/](?P<d>\d{2})", joined):
        if date not in joined:
            return None

    kickoff_time = None
    for kickoff_raw in cells:
        if re.search(r"\d{2}-\d{2}\s+\d{2}:\d{2}", kickoff_raw or "") or re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", kickoff_raw or ""):
            kickoff_time = _normalize_kickoff_time(date=date, kickoff_raw=kickoff_raw)
            break
    if kickoff_time is None:
        tm = re.search(r"(\d{2}-\d{2}\s+\d{2}:\d{2})", joined)
        if tm:
            kickoff_time = _normalize_kickoff_time(date=date, kickoff_raw=tm.group(1))
        else:
            kickoff_time = f"{date} 00:00"

    league = ""
    for c in cells:
        if re.search(r"[\u4e00-\u9fff]", c or "") and not re.search(r"\d", c or "") and len(c) <= 10:
            league = c.strip()
            break
    if not league and cells:
        league = (cells[0] or "").strip()

    home = ""
    away = ""
    vs_m = re.search(r"(?P<home>.+?)\s*(?:VS|vs|V\s*S)\s*(?P<away>.+)", joined)
    if vs_m:
        home = _clean_team_name(vs_m.group("home"))
        away_raw = re.sub(r"(?<!\d)(\d{1,2})\s*[:\-]\s*(\d{1,2})(?!\d)", "", vs_m.group("away"))
        away = _clean_team_name(away_raw)
    else:
        hsa = re.search(
            r"(?P<home>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})\s+"
            r"(?P<hg>\d{1,2})\s*[:\-]\s*(?P<ag>\d{1,2})\s+"
            r"(?P<away>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})",
            joined,
        )
        if hsa:
            home = _clean_team_name(hsa.group("home"))
            away = _clean_team_name(hsa.group("away"))
        elif len(cells) >= 3 and _extract_score(cells[1]):
            home = _clean_team_name(cells[0])
            away = _clean_team_name(cells[2])

    if not home or not away or home == away:
        return None

    score_ft = _extract_score(joined)
    status = _guess_status(joined)
    if score_ft is None and status == "FINISHED":
        return None

    score_ht = _extract_ht_score(joined)
    fid = _extract_fid_from_links(links)
    return {
        "league": league,
        "league_name": league,
        "home_team": home,
        "away_team": away,
        "kickoff_time": kickoff_time,
        "status": status,
        "score_ft": score_ft,
        "score_ht": score_ht,
        "fid": fid,
    }


def parse_500_zx_results_html(*, html: str, date: str) -> List[Dict[str, Any]]:
    if not html or "500.com" not in html:
        return []
    parser = _TableParser()
    try:
        parser.feed(html)
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str, str, str]] = set()
    for row in parser.rows:
        cells = [c for c in row.cells if c]
        r = _extract_zx_row(date=date, cells=cells, links=row.links)
        if not r:
            continue
        if r.get("status") != "FINISHED":
            continue
        key = (str(r.get("league") or ""), str(r.get("kickoff_time") or ""), str(r.get("home_team") or ""), str(r.get("away_team") or ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def fetch_500_trade_results_by_date(*, date: str) -> Dict[str, Any]:
    fetched = fetch_500_trade_results_html(date=date)
    if not fetched.get("ok"):
        if fetched.get("error") == "captcha":
            return {
                "ok": False,
                "data": None,
                "error": {"code": "CAPTCHA_REQUIRED", "message": "500.com trade results page requires captcha"},
                "meta": {"mock": False, "source": "trade.500.com", "confidence": 0.0, "stale": True},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "FETCH_FAILED", "message": f"failed to fetch trade results page: {fetched.get('error')}"},
            "meta": {"mock": False, "source": "trade.500.com", "confidence": 0.0, "stale": True},
        }

    html = str(fetched.get("html") or "")
    parsed = parse_500_trade_results_html(html=html, date=date)
    if not parsed:
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "no finished results parsed from trade.500.com"},
            "meta": {"mock": False, "source": "trade.500.com", "confidence": 0.0, "stale": True},
        }

    html_sha1 = hashlib.sha1(html.encode("utf-8", errors="ignore")).hexdigest()
    payload = {
        "results": parsed,
        "provider": "500.com",
        "source_url": fetched.get("url"),
        "date": date,
        "raw_html_sha1": html_sha1,
        "raw_html_excerpt": html[:20000],
    }
    return {
        "ok": True,
        "data": payload,
        "error": None,
        "meta": {"mock": False, "source": "trade.500.com", "confidence": 0.88, "stale": False},
    }


def fetch_500_zx_results_by_date(*, date: str) -> Dict[str, Any]:
    fetched = fetch_500_zx_results_html()
    if not fetched.get("ok"):
        if fetched.get("error") == "captcha":
            return {
                "ok": False,
                "data": None,
                "error": {"code": "CAPTCHA_REQUIRED", "message": "500.com zx results page requires captcha"},
                "meta": {"mock": False, "source": "zx.500.com", "confidence": 0.0, "stale": True},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "FETCH_FAILED", "message": f"failed to fetch zx results page: {fetched.get('error')}"},
            "meta": {"mock": False, "source": "zx.500.com", "confidence": 0.0, "stale": True},
        }

    html = str(fetched.get("html") or "")
    parsed = parse_500_zx_results_html(html=html, date=date)
    if not parsed:
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "no finished results parsed from zx.500.com"},
            "meta": {"mock": False, "source": "zx.500.com", "confidence": 0.0, "stale": True},
        }

    html_sha1 = hashlib.sha1(html.encode("utf-8", errors="ignore")).hexdigest()
    payload = {
        "results": parsed,
        "provider": "500.com",
        "source_url": fetched.get("url"),
        "date": date,
        "raw_html_sha1": html_sha1,
        "raw_html_excerpt": html[:20000],
    }
    return {
        "ok": True,
        "data": payload,
        "error": None,
        "meta": {"mock": False, "source": "zx.500.com", "confidence": 0.8, "stale": False},
    }
