import apiClient from './apiClient';

// ── Types ──────────────────────────────────────────────────────────────────

export interface ResearchGap {
  id: string;
  title: string;
  description: string;
  type: string;
  impact: 'high' | 'medium' | 'low';
  confidence: number;
  entities?: string[];
  source?: string;
  evidence_count?: number;
}

export interface Contradiction {
  id: string;
  entity?: string;
  title: string;
  claim_a: string;
  claim_b: string;
  explanation: string;
  severity: 'high' | 'medium' | 'low';
  resolution_hint?: string;
  score: number;
  source?: string;
  doc_a?: string;
  doc_b?: string;
}

export interface Hypothesis {
  id: string;
  text: string;
  rationale: string;
  evidence?: string[];
  counter_evidence?: string[];
  methodology: string;
  validation_plan?: string;
  expected_impact: string;
  novelty?: string;
  feasibility?: string;
  falsifiability?: string;
  novelty_score?: number;
  feasibility_score?: number;
  falsifiability_score?: number;
  confidence: number;
  evidence_sources?: string[];
  source?: string;
  status: string;
  votes_up: number;
  votes_down: number;
}

export interface Trend {
  id?: string;
  title?: string;
  entity_name?: string;
  entity_key?: string;
  label?: string;
  description?: string;
  velocity?: string;
  trend_score?: number;
  document_count?: number;
  mention_count?: number;
  direction?: 'up' | 'down';
  delta?: number;
}

export interface DiscoverySummary {
  gaps_found: number;
  hypotheses_generated: number;
  contradictions_detected: number;
  trends_identified: number;
}

export interface StructuralQueryResult {
  answer: string;
  evidence: Array<{
    section_id: string;
    title: string;
    breadcrumb: string;
    text_preview: string;
    document_id: string;
    document_title: string;
  }>;
  reasoning_trace: string;
  navigation_path: string[];
  method: string;
}

// ── API Calls ─────────────────────────────────────────────────────────────

export const runFullDiscoveryAnalysis = async () => {
  const res = await apiClient.post('/discovery/analyze');
  return res.data;
};

export const getGraphGaps = async (limit = 15): Promise<{ gaps: ResearchGap[]; source: string }> => {
  const res = await apiClient.get(`/discovery/graph/gaps?limit=${limit}`);
  return res.data;
};

export const getGraphContradictions = async (
  entity?: string,
  limit = 10
): Promise<{ contradictions: Contradiction[]; source: string }> => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (entity) params.append('entity', entity);
  const res = await apiClient.get(`/discovery/graph/contradictions?${params}`);
  return res.data;
};

export const generateGraphHypotheses = async (): Promise<{
  hypotheses: Hypothesis[];
  count: number;
  source?: string;
}> => {
  const res = await apiClient.post('/discovery/graph/hypotheses');
  return res.data;
};

export const getResearchGaps = async (): Promise<ResearchGap[]> => {
  const res = await apiClient.get('/discovery/gaps');
  return res.data.gaps ?? [];
};

export const getHypotheses = async (): Promise<Hypothesis[]> => {
  const res = await apiClient.get('/discovery/hypotheses');
  return res.data.hypotheses ?? [];
};

export const getContradictions = async (): Promise<Contradiction[]> => {
  const res = await apiClient.get('/discovery/contradictions');
  return res.data.contradictions ?? [];
};

export const getTrends = async (): Promise<Trend[]> => {
  const res = await apiClient.get('/discovery/trends');
  return res.data.trends ?? [];
};

export const getDiscoverySummary = async (): Promise<DiscoverySummary> => {
  const res = await apiClient.get('/discovery/summary');
  return res.data;
};

export const voteOnHypothesis = async (
  id: string,
  direction: 'up' | 'down'
): Promise<{ votes_up: number; votes_down: number }> => {
  const res = await apiClient.post(`/discovery/hypotheses/${id}/vote`, { direction });
  return res.data;
};

export const structuralQuery = async (
  query: string,
  documentIds?: number[]
): Promise<StructuralQueryResult> => {
  const res = await apiClient.post('/discovery/structural-query', {
    query,
    document_ids: documentIds,
  });
  return res.data;
};

export const findBridgePath = async (
  concept1: string,
  concept2: string,
  maxDepth = 4
) => {
  const res = await apiClient.post('/discovery/path', {
    concept1,
    concept2,
    max_depth: maxDepth,
  });
  return res.data;
};
