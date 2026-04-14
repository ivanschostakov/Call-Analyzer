import { clsx, type ClassValue } from 'clsx';
import { formatDistanceToNowStrict, parseISO } from 'date-fns';
import { ru } from 'date-fns/locale';
import { twMerge } from 'tailwind-merge';

import type { UserRole } from '../auth/types';
import type { AnalysisResultReadAnswer } from '../api/generated/model/analysisResultReadAnswer';
import type { CriterionAnswerType } from '../api/generated/model/criterionAnswerType';
import type { TranscriptionStatus } from '../api/generated/model/transcriptionStatus';

export type PercentageTone = 'danger' | 'warning' | 'success' | 'perfect';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function roleLabel(role: UserRole) {
  switch (role) {
    case 'admin':
      return 'Администратор';
    case 'employee':
      return 'Сотрудник';
    default:
      return 'Владелец';
  }
}

export function canManageCompany(role: UserRole | undefined) {
  return role === 'owner' || role === 'admin';
}

export function canManageTeam(role: UserRole | undefined) {
  return role === 'owner' || role === 'admin';
}

export function relativeTime(value: string) {
  return formatDistanceToNowStrict(parseISO(value), {
    addSuffix: true,
    locale: ru,
  });
}

export function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function resolveCallDate(value: { call_started_at?: string | null; created_at: string }) {
  return value.call_started_at ?? value.created_at;
}

export function getErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  if (typeof error === 'object' && error && 'detail' in error) {
    const detail = (error as { detail?: unknown }).detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }

  return 'Что-то пошло не так. Попробуйте еще раз.';
}

export function transcriptionStatusLabel(status: TranscriptionStatus) {
  switch (status) {
    case 'uploaded':
      return 'Загружен';
    case 'queued':
      return 'В очереди';
    case 'processing':
      return 'Расшифровывается';
    case 'completed':
      return 'Готово';
    case 'failed':
      return 'Ошибка';
    default:
      return status;
  }
}

export function transcriptionStatusTone(status: TranscriptionStatus) {
  switch (status) {
    case 'completed':
      return 'success' as const;
    case 'failed':
      return 'danger' as const;
    case 'queued':
    case 'processing':
      return 'warning' as const;
    default:
      return 'default' as const;
  }
}

export function formatAnalysisAnswer(answer: AnalysisResultReadAnswer, answerType: CriterionAnswerType) {
  if (answerType === 'boolean') {
    return answer === true ? 'Да' : 'Нет';
  }

  if (answerType === 'percentage') {
    const normalized = getAnalysisPercentageValue(answer, answerType);
    if (normalized !== null) {
      return `${normalized}%`;
    }

    const fallback = String(answer).trim();
    if (!fallback) {
      return '...';
    }
    return fallback.endsWith('%') ? fallback : `${fallback}%`;
  }

  return String(answer);
}

export function getAnalysisPercentageValue(answer: AnalysisResultReadAnswer, answerType: CriterionAnswerType): number | null {
  if (answerType !== 'percentage') {
    return null;
  }

  if (typeof answer === 'number' && Number.isFinite(answer)) {
    const normalized = Math.round(answer);
    return normalized >= 0 && normalized <= 100 ? normalized : null;
  }

  if (typeof answer === 'string') {
    const normalized = answer.trim().replace('%', '').replace(',', '.');
    if (!normalized) {
      return null;
    }

    const parsed = Number(normalized);
    if (!Number.isFinite(parsed)) {
      return null;
    }

    const rounded = Math.round(parsed);
    return rounded >= 0 && rounded <= 100 ? rounded : null;
  }

  return null;
}

export function getAnalysisBooleanValue(answer: AnalysisResultReadAnswer, answerType: CriterionAnswerType): boolean | null {
  if (answerType !== 'boolean') {
    return null;
  }

  if (typeof answer === 'boolean') {
    return answer;
  }

  if (typeof answer === 'string') {
    const normalized = answer.trim().toLowerCase();
    if (['true', 'yes', 'da', 'да', '1'].includes(normalized)) {
      return true;
    }
    if (['false', 'no', 'net', 'нет', '0'].includes(normalized)) {
      return false;
    }
  }

  return null;
}

export function getPercentageTone(value: number): PercentageTone {
  if (value <= 33) {
    return 'danger';
  }
  if (value <= 66) {
    return 'warning';
  }
  if (value < 100) {
    return 'success';
  }
  return 'perfect';
}

export function truncateText(value: string | null | undefined, maxLength = 160) {
  if (!value) {
    return '';
  }
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength).trimEnd()}...`;
}

export function formatUserLabel(displayName?: string | null, email?: string | null) {
  const trimmedName = displayName?.trim();
  const trimmedEmail = email?.trim();

  if (trimmedName && trimmedEmail && trimmedName.toLowerCase() !== trimmedEmail.toLowerCase()) {
    return `${trimmedName} · ${trimmedEmail}`;
  }

  return trimmedName || trimmedEmail || 'Пользователь';
}

export function resolveConversationEmployeeUserId(value: { detected_employee_user_id?: number | null; uploaded_by_user_id: number }) {
  return value.detected_employee_user_id ?? value.uploaded_by_user_id;
}

export function resolveConversationEmployeeLabel(value: {
  detected_employee_user_id?: number | null;
  detected_employee_display_name?: string | null;
  detected_employee_email?: string | null;
  uploaded_by_display_name?: string | null;
  uploaded_by_email?: string | null;
}) {
  if (value.detected_employee_user_id != null) {
    return formatUserLabel(value.detected_employee_display_name, value.detected_employee_email);
  }

  return formatUserLabel(value.uploaded_by_display_name, value.uploaded_by_email);
}

export function formatDetectedEmployeeLabel(value: {
  detected_employee_user_id?: number | null;
  detected_employee_display_name?: string | null;
  detected_employee_email?: string | null;
  uploaded_by_user_id?: number;
  uploaded_by_display_name?: string | null;
  uploaded_by_email?: string | null;
}) {
  if (value.detected_employee_user_id == null) {
    return 'Не определен';
  }

  return formatUserLabel(value.detected_employee_display_name, value.detected_employee_email);
}
