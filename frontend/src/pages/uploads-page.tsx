import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Star, Trash2, Upload } from 'lucide-react';

import {
  useDeleteUploadUploadsCompanyIdFileIdDelete,
  useListEmployeesRouteEmployeesGet,
  useListUploadsUploadsCompanyIdGet,
  uploadAudioUploadsCompanyIdPost,
} from '../api/generated/client';
import type { BodyUploadAudioUploadsCompanyIdPost } from '../api/generated/model';
import { favoriteUpload, unfavoriteUpload } from '../api/favorites';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { useAuth } from '../auth/context';
import { AuthenticatedAudio } from '../components/workspace/authenticated-audio';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { useViewport } from '../hooks/use-viewport';
import { runWithConcurrency } from '../lib/async';
import { getFavoriteButtonStyle, getFavoriteStarStyle } from '../lib/favorite-styles';
import {
  canManageTeam,
  formatDateTime,
  formatDetectedEmployeeLabel,
  formatUserLabel,
  getErrorMessage,
  resolveCallDate,
  resolveConversationEmployeeUserId,
  transcriptionStatusLabel,
  transcriptionStatusTone,
} from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

const UPLOAD_CONCURRENCY = 3;

export function UploadsPage({ companyId }: { companyId: number }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const canManageCurrentTeam = canManageTeam(auth.user?.role);
  const [employeeFilter, setEmployeeFilter] = useState('all');
  const [isUploadingBatch, setIsUploadingBatch] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const uploadsQuery = useListUploadsUploadsCompanyIdGet(companyId, {
    query: {
      enabled: Boolean(companyId),
      refetchInterval(query) {
        const items = query.state.data?.items ?? [];
        return items.some((item) => item.status === 'queued' || item.status === 'processing') ? 5_000 : false;
      },
    },
  });
  const employeesQuery = useListEmployeesRouteEmployeesGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId && canManageCurrentTeam),
      },
    },
  );
  const deleteMutation = useDeleteUploadUploadsCompanyIdFileIdDelete({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const favoriteMutation = useMutation({
    mutationFn: ({ fileId, nextValue }: { fileId: string; nextValue: boolean }) =>
      nextValue ? favoriteUpload(companyId, fileId) : unfavoriteUpload(companyId, fileId),
    onSuccess() {
      void invalidateWorkspaceQueries();
    },
  });

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) {
      return;
    }

    try {
      setIsUploadingBatch(true);
      setUploadFeedback(null);
      setUploadError(null);

      const results = await runWithConcurrency(files, UPLOAD_CONCURRENCY, (file) =>
        uploadAudioUploadsCompanyIdPost(companyId, { file } as unknown as BodyUploadAudioUploadsCompanyIdPost),
      );
      const successCount = results.filter((result) => result.status === 'fulfilled').length;
      const failedCount = results.length - successCount;

      await invalidateWorkspaceQueries();

      if (successCount) {
        setUploadFeedback(`Загружено и отправлено в расшифровку: ${successCount} файлов.`);
      }
      if (failedCount) {
        const firstFailure = results.find((result): result is PromiseRejectedResult => result.status === 'rejected');
        setUploadError(firstFailure ? getErrorMessage(firstFailure.reason) : 'Не удалось загрузить часть файлов.');
      }
    } finally {
      setIsUploadingBatch(false);
      event.target.value = '';
    }
  }

  async function handleDelete(fileId: string) {
    if (!window.confirm('Удалить этот файл?')) {
      return;
    }
    await deleteMutation.mutateAsync({ companyId, fileId });
  }

  async function handleFavoriteToggle(fileId: string, nextValue: boolean) {
    await favoriteMutation.mutateAsync({ fileId, nextValue });
  }

  const employeeOptions = useMemo(() => {
    const result = new Map<number, string>();

    if (auth.user?.id) {
      result.set(auth.user.id, formatUserLabel(`${auth.user.name} ${auth.user.surname}`.trim(), auth.user.email));
    }

    for (const employee of employeesQuery.data ?? []) {
      result.set(employee.user_id, formatUserLabel(employee.user_display_name, employee.user_email));
    }

    return Array.from(result.entries())
      .map(([id, label]) => ({ id, label }))
      .sort((left, right) => left.label.localeCompare(right.label, 'ru'));
  }, [auth.user, employeesQuery.data]);
  const items = useMemo(
    () =>
      [...(uploadsQuery.data?.items ?? [])]
        .filter((item) => employeeFilter === 'all' || resolveConversationEmployeeUserId(item) === Number(employeeFilter))
        .sort((left, right) => new Date(resolveCallDate(right)).getTime() - new Date(resolveCallDate(left)).getTime()),
    [employeeFilter, uploadsQuery.data?.items],
  );

  useEffect(() => {
    setEmployeeFilter('all');
  }, [companyId]);

  return (
    <WorkspaceShell
      title="Загрузки"
      description="Хранилище аудиофайлов компании с быстрым доступом к воспроизведению и удалению."
      section="uploads"
      companyId={companyId}
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.uploads(nextCompanyId) })}
      actions={
        <>
          <input ref={fileInputRef} type="file" accept="audio/*" multiple hidden onChange={handleUpload} />
          <Button onClick={() => fileInputRef.current?.click()} disabled={isUploadingBatch} style={viewport.isMobile ? { width: '100%' } : undefined}>
            <Upload size={16} />
            {isUploadingBatch ? 'Загружаем...' : 'Загрузить файлы'}
          </Button>
        </>
      }
    >
      <section style={styles.section}>
        <div style={styles.sectionHeader}>
          <div>
            <h2 style={styles.sectionTitle}>Файлы</h2>
            <p style={styles.sectionText}>Каждая загрузка связана с транскрибацией и может быть открыта из браузера с авторизацией.</p>
          </div>
          {canManageCurrentTeam ? (
            <div style={{ ...styles.fieldStack, ...styles.responsiveField }}>
              <Label htmlFor="uploads-employee-filter">Сотрудник</Label>
              <Select id="uploads-employee-filter" value={employeeFilter} onChange={(event) => setEmployeeFilter(event.target.value)}>
                <option value="all">Все сотрудники</option>
                {employeeOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>
          ) : null}
        </div>

        {uploadsQuery.isError ? <p style={styles.errorText}>{getErrorMessage(uploadsQuery.error)}</p> : null}
        {employeesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(employeesQuery.error)}</p> : null}
        {uploadFeedback ? <p style={{ ...styles.subtleText, color: tokens.success }}>{uploadFeedback}</p> : null}
        {uploadError ? <p style={styles.errorText}>{uploadError}</p> : null}

        {!uploadsQuery.isError && !items.length ? <p style={styles.mutedText}>Файлы еще не загружались.</p> : null}

        {!!items.length ? (
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.tableHead}>Файл</th>
                  <th style={styles.tableHead}>Дата звонка</th>
                  <th style={styles.tableHead}>Статус</th>
                  <th style={styles.tableHead}>Обновлен</th>
                  <th style={styles.tableHead}>Аудио</th>
                  <th style={styles.tableHead} />
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.file_id} style={styles.dividerRow}>
                    <td style={styles.tableCell}>
                      <div style={styles.fieldStack}>
                        <span>{item.original_filename}</span>
                        <span style={styles.subtleText}>{item.file_id}</span>
                        <span style={styles.subtleText}>Сотрудник в звонке: {formatDetectedEmployeeLabel(item)}</span>
                        <span style={styles.subtleText}>Загрузил: {formatUserLabel(item.uploaded_by_display_name, item.uploaded_by_email)}</span>
                      </div>
                    </td>
                    <td style={styles.tableCell}>
                      {formatDateTime(resolveCallDate(item))}
                    </td>
                    <td style={styles.tableCell}>
                      <Badge tone={transcriptionStatusTone(item.status)}>{transcriptionStatusLabel(item.status)}</Badge>
                    </td>
                    <td style={styles.tableCell}>{formatDateTime(item.updated_at)}</td>
                    <td style={styles.tableCell}>
                      <AuthenticatedAudio mediaUrl={item.media_url} compact />
                    </td>
                    <td style={styles.tableCell}>
                      <div style={styles.rowActions}>
                        <Button
                          variant="ghost"
                          size="sm"
                          style={getFavoriteButtonStyle()}
                          onClick={() => handleFavoriteToggle(item.file_id, !item.is_favorite)}
                          disabled={favoriteMutation.isPending}
                          aria-label={item.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное'}
                          title={item.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное'}
                        >
                          <Star size={14} style={getFavoriteStarStyle(item.is_favorite ?? false)} />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => navigate({ to: workspacePaths.transcriptions(companyId) })}>
                          К расшифровке
                        </Button>
                        <Button variant="danger" size="sm" onClick={() => handleDelete(item.file_id)} disabled={deleteMutation.isPending}>
                          <Trash2 size={14} />
                          Удалить
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </WorkspaceShell>
  );
}
