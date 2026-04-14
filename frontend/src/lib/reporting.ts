import type { AnalysisListItemRead, AnalysisRead, AnalysisResultReadAnswer, CriterionRead, TranscriptionResponse } from '../api/generated/model';
import { formatAnalysisAnswer, formatDetectedEmployeeLabel, formatUserLabel } from './utils';

export type FlattenedCriterionCell = {
  key: string;
  label: string;
  answer: string;
  rawAnswer: AnalysisResultReadAnswer;
  evidence: string[];
  answerType: CriterionRead['answer_type'];
  position: number;
};

export type ReportTableRow = {
  analysisId: number;
  callDate: string;
  createdAt: string;
  updatedAt: string;
  templateName: string;
  summary: string;
  originalFilename: string | null;
  transcriptionId: number | null;
  detectedEmployeeLabel: string | null;
  analysisAuthorLabel: string | null;
  uploadAuthorLabel: string | null;
  criteria: FlattenedCriterionCell[];
};

export type ReportColumnDefinition =
  | { key: 'callDate' | 'createdAt' | 'templateName' | 'originalFilename' | 'summary'; label: string; kind: 'base' }
  | { key: string; label: string; kind: 'criterion'; criterionId: number };

export type TemplateScopedReportState = {
  templateId: number | 'all';
  columns: ReportColumnDefinition[];
  rows: ReportTableRow[];
};

export function flattenAnalysisDetail(detail: AnalysisRead | undefined): FlattenedCriterionCell[] {
  if (!detail) {
    return [];
  }

  return [...detail.criteria_evaluated]
    .sort((left, right) => (left.position ?? 0) - (right.position ?? 0))
    .map((criterion) => ({
      key: criterion.criterion_id ? `criterion-${criterion.criterion_id}` : `criterion-name-${criterion.criterion_name}`,
      label: criterion.criterion_name,
      answer: formatAnalysisAnswer(criterion.answer, criterion.answer_type),
      rawAnswer: criterion.answer,
      evidence: criterion.evidence ?? [],
      answerType: criterion.answer_type,
      position: criterion.position ?? 0,
    }));
}

export function buildReportRows(
  analyses: AnalysisListItemRead[],
  transcriptions: TranscriptionResponse[],
  detailsByAnalysisId: Map<number, AnalysisRead>,
): ReportTableRow[] {
  return analyses.map((analysis) => {
    const transcription = transcriptions.find((item) => item.id === analysis.transcription_id) ?? null;
    const detail = detailsByAnalysisId.get(analysis.id);

    return {
      analysisId: analysis.id,
      callDate: transcription?.call_started_at ?? transcription?.created_at ?? analysis.created_at,
      createdAt: analysis.created_at,
      updatedAt: analysis.updated_at,
      templateName: analysis.template_name,
      summary: analysis.summary,
      originalFilename: transcription?.original_filename ?? null,
      transcriptionId: analysis.transcription_id ?? null,
      detectedEmployeeLabel: transcription ? formatDetectedEmployeeLabel(transcription) : null,
      analysisAuthorLabel: formatUserLabel(analysis.created_by_display_name, analysis.created_by_email),
      uploadAuthorLabel: transcription ? formatUserLabel(transcription.uploaded_by_display_name, transcription.uploaded_by_email) : null,
      criteria: flattenAnalysisDetail(detail),
    };
  });
}

export function buildReportColumns(selectedTemplateCriteria: CriterionRead[] | undefined): ReportColumnDefinition[] {
  const baseColumns: ReportColumnDefinition[] = [
    { key: 'callDate', label: 'Дата звонка', kind: 'base' },
    { key: 'createdAt', label: 'Дата анализа', kind: 'base' },
    { key: 'originalFilename', label: 'Звонок', kind: 'base' },
    { key: 'templateName', label: 'Шаблон', kind: 'base' },
    { key: 'summary', label: 'Сводка', kind: 'base' },
  ];

  if (!selectedTemplateCriteria?.length) {
    return baseColumns;
  }

  const criterionColumns = [...selectedTemplateCriteria]
    .sort((left, right) => (left.position ?? 0) - (right.position ?? 0))
    .map<ReportColumnDefinition>((criterion) => ({
      key: `criterion-${criterion.id}`,
      label: criterion.name,
      kind: 'criterion',
      criterionId: criterion.id,
    }));

  return [...baseColumns, ...criterionColumns];
}
