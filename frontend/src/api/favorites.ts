import { apiFetch } from './http';

export function favoriteUpload(companyId: number, fileId: string) {
  return apiFetch({
    url: `/uploads/${companyId}/${fileId}/favorite`,
    method: 'POST',
  });
}

export function unfavoriteUpload(companyId: number, fileId: string) {
  return apiFetch({
    url: `/uploads/${companyId}/${fileId}/favorite`,
    method: 'DELETE',
  });
}
