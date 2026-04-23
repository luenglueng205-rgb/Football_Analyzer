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


def build_500_jczq_trade_url(*, date: Optional[str] = None) -> str:
    base = "https://trade.500.com/jczq/"
    if date:
        return f"{base}?playid=312&g=2&date={date}"
    return f"{base}?playid=312&g=2"


def _looks_like_captcha(html: str) -> bool:
    t = html or ""
    return any(k in t for k in ("验证码", "安全验证", "人机验证", "verify", "captcha"))


def fetch_500_jczq_trade_html(*, date: Optional[str] = None, timeout_s: float = 4.0) -> Dict[str, Any]:
    url = build_500_jczq_trade_url(date=date)
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


def _parse_handicap_cell(text: str) -> List[int]:
    raw = (text or "").replace("单关", " ")
    nums = re.findall(r"[+-]?\d+", raw)
    out: List[int] = []
    for n in nums:
        try:
            out.append(int(n))
        except Exception:
            continue
    return out


def _parse_sp_cell(text: str) -> List[Optional[float]]:
    t = text or ""
    if "未开售" in t or "停售" in t:
        return []
    nums = re.findall(r"\d+(?:\.\d+)", t)
    out: List[Optional[float]] = []
    for n in nums:
        try:
            out.append(float(n))
        except Exception:
            continue
    return out


def parse_500_jczq_trade_sp_html(
    *,
    html: str,
    home_team: str,
    away_team: str,
    kickoff_time: Optional[str] = None,
    fid: Optional[str] = None,
) -> Dict[str, Any]:
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

    best_row: Optional[List[str]] = None
    if fid:
        fid_s = str(fid).strip()
        for row in parser.rows:
            if not row.cells:
                continue
            row_fid = _extract_fid_from_links(row.links)
            if row_fid and row_fid == fid_s:
                cells = [c for c in row.cells if c]
                if len(cells) >= 8:
                    best_row = cells
                    break

    if not best_row:
        for row in parser.rows:
            cells = [c for c in row.cells if c]
            if len(cells) < 8:
                continue
            vs_cell = cells[3]
            if "VS" not in vs_cell and "vs" not in vs_cell and "V S" not in vs_cell:
                continue
            m = re.search(r"(?P<home>.+?)\s*(?:VS|vs|V\s*S)\s*(?P<away>.+)", vs_cell)
            if not m:
                continue
            h = _normalize_team_key(m.group("home"))
            a = _normalize_team_key(m.group("away"))
            if h == home_k and a == away_k:
                best_row = cells
                break
            if h == away_k and a == home_k:
                best_row = cells
                break

    if not best_row:
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "match row not found on 500 trade page"},
            "meta": {"source": "500.com", "confidence": 0.0},
        }

    handicap_nums = _parse_handicap_cell(best_row[4])
    win = _parse_sp_cell(best_row[5])
    draw = _parse_sp_cell(best_row[6])
    lose = _parse_sp_cell(best_row[7])

    markets: Dict[str, Any] = {}
    if len(win) >= 1 and len(draw) >= 1 and len(lose) >= 1:
        markets["WDL"] = {
            "handicap": float(handicap_nums[0]) if handicap_nums else 0.0,
            "home": win[0],
            "draw": draw[0],
            "away": lose[0],
        }
    if len(win) >= 2 and len(draw) >= 2 and len(lose) >= 2 and len(handicap_nums) >= 2:
        markets["HANDICAP_WDL"] = {
            "handicap": float(handicap_nums[1]),
            "home": win[1],
            "draw": draw[1],
            "away": lose[1],
        }

    if not markets:
        return {
            "ok": False,
            "data": None,
            "error": {"code": "ODDS_UNAVAILABLE", "message": "no SP values found in row"},
            "meta": {"source": "500.com", "confidence": 0.0},
        }

    date = _extract_date(kickoff_time)
    html_sha1 = hashlib.sha1(html.encode("utf-8", errors="ignore")).hexdigest()
    payload = {
        "jingcai_sp": markets,
        "date": date,
        "provider": "500.com",
        "raw_html_sha1": html_sha1,
        "raw_html_excerpt": html[:20000],
    }
    return {
        "ok": True,
        "data": payload,
        "error": None,
        "meta": {"mock": False, "source": "500.com", "confidence": 0.92, "stale": False},
    }


def fetch_500_jczq_sp_by_teams(
    *, home_team: str, away_team: str, kickoff_time: Optional[str] = None, fid: Optional[str] = None
) -> Dict[str, Any]:
    date = _extract_date(kickoff_time)
    fetched = fetch_500_jczq_trade_html(date=date)
    if not fetched.get("ok"):
        if fetched.get("error") == "captcha":
            return {
                "ok": False,
                "data": None,
                "error": {"code": "CAPTCHA_REQUIRED", "message": "500.com trade page requires captcha"},
                "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "FETCH_FAILED", "message": f"failed to fetch 500.com trade page: {fetched.get('error')}"},
            "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
        }

    parsed = parse_500_jczq_trade_sp_html(
        html=str(fetched.get("html") or ""),
        home_team=home_team,
        away_team=away_team,
        kickoff_time=kickoff_time,
        fid=fid,
    )
    if parsed.get("ok"):
        parsed["data"]["source_url"] = fetched.get("url")
    return parsed
