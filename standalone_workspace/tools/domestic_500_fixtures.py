from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import List, Optional

import requests


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
}


def build_500_trade_url(*, date: Optional[str] = None) -> str:
    base = "https://trade.500.com/jczq/"
    if date:
        return f"{base}?playid=312&g=2&date={date}"
    return f"{base}?playid=312&g=2"


def fetch_500_trade_html(*, date: Optional[str] = None, timeout_s: float = 3.0) -> Optional[str]:
    url = build_500_trade_url(date=date)
    try:
        resp = requests.get(url, headers=_DEFAULT_HEADERS, timeout=timeout_s)
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    if not resp.text or len(resp.text) < 200:
        return None
    return resp.text


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

    def _record_link_candidate(self, value: str) -> None:
        v = str(value or "").strip()
        if not v:
            return
        if not re.search(r"\d{4,12}", v):
            return
        if v in self._cur_links:
            return
        self._cur_links.append(v)

    def handle_starttag(self, tag: str, attrs):
        if tag == "tr":
            self._in_tr = True
            self._cur_cells = []
            self._cur_links = []
            for _, v in attrs or []:
                if v:
                    self._record_link_candidate(str(v))
        elif tag in ("td", "th") and self._in_tr:
            self._in_cell = True
            self._cell_buf = []
        elif self._in_tr:
            for _, v in attrs or []:
                if v:
                    self._record_link_candidate(str(v))

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


def _clean_team_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\[[^\]]{1,6}\]", "", name)
    name = re.sub(r"^\*+|\*+$", "", name).strip()
    name = re.sub(r"[\u00a0\s]+", " ", name).strip()
    return name


def _normalize_kickoff_time(*, date: str, kickoff_raw: str) -> str:
    kickoff_raw = re.sub(r"[\u00a0\s]+", " ", kickoff_raw).strip()
    m = re.search(r"(?P<mm>\d{2})-(?P<dd>\d{2})\s+(?P<hh>\d{2}):(?P<mi>\d{2})", kickoff_raw)
    if m:
        year = date.split("-", 1)[0]
        return f"{year}-{m.group('mm')}-{m.group('dd')} {m.group('hh')}:{m.group('mi')}"
    m = re.search(r"(?P<yyyy>\d{4})-(?P<mm>\d{2})-(?P<dd>\d{2})\s+(?P<hh>\d{2}):(?P<mi>\d{2})", kickoff_raw)
    if m:
        return f"{m.group('yyyy')}-{m.group('mm')}-{m.group('dd')} {m.group('hh')}:{m.group('mi')}"
    return f"{date} 00:00"


def _extract_fid_from_links(links: List[str]) -> Optional[str]:
    for link in links or []:
        for pat in (
            r"ouzh[i]?\-(\d{4,12})\.shtml",
            r"fenxi/[a-z]+-(\d{4,12})\.shtml",
            r"fid=(\d{4,12})",
            r"(?:fid|matchid|mid)\D{0,6}(\d{4,12})",
            r"ouzhi\D{0,6}(\d{4,12})",
            r"ouzh\D{0,6}(\d{4,12})",
        ):
            m = re.search(pat, link)
            if m:
                return m.group(1)
    return None


def parse_500_trade_fixtures_html(*, html: str, date: Optional[str] = None) -> List[dict]:
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    if not html or "500.com" not in html:
        return []

    parser = _TableParser()
    try:
        parser.feed(html)
    except Exception:
        return []

    fixtures: List[dict] = []
    seen: set[tuple[str, str, str, str]] = set()

    for row in parser.rows:
        cells = [c for c in row.cells if c]
        if len(cells) < 4:
            continue
        match_no, league, kickoff_raw, vs_cell = cells[0], cells[1], cells[2], cells[3]
        if not re.match(r"^周[一二三四五六日]\d{3}$", match_no):
            continue
        if "VS" not in vs_cell and "vs" not in vs_cell and "V S" not in vs_cell:
            continue
        m = re.search(r"(?P<home>.+?)\s*(?:VS|vs|V\s*S)\s*(?P<away>.+)", vs_cell)
        if not m:
            continue
        home = _clean_team_name(m.group("home"))
        away = _clean_team_name(m.group("away"))
        if not home or not away or home == away:
            continue

        kickoff_time = _normalize_kickoff_time(date=target_date, kickoff_raw=kickoff_raw)
        status = "played" if re.search(r"\d+\s*:\s*\d+", vs_cell) else "upcoming"
        fid = _extract_fid_from_links(row.links)

        key = (league, kickoff_time, home, away)
        if key in seen:
            continue
        seen.add(key)

        fixtures.append(
            {
                "league": league,
                "league_name": league,
                "home_team": home,
                "away_team": away,
                "kickoff_time": kickoff_time,
                "status": status,
                "match_no": match_no,
                "fid": fid,
            }
        )

    return fixtures
