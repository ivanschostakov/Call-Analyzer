import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Bot, MessageSquarePlus, Send, UserRound } from 'lucide-react';

import {
  useListAnalysisRouteAnalysisGet,
  useListCriteriaRouteCriteriaGet,
  useListEmployeesRouteEmployeesGet,
  useListTemplatesRouteTemplatesGet,
  useListTranscriptionsTranscriptionsCompanyIdGet,
} from '../api/generated/client';
import {
  createMentorMessage,
  getMentorThread,
  listMentorThreads,
  type MentorMessageResponse,
  type MentorThreadDetailResponse,
} from '../api/mentor';
import { queryClient } from '../app/query-client';
import { workspacePaths } from '../app/workspace';
import { useAuth } from '../auth/context';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { getReportsStyles } from '../components/reports/reports.styles';
import { useViewport } from '../hooks/use-viewport';
import { buildReportColumns } from '../lib/reporting';
import {
  canManageTeam,
  formatDateTime,
  formatUserLabel,
  getErrorMessage,
  resolveCallDate,
  resolveConversationEmployeeUserId,
  truncateText,
} from '../lib/utils';
import { useTheme } from '../theme/theme';
import { useWorkspace } from '../workspace/workspace-context';
import { getWorkspacePageStyles } from './workspace-page.styles';

const PAGE_SIZE = 8;

function messageQueryKey(threadId: number | null) {
  return ['mentor', 'thread', threadId] as const;
}

function threadsQueryKey(companyId: number) {
  return ['mentor', 'threads', companyId] as const;
}

export function MentorPage({ companyId }: { companyId: number }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const workspace = useWorkspace();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const pageStyles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const reportStyles = getReportsStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const canManageCurrentTeam = canManageTeam(auth.user?.role);
  const previousFilteredAnalysisIdsRef = useRef<Set<number>>(new Set());
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [employeeFilter, setEmployeeFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [prompt, setPrompt] = useState('');
  const [selectedAnalysisIds, setSelectedAnalysisIds] = useState<Set<number>>(new Set());
  const [selectedColumnKeys, setSelectedColumnKeys] = useState<Set<string>>(new Set());

  const analysesQuery = useListAnalysisRouteAnalysisGet(
    { company_id: companyId },
    {
      query: { enabled: Boolean(companyId) },
    },
  );
  const transcriptionsQuery = useListTranscriptionsTranscriptionsCompanyIdGet(companyId, {
    query: { enabled: Boolean(companyId) },
  });
  const templatesQuery = useListTemplatesRouteTemplatesGet(
    { company_id: companyId },
    {
      query: { enabled: Boolean(companyId) },
    },
  );
  const employeesQuery = useListEmployeesRouteEmployeesGet(
    { company_id: companyId },
    {
      query: { enabled: Boolean(companyId && canManageCurrentTeam) },
    },
  );
  const criteriaQuery = useListCriteriaRouteCriteriaGet(
    { template_id: templateId ?? 0 },
    {
      query: { enabled: Boolean(templateId) },
    },
  );
  const threadsQuery = useQuery({
    queryKey: threadsQueryKey(companyId),
    queryFn: () => listMentorThreads(companyId),
    enabled: Boolean(companyId),
  });
  const threadDetailQuery = useQuery({
    queryKey: messageQueryKey(activeThreadId),
    queryFn: () => getMentorThread(activeThreadId as number),
    enabled: Boolean(activeThreadId),
  });
  const sendMutation = useMutation({
    mutationFn: createMentorMessage,
    onSuccess(result) {
      setActiveThreadId(result.thread.id);
      setPrompt('');
      queryClient.setQueryData<MentorThreadDetailResponse>(messageQueryKey(result.thread.id), (current) => ({
        ...(current ?? { ...result.thread, messages: [] }),
        ...result.thread,
        messages: [...(current?.messages ?? []), result.user_message, result.assistant_message],
      }));
      void queryClient.invalidateQueries({ queryKey: threadsQueryKey(companyId) });
    },
  });

  const analyses = analysesQuery.data ?? [];
  const transcriptions = transcriptionsQuery.data?.items ?? [];
  const templates = templatesQuery.data ?? [];
  const threads = threadsQuery.data ?? [];
  const threadMessages = threadDetailQuery.data?.messages ?? [];
  const currentCompany = workspace.getCompanyById(companyId);
  const activeTemplate = templateId ? templates.find((item) => item.id === templateId) ?? null : null;
  const transcriptionsById = useMemo(() => new Map(transcriptions.map((item) => [item.id, item])), [transcriptions]);
  const columns = useMemo(() => buildReportColumns(criteriaQuery.data), [criteriaQuery.data]);
  const selectedColumns = useMemo(() => columns.filter((column) => selectedColumnKeys.has(column.key)), [columns, selectedColumnKeys]);

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

  useEffect(() => {
    setTemplateId(null);
    setActiveThreadId(null);
    setSearch('');
    setDateFrom('');
    setDateTo('');
    setEmployeeFilter('all');
    setPage(1);
    setPrompt('');
    setSelectedAnalysisIds(new Set());
    setSelectedColumnKeys(new Set());
    previousFilteredAnalysisIdsRef.current = new Set();
  }, [companyId]);

  useEffect(() => {
    if (!templateId && templates.length) {
      setTemplateId(templates[0].id);
    }
  }, [templateId, templates]);

  useEffect(() => {
    setSelectedColumnKeys(new Set(columns.map((column) => column.key)));
  }, [columns, templateId]);

  const filteredAnalyses = useMemo(() => {
    const lowerSearch = search.trim().toLowerCase();
    if (!templateId) {
      return [];
    }

    return [...analyses]
      .filter((analysis) => {
        if (analysis.template_id !== templateId) {
          return false;
        }
        const transcription = analysis.transcription_id ? transcriptionsById.get(analysis.transcription_id) ?? null : null;
        if (employeeFilter !== 'all' && (!transcription || resolveConversationEmployeeUserId(transcription) !== Number(employeeFilter))) {
          return false;
        }
        const callDate = new Date(resolveCallDate(transcription ?? { created_at: analysis.created_at }));
        if (dateFrom && callDate < new Date(`${dateFrom}T00:00:00`)) {
          return false;
        }
        if (dateTo && callDate > new Date(`${dateTo}T23:59:59.999`)) {
          return false;
        }
        if (!lowerSearch) {
          return true;
        }
        return [analysis.summary, transcription?.original_filename]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(lowerSearch));
      })
      .sort((left, right) => {
        const leftTranscription = left.transcription_id ? transcriptionsById.get(left.transcription_id) ?? null : null;
        const rightTranscription = right.transcription_id ? transcriptionsById.get(right.transcription_id) ?? null : null;
        return new Date(resolveCallDate(rightTranscription ?? { created_at: right.created_at })).getTime()
          - new Date(resolveCallDate(leftTranscription ?? { created_at: left.created_at })).getTime();
      });
  }, [analyses, dateFrom, dateTo, employeeFilter, search, templateId, transcriptionsById]);

  function filteredAnalysisIds() {
    return filteredAnalyses.map((analysis) => analysis.id);
  }

  const filteredIds = useMemo(() => filteredAnalysisIds(), [filteredAnalyses]);
  const selectedAnalysisIdsList = useMemo(
    () => filteredIds.filter((analysisId) => selectedAnalysisIds.has(analysisId)),
    [filteredIds, selectedAnalysisIds],
  );
  const totalPages = Math.max(1, Math.ceil(filteredAnalyses.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = filteredAnalyses.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  useEffect(() => {
    setPage((currentPage) => Math.min(currentPage, totalPages));
  }, [totalPages]);

  useEffect(() => {
    setSelectedAnalysisIds((current) => {
      const previous = previousFilteredAnalysisIdsRef.current;
      const next = new Set<number>();
      filteredIds.forEach((analysisId) => {
        if (!previous.has(analysisId) || current.has(analysisId)) {
          next.add(analysisId);
        }
      });
      return next;
    });
    previousFilteredAnalysisIdsRef.current = new Set(filteredIds);
  }, [filteredIds]);

  function toggleAnalysisSelection(analysisId: number) {
    setSelectedAnalysisIds((current) => {
      const next = new Set(current);
      if (next.has(analysisId)) {
        next.delete(analysisId);
      } else {
        next.add(analysisId);
      }
      return next;
    });
  }

  function setAllRowsSelection(selected: boolean) {
    setSelectedAnalysisIds(selected ? new Set(filteredIds) : new Set());
  }

  function toggleColumnSelection(columnKey: string) {
    setSelectedColumnKeys((current) => {
      const next = new Set(current);
      if (next.has(columnKey)) {
        next.delete(columnKey);
      } else {
        next.add(columnKey);
      }
      return next;
    });
  }

  function setAllColumnsSelection(selected: boolean) {
    setSelectedColumnKeys(selected ? new Set(columns.map((column) => column.key)) : new Set());
  }

  async function handleSendMessage(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!templateId || !prompt.trim() || !selectedAnalysisIdsList.length || !selectedColumns.length) {
      return;
    }
    await sendMutation.mutateAsync({
      thread_id: activeThreadId,
      company_id: companyId,
      template_id: templateId,
      analysis_ids: selectedAnalysisIdsList,
      columns: selectedColumns.map((column) => column.key),
      prompt: prompt.trim(),
    });
  }

  function renderMessage(message: MentorMessageResponse) {
    const isUser = message.role === 'user';
    return (
      <div
        key={message.id}
        style={{
          display: 'flex',
          gap: 10,
          alignItems: 'flex-start',
          alignSelf: isUser ? 'flex-end' : 'stretch',
          maxWidth: isUser ? 'min(680px, 100%)' : '100%',
        }}
      >
        {!isUser ? (
          <span style={avatarStyle(tokens.accentSoft, tokens.accent)}>
            <Bot size={16} />
          </span>
        ) : null}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            padding: 14,
            borderRadius: 16,
            background: isUser ? tokens.accentSoft : tokens.surfaceMuted,
            color: tokens.text,
            minWidth: 0,
            flex: isUser ? '0 1 auto' : 1,
          }}
        >
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.65, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{message.content}</p>
          <p style={pageStyles.subtleText}>
            {formatDateTime(message.created_at)} · {message.summarized_row_count}/{message.row_count} строк
            {message.omitted_row_count ? ` · пропущено ${message.omitted_row_count}` : ''}
          </p>
        </div>
        {isUser ? (
          <span style={avatarStyle(tokens.surfaceMuted, tokens.textMuted)}>
            <UserRound size={16} />
          </span>
        ) : null}
      </div>
    );
  }

  const canSend = Boolean(templateId && prompt.trim() && selectedAnalysisIdsList.length && selectedColumns.length && !sendMutation.isPending);
  const errors = [analysesQuery.error, transcriptionsQuery.error, templatesQuery.error, criteriaQuery.error, employeesQuery.error, threadsQuery.error, threadDetailQuery.error]
    .filter(Boolean)
    .map((error, index) => (
      <p key={index} style={pageStyles.errorText}>
        {getErrorMessage(error)}
      </p>
    ));

  return (
    <WorkspaceShell
      title="AI Mentor"
      section="mentor"
      companyId={companyId}
      wideContent
      compactTopbar
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.mentor(nextCompanyId) })}
    >
      <div style={pageStyles.stack}>
        {errors}
        <div style={{ display: 'grid', gridTemplateColumns: viewport.isCompactNav ? '1fr' : '300px minmax(0, 1fr)', gap: 16, alignItems: 'start' }}>
          <section style={pageStyles.section}>
            <div style={pageStyles.sectionHeader}>
              <div>
                <h2 style={pageStyles.sectionTitle}>Диалоги</h2>
                <p style={pageStyles.sectionText}>{currentCompany?.name ?? 'Компания'}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setActiveThreadId(null)}>
                <MessageSquarePlus size={15} />
                Новый
              </Button>
            </div>
            <div style={pageStyles.list}>
              {threads.length ? (
                threads.map((thread) => (
                  <button
                    key={thread.id}
                    type="button"
                    onClick={() => setActiveThreadId(thread.id)}
                    style={{
                      ...threadButtonStyle(tokens),
                      background: thread.id === activeThreadId ? tokens.accentSoft : tokens.surfaceMuted,
                    }}
                  >
                    <span style={{ fontWeight: 700 }}>{truncateText(thread.title, 72)}</span>
                    <span style={pageStyles.subtleText}>{formatDateTime(thread.updated_at)}</span>
                  </button>
                ))
              ) : (
                <p style={pageStyles.mutedText}>Диалогов пока нет.</p>
              )}
            </div>
          </section>

          <div style={pageStyles.stack}>
            <section style={pageStyles.section}>
              <div style={pageStyles.sectionHeader}>
                <div>
                  <h2 style={pageStyles.sectionTitle}>Контекст</h2>
                  <p style={pageStyles.sectionText}>
                    {selectedAnalysisIdsList.length} строк · {selectedColumns.length} колонок
                  </p>
                </div>
                <div style={pageStyles.rowActions}>
                  <Button variant="ghost" size="sm" onClick={() => setAllRowsSelection(true)} disabled={!filteredIds.length}>
                    Все строки
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setAllRowsSelection(false)} disabled={!selectedAnalysisIdsList.length}>
                    Очистить строки
                  </Button>
                </div>
              </div>

              <div style={pageStyles.formGrid}>
                <div style={pageStyles.fieldStack}>
                  <Label htmlFor="mentor-template">Шаблон</Label>
                  <Select
                    id="mentor-template"
                    value={templateId ?? ''}
                    onChange={(event) => {
                      setTemplateId(Number(event.target.value) || null);
                      setPage(1);
                    }}
                  >
                    <option value="">Выберите шаблон</option>
                    {templates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    ))}
                  </Select>
                </div>
                <div style={pageStyles.fieldStack}>
                  <Label htmlFor="mentor-search">Поиск</Label>
                  <Input id="mentor-search" value={search} onChange={(event) => setSearch(event.target.value)} />
                </div>
                <div style={pageStyles.fieldStack}>
                  <Label htmlFor="mentor-date-from">С даты</Label>
                  <Input id="mentor-date-from" type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                </div>
                <div style={pageStyles.fieldStack}>
                  <Label htmlFor="mentor-date-to">До даты</Label>
                  <Input id="mentor-date-to" type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
                </div>
                {canManageCurrentTeam ? (
                  <div style={pageStyles.fieldStack}>
                    <Label htmlFor="mentor-employee">Сотрудник</Label>
                    <Select id="mentor-employee" value={employeeFilter} onChange={(event) => setEmployeeFilter(event.target.value)}>
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

              <div style={pageStyles.tagRow}>
                {columns.map((column) => (
                  <label key={column.key} style={columnToggleStyle(tokens, selectedColumnKeys.has(column.key))}>
                    <input
                      type="checkbox"
                      checked={selectedColumnKeys.has(column.key)}
                      onChange={() => toggleColumnSelection(column.key)}
                      style={{ accentColor: tokens.accent }}
                    />
                    <span>{column.label}</span>
                  </label>
                ))}
                <Button variant="ghost" size="sm" onClick={() => setAllColumnsSelection(true)} disabled={!columns.length}>
                  Все колонки
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setAllColumnsSelection(false)} disabled={!selectedColumns.length}>
                  Очистить колонки
                </Button>
              </div>

              <div style={pageStyles.tableWrap}>
                <table style={{ ...pageStyles.table, minWidth: viewport.isMobile ? 680 : 860 }}>
                  <thead>
                    <tr>
                      <th style={pageStyles.tableHead}>Вкл.</th>
                      <th style={pageStyles.tableHead}>Звонок</th>
                      <th style={pageStyles.tableHead}>Дата</th>
                      <th style={pageStyles.tableHead}>Сводка</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageItems.map((analysis) => {
                      const transcription = analysis.transcription_id ? transcriptionsById.get(analysis.transcription_id) ?? null : null;
                      return (
                        <tr key={analysis.id} style={pageStyles.dividerRow}>
                          <td style={{ ...pageStyles.tableCell, width: 70 }}>
                            <input
                              type="checkbox"
                              checked={selectedAnalysisIds.has(analysis.id)}
                              onChange={() => toggleAnalysisSelection(analysis.id)}
                              style={{ accentColor: tokens.accent }}
                            />
                          </td>
                          <td style={pageStyles.tableCell}>
                            <p style={reportStyles.rowTitle}>{transcription?.original_filename ?? `Анализ #${analysis.id}`}</p>
                            <p style={reportStyles.rowMeta}>{activeTemplate?.name ?? analysis.template_name}</p>
                          </td>
                          <td style={pageStyles.tableCell}>{formatDateTime(resolveCallDate(transcription ?? { created_at: analysis.created_at }))}</td>
                          <td style={pageStyles.tableCell}>{truncateText(analysis.summary, 220)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {!pageItems.length ? <p style={{ ...pageStyles.mutedText, padding: 16 }}>Строк нет.</p> : null}
              </div>

              <div style={pageStyles.pagination}>
                <p style={reportStyles.resultsMeta}>
                  Страница {safePage} из {totalPages}
                </p>
                <div style={pageStyles.rowActions}>
                  <Button variant="ghost" size="sm" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={safePage <= 1}>
                    Назад
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setPage((current) => Math.min(totalPages, current + 1))} disabled={safePage >= totalPages}>
                    Вперед
                  </Button>
                </div>
              </div>
            </section>

            <section style={pageStyles.section}>
              <div style={pageStyles.sectionHeader}>
                <div>
                  <h2 style={pageStyles.sectionTitle}>{threadDetailQuery.data?.title ?? 'Новый диалог'}</h2>
                  <p style={pageStyles.sectionText}>{activeTemplate?.name ?? 'Шаблон не выбран'}</p>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 280 }}>
                {threadMessages.length ? threadMessages.map(renderMessage) : <p style={pageStyles.mutedText}>Напишите первое сообщение ментору.</p>}
                {sendMutation.isPending ? (
                  <p style={pageStyles.mutedText}>Ментор готовит ответ...</p>
                ) : null}
              </div>

              <form onSubmit={handleSendMessage} style={pageStyles.fieldStack}>
                <Label htmlFor="mentor-prompt">Сообщение</Label>
                <Textarea
                  id="mentor-prompt"
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  placeholder="Например: где у меня повторяются слабые места и что тренировать в первую очередь?"
                />
                {sendMutation.isError ? <p style={pageStyles.errorText}>{getErrorMessage(sendMutation.error)}</p> : null}
                <div style={pageStyles.rowActions}>
                  <Button type="submit" disabled={!canSend}>
                    <Send size={15} />
                    {sendMutation.isPending ? 'Отправляем...' : 'Отправить'}
                  </Button>
                </div>
              </form>
            </section>
          </div>
        </div>
      </div>
    </WorkspaceShell>
  );
}

function avatarStyle(background: string, color: string): React.CSSProperties {
  return {
    display: 'inline-grid',
    placeItems: 'center',
    flex: '0 0 auto',
    width: 32,
    height: 32,
    borderRadius: 16,
    background,
    color,
  };
}

function threadButtonStyle(tokens: ReturnType<typeof useTheme>['tokens']): React.CSSProperties {
  return {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    width: '100%',
    padding: 12,
    border: 0,
    borderRadius: 14,
    color: tokens.text,
    textAlign: 'left',
    cursor: 'pointer',
  };
}

function columnToggleStyle(tokens: ReturnType<typeof useTheme>['tokens'], selected: boolean): React.CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 10px',
    borderRadius: 14,
    background: selected ? tokens.accentSoft : tokens.surfaceMuted,
    color: tokens.text,
    fontSize: 13,
    cursor: 'pointer',
  };
}
