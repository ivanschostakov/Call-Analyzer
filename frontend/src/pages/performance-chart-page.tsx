import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import {
  useListEmployeesRouteEmployeesGet,
  useListTemplatesRouteTemplatesGet,
} from '../api/generated/client';
import { generatePerformanceChart, type PerformanceCallData } from '../api/performance-chart';
import { useAuth } from '../auth/context';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { useViewport } from '../hooks/use-viewport';
import {
  canManageTeam,
  formatUserLabel,
  getErrorMessage,
} from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

const OVERALL_COLOR = '#69a4ff';

type ChartPoint = {
  label: string;
  call_date: string;
  call_count: number;
  overall_score: number;
  [key: string]: string | number;
};

function buildChartData(calls: PerformanceCallData[]): ChartPoint[] {
  return calls.map((call) => ({
    label: call.label,
    call_date: call.call_date,
    call_count: call.call_count,
    overall_score: call.overall_score,
  }));
}

function scoreColor(score: number, tokens: { success: string; warning: string; danger: string }) {
  if (score >= 70) return tokens.success;
  if (score >= 45) return tokens.warning;
  return tokens.danger;
}

function callWord(n: number): string {
  if (n === 1) return 'звонок';
  if (n >= 2 && n <= 4) return 'звонка';
  return 'звонков';
}

type TooltipEntry = { dataKey?: string | number | ((obj: unknown) => unknown); value?: number | string | Array<number | string>; color?: string };

type CustomTooltipProps = {
  active?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload?: ReadonlyArray<any>;
  label?: string | number;
  hiddenCriteria: Set<string>;
  tokens: { surface: string; surfaceStrong: string; text: string; textMuted: string; textSubtle: string };
};

function ChartTooltip({ active, payload, label, hiddenCriteria, tokens }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;

  const key = (p: TooltipEntry) => (typeof p.dataKey === 'string' ? p.dataKey : '');
  const overall = payload.find((p) => key(p) === 'overall_score');
  const callCountEntry = payload.find((p) => key(p) === 'call_count');
  const callCount = callCountEntry ? Number(callCountEntry.value) : undefined;
  const criteria = payload
    .filter((p) => !['overall_score', 'call_count', 'call_date', 'label'].includes(key(p)) && !hiddenCriteria.has(key(p)))
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

  return (
    <div style={{
      background: tokens.surface,
      border: `1px solid ${tokens.surfaceStrong}`,
      borderRadius: 12,
      padding: '12px 14px',
      fontSize: 13,
      color: tokens.text,
      minWidth: 200,
      maxWidth: 260,
      boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
    }}>
      <p style={{ margin: '0 0 4px', fontWeight: 700, color: tokens.textMuted, fontSize: 12 }}>{label}</p>
      {callCount !== undefined && (
        <p style={{ margin: '0 0 8px', fontSize: 11, color: tokens.textSubtle }}>{callCount} {callWord(callCount)}</p>
      )}
      {overall && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontWeight: 700 }}>Общий балл</span>
          <span style={{ fontWeight: 700, color: overall.color }}>{Number(overall.value).toFixed(1)}%</span>
        </div>
      )}
      {criteria.length > 0 && (
        <div style={{ borderTop: `1px solid ${tokens.surfaceStrong}`, marginTop: 6, paddingTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {criteria.slice(0, 8).map((c) => (
            <div key={key(c)} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <span style={{ color: tokens.textMuted, fontSize: 12, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {key(c)}
              </span>
              <span style={{ fontWeight: 600, color: c.color, flexShrink: 0 }}>
                {Number(c.value).toFixed(0)}%
              </span>
            </div>
          ))}
          {criteria.length > 8 && (
            <p style={{ margin: 0, fontSize: 11, color: tokens.textSubtle }}>+ ещё {criteria.length - 8}</p>
          )}
        </div>
      )}
    </div>
  );
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function monthAgoISO(): string {
  const d = new Date();
  d.setMonth(d.getMonth() - 1);
  return d.toISOString().slice(0, 10);
}

type Props = { companyId: number };

export function PerformanceChartPage({ companyId }: Props) {
  const auth = useAuth();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const canManageCurrentTeam = canManageTeam(auth.user?.role);

  const [templateId, setTemplateId] = useState<string>('');
  const [employeeFilter, setEmployeeFilter] = useState<string>('all');
  const [dateFrom, setDateFrom] = useState<string>(monthAgoISO());
  const [dateTo, setDateTo] = useState<string>(todayISO());

  const templatesQuery = useListTemplatesRouteTemplatesGet(
    { company_id: companyId },
    { query: { enabled: Boolean(companyId) } },
  );
  const employeesQuery = useListEmployeesRouteEmployeesGet(
    { company_id: companyId },
    { query: { enabled: Boolean(companyId && canManageCurrentTeam) } },
  );

  const employeeOptions = useMemo(() => {
    const result = new Map<number, string>();
    if (auth.user?.id) {
      result.set(auth.user.id, formatUserLabel(`${auth.user.name} ${auth.user.surname}`.trim(), auth.user.email));
    }
    for (const emp of employeesQuery.data ?? []) {
      result.set(emp.user_id, formatUserLabel(emp.user_display_name, emp.user_email));
    }
    return Array.from(result.entries()).map(([id, label]) => ({ id, label })).sort((a, b) => a.label.localeCompare(b.label, 'ru'));
  }, [auth.user, employeesQuery.data]);

  const canBuild = Boolean(templateId) && Boolean(dateFrom) && Boolean(dateTo) && dateFrom <= dateTo;

  const chartMutation = useMutation({
    mutationFn: () =>
      generatePerformanceChart({
        company_id: companyId,
        template_id: Number(templateId),
        employee_user_id: employeeFilter !== 'all' ? Number(employeeFilter) : undefined,
        date_from: dateFrom,
        date_to: dateTo,
      }),
  });

  const resetChart = () => chartMutation.reset();

  const chartCalls = chartMutation.data?.calls ?? [];
  const chartData = useMemo(() => buildChartData(chartCalls), [chartCalls]);

  const avgScore = chartData.length > 0
    ? chartData.reduce((s, d) => s + d.overall_score, 0) / chartData.length
    : null;

  return (
    <WorkspaceShell
      title="График роста"
      description="Динамика производительности сотрудника по дням на основе анализов звонков."
      section="performance-chart"
      companyId={companyId}
      wideContent
      managerOnly
    >
      <div style={styles.stack}>

        {/* Filters */}
        <section style={styles.section}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end' }}>
            <div style={{ ...styles.fieldStack, width: viewport.isMobile ? '100%' : 'min(220px, 100%)' }}>
              <Label htmlFor="pc-template">Шаблон оценки</Label>
              <Select
                id="pc-template"
                value={templateId}
                onChange={(e) => { setTemplateId(e.target.value); resetChart(); }}
              >
                <option value="">— выберите шаблон —</option>
                {(templatesQuery.data ?? []).map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </Select>
            </div>

            {canManageCurrentTeam && (
              <div style={{ ...styles.fieldStack, width: viewport.isMobile ? '100%' : 'min(220px, 100%)' }}>
                <Label htmlFor="pc-employee">Сотрудник</Label>
                <Select id="pc-employee" value={employeeFilter} onChange={(e) => { setEmployeeFilter(e.target.value); resetChart(); }}>
                  <option value="all">Все сотрудники</option>
                  {employeeOptions.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                </Select>
              </div>
            )}

            <div style={{ ...styles.fieldStack, width: viewport.isMobile ? 'calc(50% - 6px)' : 'min(160px, 100%)' }}>
              <Label htmlFor="pc-date-from">С даты</Label>
              <Input
                id="pc-date-from"
                type="date"
                value={dateFrom}
                max={dateTo || todayISO()}
                onChange={(e) => { setDateFrom(e.target.value); resetChart(); }}
              />
            </div>

            <div style={{ ...styles.fieldStack, width: viewport.isMobile ? 'calc(50% - 6px)' : 'min(160px, 100%)' }}>
              <Label htmlFor="pc-date-to">По дату</Label>
              <Input
                id="pc-date-to"
                type="date"
                value={dateTo}
                min={dateFrom}
                max={todayISO()}
                onChange={(e) => { setDateTo(e.target.value); resetChart(); }}
              />
            </div>

            <Button
              onClick={() => chartMutation.mutate()}
              disabled={!canBuild || chartMutation.isPending}
              style={{ alignSelf: 'flex-end' }}
            >
              {chartMutation.isPending ? 'Строим…' : 'Построить →'}
            </Button>
          </div>
          {dateFrom > dateTo && (
            <p style={{ margin: '4px 0 0', fontSize: 12, color: tokens.danger ?? '#ef4444' }}>
              Начальная дата не может быть позже конечной
            </p>
          )}
        </section>

        {/* Chart area */}
        {chartMutation.isError && (
          <section style={{ ...styles.section, alignItems: 'center', padding: '48px 24px', textAlign: 'center' }}>
            <p style={{ margin: 0, fontSize: 15, color: tokens.danger ?? '#ef4444' }}>
              Ошибка: {getErrorMessage(chartMutation.error)}
            </p>
          </section>
        )}

        {chartMutation.isPending && (
          <section style={{ ...styles.section, alignItems: 'center', padding: '48px 24px', textAlign: 'center' }}>
            <p style={{ margin: 0, fontSize: 15, color: tokens.textMuted }}>Генерируем график…</p>
          </section>
        )}

        {!chartMutation.isPending && !chartMutation.isError && chartMutation.isSuccess && chartData.length === 0 && (
          <section style={{ ...styles.section, alignItems: 'center', padding: '48px 24px', textAlign: 'center' }}>
            <p style={{ margin: 0, fontSize: 15, color: tokens.textMuted }}>
              За выбранный период нет анализов звонков
            </p>
          </section>
        )}

        {!chartMutation.isIdle && !chartMutation.isPending && !chartMutation.isError && chartData.length > 0 && (
          <section style={styles.section}>
            {/* Summary stats */}
            <div style={{ display: 'flex', gap: viewport.isMobile ? 12 : 20, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <h2 style={styles.sectionTitle}>Динамика по дням</h2>
                <p style={{ ...styles.sectionText, marginTop: 4 }}>
                  {chartData.length} {chartData.length === 1 ? 'день' : chartData.length < 5 ? 'дня' : 'дней'} · {chartData.reduce((s, d) => s + d.call_count, 0)} звонков
                </p>
              </div>
              {avgScore !== null && (
                <div style={{ textAlign: 'right' }}>
                  <p style={{ margin: 0, fontSize: 12, color: tokens.textSubtle }}>Средний балл</p>
                  <p style={{ margin: 0, fontSize: 26, fontWeight: 800, color: scoreColor(avgScore, tokens), fontVariantNumeric: 'tabular-nums' }}>
                    {avgScore.toFixed(1)}%
                  </p>
                </div>
              )}
            </div>

            {/* Overall score dot chart */}
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={tokens.surfaceStrong} vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: tokens.textSubtle }} tickLine={false} axisLine={false} padding={{ left: 40, right: 40 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: tokens.textSubtle }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} width={38} />
                  {avgScore !== null && (
                    <ReferenceLine y={avgScore} stroke={OVERALL_COLOR} strokeDasharray="4 3" strokeOpacity={0.5} />
                  )}
                  <Tooltip content={(props) => (
                    <ChartTooltip {...props} hiddenCriteria={new Set()} tokens={tokens} />
                  )} />
                  <Line
                    type="monotone"
                    dataKey="overall_score"
                    stroke={OVERALL_COLOR}
                    strokeWidth={2}
                    dot={{ r: 5, fill: OVERALL_COLOR, strokeWidth: 0 }}
                    activeDot={{ r: 7, strokeWidth: 0 }}
                    isAnimationActive={false}
                  />
                  <Line dataKey="call_count" hide />
                </LineChart>
              </ResponsiveContainer>
            </div>


            {/* Daily summary table */}
            <div style={{ borderTop: `1px solid ${tokens.surfaceStrong}`, paddingTop: 14 }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '6px 10px', color: tokens.textSubtle, fontWeight: 600, whiteSpace: 'nowrap' }}>Дата</th>
                      <th style={{ textAlign: 'center', padding: '6px 10px', color: tokens.textSubtle, fontWeight: 600, whiteSpace: 'nowrap' }}>Звонков</th>
                      <th style={{ textAlign: 'right', padding: '6px 10px', color: tokens.textSubtle, fontWeight: 600, whiteSpace: 'nowrap' }}>Средний балл</th>
                    </tr>
                  </thead>
                  <tbody>
                    {chartData.map((day) => (
                      <tr key={day.call_date} style={{ borderTop: `1px solid ${tokens.surfaceStrong}` }}>
                        <td style={{ padding: '8px 10px', color: tokens.textMuted, fontVariantNumeric: 'tabular-nums' }}>{day.label}</td>
                        <td style={{ padding: '8px 10px', textAlign: 'center', color: tokens.textSubtle, fontVariantNumeric: 'tabular-nums' }}>{day.call_count}</td>
                        <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: scoreColor(day.overall_score, tokens), fontVariantNumeric: 'tabular-nums' }}>
                          {day.overall_score.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}
      </div>
    </WorkspaceShell>
  );
}
