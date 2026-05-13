import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  deleteDocument,
  DocumentRecord,
  DocumentStats,
  fetchDocumentStats,
  fetchDocuments,
  uploadDocuments,
} from '../services/documentService';
import { fetchGraphStats, submitChatQuery } from '../services/researchService';
import { ChatMessage, GraphStats } from '../types/api';

const WorkspacePage = () => {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [docStats, setDocStats] = useState<DocumentStats | null>(null);
  const [graphStats, setGraphStats] = useState<GraphStats | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState<ChatMessage | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [paperActionError, setPaperActionError] = useState<string | null>(null);
  const [deletingDocumentId, setDeletingDocumentId] = useState<number | null>(null);

  const loadWorkspace = async () => {
    setIsLoading(true);
    try {
      const [docs, stats, graph] = await Promise.all([
        fetchDocuments(),
        fetchDocumentStats(),
        fetchGraphStats().catch(() => null),
      ]);
      setDocuments(docs);
      setDocStats(stats);
      setGraphStats(graph);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, []);

  useEffect(() => {
    const hasProcessing = documents.some(doc => doc.status === 'pending' || doc.status === 'processing');
    if (!hasProcessing) return undefined;

    const timer = window.setInterval(() => {
      loadWorkspace();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [documents]);

  const metrics = useMemo(() => {
    const completed = documents.filter(doc => doc.status === 'completed').length;
    const processing = documents.filter(doc => doc.status === 'pending' || doc.status === 'processing').length;
    const chunks = docStats?.vector_store.total_chunks ?? documents.reduce((sum, doc) => sum + doc.chunk_count, 0);
    const graphNodes = graphStats?.nodes ?? docStats?.knowledge_graph.nodes ?? 0;

    return [
      { label: 'Papers', value: documents.length.toLocaleString(), detail: `${completed} completed` },
      { label: 'Processing', value: processing.toLocaleString(), detail: 'background jobs' },
      { label: 'Chunks', value: chunks.toLocaleString(), detail: 'retrievable evidence' },
      { label: 'Graph Nodes', value: graphNodes.toLocaleString(), detail: 'documents, concepts, claims' },
    ];
  }, [docStats, documents, graphStats]);

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedFiles(Array.from(event.target.files ?? []).filter(file => file.name.toLowerCase().endsWith('.pdf')));
    setUploadError(null);
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadError(null);
    try {
      await uploadDocuments(selectedFiles);
      setSelectedFiles([]);
      await loadWorkspace();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleAsk = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;

    setIsAsking(true);
    setQueryError(null);
    try {
      const response = await submitChatQuery(query.trim());
      setAnswer(response);
    } catch (err) {
      setAnswer(null);
      setQueryError(err instanceof Error ? err.message : 'Query failed.');
    } finally {
      setIsAsking(false);
    }
  };

  const handleDeletePaper = async (doc: DocumentRecord) => {
    const confirmed = window.confirm(`Delete "${doc.title}" from this workspace?`);
    if (!confirmed) return;

    setDeletingDocumentId(doc.id);
    setPaperActionError(null);
    try {
      await deleteDocument(doc.id);
      setDocuments(prev => prev.filter(item => item.id !== doc.id));
      await loadWorkspace();
    } catch (err) {
      setPaperActionError(err instanceof Error ? err.message : 'Could not delete this paper.');
    } finally {
      setDeletingDocumentId(null);
    }
  };

  return (
    <section className="min-h-screen bg-black text-white pt-28 pb-16 px-6 md:px-12">
      <div className="max-w-7xl mx-auto space-y-10">
        <header className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-8 items-end">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.35em] text-white/50">Eureka Research Workspace</p>
            <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-none">
              Discover what your papers do not say directly.
            </h1>
            <p className="text-lg text-white/60 max-w-3xl">
              Upload research papers, build a provenance graph, ask structural RAG questions, surface gaps,
              contradictions, trends, and generate falsifiable hypotheses.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {metrics.map(metric => (
              <div key={metric.label} className="border border-white/10 bg-white/5 rounded-xl p-4">
                <p className="text-3xl font-bold">{isLoading ? '-' : metric.value}</p>
                <p className="text-xs uppercase tracking-widest text-white/50">{metric.label}</p>
                <p className="text-xs text-white/35 mt-1">{metric.detail}</p>
              </div>
            ))}
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-[0.95fr_1.05fr] gap-6">
          <section className="border border-white/10 bg-white/5 rounded-xl p-6 space-y-5">
            <div>
              <p className="text-xs uppercase tracking-widest text-white/45">Ingest Papers</p>
              <h2 className="text-2xl font-bold mt-1">Upload PDFs</h2>
            </div>
            <label className="block border border-dashed border-white/20 rounded-xl p-6 cursor-pointer hover:bg-white/5 transition">
              <input type="file" accept="application/pdf" multiple className="hidden" onChange={handleFiles} />
              <span className="text-sm text-white/70">
                {selectedFiles.length === 0
                  ? 'Choose one or many research papers'
                  : `${selectedFiles.length} PDF file(s) selected`}
              </span>
            </label>
            {selectedFiles.length > 0 && (
              <div className="max-h-28 overflow-y-auto space-y-1 text-xs text-white/50">
                {selectedFiles.map(file => (
                  <p key={`${file.name}-${file.size}`} className="truncate">
                    {file.name}
                  </p>
                ))}
              </div>
            )}
            <button
              onClick={handleUpload}
              disabled={isUploading || selectedFiles.length === 0}
              className="w-full bg-white text-black py-3 rounded-lg font-bold text-xs uppercase tracking-widest disabled:opacity-50"
            >
              {isUploading ? 'Uploading...' : 'Upload and Build Graph'}
            </button>
            {uploadError && <p className="text-sm text-red-300">{uploadError}</p>}
            <div className="grid grid-cols-2 gap-3 text-xs text-white/50">
              <span>Structural RAG</span>
              <span>Vector retrieval</span>
              <span>Claim extraction</span>
              <span>Neo4j provenance</span>
            </div>
          </section>

          <section className="border border-white/10 bg-white/5 rounded-xl p-6 space-y-5">
            <div>
              <p className="text-xs uppercase tracking-widest text-white/45">Evidence RAG</p>
              <h2 className="text-2xl font-bold mt-1">Ask the Corpus</h2>
            </div>
            <form onSubmit={handleAsk} className="space-y-3">
              <textarea
                value={query}
                onChange={event => setQuery(event.target.value)}
                rows={4}
                placeholder="Which methods have weak validation evidence, and what papers support that?"
                className="w-full bg-black/40 border border-white/10 rounded-lg p-4 text-sm outline-none focus:border-white/40 resize-none"
              />
              <button
                type="submit"
                disabled={isAsking || !query.trim()}
                className="bg-white text-black px-5 py-3 rounded-lg font-bold text-xs uppercase tracking-widest disabled:opacity-50"
              >
                {isAsking ? 'Retrieving...' : 'Ask with Citations'}
              </button>
            </form>
            {queryError && <p className="text-sm text-red-300">{queryError}</p>}
            {answer && (
              <div className="border border-white/10 rounded-lg p-4 bg-black/30 space-y-3">
                <p className="text-sm text-white/80 leading-relaxed">{answer.content}</p>
                {answer.citations && answer.citations.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {answer.citations.map((citation, index) => (
                      <span key={`${citation.title}-${index}`} className="text-xs border border-white/10 px-2 py-1 rounded-full text-white/50">
                        {citation.title}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>
        </div>

        <section className="border border-white/10 bg-white/5 rounded-xl overflow-hidden">
          <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10">
            <div>
              <p className="text-xs uppercase tracking-widest text-white/45">Corpus</p>
              <h2 className="text-2xl font-bold mt-1">Processed Papers</h2>
            </div>
            <div className="flex flex-wrap gap-3">
              <button onClick={() => navigate('/discovery')} className="px-4 py-2 rounded-lg bg-white text-black text-xs font-bold uppercase tracking-widest">
                Run Discovery
              </button>
              <button onClick={() => navigate('/knowledge-graph')} className="px-4 py-2 rounded-lg border border-white/20 text-xs font-bold uppercase tracking-widest">
                Explore Graph
              </button>
              <button onClick={() => navigate('/hypothesis')} className="px-4 py-2 rounded-lg border border-white/20 text-xs font-bold uppercase tracking-widest">
                Hypothesis Lab
              </button>
            </div>
          </div>
          {paperActionError && (
            <div className="border-b border-red-400/20 bg-red-500/10 px-6 py-3 text-sm text-red-200">
              {paperActionError}
            </div>
          )}
          <div className="divide-y divide-white/10">
            {documents.length === 0 && (
              <div className="p-8 text-center text-white/45">No papers uploaded yet.</div>
            )}
            {documents.map(doc => (
              <article key={doc.id} className="p-5 grid grid-cols-1 gap-4 md:grid-cols-[minmax(0,1fr)_auto_auto_auto_auto] md:items-center">
                <div className="min-w-0">
                  <h3 className="font-semibold text-white/90">{doc.title}</h3>
                  <p className="text-xs text-white/40">Uploaded {new Date(doc.upload_date).toLocaleString()}</p>
                </div>
                <StatusBadge status={doc.status} />
                <span className="text-sm text-white/60">{doc.chunk_count} chunks</span>
                <span className="text-sm text-white/60">{doc.structural_sections} sections</span>
                <div className="flex flex-wrap gap-2 md:justify-end">
                  <button
                    onClick={() => navigate(`/chat?document=${doc.id}`)}
                    disabled={doc.status !== 'completed'}
                    className="border border-white/20 px-3 py-2 text-xs font-bold uppercase tracking-widest text-white/70 transition-colors hover:border-white hover:bg-white hover:text-black disabled:cursor-not-allowed disabled:opacity-35"
                  >
                    Chat
                  </button>
                  <button
                    onClick={() => handleDeletePaper(doc)}
                    disabled={deletingDocumentId === doc.id}
                    className="border border-red-300/35 px-3 py-2 text-xs font-bold uppercase tracking-widest text-red-200 transition-colors hover:border-red-200 hover:bg-red-300 hover:text-black disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    {deletingDocumentId === doc.id ? 'Deleting' : 'Delete'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
};

const StatusBadge = ({ status }: { status: DocumentRecord['status'] }) => {
  const color =
    status === 'completed'
      ? 'text-emerald-300 border-emerald-400/30 bg-emerald-400/10'
      : status === 'failed'
        ? 'text-red-300 border-red-400/30 bg-red-400/10'
        : 'text-amber-300 border-amber-400/30 bg-amber-400/10';

  return (
    <span className={`w-fit text-xs px-2 py-1 rounded-full border capitalize ${color}`}>
      {status}
    </span>
  );
};

export default WorkspacePage;
