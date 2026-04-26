# ZSA Phase 1: Millisecond Social News Listener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the `SocialNewsListener` from a slow, synchronous HTTP-fetching script into a lightning-fast, in-memory daemon that powers the Zero-Shot Cross-Market Arbitrage (ZSA) "fast-path" for millisecond news arbitrage.

**Architecture:** The listener will spin up a background thread upon initialization that continuously polls RSS feeds and caches the latest analyzed news (along with its xG impact) in memory. The MCP tool `fetch_arbitrage_news` will simply retrieve the cached value in O(1) time.

**Tech Stack:** Python, Threading, FastMCP, OpenAI API.

---

### Task 1: Refactor `SocialNewsListener` for Background Polling

**Files:**
- Modify: `core_system/skills/news_arbitrage/social_listener.py`

- [ ] **Step 1: Remove hardcoded mock and set up caching**
Modify `__init__` to read `NEWS_LISTENER_MOCK` from the environment. Initialize a thread-safe cache dictionary.

- [ ] **Step 2: Implement the background polling loop**
Create a `_background_poll` method that runs every 30 seconds, fetching RSS feeds and updating the cache.

- [ ] **Step 3: Start the thread on init**
Launch the background thread inside `__init__` using `threading.Thread(target=self._background_poll, daemon=True).start()`.

- [ ] **Step 4: Update `fetch_latest_news`**
Change this method to return the cached news instantly instead of making synchronous HTTP requests. Calculate the latency difference to prove the speedup.

### Task 2: Update MCP Server

**Files:**
- Modify: `core_system/skills/news_arbitrage/server.py`

- [ ] **Step 1: Remove `use_mock=True` hardcoding**
Change `listener = SocialNewsListener(use_mock=True)` to `listener = SocialNewsListener()` so it respects the environment variable.

- [ ] **Step 2: Add shutdown hooks (optional)**
Ensure the MCP server gracefully handles thread termination if needed.

### Task 3: End-to-End Verification

**Files:**
- Test: Manually or via script verify that `fetch_arbitrage_news` returns data in <5ms.

- [ ] **Step 1: Write a quick test script**
Create `test_zsa_latency.py` to call the listener and measure response time.

- [ ] **Step 2: Run the test**
Ensure latency is below 10ms.
