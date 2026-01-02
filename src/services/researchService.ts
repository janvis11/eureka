import apiClient from './apiClient';
import {
  ChatMessage,
  DiscoveryInsight,
  GraphPathRequest,
  GraphStats,
  Hypothesis,
  ResearchGap,
  TrendMetric
} from '../types/api';
import { mockChatResponse, mockGaps, mockGraphStats, mockHypotheses, mockInsights, mockTrends } from '../data/mockData';

type BackendGapsResponse = {
  gaps: Array<{
    id: string;
    title: string;
    description: string;
    concept1: string;
    concept2: string;
    impact: string;
    confidence: number;
    potential_path?: string[];
  }>;
};

type BackendHypothesesResponse = {
  hypotheses: Array<{
    id: number;
    text: string;
    confidence: number;
    votes_up: number;
    votes_down: number;
    status: Hypothesis['status'];
    entities: string[];
    rationale?: string | null;
    methodology?: string | null;
    expected_impact?: string | null;
  }>;
};

const toSlug = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

export const submitChatQuery = async (prompt: string, documentId?: number): Promise<ChatMessage> => {
  try {
    // Try the new backend endpoint first
    const { data } = await apiClient.post('/queries/ask', { 
      question: prompt,
      document_id: documentId ?? 1,
      top_k: 5
    });

    const citations = Array.isArray(data.sources)
      ? data.sources.map((source: any, index: number) => ({
          title: source.title ?? source.document_id ?? `Source ${index + 1}`,
          url: '#'
        }))
      : undefined;

    return {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: data.answer ?? mockChatResponse.content,
      citations,
      createdAt: new Date().toISOString()
    };
  } catch (error) {
    // Fallback to mock data if API fails
    console.warn('Chat API unavailable, using mock response:', error);
    return { ...mockChatResponse, content: `${mockChatResponse.content}\n\n(Mocked response while API is offline.)` };
  }
};

export const fetchResearchGaps = async (): Promise<ResearchGap[]> => {
  try {
    const { data } = await apiClient.get<BackendGapsResponse>('/discovery/gaps');
    const gaps = Array.isArray(data.gaps) ? data.gaps : [];
    if (gaps.length === 0) return mockGaps;
    return gaps.map((gap) => ({
      id: gap.id ?? toSlug(gap.title),
      title: gap.title,
      description: gap.description,
      concept1: gap.concept1,
      concept2: gap.concept2,
      impact: (gap.impact ?? 'medium').toLowerCase() as ResearchGap['impact'],
      confidence: Number(gap.confidence ?? 0),
      potentialPath: gap.potential_path ?? []
    }));
  } catch {
    return mockGaps;
  }
};

export const fetchHypotheses = async (): Promise<Hypothesis[]> => {
  try {
    const { data } = await apiClient.get<BackendHypothesesResponse>('/discovery/hypotheses');
    const hypotheses = Array.isArray(data.hypotheses) ? data.hypotheses : [];
    if (hypotheses.length === 0) return mockHypotheses;

    return hypotheses.map((hypothesis) => ({
      id: hypothesis.id.toString(),
      text: hypothesis.text,
      confidence: hypothesis.confidence ?? 0,
      votesUp: hypothesis.votes_up ?? 0,
      votesDown: hypothesis.votes_down ?? 0,
      status: hypothesis.status ?? 'proposed',
      entities: hypothesis.entities ?? [],
      rationale: hypothesis.rationale ?? undefined,
      methodology: hypothesis.methodology ?? undefined,
      expectedImpact: hypothesis.expected_impact ?? undefined
    }));
  } catch {
    return mockHypotheses;
  }
};

export const voteOnHypothesis = async (id: string, direction: 'up' | 'down'): Promise<void> => {
  try {
    await apiClient.post(`/discovery/hypotheses/${id}/vote`, { direction });
  } catch {
    if (import.meta.env.DEV) {
      console.warn('Vote endpoint unavailable, running offline.');
    }
  }
};

export const fetchGraphStats = async (): Promise<GraphStats> => {
  try {
    const { data } = await apiClient.get('/discovery/graph-stats');
    return {
      nodes: data.nodes ?? 0,
      edges: data.edges ?? 0,
      density: data.density ?? 0,
      communities: data.communities ?? 0,
      topEntities: data.top_entities ?? [],
      breakdown: data.breakdown
    };
  } catch {
    return mockGraphStats;
  }
};

export const fetchGraphPath = async (payload: GraphPathRequest): Promise<string[]> => {
  try {
    const { data } = await apiClient.post('/discovery/path', {
      concept1: payload.source,
      concept2: payload.target,
      max_depth: payload.maxDepth ?? 4
    });
    return data.paths?.[0]?.nodes ?? data.path ?? [];
  } catch {
    return [];
  }
};

export const fetchDiscoveryInsights = async (): Promise<DiscoveryInsight[]> => {
  try {
    const { data } = await apiClient.get('/discovery/contradictions');
    const insights = Array.isArray(data.contradictions) ? data.contradictions : [];
    if (insights.length === 0) return mockInsights;
    return insights.map((item: any) => ({
      id: toSlug(item.title),
      type: 'contradiction',
      title: item.title,
      detail: item.description,
      impact: 'medium'
    }));
  } catch {
    return mockInsights;
  }
};

export const fetchTrendMetrics = async (): Promise<TrendMetric[]> => {
  try {
    const { data } = await apiClient.get('/discovery/trends');
    const trends = Array.isArray(data.trends) ? data.trends : [];
    if (trends.length === 0) return mockTrends;
    return trends.map((trend: any) => {
      const numericDelta = Number((trend.growth ?? '0').toString().replace(/[+%]/g, ''));
      return {
        id: toSlug(trend.title),
        label: trend.title,
        delta: Number.isNaN(numericDelta) ? 0 : numericDelta,
        direction: numericDelta >= 0 ? 'up' : 'down',
        velocity: trend.velocity
      };
    });
  } catch {
    return mockTrends;
  }
};
