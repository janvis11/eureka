import React, { useState } from 'react';
import type { Hypothesis } from '../../services/discoveryService';
import { voteOnHypothesis } from '../../services/discoveryService';

interface HypothesisCardProps {
  hypothesis: Hypothesis;
  index: number;
}

const confidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return '#ffffff';
  if (confidence >= 0.6) return '#bdbdbd';
  return '#8a8a8a';
};

const HypothesisCard: React.FC<HypothesisCardProps> = ({ hypothesis, index }) => {
  const [votes, setVotes] = useState({
    up: hypothesis.votes_up,
    down: hypothesis.votes_down,
  });
  const [voted, setVoted] = useState<'up' | 'down' | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [voting, setVoting] = useState(false);

  const handleVote = async (dir: 'up' | 'down') => {
    if (voting || voted) return;
    setVoting(true);
    try {
      const res = await voteOnHypothesis(hypothesis.id, dir);
      setVotes({ up: res.votes_up, down: res.votes_down });
      setVoted(dir);
    } catch {
      setVotes(v => ({
        up: v.up + (dir === 'up' ? 1 : 0),
        down: v.down + (dir === 'down' ? 1 : 0),
      }));
      setVoted(dir);
    } finally {
      setVoting(false);
    }
  };

  const color = confidenceColor(hypothesis.confidence);
  const confidencePct = Math.round(hypothesis.confidence * 100);

  return (
    <article className="border border-white/15 bg-black/70 p-5 transition-colors duration-300 hover:border-white/35">
      <div className="mb-3 flex items-start justify-between gap-3">
        <span className="border border-white/20 px-2 py-1 font-mono text-xs font-bold text-white/65">
          H-{String(index + 1).padStart(2, '0')}
        </span>

        <div className="flex flex-wrap items-center justify-end gap-2 text-xs text-white/50">
          {hypothesis.source === 'neo4j_graph' && (
            <span className="border border-white/20 px-2 py-0.5 uppercase tracking-wider text-white/50">
              Neo4j graph
            </span>
          )}
          <span className="border border-white/15 px-2 py-0.5 uppercase tracking-wider">
            {hypothesis.status}
          </span>
        </div>
      </div>

      <p className="mb-4 text-sm font-medium leading-relaxed text-white/90">
        {hypothesis.text}
      </p>

      <div className="mb-4">
        <div className="mb-1 flex justify-between text-xs">
          <span className="text-white/50">Confidence</span>
          <span style={{ color }} className="font-semibold">
            {confidencePct}%
          </span>
        </div>
        <div className="h-1.5 overflow-hidden bg-white/10">
          <div
            className="h-full transition-all duration-700"
            style={{
              width: `${confidencePct}%`,
              background: color,
            }}
          />
        </div>
      </div>

      {expanded && (
        <div className="mb-4 space-y-3 text-sm">
          {hypothesis.rationale && <Detail label="Rationale" value={hypothesis.rationale} />}
          {hypothesis.methodology && <Detail label="Methodology" value={hypothesis.methodology} />}
          {hypothesis.expected_impact && <Detail label="Expected Impact" value={hypothesis.expected_impact} />}
          {hypothesis.novelty && <Detail label="Novelty" value={hypothesis.novelty} />}

          {(hypothesis.novelty_score || hypothesis.feasibility_score || hypothesis.falsifiability_score) && (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <Score label="Novelty" value={hypothesis.novelty_score} />
              <Score label="Feasible" value={hypothesis.feasibility_score} />
              <Score label="Falsifiable" value={hypothesis.falsifiability_score} />
            </div>
          )}

          {hypothesis.validation_plan && <Detail label="Validation Plan" value={hypothesis.validation_plan} />}

          {hypothesis.counter_evidence?.length ? (
            <Detail label="Counter-evidence" value={hypothesis.counter_evidence.join('; ')} />
          ) : null}

          {hypothesis.evidence_sources?.length ? (
            <div>
              <p className="mb-1 text-xs uppercase tracking-[0.2em] text-white/40">Evidence Sources</p>
              <div className="flex flex-wrap gap-1">
                {hypothesis.evidence_sources.map(src => (
                  <span key={src} className="border border-white/15 px-2 py-0.5 text-xs text-white/50">
                    {src}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-white/10 pt-3">
        <button
          onClick={() => setExpanded(e => !e)}
          className="border border-white/15 px-3 py-1.5 text-xs uppercase tracking-[0.14em] text-white/50 transition-colors hover:border-white/35 hover:text-white"
        >
          {expanded ? 'Collapse' : 'Details'}
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleVote('up')}
            disabled={!!voted || voting}
            title="Support this hypothesis"
            className={`border px-2.5 py-1 text-xs transition-colors ${
              voted === 'up'
                ? 'border-white bg-white text-black'
                : 'border-white/15 text-white/50 hover:border-white/40 hover:text-white'
            } disabled:cursor-not-allowed disabled:opacity-50`}
          >
            UP {votes.up}
          </button>

          <button
            onClick={() => handleVote('down')}
            disabled={!!voted || voting}
            title="Doubt this hypothesis"
            className={`border px-2.5 py-1 text-xs transition-colors ${
              voted === 'down'
                ? 'border-white bg-white text-black'
                : 'border-white/15 text-white/50 hover:border-white/40 hover:text-white'
            } disabled:cursor-not-allowed disabled:opacity-50`}
          >
            DOWN {votes.down}
          </button>
        </div>
      </div>
    </article>
  );
};

const Detail = ({ label, value }: { label: string; value: string }) => (
  <div>
    <p className="mb-1 text-xs uppercase tracking-[0.2em] text-white/40">{label}</p>
    <p className="leading-relaxed text-white/70">{value}</p>
  </div>
);

const Score = ({ label, value }: { label: string; value?: number }) => (
  <div className="border border-white/10 bg-white/[0.03] p-2">
    <p className="uppercase tracking-wider text-white/35">{label}</p>
    <p className="font-semibold text-white/80">{value === undefined ? '-' : `${Math.round(value * 100)}%`}</p>
  </div>
);

export default HypothesisCard;
