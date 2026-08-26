"""Discovery agents for Eureka.

Exports are lazy to avoid importing the full retrieval and graph stacks when a
single extractor is needed during startup.
"""

from importlib import import_module

_EXPORTS = {
    "ClaimExtractor": "app.services.discovery.claim_extractor",
    "RelationExtractor": "app.services.discovery.relation_extractor",
    "ContradictionMiner": "app.services.discovery.contradiction_miner",
    "BridgeFinder": "app.services.discovery.bridge_discovery",
    "GapDetector": "app.services.discovery.gap_detector",
    "HypothesisGenerator": "app.services.discovery.hypothesis_generator",
    "HypothesisValidator": "app.services.discovery.hypothesis_validator",
    "ExperimentDesigner": "app.services.discovery.experiment_designer",
    "TrendRadar": "app.services.discovery.trend_radar",
    "ReportBuilder": "app.services.discovery.report_builder",
    "DiscoveryEngine": "app.services.discovery.engine",
    "score_hypothesis": "app.services.discovery.heuristic_priors",
    "rank_hypotheses": "app.services.discovery.heuristic_priors",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)
    module = import_module(_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
