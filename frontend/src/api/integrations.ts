import { apiFetch } from './http';

export type CompanyBeelineIntegration = {
  company_id: number;
  enabled: boolean;
  has_token: boolean;
  token_hint: string | null;
  analysis_template_id: number | null;
  last_sync_target_date: string | null;
  last_sync_started_at: string | null;
  last_sync_finished_at: string | null;
  last_sync_status: string | null;
  last_sync_error: string | null;
};

export function getCompanyBeelineIntegration(companyId: number) {
  return apiFetch<CompanyBeelineIntegration>({
    url: `/companies/${companyId}/integrations/beeline`,
  });
}

export function updateCompanyBeelineIntegration(
  companyId: number,
  payload: {
    api_token?: string;
    analysis_template_id?: number | null;
  },
) {
  return apiFetch<CompanyBeelineIntegration>({
    url: `/companies/${companyId}/integrations/beeline`,
    method: 'PUT',
    data: payload,
  });
}

export function clearCompanyBeelineIntegration(companyId: number) {
  return apiFetch<{ ok: boolean; message: string }>({
    url: `/companies/${companyId}/integrations/beeline`,
    method: 'DELETE',
  });
}

export function syncCompanyBeelineCurrentDate(companyId: number) {
  return apiFetch<CompanyBeelineIntegration>({
    url: `/companies/${companyId}/integrations/beeline/sync-current-date`,
    method: 'POST',
  });
}

export function syncCompanyBeelineDateRange(
  companyId: number,
  payload: {
    date_from: string;
    date_to: string;
  },
) {
  return apiFetch<CompanyBeelineIntegration>({
    url: `/companies/${companyId}/integrations/beeline/sync-range`,
    method: 'POST',
    data: payload,
  });
}
