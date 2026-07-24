import type { TranscriptionResponse } from './generated/model/transcriptionResponse';
import { apiFetch } from './http';

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
