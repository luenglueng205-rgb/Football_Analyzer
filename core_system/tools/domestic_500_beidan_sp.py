from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import requests


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
}


def build_500_beidan_url(*, date: Optional[str] = None) -> str:
    base = "https://trade.500.com/bjdc/index.php"
    if date:
        return f"{base}?date={date}"
    return base


def _looks_like_captcha(html: str) -> bool:
    t = html or ""
    return any(k in t for k in ("验证码", "安全验证", "人机验证", "verify", "captcha"))


def _extract_date(kickoff_time: Optional[str]) -> str:
    if kickoff_time:
        m = re.search(r"(?P<y>\d{4})[-/](?P<m>\d{1,2})[-/](?P<d>\d{1,2})", kickoff_time)
        if m:
            y = int(m.group("y"))
            mm = int(m.group("m"))
            dd = int(m.group("d"))
            if 1900 <= y <= 2100 and 1 <= mm <= 12 and 1 <= dd <= 31:
                return f"{y:04d}-{mm:02d}-{dd:02d}"
    return datetime.now().strftime("%Y-%m-%d")


def fetch_500_beidan_html(*, date: Optional[str] = None, timeout_s: float = 5.0) -> Dict[str, Any]:
    url = build_500_beidan_url(date=date)
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


def _normalize_team_key(name: str) -> str:
    t = (name or "").strip()
    t = re.sub(r"\[[^\]]{1,8}\]", "", t)
    t = re.sub(r"[\u00a0\s]+", "", t)
    t = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", t)
    return t.lower()


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


def parse_500_beidan_sp_html(*, html: str, home_team: str, away_team: str, fid: Optional[str] = None) -> Dict[str, Any]:
    if not html:
        return {"ok": False, "data": None, "error": {"code": "EMPTY", "message": "empty html"}, "meta": {"source": "500.com", "confidence": 0.0}}

    parser = _TableParser()
    try:
        parser.feed(html)
    except Exception:
        return {"ok": False, "data": None, "error": {"code": "PARSE_FAILED", "message": "html parser failed"}, "meta": {"source": "500.com", "confidence": 0.0}}

    home_k = _normalize_team_key(home_team)
    away_k = _normalize_team_key(away_team)
    if not home_k or not away_k:
        return {"ok": False, "data": None, "error": {"code": "BAD_INPUT", "message": "empty team name"}, "meta": {"source": "500.com", "confidence": 0.0}}

    best: Optional[List[str]] = None
    if fid:
        fid_s = str(fid).strip()
        for row in parser.rows:
            row_fid = _extract_fid_from_links(row.links)
            if row_fid and row_fid == fid_s:
                cells = [c for c in row.cells if c]
                if cells:
                    best = cells
                    break

    if not best:
        for row in parser.rows:
            cells = [c for c in row.cells if c]
            if not cells:
                continue
            joined = " ".join(cells)
            if home_k in _normalize_team_key(joined) and away_k in _normalize_team_key(joined):
                best = cells
                break

    if not best:
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "match row not found on 500 beidan page"},
            "meta": {"source": "500.com", "confidence": 0.0},
        }

    handicap: Optional[float] = None
    for c in best:
        if re.fullmatch(r"[+-]?\d+", c.strip()):
            try:
                v = int(c.strip())
                if abs(v) <= 10:
                    handicap = float(v)
                    break
            except Exception:
                continue

    floats: List[float] = []
    for c in best:
        for s in re.findall(r"\d+(?:\.\d+)", c):
            try:
                floats.append(float(s))
            except Exception:
                continue

    if len(floats) < 3:
        return {
            "ok": False,
            "data": None,
            "error": {"code": "ODDS_UNAVAILABLE", "message": "no SP values found in row"},
            "meta": {"source": "500.com", "confidence": 0.0},
        }

    sp_home, sp_draw, sp_away = floats[-3], floats[-2], floats[-1]
    html_sha1 = hashlib.sha1(html.encode("utf-8", errors="ignore")).hexdigest()
    payload = {
        "beidan_sp": {
            "HANDICAP_WDL": {"handicap": handicap if handicap is not None else 0.0, "home": sp_home, "draw": sp_draw, "away": sp_away}
        },
        "provider": "500.com",
        "raw_html_sha1": html_sha1,
        "raw_html_excerpt": html[:20000],
    }
    return {
        "ok": True,
        "data": payload,
        "error": None,
        "meta": {"mock": False, "source": "500.com", "confidence": 0.7, "stale": False},
    }


def fetch_500_beidan_sp_by_teams(
    *, home_team: str, away_team: str, kickoff_time: Optional[str] = None, fid: Optional[str] = None
) -> Dict[str, Any]:
    date = _extract_date(kickoff_time)
    fetched = fetch_500_beidan_html(date=date)
    if not fetched.get("ok"):
        if fetched.get("error") == "captcha":
            return {
                "ok": False,
                "data": None,
                "error": {"code": "CAPTCHA_REQUIRED", "message": "500.com beidan page requires captcha"},
                "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "FETCH_FAILED", "message": f"failed to fetch 500.com beidan page: {fetched.get('error')}"},
            "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
        }

    parsed = parse_500_beidan_sp_html(html=str(fetched.get("html") or ""), home_team=home_team, away_team=away_team, fid=fid)
    if parsed.get("ok"):
        parsed["data"]["source_url"] = fetched.get("url")
        parsed["data"]["date"] = date
    return parsed
