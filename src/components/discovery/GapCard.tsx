import React from 'react';
import type { ResearchGap } from '../../services/discoveryService';

interface GapCardProps {
  gap: ResearchGap;
}

const IMPACT_STYLES: Record<string, { badge: string; bar: string }> = {
  high: {
    badge: 'border-white bg-white text-black',
    bar: '#ffffff',
  },
  medium: {
    badge: 'border-white/25 bg-white/10 text-white',
    bar: '#bdbdbd',
  },
  low: {
    badge: 'border-white/20 bg-black text-white/55',
    bar: '#7a7a7a',
  },
};

const TYPE_CODE: Record<string, string> = {
  methodological: 'MTH',
  theoretical: 'THR',
  empirical: 'EMP',
  application: 'APP',
  knowledge_graph_gap: 'KGG',
};

const GapCard: React.FC<GapCardProps> = ({ gap }) => {
  const impact = gap.impact || 'medium';
  const styles = IMPACT_STYLES[impact] || IMPACT_STYLES.medium;
  const confidencePct = Math.round(gap.confidence * 100);
  const typeCode = TYPE_CODE[gap.type] || 'GAP';

  return (
    <div className="border border-white/15 bg-black/70 p-5 transition-colors duration-300 hover:border-white/35">
      <div className="mb-3 flex items-start gap-3">
        <span className="mt-0.5 border border-white/20 px-2 py-1 font-mono text-[10px] leading-none text-white/55">
          {typeCode}
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex items-center justify-between gap-2">
            <span className={`border px-2 py-0.5 text-xs font-semibold uppercase tracking-wider ${styles.badge}`}>
              {impact} impact
            </span>
            {gap.source === 'neo4j_graph' && (
              <span className="border border-white/20 px-2 py-0.5 text-xs uppercase tracking-wider text-white/50">
                Neo4j
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold leading-snug text-white">
            {gap.title}
          </h3>
        </div>
      </div>

      <p className="mb-4 text-sm leading-relaxed text-white/60">
        {gap.description}
      </p>

      {gap.entities?.length ? (
        <div className="mb-4 flex flex-wrap gap-1">
          {gap.entities.map(e => (
            <span key={e} className="border border-white/15 px-2 py-0.5 text-xs text-white/50">
              {e}
            </span>
          ))}
        </div>
      ) : null}

      <div>
        <div className="mb-1 flex justify-between text-xs text-white/40">
          <span>Confidence</span>
          <span style={{ color: styles.bar }}>{confidencePct}%</span>
        </div>
        <div className="h-1 overflow-hidden bg-white/10">
          <div
            className="h-full transition-all duration-700"
            style={{
              width: `${confidencePct}%`,
              background: styles.bar,
            }}
          />
        </div>
      </div>

      {gap.evidence_count ? (
        <p className="mt-2 text-xs text-white/35">
          {gap.evidence_count} document{gap.evidence_count !== 1 ? 's' : ''} as evidence
        </p>
      ) : null}
    </div>
  );
};

export default GapCard;
