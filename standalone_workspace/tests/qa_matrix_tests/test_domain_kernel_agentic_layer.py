import asyncio

from core.domain_kernel import DomainKernel


def test_domain_kernel_router_contract_ok():
    payload = {
        "status": "success",
        "decision": {"action": "IGNORE", "reason": "low value"},
        "confidence": 0.9,
        "data_source": "router:test",
    }
    out = DomainKernel.attach("router", payload)
    assert out["domain_kernel"]["ok"] is True
    assert out["role"] == "router"
    assert out["schema_version"] == "1.0"


def test_domain_kernel_risk_contract_ok():
    payload = {
        "status": "success",
        "recommendation": "approve",
        "checks": {"stake_ratio": {"passed": True}},
        "risk_score": 0.1,
        "confidence": 0.8,
        "data_source": "risk:test",
    }
    out = DomainKernel.attach("risk-manager", payload)
    assert out["domain_kernel"]["ok"] is True
    assert out["role"] == "risk-manager"


def test_router_agent_offline_is_deterministic(monkeypatch):
    from agents.router_agent import RouterAgent

    monkeypatch.setenv("ROUTER_OFFLINE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key-for-test")

    agent = RouterAgent()

    res = asyncio.run(
        agent.evaluate_match_value({"home": "Man City", "away": "League Two Team", "odds": [1.05, 15.0, 34.0]})
    )

    assert res["decision"]["action"] == "IGNORE"
    assert res["domain_kernel"]["ok"] is True

