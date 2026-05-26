import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Star } from 'lucide-react';

import { useListEmployeesRouteEmployeesGet, useListUploadsUploadsCompanyIdGet } from '../api/generated/client';
import { unfavoriteUpload } from '../api/favorites';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { useAuth } from '../auth/context';
import { AuthenticatedAudio } from '../components/workspace/authenticated-audio';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { SectionCard } from '../components/ui/section-card';
import { Select } from '../components/ui/select';
import { useViewport } from '../hooks/use-viewport';
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

export function FavoritesPage({ companyId }: { companyId: number }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const canManageCurrentTeam = canManageTeam(auth.user?.role);
  const [employeeFilter, setEmployeeFilter] = useState('all');

  const uploadsQuery = useListUploadsUploadsCompanyIdGet(companyId, {
    query: {
      enabled: Boolean(companyId),
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
  const unfavoriteMutation = useMutation({
    mutationFn: (fileId: string) => unfavoriteUpload(companyId, fileId),
    onSuccess() {
      void invalidateWorkspaceQueries();
    },
  });

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
        .filter((item) => item.is_favorite)
        .filter((item) => employeeFilter === 'all' || resolveConversationEmployeeUserId(item) === Number(employeeFilter))
        .sort((left, right) => new Date(resolveCallDate(right)).getTime() - new Date(resolveCallDate(left)).getTime()),
    [employeeFilter, uploadsQuery.data?.items],
  );

  async function handleUnfavorite(fileId: string) {
    await unfavoriteMutation.mutateAsync(fileId);
  }

  return (
    <WorkspaceShell
      title="Избранное"
      description="Быстрый доступ к важным загрузкам с аудио и переходом к расшифровке."
      section="favorites"
      companyId={companyId}
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.favorites(nextCompanyId) })}
    >
      <SectionCard
        title="Избранные загрузки"
        description="Здесь собраны отмеченные файлы. Сортировка идет по дате звонка, если она известна."
        actions={
          canManageCurrentTeam ? (
            <div style={{ ...styles.fieldStack, ...styles.responsiveField }}>
              <Label htmlFor="favorites-employee-filter">Сотрудник</Label>
              <Select id="favorites-employee-filter" value={employeeFilter} onChange={(event) => setEmployeeFilter(event.target.value)}>
                <option value="all">Все сотрудники</option>
                {employeeOptions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </div>
          ) : undefined
        }
      >

        {uploadsQuery.isError ? <p style={styles.errorText}>{getErrorMessage(uploadsQuery.error)}</p> : null}
        {employeesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(employeesQuery.error)}</p> : null}
        {!uploadsQuery.isError && !items.length ? <p style={styles.mutedText}>Избранных загрузок пока нет.</p> : null}

        {!!items.length ? (
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.tableHead}>Файл</th>
                  <th style={styles.tableHead}>Дата звонка</th>
                  <th style={styles.tableHead}>Статус</th>
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
                    <td style={styles.tableCell}>{formatDateTime(resolveCallDate(item))}</td>
                    <td style={styles.tableCell}>
                      <Badge tone={transcriptionStatusTone(item.status)}>{transcriptionStatusLabel(item.status)}</Badge>
                    </td>
                    <td style={styles.tableCell}>
                      <AuthenticatedAudio mediaUrl={item.media_url} compact />
                    </td>
                    <td style={styles.tableCell}>
                      <div style={styles.rowActions}>
                        <Button variant="ghost" size="sm" onClick={() => navigate({ to: workspacePaths.transcriptions(companyId) })}>
                          К расшифровкам
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          style={getFavoriteButtonStyle()}
                          onClick={() => handleUnfavorite(item.file_id)}
                          disabled={unfavoriteMutation.isPending}
                          aria-label="Убрать из избранного"
                          title="Убрать из избранного"
                        >
                          <Star size={14} style={getFavoriteStarStyle(true)} />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => navigate({ to: workspacePaths.uploads(companyId) })}>
                          Загрузки
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </SectionCard>
    </WorkspaceShell>
  );
}
