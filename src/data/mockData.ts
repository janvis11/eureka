import { ChatMessage, DiscoveryInsight, GraphStats, Hypothesis, ResearchGap, TrendMetric } from '../types/api';

export const mockChatResponse: ChatMessage = {
  id: 'mock-response',
  role: 'assistant',
  content:
    'Based on 1.2M indexed papers, the most promising approach combines self-supervised representation learning with domain-specific ontologies to reduce hallucinations in biomedical RAG systems.',
  citations: [
    { title: 'Self-Supervised Biomedical RAG', url: 'https://arxiv.org/abs/2402.01234' },
    { title: 'Ontology-Grounded Generation', url: 'https://arxiv.org/abs/2311.04567' }
  ],
  createdAt: new Date().toISOString()
};

export const mockGaps: ResearchGap[] = [
  {
    id: 'gap-1',
    title: 'Multimodal Benchmarks',
    description: 'Only 4% of biomedical benchmarks evaluate joint text+graph reasoning for discovery workflows.',
    concept1: 'Biomedical RAG',
    concept2: 'Multimodal Evaluation',
    impact: 'high',
    confidence: 0.83,
    potentialPath: ['Biomedical RAG', 'Ontology Embeddings', 'Multimodal Evaluation']
  },
  {
    id: 'gap-2',
    title: 'Temporal Drift in RAG Pipelines',
    description: 'Retrieval pipelines rarely adapt embeddings for temporal concept drift in fast-moving fields.',
    concept1: 'Temporal Embeddings',
    concept2: 'Autonomous Discovery',
    impact: 'medium',
    confidence: 0.74,
    potentialPath: ['Temporal Embeddings', 'Adaptive Indexing', 'Autonomous Discovery']
  },
  {
    id: 'gap-3',
    title: 'Sparse Hypothesis Validation',
    description: 'Less than 2% of generated hypotheses have structured validation or reproducibility metadata.',
    concept1: 'Hypothesis Agents',
    concept2: 'Lab Automation',
    impact: 'high',
    confidence: 0.68,
    potentialPath: ['Hypothesis Agents', 'Experiment Scheduling', 'Lab Automation']
  }
];

export const mockHypotheses: Hypothesis[] = [
  {
    id: 'hyp-1',
    text: 'Integrate patient genomic graphs with literature embeddings to prioritize therapy gaps in rare cancers.',
    rationale: 'Graph-conditioned retrieval exposes under-studied gene signatures linked to therapy resistance.',
    methodology: 'Fine-tune a graph-RAG pipeline that fuses patient graphs with oncology corpora and evaluate on TCGA cohorts.',
    expectedImpact: 'Accelerates identification of new therapeutic targets for orphan cancers.',
    confidence: 0.71,
    votesUp: 128,
    votesDown: 12,
    status: 'proposed',
    entities: ['graph rag', 'oncology', 'genomics']
  },
  {
    id: 'hyp-2',
    text: 'Deploy autonomous agents to enumerate unexplored electrolyte combinations for solid-state batteries.',
    rationale: 'Agent swarms can scan electrochemistry literature faster than manual reviews.',
    methodology: 'Use multi-agent search with reaction rule validation and benchmark against historical discoveries.',
    expectedImpact: 'Cuts material exploration cycles by 40% for next-gen batteries.',
    confidence: 0.64,
    votesUp: 96,
    votesDown: 5,
    status: 'claimed',
    entities: ['agents', 'materials', 'energy']
  },
  {
    id: 'hyp-3',
    text: 'Monitor semantic drift across long-running RAG deployments and auto-trigger embedding refreshes.',
    rationale: 'Embedding drift quietly degrades retrieval quality in domains with rapid concept evolution.',
    methodology: 'Train a drift detector on timestamped corpora and integrate with retraining pipelines.',
    expectedImpact: 'Maintains >95% retrieval fidelity without manual audits.',
    confidence: 0.82,
    votesUp: 201,
    votesDown: 17,
    status: 'validated',
    entities: ['mlops', 'rag', 'monitoring']
  }
];

export const mockGraphStats: GraphStats = {
  nodes: 1200000,
  edges: 4800000,
  density: 0.0007,
  communities: 128,
  topEntities: ['Graph Neural Networks', 'CRISPR-Cas9', 'Solid-State Batteries', 'Quantum Error Correction'],
  breakdown: {
    papers: 400000,
    concepts: 600000,
    methods: 200000
  }
};

export const mockInsights: DiscoveryInsight[] = [
  {
    id: 'insight-1',
    type: 'gap',
    title: 'Sparse citations in temporal graph studies',
    detail: 'Only 3% of time-aware knowledge graph papers cite downstream validation studies.',
    impact: 'high'
  },
  {
    id: 'insight-2',
    type: 'trend',
    title: 'Rise of symbolic + neural pipelines',
    detail: 'Hybrid symbolic + neural RAG papers increased 42% QoQ.',
    impact: 'medium'
  },
  {
    id: 'insight-3',
    type: 'contradiction',
    title: 'Conflicting results on electron mobility',
    detail: 'Two high-impact papers disagree on dopant concentrations for GaN substrates.',
    impact: 'medium'
  }
];

export const mockTrends: TrendMetric[] = [
  { id: 'trend-1', label: 'Graph RAG', delta: 38, direction: 'up' },
  { id: 'trend-2', label: 'Autonomous Discovery Agents', delta: 24, direction: 'up' },
  { id: 'trend-3', label: 'Symbolic Reasoning', delta: -7, direction: 'down' }
];

