# Services module
self.agent_orchestrator = ScienceAgentOrchestrator(self.hf_client, self.keyword_extractor)
self.contradiction_graph_builder = ContradictionGraphBuilder()
self.bridge_discovery = HiddenBridgeDiscovery(self.hf_client)
