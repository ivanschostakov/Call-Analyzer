import type { TranscriptionResponse } from './generated/model/transcriptionResponse';
import { apiFetch } from './http';

export type TranscriptionSummary = Omit<TranscriptionResponse, 'text' | 'segments'> & {
  text_preview: string | null;
  has_text: boolean;
};

export type TranscriptionListParams = {
  page: number;
  page_size: number;
  employee: string;
  status?: TranscriptionResponse['status'];
  favorites_only: boolean;
};

export type TranscriptionPageResponse = {
  items: TranscriptionSummary[];
  total: number;
  page: number;
  page_size: number;
};

export function listTranscriptionPage(companyId: number, params: TranscriptionListParams, signal?: AbortSignal) {
  return apiFetch<TranscriptionPageResponse>({
    url: `/transcriptions/${companyId}/list/page`,
    params,
    signal,
  });
}

export function getTranscriptionDetail(companyId: number, fileId: string, signal?: AbortSignal) {
  return apiFetch<TranscriptionResponse>({
    url: `/transcriptions/${companyId}/${encodeURIComponent(fileId)}`,
    signal,
  });
}

export function assignTranscriptionEmployee(
  companyId: number,
  fileId: string,
  employeeUserId: number | null,
) {
  return apiFetch<TranscriptionResponse>({
    url: `/transcriptions/${companyId}/${fileId}/employee`,
    method: 'PATCH',
    data: {
      employee_user_id: employeeUserId,
    },
  });
}
