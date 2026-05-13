import apiClient from './apiClient';

export type DocumentRecord = {
  id: number;
  title: string;
  source: string;
  upload_date: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count: number;
  structural_sections: number;
};

export type UploadResult = {
  id: number;
  filename: string;
  status: string;
  message: string;
  features: string[];
};

export type DocumentStats = {
  vector_store: {
    total_chunks?: number;
    total_documents?: number;
    embedding_dim?: number;
    index_type?: string;
  };
  structural_index: {
    indexed_documents?: number;
  };
  knowledge_graph: {
    nodes: number;
    edges: number;
    density: number;
    communities: number;
  };
};

export const fetchDocuments = async (): Promise<DocumentRecord[]> => {
  const { data } = await apiClient.get('/documents');
  return Array.isArray(data.documents) ? data.documents : [];
};

export const fetchDocumentStats = async (): Promise<DocumentStats> => {
  const { data } = await apiClient.get('/documents/stats/overview');
  return data;
};

export const uploadDocuments = async (files: File[]): Promise<UploadResult[]> => {
  if (files.length === 0) return [];

  const formData = new FormData();
  if (files.length === 1) {
    formData.append('file', files[0]);
    const { data } = await apiClient.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return [data];
  }

  files.forEach(file => formData.append('files', file));
  const { data } = await apiClient.post('/documents/upload/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return Array.isArray(data.documents) ? data.documents : [];
};

export const deleteDocument = async (documentId: number): Promise<void> => {
  await apiClient.delete(`/documents/${documentId}`);
};
