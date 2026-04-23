import asyncio
import json
import hashlib
import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests
from core.data_contract import NormalizedLiveState, NormalizedMatch, NormalizedOdds
from core.match_identity import MatchIdentityBuilder
from tools.entity_resolver import EntityResolver
from tools.domestic_sources import DomesticSources
from tools.snapshot_store import SnapshotStore
from tools.agent_browser import AgentBrowser
from tools.api_clients import ForeignAPIClient
from tools.web_intel_extractor import WebIntelExtractor


class MultiSourceFetcher:
    def __init__(
        self,
        store: SnapshotStore | None = None,
        resolver: EntityResolver | None = None,
        *,
        online: bool = False,
    ):
        self.store = store or SnapshotStore()
        self.resolver = resolver or EntityResolver()
        self.online = bool(online)
        self.browser = AgentBrowser(online=self.online)
        self.domestic = DomesticSources(browser=self.browser)
        self.foreign_api = ForeignAPIClient()
        self.identity = MatchIdentityBuilder()
        self.web_intel = WebIntelExtractor(browser=self.browser, identity=self.identity)
        self._odds_context: Dict[tuple[str, str], Dict[str, Any]] = {}

    def fetch_odds_sync(self, home_team: str, away_team: str) -> dict:
        return self._fetch_odds_impl(home_team=home_team, away_team=away_team)

    async def fetch_odds(self, home_team: str, away_team: str) -> dict:
        return self._fetch_odds_impl(home_team=home_team, away_team=away_team)

    def _fetch_odds_impl(self, home_team: str, away_team: str) -> dict:
        ctx = self._odds_context.get((home_team, away_team)) or {}
        kickoff_time = ctx.get("kickoff_time")
        lottery_type = str(ctx.get("lottery_type") or "")
        market = str(ctx.get("market") or "")
        fid = ctx.get("fid")
        skip_foreign_api = bool(ctx.get("skip_foreign_api") or False) or (not self.online)
        skip_browser_fallback = bool(ctx.get("skip_browser_fallback") or False) or (not self.online)
        degradations: List[str] = []

        home = self.resolver.resolve_team(home_team)
        away = self.resolver.resolve_team(away_team)
        if not home["ok"] or not away["ok"]:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "BAD_INPUT", "message": "team resolve failed"},
                "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
            }

        match_id = f"ODDS::{home['data']['team_id']}::{away['data']['team_id']}"
        self.store.upsert_match(match_id, "Unknown", home_team, away_team, "Unknown", "agent_browser")
        
        latest = self.store.get_latest_snapshot("odds", match_id)
        if latest["ok"]:
            payload = latest["data"]["payload"]
            if not isinstance(payload, dict):
                payload = {}

            wants_sp = lottery_type in {"JINGCAI", "BEIDAN"} and market in {"WDL", "HANDICAP_WDL"}
            if not wants_sp:
                return {
                    "ok": True,
                    "data": payload,
                    "error": None,
                    "meta": {
                        "mock": False,
                        "source": "snapshot",
                        "confidence": float(latest["data"]["meta"]["confidence"]),
                        "stale": True,
                    },
                }

            if lottery_type == "JINGCAI" and isinstance(payload.get("jingcai_sp"), dict) and market in payload["jingcai_sp"]:
                return {
                    "ok": True,
                    "data": payload,
                    "error": None,
                    "meta": {
                        "mock": False,
                        "source": "snapshot",
                        "confidence": float(latest["data"]["meta"]["confidence"]),
                        "stale": True,
                    },
                }
            if lottery_type == "BEIDAN" and isinstance(payload.get("beidan_sp"), dict) and market in payload["beidan_sp"]:
                return {
                    "ok": True,
                    "data": payload,
                    "error": None,
                    "meta": {
                        "mock": False,
                        "source": "snapshot",
                        "confidence": float(latest["data"]["meta"]["confidence"]),
                        "stale": True,
                    },
                }

        if lottery_type == "JINGCAI" and market in {"WDL", "HANDICAP_WDL"}:
            domestic_odds = self.domestic.get_jingcai_sp(
                home_team=home_team, away_team=away_team, kickoff_time=kickoff_time, fid=str(fid) if fid else None
            )
        elif lottery_type == "BEIDAN" and market in {"WDL", "HANDICAP_WDL"}:
            domestic_odds = self.domestic.get_beidan_sp(
                home_team=home_team, away_team=away_team, kickoff_time=kickoff_time, fid=str(fid) if fid else None
            )
        else:
            domestic_odds = self.domestic.get_eu_odds(
                home_team=home_team, away_team=away_team, kickoff_time=kickoff_time, fid=str(fid) if fid else None
            )
        if domestic_odds.get("ok"):
            meta = domestic_odds.get("meta") or {}
            self.store.insert_snapshot(
                "odds",
                match_id,
                str(meta.get("source") or "500.com"),
                domestic_odds.get("data") or {},
                float(meta.get("confidence") or 0.0),
                False,
            )
            return domestic_odds
        domestic_err = domestic_odds.get("error") or {}
        if isinstance(domestic_err, dict) and domestic_err.get("code") == "CAPTCHA_REQUIRED":
            domestic_src = str((domestic_odds.get("meta") or {}).get("source") or "domestic")
            degradations.append(f"captcha_required:{domestic_src}")

        if skip_foreign_api:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_FOUND", "message": "foreign api disabled for this call"},
                "meta": {
                    "mock": False,
                    "source": "multisource",
                    "confidence": 0.0,
                    "stale": True,
                    "degradations": list(degradations) if degradations else [],
                },
            }

        foreign_odds = self.foreign_api.get_odds(home_team, away_team)
        if foreign_odds.get("ok"):
            foreign_meta = foreign_odds.get("meta") or {}
            foreign_src = str(foreign_meta.get("source") or "foreign_api")
            out_meta = dict(foreign_meta)
            if degradations:
                confidence = 0.35
                out_meta["confidence"] = confidence
                out_meta["degradations"] = list(degradations)
            else:
                confidence = 0.9
            out = dict(foreign_odds)
            out["meta"] = out_meta
            self.store.insert_snapshot("odds", match_id, foreign_src, foreign_odds.get("data") or {}, confidence, False)
            return out

        if skip_browser_fallback:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "NOT_FOUND", "message": "browser fallback disabled for this call"},
                "meta": {
                    "mock": False,
                    "source": "multisource",
                    "confidence": 0.0,
                    "stale": True,
                    "degradations": list(degradations) if degradations else [],
                },
            }

        browser_results = self.browser.scrape_okooo_odds_search(home_team, away_team)
        if browser_results:
            # We save this unstructured data as a snapshot
            payload = {"raw_analysis": browser_results, "home_team": home_team, "away_team": away_team}
            self.store.insert_snapshot("odds", match_id, "agent_browser", payload, 0.6, False)
            return {
                "ok": True,
                "data": payload,
                "error": None,
                "meta": {
                    "mock": False,
                    "source": "agent_browser",
                    "confidence": 0.6,
                    "stale": False,
                    "degradations": list(degradations) if degradations else [],
                },
            }

        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "no odds snapshot and browser fallback failed"},
            "meta": {
                "mock": False,
                "source": "multisource",
                "confidence": 0.0,
                "stale": True,
                "degradations": list(degradations) if degradations else [],
            },
        }

    def _snapshot_ref(self, category: str, key: str, payload: Dict[str, Any], source: str, confidence: float) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        digest = hashlib.sha1(encoded).hexdigest()[:12]
        self.store.insert_snapshot(category=category, match_id=key, source=source, payload=payload, confidence=confidence, stale=False)
        return f"snapshot:{category}:{source}:{digest}"

    def _snapshot_ref_cached(self, category: str, source: str, payload: Dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        digest = hashlib.sha1(encoded).hexdigest()[:12]
        return f"snapshot:{category}:{source}:{digest}"

    def get_fixtures_normalized(self, date: str) -> List[Dict[str, Any]]:
        cached = self.store.get_latest_snapshot(category="fixtures", match_id=f"FIXTURES::{date}")
        if cached.get("ok"):
            payload = cached.get("data", {}).get("payload") or {}
            if isinstance(payload, dict) and isinstance(payload.get("fixtures"), list):
                meta = cached.get("data", {}).get("meta") or {}
                fixtures = payload.get("fixtures") or []
                source = str(meta.get("source") or "snapshot")
                confidence = float(meta.get("confidence") or 0.0)
                raw_ref = self._snapshot_ref_cached(
                    category="fixtures",
                    source=source,
                    payload={"date": date, "fixtures": fixtures},
                )
            else:
                fixtures = []
                source = "snapshot"
                confidence = 0.0
                raw_ref = self._snapshot_ref_cached(category="fixtures", source=source, payload={"date": date, "fixtures": fixtures})
        else:
            raw = self.fetch_fixtures_sync(date=date)
            if not raw.get("ok"):
                if not self.online:
                    return []
                intel = self.web_intel.extract_fixtures_normalized(date=date)
                return intel if intel else []

            fixtures = raw.get("data", {}).get("fixtures") or []
            meta = raw.get("meta", {}) or {}
            source = str(meta.get("source") or "multisource")
            confidence = float(meta.get("confidence") or 0.0)
            raw_ref = self._snapshot_ref(
                category="fixtures",
                key=f"FIXTURES::{date}",
                payload={"date": date, "fixtures": fixtures},
                source=source,
                confidence=confidence,
            )

        out: List[Dict[str, Any]] = []
        for fx in fixtures:
            league_name = (fx.get("league") or fx.get("league_name") or "UNK").strip()
            kickoff_time = (fx.get("kickoff_time") or fx.get("kickoff") or f"{date} 00:00").strip()
            home_team = (fx.get("home_team") or "").strip()
            away_team = (fx.get("away_team") or "").strip()
            if not home_team or not away_team:
                continue
            fid = fx.get("fid")
            source_ids: Dict[str, Any] = {}
            if fid:
                source_ids["500.com"] = {"fid": str(fid)}

            match_id = self.identity.build(league_name, home_team, away_team, kickoff_time)
            league_code = self.identity.league_resolver.resolve_code(league_name)
            home_id = self.identity.team_resolver.resolve_team_id(home_team)
            away_id = self.identity.team_resolver.resolve_team_id(away_team)
            status_raw = (fx.get("status") or "").strip().lower()
            if status_raw in {"live", "playing"}:
                status = "LIVE"
            elif status_raw in {"played", "finished", "ft"}:
                status = "FINISHED"
            else:
                status = "SCHEDULED"

            m = NormalizedMatch(
                match_id=match_id,
                league_code=league_code,
                home_team_id=home_id,
                away_team_id=away_id,
                kickoff_time_utc=kickoff_time,
                status=status,  # type: ignore[arg-type]
                source=source,
                confidence=confidence,
                raw_ref=raw_ref,
            )
            rec = asdict(m)
            rec["source_ids"] = source_ids
            rec["league_name"] = league_name
            rec["home_team"] = home_team
            rec["away_team"] = away_team
            out.append(rec)
        return out

    def get_odds_normalized(
        self,
        *,
        league_name: str,
        home_team: str,
        away_team: str,
        kickoff_time: str,
        source_ids: Optional[Dict[str, Any]] = None,
        lottery_type: str = "JINGCAI",
        play_type: str = "JINGCAI_WDL",
        market: str = "WDL",
        handicap: Optional[float] = None,
    ) -> Dict[str, Any]:
        match_id = self.identity.build(league_name, home_team, away_team, kickoff_time)
        fid: Optional[str] = None
        if isinstance(source_ids, dict):
            if isinstance(source_ids.get("500.com"), dict) and source_ids["500.com"].get("fid"):
                fid = str(source_ids["500.com"]["fid"])
            elif source_ids.get("fid"):
                fid = str(source_ids.get("fid"))
        base_ctx = {
            "kickoff_time": kickoff_time,
            "league_name": league_name,
            "lottery_type": lottery_type,
            "play_type": play_type,
            "market": market,
            "fid": fid,
        }
        self._odds_context[(home_team, away_team)] = {**base_ctx, "skip_foreign_api": True, "skip_browser_fallback": True}
        raw = self.fetch_odds_sync(home_team=home_team, away_team=away_team)
        self._odds_context[(home_team, away_team)] = base_ctx
        meta = raw.get("meta", {}) or {}
        source = str(meta.get("source") or "multisource")
        confidence = float(meta.get("confidence") or 0.0)
        degradations: List[str] = []
        if isinstance(meta, dict) and isinstance(meta.get("degradations"), list):
            degradations = [str(x) for x in meta.get("degradations") if x]
        payload = raw.get("data") or {}

        selections: Dict[str, Dict[str, Any]] = {}
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        parsed_handicap: Optional[float] = None

        if isinstance(payload, dict) and isinstance(payload.get("jingcai_sp"), dict):
            sp_market = payload["jingcai_sp"].get(market)
            if isinstance(sp_market, dict):
                try:
                    selections = {
                        "H": {"odds": float(sp_market["home"]), "sp": float(sp_market["home"]), "last_update": now},
                        "D": {"odds": float(sp_market["draw"]), "sp": float(sp_market["draw"]), "last_update": now},
                        "A": {"odds": float(sp_market["away"]), "sp": float(sp_market["away"]), "last_update": now},
                    }
                    parsed_handicap = float(sp_market.get("handicap")) if sp_market.get("handicap") is not None else None
                except Exception:
                    selections = {}

        if not selections and isinstance(payload, dict) and isinstance(payload.get("beidan_sp"), dict):
            sp_market = payload["beidan_sp"].get(market)
            if isinstance(sp_market, dict):
                try:
                    selections = {
                        "H": {"odds": float(sp_market["home"]), "sp": float(sp_market["home"]), "last_update": now},
                        "D": {"odds": float(sp_market["draw"]), "sp": float(sp_market["draw"]), "last_update": now},
                        "A": {"odds": float(sp_market["away"]), "sp": float(sp_market["away"]), "last_update": now},
                    }
                    parsed_handicap = float(sp_market.get("handicap")) if sp_market.get("handicap") is not None else None
                except Exception:
                    selections = {}

        if not selections and isinstance(payload, dict) and isinstance(payload.get("eu_odds"), dict):
            eu = payload["eu_odds"]
            for k, sel in (("H", "home"), ("D", "draw"), ("A", "away")):
                if sel in eu and eu[sel] is not None:
                    selections[k] = {"odds": float(eu[sel]), "last_update": now}

        if not selections and isinstance(payload, dict):
            for k in ("H", "D", "A"):
                if k in payload and payload[k] is not None:
                    selections[k] = {"odds": float(payload[k]), "last_update": now}

        final_source = source
        final_confidence = confidence
        final_payload = payload
        final_degradations = list(degradations)
        allow_external_fallbacks = self.online and not (raw.get("ok") and isinstance(meta, dict) and bool(meta.get("mock") or False))

        if not selections and allow_external_fallbacks:
            intel = self.web_intel.extract_odds_normalized(
                league_name=league_name,
                home_team=home_team,
                away_team=away_team,
                kickoff_time=kickoff_time,
                lottery_type=lottery_type,
                play_type=play_type,
                market=market,
                handicap=handicap,
            )
            if intel.get("ok"):
                selections = intel.get("selections") or {}
                final_source = str(intel.get("source") or "web_intel")
                final_confidence = float(intel.get("confidence") or 0.0)
                final_payload = dict(intel)
                final_degradations.extend([str(x) for x in (intel.get("degradations") or []) if x])

        if not selections and allow_external_fallbacks:
            foreign = self.foreign_api.get_odds(home_team, away_team)
            if foreign.get("ok"):
                foreign_meta = foreign.get("meta") or {}
                foreign_src = str(foreign_meta.get("source") or "foreign_api")
                foreign_payload = foreign.get("data") or {}
                selections = {}
                if isinstance(foreign_payload, dict) and isinstance(foreign_payload.get("eu_odds"), dict):
                    eu = foreign_payload.get("eu_odds") or {}
                    for k, sel in (("H", "home"), ("D", "draw"), ("A", "away")):
                        if sel in eu and eu[sel] is not None:
                            selections[k] = {"odds": float(eu[sel]), "last_update": now}
                if not selections and isinstance(foreign_payload, dict) and isinstance(foreign_payload.get("foreign_api_odds"), list):
                    arr = foreign_payload.get("foreign_api_odds") or []
                    if arr and isinstance(arr[0], dict) and isinstance(arr[0].get("odds"), list):
                        odds_arr = arr[0].get("odds") or []
                        mapped: Dict[str, float] = {}
                        for it in odds_arr:
                            if not isinstance(it, dict) or it.get("price") is None:
                                continue
                            name = str(it.get("name") or "").strip().lower()
                            price = float(it.get("price"))
                            if name in {"draw", "平局"}:
                                mapped["D"] = price
                            elif name and name in str(arr[0].get("home_team_en") or "").strip().lower():
                                mapped["H"] = price
                            elif name and name in str(arr[0].get("away_team_en") or "").strip().lower():
                                mapped["A"] = price
                        if len(mapped) < 3 and len(odds_arr) >= 3:
                            try:
                                mapped.setdefault("H", float(odds_arr[0].get("price")))
                                mapped.setdefault("D", float(odds_arr[1].get("price")))
                                mapped.setdefault("A", float(odds_arr[2].get("price")))
                            except Exception:
                                mapped = {}
                        if mapped.get("H") is not None and mapped.get("D") is not None and mapped.get("A") is not None:
                            selections = {
                                "H": {"odds": float(mapped["H"]), "last_update": now},
                                "D": {"odds": float(mapped["D"]), "last_update": now},
                                "A": {"odds": float(mapped["A"]), "last_update": now},
                            }
                if selections:
                    final_source = foreign_src
                    final_confidence = 0.35 if final_degradations else float(foreign_meta.get("confidence") or 0.9)
                    final_payload = foreign_payload

        raw_ref = self._snapshot_ref(
            category="odds_raw",
            key=f"ODDS::{match_id}::{market}",
            payload={"match_id": match_id, "market": market, "payload": final_payload, "meta": meta},
            source=final_source,
            confidence=final_confidence,
        )

        base = {
            "match_id": match_id,
            "lottery_type": lottery_type,
            "play_type": play_type,
            "market": market,
            "handicap": handicap if handicap is not None else parsed_handicap,
            "selections": selections,
            "source": final_source,
            "confidence": final_confidence,
            "raw_ref": raw_ref,
            "degradations": final_degradations,
        }
        if not selections:
            return {
                "ok": False,
                **base,
                "error": {
                    "code": "ODDS_UNAVAILABLE",
                    "message": f"no structured odds parsed from source={source}",
                },
            }

        o = NormalizedOdds(
            match_id=match_id,
            lottery_type=lottery_type,  # type: ignore[arg-type]
            play_type=play_type,  # type: ignore[arg-type]
            market=market,
            handicap=handicap if handicap is not None else parsed_handicap,
            selections=selections,
            source=final_source,
            confidence=final_confidence,
            raw_ref=raw_ref,
        )
        return {"ok": True, **asdict(o), "degradations": final_degradations}

    def get_live_state_normalized(
        self,
        *,
        match_id: Optional[str] = None,
        league_name: Optional[str] = None,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
        kickoff_time: Optional[str] = None,
        source_ids: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not match_id:
            if not (league_name and home_team and away_team and kickoff_time):
                return {
                    "ok": False,
                    "match_id": None,
                    "error": {"code": "BAD_INPUT", "message": "need match_id or (league_name,home_team,away_team,kickoff_time)"},
                }
            match_id = self.identity.build(str(league_name), str(home_team), str(away_team), str(kickoff_time))

        if not (home_team and away_team and kickoff_time and league_name):
            m = self.store.get_match(match_id)
            if m.get("ok"):
                md = m.get("data") or {}
                league_name = str(league_name or md.get("league") or "UNK")
                home_team = str(home_team or md.get("home_team") or "")
                away_team = str(away_team or md.get("away_team") or "")
                kickoff_time = str(kickoff_time or md.get("kickoff_time") or "")

        fid: Optional[str] = None
        if isinstance(source_ids, dict):
            if isinstance(source_ids.get("500.com"), dict) and source_ids["500.com"].get("fid"):
                fid = str(source_ids["500.com"]["fid"])
            elif source_ids.get("fid"):
                fid = str(source_ids.get("fid"))

        match: Dict[str, Any] = {
            "match_id": match_id,
            "league": league_name,
            "home_team": home_team,
            "away_team": away_team,
            "kickoff_time": kickoff_time,
            "source_ids": source_ids or ({"500.com": {"fid": fid}} if fid else {}),
        }
        if fid:
            match["fid"] = fid

        raw = self.domestic.get_live_state(match)
        if not raw.get("ok"):
            err = raw.get("error") if isinstance(raw, dict) else None
            return {
                "ok": False,
                "match_id": match_id,
                "error": err if isinstance(err, dict) else {"code": "LIVE_STATE_UNAVAILABLE", "message": "live state unavailable"},
            }

        meta = raw.get("meta") or {}
        source = str(meta.get("source") or "live.500.com")
        confidence = float(meta.get("confidence") or 0.0)
        payload = raw.get("data") or {}
        raw_ref = self._snapshot_ref(
            category="live_state",
            key=match_id,
            payload={"match_id": match_id, "live_state": payload},
            source=source,
            confidence=confidence,
        )

        minute = int(payload.get("minute") or 0)
        score_ft = str(payload.get("ft_score") or payload.get("score_ft") or "")
        red_cards = payload.get("red_cards")
        rc: Dict[str, int] = {"home": 0, "away": 0}
        if isinstance(red_cards, dict):
            if red_cards.get("home") is not None:
                rc["home"] = int(red_cards.get("home") or 0)
            if red_cards.get("away") is not None:
                rc["away"] = int(red_cards.get("away") or 0)

        live = NormalizedLiveState(
            match_id=match_id,
            minute=minute,
            score_ft=score_ft,
            red_cards=rc,
            lineups=None,
            injuries_suspensions=None,
            key_events=None,
            source=source,
            confidence=confidence,
            raw_ref=raw_ref,
        )
        return {"ok": True, **asdict(live)}

    def get_results_normalized(self, date: str) -> List[Dict[str, Any]]:
        cached = self.store.get_latest_snapshot(category="results", match_id=f"RESULTS::{date}")
        if cached.get("ok"):
            payload = cached.get("data", {}).get("payload") or {}
            if isinstance(payload, dict) and isinstance(payload.get("results"), list):
                meta = cached.get("data", {}).get("meta") or {}
                results = payload.get("results") or []
                source = str(meta.get("source") or "snapshot")
                confidence = float(meta.get("confidence") or 0.0)
                raw_ref = self._snapshot_ref_cached(
                    category="results",
                    source=source,
                    payload={"date": date, "results": results},
                )
            else:
                results = []
                source = "snapshot"
                confidence = 0.0
                raw_ref = self._snapshot_ref_cached(category="results", source=source, payload={"date": date, "results": results})
        else:
            raw = self.fetch_results_sync(date=date)
            if not raw.get("ok"):
                if not self.online:
                    return []
                intel = self.web_intel.extract_results_normalized(date=date)
                return intel if intel else []
            results = raw.get("data", {}).get("results") or []
            meta = raw.get("meta", {}) or {}
            source = str(meta.get("source") or "multisource")
            confidence = float(meta.get("confidence") or 0.0)
            raw_ref = self._snapshot_ref(
                category="results",
                key=f"RESULTS::{date}",
                payload={"date": date, "results": results},
                source=source,
                confidence=confidence,
            )

        out: List[Dict[str, Any]] = []
        for r in results:
            if not isinstance(r, dict):
                continue
            league_name = str(r.get("league") or r.get("league_name") or "UNK").strip()
            kickoff_time = str(r.get("kickoff_time") or r.get("kickoff") or f"{date} 00:00").strip()
            home_team = str(r.get("home_team") or "").strip()
            away_team = str(r.get("away_team") or "").strip()
            if not home_team or not away_team:
                continue
            fid = r.get("fid")
            source_ids: Dict[str, Any] = {}
            if fid:
                source_ids["500.com"] = {"fid": str(fid)}

            match_id = str(r.get("match_id") or self.identity.build(league_name, home_team, away_team, kickoff_time))
            status_raw = str(r.get("status") or "FINISHED").strip().upper()
            if status_raw in {"CANCELLED", "VOID"}:
                status = "CANCELLED"
            elif status_raw in {"POSTPONED"}:
                status = "POSTPONED"
            elif status_raw in {"ABANDONED"}:
                status = "ABANDONED"
            else:
                status = "FINISHED"

            score_ft = r.get("score_ft")
            if score_ft is not None:
                score_ft = str(score_ft).strip().replace(":", "-")
                if not score_ft or not re.fullmatch(r"\d{1,2}-\d{1,2}", score_ft):
                    score_ft = None

            score_ht = r.get("score_ht")
            if score_ht is not None:
                score_ht = str(score_ht).strip().replace(":", "-")
                if not score_ht or not re.fullmatch(r"\d{1,2}-\d{1,2}", score_ht):
                    score_ht = None

            if status == "FINISHED" and not score_ft:
                continue

            rec: Dict[str, Any] = {
                "match_id": match_id,
                "status": status,
                "score_ft": score_ft,
                "source": source,
                "confidence": confidence,
                "raw_ref": raw_ref,
                "source_ids": source_ids,
                "league": league_name,
                "kickoff_time": kickoff_time,
                "home_team": home_team,
                "away_team": away_team,
            }
            if score_ht:
                rec["score_ht"] = score_ht
            out.append(rec)

        return out

    def fetch_results_sync(self, date: str) -> dict:
        res = self.domestic.get_results(date=date)
        if res.get("ok"):
            data = res.get("data") or {}
            results = data.get("results") if isinstance(data, dict) else None
            if isinstance(results, list) and results:
                meta = res.get("meta", {}) or {}
                return {
                    "ok": True,
                    "data": {"results": results},
                    "error": None,
                    "meta": {
                        "mock": bool(meta.get("mock") or False),
                        "source": str(meta.get("source") or "500.com"),
                        "confidence": float(meta.get("confidence") or 0.0),
                        "stale": bool(meta.get("stale") or False),
                    },
                }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "failed to fetch domestic results"},
            "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
        }

    def fetch_fixtures_sync(self, date: Optional[str] = None) -> dict:
        fixtures = self.domestic.get_fixtures(date=date)
        if fixtures:
            return {
                "ok": True,
                "data": {"fixtures": fixtures},
                "error": None,
                "meta": {"mock": False, "source": "500.com", "confidence": 0.9, "stale": False},
            }

        if date:
            latest = self.store.get_latest_snapshot(category="fixtures", match_id=f"FIXTURES::{date}")
            if latest.get("ok"):
                payload = latest.get("data", {}).get("payload") or {}
                if isinstance(payload, dict) and isinstance(payload.get("fixtures"), list) and payload.get("fixtures"):
                    meta = latest.get("data", {}).get("meta") or {}
                    return {
                        "ok": True,
                        "data": {"fixtures": payload.get("fixtures")},
                        "error": None,
                        "meta": {
                            "mock": False,
                            "source": str(meta.get("source") or "snapshot"),
                            "confidence": float(meta.get("confidence") or 0.0),
                            "stale": True,
                        },
                    }

        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "failed to fetch fixtures from 500.com"},
            "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
        }

    def fetch_injuries_sync(self, team_name: str) -> dict:
        """Fetch injuries using Dongqiudi search via AgentBrowser"""
        news = self.browser.search_dongqiudi_news(team_name)
        if news:
            return {
                "ok": True,
                "data": {"injuries": news},
                "error": None,
                "meta": {"mock": False, "source": "dongqiudi", "confidence": 0.8, "stale": False},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "failed to fetch injuries/news from dongqiudi"},
            "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
        }

    def fetch_news_sync(self, team_name: str, limit: int = 5) -> dict:
        news = self.browser.search_dongqiudi_news(team_name)
        if news:
            return {
                "ok": True,
                "data": {"articles": news},
                "error": None,
                "meta": {"mock": False, "source": "dongqiudi", "confidence": 0.8, "stale": False},
            }
        return {
            "ok": False,
            "data": None,
            "error": {"code": "NOT_FOUND", "message": "failed to fetch news from dongqiudi"},
            "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True},
        }

    def fetch_weather_sync(self, city: str, api_key: str) -> dict:
        """Fetch real weather data using OpenWeatherMap API"""
        # 如果没有传入 city，设置一个默认的足球城市用于测试，实际应由外部传入比赛所在城市
        if not city:
            city = "London"
            
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                # 转换 OpenWeatherMap condition 匹配 EnvironmentAnalyzer 的认知
                raw_condition = data["weather"][0]["main"].lower()
                condition_map = {
                    "rain": "heavy_rain",
                    "drizzle": "heavy_rain",
                    "thunderstorm": "heavy_rain",
                    "snow": "snow",
                    "clear": "clear",
                    "clouds": "clear", # 多云对比赛影响不大，视为 clear
                    "extreme": "extreme_heat" # 简化处理
                }
                mapped_condition = condition_map.get(raw_condition, "clear")
                
                return {
                    "ok": True,
                    "data": {
                        "temperature": data["main"]["temp"],
                        "condition": mapped_condition,
                        "wind": "strong" if data["wind"]["speed"] > 8 else "light",
                    },
                    "error": None,
                    "meta": {"mock": False, "source": "openweathermap", "confidence": 1.0, "stale": False}
                }
            return {
                "ok": False,
                "data": None,
                "error": {"code": "API_ERROR", "message": f"Status: {response.status_code}"},
                "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True}
            }
        except Exception as e:
            return {
                "ok": False,
                "data": None,
                "error": {"code": "REQUEST_FAILED", "message": str(e)},
                "meta": {"mock": False, "source": "multisource", "confidence": 0.0, "stale": True}
            }
