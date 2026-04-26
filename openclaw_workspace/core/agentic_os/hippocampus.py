import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from tools.paths import knowledge_base_dir
except ImportError:
    knowledge_base_dir = lambda *args: Path(__file__).resolve().parent.parent.parent / "workspace" / "orchestrator" / "knowledge_base"


_DEFAULT_MEMORY_DIR = Path(knowledge_base_dir("memory_core"))


class HippocampusMemory:
    """
    2026 Agentic OS - 海马体 (Continuous Long-Term Memory)
    负责多级记忆管理 (类 MemGPT/Zep 架构)，将短期快照压缩提炼为长期真理。
    """
    def __init__(self, memory_dir=None, event_bus=None, chroma_path: Optional[str] = None):
        self.memory_dir = Path(memory_dir).expanduser() if memory_dir else _DEFAULT_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.working_memory = [] # 当前处理上下文 (RAM)
        self.episodic_memory_file = self.memory_dir / "episodic.json" # 情节记忆 (日记)
        self.semantic_memory_file = self.memory_dir / "semantic_truth.json" # 语义记忆 (提炼的规律)

        # ChromaDB for semantic search
        self.chroma_path = chroma_path or str(self.memory_dir / "chroma_db")
        self._chroma_client = None
        self._chroma_collection = None

        # EventBus integration
        self._event_bus = event_bus
        if self._event_bus is None:
            try:
                from core.event_bus import EventBus as _EB
                self._event_bus = _EB()
            except ImportError:
                pass
        if self._event_bus is not None:
            # subscribe is async, schedule it safely
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._event_bus.subscribe("workflow.complete", self.on_workflow_complete))
            except RuntimeError:
                pass

        self._init_memory_files()
        self._init_chroma()

    def _init_chroma(self) -> None:
        """Initialize ChromaDB for semantic memory storage"""
        try:
            import chromadb
            os.makedirs(self.chroma_path, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=self.chroma_path)
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="semantic_lessons",
                metadata={"description": "Extracted lessons from workflow outcomes"}
            )
            print(f"   [Memory] 🗄️ ChromaDB initialized at {self.chroma_path}")
        except ImportError:
            print("   [Memory] ⚠️ ChromaDB not available, falling back to JSON storage")
        except Exception as e:
            print(f"   [Memory] ⚠️ ChromaDB init failed: {e}")

    def on_workflow_complete(self, data: Dict[str, Any]) -> None:
        """收到 workflow 完成事件时，提取教训存入记忆"""
        pnl = data.get("pnl", 0)
        match_id = data.get("match_id") or data.get("selection")
        workflow = data.get("workflow", "unknown")
        league = data.get("league", "unknown")

        context = {
            "workflow": workflow,
            "league": league,
            "selection": data.get("selection"),
        }

        # Record episode
        self.record_episode(
            match_id=match_id or f"{workflow}_{time.time()}",
            action=data.get("selection") or "unknown",
            pnl=pnl,
            context_snapshot=context,
        )

        # If loss, try to extract lesson via LLM
        if pnl < 0:
            self._extract_loss_lesson(data)

    def _init_memory_files(self):
        if not self.episodic_memory_file.exists():
            with open(self.episodic_memory_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        if not self.semantic_memory_file.exists():
            with open(self.semantic_memory_file, "w", encoding="utf-8") as f:
                json.dump({"truths": [], "risk_tolerance": 0.05}, f)

    def record_episode(self, match_id, action, pnl, context_snapshot):
        """记录每一次交易的心路历程 (盈亏、环境特征)"""
        episode = {
            "timestamp": time.time(),
            "match": match_id,
            "action": action,
            "PnL": pnl, # 真实盈亏反馈 (Profit and Loss)
            "context": context_snapshot
        }
        
        with open(self.episodic_memory_file, "r+", encoding="utf-8") as f:
            episodes = json.load(f)
            episodes.append(episode)
            f.seek(0)
            json.dump(episodes[-1000:], f, indent=2) # 滚动保留最近 1000 条记忆
            f.truncate()
            
        print(f"   [Memory] 🧠 痛觉/快感已记录入海马体情节库 (Match: {match_id}, PnL: {pnl})")

    def sleep_and_consolidate(self, pnl_data: Optional[List[Dict[str, Any]]] = None):
        """
        夜间休眠模式：主动归纳提炼 (Semantic Consolidation)
        将过去一天的亏损日志，提炼成不可违背的"语义真理"。
        支持真实 PnL 数据分析，写入 ChromaDB。
        """
        print("   [Memory] 🌙 进入深度睡眠记忆重组模式 (Memory Consolidation)...")

        # Use provided data or read from file
        if pnl_data is None:
            with open(self.episodic_memory_file, "r", encoding="utf-8") as f:
                episodes = json.load(f)
        else:
            episodes = pnl_data

        losses = [e for e in episodes if isinstance(e, dict) and e.get("PnL", 0) < 0]

        if len(losses) >= 1:
            # Analyze failure patterns from real data
            failure_patterns = self._analyze_failure_patterns(losses)

            # Try LLM extraction if API key available
            api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
            if api_key and failure_patterns:
                new_truth = self._llm_extract_lesson(failure_patterns, losses)
            else:
                # Fallback to pattern-based rule
                new_truth = failure_patterns[0] if failure_patterns else None

            if new_truth:
                # Write to ChromaDB
                self._write_to_chroma(new_truth, losses)

                # Update semantic JSON
                with open(self.semantic_memory_file, "r+", encoding="utf-8") as f:
                    semantic = json.load(f)
                    if new_truth not in semantic["truths"]:
                        semantic["truths"].append(new_truth)
                        semantic["risk_tolerance"] = max(0.01, semantic.get("risk_tolerance", 0.05) - 0.01)
                        f.seek(0)
                        json.dump(semantic, f, indent=2, ensure_ascii=False)
                        f.truncate()
                print(f"   [Memory] 💡 顿悟！从亏损中提取出新的语义真理并固化: {new_truth[:60]}...")
                print(f"   [Memory] 🛡️ 系统的风险容忍度已自主下调。")
        else:
            print("   [Memory] 💤 记忆回放完毕，今日无严重创伤需要重塑认知。")

    def _analyze_failure_patterns(self, losses: List[Dict[str, Any]]) -> List[str]:
        """分析亏损模式，提取共性规律"""
        patterns = []
        league_losses = {}
        selection_losses = {}

        for loss in losses:
            ctx = loss.get("context", {}) if isinstance(loss, dict) else {}
            league = ctx.get("league", "unknown") if isinstance(ctx, dict) else "unknown"
            action = loss.get("action", "unknown")

            if league != "unknown":
                league_losses[league] = league_losses.get(league, 0) + 1
            if action != "unknown":
                selection_losses[action] = selection_losses.get(action, 0) + 1

        # Generate pattern rules
        for league, count in league_losses.items():
            if count >= 2:
                patterns.append(f"RULE_UPDATE: {league}联赛近期亏损{count}次，需谨慎对待。")

        for selection, count in selection_losses.items():
            if count >= 2:
                patterns.append(f"RULE_UPDATE: 选择'{selection}'近期亏损{count}次，建议回避。")

        return patterns

    def _llm_extract_lesson(self, patterns: List[str], losses: List[Dict[str, Any]]) -> Optional[str]:
        """调用 LLM 从亏损数据中提取教训"""
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            return patterns[0] if patterns else None

        try:
            import openai
            
            client_kwargs = {"api_key": api_key}
            base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE")
            if base_url:
                client_kwargs["base_url"] = base_url
                
            client = openai.OpenAI(**client_kwargs)

            loss_summary = "\n".join([
                f"- Match: {l.get('match', 'N/A')}, PnL: {l.get('PnL', 0)}, Context: {l.get('context', {})}"
                for l in losses[:5]
            ])

            model_name = os.environ.get("MODEL_NAME", "gpt-4o-mini")

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "你是足球博彩分析专家。从以下亏损记录中提取一条简短规则（50字内），说明失败原因。不要废话，直接给规则。"},
                    {"role": "user", "content": f"亏损记录:\n{loss_summary}\n\npatterns: {patterns}"}
                ],
                max_tokens=100,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"   [Memory] ⚠️ LLM extraction failed: {e}")
            return patterns[0] if patterns else None

    def _write_to_chroma(self, lesson: str, related_losses: List[Dict[str, Any]]) -> None:
        """将教训写入 ChromaDB"""
        if self._chroma_collection is None:
            return

        try:
            match_ids = [str(l.get("match", f"loss_{i}")) for i, l in enumerate(related_losses[:5])]
            contexts = [json.dumps(l.get("context", {}), ensure_ascii=False) for l in related_losses[:5]]

            self._chroma_collection.add(
                documents=[lesson] * len(match_ids),
                metadatas=[{"context": c} for c in contexts],
                ids=match_ids,
            )
            print(f"   [Memory] 💾 教训已存入 ChromaDB ({len(match_ids)} 条关联记录)")
        except Exception as e:
            print(f"   [Memory] ⚠️ ChromaDB write failed: {e}")

    def _extract_loss_lesson(self, event_data: Dict[str, Any]) -> None:
        """从单个亏损事件提取教训（被 on_workflow_complete 调用）"""
        pnl = event_data.get("pnl", 0)
        if pnl >= 0:
            return

        league = event_data.get("league", "unknown")
        selection = event_data.get("selection")
        workflow = event_data.get("workflow", "unknown")

        lesson = f"LOSS: {workflow} workflow 在 {league} 的 {selection} 选择中亏损 {pnl}。"
        self._write_to_chroma(lesson, [event_data])

if __name__ == "__main__":
    hippo = HippocampusMemory()
    # 模拟三次连续的同类型亏损
    for i in range(3):
        hippo.record_episode(f"EPL_Match_{i}", "BUY_HOME", -100, {"asian_handicap": -0.25, "betfair_vol": 0.85})
    hippo.sleep_and_consolidate()
