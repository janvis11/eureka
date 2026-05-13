import { useNavigate } from 'react-router-dom';

type Capability = {
  number: string;
  title: string;
  description: string;
  route: string;
};

type Stat = {
  value: string;
  label: string;
  sublabel: string;
};

type GraphNode = {
  id: string;
  label: string;
  x: number;
  y: number;
  radius: number;
  kind: 'source' | 'evidence' | 'signal' | 'core';
};

type GraphEdge = {
  from: string;
  to: string;
  weight: number;
};

const capabilities: Capability[] = [
  {
    number: '01',
    title: 'Conversational Research',
    description:
      'Natural language queries that understand context. Ask complex questions and receive comprehensive, cited answers from your processed papers.',
    route: '/chat'
  },
  {
    number: '02',
    title: 'Network Intelligence',
    description:
      'Interactive visualization of research relationships. Discover non-obvious connections between concepts, methodologies, and findings across domains.',
    route: '/knowledge-graph'
  },
  {
    number: '03',
    title: 'Pattern Recognition',
    description:
      'Autonomous discovery of research opportunities. Eureka identifies gaps, contradictions, and emerging trends that human analysis might miss.',
    route: '/discovery'
  },
  {
    number: '04',
    title: 'Hypothesis Engine',
    description:
      'AI-generated research propositions with evidence, counter-evidence, feasibility, falsifiability, and validation plans.',
    route: '/hypothesis'
  }
];

const stats: Stat[] = [
  { value: 'PDF', label: 'Paper Uploads', sublabel: 'Ingest & Process' },
  { value: 'KG', label: 'Knowledge Graph', sublabel: 'Mapped Relationships' },
  { value: 'RAG', label: 'Evidence Answers', sublabel: 'Cited Retrieval' },
  { value: 'HYP', label: 'Hypotheses', sublabel: 'Validation Ready' }
];

const discoveryGraphNodes: GraphNode[] = [
  { id: 'corpus', label: 'corpus', x: 140, y: 470, radius: 6, kind: 'source' },
  { id: 'paper-a', label: 'paper A', x: 250, y: 210, radius: 5, kind: 'source' },
  { id: 'paper-b', label: 'paper B', x: 355, y: 390, radius: 5, kind: 'source' },
  { id: 'method', label: 'method', x: 470, y: 130, radius: 6, kind: 'evidence' },
  { id: 'claim', label: 'claim', x: 495, y: 500, radius: 5, kind: 'evidence' },
  { id: 'gap', label: 'gap', x: 640, y: 170, radius: 6, kind: 'signal' },
  { id: 'unseen', label: 'unseen concept', x: 660, y: 330, radius: 10, kind: 'core' },
  { id: 'evidence', label: 'evidence', x: 770, y: 520, radius: 5, kind: 'evidence' },
  { id: 'contradiction', label: 'contradiction', x: 855, y: 200, radius: 6, kind: 'signal' },
  { id: 'trend', label: 'trend', x: 975, y: 410, radius: 5, kind: 'signal' },
  { id: 'hypothesis', label: 'hypothesis', x: 1125, y: 250, radius: 6, kind: 'signal' }
];

const discoveryGraphEdges: GraphEdge[] = [
  { from: 'corpus', to: 'paper-a', weight: 0.5 },
  { from: 'corpus', to: 'paper-b', weight: 0.45 },
  { from: 'paper-a', to: 'method', weight: 0.6 },
  { from: 'paper-a', to: 'gap', weight: 0.74 },
  { from: 'paper-b', to: 'claim', weight: 0.62 },
  { from: 'method', to: 'unseen', weight: 0.82 },
  { from: 'claim', to: 'unseen', weight: 0.78 },
  { from: 'gap', to: 'unseen', weight: 0.9 },
  { from: 'unseen', to: 'evidence', weight: 0.7 },
  { from: 'unseen', to: 'contradiction', weight: 0.84 },
  { from: 'contradiction', to: 'hypothesis', weight: 0.66 },
  { from: 'evidence', to: 'trend', weight: 0.58 },
  { from: 'trend', to: 'hypothesis', weight: 0.76 },
  { from: 'gap', to: 'hypothesis', weight: 0.52 }
];

const graphNodeById = new Map(discoveryGraphNodes.map((node) => [node.id, node]));

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      <div
        className="fixed inset-0 pointer-events-none opacity-[0.025]"
        style={{
          backgroundImage:
            'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
          backgroundSize: '48px 48px'
        }}
      />

      <section className="relative h-[100svh] min-h-[600px] overflow-hidden px-4 md:min-h-[640px] md:px-10">
        <div
          className="absolute inset-0 opacity-[0.035]"
          style={{
            backgroundImage:
              'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
            backgroundSize: '54px 54px'
          }}
        />
        <div className="absolute top-24 left-0 right-0 z-20 flex justify-center">
          <div className="border border-white/10 bg-black/80 px-5 py-1.5 backdrop-blur-sm">
            <h1 className="text-3xl font-black tracking-normal md:text-4xl">eureka.ai</h1>
          </div>
        </div>

        <div className="absolute left-4 right-4 top-44 bottom-8 z-10 md:left-10 md:right-10">
          <div className="absolute inset-0 border border-white/10" />
          <div className="absolute inset-x-0 top-1/2 h-px bg-white/[0.06]" />
          <div className="absolute inset-y-0 left-1/2 w-px bg-white/[0.06]" />
          <div className="absolute left-0 right-0 top-0 h-12 bg-gradient-to-b from-black to-transparent" />
          <div className="absolute left-0 right-0 bottom-0 h-12 bg-gradient-to-t from-black to-transparent" />

          <div
            className="absolute inset-0 network-scanline pointer-events-none"
            aria-hidden="true"
          />

          <svg
            viewBox="40 40 1200 530"
            className="absolute inset-0 h-full w-full"
            preserveAspectRatio="xMidYMid meet"
            role="img"
            aria-label="Research discovery graph connecting papers, evidence, gaps, and hypotheses"
          >
            <defs>
              <filter id="networkGlow">
                <feGaussianBlur stdDeviation="2.4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {[
              'M92 132 C222 78 337 146 430 232 C535 329 629 302 726 214 C858 95 1006 110 1172 178',
              'M88 506 C238 442 356 536 496 488 C617 447 610 275 736 265 C877 253 908 487 1192 424',
              'M166 318 C314 228 432 282 548 346 C679 419 779 367 884 296 C981 231 1088 242 1184 300'
            ].map((d, index) => (
              <path
                key={d}
                d={d}
                className="network-path"
                style={{ animationDelay: `${index * 0.65}s` }}
                fill="none"
                stroke="rgba(255,255,255,0.09)"
                strokeWidth="1"
                strokeDasharray="6 18"
              />
            ))}

            {discoveryGraphEdges.map((edge, index) => {
              const from = graphNodeById.get(edge.from);
              const to = graphNodeById.get(edge.to);

              if (!from || !to) {
                return null;
              }

              return (
                <g key={`${edge.from}-${edge.to}`}>
                  <line
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    className="network-edge"
                    style={{ animationDelay: `${index * 0.22}s` }}
                    stroke={edge.weight > 0.75 ? 'rgba(255,255,255,0.34)' : 'rgba(255,255,255,0.14)'}
                    strokeWidth={edge.weight > 0.75 ? 1.25 : 0.8}
                    strokeDasharray={edge.weight > 0.75 ? '10 12' : '3 12'}
                  />
                  {index % 2 === 0 && (
                    <circle r="3.2" fill="white" opacity="0.52">
                      <animateMotion
                        dur={`${8 + index * 0.45}s`}
                        repeatCount="indefinite"
                        path={`M${from.x} ${from.y} L${to.x} ${to.y}`}
                      />
                    </circle>
                  )}
                </g>
              );
            })}

            {[86, 142, 204].map((radius, index) => (
              <circle
                key={radius}
                cx="660"
                cy="330"
                r={radius}
                fill="none"
                stroke="rgba(255,255,255,0.075)"
                strokeDasharray={index === 0 ? '2 10' : '6 16'}
                className="network-ring"
              />
            ))}

            {discoveryGraphNodes.map((node, index) => {
              const isCore = node.kind === 'core';
              const labelX = node.x > 1040 ? node.x - 16 : node.x + 16;
              const labelAnchor = node.x > 1040 ? 'end' : 'start';

              return (
                <g
                  key={node.id}
                  className={isCore ? 'network-core' : 'network-node'}
                  style={{ animationDelay: `${index * 0.15}s` }}
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={isCore ? 42 : node.radius + 14}
                    fill="black"
                    stroke={isCore ? 'rgba(255,255,255,0.24)' : 'rgba(255,255,255,0.11)'}
                    strokeDasharray={isCore ? '5 12' : undefined}
                  />
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={isCore ? node.radius + 2 : node.radius + 1}
                    fill={isCore ? 'white' : 'black'}
                    stroke="white"
                    strokeWidth={isCore ? 2 : 1.4}
                    filter="url(#networkGlow)"
                  />
                  {isCore ? (
                    <>
                      <text x={node.x} y={node.y - 62} textAnchor="middle" fill="rgba(255,255,255,0.86)" fontSize="19">
                        unseen concept
                      </text>
                      <text x={node.x} y={node.y + 76} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="15">
                        candidate discovery
                      </text>
                    </>
                  ) : (
                    <text
                      x={labelX}
                      y={node.y - 12}
                      textAnchor={labelAnchor}
                      fill="rgba(255,255,255,0.62)"
                      fontSize="16"
                    >
                      {node.label}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

        </div>
      </section>

      <section className="py-32 px-6 md:px-12 bg-white text-black border-t-2 border-black">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
            <div>
              <div className="flex items-center space-x-4 mb-8">
                <div className="w-12 h-12 border-2 border-black flex items-center justify-center">
                  <span className="text-xs font-bold">01</span>
                </div>
                <h2 className="text-5xl font-bold tracking-tight">THE PROBLEM</h2>
              </div>

              <p className="text-xl text-gray-600 leading-relaxed mb-8">
                Researchers face three critical challenges that traditional tools cannot solve:
              </p>
            </div>

            <div className="space-y-8">
              <div className="border-l-4 border-black pl-6">
                <h3 className="text-2xl font-bold mb-3">Information Overload</h3>
                <p className="text-gray-600 leading-relaxed">
                  Thousands of papers published daily. It is physically impossible to read everything
                  relevant to your field. Critical insights are buried in data you will never see.
                </p>
              </div>

              <div className="border-l-4 border-black pl-6">
                <h3 className="text-2xl font-bold mb-3">Siloed Knowledge</h3>
                <p className="text-gray-600 leading-relaxed">
                  Breakthrough connections often exist between disparate fields but remain undiscovered.
                  The next major innovation could be hiding in the gap between two domains.
                </p>
              </div>

              <div className="border-l-4 border-black pl-6">
                <h3 className="text-2xl font-bold mb-3">Hidden Opportunities</h3>
                <p className="text-gray-600 leading-relaxed">
                  Research gaps, untested hypotheses, and emerging trends are invisible to manual analysis.
                  Eureka makes those hidden directions inspectable.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-32 px-6 md:px-12 bg-black text-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-5xl md:text-6xl font-bold mb-6 tracking-tight">
              WHAT MAKES EUREKA DIFFERENT
            </h2>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto">
              Not another search engine. An autonomous discovery system that identifies
              what you did not know to look for.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-1">
            {[
              {
                num: '9',
                unit: 'OF 10',
                title: 'Advanced Features',
                desc: 'Knowledge graphs, discovery agents, hypothesis generation, contradiction detection, and temporal analysis working together.'
              },
              {
                num: '3',
                unit: 'ENGINES',
                title: 'Integrated Systems',
                desc: 'RAG engine, knowledge graph, and discovery engine operating in concert to surface insights invisible to traditional methods.'
              },
              {
                num: 'AI',
                unit: 'DISCOVERY',
                title: 'Autonomous Discovery',
                desc: 'Agents analyze patterns, identify gaps, and generate testable hypotheses from uploaded research evidence.'
              }
            ].map((item, idx) => (
              <div key={idx} className="border border-white/20 p-12 hover:bg-white hover:text-black transition-colors duration-300">
                <div className="text-6xl font-bold mb-2">{item.num}</div>
                <div className="text-sm font-bold tracking-wider mb-6 opacity-70">{item.unit}</div>
                <h3 className="text-2xl font-bold mb-4">{item.title}</h3>
                <p className="text-sm leading-relaxed opacity-80">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative py-32 px-6 md:px-12 bg-white text-black">
        <div className="max-w-7xl mx-auto mb-20">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 border-2 border-black flex items-center justify-center">
              <span className="text-xs font-bold">02</span>
            </div>
            <div>
              <h2 className="text-4xl md:text-6xl font-bold tracking-tight">CAPABILITIES</h2>
              <p className="text-gray-500 text-sm mt-2">FOUR CORE SYSTEMS</p>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-1 border border-black">
            {capabilities.map((capability, index) => (
              <div
                key={index}
                className="group relative border border-black p-12 hover:bg-black hover:text-white transition-colors duration-500 cursor-pointer"
                onClick={() => navigate(capability.route)}
                style={{ minHeight: '400px' }}
              >
                <div className="absolute top-0 left-0 p-4">
                  <span className="text-8xl font-bold opacity-5 group-hover:opacity-10">{capability.number}</span>
                </div>

                <div className="relative z-10 h-full flex flex-col justify-between">
                  <div>
                    <h3 className="text-3xl font-bold mb-4 tracking-tight">{capability.title}</h3>
                    <p className="text-sm leading-relaxed opacity-70 max-w-md">
                      {capability.description}
                    </p>
                  </div>

                  <div className="flex justify-end mt-8">
                    <div className="w-12 h-12 border border-current flex items-center justify-center group-hover:bg-white group-hover:text-black transition-all">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-32 px-6 md:px-12 bg-black text-white border-y border-white/20">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center space-x-4 mb-12">
            <div className="w-12 h-12 border-2 border-white flex items-center justify-center">
              <span className="text-xs font-bold">03</span>
            </div>
            <h2 className="text-4xl md:text-6xl font-bold tracking-tight">SYSTEMS</h2>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-1">
            {stats.map((stat, index) => (
              <div key={index} className="border border-white/20 p-8 text-center hover:bg-white hover:text-black transition-colors duration-300">
                <div className="text-5xl md:text-6xl font-bold mb-2">{stat.value}</div>
                <div className="text-sm font-semibold uppercase tracking-wider">{stat.label}</div>
                <div className="text-xs opacity-50 mt-1">{stat.sublabel}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-32 px-6 md:px-12 bg-white text-black">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center space-x-4 mb-20">
            <div className="w-12 h-12 border-2 border-black flex items-center justify-center">
              <span className="text-xs font-bold">04</span>
            </div>
            <div>
              <h2 className="text-4xl md:text-6xl font-bold tracking-tight">ARCHITECTURE</h2>
              <p className="text-gray-500 text-sm mt-2">THREE-STAGE PIPELINE</p>
            </div>
          </div>

          <div className="space-y-24">
            {[
              {
                num: '01',
                title: 'INGEST & PROCESS',
                desc: 'Upload research papers, extract structure, chunk evidence, and generate embeddings for retrieval.'
              },
              {
                num: '02',
                title: 'GRAPH CONSTRUCTION',
                desc: 'Extract concepts, claims, and provenance-backed relationships into a living Neo4j knowledge graph.'
              },
              {
                num: '03',
                title: 'PATTERN ANALYSIS',
                desc: 'Discovery agents analyze gaps, contradictions, bridges, trends, and falsifiable hypotheses.'
              }
            ].map((item, index) => (
              <div key={index} className="flex items-start space-x-8 border-l-2 border-black pl-8">
                <div className="text-6xl font-bold opacity-20">{item.num}</div>
                <div className="flex-1">
                  <h3 className="text-2xl font-bold mb-3 tracking-tight">{item.title}</h3>
                  <p className="text-gray-600 leading-relaxed max-w-xl">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative py-48 px-6 md:px-12 bg-black text-white overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: 'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
              backgroundSize: '50px 50px'
            }}
          ></div>
        </div>

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h2 className="text-5xl md:text-7xl font-bold mb-8 tracking-tighter">
            START<br />
            DISCOVERING
          </h2>
          <p className="text-xl text-gray-400 mb-12 font-light max-w-2xl mx-auto">
            Upload papers and turn unread literature into graphs, gaps, hypotheses, and cited answers.
          </p>
          <button
            onClick={() => navigate('/workspace')}
            className="group relative px-12 py-6 bg-white text-black font-bold text-lg uppercase tracking-wider overflow-hidden inline-block"
          >
            <span className="relative z-10">Initialize System</span>
            <div className="absolute inset-0 bg-gray-300 transform translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
          </button>
        </div>

        <div className="absolute bottom-10 left-10 w-24 h-24 border border-white/20"></div>
        <div className="absolute top-10 right-10 w-32 h-32 border border-white/20"></div>
      </section>
    </div>
  );
};

export default LandingPage;
