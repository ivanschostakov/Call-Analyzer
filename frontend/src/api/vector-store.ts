import { apiFetch } from './http';

export type CompanyVectorStoreFile = {
  id: string;
  filename: string;
  status: 'in_progress' | 'completed' | 'cancelled' | 'failed' | string;
  usage_bytes: number;
  created_at: string;
  last_error_message: string | null;
};

export type CompanyVectorStoreBatchUpload = {
  vector_store_id: string;
  status: string;
  uploaded_count: number;
  completed_count: number;
  failed_count: number;
  cancelled_count: number;
  in_progress_count: number;
};

export function createCompanyVectorStore(companyId: number, name?: string) {
  return apiFetch<{ company_id: number; vector_store_id: string | null }>({
    url: `/companies/${companyId}/vector-store`,
    method: 'POST',
    data: {
      name: name?.trim() || undefined,
    },
  });
}

export function listCompanyVectorStoreFiles(companyId: number) {
  return apiFetch<CompanyVectorStoreFile[]>({
    url: `/companies/${companyId}/vector-store/files`,
  });
}

export function uploadCompanyVectorStoreFiles(companyId: number, files: File[]) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  return apiFetch<CompanyVectorStoreBatchUpload>({
    url: `/companies/${companyId}/vector-store/files`,
    method: 'POST',
    data: formData,
  });
}
