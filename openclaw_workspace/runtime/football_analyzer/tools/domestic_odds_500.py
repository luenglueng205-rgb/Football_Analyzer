from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, Optional

import requests


_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def _normalize_compact(text: str) -> str:
    return re.sub(r"[\s\u00a0·•．。･・\-_/]+", "", (text or "").lower())


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


def _looks_like_captcha(html: str) -> bool:
    t = html or ""
    return any(k in t for k in ("验证码", "安全验证", "人机验证", "verify", "captcha"))


def fetch_500_jczq_html(*, date: str, timeout_s: float = 6.0) -> Dict[str, Any]:
    url = "https://zx.500.com/jczq/"
    headers = {"User-Agent": _UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout_s)
        if r.status_code != 200:
            return {"ok": False, "html": "", "error": f"status:{r.status_code}", "url": url}
        r.encoding = r.apparent_encoding or r.encoding
        html = r.text or ""
        if _looks_like_captcha(html):
            return {"ok": False, "html": html, "error": "captcha", "url": url}
        return {"ok": True, "html": html, "error": None, "url": url}
    except Exception as e:
        return {"ok": False, "html": "", "error": f"request_failed:{type(e).__name__}", "url": url}


def find_fid_from_jczq_html(*, html: str, home_team: str, away_team: str) -> Optional[str]:
    if not html or not home_team or not away_team:
        return None

    nh = _normalize_compact(html)
    home_n = _normalize_compact(home_team)
    away_n = _normalize_compact(away_team)
    if not home_n or not away_n:
        return None

    i1 = nh.find(home_n)
    i2 = nh.find(away_n)
    if i1 < 0 or i2 < 0:
        return None

    lo = max(min(i1, i2) - 2000, 0)
    hi = min(max(i1, i2) + 2000, len(nh))
    window = nh[lo:hi]

    for pat in (r"ouzh[i]?\-(\d{4,12})\.shtml", r"fid=(\d{4,12})"):
        m = re.search(pat, window)
        if m:
            return m.group(1)
    return None


def fetch_500_ouzhi_html(*, fid: str, timeout_s: float = 6.0) -> Dict[str, Any]:
    url = f"https://odds.500.com/fenxi/ouzhi-{fid}.shtml"
    headers = {"User-Agent": _UA, "Referer": "https://zx.500.com/jczq/"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout_s)
        if r.status_code != 200:
            return {"ok": False, "html": "", "error": f"status:{r.status_code}", "url": url}
        r.encoding = r.apparent_encoding or r.encoding
        html = r.text or ""
        if _looks_like_captcha(html):
            return {"ok": False, "html": html, "error": "captcha", "url": url}
        return {"ok": True, "html": html, "error": None, "url": url}
    except Exception as e:
        return {"ok": False, "html": "", "error": f"request_failed:{type(e).__name__}", "url": url}


def parse_500_eu_odds_from_ouzhi_html(html: str) -> Optional[Dict[str, float]]:
    if not html:
        return None

    nh = _normalize_compact(html)
    idx = nh.find("平均")
    hay = nh[idx : idx + 20000] if idx >= 0 else nh[:20000]

    m = re.search(
        r"平均[^0-9]{0,200}(\d+(?:\.\d+)?)"
        r"[^0-9]{0,200}(\d+(?:\.\d+)?)"
        r"[^0-9]{0,200}(\d+(?:\.\d+)?)",
        hay,
    )
    if not m:
        return None

    try:
        home = float(m.group(1))
        draw = float(m.group(2))
        away = float(m.group(3))
    except Exception:
        return None

    if not (1.01 <= home <= 200 and 1.01 <= draw <= 200 and 1.01 <= away <= 200):
        return None

    return {"home": home, "draw": draw, "away": away}


def fetch_500_eu_odds_by_teams(
    *, home_team: str, away_team: str, kickoff_time: Optional[str] = None, fid: Optional[str] = None
) -> Dict[str, Any]:
    date = _extract_date(kickoff_time)
    fid_s: Optional[str] = str(fid).strip() if fid else None
    if not fid_s:
        fixtures = fetch_500_jczq_html(date=date)
        if not fixtures.get("ok"):
            if fixtures.get("error") == "captcha":
                return {
                    "ok": False,
                    "data": None,
                    "error": {"code": "CAPTCHA_REQUIRED", "message": "500.com jczq page requires captcha"},
                    "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
                }
            return {
                "ok": False,
                "data": None,
                "error": {"code": "FETCH_FAILED", "message": f"failed to fetch 500.com fixtures page: {fixtures.get('error')}"},
                "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
            }

        fid_s = find_fid_from_jczq_html(html=str(fixtures.get("html") or ""), home_team=home_team, away_team=away_team)
        if not fid_s:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_FOUND", "message": "match fid not found on 500.com jczq page"},
                "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
            }

    odds_page = fetch_500_ouzhi_html(fid=fid_s)
    if not odds_page.get("ok"):
        if odds_page.get("error") == "captcha":
            return {
                "ok": False,
                "data": None,
                "error": {"code": "CAPTCHA_REQUIRED", "message": "500.com odds page requires captcha"},
                "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "FETCH_FAILED", "message": f"failed to fetch odds page: {odds_page.get('error')}"},
            "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
        }

    html = str(odds_page.get("html") or "")
    eu = parse_500_eu_odds_from_ouzhi_html(html)
    if not eu:
        return {
            "ok": False,
            "data": None,
            "error": {"code": "PARSE_FAILED", "message": "failed to parse 500.com eu odds from html"},
            "meta": {"mock": False, "source": "500.com", "confidence": 0.0, "stale": True},
        }

    html_bytes = html.encode("utf-8", errors="ignore")
    html_sha1 = hashlib.sha1(html_bytes).hexdigest()
    excerpt = html[:20000]
    payload = {
        "eu_odds": eu,
        "provider": "500.com",
        "fid": fid_s,
        "source_url": odds_page.get("url"),
        "raw_html_sha1": html_sha1,
        "raw_html_excerpt": excerpt,
    }
    return {
        "ok": True,
        "data": payload,
        "error": None,
        "meta": {"mock": False, "source": "500.com", "confidence": 0.86, "stale": False},
    }
