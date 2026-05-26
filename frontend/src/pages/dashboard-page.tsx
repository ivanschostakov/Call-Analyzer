import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Upload } from 'lucide-react';

import {
  useGetCompanyVectorStoreRouteCompaniesCompanyIdVectorStoreGet,
  useListAnalysisRouteAnalysisGet,
  useListEmployeesRouteEmployeesGet,
  useListTemplatesRouteTemplatesGet,
  useListTranscriptionsTranscriptionsCompanyIdGet,
  useUploadAudioUploadsCompanyIdPost,
} from '../api/generated/client';
import type { BodyUploadAudioUploadsCompanyIdPost } from '../api/generated/model';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { useAuth } from '../auth/context';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { SectionCard } from '../components/ui/section-card';
import { Select } from '../components/ui/select';
import { WORKSPACE_TOPBAR_CONTROL_WIDTH } from '../components/workspace/workspace.styles';
import { useViewport } from '../hooks/use-viewport';
import { useWorkspace } from '../workspace/workspace-context';
import {
  canManageCompany,
  canManageTeam,
  formatDateTime,
  formatDetectedEmployeeLabel,
  formatUserLabel,
  getErrorMessage,
  relativeTime,
  resolveConversationEmployeeUserId,
  roleLabel,
  transcriptionStatusLabel,
  truncateText,
} from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

function sortByUpdated<T extends { updated_at: string }>(items: T[]) {
  return [...items].sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime());
}

export function DashboardPage() {
  const auth = useAuth();
  const workspace = useWorkspace();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const isOwner = canManageCompany(auth.user?.role);
  const canManageCurrentTeam = canManageTeam(auth.user?.role);
  const currentCompany = workspace.currentCompany;
  const currentCompanyId = workspace.currentCompanyId ?? 0;
  const [employeeFilter, setEmployeeFilter] = useState('all');

  const transcriptionsQuery = useListTranscriptionsTranscriptionsCompanyIdGet(currentCompanyId, {
    query: {
      enabled: Boolean(currentCompanyId),
      refetchInterval(query) {
        const items = query.state.data?.items ?? [];
        return items.some((item) => item.status === 'queued' || item.status === 'processing') ? 10_000 : false;
      },
    },
  });
  const analysesQuery = useListAnalysisRouteAnalysisGet(
    { company_id: currentCompanyId },
    {
      query: {
        enabled: Boolean(currentCompanyId),
      },
    },
  );
  const employeesQuery = useListEmployeesRouteEmployeesGet(
    { company_id: currentCompanyId },
    {
      query: {
        enabled: Boolean(currentCompanyId && canManageCurrentTeam),
      },
    },
  );
  const templatesQuery = useListTemplatesRouteTemplatesGet(
    { company_id: currentCompanyId },
    {
      query: {
        enabled: Boolean(currentCompanyId && isOwner),
      },
    },
  );
  const vectorStoreQuery = useGetCompanyVectorStoreRouteCompaniesCompanyIdVectorStoreGet(currentCompanyId, {
    query: {
      enabled: Boolean(currentCompanyId && isOwner),
    },
  });
  const uploadMutation = useUploadAudioUploadsCompanyIdPost({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
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

  const recentTranscriptions = useMemo(
    () =>
      sortByUpdated(transcriptionsQuery.data?.items ?? [])
        .filter((item) => employeeFilter === 'all' || resolveConversationEmployeeUserId(item) === Number(employeeFilter))
        .slice(0, 5),
    [employeeFilter, transcriptionsQuery.data?.items],
  );
  const recentAnalyses = useMemo(
    () =>
      sortByUpdated(analysesQuery.data ?? [])
        .filter((item) => {
          if (employeeFilter === 'all') {
            return true;
          }
          const transcription = (transcriptionsQuery.data?.items ?? []).find((entry) => entry.id === item.transcription_id);
          return Boolean(transcription && resolveConversationEmployeeUserId(transcription) === Number(employeeFilter));
        })
        .slice(0, 5),
    [analysesQuery.data, employeeFilter, transcriptionsQuery.data?.items],
  );
  const recentTemplates = sortByUpdated(templatesQuery.data ?? []).slice(0, 5);
  const vectorStoreId = vectorStoreQuery.data?.vector_store_id?.trim() ?? '';

  useEffect(() => {
    setEmployeeFilter('all');
  }, [currentCompanyId]);

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !currentCompanyId) {
      return;
    }

    await uploadMutation.mutateAsync({
      companyId: currentCompanyId,
      data: { file } as unknown as BodyUploadAudioUploadsCompanyIdPost,
    });

    event.target.value = '';
  }

  return (
    <WorkspaceShell
      title="Обзор"
      description="Текущая компания и последние рабочие элементы."
      section="dashboard"
      onCompanyChange={() => {
        void invalidateWorkspaceQueries();
      }}
      actions={
        <>
          <input ref={fileInputRef} type="file" accept="audio/*" hidden onChange={handleUpload} />
          <Button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending || !currentCompanyId}
            style={
              viewport.isMobile
                ? { width: '100%' }
                : { width: WORKSPACE_TOPBAR_CONTROL_WIDTH, flex: `0 0 ${WORKSPACE_TOPBAR_CONTROL_WIDTH}px`, maxWidth: '100%' }
            }
          >
            <Upload size={16} />
            {uploadMutation.isPending ? 'Загружаем...' : 'Загрузить звонок'}
          </Button>
        </>
      }
    >
      <SectionCard
        title={currentCompany?.name ?? 'Компания'}
        description={currentCompany?.description ?? undefined}
        actions={
          canManageCurrentTeam ? (
            <div style={{ ...styles.fieldStack, ...styles.responsiveField }}>
              <Label htmlFor="dashboard-employee-filter">Сотрудник</Label>
              <Select id="dashboard-employee-filter" value={employeeFilter} onChange={(event) => setEmployeeFilter(event.target.value)}>
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
        {employeesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(employeesQuery.error)}</p> : null}

        <div style={styles.triple}>
          <div style={styles.infoCard}>
            <p style={styles.infoTitle}>Роль</p>
            <p style={styles.sectionText}>{auth.user ? `${auth.user.name} ${auth.user.surname}` : 'Пользователь'}</p>
            <p style={styles.subtleText}>{auth.user ? roleLabel(auth.user.role) : ''}</p>
          </div>
          <div style={styles.infoCard}>
            <p style={styles.infoTitle}>Компании в доступе</p>
            <p style={styles.sectionText}>{workspace.companies.length}</p>
            <p style={styles.subtleText}>Переключаются в верхней панели</p>
          </div>
          {vectorStoreId ? (
            <div style={styles.infoCard}>
              <p style={styles.infoTitle}>Vector store</p>
              <p style={styles.monoText}>{vectorStoreId}</p>
            </div>
          ) : null}
        </div>
      </SectionCard>

      <div style={styles.triple}>
        <SectionCard
          title="Последние расшифровки"
          description="Последние файлы по текущей компании."
          actions={
            <Button variant="ghost" size="sm" onClick={() => navigate({ to: workspacePaths.transcriptions(currentCompanyId) })}>
              Все
            </Button>
          }
        >

          {transcriptionsQuery.isError ? <p style={styles.errorText}>{getErrorMessage(transcriptionsQuery.error)}</p> : null}
          {!transcriptionsQuery.isError && !recentTranscriptions.length ? (
            <p style={styles.mutedText}>Пока ничего не загружено.</p>
          ) : null}
          <div style={styles.list}>
            {recentTranscriptions.map((item) => (
                <div key={item.id} style={styles.listItem}>
                  <div style={styles.listItemBody}>
                    <p style={styles.listItemTitle}>{item.original_filename}</p>
                    <p style={styles.listItemMeta}>
                      {transcriptionStatusLabel(item.status)} · {relativeTime(item.updated_at)}
                    </p>
                    <p style={styles.subtleText}>Сотрудник в звонке: {formatDetectedEmployeeLabel(item)}</p>
                    <p style={styles.subtleText}>Загрузил: {formatUserLabel(item.uploaded_by_display_name, item.uploaded_by_email)}</p>
                  </div>
                  <Badge tone={item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'warning'}>
                    {transcriptionStatusLabel(item.status)}
                  </Badge>
                </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="Последние анализы"
          description="Недавние результаты по текущей компании."
          actions={
            <Button variant="ghost" size="sm" onClick={() => navigate({ to: workspacePaths.analyses(currentCompanyId) })}>
              Все
            </Button>
          }
        >

          {analysesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(analysesQuery.error)}</p> : null}
          {!analysesQuery.isError && !recentAnalyses.length ? <p style={styles.mutedText}>Анализов пока нет.</p> : null}
          <div style={styles.list}>
            {recentAnalyses.map((item) => (
                <div key={item.id} style={styles.listItem}>
                  <div style={styles.listItemBody}>
                    <p style={styles.listItemTitle}>{item.template_name}</p>
                    <p style={styles.sectionText}>{truncateText(item.summary, 140)}</p>
                    <p style={styles.listItemMeta}>{formatDateTime(item.created_at)}</p>
                    {(() => {
                      const transcription = (transcriptionsQuery.data?.items ?? []).find((entry) => entry.id === item.transcription_id);
                      return transcription ? <p style={styles.subtleText}>Сотрудник в звонке: {formatDetectedEmployeeLabel(transcription)}</p> : null;
                    })()}
                    <p style={styles.subtleText}>Автор summary: {formatUserLabel(item.created_by_display_name, item.created_by_email)}</p>
                  </div>
                  <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    navigate({
                      to:
                        item.template_id == null
                          ? workspacePaths.analyses(currentCompanyId)
                          : workspacePaths.templateReports(currentCompanyId, item.template_id),
                    })
                  }
                >
                  Открыть
                </Button>
              </div>
            ))}
          </div>
        </SectionCard>

        {isOwner ? (
          <SectionCard
            title="Шаблоны"
            description="Последние измененные шаблоны компании."
            actions={
              <Button variant="ghost" size="sm" onClick={() => navigate({ to: workspacePaths.templates(currentCompanyId) })}>
                Все
              </Button>
            }
          >

            {templatesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(templatesQuery.error)}</p> : null}
            {!templatesQuery.isError && !recentTemplates.length ? <p style={styles.mutedText}>Шаблонов пока нет.</p> : null}
            <div style={styles.list}>
              {recentTemplates.map((item) => (
                <div key={item.id} style={styles.listItem}>
                  <div style={styles.listItemBody}>
                    <p style={styles.listItemTitle}>{item.name}</p>
                    {item.description ? <p style={styles.sectionText}>{truncateText(item.description, 120)}</p> : null}
                    <p style={styles.listItemMeta}>Обновлен {relativeTime(item.updated_at)}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => navigate({ to: workspacePaths.template(currentCompanyId, item.id) })}
                  >
                    Открыть
                  </Button>
                </div>
              ))}
            </div>
          </SectionCard>
        ) : null}
      </div>
    </WorkspaceShell>
  );
}
