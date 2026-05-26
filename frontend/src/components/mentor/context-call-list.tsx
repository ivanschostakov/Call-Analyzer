import type { AnalysisListItemRead, TranscriptionResponse } from '../../api/generated/model';
import { formatDateTime, resolveCallDate, truncateText } from '../../lib/utils';
import { useTheme } from '../../theme/theme';
import { Button } from '../ui/button';

type ContextCallListProps = {
  pageItems: AnalysisListItemRead[];
  selectedAnalysisIds: Set<number>;
  transcriptionsById: Map<number, TranscriptionResponse>;
  activeTemplateName?: string | null;
  currentPage: number;
  totalPages: number;
  onPrevPage: () => void;
  onNextPage: () => void;
  onToggleAnalysisSelection: (analysisId: number) => void;
};

export function ContextCallList({
  pageItems,
  selectedAnalysisIds,
  transcriptionsById,
  activeTemplateName,
  currentPage,
  totalPages,
  onPrevPage,
  onNextPage,
  onToggleAnalysisSelection,
}: ContextCallListProps) {
  const { tokens } = useTheme();

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          gap: 10,
          alignItems: 'center',
        }}
      >
        <p style={{ margin: 0, fontSize: 12, color: tokens.textSubtle }}>
          Звонки для контекста · страница {currentPage} из {totalPages}
        </p>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="ghost" size="sm" onClick={onPrevPage} disabled={currentPage <= 1}>
            Назад
          </Button>
          <Button variant="ghost" size="sm" onClick={onNextPage} disabled={currentPage >= totalPages}>
            Вперед
          </Button>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gap: 8,
          maxHeight: 300,
          overflowY: 'auto',
          padding: 2,
          borderRadius: 12,
          background: tokens.surfaceMuted,
          border: `1px solid ${tokens.surfaceStrong}`,
        }}
      >
        {pageItems.map((analysis) => {
          const transcription = analysis.transcription_id ? transcriptionsById.get(analysis.transcription_id) ?? null : null;
          const selected = selectedAnalysisIds.has(analysis.id);

          return (
            <label
              key={analysis.id}
              style={{
                display: 'grid',
                gridTemplateColumns: 'auto minmax(0, 1fr)',
                alignItems: 'flex-start',
                gap: 10,
                padding: '10px 12px',
                borderRadius: 10,
                background: selected ? tokens.accentSoft : tokens.surface,
                border: `1px solid ${selected ? tokens.accent : tokens.surfaceStrong}`,
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={selected}
                onChange={() => onToggleAnalysisSelection(analysis.id)}
                style={{ accentColor: tokens.accent }}
              />
              <div style={{ minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: tokens.text }}>
                  {transcription?.original_filename ?? `Анализ #${analysis.id}`}
                </p>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: tokens.textSubtle }}>
                  {formatDateTime(resolveCallDate(transcription ?? { created_at: analysis.created_at }))} ·{' '}
                  {activeTemplateName ?? analysis.template_name}
                </p>
                <p style={{ margin: '8px 0 0', fontSize: 12, lineHeight: 1.5, color: tokens.textMuted }}>
                  {truncateText(analysis.summary, 200)}
                </p>
              </div>
            </label>
          );
        })}
        {!pageItems.length ? (
          <p style={{ margin: 0, padding: 12, fontSize: 13, lineHeight: 1.6, color: tokens.textMuted }}>
            По фильтрам звонков не найдено.
          </p>
        ) : null}
      </div>
    </section>
  );
}
