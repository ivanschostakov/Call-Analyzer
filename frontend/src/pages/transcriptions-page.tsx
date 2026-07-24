import { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { AudioLines, FileSearch, RotateCcw, Star, Trash2 } from 'lucide-react';

import {
  createAnalysisRouteAnalysisPost,
  useDeleteTranscriptionRouteTranscriptionsCompanyIdFileIdDelete,
  useListAnalysisRouteAnalysisGet,
  useListEmployeesRouteEmployeesGet,
  useListTemplatesRouteTemplatesGet,
  useListTranscriptionsTranscriptionsCompanyIdGet,
  useTranscribeUploadTranscriptionsCompanyIdFileIdPost,
} from '../api/generated/client';
import { favoriteUpload, unfavoriteUpload } from '../api/favorites';
import { assignTranscriptionEmployee } from '../api/transcriptions';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { useAuth } from '../auth/context';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { SectionCard } from '../components/ui/section-card';
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
  matchesEmployeeFilter,
  resolveCallDate,
  transcriptionStatusLabel,
  transcriptionStatusTone,
  truncateText,
} from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

const ANALYSIS_CONCURRENCY = 4;

export function TranscriptionsPage({ companyId }: { companyId: number }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const canManageCurrentTeam = canManageTeam(auth.user?.role);
  const actionStackStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    alignItems: 'stretch',
    minWidth: viewport.isCompactNav ? 152 : 168,
  } as const;
  const actionButtonStyle = {
    width: '100%',
  } as const;
  const [templateSelection, setTemplateSelection] = useState<Record<number, number>>({});
  const [employeeFilter, setEmployeeFilter] = useState('all');
  const [selectedTranscriptionIds, setSelectedTranscriptionIds] = useState<Set<number>>(new Set());
  const [activeTranscriptionTask, setActiveTranscriptionTask] = useState<{
    fileId: string;
    mode: 'start' | 'retry';
    startedAt: number;
  } | null>(null);
  const [activeAnalysisIds, setActiveAnalysisIds] = useState<Set<number>>(new Set());
  const [isBatchAnalyzing, setIsBatchAnalyzing] = useState(false);
  const [analysisFeedback, setAnalysisFeedback] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const transcriptionsQuery = useListTranscriptionsTranscriptionsCompanyIdGet(companyId, {
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
  const templatesQuery = useListTemplatesRouteTemplatesGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId),
      },
    },
  );
  const analysesQuery = useListAnalysisRouteAnalysisGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId),
      },
    },
  );
  const transcribeMutation = useTranscribeUploadTranscriptionsCompanyIdFileIdPost({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const deleteMutation = useDeleteTranscriptionRouteTranscriptionsCompanyIdFileIdDelete({
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
  const employeeAssignmentMutation = useMutation({
    mutationFn: ({ fileId, employeeUserId }: { fileId: string; employeeUserId: number | null }) =>
      assignTranscriptionEmployee(companyId, fileId, employeeUserId),
    onSuccess() {
      void invalidateWorkspaceQueries();
    },
  });

  const templates = templatesQuery.data ?? [];
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
  const transcriptions = useMemo(
    () =>
      [...(transcriptionsQuery.data?.items ?? [])]
        .filter((item) => matchesEmployeeFilter(item, employeeFilter))
        .sort((left, right) => new Date(resolveCallDate(right)).getTime() - new Date(resolveCallDate(left)).getTime()),
    [employeeFilter, transcriptionsQuery.data?.items],
  );
  const analysesByTranscriptionAndTemplate = useMemo(() => {
    const result = new Map<string, { analysisId: number; createdAt: string }>();

    for (const analysis of analysesQuery.data ?? []) {
      if (analysis.transcription_id == null || analysis.template_id == null) {
        continue;
      }

      const key = `${analysis.transcription_id}:${analysis.template_id}`;
      const current = result.get(key);
      if (!current || new Date(analysis.created_at).getTime() > new Date(current.createdAt).getTime()) {
        result.set(key, { analysisId: analysis.id, createdAt: analysis.created_at });
      }
    }

    return result;
  }, [analysesQuery.data]);
  const completedTranscriptions = useMemo(
    () => transcriptions.filter((item) => item.status === 'completed'),
    [transcriptions],
  );
  const selectedCompletedTranscriptionIds = useMemo(
    () => completedTranscriptions.map((item) => item.id).filter((id) => selectedTranscriptionIds.has(id)),
    [completedTranscriptions, selectedTranscriptionIds],
  );
  const allCompletedSelected = completedTranscriptions.length > 0 && selectedCompletedTranscriptionIds.length === completedTranscriptions.length;

  useEffect(() => {
    setEmployeeFilter('all');
    setSelectedTranscriptionIds(new Set());
    setAnalysisFeedback(null);
    setAnalysisError(null);
  }, [companyId]);

  useEffect(() => {
    if (!activeTranscriptionTask) {
      return;
    }

    const item = (transcriptionsQuery.data?.items ?? []).find((entry) => entry.file_id === activeTranscriptionTask.fileId);
    if (!item) {
      setActiveTranscriptionTask(null);
      return;
    }

    if (item.status === 'queued' || item.status === 'processing') {
      return;
    }

    if (new Date(item.updated_at).getTime() >= activeTranscriptionTask.startedAt - 1000) {
      setActiveTranscriptionTask(null);
    }
  }, [activeTranscriptionTask, transcriptionsQuery.data?.items]);

  function getSelectedTemplateId(transcriptionId: number) {
    return templateSelection[transcriptionId] ?? templates[0]?.id ?? 0;
  }

  function getExistingAnalysisId(transcriptionId: number, templateId: number) {
    return analysesByTranscriptionAndTemplate.get(`${transcriptionId}:${templateId}`)?.analysisId ?? null;
  }

  async function handleTranscribe(fileId: string, force = false) {
    setActiveTranscriptionTask({
      fileId,
      mode: force ? 'retry' : 'start',
      startedAt: Date.now(),
    });

    try {
      await transcribeMutation.mutateAsync({ companyId, fileId, params: { force } });
    } catch (error) {
      setActiveTranscriptionTask(null);
      throw error;
    }
  }

  async function handleDelete(fileId: string) {
    if (!window.confirm('Удалить расшифровку и связанный файл?')) {
      return;
    }
    await deleteMutation.mutateAsync({ companyId, fileId });
  }

  async function handleFavoriteToggle(fileId: string, nextValue: boolean) {
    await favoriteMutation.mutateAsync({ fileId, nextValue });
  }

  async function handleEmployeeAssignment(fileId: string, value: string) {
    await employeeAssignmentMutation.mutateAsync({
      fileId,
      employeeUserId: value === 'unresolved' ? null : Number(value),
    });
  }

  async function handleAnalyze(transcriptionId: number) {
    const templateId = getSelectedTemplateId(transcriptionId);
    if (!templateId) {
      return;
    }

    const existingAnalysisId = getExistingAnalysisId(transcriptionId, templateId);
    if (existingAnalysisId) {
      await navigate({ to: workspacePaths.analysis(existingAnalysisId) });
      return;
    }

    try {
      setActiveAnalysisIds((current) => new Set(current).add(transcriptionId));
      setAnalysisFeedback(null);
      setAnalysisError(null);
      const result = await createAnalysisRouteAnalysisPost({
        transcription_id: transcriptionId,
        template_id: templateId,
      });
      await invalidateWorkspaceQueries();
      await navigate({ to: workspacePaths.analysis(result.id) });
    } catch (error) {
      setAnalysisError(getErrorMessage(error));
    } finally {
      setActiveAnalysisIds((current) => {
        const next = new Set(current);
        next.delete(transcriptionId);
        return next;
      });
    }
  }

  async function handleAnalyzeSelected() {
    if (!selectedCompletedTranscriptionIds.length) {
      return;
    }

    const selectedItems = completedTranscriptions
      .filter((item) => selectedTranscriptionIds.has(item.id))
      .map((item) => ({
        transcriptionId: item.id,
        templateId: getSelectedTemplateId(item.id),
      }))
      .filter((item) => item.templateId > 0);
    const itemsToAnalyze = selectedItems.filter((item) => !getExistingAnalysisId(item.transcriptionId, item.templateId));

    if (!itemsToAnalyze.length) {
      setAnalysisFeedback('Для выбранных расшифровок анализ по текущим шаблонам уже существует.');
      setAnalysisError(null);
      return;
    }

    try {
      setIsBatchAnalyzing(true);
      setAnalysisFeedback(null);
      setAnalysisError(null);
      setActiveAnalysisIds((current) => {
        const next = new Set(current);
        itemsToAnalyze.forEach((item) => next.add(item.transcriptionId));
        return next;
      });

      const results = await runWithConcurrency(itemsToAnalyze, ANALYSIS_CONCURRENCY, (item) =>
        createAnalysisRouteAnalysisPost({
          transcription_id: item.transcriptionId,
          template_id: item.templateId,
        }),
      );
      const successCount = results.filter((result) => result.status === 'fulfilled').length;
      const failureCount = results.length - successCount;

      await invalidateWorkspaceQueries();

      if (successCount) {
        setAnalysisFeedback(`Анализ запущен или найден для ${successCount} расшифровок.`);
        setSelectedTranscriptionIds(new Set());
      }
      if (failureCount) {
        const firstFailure = results.find((result): result is PromiseRejectedResult => result.status === 'rejected');
        setAnalysisError(firstFailure ? getErrorMessage(firstFailure.reason) : 'Не удалось проанализировать часть расшифровок.');
      }
    } finally {
      setIsBatchAnalyzing(false);
      setActiveAnalysisIds((current) => {
        const next = new Set(current);
        selectedCompletedTranscriptionIds.forEach((id) => next.delete(id));
        return next;
      });
    }
  }

  function toggleSelectedTranscription(transcriptionId: number) {
    setSelectedTranscriptionIds((current) => {
      const next = new Set(current);
      if (next.has(transcriptionId)) {
        next.delete(transcriptionId);
      } else {
        next.add(transcriptionId);
      }
      return next;
    });
  }

  function setAllCompletedSelection(selected: boolean) {
    setSelectedTranscriptionIds(selected ? new Set(completedTranscriptions.map((item) => item.id)) : new Set());
  }

  return (
    <WorkspaceShell
      title="Расшифровки"
      description="Статусы транскрибации, текст, сегменты и запуск анализа по готовым звонкам."
      section="transcriptions"
      companyId={companyId}
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.transcriptions(nextCompanyId) })}
    >
      <SectionCard
        title="Очередь и результаты"
        description="Для готовых расшифровок можно сразу запускать анализ по выбранному шаблону."
        actions={
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'flex-end' }}>
            <Button variant="ghost" size="sm" onClick={() => setAllCompletedSelection(true)} disabled={!completedTranscriptions.length || allCompletedSelected}>
              Выбрать готовые
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setAllCompletedSelection(false)} disabled={!selectedCompletedTranscriptionIds.length}>
              Снять выбор
            </Button>
            <Button variant="primary" size="sm" onClick={handleAnalyzeSelected} disabled={isBatchAnalyzing || !selectedCompletedTranscriptionIds.length || !templates.length}>
              <FileSearch size={15} />
              {isBatchAnalyzing ? 'Анализируем...' : 'Анализировать выбранные'}
            </Button>
          </div>
        }
      >
        {canManageCurrentTeam ? (
          <div style={{ ...styles.fieldStack, ...styles.responsiveField, marginBottom: 12 }}>
            <Label htmlFor="transcriptions-employee-filter">Сотрудник</Label>
            <Select id="transcriptions-employee-filter" value={employeeFilter} onChange={(event) => setEmployeeFilter(event.target.value)}>
              <option value="all">Все сотрудники</option>
              <option value="unresolved">Не выяснено</option>
              {employeeOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
        ) : null}

        {transcriptionsQuery.isError ? <p style={styles.errorText}>{getErrorMessage(transcriptionsQuery.error)}</p> : null}
        {templatesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(templatesQuery.error)}</p> : null}
        {employeesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(employeesQuery.error)}</p> : null}
        {analysesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(analysesQuery.error)}</p> : null}
        {analysisFeedback ? <p style={{ ...styles.subtleText, color: tokens.success }}>{analysisFeedback}</p> : null}
        {analysisError ? <p style={styles.errorText}>{analysisError}</p> : null}
        {!transcriptionsQuery.isError && !transcriptions.length ? <p style={styles.mutedText}>Расшифровок пока нет.</p> : null}

        {!!transcriptions.length ? (
          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.tableHead}>
                    <input
                      type="checkbox"
                      checked={allCompletedSelected}
                      onChange={(event) => setAllCompletedSelection(event.target.checked)}
                      disabled={!completedTranscriptions.length}
                      aria-label="Выбрать все готовые расшифровки"
                    />
                  </th>
                  <th style={styles.tableHead}>Файл</th>
                  <th style={styles.tableHead}>Дата звонка</th>
                  <th style={styles.tableHead}>Статус</th>
                  <th style={styles.tableHead}>Обновлен</th>
                  <th style={styles.tableHead}>Текст</th>
                  <th style={styles.tableHead}>Анализ</th>
                  <th style={styles.tableHead} />
                </tr>
              </thead>
              <tbody>
                {transcriptions.map((item) => {
                  const isBusy = item.status === 'queued' || item.status === 'processing';
                  const isStartingTask = activeTranscriptionTask?.fileId === item.file_id;
                  const isRetryTask = isStartingTask && activeTranscriptionTask?.mode === 'retry';
                  const isStartTask = isStartingTask && activeTranscriptionTask?.mode === 'start';
                  const selectedTemplateId = getSelectedTemplateId(item.id);
                  const existingAnalysisId = item.status === 'completed' ? getExistingAnalysisId(item.id, selectedTemplateId) : null;
                  const isAnalysisPending = activeAnalysisIds.has(item.id);
                  const startButtonLabel =
                    item.status === 'queued'
                      ? 'В очереди'
                      : item.status === 'processing'
                        ? 'Расшифровывается...'
                        : isStartTask
                          ? 'Запускаем...'
                          : 'Запустить';
                  const retryButtonLabel =
                    item.status === 'queued'
                      ? 'В очереди'
                      : item.status === 'processing'
                        ? 'Расшифровывается...'
                        : isRetryTask
                          ? 'Запускаем...'
                          : 'Повторить';

                  return (
                    <tr key={item.file_id} style={styles.dividerRow}>
                      <td style={styles.tableCell}>
                        <input
                          type="checkbox"
                          checked={selectedTranscriptionIds.has(item.id)}
                          onChange={() => toggleSelectedTranscription(item.id)}
                          disabled={item.status !== 'completed'}
                          aria-label={`Выбрать ${item.original_filename}`}
                        />
                      </td>
                      <td style={styles.tableCell}>
                        <div style={styles.fieldStack}>
                          <span>{item.original_filename}</span>
                          <span style={styles.subtleText}>{item.language || 'Язык не определен'}</span>
                          {canManageCurrentTeam ? (
                            <Label>
                              Сотрудник в звонке
                              <Select
                                value={item.detected_employee_user_id == null ? 'unresolved' : String(item.detected_employee_user_id)}
                                onChange={(event) => handleEmployeeAssignment(item.file_id, event.target.value)}
                                disabled={employeeAssignmentMutation.isPending}
                                aria-label={`Сотрудник в звонке ${item.original_filename}`}
                              >
                                <option value="unresolved">Не выяснено</option>
                                {employeeOptions.map((option) => (
                                  <option key={option.id} value={option.id}>
                                    {option.label}
                                  </option>
                                ))}
                              </Select>
                            </Label>
                          ) : (
                            <span style={styles.subtleText}>Сотрудник в звонке: {formatDetectedEmployeeLabel(item)}</span>
                          )}
                          <span style={styles.subtleText}>Загрузил: {formatUserLabel(item.uploaded_by_display_name, item.uploaded_by_email)}</span>
                        </div>
                      </td>
                      <td style={styles.tableCell}>{formatDateTime(resolveCallDate(item))}</td>
                      <td style={styles.tableCell}>
                        <Badge tone={transcriptionStatusTone(item.status)}>{transcriptionStatusLabel(item.status)}</Badge>
                      </td>
                      <td style={styles.tableCell}>{formatDateTime(item.updated_at)}</td>
                      <td style={styles.tableCell}>
                        {item.text ? (
                          <details>
                            <summary style={{ cursor: 'pointer' }}>{truncateText(item.text, 180)}</summary>
                            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                              {(item.segments ?? []).map((segment, index) => (
                                <p key={`${item.id}-${index}`} style={styles.subtleText}>
                                  {segment.start.toFixed(1)} - {segment.end.toFixed(1)} · {segment.text}
                                </p>
                              ))}
                            </div>
                          </details>
                        ) : (
                          <span style={styles.subtleText}>{item.error_message ?? 'Текст еще не готов.'}</span>
                        )}
                      </td>
                      <td style={styles.tableCell}>
                        {item.status === 'completed' ? (
                          <div style={styles.fieldStack}>
                            <Select
                              value={String(selectedTemplateId)}
                              onChange={(event) =>
                                setTemplateSelection((current) => ({
                                  ...current,
                                  [item.id]: Number(event.target.value),
                                }))
                              }
                              disabled={!templates.length || isAnalysisPending || isBatchAnalyzing}
                            >
                              {templates.map((template) => (
                                <option key={template.id} value={template.id}>
                                  {template.name}
                                </option>
                              ))}
                            </Select>
                            <Button
                              onClick={() => handleAnalyze(item.id)}
                              disabled={!existingAnalysisId && (!templates.length || isAnalysisPending || isBatchAnalyzing)}
                            >
                              <FileSearch size={15} />
                              {existingAnalysisId ? 'К анализу' : isAnalysisPending ? 'Анализируем...' : 'Анализировать'}
                            </Button>
                          </div>
                        ) : (
                          <span style={styles.subtleText}>Анализ доступен после завершения расшифровки.</span>
                        )}
                      </td>
                      <td style={styles.tableCell}>
                        <div style={actionStackStyle}>
                          <Button
                            variant="ghost"
                            size="sm"
                            style={{ ...actionButtonStyle, ...getFavoriteButtonStyle() }}
                            onClick={() => handleFavoriteToggle(item.file_id, !item.is_favorite)}
                            disabled={favoriteMutation.isPending}
                            aria-label={item.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное'}
                            title={item.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное'}
                          >
                            <Star size={14} style={getFavoriteStarStyle(item.is_favorite ?? false)} />
                          </Button>
                          {item.status !== 'completed' ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              style={actionButtonStyle}
                              onClick={() => handleTranscribe(item.file_id, false)}
                              disabled={isBusy || isStartingTask || transcribeMutation.isPending}
                            >
                              <AudioLines size={14} />
                              {startButtonLabel}
                            </Button>
                          ) : null}
                          <Button
                            variant="ghost"
                            size="sm"
                            style={actionButtonStyle}
                            onClick={() => handleTranscribe(item.file_id, true)}
                            disabled={isBusy || isStartingTask || transcribeMutation.isPending}
                          >
                            <RotateCcw size={14} />
                            {retryButtonLabel}
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            style={actionButtonStyle}
                            onClick={() => handleDelete(item.file_id)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 size={14} />
                            Удалить
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </SectionCard>
    </WorkspaceShell>
  );
}
