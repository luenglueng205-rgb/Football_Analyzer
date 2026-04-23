# 真实天气 API 接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除系统中的天气 Mock 数据，接入真实的 OpenWeatherMap API，为 EnvironmentAnalyzer 提供真实的非结构化气象数据。

**Architecture:** 在 `MultiSourceFetcher` 中封装对 OpenWeatherMap API 的网络请求，处理 JSON 响应，并转换成统一的天气描述（如 `clear`, `heavy_rain`）。在 `ScoutAgent` 中移除硬编码，调用 Fetcher，并保留 Mock 作为网络失败时的降级方案。

**Tech Stack:** Python 3.10+, `requests`

---

### Task 1: 在 Fetcher 中封装 OpenWeatherMap API

**Files:**
- Modify: `standalone_workspace/tools/multisource_fetcher.py`

- [ ] **Step 1: 添加 `fetch_weather_sync` 方法**

在 `MultiSourceFetcher` 类中增加真实 API 的调用和数据转换逻辑。注意需要将 OpenWeatherMap 的天气 condition（如 'Rain', 'Snow', 'Clear'）映射到我们 `EnvironmentAnalyzer` 认识的格式（如 `heavy_rain`, `snow`, `clear`）。

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/tools/multisource_fetcher.py
git commit -m "feat: add OpenWeatherMap API integration in fetcher"
```

### Task 2: 替换 ScoutAgent 中的 Mock 逻辑

**Files:**
- Modify: `standalone_workspace/agents/async_scout.py`

- [ ] **Step 1: 修改 `_get_weather_info` 方法**

引入 `MultiSourceFetcher`，并使用用户提供的真实 API Key。

```python
    def _get_weather_info(self, match_info: dict = None) -> dict:
        """
        接入真实的 OpenWeatherMap API。
        优先从 match_info 提取主队所在城市，提取失败默认用伦敦。
        """
        api_key = "72614075c57839dcdab31d0edbb2df26" # 用户提供的真实 Key
        
        # 尝试从 match_info 中提取城市名称，如果没有则默认伦敦
        city = "London"
        if match_info and match_info.get("home_team"):
            city = match_info.get("home_team").split()[0] # 极其简化的球队到城市的映射，真实环境需查字典
            
        try:
            # 这里需要用到 multisource_fetcher
            from tools.multisource_fetcher import MultiSourceFetcher
            fetcher = MultiSourceFetcher()
            result = fetcher.fetch_weather_sync(city, api_key)
            
            if result.get("ok") and result.get("data"):
                return result["data"]
        except Exception as e:
            logger.warning(f"获取真实天气异常，降级使用 Mock: {e}")
            
        # Fallback 降级：如果 API 调用失败或断网，返回默认的好天气，不干扰 xG
        return {"temperature": 15, "condition": "clear", "wind": "light"}
```

- [ ] **Step 2: Commit**

```bash
git add standalone_workspace/agents/async_scout.py
git commit -m "feat: replace weather mock with real OpenWeatherMap API in ScoutAgent"
```