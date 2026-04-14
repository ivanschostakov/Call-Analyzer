import { createContext, useContext, useMemo } from 'react';

import { useListCompaniesRouteCompaniesGet } from '../api/generated/client';
import type { CompanyRead } from '../api/generated/model';
import { useAuth } from '../auth/context';
import { useCurrentCompany } from '../hooks/use-current-company';

type WorkspaceContextValue = {
  companies: CompanyRead[];
  currentCompany: CompanyRead | null;
  currentCompanyId: number | null;
  selectedCompanyId: number | null;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetchCompanies: () => Promise<unknown>;
  getCompanyById: (companyId: number | null | undefined) => CompanyRead | null;
  setCurrentCompanyId: (companyId: number) => void;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const companiesQuery = useListCompaniesRouteCompaniesGet({
    query: {
      enabled: auth.isAuthenticated,
      staleTime: 30_000,
    },
  });

  const companies = companiesQuery.data ?? [];
  const currentCompanyState = useCurrentCompany(companies);

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      companies,
      currentCompany: currentCompanyState.currentCompany,
      currentCompanyId: currentCompanyState.currentCompanyId,
      selectedCompanyId: currentCompanyState.selectedCompanyId,
      isLoading: auth.isAuthenticated && companiesQuery.isPending,
      isError: companiesQuery.isError,
      error: companiesQuery.error,
      refetchCompanies: companiesQuery.refetch,
      getCompanyById(companyId) {
        if (!companyId) {
          return null;
        }
        return companies.find((company) => company.id === companyId) ?? null;
      },
      setCurrentCompanyId: currentCompanyState.setCurrentCompanyId,
    }),
    [auth.isAuthenticated, companies, companiesQuery.error, companiesQuery.isError, companiesQuery.isPending, companiesQuery.refetch, currentCompanyState],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) {
    throw new Error('useWorkspace must be used within WorkspaceProvider');
  }
  return value;
}
