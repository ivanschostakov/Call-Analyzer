import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Bot, MessageSquarePlus, Send, UserRound, X } from 'lucide-react';

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
import { ContextCallList } from '../components/mentor/context-call-list';
import { CriteriaSelectionPanel } from '../components/mentor/criteria-selection-panel';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { SectionCard } from '../components/ui/section-card';
import { Select } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
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
  const { tokens } = useTheme();
  const viewport = useViewport();
  const pageStyles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const canManageCurrentTeam = canManageTeam(auth.user?.role);
  const previousFilteredAnalysisIdsRef = useRef<Set<number>>(new Set());
  const messageViewportRef = useRef<HTMLDivElement | null>(null);
  const [templateId, setTemplateId] = useState<number | null>(null);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);
  const [showContextSetupModal, setShowContextSetupModal] = useState(false);
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
  const activeThread = activeThreadId ? threads.find((thread) => thread.id === activeThreadId) ?? null : null;
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
    setShowContextSetupModal(false);
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

  useEffect(() => {
    if (!activeThread || activeThread.template_id == null) {
      return;
    }

    setTemplateId((currentTemplateId) => currentTemplateId ?? activeThread.template_id ?? null);
  }, [activeThread]);

  useEffect(() => {
    if (!showContextSetupModal || typeof document === 'undefined') {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [showContextSetupModal]);

  useEffect(() => {
    if (!showContextSetupModal || typeof window === 'undefined') {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setShowContextSetupModal(false);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showContextSetupModal]);

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

  function startNewDialog() {
    setActiveThreadId(null);
    setPrompt('');
    setShowContextSetupModal(true);
  }

  function handleThreadSelect(value: string) {
    if (value === 'new') {
      startNewDialog();
      return;
    }

    const nextThreadId = Number(value);
    if (!Number.isFinite(nextThreadId)) {
      return;
    }

    setActiveThreadId(nextThreadId);
    setShowContextSetupModal(false);
  }

  function openContextSetupModal() {
    setShowContextSetupModal(true);
  }

  function closeContextSetupModal() {
    setShowContextSetupModal(false);
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

  useEffect(() => {
    if (!messageViewportRef.current) {
      return;
    }
    messageViewportRef.current.scrollTop = messageViewportRef.current.scrollHeight;
  }, [threadMessages, sendMutation.isPending]);

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
  const isNewDialog = activeThreadId === null;
  const dialogSelectValue = activeThreadId === null ? 'new' : String(activeThreadId);

  return (
    <WorkspaceShell
      title="Ментор"
      section="mentor"
      companyId={companyId}
      wideContent
      compactTopbar
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.mentor(nextCompanyId) })}
      actions={
        <div style={mentorHeaderActionsStyle(viewport.isMobile)}>
          <Select
            value={dialogSelectValue}
            onChange={(event) => handleThreadSelect(event.target.value)}
            style={{ minWidth: viewport.isMobile ? '100%' : 250 }}
          >
            <option value="new">Новый диалог</option>
            {threads.map((thread) => (
              <option key={thread.id} value={thread.id}>
                {truncateText(thread.title, 64)}
              </option>
            ))}
          </Select>

          <Button
            variant="primary"
            size="sm"
            onClick={startNewDialog}
            style={viewport.isMobile ? { width: '100%' } : undefined}
          >
            <MessageSquarePlus size={15} />
            + Новый диалог
          </Button>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 0 }}>
        {errors}
        <SectionCard
          title={isNewDialog ? 'Контекст нового диалога' : 'Контекст сообщений'}
          description={`Выбрано звонков: ${selectedAnalysisIdsList.length} из ${filteredAnalyses.length} · критериев: ${selectedColumns.length} из ${columns.length}`}
          actions={
            <Button variant="ghost" size="sm" onClick={openContextSetupModal}>
              {isNewDialog ? 'Задать контекст' : 'Изменить контекст'}
            </Button>
          }
        >
          <p style={pageStyles.subtleText}>
            {activeTemplate?.name ? `Шаблон: ${activeTemplate.name}` : 'Выберите шаблон, звонки и критерии перед первым сообщением.'}
          </p>
        </SectionCard>

        <section
          style={{
            ...pageStyles.section,
            padding: 0,
            overflow: 'hidden',
            minHeight: viewport.isMobile ? '68vh' : 'calc(100vh - 250px)',
            display: 'grid',
            gridTemplateRows: 'auto minmax(0, 1fr) auto',
            gap: 0,
          }}
        >
          <div
            style={{
              padding: viewport.isMobile ? '14px 14px 12px' : '16px 18px 14px',
              borderBottom: `1px solid ${tokens.surfaceStrong}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 10,
            }}
          >
            <div style={{ minWidth: 0 }}>
              <h2 style={{ margin: 0, fontSize: 19, fontWeight: 700, color: tokens.text }}>
                {threadDetailQuery.data?.title ?? activeThread?.title ?? 'Новый диалог'}
              </h2>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: tokens.textMuted }}>
                {activeTemplate?.name ?? 'Выберите шаблон и контекст для диалога'}
              </p>
            </div>
          </div>

          <div
            ref={messageViewportRef}
            style={{
              overflowY: 'auto',
              padding: viewport.isMobile ? 12 : 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
              background: tokens.surfaceMuted,
            }}
          >
            {threadMessages.length ? threadMessages.map(renderMessage) : <p style={pageStyles.mutedText}>Напишите первое сообщение ментору.</p>}
            {sendMutation.isPending ? <p style={pageStyles.mutedText}>Ментор готовит ответ...</p> : null}
          </div>

          <form
            onSubmit={handleSendMessage}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 10,
              padding: viewport.isMobile ? 12 : 16,
              borderTop: `1px solid ${tokens.surfaceStrong}`,
              background: tokens.surface,
            }}
          >
            <Textarea
              id="mentor-prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Например: где у меня повторяются слабые места и что тренировать в первую очередь?"
              style={{ minHeight: viewport.isMobile ? 82 : 92 }}
            />
            {sendMutation.isError ? <p style={pageStyles.errorText}>{getErrorMessage(sendMutation.error)}</p> : null}
            {!templateId || !selectedAnalysisIdsList.length || !selectedColumns.length ? (
              <p style={pageStyles.subtleText}>
                Для отправки выберите шаблон, звонки и критерии через кнопку «{isNewDialog ? 'Задать контекст' : 'Изменить контекст'}».
              </p>
            ) : null}
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button type="submit" disabled={!canSend}>
                <Send size={15} />
                {sendMutation.isPending ? 'Отправляем...' : 'Отправить'}
              </Button>
            </div>
          </form>
        </section>

        {showContextSetupModal ? (
          <>
            <div style={contextModalBackdropStyle(tokens)} onClick={closeContextSetupModal} />
            <div style={contextModalWrapStyle(viewport.isMobile)}>
              <section
                role="dialog"
                aria-modal="true"
                aria-labelledby="mentor-context-modal-title"
                style={contextModalCardStyle(tokens, viewport.isMobile)}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: 12,
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <h2 id="mentor-context-modal-title" style={{ margin: 0, fontSize: 19, lineHeight: 1.25, color: tokens.text }}>
                      {isNewDialog ? 'Контекст нового диалога' : 'Контекст сообщений'}
                    </h2>
                    <p style={{ margin: '6px 0 0', fontSize: 13, lineHeight: 1.55, color: tokens.textMuted }}>
                      {isNewDialog
                        ? 'Выберите шаблон, критерии и звонки, которые ментор должен использовать в новом диалоге.'
                        : 'Обновите шаблон, критерии и звонки для следующих сообщений в текущем диалоге.'}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={closeContextSetupModal}
                    aria-label="Закрыть окно настройки контекста"
                    style={contextModalCloseStyle(tokens)}
                  >
                    <X size={16} />
                  </button>
                </div>

                <div style={{ display: 'grid', gap: 12, overflowY: 'auto', minHeight: 0, paddingRight: 2 }}>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: viewport.isMobile ? '1fr' : 'repeat(auto-fit, minmax(170px, 1fr))',
                      gap: 10,
                    }}
                  >
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
                      <Label htmlFor="mentor-search">Поиск звонков</Label>
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

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    <Button variant="ghost" size="sm" onClick={() => setAllRowsSelection(true)} disabled={!filteredIds.length}>
                      Все звонки
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setAllRowsSelection(false)} disabled={!selectedAnalysisIdsList.length}>
                      Очистить звонки
                    </Button>
                  </div>

                  <CriteriaSelectionPanel
                    columns={columns}
                    selectedColumnKeys={selectedColumnKeys}
                    onToggleColumn={toggleColumnSelection}
                    onSelectAllColumns={() => setAllColumnsSelection(true)}
                    onClearColumns={() => setAllColumnsSelection(false)}
                  />

                  <ContextCallList
                    pageItems={pageItems}
                    selectedAnalysisIds={selectedAnalysisIds}
                    transcriptionsById={transcriptionsById}
                    activeTemplateName={activeTemplate?.name}
                    currentPage={safePage}
                    totalPages={totalPages}
                    onPrevPage={() => setPage((current) => Math.max(1, current - 1))}
                    onNextPage={() => setPage((current) => Math.min(totalPages, current + 1))}
                    onToggleAnalysisSelection={toggleAnalysisSelection}
                  />
                </div>

                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: 10,
                    flexWrap: 'wrap',
                  }}
                >
                  <p style={pageStyles.subtleText}>
                    Выбрано звонков: {selectedAnalysisIdsList.length} · критериев: {selectedColumns.length}
                  </p>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <Button variant="ghost" size="sm" onClick={closeContextSetupModal}>
                      Закрыть
                    </Button>
                    <Button
                      size="sm"
                      onClick={closeContextSetupModal}
                      disabled={!templateId || !selectedAnalysisIdsList.length || !selectedColumns.length}
                    >
                      {isNewDialog ? 'Сохранить контекст' : 'Применить изменения'}
                    </Button>
                  </div>
                </div>
              </section>
            </div>
          </>
        ) : null}
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

function mentorHeaderActionsStyle(mobile: boolean): React.CSSProperties {
  return {
    display: 'flex',
    flexDirection: mobile ? 'column' : 'row',
    alignItems: mobile ? 'stretch' : 'center',
    gap: 8,
    minWidth: 0,
    width: mobile ? '100%' : 'auto',
  };
}

function contextModalBackdropStyle(tokens: ReturnType<typeof useTheme>['tokens']): React.CSSProperties {
  return {
    position: 'fixed',
    inset: 0,
    background: tokens.mode === 'dark' ? 'rgba(8, 10, 12, 0.58)' : 'rgba(16, 22, 30, 0.34)',
    zIndex: 70,
    animation: 'reportOverlayFadeIn 180ms ease',
  };
}

function contextModalWrapStyle(mobile: boolean): React.CSSProperties {
  return {
    position: 'fixed',
    inset: mobile ? 10 : 16,
    zIndex: 71,
    display: 'grid',
    placeItems: 'center',
  };
}

function contextModalCardStyle(
  tokens: ReturnType<typeof useTheme>['tokens'],
  mobile: boolean,
): React.CSSProperties {
  return {
    width: mobile ? '100%' : 'min(960px, calc(100vw - 48px))',
    maxHeight: mobile ? 'calc(100vh - 20px)' : 'calc(100vh - 56px)',
    background: tokens.surface,
    borderRadius: tokens.radiusLg,
    border: `1px solid ${tokens.surfaceStrong}`,
    boxShadow: tokens.shadowLg,
    display: 'grid',
    gridTemplateRows: 'auto minmax(0, 1fr) auto',
    gap: 12,
    padding: mobile ? 14 : 18,
    animation: 'reportDrawerIn 220ms ease',
  };
}

function contextModalCloseStyle(tokens: ReturnType<typeof useTheme>['tokens']): React.CSSProperties {
  return {
    width: 32,
    height: 32,
    borderRadius: tokens.radiusSm,
    border: `1px solid ${tokens.surfaceStrong}`,
    background: tokens.surface,
    color: tokens.textMuted,
    display: 'inline-grid',
    placeItems: 'center',
    cursor: 'pointer',
    flexShrink: 0,
  };
}
