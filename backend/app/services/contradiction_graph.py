from typing import List, Dict, Any, Tuple
import networkx as nx
from transformers import pipeline

class ContradictionGraphBuilder:
    def __init__(self, model_name="roberta-large-mnli"):
        self.nli = pipeline("text-classification", model=model_name)

    def compare_claims(self, claim1: str, claim2: str) -> Tuple[str, float]:
        """Returns label + score"""
        result = self.nli({"text": claim1, "text_pair": claim2})[0]
        label = result["label"]  # entailment / contradiction / neutral
        score = float(result["score"])
        return label, score

    def build_graph(self, claims: List[str]) -> Dict[str, Any]:
        G = nx.Graph()
        for i, c in enumerate(claims):
            G.add_node(i, claim=c)

        for i in range(len(claims)):
            for j in range(i+1, len(claims)):
                label, score = self.compare_claims(claims[i], claims[j])
                if label == "CONTRADICTION" and score > 0.75:
                    G.add_edge(i, j, label="contradiction", weight=score)

        return {
            "nodes": [{"id": n, "claim": G.nodes[n]["claim"]} for n in G.nodes],
            "edges": [{"source": u, "target": v, "weight": d["weight"]} for u,v,d in G.edges(data=True)]
        }
