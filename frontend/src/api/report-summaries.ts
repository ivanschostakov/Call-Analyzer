import { apiFetch } from './http';

export type ReportSummaryRequest = {
  company_id: number;
  template_id: number;
  prompt: string;
  analysis_ids: number[];
  columns?: string[];
};

export type ReportSummaryResponse = {
  company_id: number;
  template_id: number;
  analysis_ids: number[];
  selected_columns: string[];
  selected_column_labels: string[];
  row_count: number;
  summarized_row_count: number;
  omitted_row_count: number;
  text: string;
};

export function summarizeAnalysisReport(payload: ReportSummaryRequest) {
  return apiFetch<ReportSummaryResponse>({
    url: '/analysis/report-summary',
    method: 'POST',
    data: payload,
  });
}
