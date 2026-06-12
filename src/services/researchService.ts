import apiClient from './apiClient';
import {
  ChatMessage,
  DiscoveryInsight,
  GraphEdge,
  GraphNode,
  GraphOverview,
  GraphPathRequest,
  GraphStats,
  Hypothesis,
  ResearchGap,
  TrendMetric,
} from '../types/api';

const toSlug = (value: string) =>
  value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

const normalizeImpact = (value: unknown): ResearchGap['impact'] => {
  const text = String(value ?? 'medium').toLowerCase();
  if (text === 'high' || text === 'low') return text;
  return 'medium';
};

export const submitChatQuery = async (prompt: string, documentId?: number): Promise<ChatMessage> => {
  const payload: Record<string, unknown> = {
    question: prompt,
    top_k: 5,
    use_structural: true,
  };
  if (documentId !== undefined) payload.document_id = documentId;

  const { data } = await apiClient.post('/queries/ask', payload);

  const citations = Array.isArray(data.sources)
    ? data.sources.map((source: any, index: number) => ({
        title: source.title ?? source.breadcrumb ?? source.document_id ?? `Source ${index + 1}`,
        url: '#',
      }))
    : undefined;

  return {
    id: crypto.randomUUID(),
    role: 'assistant',
    content: data.answer ?? 'No answer was returned by the research engine.',
    citations,
    createdAt: new Date().toISOString(),
  };
};

export const fetchResearchGaps = async (): Promise<ResearchGap[]> => {
  const { data } = await apiClient.get('/discovery/graph/gaps?limit=15');
  const gaps = Array.isArray(data.gaps) ? data.gaps : [];

  return gaps.map((gap: any, index: number) => {
    const entities = Array.isArray(gap.entities) ? gap.entities : [gap.concept1, gap.concept2].filter(Boolean);
    return {
      id: String(gap.id ?? toSlug(gap.title ?? `gap-${index}`)),
      title: gap.title ?? `Research gap ${index + 1}`,
      description: gap.description ?? '',
      concept1: entities[0],
      concept2: entities[1],
      impact: normalizeImpact(gap.impact),
      confidence: Number(gap.confidence ?? 0),
      potentialPath: gap.potential_path ?? [],
      evidenceCount: gap.evidence_count,
      source: data.source ?? gap.source,
    };
  });
};

export const fetchHypotheses = async (): Promise<Hypothesis[]> => {
  const { data } = await apiClient.get('/discovery/hypotheses');
  const hypotheses = Array.isArray(data.hypotheses) ? data.hypotheses : [];

  return hypotheses.map((hypothesis: any, index: number) => ({
    id: String(hypothesis.id ?? `hyp-${index}`),
    text: hypothesis.text ?? hypothesis.hypothesis ?? '',
    confidence: Number(hypothesis.confidence ?? 0),
    votesUp: Number(hypothesis.votes_up ?? 0),
    votesDown: Number(hypothesis.votes_down ?? 0),
    status: hypothesis.status ?? 'proposed',
    entities: hypothesis.entities ?? hypothesis.evidence_sources ?? [],
    rationale: hypothesis.rationale ?? undefined,
    methodology: hypothesis.methodology ?? undefined,
    expectedImpact: hypothesis.expected_impact ?? undefined,
    evidence: hypothesis.evidence ?? hypothesis.evidence_sources ?? [],
    counterEvidence: hypothesis.counter_evidence ?? [],
    novelty: hypothesis.novelty ?? undefined,
    feasibility: hypothesis.feasibility ?? undefined,
    falsifiability: hypothesis.falsifiability ?? undefined,
    validationPlan: hypothesis.validation_plan ?? undefined,
    noveltyScore: hypothesis.novelty_score ?? undefined,
    feasibilityScore: hypothesis.feasibility_score ?? undefined,
    falsifiabilityScore: hypothesis.falsifiability_score ?? undefined,
  }));
};

export const generateHypothesesFromGraph = async (): Promise<Hypothesis[]> => {
  const { data } = await apiClient.post('/discovery/graph/hypotheses');
  const hypotheses = Array.isArray(data.hypotheses) ? data.hypotheses : [];

  return hypotheses.map((hypothesis: any, index: number) => ({
    id: String(hypothesis.id ?? `hyp-${index}`),
    text: hypothesis.text ?? hypothesis.hypothesis ?? '',
    confidence: Number(hypothesis.confidence ?? 0),
    votesUp: Number(hypothesis.votes_up ?? 0),
    votesDown: Number(hypothesis.votes_down ?? 0),
    status: hypothesis.status ?? 'proposed',
    entities: hypothesis.evidence_sources ?? [],
    rationale: hypothesis.rationale ?? undefined,
    methodology: hypothesis.methodology ?? undefined,
    expectedImpact: hypothesis.expected_impact ?? undefined,
    evidence: hypothesis.evidence ?? hypothesis.evidence_sources ?? [],
    counterEvidence: hypothesis.counter_evidence ?? [],
    novelty: hypothesis.novelty ?? undefined,
    feasibility: hypothesis.feasibility ?? undefined,
    falsifiability: hypothesis.falsifiability ?? undefined,
    validationPlan: hypothesis.validation_plan ?? undefined,
    noveltyScore: hypothesis.novelty_score ?? undefined,
    feasibilityScore: hypothesis.feasibility_score ?? undefined,
    falsifiabilityScore: hypothesis.falsifiability_score ?? undefined,
  }));
};

export const voteOnHypothesis = async (id: string, direction: 'up' | 'down'): Promise<void> => {
  await apiClient.post(`/discovery/hypotheses/${id}/vote`, { direction });
};

export const fetchGraphStats = async (): Promise<GraphStats> => {
  const { data } = await apiClient.get('/discovery/graph-stats');
  return {
    nodes: data.nodes ?? 0,
    edges: data.edges ?? 0,
    density: data.density ?? 0,
    communities: data.communities ?? 0,
    topEntities: data.top_entities ?? [],
    breakdown: data.breakdown,
  };
};

export const fetchGraphOverview = async (options?: {
  limit?: number;
  relationshipTypes?: string[];
}): Promise<GraphOverview> => {
  const params = new URLSearchParams();
  params.set('limit', String(options?.limit ?? 25));
  if (options?.relationshipTypes?.length) {
    params.set('relationship_types', options.relationshipTypes.join(','));
  }

  const { data } = await apiClient.get(`/graph/overview?${params.toString()}`);
  const nodes = Array.isArray(data.nodes) ? data.nodes : [];
  const edges = Array.isArray(data.edges) ? data.edges : [];

  return {
    nodes: nodes.map((node: any): GraphNode => ({
      id: String(node.id ?? ''),
      label: String(node.label ?? node.name ?? node.title ?? node.key ?? node.id ?? 'Node'),
      kind: String(node.kind ?? node.labels?.[0] ?? 'Node'),
      labels: Array.isArray(node.labels) ? node.labels.map(String) : [],
      key: node.key,
      name: node.name,
      title: node.title,
      text: node.text,
      sourceType: node.source_type,
      chunkIndex: node.chunk_index === undefined ? undefined : Number(node.chunk_index),
      tokenCount: node.token_count === undefined ? undefined : Number(node.token_count),
      claimType: node.claim_type,
      polarity: node.polarity,
      confidence: node.confidence === undefined ? undefined : Number(node.confidence),
    })).filter((node: GraphNode) => node.id),
    edges: edges.map((edge: any): GraphEdge => ({
      id: String(edge.id ?? `${edge.source}-${edge.type}-${edge.target}`),
      source: String(edge.source ?? ''),
      target: String(edge.target ?? ''),
      type: String(edge.type ?? 'RELATED'),
      predicate: edge.predicate,
      confidence: edge.confidence === undefined ? undefined : Number(edge.confidence),
      evidence: edge.evidence,
      chunkId: edge.chunk_id,
    })).filter((edge: GraphEdge) => edge.source && edge.target),
    relationshipTypes: Array.isArray(data.relationship_types) ? data.relationship_types.map(String) : [],
    limit: Number(data.limit ?? options?.limit ?? 25),
  };
};

export const fetchGraphPath = async (payload: GraphPathRequest): Promise<string[]> => {
  const { data } = await apiClient.post('/discovery/path', {
    concept1: payload.source,
    concept2: payload.target,
    max_depth: payload.maxDepth ?? 4,
  });
  return data.paths?.[0]?.nodes ?? data.path ?? [];
};

export const fetchDiscoveryInsights = async (): Promise<DiscoveryInsight[]> => {
  const { data } = await apiClient.get('/discovery/graph/contradictions?limit=10');
  const insights = Array.isArray(data.contradictions) ? data.contradictions : [];

  return insights.map((item: any, index: number) => ({
    id: String(item.id ?? toSlug(item.title ?? `insight-${index}`)),
    type: 'contradiction',
    title: item.title ?? 'Contradiction detected',
    detail: item.explanation ?? item.description ?? '',
    impact: normalizeImpact(item.severity ?? item.impact),
  }));
};

export const fetchTrendMetrics = async (): Promise<TrendMetric[]> => {
  const { data } = await apiClient.get('/discovery/trends');
  const trends = Array.isArray(data.trends) ? data.trends : [];

  return trends.map((trend: any, index: number) => {
    const score = Number(trend.trend_score ?? trend.delta ?? 0);
    const delta = score <= 1 ? Math.round(score * 100) : score;
    return {
      id: String(trend.id ?? trend.entity_key ?? toSlug(trend.title ?? `trend-${index}`)),
      label: trend.title ?? trend.entity_name ?? trend.label ?? `Trend ${index + 1}`,
      delta,
      direction: delta >= 0 ? 'up' : 'down',
      velocity: trend.velocity,
    };
  });
};
