from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional


EditionId = Literal["standalone", "openclaw"]


@dataclass(frozen=True)
class DirSpec:
    id: str
    purpose: str
    default_relpath: str
    env_var: Optional[str] = None
    resolver: Optional[str] = None


@dataclass(frozen=True)
class EntrypointSpec:
    id: str
    kind: str
    module: str
    callable: str
    invocation: str
    default_workflow: Optional[str] = None
    uses_dirs: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkflowSpec:
    id: str
    name: str
    steps: List[str]


@dataclass(frozen=True)
class EditionInventory:
    edition: EditionId
    workspace_relpath: str
    python_root_relpath: str
    dirs: List[DirSpec]
    entrypoints: List[EntrypointSpec]
    workflows: List[WorkflowSpec]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


INVENTORY = EditionInventory(
    edition="standalone",
    workspace_relpath="standalone_workspace",
    python_root_relpath="standalone_workspace",
    dirs=[
        DirSpec(
            id="data",
            purpose="runtime_data",
            default_relpath="standalone_workspace/data",
            env_var="STANDALONE_FOOTBALL_DATA_DIR",
            resolver="tools.paths.data_dir",
        ),
        DirSpec(
            id="datasets",
            purpose="datasets",
            default_relpath="standalone_workspace/datasets",
            env_var="STANDALONE_FOOTBALL_DATASETS_DIR",
            resolver="tools.paths.datasets_dir",
        ),
        DirSpec(id="reports", purpose="reports", default_relpath="standalone_workspace/reports"),
        DirSpec(id="snapshots", purpose="snapshots", default_relpath="standalone_workspace/snapshots"),
    ],
    entrypoints=[
        EntrypointSpec(
            id="mentor_cli",
            kind="cli",
            module="scripts.mentor_cli",
            callable="main",
            invocation="python3 standalone_workspace/scripts/mentor_cli.py",
            default_workflow="mentor_workflow",
            uses_dirs=["data"],
        ),
        EntrypointSpec(
            id="self_audit",
            kind="cli",
            module="scripts.self_audit_cli",
            callable="main",
            invocation="python3 standalone_workspace/scripts/self_audit_cli.py",
            default_workflow="self_audit",
            uses_dirs=["data"],
        ),
        EntrypointSpec(
            id="run_live_decision",
            kind="cli",
            module="run_live_decision",
            callable="main",
            invocation="python3 standalone_workspace/run_live_decision.py",
            default_workflow="syndicate_os_match",
            uses_dirs=["reports", "data"],
        ),
        EntrypointSpec(
            id="market_sentinel",
            kind="daemon",
            module="market_sentinel",
            callable="MarketSentinel.run_forever",
            invocation="python3 standalone_workspace/market_sentinel.py",
            default_workflow="market_sentinel_loop",
            uses_dirs=["snapshots", "reports", "data"],
        ),
    ],
    workflows=[
        WorkflowSpec(
            id="mentor_workflow",
            name="MentorWorkflow.run",
            steps=[
                "fetch_fixtures_normalized",
                "select_match",
                "retrieve_pre_match_memory",
                "fetch_odds_normalized",
                "odds_analyzer",
                "ticket_builder_validate",
                "optional_auto_trade_or_simulated_execution",
                "live_check",
                "settlement_post_match_review",
                "daily_report",
                "write_post_match_memory",
                "audit_trail",
            ],
        ),
        WorkflowSpec(
            id="syndicate_os_match",
            name="SyndicateOS.process_match + PublisherAgent.publish",
            steps=[
                "fetch_live_fixtures",
                "select_match",
                "syndicate_os_process_match",
                "publisher_generate_report",
            ],
        ),
        WorkflowSpec(
            id="market_sentinel_loop",
            name="MarketSentinel lifecycle loops",
            steps=[
                "pre_match_poll_and_filter",
                "mentor_workflow_run_one_cycle",
                "live_state_poll_and_force_run",
                "results_poll_and_force_run",
                "persist_snapshots_and_reports",
            ],
        ),
    ],
)
