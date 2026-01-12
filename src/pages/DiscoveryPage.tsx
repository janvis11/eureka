import { fetchDiscoveryInsights, fetchResearchGaps, fetchTrendMetrics } from '../services/researchService';
import { useAsyncData } from '../hooks/useAsyncData';
import { DiscoveryInsight, ResearchGap, TrendMetric } from '../types/api';
import { CardSkeleton } from '../components/LoadingSkeleton';

const DiscoveryPage = () => {
  const gaps = useAsyncData<ResearchGap[]>(fetchResearchGaps, []);
  const insights = useAsyncData<DiscoveryInsight[]>(fetchDiscoveryInsights, []);
  const trends = useAsyncData<TrendMetric[]>(fetchTrendMetrics, []);

  return (
    <section className="pt-28 pb-16 px-6 md:px-12 bg-white text-black min-h-screen">
      <div className="max-w-7xl mx-auto space-y-12">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-[0.3em] text-black/60">Discovery Engine</p>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight">Autonomous Gap Detection</h1>
          <p className="text-lg text-black/60 max-w-3xl">
            Multi-agent workflows analyze every new paper to surface gaps, contradictions, and emerging trends—before
            they become obvious.
          </p>
        </header>

        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {gaps.isLoading && (
            <>
              <CardSkeleton />
              <CardSkeleton />
            </>
          )}
          {gaps.error && <ErrorCard message={gaps.error} action={() => gaps.refresh()} />}
          {gaps.data && !gaps.isLoading &&
            gaps.data.map((gap) => (
              <div key={gap.id} className="border border-black rounded-3xl p-6 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold tracking-widest">Gap</span>
                  <span className="text-xs px-3 py-1 rounded-full border border-black/20 uppercase">
                    Impact: {gap.impact}
                  </span>
                </div>
                <h3 className="text-2xl font-bold">{gap.title}</h3>
                <p className="text-black/70 text-sm leading-relaxed">{gap.description}</p>
                <div className="flex items-center justify-between text-xs text-black/60">
                  <span>Confidence {(gap.confidence * 100).toFixed(0)}%</span>
                  <button className="underline">View documents</button>
                </div>
              </div>
            ))}
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 border border-black rounded-3xl p-6 space-y-4">
            <h2 className="text-2xl font-bold">Contradictions & Signals</h2>
            {insights.isLoading && (
              <div className="space-y-4">
                <CardSkeleton />
                <CardSkeleton />
              </div>
            )}
            {insights.error && <ErrorCard message={insights.error} action={() => insights.refresh()} />}
            {insights.data && !insights.isLoading &&
              insights.data.map((insight) => (
                <article key={insight.id} className="border-t border-black/10 pt-4">
                  <div className="flex items-center justify-between text-xs uppercase tracking-widest mb-2">
                    <span>{insight.type}</span>
                    <span>Impact: {insight.impact}</span>
                  </div>
                  <h3 className="text-xl font-semibold">{insight.title}</h3>
                  <p className="text-sm text-black/70">{insight.detail}</p>
                </article>
              ))}
          </div>

          <div className="border border-black rounded-3xl p-6 space-y-4">
            <h2 className="text-xl font-bold">Trend Monitor</h2>
            {trends.isLoading && (
              <div className="space-y-3">
                <div className="h-16 bg-gray-200 rounded animate-pulse"></div>
                <div className="h-16 bg-gray-200 rounded animate-pulse"></div>
                <div className="h-16 bg-gray-200 rounded animate-pulse"></div>
              </div>
            )}
            {trends.error && <ErrorCard message={trends.error} action={() => trends.refresh()} />}
            {trends.data && !trends.isLoading &&
              trends.data.map((trend) => (
                <div key={trend.id} className="flex items-center justify-between border-b border-black/10 py-3">
                  <div>
                    <p className="font-semibold">{trend.label}</p>
                    <p className="text-xs text-black/60">QoQ delta</p>
                  </div>
                  <span className={`text-lg font-bold ${trend.direction === 'down' ? 'text-red-500' : 'text-emerald-600'}`}>
                    {trend.direction === 'down' ? '-' : '+'}
                    {trend.delta}%
                  </span>
                </div>
              ))}
          </div>
        </section>
      </div>
    </section>
  );
};

const PlaceholderCard = ({ title }: { title: string }) => (
  <div className="border border-dashed border-black/30 rounded-3xl p-6 text-sm text-black/60 animate-pulse">{title}</div>
);

const ErrorCard = ({ message, action }: { message: string; action: () => void }) => (
  <div className="border border-red-400 rounded-3xl p-6 text-sm text-red-600 space-y-2">
    <p>{message}</p>
    <button className="underline font-semibold" onClick={action}>
      Retry
    </button>
  </div>
);

export default DiscoveryPage;

