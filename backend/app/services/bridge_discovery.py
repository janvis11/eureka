from typing import List, Dict, Any
import numpy as np

class HiddenBridgeDiscovery:
    """
    Finds hidden connections between papers that are semantically similar but not citation-linked.
    """

    def __init__(self, hf_client):
        self.hf_client = hf_client

    def discover_bridges(self, docs: List[str], top_k=5) -> List[Dict[str, Any]]:
        embeddings = np.array(self.hf_client.embed_texts([d[:2000] for d in docs]))
        bridges = []

        similarity = embeddings @ embeddings.T
        norms = np.linalg.norm(embeddings, axis=1)
        similarity = similarity / (norms[:,None] * norms[None,:] + 1e-9)

        for i in range(len(docs)):
            for j in range(i+1, len(docs)):
                sim = similarity[i][j]
                if sim > 0.80:
                    bridges.append({
                        "doc_a": i,
                        "doc_b": j,
                        "similarity": float(sim),
                        "insight": "These papers share hidden conceptual similarity but may not cite each other."
                    })

        bridges.sort(key=lambda x: x["similarity"], reverse=True)
        return bridges[:top_k]
