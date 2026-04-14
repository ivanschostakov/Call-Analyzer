import type { OperationResponse } from './generated/model';
import { apiFetch } from './http';

export function deactivateAnalysis(analysisId: number) {
  return apiFetch<OperationResponse>({
    url: `/analysis/${analysisId}`,
    method: 'DELETE',
  });
}

export const deleteAnalysis = deactivateAnalysis;
