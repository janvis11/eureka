import { useState } from 'react';
import { fetchHypotheses, generateHypothesesFromGraph, voteOnHypothesis } from '../services/researchService';
import { useAsyncData } from '../hooks/useAsyncData';
import { Hypothesis } from '../types/api';

type VoteDelta = {
  up: number;
  down: number;
};

const HypothesisNetwork = () => (
  <svg viewBox="0 0 420 210" className="h-full w-full" role="img" aria-label="Hypothesis graph preview">
    <path
      d="M36 156 C96 96 142 128 200 86 C254 46 316 72 386 42"
      fill="none"
      stroke="rgba(255,255,255,0.24)"
      strokeWidth="1"
      strokeDasharray="8 12"
      className="network-path"
    />
    <path
      d="M46 62 C114 96 152 48 206 72 C256 94 292 158 378 136"
      fill="none"
      stroke="rgba(255,255,255,0.12)"
      strokeWidth="1"
      strokeDasharray="4 14"
      className="network-path"
    />
    {[
      [42, 154, 'gap'],
      [132, 104, 'evidence'],
      [210, 82, 'novelty'],
      [292, 72, 'validation'],
      [384, 42, 'hypothesis'],
      [378, 136, 'counter'],
    ].map(([cx, cy, label], index) => (
      <g key={`${cx}-${cy}`} className="network-node" style={{ animationDelay: `${index * 0.16}s` }}>
        <circle cx={Number(cx)} cy={Number(cy)} r="5" fill="black" stroke="white" strokeWidth="1.2" />
        <circle cx={Number(cx)} cy={Number(cy)} r="15" fill="none" stroke="rgba(255,255,255,0.12)" />
        <text x={Number(cx) + 12} y={Number(cy) - 10} fill="rgba(255,255,255,0.58)" fontSize="12">
          {label}
        </text>
      </g>
    ))}
  </svg>
);

const HypothesisPage = () => {
  const { data, isLoading, error, refresh } = useAsyncData<Hypothesis[]>(fetchHypotheses, []);
  const [optimisticVotes, setOptimisticVotes] = useState<Record<string, VoteDelta>>({});
  const [generated, setGenerated] = useState<Hypothesis[] | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const hypotheses = generated ?? data ?? [];

  const handleVote = async (id: string, direction: 'up' | 'down') => {
    setOptimisticVotes((prev: Record<string, VoteDelta>) => {
      const current = prev[id] ?? { up: 0, down: 0 };
      return {
        ...prev,
        [id]: {
          up: current.up + (direction === 'up' ? 1 : 0),
          down: current.down + (direction === 'down' ? 1 : 0)
        }
      };
    });

    await voteOnHypothesis(id, direction);
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerateError(null);
    try {
      const next = await generateHypothesesFromGraph();
      setGenerated(next);
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : 'Failed to generate hypotheses.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <section className="relative min-h-screen overflow-hidden bg-black px-4 pb-16 pt-28 text-white md:px-10">
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.035]"
        style={{
          backgroundImage:
            'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
          backgroundSize: '54px 54px'
        }}
      />

      <div className="relative mx-auto max-w-7xl space-y-8">
        <header className="grid gap-8 border-b border-white/15 pb-8 lg:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-5">
            <p className="text-xs font-semibold uppercase tracking-[0.4em] text-white/40">
              Hypothesis Engine
            </p>
            <h1 className="text-5xl font-black leading-none tracking-normal md:text-7xl">
              HYPOTHESIS
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-white/55 md:text-lg">
              Candidate research theses generated from graph paths, scored for evidence, counter-evidence,
              novelty, feasibility, falsifiability, and validation.
            </p>
          </div>

          <div className="hidden border border-white/15 bg-black/70 p-4 lg:block">
            <div className="mb-3 flex items-center justify-between border-b border-white/10 pb-3 text-[10px] uppercase tracking-[0.24em] text-white/45">
              <span>candidate map</span>
              <span>graph</span>
            </div>
            <div className="h-44">
              <HypothesisNetwork />
            </div>
          </div>
        </header>

        <div className="flex flex-wrap items-center justify-between gap-4 border-y border-white/15 py-5">
          <div className="text-xs uppercase tracking-[0.2em] text-white/45">
            <span className="font-mono text-white/65">{hypotheses.length.toString().padStart(2, '0')}</span>
            <span className="ml-3">candidate hypotheses</span>
          </div>

          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="border border-white bg-white px-6 py-3 text-xs font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-black hover:text-white disabled:cursor-not-allowed disabled:border-white/15 disabled:bg-white/10 disabled:text-white/30"
          >
            {isGenerating ? 'Generating' : 'Generate from Graph'}
          </button>
        </div>

        {isLoading && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {[0, 1, 2, 3].map(item => (
              <div key={item} className="animate-pulse border border-white/15 bg-black/70 p-6">
                <div className="mb-4 h-5 w-32 bg-white/15" />
                <div className="mb-3 h-6 w-full bg-white/10" />
                <div className="h-4 w-4/5 bg-white/10" />
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="border border-red-400/40 bg-red-500/10 p-5 text-sm text-red-200">
            <p>{error}</p>
            <button className="mt-3 border border-red-200/40 px-3 py-1 text-xs uppercase tracking-[0.16em]" onClick={() => refresh()}>
              Retry
            </button>
          </div>
        )}

        {generateError && (
          <div className="border border-red-400/40 bg-red-500/10 p-5 text-sm text-red-200">
            {generateError}
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {hypotheses.length === 0 && !isLoading && (
            <div className="border border-dashed border-white/20 bg-black/70 p-10 text-center text-white/55 md:col-span-2">
              <div className="mx-auto mb-8 h-32 max-w-xl border border-white/10 p-3">
                <HypothesisNetwork />
              </div>
              <h2 className="text-2xl font-bold text-white">No hypotheses yet</h2>
              <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-white/45">
                Upload and process papers, then generate hypotheses from the knowledge graph.
              </p>
            </div>
          )}

          {hypotheses.map((hypothesis, index) => {
            const voteDelta = optimisticVotes[hypothesis.id] ?? { up: 0, down: 0 };
            const votesUp = hypothesis.votesUp + voteDelta.up;
            const votesDown = hypothesis.votesDown + voteDelta.down;
            const confidencePct = Math.round(hypothesis.confidence * 100);

            return (
              <article key={hypothesis.id} className="space-y-4 border border-white/15 bg-black/70 p-6 transition-colors hover:border-white/35">
                <div className="flex items-start justify-between gap-4 text-xs uppercase tracking-[0.18em] text-white/55">
                  <span className="border border-white/20 px-2 py-1 font-mono text-white/65">
                    H-{String(index + 1).padStart(2, '0')}
                  </span>
                  <span>{hypothesis.status}</span>
                </div>

                <h3 className="text-2xl font-semibold leading-snug text-white">{hypothesis.text}</h3>

                {hypothesis.rationale && (
                  <p className="text-sm leading-relaxed text-white/65">{hypothesis.rationale}</p>
                )}

                <div>
                  <div className="mb-1 flex justify-between text-xs text-white/40">
                    <span>Confidence</span>
                    <span>{confidencePct}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden bg-white/10">
                    <div className="h-full bg-white transition-all duration-700" style={{ width: `${confidencePct}%` }} />
                  </div>
                </div>

                {(hypothesis.noveltyScore || hypothesis.feasibilityScore || hypothesis.falsifiabilityScore) && (
                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <Score label="Novelty" value={hypothesis.noveltyScore} />
                    <Score label="Feasible" value={hypothesis.feasibilityScore} />
                    <Score label="Falsifiable" value={hypothesis.falsifiabilityScore} />
                  </div>
                )}

                <div className="space-y-2 text-xs leading-relaxed text-white/55">
                  {hypothesis.methodology && <Detail label="Methodology" value={hypothesis.methodology} />}
                  {hypothesis.validationPlan && <Detail label="Validation" value={hypothesis.validationPlan} />}
                  {hypothesis.falsifiability && <Detail label="Falsifies If" value={hypothesis.falsifiability} />}
                  {hypothesis.expectedImpact && <Detail label="Impact" value={hypothesis.expectedImpact} />}
                </div>

                <div className="flex flex-wrap gap-2">
                  {hypothesis.entities.map((tag) => (
                    <span key={tag} className="border border-white/15 px-3 py-1 text-xs text-white/50">
                      {tag}
                    </span>
                  ))}
                </div>

                {hypothesis.counterEvidence && hypothesis.counterEvidence.length > 0 && (
                  <div className="border border-white/15 bg-white/[0.03] p-3 text-xs leading-relaxed text-white/55">
                    <span className="font-semibold uppercase tracking-[0.18em] text-white/65">Counter-evidence:</span>{' '}
                    {hypothesis.counterEvidence.join('; ')}
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-4">
                  <div className="space-y-0.5 text-sm text-white/50">
                    <p>Approvals: {votesUp}</p>
                    <p>Dismissals: {votesDown}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      className="border border-white/20 px-3 py-1.5 text-xs uppercase tracking-[0.16em] text-white/55 transition-colors hover:border-white hover:bg-white hover:text-black"
                      onClick={() => handleVote(hypothesis.id, 'up')}
                    >
                      Approve
                    </button>
                    <button
                      className="border border-white/20 px-3 py-1.5 text-xs uppercase tracking-[0.16em] text-white/55 transition-colors hover:border-white hover:bg-white hover:text-black"
                      onClick={() => handleVote(hypothesis.id, 'down')}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
};

const Detail = ({ label, value }: { label: string; value: string }) => (
  <p>
    <span className="font-semibold uppercase tracking-[0.18em] text-white/65">{label}:</span> {value}
  </p>
);

const Score = ({ label, value }: { label: string; value?: number }) => (
  <div className="border border-white/10 bg-white/[0.03] p-2">
    <p className="uppercase tracking-widest text-white/35">{label}</p>
    <p className="font-semibold text-white">{value === undefined ? '-' : `${Math.round(value * 100)}%`}</p>
  </div>
);

export default HypothesisPage;
