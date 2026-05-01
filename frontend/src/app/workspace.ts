import { queryClient } from './query-client';

export const workspacePaths = {
  dashboard: () => '/',
  uploads: (companyId: number | string) => `/companies/${companyId}/uploads`,
  favorites: (companyId: number | string) => `/companies/${companyId}/favorites`,
  mentor: (companyId: number | string) => `/companies/${companyId}/mentor`,
  transcriptions: (companyId: number | string) => `/companies/${companyId}/transcriptions`,
  analyses: (companyId: number | string) => `/companies/${companyId}/analyses`,
  templateReports: (companyId: number | string, templateId: number | string) => `/companies/${companyId}/reports/${templateId}`,
  analysis: (analysisId: number | string) => `/analysis/${analysisId}`,
  templates: (companyId: number | string) => `/companies/${companyId}/templates`,
  template: (companyId: number | string, templateId: number | string) =>
    `/companies/${companyId}/templates/${templateId}`,
  employees: (companyId: number | string) => `/companies/${companyId}/employees`,
  integrations: (companyId: number | string) => `/companies/${companyId}/integrations`,
  settings: (companyId: number | string) => `/companies/${companyId}/settings`,
  performanceChart: (companyId: number | string) => `/companies/${companyId}/performance-chart`,
};

export type WorkspaceSection =
  | 'dashboard'
  | 'reports'
  | 'transcriptions'
  | 'uploads'
  | 'favorites'
  | 'mentor'
  | 'templates'
  | 'employees'
  | 'integrations'
  | 'settings'
  | 'performance-chart';

export function invalidateWorkspaceQueries() {
  return queryClient.invalidateQueries({
    predicate(query) {
      const key = Array.isArray(query.queryKey) ? String(query.queryKey[0] ?? '') : '';
      return (
        key === '/companies' ||
        key.startsWith('/companies/') ||
        key.startsWith('/uploads/') ||
        key.startsWith('/transcriptions/') ||
      key.startsWith('/analysis') ||
      key.startsWith('/mentor') ||
      key.startsWith('/templates') ||
        key.startsWith('/criteria') ||
        key.startsWith('/employees')
      );
    },
  });
}
