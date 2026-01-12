import { useEffect, useMemo, useRef, useState } from 'react';
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

const capabilities: Capability[] = [
  {
    number: '01',
    title: 'Conversational Research',
    description:
      'Natural language queries that understand context. Ask complex questions and receive comprehensive, cited answers from our curated knowledge base.',
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
      'Autonomous discovery of research opportunities. Our AI identifies gaps, contradictions, and emerging trends that human analysis might miss.',
    route: '/discovery'
  },
  {
    number: '04',
    title: 'Hypothesis Engine',
    description:
      'AI-generated research propositions validated by community consensus. Claim opportunities and contribute to collaborative scientific advancement.',
    route: '/hypothesis'
  }
];

const stats: Stat[] = [
  { value: '1M+', label: 'Research Papers', sublabel: 'Indexed & Analyzed' },
  { value: '500K+', label: 'Knowledge Links', sublabel: 'Mapped Relationships' },
  { value: '10K+', label: 'Discoveries', sublabel: 'Research Gaps Found' },
  { value: '99.9%', label: 'Accuracy', sublabel: 'Citation Precision' }
];

const LandingPage = () => {
  const navigate = useNavigate();
  const [scrollY, setScrollY] = useState(0);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handleScroll = () => setScrollY(window.scrollY);
    const handleMouseMove = (event: MouseEvent) => setMousePosition({ x: event.clientX, y: event.clientY });

    window.addEventListener('scroll', handleScroll);
    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  const parallaxOffset = useMemo(() => scrollY * 0.2, [scrollY]);

  return (
    <div ref={containerRef} className="min-h-screen bg-black text-white overflow-hidden">
      <div 
        className="fixed w-96 h-96 pointer-events-none z-0 blur-3xl opacity-30"
        style={{
          left: mousePosition.x - 192,
          top: mousePosition.y - 192,
          background: 'radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%)',
          transition: 'left 0.3s ease-out, top 0.3s ease-out'
        }}
      />

      {/* Hero Section - Experimental Layout */}
      <section className="relative min-h-screen flex items-center px-6 md:px-12 pt-24">
        {/* Decorative Elements */}
        <div className="absolute top-1/4 right-10 w-1 h-32 bg-white opacity-20"></div>
        <div className="absolute bottom-1/4 left-10 w-32 h-1 bg-white opacity-20"></div>
        
        {/* Rotating Square */}
        <div 
          className="absolute top-1/3 right-1/4 w-64 h-64 border border-white opacity-5"
          style={{
            transform: `rotate(${scrollY * 0.1}deg)`,
            transition: 'transform 0.1s linear'
          }}
        ></div>

        <div className="max-w-7xl mx-auto w-full">
          {/* Main Title - Asymmetric */}
          <div className="relative">
            <div className="absolute -left-4 top-0 text-white/5 text-[12rem] font-bold leading-none select-none">
              EUREKA
            </div>
            
            <div className="space-y-6">
              <div className="flex items-start space-x-4 mb-8">
                <div className="w-2 h-2 bg-white mt-8 animate-pulse"></div>
                <span className="text-xs tracking-[0.3em] uppercase text-gray-400 mt-6">
                  AI-Powered Research Platform
                </span>
              </div>

              <h1 className="text-[5rem] md:text-[8rem] lg:text-[12rem] font-bold leading-none tracking-tighter">
                EUREKA
              </h1>

              {/* Split Layout */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mt-16">
                <div className="space-y-8">
                  <div className="space-y-4">
                    <p className="text-2xl md:text-3xl text-white font-light leading-relaxed">
                      The difference between a<br/>
                      <span className="font-bold">search engine</span> and a<br/>
                      <span className="font-bold">research partner</span>
                    </p>
                    <p className="text-lg text-gray-400 leading-relaxed max-w-xl">
                      Traditional RAG systems only answer questions about what's already known. 
                      Eureka discovers what <span className="text-white font-semibold">could be known</span>.
                    </p>
                  </div>
                  
                  <div className="flex items-center space-x-8">
                    <button
                      onClick={() => navigate('/chat')}
                      className="group relative px-8 py-4 bg-white text-black font-bold text-sm uppercase tracking-wider overflow-hidden"
                    >
                      <span className="relative z-10">Initialize</span>
                      <div className="absolute inset-0 bg-gray-800 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
                      <span className="absolute inset-0 flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-opacity z-20">
                        Start →
                      </span>
                    </button>
                    
                    
                  </div>
                </div>

                {/* Visual Element - Large Abstract Shape */}
                <div className="relative h-96 hidden lg:block">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div 
                      className="relative w-full h-full"
                      style={{ transform: `translateY(${parallaxOffset}px)` }}
                    >
                      {/* Concentric Circles */}
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                        {[0, 1, 2, 3].map((i) => (
                          <div
                            key={i}
                            className="absolute border border-white/20 rounded-full"
                            style={{
                              width: `${(i + 1) * 80}px`,
                              height: `${(i + 1) * 80}px`,
                              left: `-${(i + 1) * 40}px`,
                              top: `-${(i + 1) * 40}px`,
                              animation: `rotate ${20 + i * 5}s linear infinite ${i % 2 === 0 ? 'reverse' : 'normal'}`
                            }}
                          >
                            <div className="absolute w-2 h-2 bg-white rounded-full top-0 left-1/2"></div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Problem Section */}
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
                  Thousands of papers published daily. It's physically impossible to read everything 
                  relevant to your field. Critical insights are buried in data you'll never see.
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
                  Research gaps, untested hypotheses, and emerging trends are invisible to human analysis. 
                  You're competing in a race where you can't see the track.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* What Makes Different Section */}
      <section className="py-32 px-6 md:px-12 bg-black text-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-5xl md:text-6xl font-bold mb-6 tracking-tight">
              WHAT MAKES EUREKA DIFFERENT
            </h2>
            <p className="text-xl text-gray-400 max-w-3xl mx-auto">
              Not another search engine. An autonomous discovery system that identifies 
              what you didn't know to look for.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-1">
            {[
              {
                num: "9",
                unit: "OF 10",
                title: "Advanced Features",
                desc: "Knowledge graphs, discovery agents, hypothesis generation, contradiction detection, and temporal analysis—all working together."
              },
              {
                num: "3",
                unit: "ENGINES",
                title: "Integrated Systems",
                desc: "RAG engine, knowledge graph, and discovery engine operating in concert to surface insights invisible to traditional methods."
              },
              {
                num: "∞",
                unit: "INSIGHTS",
                title: "Autonomous Discovery",
                desc: "AI agents continuously analyze patterns, identify gaps, and generate testable hypotheses while you sleep."
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

      {/* Capabilities Section - Grid Brutalist */}
      <section className="relative py-32 px-6 md:px-12 bg-white text-black">
        {/* Section Label */}
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

        {/* Grid Layout */}
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-1 border border-black">
            {capabilities.map((capability, index) => (
              <div
                key={index}
                className="group relative border border-black p-12 hover:bg-black hover:text-white transition-colors duration-500 cursor-pointer"
                onClick={() => navigate(capability.route)}
                style={{
                  minHeight: '400px'
                }}
              >
                {/* Number */}
                <div className="absolute top-0 left-0 p-4">
                  <span className="text-8xl font-bold opacity-5 group-hover:opacity-10">{capability.number}</span>
                </div>

                {/* Content */}
                <div className="relative z-10 h-full flex flex-col justify-between">
                  <div>
                    <h3 className="text-3xl font-bold mb-4 tracking-tight">{capability.title}</h3>
                    <p className="text-sm leading-relaxed opacity-70 max-w-md">
                      {capability.description}
                    </p>
                  </div>

                  {/* Arrow */}
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

      {/* Stats Section - Horizontal Scroll */}
      <section className="py-32 px-6 md:px-12 bg-black text-white border-y border-white/20">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center space-x-4 mb-12">
            <div className="w-12 h-12 border-2 border-white flex items-center justify-center">
              <span className="text-xs font-bold">03</span>
            </div>
            <h2 className="text-4xl md:text-6xl font-bold tracking-tight">METRICS</h2>
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

      {/* Process Section - Vertical Timeline */}
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
                desc: 'Continuous ingestion of research papers with state-of-the-art NLP processing and semantic embedding generation.' 
              },
              { 
                num: '02', 
                title: 'GRAPH CONSTRUCTION', 
                desc: 'Automated extraction of entities and relationships, building a living knowledge graph with temporal awareness.' 
              },
              { 
                num: '03', 
                title: 'PATTERN ANALYSIS', 
                desc: 'Multi-agent systems continuously analyze for gaps, contradictions, and emerging patterns across domains.' 
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

      {/* CTA Section - Full Width */}
      <section className="relative py-48 px-6 md:px-12 bg-black text-white overflow-hidden">
        {/* Animated Grid Background */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute inset-0" style={{
            backgroundImage: 'linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)',
            backgroundSize: '50px 50px'
          }}></div>
        </div>

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <h2 className="text-5xl md:text-7xl font-bold mb-8 tracking-tighter">
            START<br />
            DISCOVERING
          </h2>
          <p className="text-xl text-gray-400 mb-12 font-light max-w-2xl mx-auto">
            Join researchers using AI to uncover what traditional methods miss
          </p>
          <button
            onClick={() => navigate('/chat')}
            className="group relative px-12 py-6 bg-white text-black font-bold text-lg uppercase tracking-wider overflow-hidden inline-block"
          >
            <span className="relative z-10">Initialize System</span>
            <div className="absolute inset-0 bg-gray-300 transform translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
          </button>
        </div>

        {/* Decorative Elements */}
        <div className="absolute bottom-10 left-10 w-24 h-24 border border-white/20"></div>
        <div className="absolute top-10 right-10 w-32 h-32 border border-white/20"></div>
      </section>

    </div>
  );
};

export default LandingPage;
