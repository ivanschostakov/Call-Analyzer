import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { TrendingDown, TrendingUp } from 'lucide-react';

import { getDailyReport, type DailyReportCallItem } from '../api/daily-report';
import { workspacePaths } from '../app/workspace';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { SectionCard } from '../components/ui/section-card';
import { useViewport } from '../hooks/use-viewport';
import { getErrorMessage } from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

function yesterdayIso(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
}

function ScoreBadge({ score, good }: { score: number; good: boolean }) {
  const { tokens } = useTheme();
  const color = good ? tokens.success : tokens.danger;
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 10px',
        borderRadius: 100,
        fontSize: 13,
        fontWeight: 700,
        fontVariantNumeric: 'tabular-nums',
        background: `${color}22`,
        color,
      }}
    >
      {score.toFixed(1)}%
    </span>
  );
}

function CallsSection({
  calls,
  label,
  good,
  styles,
}: {
  calls: DailyReportCallItem[];
  label: string;
  good: boolean;
  styles: ReturnType<typeof getWorkspacePageStyles>;
}) {
  const { tokens } = useTheme();
  const color = good ? tokens.success : tokens.danger;
  const Icon = good ? TrendingUp : TrendingDown;

  return (
    <SectionCard
      title={label}
      description={`В разделе: ${calls.length} ${calls.length === 1 ? 'звонок' : calls.length < 5 ? 'звонка' : 'звонков'}`}
      actions={<Icon size={18} color={color} />}
    >

      {calls.length === 0 ? (
        <p style={styles.sectionText}>Нет данных.</p>
      ) : (
        <div style={styles.list}>
          {calls.map((call) => (
            <div key={call.analysis_id} style={styles.listItem}>
              <div style={styles.listItemBody}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <ScoreBadge score={call.score} good={good} />
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{call.employee_name}</span>
                  <span style={{ fontSize: 12, color: tokens.textSubtle }}>{call.call_date ?? ''}</span>
                </div>
                <p style={{ ...styles.listItemMeta, fontSize: 13, color: tokens.textMuted }}>{call.call_name}</p>
                {call.summary ? (
                  <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: tokens.text }}>
                    {call.summary}
                  </p>
                ) : null}
              </div>
              <div style={{ alignSelf: 'center', flexShrink: 0 }}>
                <Link to={workspacePaths.analysis(call.analysis_id)} style={{ textDecoration: 'none' }}>
                  <Button variant="secondary" size="sm">Открыть</Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

export function DailyReportPage({ companyId }: { companyId: number }) {
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });

  const [selectedDate, setSelectedDate] = useState(yesterdayIso());

  const reportQuery = useQuery({
    queryKey: ['/daily-report', companyId, selectedDate],
    queryFn: () => getDailyReport(companyId, selectedDate),
    enabled: Boolean(companyId),
    retry: false,
  });

  const report = reportQuery.data;
  const isLoading = reportQuery.isLoading;
  const error = reportQuery.error;

  return (
    <WorkspaceShell
      title="Ежедневный отчёт"
      description="Лучшие и худшие звонки по итогам дня"
      section="daily-report"
      companyId={companyId}
      managerOnly
    >
      <div style={styles.stack}>
        <SectionCard title="Дата отчёта">
          <div style={styles.toolbar}>
            <div>
              {report ? (
                <p style={styles.sectionText}>
                  Среднее качество: <strong>{report.average_score.toFixed(1)}%</strong> · Всего звонков: <strong>{report.total_calls}</strong>
                </p>
              ) : null}
            </div>
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{ width: viewport.isMobile ? '100%' : 200 }}
            />
          </div>
        </SectionCard>

        {isLoading ? (
          <SectionCard title="Отчёт">
            <p style={styles.sectionText}>Загружаем отчёт...</p>
          </SectionCard>
        ) : error ? (
          <SectionCard title="Отчёт">
            <p style={{ ...styles.sectionText, color: tokens.textMuted }}>
              {['Not Found', 'No scored calls found for this date.'].includes(getErrorMessage(error))
                ? 'За этот день нет оценённых звонков. Возможно, звонки ещё не были оценены.'
                : getErrorMessage(error)}
            </p>
          </SectionCard>
        ) : report ? (
          <>
            <CallsSection calls={report.best_calls} label="Лучшие звонки (выше среднего)" good styles={styles} />
            <CallsSection calls={report.worst_calls} label="Худшие звонки (ниже среднего)" good={false} styles={styles} />
          </>
        ) : null}
      </div>
    </WorkspaceShell>
  );
}
