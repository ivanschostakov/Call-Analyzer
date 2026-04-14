import { apiFetch } from './http';

export type EmployeeInvitation = {
  id: number;
  company_id: number;
  company_name: string;
  email: string;
  invited_by_user_id: number | null;
  invited_by_display_name: string | null;
  invited_by_email: string | null;
  accepted_by_user_id: number | null;
  accepted_by_display_name: string | null;
  accepted_by_email: string | null;
  accepted_at: string | null;
  expires_at: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export function listEmployeeInvitations(companyId: number) {
  return apiFetch<EmployeeInvitation[]>({
    url: '/employees/invitations',
    params: { company_id: companyId },
  });
}

export function createEmployeeInvitation(companyId: number, email: string) {
  return apiFetch<EmployeeInvitation>({
    url: '/employees/invitations',
    method: 'POST',
    data: {
      company_id: companyId,
      email,
    },
  });
}

export function acceptEmployeeInvitation(token: string) {
  return apiFetch<{ ok: boolean; message: string }>({
    url: '/employees/invitations/accept',
    method: 'POST',
    data: { token },
  });
}
