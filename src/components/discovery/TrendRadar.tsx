import React from 'react';
import type { Trend } from '../../services/discoveryService';

interface TrendRadarProps {
  trends: Trend[];
}

const VELOCITY_COLOR: Record<string, string> = {
  Exploding: '#ffffff',
  Rising: '#d8d8d8',
  Emerging: '#ababab',
  Stable: '#7a7a7a',
};

const TrendRadar: React.FC<TrendRadarProps> = ({ trends }) => {
  if (!trends.length) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-white/40">
        No trends detected yet.
      </div>
    );
  }

  const normalized = trends.map((t, i) => ({
    id: t.id ?? String(i),
    label: t.title ?? t.entity_name ?? t.label ?? `Trend ${i + 1}`,
    velocity: t.velocity ?? (t.direction === 'up' ? 'Rising' : 'Emerging'),
    score: t.trend_score ?? (t.delta !== undefined ? t.delta / 100 : 0.5),
    docCount: t.document_count ?? 0,
    mentionCount: t.mention_count ?? 0,
  }));

  const maxScore = Math.max(...normalized.map(t => t.score), 1);

  return (
    <div className="space-y-3">
      {normalized.slice(0, 10).map(trend => {
        const color = VELOCITY_COLOR[trend.velocity] || '#8a8a8a';
        const barWidth = Math.round((trend.score / maxScore) * 100);

        return (
          <div key={trend.id} className="group">
            <div className="mb-1 flex items-center justify-between">
              <span className="mr-3 flex-1 truncate text-sm font-medium text-white/80">
                {trend.label}
              </span>
              <span
                className="shrink-0 border px-2 py-0.5 text-xs font-semibold uppercase tracking-[0.12em]"
                style={{ color, borderColor: `${color}66` }}
              >
                {trend.velocity}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden bg-white/10">
              <div
                className="h-full transition-all duration-700"
                style={{
                  width: `${barWidth}%`,
                  background: color,
                }}
              />
            </div>
            {(trend.docCount > 0 || trend.mentionCount > 0) && (
              <p className="mt-0.5 text-xs text-white/30">
                {trend.docCount > 0 && `${trend.docCount} docs`}
                {trend.docCount > 0 && trend.mentionCount > 0 && ' / '}
                {trend.mentionCount > 0 && `${trend.mentionCount} mentions`}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default TrendRadar;
