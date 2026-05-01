import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { TrendingDown, TrendingUp } from 'lucide-react';

import { getDailyReport, type DailyReportCallItem } from '../api/daily-report';
import { workspacePaths } from '../app/workspace';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
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

function CallsTable({
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

  if (calls.length === 0) {
    return (
      <div style={styles.section}>
        <div style={styles.sectionHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Icon size={18} color={color} />
            <h2 style={{ ...styles.sectionTitle, color }}>{label}</h2>
          </div>
        </div>
        <p style={styles.sectionText}>Нет данных.</p>
      </div>
    );
  }

  return (
    <div style={styles.section}>
      <div style={styles.sectionHeader}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon size={18} color={color} />
          <h2 style={{ ...styles.sectionTitle, color }}>{label}</h2>
        </div>
        <p style={{ ...styles.sectionText, margin: 0, alignSelf: 'center' }}>
          {calls.length} {calls.length === 1 ? 'звонок' : calls.length < 5 ? 'звонка' : 'звонков'}
        </p>
      </div>
      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.tableHead}>Сотрудник</th>
              <th style={styles.tableHead}>Звонок</th>
              <th style={styles.tableHead}>Шаблон</th>
              <th style={styles.tableHead}>Дата</th>
              <th style={styles.tableHead}>Оценка</th>
              <th style={styles.tableHead} />
            </tr>
          </thead>
          <tbody>
            {calls.map((call, idx) => (
              <tr key={call.analysis_id} style={idx > 0 ? styles.dividerRow : undefined}>
                <td style={styles.tableCell}>{call.employee_name}</td>
                <td style={{ ...styles.tableCell, ...styles.tableCellCompact }}>{call.call_name}</td>
                <td style={{ ...styles.tableCell, ...styles.tableCellMuted, ...styles.tableCellCompact }}>{call.template_name}</td>
                <td style={{ ...styles.tableCell, ...styles.tableCellMuted, whiteSpace: 'nowrap' }}>{call.call_date ?? '—'}</td>
                <td style={styles.tableCell}>
                  <ScoreBadge score={call.score} good={good} />
                </td>
                <td style={{ ...styles.tableCell, textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <Link to={workspacePaths.analysis(call.analysis_id)} style={{ textDecoration: 'none' }}>
                    <Button variant="ghost" size="sm">Открыть</Button>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
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
        <div style={styles.section}>
          <div style={styles.toolbar}>
            <div>
              <h2 style={styles.sectionTitle}>Дата отчёта</h2>
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
        </div>

        {isLoading ? (
          <div style={styles.section}>
            <p style={styles.sectionText}>Загружаем отчёт...</p>
          </div>
        ) : error ? (
          <div style={styles.section}>
            <p style={{ ...styles.sectionText, color: tokens.textMuted }}>
              {['Not Found', 'No scored calls found for this date.'].includes(getErrorMessage(error))
                ? 'За этот день нет оценённых звонков. Возможно, звонки ещё не были оценены.'
                : getErrorMessage(error)}
            </p>
          </div>
        ) : report ? (
          <>
            <CallsTable calls={report.best_calls} label="Лучшие звонки (выше среднего)" good styles={styles} />
            <CallsTable calls={report.worst_calls} label="Худшие звонки (ниже среднего)" good={false} styles={styles} />
          </>
        ) : null}
      </div>
    </WorkspaceShell>
  );
}
