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
  contextDocumentId?: number;
  contextTitle?: string;
  contextMode?: 'selected' | 'matched' | 'corpus';
};

export type ResearchGap = {
  id: string;
  title: string;
  description: string;
  concept1?: string;
  concept2?: string;
  impact: 'low' | 'medium' | 'high';
  confidence: number;
  potentialPath?: string[];
  evidenceCount?: number;
  source?: string;
};

export type Hypothesis = {
  id: string;
  text: string;
  rationale?: string;
  methodology?: string;
  expectedImpact?: string;
  evidence?: string[];
  counterEvidence?: string[];
  novelty?: string;
  feasibility?: string;
  falsifiability?: string;
  validationPlan?: string;
  noveltyScore?: number;
  feasibilityScore?: number;
  falsifiabilityScore?: number;
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
    chunks?: number;
    concepts: number;
    methods?: number;
    claims?: number;
    hypotheses?: number;
  };
};

export type GraphNode = {
  id: string;
  label: string;
  kind: string;
  labels: string[];
  key?: string;
  name?: string;
  title?: string;
  text?: string;
  sourceType?: string;
  chunkIndex?: number;
  tokenCount?: number;
  claimType?: string;
  polarity?: string;
  confidence?: number;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  predicate?: string;
  confidence?: number;
  evidence?: string;
  chunkId?: string;
};

export type GraphOverview = {
  nodes: GraphNode[];
  edges: GraphEdge[];
  relationshipTypes: string[];
  limit: number;
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
