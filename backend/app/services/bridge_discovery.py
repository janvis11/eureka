from typing import List, Dict, Any
import numpy as np
import asyncio

from app.services.model_gateway.base import EmbeddingRequest


class HiddenBridgeDiscovery:
    """
    Finds hidden connections between papers that are semantically similar but not citation-linked.
    """

    def __init__(self, gateway):
        self.gateway = gateway

    async def discover_bridges(self, docs: List[str], top_k=5) -> List[Dict[str, Any]]:
        result = await self.gateway.embed(
            EmbeddingRequest(texts=[d[:2000] for d in docs], purpose="document")
        )
        embeddings = np.array(result.embeddings)
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
