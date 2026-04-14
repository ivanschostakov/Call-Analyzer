import { X } from 'lucide-react';

import type { AnalysisRead } from '../../api/generated/model';
import { Button } from '../ui/button';
import { useViewport } from '../../hooks/use-viewport';
import { formatAnalysisAnswer, formatDateTime, getAnalysisBooleanValue, getAnalysisPercentageValue } from '../../lib/utils';
import { useTheme } from '../../theme/theme';
import { BooleanAnswer, PercentageAnswer } from './percentage-answer';
import { getReportsStyles } from './reports.styles';

type AnalysisCompactDetailProps = {
  analysis: AnalysisRead | null;
  isLoading?: boolean;
  error?: string | null;
  mode?: 'inline' | 'overlay' | 'sheet' | 'standalone';
  onClose?: () => void;
};

export function AnalysisCompactDetail({
  analysis,
  isLoading = false,
  error,
  mode = 'inline',
  onClose,
}: AnalysisCompactDetailProps) {
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getReportsStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const isStandalone = mode === 'standalone';
  const wrapperStyle =
    mode === 'inline'
      ? styles.panel
      : mode === 'standalone'
        ? styles.standaloneSurface
        : mode === 'sheet'
          ? styles.mobileSheetInner
          : styles.overlaySurface;

  return (
    <div style={wrapperStyle}>
      <div style={styles.panelHeader}>
        <div style={styles.panelTitleBlock}>
          <p style={styles.panelLabel}>Анализ</p>
          <h2 style={styles.panelTitle}>{analysis?.template_name ?? 'Выберите строку'}</h2>
        </div>
        {!isStandalone && onClose ? (
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X size={16} />
          </Button>
        ) : null}
      </div>

      {isLoading ? <p style={styles.panelSummary}>Загружаем данные анализа...</p> : null}
      {error ? <p style={{ ...styles.panelSummary, color: tokens.danger }}>{error}</p> : null}
      {!analysis && !isLoading && !error ? (
        <div style={styles.panelPlaceholder}>
          <p style={styles.panelSummary}>Сводка и ответы по критериям откроются здесь после выбора строки.</p>
        </div>
      ) : null}

      {analysis ? (
        <>
          <div style={styles.panelMeta}>
            <span style={styles.miniTag}>{analysis.template_name}</span>
            {!analysis.is_active ? <span style={styles.miniTag}>Неактивный</span> : null}
            <span style={styles.miniTag}>{formatDateTime(analysis.created_at)}</span>
          </div>

          <p style={styles.panelSummary}>{analysis.summary}</p>

          <div style={styles.criteriaList}>
            {analysis.criteria_evaluated.length ? (
              [...analysis.criteria_evaluated]
                .sort((left, right) => (left.position ?? 0) - (right.position ?? 0))
                .map((criterion) => {
                  const answer = formatAnalysisAnswer(criterion.answer, criterion.answer_type);
                  const percentageValue = getAnalysisPercentageValue(criterion.answer, criterion.answer_type);
                  const booleanValue = getAnalysisBooleanValue(criterion.answer, criterion.answer_type);
                  const isBooleanAnswer = criterion.answer_type === 'boolean';
                  const answerToneStyle =
                    isBooleanAnswer
                      ? criterion.answer === true
                        ? styles.answerPositive
                        : styles.answerNegative
                      : styles.answerNeutral;

                  return (
                    <div key={criterion.id} style={styles.criteriaRow}>
                      <div style={styles.criteriaBody}>
                        <div style={styles.criteriaHeader}>
                          <p style={styles.criteriaName}>{criterion.criterion_name}</p>
                          {percentageValue !== null ? <PercentageAnswer value={percentageValue} /> : null}
                          {percentageValue === null && booleanValue !== null ? <BooleanAnswer value={booleanValue} /> : null}
                          {percentageValue === null && booleanValue === null && isBooleanAnswer ? <span style={{ ...styles.answerPill, ...answerToneStyle }}>{answer}</span> : null}
                        </div>
                        {percentageValue === null && booleanValue === null && !isBooleanAnswer ? <p style={styles.answerText}>{answer}</p> : null}
                      </div>
                    </div>
                  );
                })
            ) : (
              <p style={styles.panelSummary}>Для этого анализа нет сохраненных критериев.</p>
            )}
          </div>

          <details style={styles.details}>
            <summary style={styles.detailsSummary}>Подробнее</summary>
            <div style={styles.detailsContent}>
              {analysis.instructions ? (
                <div>
                  <p style={styles.panelLabel}>Инструкция</p>
                  <p style={styles.detailsText}>{analysis.instructions}</p>
                </div>
              ) : null}

              {[...analysis.criteria_evaluated]
                .sort((left, right) => (left.position ?? 0) - (right.position ?? 0))
                .filter((criterion) => criterion.criterion_description || criterion.criterion_prompt || criterion.evidence?.length)
                .map((criterion) => (
                  <div key={`more-${criterion.id}`} style={styles.moreBlock}>
                    <p style={styles.panelLabel}>{criterion.criterion_name}</p>
                    {criterion.criterion_description ? <p style={styles.detailsText}>{criterion.criterion_description}</p> : null}
                    {criterion.criterion_prompt ? <p style={styles.detailsText}>{criterion.criterion_prompt}</p> : null}
                    {criterion.evidence?.length ? (
                      <div style={styles.evidenceList}>
                        {criterion.evidence.map((evidence, index) => (
                          <p key={`${criterion.id}-${index}`} style={styles.evidenceItem}>
                            {evidence}
                          </p>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
            </div>
          </details>
        </>
      ) : null}
    </div>
  );
}
