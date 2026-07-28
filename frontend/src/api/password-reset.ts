import { apiFetch } from './http';

type PasswordResetResponse = {
  ok: boolean;
  message: string;
};

export function requestPasswordReset(email: string) {
  return apiFetch<PasswordResetResponse>('/auth/password-reset/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
}

export function confirmPasswordReset(token: string, newPassword: string) {
  return apiFetch<PasswordResetResponse>('/auth/password-reset/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}
