import React, { useEffect, useRef, useState } from 'react';
import type { Contradiction } from '../../services/discoveryService';

interface ContradictionGraphProps {
  contradictions: Contradiction[];
}

interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
}

interface GraphEdge {
  source: string;
  target: string;
  severity: 'high' | 'medium' | 'low';
  label: string;
}

const SEVERITY_COLOR: Record<string, string> = {
  high: '#ffffff',
  medium: '#bdbdbd',
  low: '#7a7a7a',
};

const ContradictionGraph: React.FC<ContradictionGraphProps> = ({ contradictions }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const animRef = useRef<number>(0);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; content: string } | null>(null);
  const nodesRef = useRef<GraphNode[]>([]);

  useEffect(() => {
    if (!contradictions.length) {
      setNodes([]);
      setEdges([]);
      nodesRef.current = [];
      return;
    }

    const nodeMap = new Map<string, GraphNode>();
    const newEdges: GraphEdge[] = [];
    const W = 600;
    const H = 400;

    contradictions.forEach(c => {
      const aId = c.claim_a.slice(0, 40);
      const bId = c.claim_b.slice(0, 40);

      if (!nodeMap.has(aId)) {
        nodeMap.set(aId, {
          id: aId,
          label: `${c.claim_a.slice(0, 35)}...`,
          x: 100 + Math.random() * (W - 200),
          y: 80 + Math.random() * (H - 160),
          vx: 0,
          vy: 0,
          radius: 10 + Math.min(c.score * 8, 10),
        });
      }

      if (!nodeMap.has(bId)) {
        nodeMap.set(bId, {
          id: bId,
          label: `${c.claim_b.slice(0, 35)}...`,
          x: 100 + Math.random() * (W - 200),
          y: 80 + Math.random() * (H - 160),
          vx: 0,
          vy: 0,
          radius: 10 + Math.min(c.score * 8, 10),
        });
      }

      newEdges.push({
        source: aId,
        target: bId,
        severity: c.severity,
        label: c.title,
      });
    });

    const newNodes = Array.from(nodeMap.values());
    setNodes(newNodes);
    setEdges(newEdges);
    nodesRef.current = newNodes;
  }, [contradictions]);

  useEffect(() => {
    if (!nodes.length) return;

    const W = 600;
    const H = 400;
    const REPULSION = 3000;
    const ATTRACTION = 0.04;
    const DAMPING = 0.85;

    const tick = () => {
      const ns = nodesRef.current.map(n => ({ ...n }));

      for (let i = 0; i < ns.length; i++) {
        for (let j = i + 1; j < ns.length; j++) {
          const dx = ns[i].x - ns[j].x;
          const dy = ns[i].y - ns[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = REPULSION / (dist * dist);
          ns[i].vx += (dx / dist) * force;
          ns[i].vy += (dy / dist) * force;
          ns[j].vx -= (dx / dist) * force;
          ns[j].vy -= (dy / dist) * force;
        }
      }

      edges.forEach(edge => {
        const src = ns.find(n => n.id === edge.source);
        const tgt = ns.find(n => n.id === edge.target);
        if (src && tgt) {
          const dx = tgt.x - src.x;
          const dy = tgt.y - src.y;
          src.vx += dx * ATTRACTION;
          src.vy += dy * ATTRACTION;
          tgt.vx -= dx * ATTRACTION;
          tgt.vy -= dy * ATTRACTION;
        }
      });

      ns.forEach(n => {
        n.vx *= DAMPING;
        n.vy *= DAMPING;
        n.x = Math.max(n.radius + 10, Math.min(W - n.radius - 10, n.x + n.vx));
        n.y = Math.max(n.radius + 10, Math.min(H - n.radius - 10, n.y + n.vy));
      });

      nodesRef.current = ns;
      setNodes([...ns]);
      animRef.current = requestAnimationFrame(tick);
    };

    animRef.current = requestAnimationFrame(tick);
    const timeout = setTimeout(() => cancelAnimationFrame(animRef.current), 4000);
    return () => {
      cancelAnimationFrame(animRef.current);
      clearTimeout(timeout);
    };
  }, [edges, nodes.length]);

  const getNodeById = (id: string) => nodes.find(n => n.id === id);

  if (!contradictions.length) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-white/40">
        No contradictions detected yet. Run analysis to populate the graph.
      </div>
    );
  }

  return (
    <div className="relative w-full">
      <svg
        ref={svgRef}
        viewBox="0 0 600 400"
        className="w-full border border-white/10 bg-black"
        style={{ maxHeight: 400 }}
      >
        {edges.map((edge, i) => {
          const src = getNodeById(edge.source);
          const tgt = getNodeById(edge.target);
          if (!src || !tgt) return null;
          const color = SEVERITY_COLOR[edge.severity] || '#8a8a8a';

          return (
            <g key={i}>
              <line
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke={color}
                strokeWidth={edge.severity === 'high' ? 2.5 : 1.5}
                strokeOpacity={0.65}
                strokeDasharray={edge.severity === 'low' ? '4 5' : undefined}
              />
              <text
                x={(src.x + tgt.x) / 2}
                y={(src.y + tgt.y) / 2 - 4}
                fill={color}
                fontSize={9}
                textAnchor="middle"
                opacity={0.75}
              >
                {edge.label.slice(0, 20)}
              </text>
            </g>
          );
        })}

        {nodes.map(node => {
          const isSelected = selected === node.id;
          const contradiction = contradictions.find(
            c => c.claim_a.slice(0, 40) === node.id || c.claim_b.slice(0, 40) === node.id
          );
          const color = contradiction ? SEVERITY_COLOR[contradiction.severity] || '#ffffff' : '#ffffff';

          return (
            <g
              key={node.id}
              style={{ cursor: 'pointer' }}
              onClick={() => setSelected(isSelected ? null : node.id)}
              onMouseEnter={e => {
                const svg = svgRef.current;
                if (!svg) return;
                const rect = svg.getBoundingClientRect();
                const scaleX = rect.width / 600;
                const scaleY = rect.height / 400;
                setTooltip({
                  x: node.x * scaleX,
                  y: node.y * scaleY - 20,
                  content: contradiction
                    ? `${contradiction.title}\n${contradiction.explanation}`
                    : node.label,
                });
              }}
              onMouseLeave={() => setTooltip(null)}
            >
              <circle
                cx={node.x}
                cy={node.y}
                r={node.radius + (isSelected ? 4 : 0)}
                fill={isSelected ? color : 'black'}
                stroke={color}
                strokeWidth={isSelected ? 2.5 : 1.4}
              />
              <circle
                cx={node.x}
                cy={node.y}
                r={node.radius + 8}
                fill="none"
                stroke={color}
                strokeOpacity={0.16}
              />
              <text
                x={node.x}
                y={node.y + node.radius + 13}
                fill="white"
                fontSize={8}
                textAnchor="middle"
                opacity={0.72}
              >
                {node.label.slice(0, 20)}
              </text>
            </g>
          );
        })}
      </svg>

      {tooltip && (
        <div
          className="absolute pointer-events-none z-10 max-w-xs border border-white/20 bg-black/95 p-2 text-xs text-white"
          style={{ left: tooltip.x + 8, top: tooltip.y }}
        >
          {tooltip.content.split('\n').map((line, i) => (
            <p key={i}>{line}</p>
          ))}
        </div>
      )}

      <div className="mt-3 flex gap-4 text-xs text-white/60">
        {Object.entries(SEVERITY_COLOR).map(([severity, color]) => (
          <span key={severity} className="flex items-center gap-1">
            <span className="inline-block h-3 w-3 border" style={{ borderColor: color, background: color }} />
            {severity}
          </span>
        ))}
        <span className="ml-auto text-white/40">Click nodes to inspect</span>
      </div>
    </div>
  );
};

export default ContradictionGraph;
