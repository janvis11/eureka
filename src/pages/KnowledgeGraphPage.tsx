import { FormEvent, useState } from 'react';
import { fetchGraphPath, fetchGraphStats } from '../services/researchService';
import { useAsyncData } from '../hooks/useAsyncData';
import { GraphStats } from '../types/api';

const GraphPreview = ({ labels }: { labels: string[] }) => {
  const fallbackLabels = ['document', 'chunk', 'claim', 'concept', 'bridge', 'gap'];
  const displayLabels = (labels.length ? labels : fallbackLabels).slice(0, 6);
  const points = [
    [54, 150],
    [132, 78],
    [218, 122],
    [304, 58],
    [392, 114],
    [486, 72],
  ];

  return (
    <svg viewBox="0 0 540 220" className="h-full w-full" role="img" aria-label="Knowledge graph preview">
      <path
        d="M44 154 C108 76 158 92 222 122 C292 154 330 34 390 112 C430 162 462 86 504 70"
        fill="none"
        stroke="rgba(255,255,255,0.32)"
        strokeWidth="1.6"
        strokeDasharray="8 12"
        className="network-path"
      />
      <path
        d="M56 72 C130 132 194 38 268 82 C348 130 396 172 500 142"
        fill="none"
        stroke="rgba(255,255,255,0.18)"
        strokeWidth="1.2"
        strokeDasharray="4 14"
        className="network-path"
      />
      {points.map(([cx, cy], index) => (
        <g key={`${cx}-${cy}`} className="network-node" style={{ animationDelay: `${index * 0.16}s` }}>
          <circle cx={cx} cy={cy} r="9" fill="black" stroke="white" strokeWidth="2" />
          <circle cx={cx} cy={cy} r="24" fill="none" stroke="rgba(255,255,255,0.2)" />
          <text
            x={index > 3 ? cx - 14 : cx + 14}
            y={cy - 14}
            textAnchor={index > 3 ? 'end' : 'start'}
            fill="rgba(255,255,255,0.74)"
            fontSize="15"
          >
            {displayLabels[index] ?? fallbackLabels[index]}
          </text>
        </g>
      ))}
    </svg>
  );
};

const KnowledgeGraphPage = () => {
  const { data: stats, isLoading, error, refresh } = useAsyncData<GraphStats>(fetchGraphStats, []);
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const [pathResult, setPathResult] = useState<string[]>([]);
  const [pathMessage, setPathMessage] = useState('');
  const [isResolving, setIsResolving] = useState(false);

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
        className="fixed inset-0 pointer-events-none opacity-[0.035]"
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
              Every connection is meant to stay tied to source provenance.
            </p>
          </div>

          <div className="hidden border border-white/15 bg-black/70 p-4 lg:block">
            <div className="mb-3 flex items-center justify-between border-b border-white/10 pb-3 text-[10px] uppercase tracking-[0.24em] text-white/45">
              <span>graph topology</span>
              <span>neo4j</span>
            </div>
            <div className="h-44">
              <GraphPreview labels={stats?.topEntities ?? []} />
            </div>
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
              <StatCard label="Nodes" value={stats.nodes.toLocaleString()} detail="Documents, concepts, claims" />
              <StatCard label="Edges" value={stats.edges.toLocaleString()} detail="Provenance-backed links" />
              <StatCard label="Density" value={stats.density.toFixed(6)} detail="Graph connectivity" />
              <StatCard label="Communities" value={stats.communities.toString()} detail="Detected neighborhoods" />
            </>
          )}
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
