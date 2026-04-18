import asyncio
import threading
from datetime import datetime
import hashlib
import json
import re
import os
from typing import Any, Dict, List, Optional
from ddgs import DDGS
from tools.visual_browser import VisualBrowser
from tools.domestic_500_fixtures import fetch_500_trade_html, parse_500_trade_fixtures_html
from tools.network_gatekeeper import NetworkGatekeeper, NetworkPolicy

def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}

def _looks_like_captcha(html: str) -> bool:
    t = html or ""
    return any(k in t for k in ("验证码", "安全验证", "人机验证", "verify", "captcha"))

def _sha1_ref(prefix: str, payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return f"{prefix}:{hashlib.sha1(encoded).hexdigest()[:12]}"

def _run_async_sync(coro, timeout_s: float = 12.0):
    """
    一个能在同步方法中运行异步协程的辅助函数。
    即使当前线程已经有运行中的 event loop（比如被 run_live_decision 的 async main 内部同步调用时），
    也能通过启动新线程来避免 RuntimeError。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result = None
    err = None

    def runner():
        nonlocal result, err
        try:
            result = asyncio.run(coro)
        except Exception as e:
            err = e

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        raise TimeoutError(f"async task timeout after {timeout_s}s")
    if err:
        raise err
    return result

class AgentBrowser:
    """
    重构后的 AgentBrowser：不再写爬虫逻辑，而是将任务翻译为自然语言交给 VisualBrowser。
    同时保留 ddgs 作为极轻量级的文本搜索兜底。
    """
    def __init__(self, *, online: bool = False, policy: Optional[NetworkPolicy] = None):
        self.gatekeeper = NetworkGatekeeper(policy=policy, online=online)
        self.online = bool(self.gatekeeper.allow_network())
        self.ddgs = DDGS() if self.online else None
        self.visual = None
        try:
            if self.online and VisualBrowser is not None:
                self.visual = VisualBrowser()
        except Exception:
            self.visual = None

    @staticmethod
    def _guess_league_name(text: str) -> Optional[str]:
        for name in ("英超", "西甲", "意甲", "德甲", "法甲", "欧冠"):
            if name in text:
                return name
        return None

    @staticmethod
    def _extract_fixtures_from_search_results(results: List[Dict[str, Any]], *, date: str) -> List[Dict[str, Any]]:
        fixtures: List[Dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        time_re = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{2})")
        vs_re = re.compile(
            r"(?P<home>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})\s*(?:vs|VS|V\.S\.|对|vs\.|-)\s*(?P<away>[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff\s·]{1,30})"
        )

        for r in results:
            url = str(r.get("href") or r.get("url") or "")
            if "500.com" not in url:
                continue

            text = f"{r.get('title') or ''} {r.get('body') or ''} {r.get('snippet') or ''}"
            if date not in text and "今日" not in text and "今天" not in text:
                continue
            tm = time_re.search(text)
            if not tm:
                continue

            m = vs_re.search(text)
            if not m:
                continue

            home = m.group("home").strip()
            away = m.group("away").strip()
            league = AgentBrowser._guess_league_name(text) or "UNK"
            if league != "UNK" and home.startswith(league):
                home = home[len(league) :].strip()
            if not home or not away or home == away:
                continue

            hh = int(tm.group("h"))
            mm = int(tm.group("m"))
            if hh > 23 or mm > 59:
                continue

            kickoff_time = f"{date} {hh:02d}:{mm:02d}"
            status = "played" if any(x in text for x in ("完场", "已结束", "FT")) else "upcoming"

            key = (league, home, away)
            if key in seen:
                continue
            seen.add(key)
            fixtures.append(
                {
                    "league": league,
                    "home_team": home,
                    "away_team": away,
                    "kickoff_time": kickoff_time,
                    "status": status,
                    "url": url,
                }
            )

        return fixtures

    def _scrape_500_fixtures_ddgs(self, *, date: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.ddgs:
            return []
        target_date = date or datetime.now().strftime("%Y-%m-%d")
        query = f"site:zx.500.com jczq 竞彩足球 {target_date} 赛程"
        results = self.gatekeeper.run_sync(
            lambda: list(self.ddgs.text(query, max_results=10)),
            timeout_s=self.gatekeeper.policy.ddgs_timeout_s,
            default=[],
        )
        return self._extract_fixtures_from_search_results(results, date=target_date)

    def scrape_500_fixtures(self, date: Optional[str] = None) -> list:
        if not self.online:
            return []
        html = fetch_500_trade_html(date=date)
        if html:
            if _looks_like_captcha(html) and _env_bool("INFO_FIRST_MODE", True):
                return self._scrape_500_fixtures_ddgs(date=date)
            fixtures = parse_500_trade_fixtures_html(html=html, date=date)
            if fixtures:
                return fixtures

        if self.visual is not None:
            task = "访问 http://zx.500.com/jczq/ ，找到今天（或者即将开赛）的所有竞彩足球比赛。请严格以JSON数组格式返回，包含 'home_team', 'away_team', 'status'(填'upcoming'或'played')。"

            try:
                res = _run_async_sync(self.visual.extract_info(task), timeout_s=12.0)

                import json

                match = re.search(r"\[.*\]", res, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except Exception as e:
                print(f"[AgentBrowser] Visual scrape error: {e}")

        return self._scrape_500_fixtures_ddgs(date=date)

    def scrape_500_results_visual(self, *, date: str) -> Dict[str, Any]:
        if self.visual is None:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_AVAILABLE", "message": "visual browser not configured"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        task = (
            "访问 https://zx.500.com/jczq/ 。"
            f"筛选日期 {date} 的竞彩足球比赛，只保留已完赛/可结算的场次。"
            "严格返回 JSON 数组，每个元素包含："
            '{"league":"字符串","kickoff_time":"YYYY-MM-DD HH:MM","home_team":"字符串","away_team":"字符串","score_ft":"x-y","score_ht":"x-y(可选)","status":"FINISHED"}。'
            "如果页面只能看到 ':' 分隔比分，请转换为 '-'。如果找不到已完赛比赛，返回空数组 []。"
        )

        try:
            res = _run_async_sync(self.visual.extract_info(task), timeout_s=22.0)
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "FETCH_FAILED", "message": f"visual extract failed: {type(e).__name__}"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        try:
            m = re.search(r"\[[\s\S]*\]", str(res))
            if not m:
                raise ValueError("no json array")
            arr = json.loads(m.group(0))
            if not isinstance(arr, list):
                raise ValueError("not array")
        except Exception:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "PARSE_FAILED", "message": "visual output parse failed"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        cleaned: List[Dict[str, Any]] = []
        for it in arr:
            if not isinstance(it, dict):
                continue
            home_team = str(it.get("home_team") or "").strip()
            away_team = str(it.get("away_team") or "").strip()
            kickoff_time = str(it.get("kickoff_time") or "").strip()
            league = str(it.get("league") or "").strip()
            score_ft = str(it.get("score_ft") or "").strip().replace(":", "-")
            score_ht = it.get("score_ht")
            if score_ht is not None:
                score_ht = str(score_ht).strip().replace(":", "-")
            if not home_team or not away_team or not score_ft:
                continue
            if not re.fullmatch(r"\d{1,2}-\d{1,2}", score_ft):
                continue
            rec: Dict[str, Any] = {
                "league": league,
                "kickoff_time": kickoff_time,
                "home_team": home_team,
                "away_team": away_team,
                "score_ft": score_ft,
                "status": "FINISHED",
            }
            if score_ht and re.fullmatch(r"\d{1,2}-\d{1,2}", str(score_ht)):
                rec["score_ht"] = str(score_ht)
            cleaned.append(rec)

        if not cleaned:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_FOUND", "message": "no finished results extracted by visual browser"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        payload = {"results": cleaned, "provider": "500.com", "source_url": "browser_use", "raw_text": str(res)[:2000]}
        raw_ref = _sha1_ref("browser_use:results", payload)
        return {
            "ok": True,
            "data": payload,
            "error": None,
            "meta": {"mock": False, "source": "500.com", "confidence": 0.35, "stale": False, "raw_ref": raw_ref},
        }

    def search_dongqiudi_news(self, team_name: str) -> list:
        """使用视觉浏览器获取伤病情报"""
        if self.visual is None:
            return []

        task = f"访问懂球帝网站或直接搜索关于'{team_name}'的最新足球新闻，特别是伤停和首发情报。提炼出3条最关键的信息返回。"
        try:
            res = _run_async_sync(self.visual.extract_info(task), timeout_s=12.0)
            return [{"title": "视觉智能体情报提炼", "snippet": res, "url": "browser-use"}]
        except Exception as e:
            print(f"[AgentBrowser] Visual search error: {e}")
            return []

    def scrape_okooo_odds_search(self, home_team: str, away_team: str) -> list:
        """兜底：依然保留 ddgs 轻量搜索"""
        if not self.ddgs:
            return []
        query = f"澳客 OR 捷报比分 {home_team} vs {away_team} 赔率 分析"
        results = self.gatekeeper.run_sync(
            lambda: list(self.ddgs.text(query, max_results=3)),
            timeout_s=self.gatekeeper.policy.ddgs_timeout_s,
            default=[],
        )
        if not results:
            return []
        return [{"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")} for r in results]

    def scrape_500_eu_odds_visual(self, *, home_team: str, away_team: str, kickoff_time: Optional[str] = None) -> Dict[str, Any]:
        if self.visual is None:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_AVAILABLE", "message": "visual browser not configured"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        date_hint = None
        if kickoff_time:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", kickoff_time)
            if m:
                date_hint = m.group(1)

        task = (
            "访问 500.com（或其赔率子站 odds.500.com）。"
            f"找到 {home_team} vs {away_team} 的竞彩足球欧赔（主胜/平/客胜），优先取“平均欧赔”或“即时欧赔”。"
            "严格返回 JSON 对象："
            '{"eu_odds":{"home":数字,"draw":数字,"away":数字},"source_url":"URL","provider":"500.com"}。'
            "如果找不到或无法确认，请返回空 JSON 对象 {}。"
        )
        if date_hint:
            task = f"{task} 日期提示：{date_hint}。"

        try:
            res = _run_async_sync(self.visual.extract_info(task), timeout_s=18.0)
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "FETCH_FAILED", "message": f"visual extract failed: {type(e).__name__}"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        try:
            m = re.search(r"\{[\s\S]*\}", str(res))
            if not m:
                raise ValueError("no json object")
            obj = json.loads(m.group(0))
            eu = obj.get("eu_odds") if isinstance(obj, dict) else None
            if not isinstance(eu, dict):
                raise ValueError("eu_odds missing")
            home = float(eu.get("home"))
            draw = float(eu.get("draw"))
            away = float(eu.get("away"))
            if not (1.01 <= home <= 200 and 1.01 <= draw <= 200 and 1.01 <= away <= 200):
                raise ValueError("odds out of range")
        except Exception:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "PARSE_FAILED", "message": "visual output parse failed"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        payload = {
            "eu_odds": {"home": home, "draw": draw, "away": away},
            "provider": str(obj.get("provider") or "500.com"),
            "source_url": obj.get("source_url"),
            "raw_text": str(res)[:2000],
        }
        raw_ref = _sha1_ref("browser_use:eu_odds", payload)
        return {
            "ok": True,
            "data": payload,
            "error": None,
            "meta": {"mock": False, "source": "500.com", "confidence": 0.65, "stale": False, "raw_ref": raw_ref},
        }

    def scrape_500_jingcai_sp_visual(self, *, home_team: str, away_team: str, kickoff_time: Optional[str] = None) -> Dict[str, Any]:
        if self.visual is None:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_AVAILABLE", "message": "visual browser not configured"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        date_hint = None
        if kickoff_time:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", kickoff_time)
            if m:
                date_hint = m.group(1)

        task = (
            "访问 https://trade.500.com/jczq/ 的胜平负/让球胜平负页面。"
            f"定位 {home_team} vs {away_team} 这一行，提取两个盘口："
            "1) 胜平负(让球=0) 的 主胜/平/客胜 SP；"
            "2) 让球胜平负(让球为-1/+1等) 的 主胜/平/客胜 SP。"
            "严格返回 JSON："
            '{"jingcai_sp":{"WDL":{"handicap":0,"home":数字,"draw":数字,"away":数字},"HANDICAP_WDL":{"handicap":数字,"home":数字,"draw":数字,"away":数字}},"source_url":"URL","provider":"500.com"}。'
            "如果只能拿到其中一个盘口，也请只返回该盘口对象。找不到则返回 {}。"
        )
        if date_hint:
            task = f"{task} 日期提示：{date_hint}。"

        try:
            res = _run_async_sync(self.visual.extract_info(task), timeout_s=22.0)
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "FETCH_FAILED", "message": f"visual extract failed: {type(e).__name__}"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        try:
            m = re.search(r"\{[\s\S]*\}", str(res))
            if not m:
                raise ValueError("no json object")
            obj = json.loads(m.group(0))
            sp = obj.get("jingcai_sp") if isinstance(obj, dict) else None
            if not isinstance(sp, dict) or not sp:
                raise ValueError("jingcai_sp missing")
        except Exception:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "PARSE_FAILED", "message": "visual output parse failed"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        payload = {
            "jingcai_sp": sp,
            "provider": str(obj.get("provider") or "500.com"),
            "source_url": obj.get("source_url"),
            "raw_text": str(res)[:2000],
        }
        raw_ref = _sha1_ref("browser_use:jingcai_sp", payload)
        return {
            "ok": True,
            "data": payload,
            "error": None,
            "meta": {"mock": False, "source": "500.com", "confidence": 0.55, "stale": False, "raw_ref": raw_ref},
        }

    def scrape_500_beidan_sp_visual(self, *, home_team: str, away_team: str, kickoff_time: Optional[str] = None) -> Dict[str, Any]:
        if self.visual is None:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_AVAILABLE", "message": "visual browser not configured"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        date_hint = None
        if kickoff_time:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", kickoff_time)
            if m:
                date_hint = m.group(1)

        task = (
            "访问 https://trade.500.com/bjdc/ (足球单场) 让球胜平负页面。"
            f"定位 {home_team} vs {away_team} 这一场，提取让球数(handicap) 以及 主胜/平/主负 的 SP。"
            "严格返回 JSON："
            '{"beidan_sp":{"HANDICAP_WDL":{"handicap":数字,"home":数字,"draw":数字,"away":数字}},"source_url":"URL","provider":"500.com"}。'
            "找不到则返回 {}。"
        )
        if date_hint:
            task = f"{task} 日期提示：{date_hint}。"

        try:
            res = _run_async_sync(self.visual.extract_info(task), timeout_s=22.0)
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "FETCH_FAILED", "message": f"visual extract failed: {type(e).__name__}"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        try:
            m = re.search(r"\{[\s\S]*\}", str(res))
            if not m:
                raise ValueError("no json object")
            obj = json.loads(m.group(0))
            sp = obj.get("beidan_sp") if isinstance(obj, dict) else None
            if not isinstance(sp, dict) or not sp:
                raise ValueError("beidan_sp missing")
        except Exception:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "PARSE_FAILED", "message": "visual output parse failed"},
                "meta": {"mock": False, "source": "browser_use", "confidence": 0.0, "stale": True},
            }

        payload = {
            "beidan_sp": sp,
            "provider": str(obj.get("provider") or "500.com"),
            "source_url": obj.get("source_url"),
            "raw_text": str(res)[:2000],
        }
        raw_ref = _sha1_ref("browser_use:beidan_sp", payload)
        return {
            "ok": True,
            "data": payload,
            "error": None,
            "meta": {"mock": False, "source": "500.com", "confidence": 0.5, "stale": False, "raw_ref": raw_ref},
        }

    def search_web(self, query: str, max_results: int = 5) -> list:
        if not self.ddgs:
            return []
        return self.gatekeeper.run_sync(
            lambda: list(self.ddgs.text(query, max_results=max_results)),
            timeout_s=self.gatekeeper.policy.ddgs_timeout_s,
            default=[],
        )
