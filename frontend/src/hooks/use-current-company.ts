import { useEffect, useState } from 'react';

import type { CompanyRead } from '../api/generated/model';

const STORAGE_KEY = 'call-analyzer.currentCompanyId';

function readStoredCompanyId() {
  if (typeof window === 'undefined') {
    return null;
  }
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return null;
  }
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : null;
}

export function useCurrentCompany(companies: CompanyRead[] | undefined) {
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(() => readStoredCompanyId());

  useEffect(() => {
    if (!companies || companies.length === 0) {
      setSelectedCompanyId(null);
      return;
    }

    const hasSelectedCompany = selectedCompanyId !== null && companies.some((company) => company.id === selectedCompanyId);
    if (hasSelectedCompany) {
      return;
    }

    const fallbackId = companies[0]?.id ?? null;
    setSelectedCompanyId(fallbackId);
    if (typeof window !== 'undefined' && fallbackId !== null) {
      window.localStorage.setItem(STORAGE_KEY, String(fallbackId));
    }
  }, [companies, selectedCompanyId]);

  const currentCompany = companies?.find((company) => company.id === selectedCompanyId) ?? null;

  function setCurrentCompanyId(companyId: number) {
    setSelectedCompanyId(companyId);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, String(companyId));
    }
  }

  return {
    currentCompany,
    currentCompanyId: currentCompany?.id ?? null,
    selectedCompanyId,
    setCurrentCompanyId,
  };
}
