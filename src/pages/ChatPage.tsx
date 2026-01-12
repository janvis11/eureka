import { FormEvent, useMemo, useState, useRef, useEffect } from 'react';
import { submitChatQuery } from '../services/researchService';
import { ChatMessage } from '../types/api';
import { MessageSkeleton } from '../components/LoadingSkeleton';

const ChatPage = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hi! I am your research co-pilot. Ask about gaps, hypotheses or trends, and I will respond with citations.',
      createdAt: new Date().toISOString()
    }
  ]);
  const [prompt, setPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const orderedMessages = useMemo(
    () => [...messages].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()),
    [messages]
  );

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!prompt.trim()) {
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: prompt.trim(),
      createdAt: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMessage]);
    setPrompt('');
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await submitChatQuery(userMessage.content);
      setMessages((prev) => [...prev, response]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get response. Please try again.');
      console.error('Chat error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="pt-28 pb-16 px-6 md:px-12 bg-slate-950 min-h-screen">
      <div className="max-w-6xl mx-auto space-y-12">
        <header className="space-y-4 text-center">
          <p className="text-sm uppercase tracking-[0.35em] text-white/60">Research Copilot</p>
          <h1 className="text-4xl md:text-6xl font-bold">Conversational Discovery</h1>
          <p className="text-lg text-white/60 max-w-3xl mx-auto">
            Ask complex questions and receive grounded responses with citations from 1M+ scientific documents.
          </p>
        </header>

        <div className="bg-black/40 border border-white/10 rounded-3xl p-6 md:p-10 grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 bg-white/5 rounded-3xl border border-white/5 p-4 md:p-8 space-y-6 max-h-[70vh] overflow-y-auto">
            {error && (
              <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-4 text-red-300 text-sm">
                {error}
              </div>
            )}
            {orderedMessages.map((message) => (
              <article key={message.id} className="space-y-2">
                <div className="flex items-center space-x-3">
                  <span className="text-xs font-semibold tracking-widest text-white/60">{message.role.toUpperCase()}</span>
                  <span className="text-[10px] text-white/40">
                    {new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <p className="text-white/90 leading-relaxed">{message.content}</p>
                {message.citations && message.citations.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {message.citations.map((citation) => (
                      <a
                        key={citation.url}
                        href={citation.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs px-3 py-1 border border-white/20 rounded-full hover:bg-white hover:text-black transition"
                      >
                        {citation.title}
                      </a>
                    ))}
                  </div>
                )}
              </article>
            ))}
            {isSubmitting && <MessageSkeleton />}
            <div ref={messagesEndRef} />
          </div>

          <aside className="bg-white text-black rounded-3xl p-6 flex flex-col justify-between space-y-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <label htmlFor="prompt" className="text-sm font-semibold tracking-wider">
                ASK A QUESTION
              </label>
              <textarea
                id="prompt"
                rows={5}
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="How is Eureka surfacing contradictions in CRISPR research?"
                className="w-full bg-black/5 border border-black/10 rounded-xl p-4 text-sm focus:border-black focus:ring-2 focus:ring-black/20 outline-none resize-none"
                aria-label="Research question input"
                disabled={isSubmitting}
              />
              <button
                type="submit"
                disabled={isSubmitting || !prompt.trim()}
                aria-label="Submit research question"
                className="w-full bg-black text-white rounded-xl py-3 font-semibold tracking-widest text-xs uppercase disabled:bg-black/40 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? 'Analyzing...' : 'Generate Insight'}
              </button>
            </form>

            <div className="text-xs space-y-3">
              <div>
                <p className="font-semibold tracking-widest">MODES</p>
                <p className="text-black/60">Literature • Knowledge Graph • Discovery</p>
              </div>
              <div>
                <p className="font-semibold tracking-widest">DATA FRESHNESS</p>
                <p className="text-black/60">Updated {new Date().toLocaleDateString()}</p>
              </div>
              <div>
                <p className="font-semibold tracking-widest">GOVERNANCE</p>
                <p className="text-black/60">Citations enforced • Bias monitoring active</p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
};

export default ChatPage;

