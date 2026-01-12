import { useState } from 'react';
import { fetchHypotheses, voteOnHypothesis } from '../services/researchService';
import { useAsyncData } from '../hooks/useAsyncData';
import { Hypothesis } from '../types/api';

type VoteDelta = {
  up: number;
  down: number;
};

const HypothesisPage = () => {
  const { data, isLoading, error, refresh } = useAsyncData<Hypothesis[]>(fetchHypotheses, []);
  const [optimisticVotes, setOptimisticVotes] = useState<Record<string, VoteDelta>>({});

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

  return (
    <section className="pt-28 pb-16 px-6 md:px-12 bg-slate-950 min-h-screen">
      <div className="max-w-6xl mx-auto space-y-10">
        <header className="space-y-3 text-center">
          <p className="text-xs uppercase tracking-[0.3em] text-white/60">Hypothesis Hub</p>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight">AI-Proposed Research Theses</h1>
          <p className="text-lg text-white/60 max-w-3xl mx-auto">
            Every hypothesis is scored for novelty, feasibility, and supporting evidence. Vote to prioritize what gets
            explored next.
          </p>
        </header>

        {isLoading && <p className="text-white/60 text-center">Loading hypotheses...</p>}
        {error && (
          <div className="text-center text-red-400 space-y-2">
            <p>{error}</p>
            <button className="underline" onClick={() => refresh()}>
              Retry
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {data &&
            data.map((hypothesis) => {
              const voteDelta = optimisticVotes[hypothesis.id] ?? { up: 0, down: 0 };
              const votesUp = hypothesis.votesUp + voteDelta.up;
              const votesDown = hypothesis.votesDown + voteDelta.down;

              return (
                <article key={hypothesis.id} className="bg-white/5 border border-white/10 rounded-3xl p-6 space-y-4">
                  <div className="flex items-center justify-between text-xs uppercase tracking-widest text-white/60">
                    <span>{hypothesis.status.toUpperCase()}</span>
                    <span>Confidence {(hypothesis.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <h3 className="text-2xl font-semibold leading-snug">{hypothesis.text}</h3>
                  {hypothesis.rationale && <p className="text-sm text-white/70">{hypothesis.rationale}</p>}
                  <div className="space-y-1 text-xs text-white/60">
                    {hypothesis.methodology && (
                      <p>
                        <span className="font-semibold tracking-widest">Methodology:</span> {hypothesis.methodology}
                      </p>
                    )}
                    {hypothesis.expectedImpact && (
                      <p>
                        <span className="font-semibold tracking-widest">Impact:</span> {hypothesis.expectedImpact}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {hypothesis.entities.map((tag) => (
                      <span key={tag} className="text-xs px-3 py-1 border border-white/10 rounded-full">
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="text-sm text-white/60 space-y-0.5">
                      <p>Approvals: {votesUp}</p>
                      <p>Dismissals: {votesDown}</p>
                    </div>
                    <div className="space-x-3">
                      <button
                        className="px-3 py-1 border border-white/20 rounded-full text-xs uppercase tracking-widest"
                        onClick={() => handleVote(hypothesis.id, 'up')}
                      >
                        Approve
                      </button>
                      <button
                        className="px-3 py-1 border border-white/20 rounded-full text-xs uppercase tracking-widest"
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

export default HypothesisPage;

