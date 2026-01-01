export type ChatRole = 'user' | 'assistant';

export type Citation = {
  title: string;
  url: string;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  citations?: Citation[];
  createdAt: string;
};

export type ResearchGap = {
  id: string;
  title: string;
  description: string;
  concept1: string;
  concept2: string;
  impact: 'low' | 'medium' | 'high';
  confidence: number;
  potentialPath?: string[];
};

export type Hypothesis = {
  id: string;
  text: string;
  rationale?: string;
  methodology?: string;
  expectedImpact?: string;
  confidence: number;
  votesUp: number;
  votesDown: number;
  status: 'proposed' | 'claimed' | 'validated' | 'rejected';
  entities: string[];
};

export type GraphStats = {
  nodes: number;
  edges: number;
  density: number;
  communities: number;
  topEntities: string[];
  breakdown?: {
    papers: number;
    concepts: number;
    methods: number;
  };
};

export type GraphPathRequest = {
  source: string;
  target: string;
  maxDepth?: number;
};

export type DiscoveryInsight = {
  id: string;
  type: 'gap' | 'trend' | 'contradiction';
  title: string;
  detail: string;
  impact: 'low' | 'medium' | 'high';
};

export type TrendMetric = {
  id: string;
  label: string;
  delta: number;
  direction: 'up' | 'down';
  velocity?: string;
};

export type ApiState<T> = {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

