import { apiFetch } from './http';

export type PerformanceCallData = {
  call_count: number;
  label: string;
  call_date: string;
  overall_score: number;
};

export type PerformanceChartRequest = {
  company_id: number;
  template_id: number;
  employee_user_id?: number;
  date_from: string;
  date_to: string;
};

export type PerformanceChartResponse = {
  company_id: number;
  template_id: number;
  calls: PerformanceCallData[];
};

export function generatePerformanceChart(payload: PerformanceChartRequest): Promise<PerformanceChartResponse> {
  return apiFetch<PerformanceChartResponse>({
    url: '/analysis/performance-chart',
    method: 'POST',
    data: payload,
  });
}
