import { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  CartesianGrid,
  Legend,
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
import { SectionCard } from '../components/ui/section-card';
import { Select } from '../components/ui/select';
import { useViewport } from '../hooks/use-viewport';
import { useWorkspace } from '../workspace/workspace-context';
import {
  canManageTeam,
  formatUserLabel,
  getErrorMessage,
} from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

const SERIES_COLORS = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2', '#be123c', '#4d7c0f', '#c2410c', '#475569'];

type EmployeeOption = {
  id: number;
  label: string;
};

type EmployeeChartSeries = EmployeeOption & {
  color: string;
  scoreKey: string;
  callCountKey: string;
  calls: PerformanceCallData[];
};

type PerformanceChartResult = {
  series: EmployeeChartSeries[];
};

type ChartPoint = {
  label: string;
  call_date: string;
  total_call_count: number;
  [key: string]: string | number;
};

function buildChartData(series: EmployeeChartSeries[]): ChartPoint[] {
  const points = new Map<string, ChartPoint>();

  for (const item of series) {
    for (const call of item.calls) {
      const point = points.get(call.call_date) ?? {
        label: call.label,
        call_date: call.call_date,
        total_call_count: 0,
      };
      point[item.scoreKey] = call.overall_score;
      point[item.callCountKey] = call.call_count;
      point.total_call_count += call.call_count;
      points.set(call.call_date, point);
    }
  }

  return Array.from(points.values()).sort((left, right) => left.call_date.localeCompare(right.call_date));
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

type CustomTooltipProps = {
  active?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  payload?: ReadonlyArray<any>;
  label?: string | number;
  series: EmployeeChartSeries[];
  tokens: { surface: string; surfaceStrong: string; text: string; textMuted: string; textSubtle: string };
};

function ChartTooltip({ active, payload, label, series, tokens }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;

  const point = payload[0]?.payload as ChartPoint | undefined;
  if (!point) return null;

  const visibleSeries = series.filter((item) => typeof point[item.scoreKey] === 'number');

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
      {visibleSeries.map((item) => {
        const score = Number(point[item.scoreKey]);
        const callCount = Number(point[item.callCountKey] ?? 0);
        return (
          <div key={item.id} style={{ display: 'grid', gridTemplateColumns: '10px minmax(0, 1fr) auto', gap: 8, alignItems: 'center', marginTop: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: item.color }} />
            <span style={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.label}</span>
            <span style={{ fontWeight: 700, color: item.color, whiteSpace: 'nowrap' }}>
              {score.toFixed(1)}% · {callCount} {callWord(callCount)}
            </span>
          </div>
        );
      })}
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
  const workspace = useWorkspace();
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
  const currentCompany = workspace.getCompanyById(companyId);

  useEffect(() => {
    if (templateId || !templatesQuery.data?.length) return;
    const configuredTemplateId = currentCompany?.beeline_auto_analysis_template_id;
    const configuredTemplate = templatesQuery.data.find((template) => template.id === configuredTemplateId);
    setTemplateId(String(configuredTemplate?.id ?? templatesQuery.data[0].id));
  }, [currentCompany?.beeline_auto_analysis_template_id, templateId, templatesQuery.data]);
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

  const canBuild = Boolean(templateId)
    && Boolean(dateFrom)
    && Boolean(dateTo)
    && dateFrom <= dateTo
    && (!canManageCurrentTeam || !employeesQuery.isPending);

  const chartMutation = useMutation<PerformanceChartResult>({
    mutationFn: async () => {
      const selectedEmployees = canManageCurrentTeam && employeeFilter === 'all'
        ? employeeOptions
        : employeeOptions.filter((employee) => employee.id === Number(canManageCurrentTeam ? employeeFilter : auth.user?.id));

      const responses = await Promise.all(selectedEmployees.map((employee) =>
        generatePerformanceChart({
          company_id: companyId,
          template_id: Number(templateId),
          employee_user_id: employee.id,
          date_from: dateFrom,
          date_to: dateTo,
        }),
      ));

      return {
        series: selectedEmployees.map((employee, index) => ({
          ...employee,
          color: SERIES_COLORS[index % SERIES_COLORS.length],
          scoreKey: `score_${employee.id}`,
          callCountKey: `calls_${employee.id}`,
          calls: responses[index].calls,
        })).filter((item) => item.calls.length > 0),
      };
    },
  });

  const resetChart = () => chartMutation.reset();

  const chartSeries = chartMutation.data?.series ?? [];
  const chartData = useMemo(() => buildChartData(chartSeries), [chartSeries]);
  const totalCalls = chartData.reduce((sum, day) => sum + day.total_call_count, 0);
  const weightedScoreTotal = chartSeries.reduce(
    (sum, item) => sum + item.calls.reduce((seriesSum, call) => seriesSum + call.overall_score * call.call_count, 0),
    0,
  );
  const avgScore = totalCalls > 0 ? weightedScoreTotal / totalCalls : null;

  return (
    <WorkspaceShell
      title="График роста"
      description="Динамика производительности сотрудников по дням на основе анализов звонков."
      section="performance-chart"
      companyId={companyId}
      wideContent
    >
      <div style={styles.stack}>
        <SectionCard
          title="Параметры графика"
          description={canManageCurrentTeam
            ? 'Сравните всю доступную команду на одном графике или выберите одного сотрудника.'
            : 'График строится только по вашим звонкам и по шаблону, выбранному руководителем.'}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end' }}>
            <div style={{ ...styles.fieldStack, width: viewport.isMobile ? '100%' : 'min(220px, 100%)' }}>
              <Label htmlFor="pc-template">Шаблон оценки</Label>
              <Select
                id="pc-template"
                value={templateId}
                disabled={Boolean(currentCompany?.beeline_auto_analysis_template_id)}
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
                <Label htmlFor="pc-employee">Сотрудники</Label>
                <Select id="pc-employee" value={employeeFilter} onChange={(e) => { setEmployeeFilter(e.target.value); resetChart(); }}>
                  <option value="all">Вся команда · отдельные линии</option>
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
              {chartMutation.isPending ? 'Строим…' : 'Построить'}
            </Button>
          </div>
          {dateFrom > dateTo && (
            <p style={{ margin: '4px 0 0', fontSize: 12, color: tokens.danger ?? '#ef4444' }}>
              Начальная дата не может быть позже конечной
            </p>
          )}
        </SectionCard>

        {chartMutation.isError && (
          <SectionCard title="График роста" style={{ alignItems: 'center', textAlign: 'center' }}>
            <p style={{ margin: 0, fontSize: 15, color: tokens.danger ?? '#ef4444' }}>
              Ошибка: {getErrorMessage(chartMutation.error)}
            </p>
          </SectionCard>
        )}

        {chartMutation.isPending && (
          <SectionCard title="График роста" style={{ alignItems: 'center', textAlign: 'center' }}>
            <p style={{ margin: 0, fontSize: 15, color: tokens.textMuted }}>Генерируем график…</p>
          </SectionCard>
        )}

        {!chartMutation.isPending && !chartMutation.isError && chartMutation.isSuccess && chartData.length === 0 && (
          <SectionCard title="График роста" style={{ alignItems: 'center', textAlign: 'center' }}>
            <p style={{ margin: 0, fontSize: 15, color: tokens.textMuted }}>
              За выбранный период нет анализов звонков
            </p>
          </SectionCard>
        )}

        {!chartMutation.isIdle && !chartMutation.isPending && !chartMutation.isError && chartData.length > 0 && (
          <SectionCard title={chartSeries.length > 1 ? 'Динамика команды по дням' : 'Динамика по дням'}>
            <div style={{ display: 'flex', gap: viewport.isMobile ? 12 : 20, flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <p style={{ ...styles.sectionText, marginTop: 4 }}>
                  {chartData.length} {chartData.length === 1 ? 'день' : chartData.length < 5 ? 'дня' : 'дней'} · {totalCalls} звонков · {chartSeries.length} {chartSeries.length === 1 ? 'сотрудник' : 'сотрудников'}
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

            <div style={{ width: '100%', height: chartSeries.length > 4 ? 300 : 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: chartSeries.length > 1 ? 12 : 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={tokens.surfaceStrong} vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: tokens.textSubtle }} tickLine={false} axisLine={false} padding={{ left: 40, right: 40 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: tokens.textSubtle }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} width={38} />
                  {avgScore !== null && (
                    <ReferenceLine y={avgScore} stroke={tokens.textSubtle} strokeDasharray="4 3" strokeOpacity={0.5} />
                  )}
                  <Tooltip content={(props) => (
                    <ChartTooltip {...props} series={chartSeries} tokens={tokens} />
                  )} />
                  {chartSeries.length > 1 ? <Legend verticalAlign="bottom" wrapperStyle={{ fontSize: 12, paddingTop: 12 }} /> : null}
                  {chartSeries.map((item) => (
                    <Line
                      key={item.id}
                      type="monotone"
                      dataKey={item.scoreKey}
                      name={item.label}
                      stroke={item.color}
                      strokeWidth={2}
                      connectNulls
                      dot={{ r: 4, fill: item.color, strokeWidth: 0 }}
                      activeDot={{ r: 6, strokeWidth: 0 }}
                      isAnimationActive={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>


            <div style={{ borderTop: `1px solid ${tokens.surfaceStrong}`, paddingTop: 14 }}>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left', padding: '6px 10px', color: tokens.textSubtle, fontWeight: 600, whiteSpace: 'nowrap' }}>Дата</th>
                      {chartSeries.map((item) => (
                        <th key={item.id} style={{ textAlign: 'right', padding: '6px 10px', color: item.color, fontWeight: 700, whiteSpace: 'nowrap' }}>
                          {item.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {chartData.map((day) => (
                      <tr key={day.call_date} style={{ borderTop: `1px solid ${tokens.surfaceStrong}` }}>
                        <td style={{ padding: '8px 10px', color: tokens.textMuted, fontVariantNumeric: 'tabular-nums' }}>{day.label}</td>
                        {chartSeries.map((item) => {
                          const score = day[item.scoreKey];
                          const calls = day[item.callCountKey];
                          return (
                            <td key={item.id} style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: typeof score === 'number' ? scoreColor(score, tokens) : tokens.textSubtle, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                              {typeof score === 'number' ? `${score.toFixed(1)}% · ${Number(calls ?? 0)}` : '—'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </SectionCard>
        )}
      </div>
    </WorkspaceShell>
  );
}
