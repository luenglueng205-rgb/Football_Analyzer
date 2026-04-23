# AI-Native Cognitive Upgrade: League Persona & 16-Market Strategist

## 1. The Core Problem
For 10+ rounds, the system has been heavily focused on "technical engineering" (routers, buses, daemons, MCPs) while neglecting the true power of an AI-Native system: **Cognitive Depth**.
The AI was treating a Premier League match the same as a J2 League match. It was treating a "Total Goals" bet the same as a "Let-Ball (Handicap)" bet. It was merely fetching numbers and running static Python scripts. 

## 2. The AI-Native Solution
We will tear down the static reasoning and inject **Domain Cognitive Frameworks** directly into the LLM's brain, allowing it to autonomously synthesize multi-modal intelligence, recognize league patterns, and strategize across the 16 distinct lottery markets.

### 2.1 League Persona & Context Engine (联赛特征识别大脑)
Instead of treating all matches as equal mathematical variables, the AI will first identify the **League Persona**.
- E.g., "This is Serie A: Historically low-variance, tactical, high rate of Under 2.5 goals. The underdog often parks the bus."
- E.g., "This is Eredivisie: High variance, open play, high goal counts."
- **Implementation**: We will create a `league_profiler.py` tool that the LLM *must* call to fetch the League Persona, referee leniency, and historical variance before making any prediction.

### 2.2 16-Market AI Strategist (16种玩法策略师)
The LLM must stop defaulting to "Win-Draw-Loss" (SPF). It must deeply analyze the match's variance and map it to the **safest and most profitable of the 16 play types**.
- If a match is highly unpredictable (e.g., Cup matches), the AI should recognize that SPF is a trap, and instead pivot to "Total Goals (2-3)" or "Both Teams to Score".
- **Implementation**: We will inject a `Cognitive Strategy Prompt` that forces the LLM to output a "Play Type Allocation Matrix" (e.g., 60% confidence in Let-Ball, 80% in Total Goals). 

### 2.3 Dynamic Intelligence Gathering (多模态/全网动态感知)
The AI should act like a real analyst: scouring the web for breaking news, injury reports, and weather conditions.
- **Implementation**: We will enhance the `multisource_fetcher` with a `news_sentiment_analyzer` tool. The LLM will autonomously search for "Team A injury news" and incorporate the sentiment into its Poisson distribution adjustments.

### 2.4 Virtual Ticket Simulator (模拟选号格式，类似500彩票网)
The user explicitly stated: "No need for physical ticket output, just format it like 500.com's simulated ticket selection."
- **Implementation**: The output formatter will be rewritten to generate a clean, web-like markdown structure that mimics a 500.com bet slip, showing the Match, Play Type, Selection, Odds, and Expected Return in a visually appealing table.

## 3. Architecture Changes
1. **`agents/ai_native_core.py`**: Rewrite the `system_prompt` and `process` loop to enforce the "Cognitive Framework" (League Profile -> Intelligence Gather -> 16-Market Matrix -> Simulated Ticket).
2. **`tools/league_profiler.py`**: A new tool providing League Personas.
3. **`tools/intelligence_gatherer.py`**: A new tool wrapping `ddgs` specifically for fetching breaking news and injuries.
4. **`tools/simulated_ticket.py`**: A new formatter tool that outputs the 500.com style bet slip.

## 4. Execution Plan
We will proceed to implement these changes, completely shifting the system from "Python Scripts" to "AI-Native Reasoning".
