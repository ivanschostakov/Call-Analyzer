import { useEffect, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';

import { createAnalysisRouteAnalysisPost, useGetAnalysisRouteAnalysisAnalysisIdGet } from '../api/generated/client';
import { CriterionAnswerType } from '../api/generated/model/criterionAnswerType';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { AnalysisCompactDetail } from '../components/reports/analysis-compact-detail';
import { getReportsStyles } from '../components/reports/reports.styles';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { useViewport } from '../hooks/use-viewport';
import { getErrorMessage } from '../lib/utils';
import { useTheme } from '../theme/theme';

type RetryCriterionDraft = {
  criterion_id?: number | null;
  name: string;
  description: string;
  prompt: string;
  answer_type: CriterionAnswerType;
  position: number;
};

function buildRetryCriterionDrafts(
  criteria: Array<{
    criterion_id?: number | null;
    criterion_name: string;
    criterion_description?: string | null;
    criterion_prompt?: string | null;
    answer_type: CriterionAnswerType;
    position?: number;
  }>,
): RetryCriterionDraft[] {
  return [...criteria]
    .sort((left, right) => (left.position ?? 0) - (right.position ?? 0))
    .map((criterion, index) => ({
      criterion_id: criterion.criterion_id ?? null,
      name: criterion.criterion_name,
      description: criterion.criterion_description ?? '',
      prompt: criterion.criterion_prompt ?? '',
      answer_type: criterion.answer_type,
      position: criterion.position ?? index,
    }));
}

export function AnalysisDetailPage({ analysisId }: { analysisId: number }) {
  const navigate = useNavigate();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getReportsStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const analysisQuery = useGetAnalysisRouteAnalysisAnalysisIdGet(analysisId, {
    query: {
      enabled: Boolean(analysisId),
    },
  });
  const analysis = analysisQuery.data;
  const [showRetryEditor, setShowRetryEditor] = useState(false);
  const [retryInstructions, setRetryInstructions] = useState('');
  const [retryCriteria, setRetryCriteria] = useState<RetryCriterionDraft[]>([]);
  const [isRetrying, setIsRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const canRetry = Boolean(analysis?.transcription_id && analysis?.template_id);
  const templateReportPath =
    analysis?.template_id != null ? workspacePaths.templateReports(analysis.company_id, analysis.template_id) : null;

  useEffect(() => {
    if (!analysis) {
      return;
    }

    setRetryInstructions(analysis.instructions ?? '');
    setRetryCriteria(buildRetryCriterionDrafts(analysis.criteria_evaluated));
    setRetryError(null);
    setShowRetryEditor(false);
  }, [analysis]);

  function resetRetryDrafts() {
    if (!analysis) {
      return;
    }

    setRetryInstructions(analysis.instructions ?? '');
    setRetryCriteria(buildRetryCriterionDrafts(analysis.criteria_evaluated));
    setRetryError(null);
  }

  function updateRetryCriterion(index: number, patch: Partial<RetryCriterionDraft>) {
    setRetryCriteria((current) =>
      current.map((criterion, criterionIndex) => (criterionIndex === index ? { ...criterion, ...patch } : criterion)),
    );
  }

  async function handleRetryAnalysis(useEditedDrafts: boolean) {
    if (!analysis?.transcription_id || !analysis.template_id) {
      return;
    }

    const criteria = (useEditedDrafts ? retryCriteria : buildRetryCriterionDrafts(analysis.criteria_evaluated)).map((criterion, index) => ({
      criterion_id: criterion.criterion_id ?? undefined,
      name: criterion.name.trim() || `Критерий ${index + 1}`,
      description: criterion.description.trim() || undefined,
      prompt: criterion.prompt.trim() || undefined,
      answer_type: criterion.answer_type,
      position: criterion.position,
    }));
    const instructions = useEditedDrafts ? retryInstructions : analysis.instructions;

    try {
      setIsRetrying(true);
      setRetryError(null);
      const result = await createAnalysisRouteAnalysisPost({
        transcription_id: analysis.transcription_id,
        template_id: analysis.template_id,
        replace_existing: true,
        instructions,
        criteria,
      });
      await invalidateWorkspaceQueries();
      setShowRetryEditor(false);
      await navigate({ to: workspacePaths.analysis(result.id) });
    } catch (error) {
      setRetryError(getErrorMessage(error));
    } finally {
      setIsRetrying(false);
    }
  }

  return (
    <WorkspaceShell
      title={analysis ? analysis.template_name : 'Анализ'}
      section="reports"
      companyId={analysis?.company_id ?? null}
      wideContent
      compactTopbar
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.analyses(nextCompanyId) })}
    >
      <div style={{ ...styles.standalone, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {analysisQuery.isError ? (
          <p style={{ ...styles.emptyState, color: tokens.danger }}>{getErrorMessage(analysisQuery.error)}</p>
        ) : null}
        {analysisQuery.isPending ? <p style={styles.emptyState}>Загружаем анализ...</p> : null}

        {analysis ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
              <Button onClick={() => void handleRetryAnalysis(false)} disabled={!canRetry || isRetrying}>
                {isRetrying && !showRetryEditor ? 'Повторяем...' : 'Повторить анализ'}
              </Button>
              <Button
                variant={showRetryEditor ? 'secondary' : 'ghost'}
                onClick={() => {
                  if (!showRetryEditor) {
                    resetRetryDrafts();
                  }
                  setShowRetryEditor((current) => !current);
                }}
                disabled={!canRetry || isRetrying}
              >
                {showRetryEditor ? 'Скрыть правки' : 'Повторить с правками'}
              </Button>
              {templateReportPath ? (
                <Button variant="ghost" onClick={() => navigate({ to: templateReportPath })}>
                  К шаблону
                </Button>
              ) : null}
              {!analysis.is_active ? <span style={styles.miniTag}>Неактивный</span> : null}
            </div>

            {showRetryEditor ? (
              <div style={styles.expansionCard}>
                <div style={styles.expansionCardHeader}>
                  <p style={styles.expansionCardTitle}>Правки перед повторным анализом</p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <Label htmlFor="analysis-retry-instructions">Инструкция</Label>
                    <Textarea
                      id="analysis-retry-instructions"
                      value={retryInstructions}
                      onChange={(event) => setRetryInstructions(event.target.value)}
                      placeholder="Уточните правила анализа перед повтором"
                    />
                  </div>

                  {retryCriteria.map((criterion, index) => (
                    <div
                      key={`${criterion.criterion_id ?? 'draft'}-${index}`}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 10,
                        padding: 12,
                        borderRadius: 14,
                        background: tokens.surface,
                      }}
                    >
                      <div
                        style={{
                          display: 'grid',
                          gridTemplateColumns: viewport.isMobile ? '1fr' : 'minmax(0, 1fr) 180px',
                          gap: 10,
                        }}
                      >
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          <Label htmlFor={`analysis-retry-name-${index}`}>Название критерия</Label>
                          <Input
                            id={`analysis-retry-name-${index}`}
                            value={criterion.name}
                            onChange={(event) => updateRetryCriterion(index, { name: event.target.value })}
                          />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          <Label htmlFor={`analysis-retry-type-${index}`}>Тип ответа</Label>
                          <Select
                            id={`analysis-retry-type-${index}`}
                            value={criterion.answer_type}
                            onChange={(event) =>
                              updateRetryCriterion(index, {
                                answer_type: event.target.value as CriterionAnswerType,
                              })
                            }
                          >
                            {Object.values(CriterionAnswerType).map((answerType) => (
                              <option key={answerType} value={answerType}>
                                {answerType}
                              </option>
                            ))}
                          </Select>
                        </div>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <Label htmlFor={`analysis-retry-description-${index}`}>Описание</Label>
                        <Textarea
                          id={`analysis-retry-description-${index}`}
                          value={criterion.description}
                          onChange={(event) => updateRetryCriterion(index, { description: event.target.value })}
                          placeholder="Что именно должен проверять критерий"
                        />
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <Label htmlFor={`analysis-retry-prompt-${index}`}>Промпт критерия</Label>
                        <Textarea
                          id={`analysis-retry-prompt-${index}`}
                          value={criterion.prompt}
                          onChange={(event) => updateRetryCriterion(index, { prompt: event.target.value })}
                          placeholder="Как анализатор должен оценивать этот критерий"
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {retryError ? <p style={{ ...styles.expansionCardText, color: tokens.danger }}>{retryError}</p> : null}

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  <Button onClick={() => void handleRetryAnalysis(true)} disabled={!canRetry || isRetrying || !retryCriteria.length}>
                    {isRetrying ? 'Повторяем...' : 'Применить правки и повторить'}
                  </Button>
                  <Button variant="ghost" onClick={resetRetryDrafts} disabled={isRetrying}>
                    Сбросить правки
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {analysis ? <AnalysisCompactDetail analysis={analysis} mode="standalone" /> : null}
      </div>
    </WorkspaceShell>
  );
}
