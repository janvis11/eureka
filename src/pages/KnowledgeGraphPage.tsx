import { FormEvent, useState } from 'react';
import { fetchGraphPath, fetchGraphStats } from '../services/researchService';
import { useAsyncData } from '../hooks/useAsyncData';
import { GraphStats } from '../types/api';
import { StatCardSkeleton } from '../components/LoadingSkeleton';

const KnowledgeGraphPage = () => {
  const { data: stats, isLoading, error, refresh } = useAsyncData<GraphStats>(fetchGraphStats, []);
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const [pathResult, setPathResult] = useState<string[]>([]);
  const [pathMessage, setPathMessage] = useState<string>('');
  const [isResolving, setIsResolving] = useState(false);

  const handlePathSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!source || !target) return;
    setIsResolving(true);
    setPathMessage('');
    const path = await fetchGraphPath({ source, target, maxDepth: 4 });
    if (path.length === 0) {
      setPathResult([]);
      setPathMessage('No direct path found within 4 hops. Try different entities or increase depth.');
    } else {
      setPathMessage('');
      setPathResult(path);
    }
    setIsResolving(false);
  };

  return (
    <section className="pt-28 pb-16 px-6 md:px-12 bg-black min-h-screen">
      <div className="max-w-7xl mx-auto space-y-12">
        <header className="text-center space-y-3">
          <p className="text-xs uppercase tracking-[0.3em] text-white/60">Knowledge Graph</p>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight">Network Intelligence</h1>
          <p className="text-lg text-white/60 max-w-3xl mx-auto">
            4.8M+ relations mapped across methods, findings, compounds, and concepts with Neo4j-powered analytics.
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {isLoading && (
            <>
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
              <StatCardSkeleton />
            </>
          )}
          {error && (
            <div className="col-span-4 text-center text-red-400 bg-red-900/20 border border-red-500/50 rounded-xl p-6">
              <p className="mb-4">Failed to load graph statistics.</p>
              <button 
                className="px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors"
                onClick={() => refresh()}
                aria-label="Retry loading graph stats"
              >
                Retry
              </button>
            </div>
          )}
          {stats && !isLoading && (
            <>
              <StatCard label="Nodes" value={stats.nodes.toLocaleString()} detail="Unique scientific entities" />
              <StatCard label="Edges" value={stats.edges.toLocaleString()} detail="Relationships tracked" />
              <StatCard label="Density" value={stats.density.toFixed(6)} detail="Graph connectivity" />
              <StatCard label="Communities" value={stats.communities.toString()} detail="Detected domains" />
            </>
          )}
        </div>

        {stats && (
          <div className="bg-white text-black rounded-3xl p-10 space-y-6">
            <h2 className="text-2xl font-bold tracking-tight">Top Emerging Entities</h2>
            {stats.breakdown && (
              <div className="flex flex-wrap gap-6 text-sm text-black/70">
                <span>Papers: {stats.breakdown.papers.toLocaleString()}</span>
                <span>Concepts: {stats.breakdown.concepts.toLocaleString()}</span>
                <span>Methods: {stats.breakdown.methods.toLocaleString()}</span>
              </div>
            )}
            <div className="flex flex-wrap gap-3">
              {stats.topEntities.map((entity) => (
                <span key={entity} className="px-4 py-2 border border-black/10 rounded-full text-sm font-medium">
                  {entity}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <form onSubmit={handlePathSearch} className="bg-white text-black rounded-3xl p-8 space-y-4">
            <h3 className="text-xl font-semibold tracking-tight">Path Finder</h3>
            <p className="text-black/60 text-sm">Find multi-hop explanations between research concepts.</p>
            <label className="text-xs font-semibold tracking-widest">SOURCE</label>
            <input
              value={source}
              onChange={(event) => setSource(event.target.value)}
              placeholder="Graph Neural Networks"
              className="w-full border border-black/10 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-black"
            />
            <label className="text-xs font-semibold tracking-widest">TARGET</label>
            <input
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              placeholder="Solid-state batteries"
              className="w-full border border-black/10 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-black"
            />
            <button
              type="submit"
              disabled={isResolving || !source.trim() || !target.trim()}
              aria-label="Find path between concepts"
              className="w-full bg-black text-white py-3 rounded-xl font-semibold tracking-wide disabled:bg-black/40 disabled:cursor-not-allowed transition-colors"
            >
              {isResolving ? 'Mapping...' : 'Resolve Path'}
            </button>
            {pathResult.length > 0 && <p className="text-sm text-black/70">{pathResult.join(' → ')}</p>}
            {pathMessage && <p className="text-sm text-red-500">{pathMessage}</p>}
          </form>

          <div className="rounded-3xl border border-white/10 p-8 bg-gradient-to-br from-slate-900 to-slate-800 space-y-4">
            <h3 className="text-xl font-semibold">Graph Analytics Stack</h3>
            <ul className="space-y-3 text-white/70 text-sm">
              <li>• Neo4j 5.x cluster with Aura Enterprise</li>
              <li>• Community detection (Louvain, Leiden)</li>
              <li>• Temporal snapshots + drift detection</li>
              <li>• Path ranking via contextual embeddings</li>
              <li>• Real-time sync with discovery engine</li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};

const StatCard = ({ label, value, detail }: { label: string; value: string; detail: string }) => (
  <div className="border border-white/10 rounded-3xl p-6 space-y-2 bg-white/5">
    <p className="text-xs tracking-[0.3em] text-white/60 uppercase">{label}</p>
    <p className="text-4xl font-bold">{value}</p>
    <p className="text-sm text-white/60">{detail}</p>
  </div>
);

export default KnowledgeGraphPage;

