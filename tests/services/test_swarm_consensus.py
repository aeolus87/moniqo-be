from app.modules.flows import service as flow_service


def test_swarm_majority_vote_confidence_tiebreak():
    results = [
        {"action": "buy", "confidence": 0.6, "reasoning": "A"},
        {"action": "sell", "confidence": 0.9, "reasoning": "B"},
        {"action": "buy", "confidence": 0.4, "reasoning": "C"},
    ]

    aggregated = flow_service._aggregate_swarm_results(results)

    assert aggregated["action"] == "buy"
    assert aggregated["agreement"] == 66
    assert aggregated["is_unanimous"] is False
