import apiClient from './apiClient';
import {
  ChatMessage,
  DiscoveryInsight,
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
