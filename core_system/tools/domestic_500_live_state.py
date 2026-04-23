from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

import requests


_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
_DEFAULT_HEADERS = {"User-Agent": _UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}


def _looks_like_captcha(html: str) -> bool:
    t = html or ""
    return any(k in t for k in ("验证码", "安全验证", "人机验证", "verify", "captcha"))


def build_500_live_detail_url(*, fid: str) -> str:
    fid = str(fid or "").strip()
    return f"https://live.500.com/detail.php?fid={fid}&r=1"


class _TextAttrParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: List[str] = []

    def handle_starttag(self, tag: str, attrs):
        for k, v in attrs or []:
            if not v:
                continue
            ks = str(k or "").lower()
            if ks in {"alt", "title", "aria-label"}:
                self._parts.append(str(v))
            else:
                sv = str(v)
                if "红牌" in sv or "红" in sv or re.search(r"\d{1,3}\s*['′分钟]", sv):
                    self._parts.append(sv)

    def handle_data(self, data: str):
        if data:
            self._parts.append(data)

    @property
    def text(self) -> str:
        t = " ".join(self._parts)
        t = re.sub(r"[\u00a0\s]+", " ", t)
        return t.strip()


def _extract_minute(text: str) -> Optional[int]:
    t = text or ""
    if any(k in t for k in ("完场", "全场结束", "结束", "已完")):
        return 90
    if any(k in t for k in ("中场", "半场")):
        return 45
    for pat in (r"(?<!\d)(\d{1,3})(?:\+(\d{1,2}))?\s*['′]", r"(?<!\d)(\d{1,3})(?:\+(\d{1,2}))?\s*分钟"):
        m = re.search(pat, t)
        if not m:
            continue
        base = int(m.group(1))
        extra = int(m.group(2)) if m.group(2) else 0
        minute = base + extra
        if 0 <= minute <= 130:
            return minute
    return None


def _score_candidates(text: str) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    for m in re.finditer(r"(?<!\d)(\d{1,2})\s*[:\-]\s*(\d{1,2})(?!\d)", text or ""):
        hg = int(m.group(1))
        ag = int(m.group(2))
        if 0 <= hg <= 10 and 0 <= ag <= 10:
            out.append((f"{hg}-{ag}", m.start()))
    return out


def _extract_score_ft(text: str) -> Optional[str]:
    t = text or ""
    cands = _score_candidates(t)
    if not cands:
        return None
    best = None
    best_w = 999999
    for s, idx in cands:
        window = t[max(0, idx - 12) : min(len(t), idx + 12)]
        w = 10
        if "比分" in window:
            w -= 6
        if "半场" in window or "HT" in window:
            w += 4
        if "全场" in window or "完场" in window:
            w -= 1
        if w < best_w:
            best_w = w
            best = s
    return best


def _extract_red_cards(text: str) -> Optional[Dict[str, int]]:
    t = text or ""
    m = re.search(r"红牌\s*[:：]?\s*(\d{1,2})\s*[-/]\s*(\d{1,2})", t)
    if m:
        return {"home": int(m.group(1)), "away": int(m.group(2))}
    m = re.search(r"红牌\s*[:：]?\s*(\d{1,2})\D{1,10}(\d{1,2})", t)
    if m:
        return {"home": int(m.group(1)), "away": int(m.group(2))}
    return None


def parse_500_live_detail_html(*, html: str) -> Dict[str, Any]:
    if not html or "500.com" not in html:
        return {"ok": False, "data": None, "error": {"code": "PARSE_FAILED", "message": "html empty or not 500.com"}, "meta": {"confidence": 0.0}}

    if _looks_like_captcha(html):
        return {"ok": False, "data": None, "error": {"code": "CAPTCHA_REQUIRED", "message": "captcha page"}, "meta": {"confidence": 0.0}}

    parser = _TextAttrParser()
    try:
        parser.feed(html)
    except Exception:
        return {"ok": False, "data": None, "error": {"code": "PARSE_FAILED", "message": "html parse error"}, "meta": {"confidence": 0.0}}

    text = parser.text
    minute = _extract_minute(text)
    ft_score = _extract_score_ft(text)
    red_cards = _extract_red_cards(text)

    if ft_score is None:
        return {"ok": False, "data": None, "error": {"code": "REFUSED", "message": "score not found"}, "meta": {"confidence": 0.0}}
    if minute is None:
        return {"ok": False, "data": None, "error": {"code": "REFUSED", "message": "minute not found"}, "meta": {"confidence": 0.0}}

    payload: Dict[str, Any] = {"minute": minute, "ft_score": ft_score}
    if isinstance(red_cards, dict):
        payload["red_cards"] = red_cards
    return {"ok": True, "data": payload, "error": None, "meta": {"confidence": 0.66}}


def fetch_500_live_detail_html(*, fid: str, timeout_s: float = 4.0) -> Dict[str, Any]:
    url = build_500_live_detail_url(fid=fid)
    try:
        r = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout_s)
    except Exception as e:
        return {"ok": False, "html": "", "url": url, "error": f"request_failed:{type(e).__name__}"}
    if r.status_code != 200:
        return {"ok": False, "html": "", "url": url, "error": f"status:{r.status_code}"}
    r.encoding = getattr(r, "apparent_encoding", None) or r.encoding
    html = r.text or ""
    if len(html) < 200:
        return {"ok": False, "html": html, "url": url, "error": "empty"}
    if _looks_like_captcha(html):
        return {"ok": False, "html": html, "url": url, "error": "captcha"}
    return {"ok": True, "html": html, "url": url, "error": None}


def fetch_500_live_state_by_fid(*, fid: str) -> Dict[str, Any]:
    fid_s = str(fid or "").strip()
    if not re.fullmatch(r"\d{4,12}", fid_s):
        return {
            "ok": False,
            "data": None,
            "error": {"code": "BAD_INPUT", "message": "fid required"},
            "meta": {"mock": False, "source": "live.500.com", "confidence": 0.0, "stale": True},
        }

    fetched = fetch_500_live_detail_html(fid=fid_s)
    if not fetched.get("ok"):
        if fetched.get("error") == "captcha":
            return {
                "ok": False,
                "data": None,
                "error": {"code": "CAPTCHA_REQUIRED", "message": "500.com live detail requires captcha"},
                "meta": {"mock": False, "source": "live.500.com", "confidence": 0.0, "stale": True},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "FETCH_FAILED", "message": f"failed to fetch live detail: {fetched.get('error')}"},
            "meta": {"mock": False, "source": "live.500.com", "confidence": 0.0, "stale": True},
        }

    html = str(fetched.get("html") or "")
    parsed = parse_500_live_detail_html(html=html)
    if not parsed.get("ok"):
        err = parsed.get("error") if isinstance(parsed, dict) else None
        code = (err or {}).get("code") if isinstance(err, dict) else "PARSE_FAILED"
        msg = (err or {}).get("message") if isinstance(err, dict) else "parse failed"
        if code == "CAPTCHA_REQUIRED":
            return {
                "ok": False,
                "data": None,
                "error": {"code": "CAPTCHA_REQUIRED", "message": "captcha page"},
                "meta": {"mock": False, "source": "live.500.com", "confidence": 0.0, "stale": True},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": str(code), "message": str(msg)},
            "meta": {"mock": False, "source": "live.500.com", "confidence": 0.0, "stale": True},
        }

    minute = int((parsed.get("data") or {}).get("minute"))
    ft_score = str((parsed.get("data") or {}).get("ft_score") or "")
    red_cards = (parsed.get("data") or {}).get("red_cards")
    payload: Dict[str, Any] = {
        "fid": fid_s,
        "minute": minute,
        "ft_score": ft_score,
        "provider": "500.com",
        "source_url": fetched.get("url"),
        "raw_html_sha1": hashlib.sha1(html.encode("utf-8", errors="ignore")).hexdigest(),
        "raw_html_excerpt": html[:20000],
    }
    if isinstance(red_cards, dict):
        payload["red_cards"] = red_cards

    confidence = float(((parsed.get("meta") or {}) or {}).get("confidence") or 0.6)
    confidence = max(0.0, min(1.0, confidence))
    return {
        "ok": True,
        "data": payload,
        "error": None,
        "meta": {"mock": False, "source": "live.500.com", "confidence": confidence, "stale": False},
    }

