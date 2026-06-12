import { FormEvent, useEffect, useMemo, useState } from 'react';
import { fetchGraphOverview, fetchGraphPath, fetchGraphStats } from '../services/researchService';
import { useAsyncData } from '../hooks/useAsyncData';
import { GraphEdge, GraphNode, GraphOverview, GraphStats } from '../types/api';

const GRAPH_LIMIT = 25;
const RELATIONSHIP_FILTERS = ['CONTAINS', 'MENTIONS', 'ASSERTS', 'ABOUT', 'RELATED', 'ALL'];
const SVG_WIDTH = 920;
const SVG_HEIGHT = 540;

type NodeTheme = {
  fill: string;
  stroke: string;
  halo: string;
  text: string;
  radius: number;
};

type PositionedNode = GraphNode & {
  x: number;
  y: number;
  degree: number;
};

const NODE_THEMES: Record<string, NodeTheme> = {
  Document: {
    fill: '#4cebe3',
    stroke: 'rgba(76, 235, 227, 0.95)',
    halo: 'rgba(76, 235, 227, 0.14)',
    text: '#021312',
    radius: 17,
  },
  Chunk: {
    fill: '#f8a9eb',
    stroke: 'rgba(248, 169, 235, 0.94)',
    halo: 'rgba(248, 169, 235, 0.14)',
    text: '#1b0716',
    radius: 13,
  },
  Entity: {
    fill: '#f3c567',
    stroke: 'rgba(243, 197, 103, 0.92)',
    halo: 'rgba(243, 197, 103, 0.14)',
    text: '#1a1101',
    radius: 15,
  },
  Claim: {
    fill: '#6ee7a8',
    stroke: 'rgba(110, 231, 168, 0.9)',
    halo: 'rgba(110, 231, 168, 0.14)',
    text: '#03150b',
    radius: 14,
  },
  Hypothesis: {
    fill: '#b7a2ff',
    stroke: 'rgba(183, 162, 255, 0.94)',
    halo: 'rgba(183, 162, 255, 0.14)',
    text: '#10052f',
    radius: 15,
  },
  ResearchGap: {
    fill: '#fb923c',
    stroke: 'rgba(251, 146, 60, 0.92)',
    halo: 'rgba(251, 146, 60, 0.14)',
    text: '#1d0900',
    radius: 15,
  },
  Node: {
    fill: '#f7f7f7',
    stroke: 'rgba(255, 255, 255, 0.8)',
    halo: 'rgba(255, 255, 255, 0.1)',
    text: '#050505',
    radius: 13,
  },
};

const EDGE_COLORS: Record<string, string> = {
  CONTAINS: 'rgba(76, 235, 227, 0.52)',
  MENTIONS: 'rgba(243, 197, 103, 0.52)',
  ASSERTS: 'rgba(110, 231, 168, 0.5)',
  ABOUT: 'rgba(183, 162, 255, 0.52)',
  RELATED: 'rgba(251, 146, 60, 0.48)',
};

const getPrimaryKind = (kind: string) => {
  if (NODE_THEMES[kind]) return kind;
  return 'Node';
};

const getNodeTheme = (kind: string) => NODE_THEMES[getPrimaryKind(kind)];

const truncate = (value: string, maxLength = 28) => (
  value.length > maxLength ? `${value.slice(0, maxLength - 3)}...` : value
);

const getNodeDisplayLabel = (node: GraphNode, maxLength = 28) => {
  if (node.kind === 'Chunk') {
    const chunkIndex = Number.isFinite(node.chunkIndex) ? node.chunkIndex : undefined;
    return chunkIndex === undefined ? 'Chunk' : `Chunk ${chunkIndex}`;
  }

  if (node.kind === 'Claim') {
    return truncate(node.claimType ? `${node.claimType} claim` : node.label || 'Claim', maxLength);
  }

  return truncate(node.name || node.title || node.key || node.label || node.id, maxLength);
};

const getNodeInitial = (node: GraphNode) => {
  if (node.kind === 'ResearchGap') return 'G';
  return (node.kind || 'N').slice(0, 1).toUpperCase();
};

const buildGraphLayout = (nodes: GraphNode[], edges: GraphEdge[]): PositionedNode[] => {
  const degreeById = new Map<string, number>();
  edges.forEach(edge => {
    degreeById.set(edge.source, (degreeById.get(edge.source) ?? 0) + 1);
    degreeById.set(edge.target, (degreeById.get(edge.target) ?? 0) + 1);
  });

  const grouped = nodes.reduce<Record<string, GraphNode[]>>((acc, node) => {
    const kind = getPrimaryKind(node.kind);
    acc[kind] = acc[kind] ? [...acc[kind], node] : [node];
    return acc;
  }, {});

  const columnOrder = ['Document', 'Chunk', 'Entity', 'Claim', 'Hypothesis', 'ResearchGap', 'Node'];
  const columnX: Record<string, number> = {
    Document: 120,
    Chunk: 345,
    Entity: 575,
    Claim: 760,
    Hypothesis: 760,
    ResearchGap: 760,
    Node: 575,
  };

  return Object.entries(grouped)
    .sort(([kindA], [kindB]) => columnOrder.indexOf(kindA) - columnOrder.indexOf(kindB))
    .flatMap(([kind, group]) => {
      const sortedGroup = [...group].sort((a, b) => {
        const degreeDelta = (degreeById.get(b.id) ?? 0) - (degreeById.get(a.id) ?? 0);
        if (degreeDelta !== 0) return degreeDelta;
        return getNodeDisplayLabel(a).localeCompare(getNodeDisplayLabel(b));
      });
      const spacing = Math.min(58, Math.max(28, (SVG_HEIGHT - 150) / Math.max(sortedGroup.length - 1, 1)));
      const startY = SVG_HEIGHT / 2 - ((sortedGroup.length - 1) * spacing) / 2;

      return sortedGroup.map((node, index) => ({
        ...node,
        x: (columnX[kind] ?? columnX.Node) + (index % 2 === 0 ? 0 : 18),
        y: sortedGroup.length === 1 ? SVG_HEIGHT / 2 : startY + index * spacing,
        degree: degreeById.get(node.id) ?? 0,
      }));
    });
};

const countBy = (values: string[]) => (
  values.reduce<Record<string, number>>((acc, value) => {
    const key = value || 'Unknown';
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {})
);

const sortedCounts = (counts: Record<string, number>) => (
  Object.entries(counts).sort(([, countA], [, countB]) => countB - countA)
);

const LiveGraphView = ({
  graph,
  selectedNodeId,
  onSelectNode,
}: {
  graph: GraphOverview;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string) => void;
}) => {
  const positionedNodes = useMemo(
    () => buildGraphLayout(graph.nodes, graph.edges),
    [graph.nodes, graph.edges],
  );
  const nodesById = useMemo(
    () => new Map(positionedNodes.map(node => [node.id, node])),
    [positionedNodes],
  );

  if (graph.nodes.length === 0) {
    return (
      <div className="flex h-[34rem] items-center justify-center border border-white/10 bg-white/[0.02] text-sm text-white/45">
        No Neo4j relationships found for this filter.
      </div>
    );
  }

  return (
    <div className="relative h-[34rem] overflow-hidden border border-white/10 bg-black">
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        className="h-full w-full"
        role="img"
        aria-label="Neo4j knowledge graph"
      >
        <defs>
          <marker
            id="graph-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(255,255,255,0.42)" />
          </marker>
        </defs>

        <rect width={SVG_WIDTH} height={SVG_HEIGHT} fill="rgba(255,255,255,0.015)" />
        <g opacity="0.18">
          {Array.from({ length: 10 }).map((_, index) => (
            <line
              key={`v-${index}`}
              x1={70 + index * 86}
              y1="28"
              x2={70 + index * 86}
              y2={SVG_HEIGHT - 28}
              stroke="white"
              strokeWidth="0.7"
            />
          ))}
          {Array.from({ length: 6 }).map((_, index) => (
            <line
              key={`h-${index}`}
              x1="44"
              y1={62 + index * 82}
              x2={SVG_WIDTH - 44}
              y2={62 + index * 82}
              stroke="white"
              strokeWidth="0.7"
            />
          ))}
        </g>

        <g>
          {graph.edges.map(edge => {
            const source = nodesById.get(edge.source);
            const target = nodesById.get(edge.target);
            if (!source || !target) return null;

            const edgeColor = EDGE_COLORS[edge.type] ?? 'rgba(255,255,255,0.34)';
            const midX = (source.x + target.x) / 2;
            const midY = (source.y + target.y) / 2;
            const label = truncate(edge.predicate || edge.type, 18);

            return (
              <g key={edge.id}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={edgeColor}
                  strokeWidth={selectedNodeId === source.id || selectedNodeId === target.id ? 2.4 : 1.3}
                  markerEnd="url(#graph-arrow)"
                />
                {graph.edges.length <= 35 && (
                  <text
                    x={midX}
                    y={midY - 5}
                    textAnchor="middle"
                    fill="rgba(255,255,255,0.45)"
                    fontSize="10"
                    fontWeight="700"
                  >
                    {label}
                  </text>
                )}
              </g>
            );
          })}
        </g>

        <g>
          {positionedNodes.map(node => {
            const theme = getNodeTheme(node.kind);
            const isSelected = selectedNodeId === node.id;
            const label = getNodeDisplayLabel(node, 20);

            return (
              <g
                key={node.id}
                tabIndex={0}
                role="button"
                aria-label={getNodeDisplayLabel(node, 80)}
                className="cursor-pointer outline-none"
                onClick={() => onSelectNode(node.id)}
                onKeyDown={event => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onSelectNode(node.id);
                  }
                }}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={theme.radius + 13}
                  fill={theme.halo}
                  stroke={isSelected ? 'rgba(255,255,255,0.5)' : 'transparent'}
                  strokeWidth="1"
                />
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={isSelected ? theme.radius + 3 : theme.radius}
                  fill={theme.fill}
                  stroke={isSelected ? 'white' : theme.stroke}
                  strokeWidth={isSelected ? 2.5 : 1.6}
                />
                <text
                  x={node.x}
                  y={node.y + 4}
                  textAnchor="middle"
                  fill={theme.text}
                  fontSize="11"
                  fontWeight="800"
                >
                  {getNodeInitial(node)}
                </text>
                <text
                  x={node.x}
                  y={node.y + theme.radius + 20}
                  textAnchor="middle"
                  fill={isSelected ? 'white' : 'rgba(255,255,255,0.64)'}
                  fontSize="11"
                  fontWeight={isSelected ? 800 : 600}
                >
                  {label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
};

const GraphInspector = ({ graph, selectedNode }: { graph: GraphOverview; selectedNode: GraphNode | null }) => {
  const nodeCounts = sortedCounts(countBy(graph.nodes.map(node => node.kind)));
  const edgeCounts = sortedCounts(countBy(graph.edges.map(edge => edge.type)));
  const detailRows = selectedNode
    ? [
        ['Kind', selectedNode.kind],
        ['Key', selectedNode.key],
        ['Name', selectedNode.name],
        ['Title', selectedNode.title],
        ['Chunk', selectedNode.chunkIndex === undefined ? undefined : String(selectedNode.chunkIndex)],
        ['Tokens', selectedNode.tokenCount === undefined ? undefined : selectedNode.tokenCount.toLocaleString()],
        ['Claim type', selectedNode.claimType],
        ['Polarity', selectedNode.polarity],
        ['Confidence', selectedNode.confidence === undefined ? undefined : `${Math.round(selectedNode.confidence * 100)}%`],
      ].filter(([, value]) => value !== undefined && value !== '')
    : [];

  return (
    <aside className="border-t border-white/10 pt-5 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.22em] text-white/35">Results Overview</p>
        <div className="mt-3 space-y-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-white/55">
              Nodes ({graph.nodes.length})
            </p>
            <div className="flex flex-wrap gap-2">
              {nodeCounts.map(([kind, count]) => {
                const theme = getNodeTheme(kind);
                return (
                  <span
                    key={kind}
                    className="border px-2.5 py-1 text-xs font-bold text-white"
                    style={{ borderColor: theme.stroke, backgroundColor: theme.halo }}
                  >
                    {kind} {count}
                  </span>
                );
              })}
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-white/55">
              Relationships ({graph.edges.length})
            </p>
            <div className="flex flex-wrap gap-2">
              {edgeCounts.map(([type, count]) => (
                <span key={type} className="border border-white/15 px-2.5 py-1 text-xs font-bold text-white/70">
                  {type} {count}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-white/10 pt-5">
        <p className="text-xs uppercase tracking-[0.22em] text-white/35">Selected Node</p>
        {selectedNode ? (
          <div className="mt-4 space-y-4">
            <div>
              <h3 className="text-lg font-bold text-white">{getNodeDisplayLabel(selectedNode, 44)}</h3>
              {selectedNode.text && (
                <p className="mt-2 max-h-36 overflow-y-auto text-sm leading-relaxed text-white/55">
                  {selectedNode.text}
                </p>
              )}
            </div>
            <dl className="space-y-2 text-sm">
              {detailRows.map(([label, value]) => (
                <div key={label} className="grid grid-cols-[92px_minmax(0,1fr)] gap-3 border-t border-white/10 pt-2">
                  <dt className="text-xs uppercase tracking-[0.14em] text-white/35">{label}</dt>
                  <dd className="break-words text-white/68">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ) : (
          <p className="mt-4 text-sm text-white/45">No node selected.</p>
        )}
      </div>
    </aside>
  );
};

const KnowledgeGraphPage = () => {
  const { data: stats, isLoading, error, refresh } = useAsyncData<GraphStats>(fetchGraphStats, []);
  const [relationshipFilter, setRelationshipFilter] = useState('CONTAINS');
  const {
    data: graph,
    isLoading: isGraphLoading,
    error: graphError,
    refresh: refreshGraph,
  } = useAsyncData<GraphOverview>(
    () => fetchGraphOverview({
      limit: GRAPH_LIMIT,
      relationshipTypes: relationshipFilter === 'ALL' ? [] : [relationshipFilter],
    }),
    [relationshipFilter],
  );
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const [pathResult, setPathResult] = useState<string[]>([]);
  const [pathMessage, setPathMessage] = useState('');
  const [isResolving, setIsResolving] = useState(false);

  const selectedNode = useMemo(
    () => graph?.nodes.find(node => node.id === selectedNodeId) ?? graph?.nodes[0] ?? null,
    [graph, selectedNodeId],
  );
  const cypherPreview = relationshipFilter === 'ALL'
    ? `MATCH p=()-[]->() RETURN p LIMIT ${GRAPH_LIMIT};`
    : `MATCH p=()-[:${relationshipFilter}]->() RETURN p LIMIT ${GRAPH_LIMIT};`;

  useEffect(() => {
    if (!graph?.nodes.length) {
      setSelectedNodeId(null);
      return;
    }

    if (!selectedNodeId || !graph.nodes.some(node => node.id === selectedNodeId)) {
      setSelectedNodeId(graph.nodes[0].id);
    }
  }, [graph, selectedNodeId]);

  const handlePathSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!source.trim() || !target.trim()) return;

    setIsResolving(true);
    setPathMessage('');
    try {
      const path = await fetchGraphPath({ source: source.trim(), target: target.trim(), maxDepth: 4 });
      if (path.length === 0) {
        setPathResult([]);
        setPathMessage('No path found within 4 hops. Try entities that appear in processed papers.');
      } else {
        setPathResult(path);
      }
    } catch (err) {
      setPathResult([]);
      setPathMessage(err instanceof Error ? err.message : 'Path search failed.');
    } finally {
      setIsResolving(false);
    }
  };

  return (
    <section className="relative min-h-screen overflow-hidden bg-black px-4 pb-16 pt-28 text-white md:px-10">
      <div
        className="pointer-events-none fixed inset-0 opacity-[0.035]"
        style={{
          backgroundImage:
            'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
          backgroundSize: '54px 54px',
        }}
      />

      <div className="relative mx-auto max-w-7xl space-y-8">
        <header className="grid gap-8 border-b border-white/15 pb-8 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-5">
            <p className="text-xs font-semibold uppercase tracking-[0.4em] text-white/40">
              Knowledge Graph
            </p>
            <h1 className="text-5xl font-black leading-none tracking-normal md:text-7xl">
              NETWORK
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-white/55 md:text-lg">
              Explore concept, claim, evidence, and document paths generated from uploaded research papers.
              Every connection is tied to Neo4j provenance.
            </p>
          </div>

          <div className="hidden border border-white/15 bg-black/70 p-5 lg:block">
            <div className="mb-5 flex items-center justify-between border-b border-white/10 pb-3 text-[10px] uppercase tracking-[0.24em] text-white/45">
              <span>live graph</span>
              <span>neo4j</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="border border-white/10 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-white/35">Sample Nodes</p>
                <p className="mt-3 font-mono text-3xl font-bold">{graph?.nodes.length ?? 0}</p>
              </div>
              <div className="border border-white/10 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-white/35">Sample Edges</p>
                <p className="mt-3 font-mono text-3xl font-bold">{graph?.edges.length ?? 0}</p>
              </div>
            </div>
            <p className="mt-5 break-all border-t border-white/10 pt-4 font-mono text-xs text-white/45">
              {cypherPreview}
            </p>
          </div>
        </header>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {isLoading && (
            <>
              {[0, 1, 2, 3].map(item => (
                <div key={item} className="animate-pulse border border-white/15 bg-black/70 p-6">
                  <div className="mb-4 h-4 w-24 bg-white/15" />
                  <div className="mb-3 h-10 w-28 bg-white/10" />
                  <div className="h-3 w-full bg-white/10" />
                </div>
              ))}
            </>
          )}

          {error && (
            <div className="col-span-2 border border-red-400/40 bg-red-500/10 p-6 text-sm text-red-200 lg:col-span-4">
              <p className="mb-4">Failed to load graph statistics.</p>
              <button
                className="border border-red-200/40 px-4 py-2 text-xs uppercase tracking-[0.16em]"
                onClick={() => refresh()}
              >
                Retry
              </button>
            </div>
          )}

          {stats && !isLoading && (
            <>
              <StatCard label="Nodes" value={stats.nodes.toLocaleString()} detail="Documents, chunks, concepts, claims" />
              <StatCard label="Edges" value={stats.edges.toLocaleString()} detail="Provenance-backed links" />
              <StatCard label="Density" value={stats.density.toFixed(6)} detail="Graph connectivity" />
              <StatCard label="Communities" value={stats.communities.toString()} detail="Detected neighborhoods" />
            </>
          )}
        </div>

        <div className="border border-white/15 bg-black/70 p-5 md:p-7">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-white/35">Neo4j Browser</p>
              <h2 className="mt-2 text-2xl font-bold">Live Graph View</h2>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {RELATIONSHIP_FILTERS.map(filter => {
                const isActive = relationshipFilter === filter;
                return (
                  <button
                    key={filter}
                    type="button"
                    onClick={() => setRelationshipFilter(filter)}
                    className={`border px-3 py-2 text-xs font-bold uppercase tracking-[0.14em] transition-colors ${
                      isActive
                        ? 'border-white bg-white text-black'
                        : 'border-white/15 text-white/55 hover:border-white/50 hover:text-white'
                    }`}
                  >
                    {filter}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => refreshGraph()}
                className="border border-white/15 px-3 py-2 text-xs font-bold uppercase tracking-[0.14em] text-white/55 transition-colors hover:border-white/50 hover:text-white"
              >
                Reload
              </button>
            </div>
          </div>

          <div className="mb-5 border border-white/10 bg-white/[0.03] px-4 py-3 font-mono text-xs text-white/55">
            {cypherPreview}
          </div>

          {graphError && (
            <div className="mb-5 border border-red-400/40 bg-red-500/10 p-4 text-sm text-red-200">
              <p className="mb-3">Failed to load Neo4j graph data.</p>
              <button
                type="button"
                className="border border-red-200/40 px-4 py-2 text-xs uppercase tracking-[0.16em]"
                onClick={() => refreshGraph()}
              >
                Retry
              </button>
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_330px]">
            <div>
              {isGraphLoading && (
                <div className="flex h-[34rem] animate-pulse items-center justify-center border border-white/10 bg-white/[0.02]">
                  <span className="text-sm uppercase tracking-[0.2em] text-white/35">Loading graph</span>
                </div>
              )}

              {graph && !isGraphLoading && (
                <LiveGraphView
                  graph={graph}
                  selectedNodeId={selectedNode?.id ?? null}
                  onSelectNode={setSelectedNodeId}
                />
              )}
            </div>

            {graph && !isGraphLoading && (
              <GraphInspector graph={graph} selectedNode={selectedNode} />
            )}
          </div>
        </div>

        {stats && (
          <div className="border border-white/15 bg-black/70 p-6 md:p-8">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-white/35">Entity Index</p>
                <h2 className="mt-2 text-2xl font-bold">Top Entities</h2>
              </div>
              {stats.breakdown && (
                <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.14em] text-white/45">
                  <span className="border border-white/15 px-3 py-1">Papers {stats.breakdown.papers.toLocaleString()}</span>
                  {stats.breakdown.chunks !== undefined && (
                    <span className="border border-white/15 px-3 py-1">Chunks {stats.breakdown.chunks.toLocaleString()}</span>
                  )}
                  <span className="border border-white/15 px-3 py-1">Concepts {stats.breakdown.concepts.toLocaleString()}</span>
                  {stats.breakdown.claims !== undefined && (
                    <span className="border border-white/15 px-3 py-1">Claims {stats.breakdown.claims.toLocaleString()}</span>
                  )}
                  {stats.breakdown.hypotheses !== undefined && (
                    <span className="border border-white/15 px-3 py-1">
                      Hypotheses {stats.breakdown.hypotheses.toLocaleString()}
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              {stats.topEntities.length === 0 && (
                <span className="text-sm text-white/45">No graph entities yet. Upload and process PDFs first.</span>
              )}
              {stats.topEntities.map(entity => (
                <span key={entity} className="border border-white/15 px-4 py-2 text-sm font-medium text-white/65">
                  {entity}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <form onSubmit={handlePathSearch} className="space-y-4 border border-white/15 bg-black/70 p-6 md:p-8">
            <div className="border-b border-white/10 pb-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/35">Traversal</p>
              <h3 className="mt-2 text-2xl font-semibold">Path Finder</h3>
              <p className="mt-2 text-sm text-white/45">
                Find multi-hop explanations between concepts found in your corpus.
              </p>
            </div>

            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Source</label>
            <input
              value={source}
              onChange={event => setSource(event.target.value)}
              placeholder="Graph RAG"
              className="w-full border border-white/15 bg-black p-3 text-sm text-white outline-none transition-colors placeholder:text-white/25 focus:border-white"
            />

            <label className="text-xs font-semibold uppercase tracking-[0.2em] text-white/55">Target</label>
            <input
              value={target}
              onChange={event => setTarget(event.target.value)}
              placeholder="Drug Discovery"
              className="w-full border border-white/15 bg-black p-3 text-sm text-white outline-none transition-colors placeholder:text-white/25 focus:border-white"
            />

            <button
              type="submit"
              disabled={isResolving || !source.trim() || !target.trim()}
              className="w-full border border-white bg-white py-3 text-xs font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-black hover:text-white disabled:cursor-not-allowed disabled:border-white/15 disabled:bg-white/10 disabled:text-white/30"
            >
              {isResolving ? 'Mapping' : 'Resolve Path'}
            </button>

            {pathResult.length > 0 && (
              <div className="border border-white/15 bg-white/[0.03] p-4">
                <p className="mb-3 text-xs uppercase tracking-[0.2em] text-white/35">Resolved Path</p>
                <div className="flex flex-wrap items-center gap-2">
                  {pathResult.map((node, index) => (
                    <span key={`${node}-${index}`} className="flex items-center gap-2">
                      <span className="border border-white/20 px-3 py-1 text-sm text-white/70">{node}</span>
                      {index < pathResult.length - 1 && <span className="text-white/35">-&gt;</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {pathMessage && <p className="border border-white/15 p-3 text-sm text-white/45">{pathMessage}</p>}
          </form>

          <div className="space-y-5 border border-white/15 bg-black/70 p-6 md:p-8">
            <div className="border-b border-white/10 pb-4">
              <p className="text-xs uppercase tracking-[0.24em] text-white/35">Extraction Stack</p>
              <h3 className="mt-2 text-2xl font-semibold">Graph Construction</h3>
            </div>
            {[
              'Document nodes preserve source metadata.',
              'Chunk nodes keep source spans for citations.',
              'Entity nodes attach to claims and mentions.',
              'Relationships keep predicate, evidence, confidence, and chunk provenance.',
              'Gap and path queries run over the Neo4j graph when available.',
            ].map((item, index) => (
              <div key={item} className="flex gap-4 border border-white/10 p-4 text-sm text-white/60">
                <span className="font-mono text-white/35">{String(index + 1).padStart(2, '0')}</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

const StatCard = ({ label, value, detail }: { label: string; value: string; detail: string }) => (
  <div className="border border-white/15 bg-black/70 p-6">
    <p className="text-xs uppercase tracking-[0.24em] text-white/40">{label}</p>
    <p className="mt-3 font-mono text-4xl font-bold text-white">{value}</p>
    <p className="mt-2 text-sm text-white/45">{detail}</p>
  </div>
);

export default KnowledgeGraphPage;
