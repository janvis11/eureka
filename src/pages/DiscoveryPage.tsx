import React, { useCallback, useState } from 'react';
import ContradictionGraph from '../components/discovery/ContradictionGraph';
import HypothesisCard from '../components/discovery/HypothesisCard';
import GapCard from '../components/discovery/GapCard';
import TrendRadar from '../components/discovery/TrendRadar';
import {
  runFullDiscoveryAnalysis,
  getGraphGaps,
  getGraphContradictions,
  generateGraphHypotheses,
  getTrends,
  type ResearchGap,
  type Contradiction,
  type Hypothesis,
  type Trend,
} from '../services/discoveryService';

type Tab = 'gaps' | 'contradictions' | 'hypotheses' | 'trends';

type AnalysisPhase =
  | 'idle'
  | 'analyzing'
  | 'gaps'
  | 'contradictions'
  | 'hypotheses'
  | 'trends'
  | 'done'
  | 'error';

interface DiscoveryState {
  gaps: ResearchGap[];
  contradictions: Contradiction[];
  hypotheses: Hypothesis[];
  trends: Trend[];
  phase: AnalysisPhase;
  error?: string;
  sources: {
    gaps?: string;
    contradictions?: string;
    hypotheses?: string;
  };
}

const PHASE_META: Record<AnalysisPhase, { label: string; token: string }> = {
  idle: { label: 'Ready', token: '00' },
  analyzing: { label: 'Initializing discovery pipeline', token: '01' },
  gaps: { label: 'Detecting graph gaps', token: '02' },
  contradictions: { label: 'Mining contradictions', token: '03' },
  hypotheses: { label: 'Generating hypotheses', token: '04' },
  trends: { label: 'Computing trend signals', token: '05' },
  done: { label: 'Analysis complete', token: 'OK' },
  error: { label: 'Analysis failed', token: 'ER' },
};

const PHASE_ORDER: AnalysisPhase[] = [
  'analyzing',
  'gaps',
  'contradictions',
  'hypotheses',
  'trends',
  'done',
];

const TABS: Array<{ id: Tab; label: string }> = [
  { id: 'gaps', label: 'Gaps' },
  { id: 'contradictions', label: 'Contradictions' },
  { id: 'hypotheses', label: 'Hypotheses' },
  { id: 'trends', label: 'Trends' },
];

const PhaseIndicator: React.FC<{ phase: AnalysisPhase }> = ({ phase }) => {
  const meta = PHASE_META[phase];
  const isActive = !['idle', 'done', 'error'].includes(phase);

  return (
    <div className="flex items-center gap-3 text-xs uppercase tracking-[0.18em]">
      <span
        className={`flex h-9 w-9 items-center justify-center border font-mono ${
          isActive
            ? 'network-node border-white text-white'
            : phase === 'error'
              ? 'border-red-400/60 text-red-300'
              : 'border-white/25 text-white/65'
        }`}
      >
        {meta.token}
      </span>
      <span className={phase === 'error' ? 'text-red-300' : 'text-white/65'}>{meta.label}</span>
    </div>
  );
};

const TabButton: React.FC<{
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}> = ({ label, count, active, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center border px-4 py-3 text-xs font-bold uppercase tracking-[0.18em] transition-colors ${
      active
        ? 'border-white bg-white text-black'
        : 'border-white/15 bg-black/70 text-white/55 hover:border-white/40 hover:text-white'
    }`}
  >
    <span>{label}</span>
    <span className={`ml-3 border-l pl-3 font-mono ${active ? 'border-black/25' : 'border-white/15'}`}>
      {count}
    </span>
  </button>
);

const StatPill: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="border border-white/15 bg-black/70 p-5">
    <p className="font-mono text-4xl font-bold text-white">{value}</p>
    <p className="mt-2 text-xs uppercase tracking-[0.18em] text-white/45">{label}</p>
  </div>
);

const MiniNetwork = () => (
  <svg viewBox="0 0 360 180" className="h-full w-full" role="img" aria-label="Discovery network preview">
    <path
      d="M24 132 C86 72 138 120 180 92 C230 58 260 78 336 40"
      fill="none"
      stroke="rgba(255,255,255,0.35)"
      strokeWidth="1"
      strokeDasharray="8 12"
      className="network-path"
    />
    <path
      d="M36 56 C96 84 116 42 166 58 C222 78 238 136 326 118"
      fill="none"
      stroke="rgba(255,255,255,0.18)"
      strokeWidth="1"
      strokeDasharray="4 14"
      className="network-path"
    />
    {[
      [38, 128, 'paper'],
      [118, 92, 'claim'],
      [180, 92, 'gap'],
      [248, 70, 'bridge'],
      [326, 42, 'hypothesis'],
      [326, 118, 'trend'],
    ].map(([cx, cy, label], index) => (
      <g key={`${cx}-${cy}`} className="network-node" style={{ animationDelay: `${index * 0.18}s` }}>
        <circle cx={Number(cx)} cy={Number(cy)} r={5} fill="black" stroke="white" strokeWidth="1.2" />
        <circle cx={Number(cx)} cy={Number(cy)} r={14} fill="none" stroke="rgba(255,255,255,0.16)" />
        <text x={Number(cx) + 10} y={Number(cy) - 9} fill="rgba(255,255,255,0.5)" fontSize="10">
          {label}
        </text>
      </g>
    ))}
  </svg>
);

const DiscoveryPage: React.FC = () => {
  const [state, setState] = useState<DiscoveryState>({
    gaps: [],
    contradictions: [],
    hypotheses: [],
    trends: [],
    phase: 'idle',
    sources: {},
  });
  const [activeTab, setActiveTab] = useState<Tab>('gaps');

  const runAnalysis = useCallback(async () => {
    setState(s => ({ ...s, phase: 'analyzing', error: undefined }));

    try {
      setState(s => ({ ...s, phase: 'gaps' }));
      let gaps: ResearchGap[] = [];
      try {
        const gapsResult = await getGraphGaps(15);
        gaps = gapsResult.gaps;
        setState(s => ({
          ...s,
          gaps,
          sources: { ...s.sources, gaps: gapsResult.source },
        }));
      } catch {
        try {
          const legacyResult = await runFullDiscoveryAnalysis();
          gaps = legacyResult?.analysis?.gaps ?? [];
          setState(s => ({ ...s, gaps }));
        } catch {
          gaps = [];
        }
      }

      setState(s => ({ ...s, phase: 'contradictions' }));
      let contradictions: Contradiction[] = [];
      try {
        const contrResult = await getGraphContradictions(undefined, 10);
        contradictions = contrResult.contradictions;
        setState(s => ({
          ...s,
          contradictions,
          sources: { ...s.sources, contradictions: contrResult.source },
        }));
      } catch {
        contradictions = [];
      }

      setState(s => ({ ...s, phase: 'hypotheses' }));
      let hypotheses: Hypothesis[] = [];
      try {
        const hypResult = await generateGraphHypotheses();
        hypotheses = hypResult.hypotheses;
        setState(s => ({
          ...s,
          hypotheses,
          sources: { ...s.sources, hypotheses: hypResult.source },
        }));
      } catch {
        hypotheses = [];
      }

      setState(s => ({ ...s, phase: 'trends' }));
      let trends: Trend[] = [];
      try {
        trends = await getTrends();
        setState(s => ({ ...s, trends }));
      } catch {
        trends = [];
      }

      setState(s => ({ ...s, phase: 'done' }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setState(s => ({ ...s, phase: 'error', error: msg }));
    }
  }, []);

  const hasResults =
    state.gaps.length > 0 ||
    state.contradictions.length > 0 ||
    state.hypotheses.length > 0 ||
    state.trends.length > 0;

  const isRunning = !['idle', 'done', 'error'].includes(state.phase);

  const counts: Record<Tab, number> = {
    gaps: state.gaps.length,
    contradictions: state.contradictions.length,
    hypotheses: state.hypotheses.length,
    trends: state.trends.length,
  };

  return (
    <section className="relative min-h-screen overflow-hidden bg-black px-4 pb-16 pt-28 text-white md:px-10">
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.045]"
        style={{
          backgroundImage:
            'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
          backgroundSize: '54px 54px',
        }}
      />

      <div className="relative mx-auto max-w-7xl space-y-10">
        <header className="grid gap-8 border-b border-white/15 pb-10 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-5">
            <p className="text-xs font-semibold uppercase tracking-[0.4em] text-white/40">
              Discovery Engine
            </p>
            <h1 className="text-5xl font-black leading-none tracking-normal md:text-7xl">
              DISCOVERY
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-white/55 md:text-lg">
              Graph-native gap detection, contradiction mining, trend sensing, and hypothesis generation
              over the evidence extracted from uploaded research papers.
            </p>
          </div>

          <div className="hidden border border-white/15 bg-black/70 p-4 lg:block">
            <div className="mb-3 flex items-center justify-between border-b border-white/10 pb-3 text-[10px] uppercase tracking-[0.24em] text-white/45">
              <span>live graph map</span>
              <span>neo4j</span>
            </div>
            <div className="h-44">
              <MiniNetwork />
            </div>
          </div>
        </header>

        <div className="flex flex-wrap items-center justify-between gap-4 border-y border-white/15 py-5">
          <PhaseIndicator phase={state.phase} />

          <button
            id="run-discovery-btn"
            onClick={runAnalysis}
            disabled={isRunning}
            className={`border px-8 py-3 text-xs font-bold uppercase tracking-[0.18em] transition-colors disabled:cursor-not-allowed ${
              isRunning
                ? 'border-white/15 bg-white/5 text-white/35'
                : 'border-white bg-white text-black hover:bg-black hover:text-white'
            }`}
          >
            {isRunning ? 'Analyzing' : hasResults ? 'Re-run Analysis' : 'Run Discovery'}
          </button>
        </div>

        {isRunning && (
          <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
            {(['gaps', 'contradictions', 'hypotheses', 'trends'] as const).map(step => {
              const currentIdx = PHASE_ORDER.indexOf(state.phase);
              const stepIdx = PHASE_ORDER.indexOf(step);
              const done = currentIdx > stepIdx;
              const active = currentIdx === stepIdx;

              return (
                <div
                  key={step}
                  className={`border px-4 py-3 text-xs uppercase tracking-[0.18em] ${
                    done
                      ? 'border-white bg-white text-black'
                      : active
                        ? 'border-white text-white'
                        : 'border-white/15 text-white/35'
                  }`}
                >
                  <span className="font-mono">{String(stepIdx + 1).padStart(2, '0')}</span>
                  <span className="ml-3">{step}</span>
                </div>
              );
            })}
          </div>
        )}

        {hasResults && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatPill label="Gaps Found" value={state.gaps.length} />
            <StatPill label="Contradictions" value={state.contradictions.length} />
            <StatPill label="Hypotheses" value={state.hypotheses.length} />
            <StatPill label="Trends" value={state.trends.length} />
          </div>
        )}

        {state.phase === 'error' && (
          <div className="border border-red-400/40 bg-red-500/10 p-6">
            <p className="mb-1 text-sm font-semibold text-red-300">Analysis failed</p>
            <p className="text-sm text-red-200/70">{state.error}</p>
          </div>
        )}

        {!hasResults && state.phase === 'idle' && (
          <div className="border border-dashed border-white/20 bg-black/70 p-10 text-center md:p-16">
            <div className="mx-auto mb-8 h-32 max-w-xl border border-white/10 p-3">
              <MiniNetwork />
            </div>
            <h2 className="text-2xl font-bold text-white">Ready to discover</h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-white/45">
              Upload papers in the workspace, then run discovery to detect graph gaps, contradictions,
              emerging trends, and candidate hypotheses with traceable evidence.
            </p>
          </div>
        )}

        {hasResults && (
          <div className="space-y-8">
            <div className="flex flex-wrap gap-2 border-b border-white/15 pb-4">
              {TABS.map(tab => (
                <TabButton
                  key={tab.id}
                  label={tab.label}
                  count={counts[tab.id]}
                  active={activeTab === tab.id}
                  onClick={() => setActiveTab(tab.id)}
                />
              ))}
            </div>

            {activeTab === 'gaps' && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-2xl font-bold">Research Gaps</h2>
                  {state.sources.gaps && (
                    <span className="border border-white/15 px-3 py-1 text-xs uppercase tracking-[0.16em] text-white/45">
                      Source: {state.sources.gaps}
                    </span>
                  )}
                </div>
                {state.gaps.length === 0 ? (
                  <p className="border border-white/15 p-5 text-sm text-white/45">
                    No gaps detected. Try uploading more documents.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {state.gaps.map(gap => (
                      <GapCard key={gap.id} gap={gap} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'contradictions' && (
              <div className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="text-2xl font-bold">Contradiction Network</h2>
                  {state.sources.contradictions && (
                    <span className="border border-white/15 px-3 py-1 text-xs uppercase tracking-[0.16em] text-white/45">
                      Source: {state.sources.contradictions}
                    </span>
                  )}
                </div>

                <div className="border border-white/15 bg-black/70 p-6">
                  <p className="mb-4 text-xs uppercase tracking-[0.24em] text-white/40">
                    Force-directed contradiction graph
                  </p>
                  <ContradictionGraph contradictions={state.contradictions} />
                </div>

                {state.contradictions.length > 0 ? (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-white/55">
                      Contradiction Details
                    </h3>
                    {state.contradictions.map(c => (
                      <div key={c.id} className="space-y-4 border border-white/15 bg-black/70 p-5">
                        <div className="flex items-start justify-between gap-3">
                          <h4 className="text-sm font-semibold text-white/90">{c.title}</h4>
                          <span className="shrink-0 border border-white/20 px-2 py-1 text-xs uppercase tracking-[0.16em] text-white/55">
                            {c.severity}
                          </span>
                        </div>

                        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                          <div className="border border-white/10 bg-white/[0.03] p-3">
                            <p className="mb-1 text-xs uppercase tracking-[0.18em] text-white/35">
                              {c.doc_a || 'Claim A'}
                            </p>
                            <p className="text-sm text-white/75">{c.claim_a}</p>
                          </div>
                          <div className="border border-white/10 bg-white/[0.03] p-3">
                            <p className="mb-1 text-xs uppercase tracking-[0.18em] text-white/35">
                              {c.doc_b || 'Claim B'}
                            </p>
                            <p className="text-sm text-white/75">{c.claim_b}</p>
                          </div>
                        </div>

                        {c.explanation && (
                          <p className="border-t border-white/10 pt-3 text-sm leading-relaxed text-white/55">
                            {c.explanation}
                          </p>
                        )}

                        {c.resolution_hint && (
                          <p className="border-t border-white/10 pt-3 text-xs uppercase tracking-[0.14em] text-white/45">
                            Resolution: {c.resolution_hint}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="border border-white/15 p-5 text-sm text-white/45">
                    No contradictions found between documents.
                  </p>
                )}
              </div>
            )}

            {activeTab === 'hypotheses' && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h2 className="text-2xl font-bold">Generated Hypotheses</h2>
                    <p className="mt-1 text-sm text-white/40">
                      Candidate claims with rationale, novelty, feasibility, falsifiability, and validation plans.
                    </p>
                  </div>
                  {state.sources.hypotheses && (
                    <span className="border border-white/15 px-3 py-1 text-xs uppercase tracking-[0.16em] text-white/45">
                      Source: {state.sources.hypotheses}
                    </span>
                  )}
                </div>

                {state.hypotheses.length === 0 ? (
                  <p className="border border-white/15 p-5 text-sm text-white/45">
                    No hypotheses generated yet.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {state.hypotheses.map((hyp, i) => (
                      <HypothesisCard key={hyp.id} hypothesis={hyp} index={i} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'trends' && (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold">Trend Signals</h2>
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <div className="border border-white/15 bg-black/70 p-6">
                    <p className="mb-5 text-xs uppercase tracking-[0.24em] text-white/40">
                      Velocity Monitor
                    </p>
                    <TrendRadar trends={state.trends} />
                  </div>

                  <div className="space-y-4 border border-white/15 bg-black/70 p-6">
                    <p className="mb-4 text-xs uppercase tracking-[0.24em] text-white/40">
                      Signal Legend
                    </p>
                    {[
                      { key: 'Exploding', label: 'Exploding', desc: 'Massive rapid growth' },
                      { key: 'Rising', label: 'Rising', desc: 'Strong consistent growth' },
                      { key: 'Emerging', label: 'Emerging', desc: 'Early-stage growth signals' },
                      { key: 'Stable', label: 'Stable', desc: 'Established, steady field' },
                    ].map(v => (
                      <div key={v.key} className="flex items-center gap-3 border border-white/10 p-3">
                        <span className="h-3 w-3 shrink-0 border border-white bg-white" />
                        <div>
                          <p className="text-sm font-semibold text-white">{v.label}</p>
                          <p className="text-xs text-white/40">{v.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="border-t border-white/10 pt-8">
          <p className="mb-3 text-xs uppercase tracking-[0.24em] text-white/30">Powered by</p>
          <div className="flex flex-wrap gap-2">
            {[
              'Neo4j Graph DB',
              'Structural RAG',
              'LLM Navigation',
              'NLI Contradiction',
              'Claim Extraction',
              'Force Graph',
            ].map(label => (
              <span
                key={label}
                className="border border-white/15 px-3 py-1 text-xs uppercase tracking-[0.14em] text-white/45"
              >
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default DiscoveryPage;
