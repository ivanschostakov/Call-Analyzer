import { apiFetch } from './http';

export type DailyReportCallItem = {
  analysis_id: number;
  call_name: string;
  employee_name: string;
  score: number;
  template_name: string;
  call_date: string | null;
};

export type DailyReportResponse = {
  report_date: string;
  average_score: number;
  total_calls: number;
  best_calls: DailyReportCallItem[];
  worst_calls: DailyReportCallItem[];
};

export function getDailyReport(companyId: number, reportDate?: string): Promise<DailyReportResponse> {
  const params = reportDate ? `?report_date=${reportDate}` : '';
  return apiFetch<DailyReportResponse>({
    url: `/companies/${companyId}/daily-report/latest${params}`,
    method: 'GET',
  });
}
