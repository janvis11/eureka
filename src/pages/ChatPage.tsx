import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DocumentRecord, fetchDocuments } from '../services/documentService';
import { submitChatQuery } from '../services/researchService';
import { ChatMessage } from '../types/api';

const titleStopWords = new Set([
  'the',
  'and',
  'for',
  'with',
  'from',
  'this',
  'that',
  'paper',
  'about',
  'what',
  'which',
  'does',
  'have',
  'need',
  'using',
  'use',
]);

const normalizeText = (value: string) =>
  value.toLowerCase().replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim();

const getTitleTokens = (value: string) =>
  normalizeText(value)
    .split(' ')
    .filter(token => token.length > 2 && !titleStopWords.has(token));

const findMentionedDocument = (prompt: string, documents: DocumentRecord[]) => {
  const promptTokens = new Set(getTitleTokens(prompt));
  const normalizedPrompt = normalizeText(prompt);

  const scored = documents
    .map(doc => {
      const titleTokens = getTitleTokens(doc.title);
      const overlap = titleTokens.filter(token => promptTokens.has(token)).length;
      const titlePhraseBonus =
        normalizedPrompt.includes('attention is all you need') &&
        normalizeText(doc.title).includes('attention is all you need')
          ? 4
          : 0;
      const bertBonus = promptTokens.has('bert') && getTitleTokens(doc.title).includes('bert') ? 3 : 0;
      return {
        doc,
        score: overlap + titlePhraseBonus + bertBonus,
      };
    })
    .filter(item => item.score >= 2)
    .sort((a, b) => b.score - a.score || b.doc.id - a.doc.id);

  return scored[0]?.doc;
};

const ChatNetwork = () => (
  <svg viewBox="0 0 420 210" className="h-full w-full" role="img" aria-label="RAG network preview">
    <path
      d="M32 150 C92 78 158 128 218 88 C280 46 326 76 392 48"
      fill="none"
      stroke="rgba(255,255,255,0.24)"
      strokeWidth="1"
      strokeDasharray="8 12"
      className="network-path"
    />
    <path
      d="M44 74 C104 110 142 40 198 74 C250 106 286 166 380 140"
      fill="none"
      stroke="rgba(255,255,255,0.12)"
      strokeWidth="1"
      strokeDasharray="4 14"
      className="network-path"
    />
    {[
      [42, 148, 'query'],
      [128, 100, 'chunk'],
      [210, 88, 'claim'],
      [290, 70, 'citation'],
      [382, 48, 'answer'],
      [382, 140, 'graph path'],
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

const ChatPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Ask about uploaded papers, gaps, hypotheses, trends, contradictions, or citations. I will answer from retrieved evidence.',
      createdAt: new Date().toISOString()
    }
  ]);
  const [prompt, setPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState(searchParams.get('document') ?? 'all');

  useEffect(() => {
    let isMounted = true;
    fetchDocuments()
      .then(docs => {
        if (isMounted) setDocuments(docs);
      })
      .catch(err => {
        if (isMounted) setDocumentsError(err instanceof Error ? err.message : 'Could not load papers.');
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    setSelectedDocumentId(searchParams.get('document') ?? 'all');
  }, [searchParams]);

  const orderedMessages = useMemo(
    () => [...messages].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()),
    [messages]
  );

  const completedDocuments = useMemo(
    () => documents.filter(document => document.status === 'completed'),
    [documents]
  );

  const selectedDocument = useMemo(
    () => completedDocuments.find(document => document.id === Number(selectedDocumentId)),
    [completedDocuments, selectedDocumentId]
  );

  const currentContextTitle = selectedDocument?.title ?? 'All processed papers';

  const handleDocumentSelect = (value: string) => {
    setSelectedDocumentId(value);
    const nextParams = new URLSearchParams(searchParams);
    if (value === 'all') {
      nextParams.delete('document');
    } else {
      nextParams.set('document', value);
    }
    setSearchParams(nextParams, { replace: true });
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!prompt.trim()) return;

    const explicitDocument = selectedDocumentId === 'all' ? undefined : selectedDocument;
    const matchedDocument = explicitDocument ? undefined : findMentionedDocument(prompt.trim(), completedDocuments);
    const scopedDocument = explicitDocument ?? matchedDocument;
    const contextTitle = scopedDocument?.title ?? 'All processed papers';
    const contextMode: ChatMessage['contextMode'] = explicitDocument
      ? 'selected'
      : matchedDocument
        ? 'matched'
        : 'corpus';

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: prompt.trim(),
      createdAt: new Date().toISOString(),
      contextDocumentId: scopedDocument?.id,
      contextTitle,
      contextMode,
    };

    setMessages((prev) => [...prev, userMessage]);
    setPrompt('');
    setIsSubmitting(true);
    setError(null);

    try {
      const response = await submitChatQuery(userMessage.content, scopedDocument?.id);
      setMessages((prev) => [
        ...prev,
        {
          ...response,
          contextDocumentId: scopedDocument?.id,
          contextTitle,
          contextMode,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get response. Please try again.');
      console.error('Chat error:', err);
    } finally {
      setIsSubmitting(false);
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
              Research Copilot
            </p>
            <h1 className="text-5xl font-black leading-none tracking-normal md:text-7xl">
              CHAT
            </h1>
            <p className="max-w-2xl text-base leading-relaxed text-white/55 md:text-lg">
              Ask your corpus questions and receive grounded answers with citations from processed papers,
              graph paths, and retrieved evidence.
            </p>
          </div>

          <div className="hidden border border-white/15 bg-black/70 p-4 lg:block">
            <div className="mb-3 flex items-center justify-between border-b border-white/10 pb-3 text-[10px] uppercase tracking-[0.24em] text-white/45">
              <span>retrieval route</span>
              <span>rag</span>
            </div>
            <div className="h-44">
              <ChatNetwork />
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="max-h-[68vh] space-y-6 overflow-y-auto border border-white/15 bg-black/70 p-5 md:p-8">
            {error && (
              <div className="border border-red-400/40 bg-red-500/10 p-4 text-sm text-red-200">
                {error}
              </div>
            )}

            {orderedMessages.map((message) => (
              <article key={message.id} className="border-b border-white/10 pb-5 last:border-b-0">
                <div className="mb-2 flex items-center gap-3">
                  <span className="border border-white/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/60">
                    {message.role}
                  </span>
                  <span className="font-mono text-[10px] text-white/35">
                    {new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                {message.contextTitle && (
                  <p className="mb-3 max-w-full break-words border border-white/15 bg-white/[0.03] px-3 py-2 text-xs text-white/55">
                    <span className="font-semibold uppercase tracking-[0.14em] text-white/35">Paper context</span>
                    <span className="ml-2 text-white/70">{message.contextTitle}</span>
                    {message.contextMode === 'matched' ? <span className="ml-2 text-white/35">matched from question</span> : null}
                    {message.contextMode === 'corpus' ? <span className="ml-2 text-white/35">corpus</span> : null}
                  </p>
                )}
                <p className="whitespace-pre-wrap leading-relaxed text-white/88">{message.content}</p>

                {message.citations && message.citations.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {message.citations.map((citation, index) => (
                      <a
                        key={`${citation.title}-${citation.url}-${index}`}
                        href={citation.url}
                        target="_blank"
                        rel="noreferrer"
                        className="border border-white/20 px-3 py-1 text-xs uppercase tracking-[0.12em] text-white/55 transition-colors hover:border-white hover:bg-white hover:text-black"
                      >
                        {citation.title}
                      </a>
                    ))}
                  </div>
                )}
              </article>
            ))}

            {isSubmitting && (
              <div className="animate-pulse space-y-3 border-b border-white/10 pb-5">
                <div className="h-5 w-28 bg-white/15" />
                <div className="h-4 w-full bg-white/10" />
                <div className="h-4 w-4/5 bg-white/10" />
              </div>
            )}
          </div>

          <aside className="border border-white/15 bg-black/80 p-5 md:p-6">
            <div className="mb-6 space-y-3 border-b border-white/10 pb-6">
              <label htmlFor="paper-context" className="text-xs font-bold uppercase tracking-[0.22em] text-white/55">
                Paper context
              </label>
              <select
                id="paper-context"
                value={selectedDocumentId}
                onChange={event => handleDocumentSelect(event.target.value)}
                className="w-full border border-white/15 bg-black p-3 text-sm text-white outline-none transition-colors focus:border-white"
              >
                <option value="all">All processed papers</option>
                {completedDocuments.map(document => (
                  <option key={document.id} value={document.id}>
                    {document.title}
                  </option>
                ))}
              </select>
              <div className="border border-white/10 bg-white/[0.03] p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/35">
                  Chatting about
                </p>
                <p className="mt-1 text-sm leading-relaxed text-white/70">{currentContextTitle}</p>
                {documentsError && <p className="mt-2 text-xs text-red-300">{documentsError}</p>}
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <label htmlFor="prompt" className="text-xs font-bold uppercase tracking-[0.22em] text-white/55">
                Ask a question
              </label>
              <textarea
                id="prompt"
                rows={7}
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="Which claims contradict across these papers?"
                className="w-full resize-none border border-white/15 bg-black p-4 text-sm text-white outline-none transition-colors placeholder:text-white/25 focus:border-white"
                aria-label="Research question input"
                disabled={isSubmitting}
              />
              <button
                type="submit"
                disabled={isSubmitting || !prompt.trim()}
                aria-label="Submit research question"
                className="w-full border border-white bg-white py-3 text-xs font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-black hover:text-white disabled:cursor-not-allowed disabled:border-white/15 disabled:bg-white/10 disabled:text-white/30"
              >
                {isSubmitting ? 'Analyzing' : 'Generate Insight'}
              </button>
            </form>

            <div className="mt-8 space-y-4 border-t border-white/10 pt-6 text-xs">
              <div>
                <p className="font-semibold uppercase tracking-[0.2em] text-white/55">Modes</p>
                <p className="mt-1 text-white/35">Literature / Knowledge Graph / Discovery</p>
              </div>
              <div>
                <p className="font-semibold uppercase tracking-[0.2em] text-white/55">Retrieval</p>
                <p className="mt-1 text-white/35">Evidence spans, citations, and graph context</p>
              </div>
              <div>
                <p className="font-semibold uppercase tracking-[0.2em] text-white/55">Governance</p>
                <p className="mt-1 text-white/35">Answers stay tied to source material</p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
};

export default ChatPage;
