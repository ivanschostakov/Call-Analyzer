import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { useListTemplatesRouteTemplatesGet } from '../api/generated/client';
import { clearCompanyBeelineIntegration, getCompanyBeelineIntegration, syncCompanyBeelineDateRange, updateCompanyBeelineIntegration } from '../api/integrations';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { useViewport } from '../hooks/use-viewport';
import { formatDateTime, getErrorMessage } from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

function getTodayDateInputValue() {
  const now = new Date();
  const localDate = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 10);
}

function integrationStatusTone(status: string | null): 'default' | 'success' | 'warning' | 'danger' {
  if (status === 'success') {
    return 'success';
  }
  if (status === 'failed') {
    return 'danger';
  }
  if (status === 'running') {
    return 'warning';
  }
  return 'default';
}

function integrationStatusLabel(status: string | null) {
  if (status === 'success') {
    return 'Успешно';
  }
  if (status === 'failed') {
    return 'Ошибка';
  }
  if (status === 'running') {
    return 'Идет синк';
  }
  return 'Не запускалась';
}

export function IntegrationsPage({ companyId }: { companyId: number }) {
  const navigate = useNavigate();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const [token, setToken] = useState('');
  const [analysisTemplateId, setAnalysisTemplateId] = useState('');
  const [syncDateFrom, setSyncDateFrom] = useState(() => getTodayDateInputValue());
  const [syncDateTo, setSyncDateTo] = useState(() => getTodayDateInputValue());

  const integrationQuery = useQuery({
    queryKey: [`/companies/${companyId}/integrations/beeline`, { companyId }],
    queryFn: () => getCompanyBeelineIntegration(companyId),
    enabled: Boolean(companyId),
  });
  const templatesQuery = useListTemplatesRouteTemplatesGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId),
      },
    },
  );

  const defaultTemplate = useMemo(
    () => (templatesQuery.data ?? []).find((template) => template.name === 'Базовый шаблон') ?? templatesQuery.data?.[0] ?? null,
    [templatesQuery.data],
  );

  useEffect(() => {
    if (!integrationQuery.data) {
      return;
    }
    if (integrationQuery.data.analysis_template_id) {
      setAnalysisTemplateId(String(integrationQuery.data.analysis_template_id));
      return;
    }
    if (defaultTemplate) {
      setAnalysisTemplateId(String(defaultTemplate.id));
    }
  }, [defaultTemplate, integrationQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateCompanyBeelineIntegration(companyId, {
        api_token: token.trim() || undefined,
        analysis_template_id: analysisTemplateId ? Number(analysisTemplateId) : undefined,
      }),
    onSuccess() {
      setToken('');
      void invalidateWorkspaceQueries();
      void integrationQuery.refetch();
    },
  });
  const clearMutation = useMutation({
    mutationFn: () => clearCompanyBeelineIntegration(companyId),
    onSuccess() {
      setToken('');
      if (defaultTemplate) {
        setAnalysisTemplateId(String(defaultTemplate.id));
      }
      void invalidateWorkspaceQueries();
      void integrationQuery.refetch();
    },
  });
  const syncRangeMutation = useMutation({
    mutationFn: () =>
      syncCompanyBeelineDateRange(companyId, {
        date_from: syncDateFrom,
        date_to: syncDateTo,
      }),
    onSuccess() {
      void invalidateWorkspaceQueries();
      void integrationQuery.refetch();
    },
  });

  const canSave = Boolean(
    companyId &&
      (token.trim() || integrationQuery.data?.has_token),
  );
  const canSyncRange = Boolean(syncDateFrom && syncDateTo && syncDateFrom <= syncDateTo);

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await saveMutation.mutateAsync();
  }

  async function handleClear() {
    if (!window.confirm('Отключить автовыгрузку записей из Beeline для этой компании?')) {
      return;
    }
    await clearMutation.mutateAsync();
  }

  return (
    <WorkspaceShell
      title="Интеграции"
      description="Владелец компании или администратор настраивает внешние интеграции. Сейчас доступна автоматическая выгрузка звонков из Beeline с ночной расшифровкой и автоанализом."
      section="integrations"
      companyId={companyId}
      ownerOnly
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.integrations(nextCompanyId) })}
    >
      <section style={styles.section}>
        <div style={styles.sectionHeader}>
          <div>
            <h2 style={styles.sectionTitle}>Автовыгрузка записей с АТС Beeline</h2>
            <p style={styles.sectionText}>
              При первом подключении система сразу подтягивает записи за текущий день, а затем каждые 2 часа проверяет текущий день на новые записи, автоматически расшифровывает их и создает анализ по выбранному шаблону.
            </p>
          </div>
          <Badge tone={integrationQuery.data?.enabled ? 'success' : 'default'}>
            {integrationQuery.data?.enabled ? 'Активна' : 'Не подключена'}
          </Badge>
        </div>

        {integrationQuery.isError ? <p style={styles.errorText}>{getErrorMessage(integrationQuery.error)}</p> : null}
        {templatesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(templatesQuery.error)}</p> : null}
        {saveMutation.isError ? <p style={styles.errorText}>{getErrorMessage(saveMutation.error)}</p> : null}
        {clearMutation.isError ? <p style={styles.errorText}>{getErrorMessage(clearMutation.error)}</p> : null}
        {syncRangeMutation.isError ? <p style={styles.errorText}>{getErrorMessage(syncRangeMutation.error)}</p> : null}

        <div style={styles.triple}>
          <div style={styles.infoCard}>
            <p style={styles.infoTitle}>Токен</p>
            <p style={styles.sectionText}>{integrationQuery.data?.has_token ? 'Сохранен' : 'Не задан'}</p>
            <p style={styles.subtleText}>{integrationQuery.data?.token_hint ?? 'После сохранения токен скрывается из интерфейса.'}</p>
          </div>
          <div style={styles.infoCard}>
            <p style={styles.infoTitle}>Последний синк</p>
            <p style={styles.sectionText}>
              {integrationQuery.data?.last_sync_finished_at ? formatDateTime(integrationQuery.data.last_sync_finished_at) : 'Пока не было'}
            </p>
            <p style={styles.subtleText}>
              {integrationQuery.data?.last_sync_target_date ? `За дату: ${integrationQuery.data.last_sync_target_date}` : 'Будет работать по текущему дню с шагом 2 часа.'}
            </p>
          </div>
          <div style={styles.infoCard}>
            <p style={styles.infoTitle}>Статус</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Badge tone={integrationStatusTone(integrationQuery.data?.last_sync_status ?? null)}>
                {integrationStatusLabel(integrationQuery.data?.last_sync_status ?? null)}
              </Badge>
            </div>
            <p style={styles.subtleText}>После импорта каждая запись уходит в расшифровку и анализ автоматически.</p>
          </div>
        </div>

        <form onSubmit={handleSave} style={styles.stack}>
          <div style={styles.formGrid}>
            <div style={styles.fieldStack}>
              <Label htmlFor="beeline-token">Токен Beeline</Label>
              <Input
                id="beeline-token"
                type="password"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                placeholder={integrationQuery.data?.has_token ? 'Введите новый токен, чтобы заменить текущий' : 'Вставьте X-MPBX-API-AUTH-TOKEN'}
              />
            </div>

            <div style={styles.fieldStack}>
              <Label htmlFor="beeline-analysis-template">Шаблон автоанализа</Label>
              <Select
                id="beeline-analysis-template"
                value={analysisTemplateId}
                onChange={(event) => setAnalysisTemplateId(event.target.value)}
                disabled={templatesQuery.isPending || !(templatesQuery.data?.length)}
              >
                {(templatesQuery.data ?? []).map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div style={styles.formGrid}>
            <div style={styles.fieldStack}>
              <Label htmlFor="beeline-sync-date-from">Дата с</Label>
              <Input
                id="beeline-sync-date-from"
                type="date"
                value={syncDateFrom}
                onChange={(event) => setSyncDateFrom(event.target.value)}
              />
            </div>
            <div style={styles.fieldStack}>
              <Label htmlFor="beeline-sync-date-to">Дата по</Label>
              <Input
                id="beeline-sync-date-to"
                type="date"
                value={syncDateTo}
                onChange={(event) => setSyncDateTo(event.target.value)}
              />
            </div>
          </div>

          {integrationQuery.data?.last_sync_error ? (
            <div style={styles.infoCard}>
              <p style={styles.infoTitle}>Последняя ошибка синка</p>
              <p style={styles.errorText}>{integrationQuery.data.last_sync_error}</p>
            </div>
          ) : null}

          <div style={styles.rowActions}>
            <Button type="submit" disabled={saveMutation.isPending || !canSave}>
              {saveMutation.isPending ? 'Сохраняем...' : integrationQuery.data?.enabled ? 'Обновить интеграцию' : 'Включить интеграцию'}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => syncRangeMutation.mutate()}
              disabled={syncRangeMutation.isPending || !integrationQuery.data?.enabled || !canSyncRange}
            >
              {syncRangeMutation.isPending ? 'Загружаем...' : 'Загрузить записи за период'}
            </Button>
            <Button type="button" variant="ghost" onClick={handleClear} disabled={clearMutation.isPending || !integrationQuery.data?.enabled}>
              {clearMutation.isPending ? 'Отключаем...' : 'Отключить'}
            </Button>
          </div>
        </form>
      </section>
    </WorkspaceShell>
  );
}
