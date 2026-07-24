import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQueries } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { ArrowDown, ArrowUp, FileSpreadsheet, MoreHorizontal, Plus, Save, Sparkles, Trash2, Upload, X } from 'lucide-react';

import {
  getAnalysisRouteAnalysisAnalysisIdGet,
  useCreateCriterionRouteCriteriaPost,
  useCreateAnalysisRouteAnalysisPost,
  useCreateTemplateRouteTemplatesPost,
  useDeleteCriterionRouteCriteriaCriterionIdDelete,
  useDeleteTemplateRouteTemplatesTemplateIdDelete,
  getGetAnalysisRouteAnalysisAnalysisIdGetQueryOptions,
  uploadAudioUploadsCompanyIdPost,
  useListAnalysisRouteAnalysisGet,
  useListCriteriaRouteCriteriaGet,
  useListEmployeesRouteEmployeesGet,
  useListTemplatesRouteTemplatesGet,
  useListTranscriptionsTranscriptionsCompanyIdGet,
  useUpdateCompanyRouteCompaniesCompanyIdPatch,
  useUpdateCriterionRouteCriteriaCriterionIdPatch,
  useUpdateTemplateRouteTemplatesTemplateIdPatch,
} from '../api/generated/client';
import type { BodyUploadAudioUploadsCompanyIdPost } from '../api/generated/model';
import { deactivateAnalysis } from '../api/analyses';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { summarizeAnalysisReport, type ReportSummaryResponse } from '../api/report-summaries';
import { useAuth } from '../auth/context';
import { AuthenticatedAudio } from '../components/workspace/authenticated-audio';
import { BooleanAnswer, PercentageAnswer } from '../components/reports/percentage-answer';
import { getReportsStyles, getSheetCellStyle, getSheetHeaderCellStyle } from '../components/reports/reports.styles';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { SectionCard } from '../components/ui/section-card';
import { Select } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { useViewport } from '../hooks/use-viewport';
import { runWithConcurrency } from '../lib/async';
import { buildReportColumns, buildReportRows, type ReportColumnDefinition, type ReportTableRow } from '../lib/reporting';
import { CriterionAnswerType } from '../api/generated/model/criterionAnswerType';
import {
  canManageCompany,
  canManageTeam,
  formatAnalysisAnswer,
  formatDateTime,
  formatUserLabel,
  getAnalysisBooleanValue,
  getAnalysisPercentageValue,
  getErrorMessage,
  matchesEmployeeFilter,
  resolveCallDate,
  transcriptionStatusLabel,
  truncateText,
} from '../lib/utils';
import { useTheme } from '../theme/theme';
import { useWorkspace } from '../workspace/workspace-context';
import { getWorkspacePageStyles } from './workspace-page.styles';

const PAGE_SIZE = 12;
const UPLOAD_CONCURRENCY = 3;
const EXPORT_CONCURRENCY = 4;
const DELETE_CONCURRENCY = 4;

type PendingReportUpload = {
  fileId: string;
  filename: string;
  status: 'queued' | 'processing' | 'analyzing' | 'failed';
  transcriptionId?: number;
  error?: string;
};

type CriterionDraft = {
  name: string;
  description: string;
  prompt: string;
  answer_type: keyof typeof CriterionAnswerType;
  position: number;
};

function escapeCsvCell(value: string) {
  const normalized = value.replace(/\r\n/g, '\n');
  if (!/[;"\n]/.test(normalized)) {
    return normalized;
  }
  return `"${normalized.replace(/"/g, '""')}"`;
}

function downloadCsv(filename: string, csvContent: string) {
  const blob = new Blob([`\uFEFF${csvContent}`], { type: 'text/csv;charset=utf-8;' });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

export function AnalysesPage({ companyId, templateId }: { companyId: number; templateId?: number }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const workspace = useWorkspace();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const reportStyles = getReportsStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const pageStyles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const isOwner = canManageCompany(auth.user?.role);
  const canManageCurrentTeam = canManageTeam(auth.user?.role);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const autoAnalysisInFlightRef = useRef<Set<string>>(new Set());
  const selectAllSummaryRowsRef = useRef<HTMLInputElement | null>(null);
  const previousFilteredAnalysisIdsRef = useRef<Set<number>>(new Set());
  const previousSummaryColumnKeysRef = useRef<Set<string>>(new Set());
  const initializedSummaryColumnsTemplateIdRef = useRef<number | null>(null);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState<'desc' | 'asc'>('desc');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [employeeFilter, setEmployeeFilter] = useState('all');
  const [page, setPage] = useState(1);
  const [expandedAnalysisId, setExpandedAnalysisId] = useState<number | null>(null);
  const [pendingUploads, setPendingUploads] = useState<Record<string, PendingReportUpload>>({});
  const [showNewTemplateForm, setShowNewTemplateForm] = useState(false);
  const [showTemplateEditor, setShowTemplateEditor] = useState(false);
  const [templateEditorCriterionId, setTemplateEditorCriterionId] = useState<number | null>(null);
  const [newTemplateDraft, setNewTemplateDraft] = useState({
    name: '',
    description: '',
    instructions: '',
  });
  const [templateDraft, setTemplateDraft] = useState({
    name: '',
    description: '',
    instructions: '',
  });
  const [criteriaDrafts, setCriteriaDrafts] = useState<Record<number, CriterionDraft>>({});
  const [newCriterion, setNewCriterion] = useState<CriterionDraft>({
    name: '',
    description: '',
    prompt: '',
    answer_type: 'text',
    position: 1,
  });
  const [summaryPrompt, setSummaryPrompt] = useState('');
  const [showSummaryAdvanced, setShowSummaryAdvanced] = useState(false);
  const [summaryResult, setSummaryResult] = useState<ReportSummaryResponse | null>(null);
  const [selectedSummaryColumnKeys, setSelectedSummaryColumnKeys] = useState<Set<string>>(new Set());
  const [selectedSummaryAnalysisIds, setSelectedSummaryAnalysisIds] = useState<Set<number>>(new Set());
  const [isUploadingAudio, setIsUploadingAudio] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isExportingCsv, setIsExportingCsv] = useState(false);
  const [isDeletingSelectedAnalyses, setIsDeletingSelectedAnalyses] = useState(false);
  const [tableActionMessage, setTableActionMessage] = useState<string | null>(null);
  const [tableActionError, setTableActionError] = useState<string | null>(null);
  const [savedQuestionFeedback, setSavedQuestionFeedback] = useState<string | null>(null);
  const [savedQuestionError, setSavedQuestionError] = useState<string | null>(null);

  const analysesQuery = useListAnalysisRouteAnalysisGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId),
      },
    },
  );
  const transcriptionsQuery = useListTranscriptionsTranscriptionsCompanyIdGet(companyId, {
    query: {
      enabled: Boolean(companyId),
      refetchInterval(query) {
        const hasPendingUploads = Object.keys(pendingUploads).length > 0;
        const items = query.state.data?.items ?? [];
        return hasPendingUploads || items.some((item) => item.status === 'queued' || item.status === 'processing') ? 5_000 : false;
      },
    },
  });
  const templatesQuery = useListTemplatesRouteTemplatesGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId),
      },
    },
  );
  const employeesQuery = useListEmployeesRouteEmployeesGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId && canManageCurrentTeam),
      },
    },
  );
  const criteriaQuery = useListCriteriaRouteCriteriaGet(
    { template_id: templateId ?? 0 },
    {
      query: {
        enabled: Boolean(templateId),
      },
    },
  );
  const analysisMutation = useCreateAnalysisRouteAnalysisPost({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const createTemplateMutation = useCreateTemplateRouteTemplatesPost({
    mutation: {
      onSuccess() {
        setNewTemplateDraft({ name: '', description: '', instructions: '' });
        setShowNewTemplateForm(false);
        void invalidateWorkspaceQueries();
      },
    },
  });
  const deleteTemplateMutation = useDeleteTemplateRouteTemplatesTemplateIdDelete({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const updateTemplateMutation = useUpdateTemplateRouteTemplatesTemplateIdPatch({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const createCriterionMutation = useCreateCriterionRouteCriteriaPost({
    mutation: {
      onSuccess() {
        setNewCriterion({
          name: '',
          description: '',
          prompt: '',
          answer_type: 'text',
          position: sortedCriteria.length + 1,
        });
        void invalidateWorkspaceQueries();
      },
    },
  });
  const updateCriterionMutation = useUpdateCriterionRouteCriteriaCriterionIdPatch({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const deleteCriterionMutation = useDeleteCriterionRouteCriteriaCriterionIdDelete({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const updateCompanyMutation = useUpdateCompanyRouteCompaniesCompanyIdPatch({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const reportSummaryMutation = useMutation({
    mutationFn: summarizeAnalysisReport,
    onSuccess(result) {
      setSummaryResult(result);
    },
  });

  const analyses = analysesQuery.data ?? [];
  const transcriptions = transcriptionsQuery.data?.items ?? [];
  const templates = templatesQuery.data ?? [];
  const currentCompany = workspace.getCompanyById(companyId);
  const savedSummaryQuestions = currentCompany?.report_summary_questions ?? [];
  const activeTemplate = templateId ? templates.find((item) => item.id === templateId) ?? null : null;
  const sortedCriteria = useMemo(
    () => [...(criteriaQuery.data ?? [])].sort((left, right) => (left.position ?? 0) - (right.position ?? 0)),
    [criteriaQuery.data],
  );
  const isSingleCriterionEditor = templateEditorCriterionId !== null;
  const focusedCriterion = useMemo(
    () => (templateEditorCriterionId ? sortedCriteria.find((criterion) => criterion.id === templateEditorCriterionId) ?? null : null),
    [sortedCriteria, templateEditorCriterionId],
  );
  const criteriaToEdit = useMemo(
    () => (templateEditorCriterionId ? sortedCriteria.filter((criterion) => criterion.id === templateEditorCriterionId) : sortedCriteria),
    [sortedCriteria, templateEditorCriterionId],
  );
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
    setPage(1);
    setSearch('');
    setDateFrom('');
    setDateTo('');
    setEmployeeFilter('all');
    setExpandedAnalysisId(null);
    setPendingUploads({});
    setShowTemplateEditor(false);
    setTemplateEditorCriterionId(null);
    setShowSummaryAdvanced(false);
    setSummaryPrompt('');
    setSummaryResult(null);
    setSelectedSummaryColumnKeys(new Set());
    setSelectedSummaryAnalysisIds(new Set());
    setUploadError(null);
    setTableActionMessage(null);
    setTableActionError(null);
    setSavedQuestionFeedback(null);
    setSavedQuestionError(null);
    previousFilteredAnalysisIdsRef.current = new Set();
    previousSummaryColumnKeysRef.current = new Set();
    initializedSummaryColumnsTemplateIdRef.current = null;
    autoAnalysisInFlightRef.current.clear();
  }, [companyId, templateId]);

  function closeTemplateEditor() {
    setShowTemplateEditor(false);
    setTemplateEditorCriterionId(null);
  }

  function openTemplateEditor() {
    setTemplateEditorCriterionId(null);
    setShowTemplateEditor(true);
  }

  function openCriterionEditor(criterionId: number) {
    setTemplateEditorCriterionId(criterionId);
    setShowTemplateEditor(true);
  }

  useEffect(() => {
    setNewTemplateDraft({ name: '', description: '', instructions: '' });
    setShowNewTemplateForm(false);
  }, [companyId]);

  useEffect(() => {
    if (!activeTemplate) {
      return;
    }

    setTemplateDraft({
      name: activeTemplate.name,
      description: activeTemplate.description ?? '',
      instructions: activeTemplate.instructions ?? '',
    });
  }, [activeTemplate]);

  useEffect(() => {
    if (!sortedCriteria.length) {
      setCriteriaDrafts({});
      setNewCriterion((current) => ({ ...current, position: 1 }));
      return;
    }

    setCriteriaDrafts(
      Object.fromEntries(
        sortedCriteria.map((criterion, index) => [
          criterion.id,
          {
            name: criterion.name,
            description: criterion.description ?? '',
            prompt: criterion.prompt ?? '',
            answer_type: (criterion.answer_type ?? 'text') as keyof typeof CriterionAnswerType,
            position: criterion.position ?? index + 1,
          },
        ]),
      ),
    );
    setNewCriterion((current) => ({ ...current, position: sortedCriteria.length + 1 }));
  }, [sortedCriteria]);

  async function handleTemplateCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createTemplateMutation.mutateAsync({
      data: {
        company_id: companyId,
        name: newTemplateDraft.name,
        description: newTemplateDraft.description || undefined,
        instructions: newTemplateDraft.instructions || undefined,
      },
    });
  }

  async function handleTemplateDelete(templateIdToDelete: number) {
    if (!window.confirm('Удалить шаблон?')) {
      return;
    }
    await deleteTemplateMutation.mutateAsync({ templateId: templateIdToDelete });
    if (templateId === templateIdToDelete) {
      await navigate({ to: workspacePaths.analyses(companyId) });
    }
  }

  async function handleTemplateSave() {
    if (!templateId) {
      return;
    }

    await updateTemplateMutation.mutateAsync({
      templateId,
      data: {
        name: templateDraft.name,
        description: templateDraft.description || undefined,
        instructions: templateDraft.instructions || undefined,
      },
    });
  }

  async function handleCriterionCreate() {
    if (!templateId) {
      return;
    }

    await createCriterionMutation.mutateAsync({
      data: {
        template_id: templateId,
        name: newCriterion.name,
        description: newCriterion.description || undefined,
        prompt: newCriterion.prompt || undefined,
        answer_type: newCriterion.answer_type,
        position: newCriterion.position,
      },
    });
  }

  async function handleCriterionSave(criterionId: number) {
    const draft = criteriaDrafts[criterionId];
    if (!draft) {
      return;
    }

    await updateCriterionMutation.mutateAsync({
      criterionId,
      data: {
        name: draft.name,
        description: draft.description || undefined,
        prompt: draft.prompt || undefined,
        answer_type: draft.answer_type,
        position: draft.position,
      },
    });
  }

  async function handleCriterionDelete(criterionId: number) {
    if (!window.confirm('Удалить критерий?')) {
      return;
    }
    await deleteCriterionMutation.mutateAsync({ criterionId });
  }

  async function moveCriterion(criterionId: number, direction: -1 | 1) {
    const index = sortedCriteria.findIndex((criterion) => criterion.id === criterionId);
    const current = sortedCriteria[index];
    const target = sortedCriteria[index + direction];

    if (!current || !target) {
      return;
    }

    await updateCriterionMutation.mutateAsync({
      criterionId: current.id,
      data: { position: target.position ?? index + direction + 1 },
    });
    await updateCriterionMutation.mutateAsync({
      criterionId: target.id,
      data: { position: current.position ?? index + 1 },
    });
  }

  if (!templateId) {
    return (
      <WorkspaceShell
        title="Отчеты"
        section="reports"
        companyId={companyId}
        compactTopbar
        onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.analyses(nextCompanyId) })}
      >
        {isOwner ? (
          <SectionCard
            title="Новый шаблон"
            description="Создайте шаблон здесь, а затем нажмите «Настроить шаблон», чтобы добавить критерии."
            actions={
              <Button variant={showNewTemplateForm ? 'secondary' : 'ghost'} size="sm" onClick={() => setShowNewTemplateForm((current) => !current)}>
                {showNewTemplateForm ? 'Скрыть форму' : 'Создать шаблон'}
              </Button>
            }
          >
            {showNewTemplateForm ? (
              <form onSubmit={handleTemplateCreate} style={pageStyles.stack}>
                <div style={pageStyles.formGrid}>
                  <div style={pageStyles.fieldStack}>
                    <Label htmlFor="reports-template-name">Название</Label>
                    <Input
                      id="reports-template-name"
                      value={newTemplateDraft.name}
                      onChange={(event) => setNewTemplateDraft((current) => ({ ...current, name: event.target.value }))}
                      placeholder="Например, Продажи B2B"
                    />
                  </div>
                  <div style={pageStyles.fieldStack}>
                    <Label htmlFor="reports-template-description">Описание</Label>
                    <Input
                      id="reports-template-description"
                      value={newTemplateDraft.description}
                      onChange={(event) => setNewTemplateDraft((current) => ({ ...current, description: event.target.value }))}
                      placeholder="Для кого и когда используется"
                    />
                  </div>
                </div>

                <div style={pageStyles.fieldStack}>
                  <Label htmlFor="reports-template-instructions">Инструкция для анализа</Label>
                  <Textarea
                    id="reports-template-instructions"
                    value={newTemplateDraft.instructions}
                    onChange={(event) => setNewTemplateDraft((current) => ({ ...current, instructions: event.target.value }))}
                    placeholder="Общие указания для анализатора"
                  />
                </div>

                {createTemplateMutation.isError ? <p style={pageStyles.errorText}>{getErrorMessage(createTemplateMutation.error)}</p> : null}

                <div style={pageStyles.rowActions}>
                  <Button type="submit" disabled={createTemplateMutation.isPending || !newTemplateDraft.name.trim()}>
                    <Plus size={15} />
                    {createTemplateMutation.isPending ? 'Создаем...' : 'Создать шаблон'}
                  </Button>
                </div>
              </form>
            ) : null}
          </SectionCard>
        ) : null}

        <SectionCard title="Шаблоны" description="Отчеты открываются внутри выбранного шаблона.">
          {templatesQuery.isError ? <p style={pageStyles.errorText}>{getErrorMessage(templatesQuery.error)}</p> : null}
          {!templatesQuery.isError && !templates.length ? <p style={pageStyles.mutedText}>Шаблонов пока нет.</p> : null}

          <div style={pageStyles.list}>
            {templates.map((template) => (
              <div key={template.id} style={pageStyles.listItem}>
                <div style={pageStyles.listItemBody}>
                  <p style={pageStyles.listItemTitle}>{template.name}</p>
                  {template.description ? <p style={pageStyles.sectionText}>{truncateText(template.description, 180)}</p> : null}
                  <p style={pageStyles.listItemMeta}>Обновлен {formatDateTime(template.updated_at)}</p>
                </div>
                <div style={pageStyles.rowActions}>
                  <Button variant="primary" size="sm" onClick={() => navigate({ to: workspacePaths.templateReports(companyId, template.id) })}>
                    <FileSpreadsheet size={15} />
                    Открыть отчет
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => navigate({ to: workspacePaths.template(companyId, template.id) })}>
                    Настроить шаблон
                  </Button>
                  {isOwner ? (
                    <Button variant="danger" size="sm" onClick={() => handleTemplateDelete(template.id)} disabled={deleteTemplateMutation.isPending}>
                      <Trash2 size={14} />
                      Удалить
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </SectionCard>
      </WorkspaceShell>
    );
  }

  const filteredAnalyses = useMemo(() => {
    const lowerSearch = search.trim().toLowerCase();

    return [...analyses]
      .filter((analysis) => {
        if (analysis.template_id !== templateId) {
          return false;
        }

        const transcription = transcriptions.find((item) => item.id === analysis.transcription_id);
        if (employeeFilter !== 'all' && (!transcription || !matchesEmployeeFilter(transcription, employeeFilter))) {
          return false;
        }
        const callDate = new Date(resolveCallDate(transcription ?? { created_at: analysis.created_at }));
        if (dateFrom) {
          const from = new Date(`${dateFrom}T00:00:00`);
          if (callDate < from) {
            return false;
          }
        }

        if (dateTo) {
          const to = new Date(`${dateTo}T23:59:59.999`);
          if (callDate > to) {
            return false;
          }
        }

        if (!lowerSearch) {
          return true;
        }

        return [analysis.summary, transcription?.original_filename]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(lowerSearch));
      })
      .sort((left, right) => {
        const factor = sort === 'desc' ? -1 : 1;
        const leftTranscription = transcriptions.find((item) => item.id === left.transcription_id);
        const rightTranscription = transcriptions.find((item) => item.id === right.transcription_id);
        const leftDate = new Date(resolveCallDate(leftTranscription ?? { created_at: left.created_at })).getTime();
        const rightDate = new Date(resolveCallDate(rightTranscription ?? { created_at: right.created_at })).getTime();
        return factor * (leftDate - rightDate);
      });
  }, [analyses, dateFrom, dateTo, employeeFilter, search, sort, templateId, transcriptions]);
  const filteredAnalysisIds = useMemo(() => filteredAnalyses.map((analysis) => analysis.id), [filteredAnalyses]);

  const totalPages = Math.max(1, Math.ceil(filteredAnalyses.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageItems = filteredAnalyses.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const transcriptionsById = useMemo(() => new Map(transcriptions.map((item) => [item.id, item])), [transcriptions]);
  const analysesByTranscriptionId = useMemo(() => {
    const result = new Map<number, number[]>();

    analyses.forEach((analysis) => {
      if (analysis.transcription_id == null) {
        return;
      }

      const existing = result.get(analysis.transcription_id) ?? [];
      existing.push(analysis.template_id ?? 0);
      result.set(analysis.transcription_id, existing);
    });

    return result;
  }, [analyses]);

  useEffect(() => {
    setPage((currentPage) => Math.min(currentPage, totalPages));
  }, [totalPages]);

  const detailQueries = useQueries({
    queries: pageItems.map((analysis) => ({
      ...getGetAnalysisRouteAnalysisAnalysisIdGetQueryOptions(analysis.id),
      staleTime: 60_000,
    })),
  });

  const detailsByAnalysisId = useMemo(() => {
    const result = new Map<number, NonNullable<(typeof detailQueries)[number]['data']>>();

    pageItems.forEach((analysis, index) => {
      const detail = detailQueries[index]?.data;
      if (detail) {
        result.set(analysis.id, detail);
      }
    });

    return result;
  }, [detailQueries, pageItems]);

  const rows = useMemo(() => buildReportRows(pageItems, transcriptions, detailsByAnalysisId), [detailsByAnalysisId, pageItems, transcriptions]);
  const columns = useMemo(() => buildReportColumns(criteriaQuery.data), [criteriaQuery.data]);
  const pendingUploadList = useMemo(() => Object.values(pendingUploads), [pendingUploads]);
  const selectedSummaryColumns = useMemo(
    () => columns.filter((column) => selectedSummaryColumnKeys.has(column.key)),
    [columns, selectedSummaryColumnKeys],
  );
  const selectedSummaryAnalysisIdsList = useMemo(
    () => filteredAnalysisIds.filter((analysisId) => selectedSummaryAnalysisIds.has(analysisId)),
    [filteredAnalysisIds, selectedSummaryAnalysisIds],
  );
  const allFilteredSummaryRowsSelected = filteredAnalysisIds.length > 0 && selectedSummaryAnalysisIdsList.length === filteredAnalysisIds.length;
  const someFilteredSummaryRowsSelected = selectedSummaryAnalysisIdsList.length > 0 && !allFilteredSummaryRowsSelected;

  useEffect(() => {
    setExpandedAnalysisId((current) => (current != null && rows.some((row) => row.analysisId === current) ? current : null));
  }, [rows]);

  useEffect(() => {
    setSelectedSummaryAnalysisIds((current) => {
      const previousFilteredIds = previousFilteredAnalysisIdsRef.current;
      const next = new Set<number>();
      filteredAnalysisIds.forEach((analysisId) => {
        if (!previousFilteredIds.has(analysisId) || current.has(analysisId)) {
          next.add(analysisId);
        }
      });
      return next;
    });
    previousFilteredAnalysisIdsRef.current = new Set(filteredAnalysisIds);
  }, [filteredAnalysisIds]);

  useEffect(() => {
    const availableColumnKeys = columns.map((column) => column.key);
    setSelectedSummaryColumnKeys((current) => {
      if (templateId && initializedSummaryColumnsTemplateIdRef.current !== templateId) {
        initializedSummaryColumnsTemplateIdRef.current = templateId;
        return new Set(availableColumnKeys);
      }

      const previousColumnKeys = previousSummaryColumnKeysRef.current;
      const next = new Set<string>();
      availableColumnKeys.forEach((columnKey) => {
        if (!previousColumnKeys.has(columnKey) || current.has(columnKey)) {
          next.add(columnKey);
        }
      });
      return next;
    });
    previousSummaryColumnKeysRef.current = new Set(availableColumnKeys);
  }, [columns]);

  useEffect(() => {
    if (selectAllSummaryRowsRef.current) {
      selectAllSummaryRowsRef.current.indeterminate = someFilteredSummaryRowsSelected;
    }
  }, [someFilteredSummaryRowsSelected]);

  useEffect(() => {
    if (!templateId || !pendingUploadList.length) {
      return;
    }

    pendingUploadList.forEach((entry) => {
      const transcription = transcriptions.find((item) => item.file_id === entry.fileId);
      if (!transcription) {
        return;
      }

      if (transcription.status === 'failed') {
        setPendingUploads((current) => {
          const existing = current[entry.fileId];
          if (!existing || (existing.status === 'failed' && existing.error === transcription.error_message)) {
            return current;
          }

          return {
            ...current,
            [entry.fileId]: {
              ...existing,
              status: 'failed',
              transcriptionId: transcription.id,
              error: transcription.error_message ?? 'Транскрибация завершилась ошибкой.',
            },
          };
        });
        return;
      }

      if (transcription.status === 'completed') {
        const existingTemplateIds = analysesByTranscriptionId.get(transcription.id) ?? [];
        if (existingTemplateIds.includes(templateId)) {
          setPendingUploads((current) => {
            if (!(entry.fileId in current)) {
              return current;
            }
            const next = { ...current };
            delete next[entry.fileId];
            return next;
          });
          return;
        }

        if (autoAnalysisInFlightRef.current.has(entry.fileId)) {
          return;
        }

        autoAnalysisInFlightRef.current.add(entry.fileId);
        setPendingUploads((current) => {
          const existing = current[entry.fileId];
          if (!existing) {
            return current;
          }
          return {
            ...current,
            [entry.fileId]: {
              ...existing,
              status: 'analyzing',
              transcriptionId: transcription.id,
              error: undefined,
            },
          };
        });

        void analysisMutation
          .mutateAsync({
            data: {
              transcription_id: transcription.id,
              template_id: templateId,
            },
          })
          .then(async () => {
            autoAnalysisInFlightRef.current.delete(entry.fileId);
            setPendingUploads((current) => {
              if (!(entry.fileId in current)) {
                return current;
              }
              const next = { ...current };
              delete next[entry.fileId];
              return next;
            });
            await invalidateWorkspaceQueries();
          })
          .catch((error) => {
            autoAnalysisInFlightRef.current.delete(entry.fileId);
            setPendingUploads((current) => {
              const existing = current[entry.fileId];
              if (!existing) {
                return current;
              }
              return {
                ...current,
                [entry.fileId]: {
                  ...existing,
                  status: 'failed',
                  transcriptionId: transcription.id,
                  error: getErrorMessage(error),
                },
              };
            });
          });
        return;
      }

      const nextStatus = transcription.status === 'processing' ? 'processing' : 'queued';
      setPendingUploads((current) => {
        const existing = current[entry.fileId];
        if (!existing || (existing.status === nextStatus && existing.transcriptionId === transcription.id)) {
          return current;
        }

        return {
          ...current,
          [entry.fileId]: {
            ...existing,
            status: nextStatus,
            transcriptionId: transcription.id,
            error: undefined,
          },
        };
      });
    });
  }, [analysisMutation, analysesByTranscriptionId, pendingUploadList, templateId, transcriptions]);

  async function handleDirectUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length || !templateId) {
      return;
    }

    try {
      setIsUploadingAudio(true);
      setUploadError(null);
      const results = await runWithConcurrency(files, UPLOAD_CONCURRENCY, (file) =>
        uploadAudioUploadsCompanyIdPost(
          companyId,
          { file } as unknown as BodyUploadAudioUploadsCompanyIdPost,
        ),
      );
      const uploadedItems = results
        .filter((result): result is PromiseFulfilledResult<Awaited<ReturnType<typeof uploadAudioUploadsCompanyIdPost>>> => result.status === 'fulfilled')
        .map((result) => result.value);
      const failedCount = results.length - uploadedItems.length;

      if (uploadedItems.length) {
        setPendingUploads((current) => ({
          ...current,
          ...Object.fromEntries(
            uploadedItems.map((uploaded) => [
              uploaded.file_id,
              {
                fileId: uploaded.file_id,
                filename: uploaded.original_filename,
                status: uploaded.status === 'processing' ? 'processing' : 'queued',
              },
            ]),
          ),
        }));
        setPage(1);
        setDateFrom('');
        setDateTo('');
        setSearch('');
      }

      if (failedCount) {
        const firstFailure = results.find((result): result is PromiseRejectedResult => result.status === 'rejected');
        setUploadError(firstFailure ? getErrorMessage(firstFailure.reason) : 'Не удалось загрузить часть файлов.');
      }
      await invalidateWorkspaceQueries();
    } finally {
      setIsUploadingAudio(false);
      event.target.value = '';
    }
  }

  async function handleReportSummary() {
    if (!templateId || !summaryPrompt.trim() || !selectedSummaryAnalysisIdsList.length || !selectedSummaryColumns.length) {
      return;
    }

    setSummaryResult(null);
    await reportSummaryMutation.mutateAsync({
      company_id: companyId,
      template_id: templateId,
      prompt: summaryPrompt.trim(),
      analysis_ids: selectedSummaryAnalysisIdsList,
      columns: selectedSummaryColumns.map((column) => column.key),
    });
  }

  async function handleExportSelectedAnalyses() {
    if (!selectedSummaryAnalysisIdsList.length) {
      return;
    }

    try {
      setIsExportingCsv(true);
      setTableActionError(null);
      setTableActionMessage(null);

      const selectedAnalyses = filteredAnalyses.filter((analysis) => selectedSummaryAnalysisIds.has(analysis.id));
      const detailResults = await runWithConcurrency(selectedAnalyses, EXPORT_CONCURRENCY, (analysis) =>
        getAnalysisRouteAnalysisAnalysisIdGet(analysis.id),
      );
      const firstFailure = detailResults.find((result): result is PromiseRejectedResult => result.status === 'rejected');
      if (firstFailure) {
        throw firstFailure.reason;
      }

      const detailsById = new Map<number, Awaited<ReturnType<typeof getAnalysisRouteAnalysisAnalysisIdGet>>>(
        selectedAnalyses.map((analysis, index) => [
          analysis.id,
          (detailResults[index] as PromiseFulfilledResult<Awaited<ReturnType<typeof getAnalysisRouteAnalysisAnalysisIdGet>>>).value,
        ]),
      );
      const exportRows = buildReportRows(selectedAnalyses, transcriptions, detailsById);
      const csvLines = [
        columns.map((column) => escapeCsvCell(column.label)).join(';'),
        ...exportRows.map((row) =>
          columns
            .map((column) => {
              if (column.kind === 'base') {
                if (column.key === 'callDate') {
                  return escapeCsvCell(formatDateTime(row.callDate));
                }
                if (column.key === 'createdAt') {
                  return escapeCsvCell(formatDateTime(row.createdAt));
                }
                if (column.key === 'originalFilename') {
                  return escapeCsvCell(row.originalFilename ?? 'Без названия');
                }
                if (column.key === 'templateName') {
                  return escapeCsvCell(row.templateName);
                }
                return escapeCsvCell(row.summary);
              }

              const criterion = row.criteria.find((item) => item.key === `criterion-${column.criterionId}`);
              return escapeCsvCell(criterion?.answer ?? '...');
            })
            .join(';'),
        ),
      ];

      downloadCsv(`analyses-template-${templateId ?? 'all'}-${new Date().toISOString().slice(0, 10)}.csv`, csvLines.join('\n'));
      setTableActionMessage(`CSV экспортирован: ${exportRows.length} строк.`);
    } catch (error) {
      setTableActionError(getErrorMessage(error));
    } finally {
      setIsExportingCsv(false);
    }
  }

  async function handleSaveSummaryPrompt() {
    const normalizedPrompt = summaryPrompt.trim();
    if (!normalizedPrompt) {
      return;
    }

    try {
      setSavedQuestionFeedback(null);
      setSavedQuestionError(null);
      await updateCompanyMutation.mutateAsync({
        companyId,
        data: {
          report_summary_questions: [normalizedPrompt, ...savedSummaryQuestions],
        },
      });
      setSavedQuestionFeedback('Вопрос сохранен в компанию.');
    } catch (error) {
      setSavedQuestionError(getErrorMessage(error));
    }
  }

  async function handleDeleteSavedSummaryPrompt(question: string) {
    try {
      setSavedQuestionFeedback(null);
      setSavedQuestionError(null);
      await updateCompanyMutation.mutateAsync({
        companyId,
        data: {
          report_summary_questions: savedSummaryQuestions.filter((item) => item !== question),
        },
      });
      if (summaryPrompt.trim() === question) {
        setSummaryPrompt('');
      }
      setSavedQuestionFeedback('Сохраненный вопрос удален.');
    } catch (error) {
      setSavedQuestionError(getErrorMessage(error));
    }
  }

  async function handleDeleteSelectedAnalyses() {
    if (!selectedSummaryAnalysisIdsList.length) {
      return;
    }

    if (!window.confirm(`Скрыть выбранные анализы: ${selectedSummaryAnalysisIdsList.length} шт.? Они останутся в истории, но исчезнут из обычных списков.`)) {
      return;
    }

    try {
      setIsDeletingSelectedAnalyses(true);
      setTableActionError(null);
      setTableActionMessage(null);
      const results = await runWithConcurrency(selectedSummaryAnalysisIdsList, DELETE_CONCURRENCY, (analysisId) =>
        deactivateAnalysis(analysisId),
      );
      const successCount = results.filter((result) => result.status === 'fulfilled').length;
      const failureCount = results.length - successCount;

      if (successCount) {
        setSummaryResult(null);
        setSelectedSummaryAnalysisIds((current) => {
          const next = new Set(current);
          selectedSummaryAnalysisIdsList.forEach((analysisId) => next.delete(analysisId));
          return next;
        });
        await invalidateWorkspaceQueries();
      }

      if (failureCount) {
        const firstFailure = results.find((result): result is PromiseRejectedResult => result.status === 'rejected');
        setTableActionError(firstFailure ? getErrorMessage(firstFailure.reason) : 'Не удалось скрыть часть анализов.');
      }
      if (successCount) {
        setTableActionMessage(`Скрыто ${successCount} анализов.`);
      }
    } finally {
      setIsDeletingSelectedAnalyses(false);
    }
  }

  function toggleSummaryRowSelection(analysisId: number) {
    setSelectedSummaryAnalysisIds((current) => {
      const next = new Set(current);
      if (next.has(analysisId)) {
        next.delete(analysisId);
      } else {
        next.add(analysisId);
      }
      return next;
    });
  }

  function setAllSummaryRowsSelection(selected: boolean) {
    setSelectedSummaryAnalysisIds(selected ? new Set(filteredAnalysisIds) : new Set());
  }

  function toggleSummaryColumnSelection(columnKey: string) {
    setSelectedSummaryColumnKeys((current) => {
      const next = new Set(current);
      if (next.has(columnKey)) {
        next.delete(columnKey);
      } else {
        next.add(columnKey);
      }
      return next;
    });
  }

  function setAllSummaryColumnsSelection(selected: boolean) {
    setSelectedSummaryColumnKeys(selected ? new Set(columns.map((column) => column.key)) : new Set());
  }

  function toggleExpandedRow(analysisId: number) {
    setExpandedAnalysisId((current) => (current === analysisId ? null : analysisId));
  }

  function getColumnWidth(column: ReportColumnDefinition) {
    if (column.key === 'callDate') {
      return 176;
    }
    if (column.key === 'createdAt') {
      return 176;
    }
    if (column.key === 'originalFilename') {
      return 250;
    }
    if (column.key === 'templateName') {
      return 170;
    }
    if (column.key === 'summary') {
      return 320;
    }
    return 200;
  }

  function getClampStyle(column: ReportColumnDefinition, expanded: boolean) {
    if (expanded || column.key === 'callDate' || column.key === 'createdAt') {
      return undefined;
    }

    if (column.key === 'summary') {
      return reportStyles.clamp4;
    }

    return reportStyles.clamp2;
  }

  function renderCell(row: ReportTableRow, column: ReportColumnDefinition, expanded: boolean) {
    if (column.kind === 'base') {
      if (column.key === 'callDate') {
        return <span style={expanded ? reportStyles.cellMonoWrap : reportStyles.cellMono}>{formatDateTime(row.callDate)}</span>;
      }
      if (column.key === 'createdAt') {
        return <span style={expanded ? reportStyles.cellMonoWrap : reportStyles.cellMono}>{formatDateTime(row.createdAt)}</span>;
      }

      if (column.key === 'originalFilename') {
        return (
          <div>
            <p
              style={{
                ...reportStyles.rowTitle,
                ...(expanded ? { overflow: 'visible', textOverflow: 'clip', whiteSpace: 'normal' } : reportStyles.clamp2),
              }}
            >
              {row.originalFilename ?? 'Без названия'}
            </p>
            <p style={reportStyles.rowMeta}>#{row.analysisId}</p>
            {row.detectedEmployeeLabel ? <p style={reportStyles.rowMeta}>Сотрудник в звонке: {row.detectedEmployeeLabel}</p> : null}
            {row.uploadAuthorLabel ? <p style={reportStyles.rowMeta}>Загрузил: {row.uploadAuthorLabel}</p> : null}
          </div>
        );
      }

      if (column.key === 'templateName') {
        return <span style={getClampStyle(column, expanded)}>{row.templateName}</span>;
      }

      return (
        <div>
          <span style={getClampStyle(column, expanded)}>{row.summary}</span>
          <p style={reportStyles.rowMeta}>Автор summary: {row.analysisAuthorLabel}</p>
        </div>
      );
    }

    const criterion = row.criteria.find((item) => item.key === `criterion-${column.criterionId}`);
    if (!criterion) {
      return <span style={reportStyles.cellMuted}>...</span>;
    }

    const answerStyle =
      criterion.answerType === 'boolean'
        ? criterion.answer === 'Да'
          ? reportStyles.answerPositive
          : reportStyles.answerNegative
        : reportStyles.answerNeutral;

    if (criterion.answerType === 'percentage') {
      const percentageValue = getAnalysisPercentageValue(criterion.rawAnswer, criterion.answerType);
      if (percentageValue !== null) {
        return <PercentageAnswer value={percentageValue} size="table" />;
      }
    }

    if (criterion.answerType === 'boolean') {
      const booleanValue = getAnalysisBooleanValue(criterion.rawAnswer, criterion.answerType);
      if (booleanValue !== null) {
        return <BooleanAnswer value={booleanValue} size="table" />;
      }
    }

    return <span style={{ ...answerStyle, ...getClampStyle(column, expanded) }}>{criterion.answer}</span>;
  }

  function renderExpandedContent(row: ReportTableRow) {
    const detail = detailsByAnalysisId.get(row.analysisId) ?? null;
    const detailQuery = detailQueries[pageItems.findIndex((item) => item.id === row.analysisId)];
    const transcription = row.transcriptionId ? transcriptionsById.get(row.transcriptionId) ?? null : null;
    const criteriaRows = detail
      ? [...detail.criteria_evaluated]
          .sort((left, right) => (left.position ?? 0) - (right.position ?? 0))
          .map((criterion) => ({
            id: criterion.id,
            name: criterion.criterion_name,
            answer: formatAnalysisAnswer(criterion.answer, criterion.answer_type),
            rawAnswer: criterion.answer,
            answerType: criterion.answer_type,
            evidence: criterion.evidence ?? [],
          }))
      : [];

    return (
      <div
        style={
          viewport.isMobile
            ? { display: 'flex', flexDirection: 'column', gap: 12, minWidth: 0 }
            : reportStyles.expansionLayout
        }
      >
        <div style={reportStyles.expansionColumn}>
          <div style={reportStyles.expansionCard}>
            <div style={reportStyles.expansionCardHeader}>
              <p style={reportStyles.expansionCardTitle}>Критерии</p>
            </div>

            {detailQuery?.isPending ? <p style={reportStyles.expansionCardText}>Загружаем критерии анализа...</p> : null}
            {detailQuery?.isError ? <p style={reportStyles.expansionCardText}>{getErrorMessage(detailQuery.error)}</p> : null}
            {!detailQuery?.isPending && !detailQuery?.isError && !criteriaRows.length ? (
              <p style={reportStyles.expansionCardText}>Для этого анализа нет сохраненных критериев.</p>
            ) : null}

            {criteriaRows.length ? (
              <div style={reportStyles.criteriaList}>
                {criteriaRows.map((criterion) => {
                  const percentageValue = getAnalysisPercentageValue(criterion.rawAnswer, criterion.answerType);
                  const booleanValue = getAnalysisBooleanValue(criterion.rawAnswer, criterion.answerType);
                  const isBooleanAnswer = criterion.answerType === 'boolean';
                  const answerToneStyle =
                    isBooleanAnswer
                      ? criterion.answer === 'Да'
                        ? reportStyles.answerPositive
                        : reportStyles.answerNegative
                      : reportStyles.answerNeutral;

                  return (
                    <div key={criterion.id} style={reportStyles.criteriaRow}>
                      <div style={reportStyles.criteriaBody}>
                        <div style={reportStyles.criteriaHeader}>
                          <p style={reportStyles.criteriaName}>{criterion.name}</p>
                          {percentageValue !== null ? <PercentageAnswer value={percentageValue} /> : null}
                          {percentageValue === null && booleanValue !== null ? <BooleanAnswer value={booleanValue} /> : null}
                          {percentageValue === null && booleanValue === null && isBooleanAnswer ? <span style={{ ...reportStyles.answerPill, ...answerToneStyle }}>{criterion.answer}</span> : null}
                        </div>
                        {percentageValue === null && booleanValue === null && !isBooleanAnswer ? <p style={reportStyles.answerText}>{criterion.answer}</p> : null}
                        {criterion.evidence.length ? (
                          <div style={reportStyles.evidenceList}>
                            {criterion.evidence.map((evidence, index) => (
                              <p key={`${criterion.id}-${index}`} style={reportStyles.evidenceItem}>
                                {evidence}
                              </p>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : null}
          </div>
        </div>

        <div style={reportStyles.expansionColumn}>
          <div style={reportStyles.expansionCard}>
            <div style={reportStyles.expansionCardHeader}>
              <p style={reportStyles.expansionCardTitle}>Аудио и статус</p>
              {transcription ? <span style={reportStyles.miniTag}>{transcriptionStatusLabel(transcription.status)}</span> : null}
            </div>
            {transcription?.media_url ? <AuthenticatedAudio mediaUrl={transcription.media_url} /> : <p style={reportStyles.expansionCardText}>Аудио недоступно.</p>}
          </div>

          <div style={reportStyles.expansionCard}>
            <div style={reportStyles.expansionCardHeader}>
              <p style={reportStyles.expansionCardTitle}>Расшифровка</p>
              {transcription?.language ? <span style={reportStyles.miniTag}>{transcription.language}</span> : null}
            </div>

            {transcription?.text ? <p style={reportStyles.compactTranscript}>{transcription.text}</p> : null}

            {transcription?.segments?.length ? (
              <div style={reportStyles.expansionSegments}>
                {transcription.segments.map((segment, index) => (
                  <p key={`${transcription.id}-${index}`} style={reportStyles.segmentRow}>
                    {segment.start.toFixed(1)} - {segment.end.toFixed(1)} · {segment.text}
                  </p>
                ))}
              </div>
            ) : !transcription?.text ? (
              <p style={reportStyles.expansionCardText}>
                {transcription?.error_message ?? 'Расшифровка еще не готова.'}
              </p>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  const errorMessages = [analysesQuery.error, transcriptionsQuery.error, criteriaQuery.error, employeesQuery.error]
    .filter(Boolean)
    .map((error, index) => (
      <p key={index} style={{ ...reportStyles.resultsMeta, color: tokens.danger }}>
        {getErrorMessage(error)}
      </p>
    ));
  const pendingMessages = pendingUploadList.map((entry) => (
    <p key={entry.fileId} style={{ ...reportStyles.resultsMeta, color: entry.status === 'failed' ? tokens.danger : tokens.textMuted }}>
      {entry.filename} ·{' '}
      {entry.status === 'queued'
        ? 'ждет транскрибацию'
        : entry.status === 'processing'
          ? 'расшифровывается'
          : entry.status === 'analyzing'
            ? 'анализируется и скоро появится в таблице'
            : entry.error ?? 'не удалось обработать файл'}
    </p>
  ));

  return (
    <WorkspaceShell
      title="Отчеты"
      section="reports"
      companyId={companyId}
      wideContent
      compactTopbar
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.analyses(nextCompanyId) })}
      actions={
        <input ref={fileInputRef} type="file" accept="audio/*" multiple hidden onChange={handleDirectUpload} />
      }
    >
      <div style={reportStyles.page}>
        <SectionCard
          title="Фильтры отчета"
          description={activeTemplate ? `Шаблон: ${activeTemplate.name}` : 'Выберите диапазон дат, сортировку, сотрудника и текстовый поиск.'}
          actions={
            <>
              <Button
                variant="primary"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingAudio}
                style={viewport.isMobile ? { width: '100%' } : undefined}
              >
                <Upload size={15} />
                {isUploadingAudio ? 'Загружаем...' : 'Загрузить аудио'}
              </Button>

              {isOwner ? (
                <Button variant="secondary" size="sm" onClick={openTemplateEditor}>
                  Редактировать шаблон
                </Button>
              ) : null}
            </>
          }
        >
          <div style={reportStyles.toolbar}>
            <div style={reportStyles.toolbarGroup}>
              <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} style={reportStyles.control} />
              <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} style={reportStyles.control} />
              <Select value={sort} onChange={(event) => setSort(event.target.value as 'desc' | 'asc')} style={reportStyles.control}>
                <option value="desc">Новые сверху</option>
                <option value="asc">Старые сверху</option>
              </Select>
              {canManageCurrentTeam ? (
                <Select value={employeeFilter} onChange={(event) => setEmployeeFilter(event.target.value)} style={reportStyles.control}>
                  <option value="all">Все сотрудники</option>
                  <option value="unresolved">Не выяснено</option>
                  {employeeOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              ) : null}
            </div>

            <div style={reportStyles.toolbarSearchGroup}>
              <Input
                placeholder="Поиск"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setPage(1);
                }}
                style={reportStyles.search}
              />
            </div>
          </div>
        </SectionCard>

        {errorMessages}
        {uploadError ? <p style={{ ...reportStyles.resultsMeta, color: tokens.danger }}>{uploadError}</p> : null}
        {pendingMessages}

        <SectionCard
          title="Саммаризация отчета"
          description="Выберите строки и колонки текущего отчета, задайте вопрос и получите итоговую текстовую сводку."
          actions={
            <Button variant={showSummaryAdvanced ? 'secondary' : 'ghost'} size="sm" onClick={() => setShowSummaryAdvanced((current) => !current)}>
              {showSummaryAdvanced ? 'Скрыть подробную настройку' : 'Подробная настройка'}
            </Button>
          }
        >
          <div style={pageStyles.fieldStack}>
            <Label htmlFor="report-summary-prompt">Вопрос для саммаризации</Label>
            <Textarea
              id="report-summary-prompt"
              value={summaryPrompt}
              onChange={(event) => setSummaryPrompt(event.target.value)}
              placeholder="Например: Какие главные проблемы, сильные стороны и повторяющиеся паттерны видны по выбранным звонкам?"
            />
          </div>

          {savedSummaryQuestions.length ? (
            <div style={pageStyles.fieldStack}>
              <p style={pageStyles.subtleText}>Сохраненные вопросы компании</p>
              <div style={pageStyles.rowActions}>
                {savedSummaryQuestions.map((question) => (
                  <Fragment key={question}>
                    <Button variant="ghost" size="sm" onClick={() => setSummaryPrompt(question)}>
                      {truncateText(question, 72)}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDeleteSavedSummaryPrompt(question)} disabled={updateCompanyMutation.isPending}>
                      <Trash2 size={14} />
                      Удалить
                    </Button>
                  </Fragment>
                ))}
              </div>
            </div>
          ) : null}

          <div style={pageStyles.rowActions}>
            <Button
              onClick={handleReportSummary}
              disabled={reportSummaryMutation.isPending || !summaryPrompt.trim() || !selectedSummaryAnalysisIdsList.length || !selectedSummaryColumns.length}
            >
              <Sparkles size={15} />
              {reportSummaryMutation.isPending ? 'Готовим summary...' : 'Сделать саммаризацию'}
            </Button>
            <Button variant="ghost" size="sm" onClick={handleSaveSummaryPrompt} disabled={updateCompanyMutation.isPending || !summaryPrompt.trim()}>
              <Save size={15} />
              {updateCompanyMutation.isPending ? 'Сохраняем вопрос...' : 'Сохранить вопрос'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setAllSummaryRowsSelection(true)} disabled={!filteredAnalysisIds.length}>
              Выбрать все строки
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setAllSummaryRowsSelection(false)} disabled={!selectedSummaryAnalysisIdsList.length}>
              Исключить все строки
            </Button>
            <Button variant="ghost" size="sm" onClick={handleExportSelectedAnalyses} disabled={isExportingCsv || !selectedSummaryAnalysisIdsList.length}>
              {isExportingCsv ? 'Готовим CSV...' : 'Экспорт CSV'}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDeleteSelectedAnalyses}
              disabled={isDeletingSelectedAnalyses || !selectedSummaryAnalysisIdsList.length}
            >
              {isDeletingSelectedAnalyses ? 'Скрываем...' : 'Скрыть выбранные'}
            </Button>
          </div>

          <p style={pageStyles.subtleText}>
            В summary включено строк: {selectedSummaryAnalysisIdsList.length} из {filteredAnalyses.length}. Колонок: {selectedSummaryColumns.length} из {columns.length}. Верхние фильтры даты работают по дате звонка.
          </p>
          {savedQuestionFeedback ? <p style={{ ...pageStyles.subtleText, color: tokens.success }}>{savedQuestionFeedback}</p> : null}
          {savedQuestionError ? <p style={pageStyles.errorText}>{savedQuestionError}</p> : null}
          {tableActionMessage ? <p style={{ ...pageStyles.subtleText, color: tokens.success }}>{tableActionMessage}</p> : null}
          {tableActionError ? <p style={pageStyles.errorText}>{tableActionError}</p> : null}

          {showSummaryAdvanced ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 14,
                padding: viewport.isMobile ? 14 : 16,
                borderRadius: tokens.radiusMd,
                border: `1px solid ${tokens.surfaceStrong}`,
                background: tokens.surfaceMuted,
              }}
            >
              <div style={pageStyles.sectionHeader}>
                <div>
                  <p style={pageStyles.sectionTitle}>Колонки для summary</p>
                  <p style={pageStyles.sectionText}>Если ничего специально не исключать, в саммаризацию идут все колонки отчета.</p>
                </div>
                <div style={pageStyles.rowActions}>
                  <Button variant="ghost" size="sm" onClick={() => setAllSummaryColumnsSelection(true)} disabled={!columns.length}>
                    Все колонки
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setAllSummaryColumnsSelection(false)} disabled={!selectedSummaryColumns.length}>
                    Очистить
                  </Button>
                </div>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: viewport.isMobile ? '1fr' : 'repeat(auto-fit, minmax(220px, 1fr))',
                  gap: 10,
                }}
              >
                {columns.map((column) => (
                  <label
                    key={column.key}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '10px 12px',
                      borderRadius: tokens.radiusSm,
                      border: `1px solid ${selectedSummaryColumnKeys.has(column.key) ? tokens.accent : tokens.surfaceStrong}`,
                      background: selectedSummaryColumnKeys.has(column.key) ? tokens.accentSoft : tokens.surface,
                      color: tokens.text,
                      cursor: 'pointer',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedSummaryColumnKeys.has(column.key)}
                      onChange={() => toggleSummaryColumnSelection(column.key)}
                      style={{ accentColor: tokens.accent }}
                    />
                    <span>{column.label}</span>
                  </label>
                ))}
              </div>
            </div>
          ) : null}

          {reportSummaryMutation.isError ? <p style={pageStyles.errorText}>{getErrorMessage(reportSummaryMutation.error)}</p> : null}

          {summaryResult ? (
            <div style={reportStyles.expansionCard}>
              <div style={reportStyles.expansionCardHeader}>
                <p style={reportStyles.expansionCardTitle}>Текстовая саммаризация</p>
                <span style={reportStyles.miniTag}>
                  {summaryResult.summarized_row_count}/{summaryResult.row_count} строк
                </span>
              </div>
              {summaryResult.omitted_row_count > 0 ? (
                <p style={reportStyles.expansionCardText}>
                  В модель поместилась не вся выборка: пропущено строк {summaryResult.omitted_row_count}. Если нужна точнее, сузьте отчет фильтрами или исключите часть строк.
                </p>
              ) : null}
              <p style={reportStyles.expansionCardText}>{summaryResult.text}</p>
            </div>
          ) : null}
        </SectionCard>

        {isOwner && showTemplateEditor ? (
          <>
            <div style={reportStyles.overlayBackdrop} onClick={closeTemplateEditor} />
            <aside
              style={reportStyles.overlayPanel}
              role="dialog"
              aria-modal="true"
              aria-label={isSingleCriterionEditor ? 'Редактор критерия' : 'Редактор критериев и шаблона'}
              onClick={(event) => event.stopPropagation()}
            >
              <div style={reportStyles.overlaySurface}>
                <div style={reportStyles.drawerHeader}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <p style={reportStyles.drawerTitle}>{isSingleCriterionEditor ? 'Редактор критерия' : 'Редактор отчёта'}</p>
                    <p style={reportStyles.drawerSubtitle}>
                      {isSingleCriterionEditor
                        ? focusedCriterion
                          ? `Редактирование критерия: ${focusedCriterion.name}`
                          : 'Редактирование выбранного критерия'
                        : 'Здесь можно быстро изменить шаблон и критерии.'}
                    </p>
                  </div>
                  <button
                    type="button"
                    style={reportStyles.drawerCloseButton}
                    onClick={closeTemplateEditor}
                    aria-label="Закрыть редактор критериев"
                  >
                    <X size={16} />
                  </button>
                </div>

                <div style={reportStyles.drawerBody}>
                  {!isSingleCriterionEditor ? (
                    <section style={reportStyles.drawerSection}>
                      <p style={reportStyles.drawerSectionTitle}>Шаблон</p>

                      <div style={pageStyles.fieldStack}>
                        <Label htmlFor="report-template-name">Название</Label>
                        <Input
                          id="report-template-name"
                          value={templateDraft.name}
                          onChange={(event) => setTemplateDraft((current) => ({ ...current, name: event.target.value }))}
                        />
                      </div>
                      <div style={pageStyles.fieldStack}>
                        <Label htmlFor="report-template-description">Описание</Label>
                        <Input
                          id="report-template-description"
                          value={templateDraft.description}
                          onChange={(event) => setTemplateDraft((current) => ({ ...current, description: event.target.value }))}
                        />
                      </div>
                      <div style={pageStyles.fieldStack}>
                        <Label htmlFor="report-template-instructions">Инструкция</Label>
                        <Textarea
                          id="report-template-instructions"
                          value={templateDraft.instructions}
                          onChange={(event) => setTemplateDraft((current) => ({ ...current, instructions: event.target.value }))}
                        />
                      </div>
                      {updateTemplateMutation.isError ? <p style={pageStyles.errorText}>{getErrorMessage(updateTemplateMutation.error)}</p> : null}
                      <div style={pageStyles.rowActions}>
                        <Button onClick={handleTemplateSave} disabled={updateTemplateMutation.isPending || !templateDraft.name.trim()}>
                          <Save size={15} />
                          Сохранить шаблон
                        </Button>
                        <Button variant="danger" size="sm" onClick={() => handleTemplateDelete(templateId)} disabled={deleteTemplateMutation.isPending}>
                          <Trash2 size={14} />
                          Удалить шаблон
                        </Button>
                      </div>
                    </section>
                  ) : null}

                  {!isSingleCriterionEditor ? (
                    <section style={reportStyles.drawerSection}>
                      <p style={reportStyles.drawerSectionTitle}>Новый критерий</p>

                      <div style={pageStyles.fieldStack}>
                        <Label htmlFor="report-criterion-name">Название</Label>
                        <Input
                          id="report-criterion-name"
                          value={newCriterion.name}
                          onChange={(event) => setNewCriterion((current) => ({ ...current, name: event.target.value }))}
                        />
                      </div>

                      <div style={pageStyles.formGrid}>
                        <div style={pageStyles.fieldStack}>
                          <Label htmlFor="report-criterion-answer-type">Тип ответа</Label>
                          <Select
                            id="report-criterion-answer-type"
                            value={newCriterion.answer_type}
                            onChange={(event) =>
                              setNewCriterion((current) => ({
                                ...current,
                                answer_type: event.target.value as keyof typeof CriterionAnswerType,
                              }))
                            }
                          >
                            {Object.values(CriterionAnswerType).map((answerType) => (
                              <option key={answerType} value={answerType}>
                                {answerType}
                              </option>
                            ))}
                          </Select>
                        </div>
                        <div style={pageStyles.fieldStack}>
                          <Label htmlFor="report-criterion-position">Позиция</Label>
                          <Input
                            id="report-criterion-position"
                            type="number"
                            min={1}
                            value={newCriterion.position}
                            onChange={(event) =>
                              setNewCriterion((current) => ({
                                ...current,
                                position: Number(event.target.value) || 1,
                              }))
                            }
                          />
                        </div>
                      </div>

                      <div style={pageStyles.fieldStack}>
                        <Label htmlFor="report-criterion-description">Описание</Label>
                        <Textarea
                          id="report-criterion-description"
                          value={newCriterion.description}
                          onChange={(event) => setNewCriterion((current) => ({ ...current, description: event.target.value }))}
                        />
                      </div>

                      <div style={pageStyles.fieldStack}>
                        <Label htmlFor="report-criterion-prompt">Prompt</Label>
                        <Textarea
                          id="report-criterion-prompt"
                          value={newCriterion.prompt}
                          onChange={(event) => setNewCriterion((current) => ({ ...current, prompt: event.target.value }))}
                        />
                      </div>

                      {createCriterionMutation.isError ? <p style={pageStyles.errorText}>{getErrorMessage(createCriterionMutation.error)}</p> : null}
                      <div style={pageStyles.rowActions}>
                        <Button onClick={handleCriterionCreate} disabled={createCriterionMutation.isPending || !newCriterion.name.trim()}>
                          <Plus size={15} />
                          Добавить критерий
                        </Button>
                      </div>
                    </section>
                  ) : null}

                  <section style={reportStyles.drawerSection}>
                    <p style={reportStyles.drawerSectionTitle}>{isSingleCriterionEditor ? 'Критерий' : 'Критерии'}</p>
                    {criteriaQuery.isError ? <p style={pageStyles.errorText}>{getErrorMessage(criteriaQuery.error)}</p> : null}
                    {!criteriaQuery.isError && !sortedCriteria.length ? <p style={pageStyles.mutedText}>Критерии еще не добавлены.</p> : null}
                    {!criteriaQuery.isError && isSingleCriterionEditor && !focusedCriterion ? (
                      <p style={pageStyles.mutedText}>Выбранный критерий не найден в текущем шаблоне.</p>
                    ) : null}

                    <div style={pageStyles.list}>
                      {criteriaToEdit.map((criterion) => {
                        const draft = criteriaDrafts[criterion.id];
                        const criterionIndex = sortedCriteria.findIndex((item) => item.id === criterion.id);
                        if (!draft) {
                          return null;
                        }

                        return (
                          <div key={criterion.id} style={reportStyles.criteriaRow}>
                            <div style={pageStyles.fieldStack}>
                              <Label>Название</Label>
                              <Input
                                value={draft.name}
                                onChange={(event) =>
                                  setCriteriaDrafts((current) => ({
                                    ...current,
                                    [criterion.id]: { ...current[criterion.id], name: event.target.value },
                                  }))
                                }
                              />
                            </div>

                            <div style={pageStyles.formGrid}>
                              <div style={pageStyles.fieldStack}>
                                <Label>Тип ответа</Label>
                                <Select
                                  value={draft.answer_type}
                                  onChange={(event) =>
                                    setCriteriaDrafts((current) => ({
                                      ...current,
                                      [criterion.id]: {
                                        ...current[criterion.id],
                                        answer_type: event.target.value as keyof typeof CriterionAnswerType,
                                      },
                                    }))
                                  }
                                >
                                  {Object.values(CriterionAnswerType).map((answerType) => (
                                    <option key={answerType} value={answerType}>
                                      {answerType}
                                    </option>
                                  ))}
                                </Select>
                              </div>
                              <div style={pageStyles.fieldStack}>
                                <Label>Позиция</Label>
                                <Input
                                  type="number"
                                  min={1}
                                  value={draft.position}
                                  onChange={(event) =>
                                    setCriteriaDrafts((current) => ({
                                      ...current,
                                      [criterion.id]: {
                                        ...current[criterion.id],
                                        position: Number(event.target.value) || 1,
                                      },
                                    }))
                                  }
                                />
                              </div>
                            </div>

                            <div style={pageStyles.fieldStack}>
                              <Label>Описание</Label>
                              <Textarea
                                value={draft.description}
                                onChange={(event) =>
                                  setCriteriaDrafts((current) => ({
                                    ...current,
                                    [criterion.id]: { ...current[criterion.id], description: event.target.value },
                                  }))
                                }
                              />
                            </div>
                            <div style={pageStyles.fieldStack}>
                              <Label>Prompt</Label>
                              <Textarea
                                value={draft.prompt}
                                onChange={(event) =>
                                  setCriteriaDrafts((current) => ({
                                    ...current,
                                    [criterion.id]: { ...current[criterion.id], prompt: event.target.value },
                                  }))
                                }
                              />
                            </div>

                            <div style={pageStyles.rowActions}>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => moveCriterion(criterion.id, -1)}
                                disabled={criterionIndex <= 0 || updateCriterionMutation.isPending}
                              >
                                <ArrowUp size={14} />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => moveCriterion(criterion.id, 1)}
                                disabled={criterionIndex === sortedCriteria.length - 1 || updateCriterionMutation.isPending}
                              >
                                <ArrowDown size={14} />
                              </Button>
                              <Button onClick={() => handleCriterionSave(criterion.id)} disabled={updateCriterionMutation.isPending || !draft.name.trim()}>
                                <Save size={15} />
                                Сохранить
                              </Button>
                              <Button variant="danger" size="sm" onClick={() => handleCriterionDelete(criterion.id)} disabled={deleteCriterionMutation.isPending}>
                                <Trash2 size={14} />
                                Удалить
                              </Button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </section>
                </div>
              </div>
            </aside>
          </>
        ) : null}

        {analysesQuery.isPending && !analyses.length ? <p style={reportStyles.emptyState}>Загружаем анализы...</p> : null}
        {!analysesQuery.isPending && !filteredAnalyses.length ? <p style={reportStyles.emptyState}>По этому шаблону анализов пока нет.</p> : null}

        {!!filteredAnalyses.length && !viewport.isMobile ? (
          <div style={reportStyles.sheetWrap}>
            <div style={reportStyles.tableScroller}>
              <table style={reportStyles.table}>
                <thead>
                  <tr>
                    <th
                      style={{
                        ...reportStyles.headerCell,
                        width: 56,
                        textAlign: 'center',
                      }}
                    >
                      <input
                        ref={selectAllSummaryRowsRef}
                        type="checkbox"
                        checked={allFilteredSummaryRowsSelected}
                        onChange={(event) => setAllSummaryRowsSelection(event.target.checked)}
                        onClick={(event) => event.stopPropagation()}
                        title="Включить или исключить все строки текущего отчета из summary"
                        style={{ accentColor: tokens.accent }}
                      />
                    </th>
                    {columns.map((column) => (
                      <th
                        key={column.key}
                        style={{
                          ...reportStyles.headerCell,
                          width: getColumnWidth(column),
                          ...getSheetHeaderCellStyle(tokens, column.key),
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                          <span>{column.label}</span>
                          {isOwner && column.kind === 'criterion' ? (
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                openCriterionEditor(column.criterionId);
                              }}
                              title="Редактировать критерии"
                              aria-label="Редактировать критерии"
                              style={{
                                width: 20,
                                height: 20,
                                borderRadius: 6,
                                border: `1px solid ${tokens.surfaceStrong}`,
                                background: tokens.surface,
                                color: tokens.textSubtle,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                padding: 0,
                                lineHeight: 0,
                                cursor: 'pointer',
                                flexShrink: 0,
                              }}
                            >
                              <MoreHorizontal size={12} />
                            </button>
                          ) : null}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => {
                    const tone = index % 2 === 0 ? 'odd' : 'even';
                    const isExpanded = expandedAnalysisId === row.analysisId;

                    return (
                      <Fragment key={row.analysisId}>
                        <tr
                          style={{
                            ...reportStyles.row,
                            ...(isExpanded ? reportStyles.rowExpanded : {}),
                          }}
                          onClick={() => toggleExpandedRow(row.analysisId)}
                        >
                          <td
                            style={{
                              ...reportStyles.cell,
                              width: 56,
                              textAlign: 'center',
                            }}
                            onClick={(event) => event.stopPropagation()}
                          >
                            <input
                              type="checkbox"
                              checked={selectedSummaryAnalysisIds.has(row.analysisId)}
                              onChange={() => toggleSummaryRowSelection(row.analysisId)}
                              title="Включить строку в summary"
                              style={{ accentColor: tokens.accent }}
                            />
                          </td>
                          {columns.map((column) => (
                            <td
                              key={column.key}
                              style={{
                                ...reportStyles.cell,
                                ...(isExpanded && column.key !== 'callDate' && column.key !== 'createdAt' ? reportStyles.cellExpanded : {}),
                                width: getColumnWidth(column),
                                ...getSheetCellStyle(tokens, column.key, isExpanded ? 'selected' : tone),
                              }}
                            >
                              {renderCell(row, column, isExpanded)}
                            </td>
                          ))}
                        </tr>

                        {isExpanded ? (
                          <tr>
                            <td colSpan={columns.length + 1} style={reportStyles.expansionCell}>
                              {renderExpandedContent(row)}
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {!!filteredAnalyses.length && viewport.isMobile ? (
          <div style={reportStyles.tableMobileList}>
            {rows.map((row) => {
              const isExpanded = expandedAnalysisId === row.analysisId;

              return (
                <div
                  key={row.analysisId}
                  style={{ ...reportStyles.mobileCard, ...(isExpanded ? reportStyles.mobileCardExpanded : {}) }}
                  onClick={() => toggleExpandedRow(row.analysisId)}
                >
                  <div style={reportStyles.mobileCardHeader}>
                    <div style={{ minWidth: 0 }}>
                      <p style={reportStyles.mobileCardTitle}>{row.originalFilename ?? 'Без названия'}</p>
                      <div style={reportStyles.mobileCardMeta}>
                        <span style={reportStyles.miniTag}>{formatDateTime(row.callDate)}</span>
                      </div>
                    </div>
                    <label
                      style={{ display: 'flex', alignItems: 'center', gap: 8, color: tokens.textSubtle }}
                      onClick={(event) => event.stopPropagation()}
                    >
                      <input
                        type="checkbox"
                        checked={selectedSummaryAnalysisIds.has(row.analysisId)}
                        onChange={() => toggleSummaryRowSelection(row.analysisId)}
                        style={{ accentColor: tokens.accent }}
                      />
                      <span>В summary</span>
                    </label>
                  </div>

                  <p style={{ ...reportStyles.mobileCardSummary, ...(isExpanded ? {} : reportStyles.clamp4) }}>{row.summary}</p>
                  {row.detectedEmployeeLabel ? <p style={reportStyles.rowMeta}>Сотрудник в звонке: {row.detectedEmployeeLabel}</p> : null}
                  <p style={reportStyles.rowMeta}>Автор summary: {row.analysisAuthorLabel}</p>
                  {row.uploadAuthorLabel ? <p style={reportStyles.rowMeta}>Загрузил: {row.uploadAuthorLabel}</p> : null}

                  {row.criteria.length ? (
                    <div style={reportStyles.mobileCardCriteria}>
                      {(isExpanded ? row.criteria : row.criteria.slice(0, 3)).map((criterion) => (
                        <span key={criterion.key} style={reportStyles.miniTag}>
                          {isExpanded ? `${criterion.label}: ${criterion.answer}` : truncateText(`${criterion.label}: ${criterion.answer}`, 38)}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  {isExpanded ? (
                    <div style={reportStyles.mobileCardDetails} onClick={(event) => event.stopPropagation()}>
                      {renderExpandedContent(row)}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : null}

        {!!filteredAnalyses.length ? (
          <div style={reportStyles.footerBar}>
            <p style={reportStyles.footerMeta}>
              {filteredAnalyses.length} строк · страница {safePage} из {totalPages}
            </p>
            <div style={reportStyles.toolbarGroup}>
              <Button variant="ghost" size="sm" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={safePage <= 1}>
                Назад
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPage((current) => Math.min(totalPages, current + 1))}
                disabled={safePage >= totalPages}
              >
                Дальше
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </WorkspaceShell>
  );
}
