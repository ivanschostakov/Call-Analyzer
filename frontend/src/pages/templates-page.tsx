import { useEffect, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Plus, Trash2 } from 'lucide-react';

import {
  useCreateTemplateRouteTemplatesPost,
  useDeleteTemplateRouteTemplatesTemplateIdDelete,
  useListTemplatesRouteTemplatesGet,
} from '../api/generated/client';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { useViewport } from '../hooks/use-viewport';
import { formatDateTime, getErrorMessage, truncateText } from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

export function TemplatesPage({ companyId }: { companyId: number }) {
  const navigate = useNavigate();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const [activePanel, setActivePanel] = useState<'list' | 'new'>('list');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');

  const templatesQuery = useListTemplatesRouteTemplatesGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId),
      },
    },
  );
  const createMutation = useCreateTemplateRouteTemplatesPost({
    mutation: {
      onSuccess() {
        setName('');
        setDescription('');
        setInstructions('');
        setActivePanel('list');
        void invalidateWorkspaceQueries();
      },
    },
  });
  const deleteMutation = useDeleteTemplateRouteTemplatesTemplateIdDelete({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createMutation.mutateAsync({
      data: {
        company_id: companyId,
        name,
        description: description || undefined,
        instructions: instructions || undefined,
      },
    });
  }

  async function handleDelete(templateId: number) {
    if (!window.confirm('Удалить шаблон?')) {
      return;
    }
    await deleteMutation.mutateAsync({ templateId });
  }

  const templates = templatesQuery.data ?? [];

  useEffect(() => {
    if (!templatesQuery.isPending && !templates.length) {
      setActivePanel('new');
    }
  }, [templates.length, templatesQuery.isPending]);

  return (
    <WorkspaceShell
      title="Шаблоны"
      section="templates"
      companyId={companyId}
      compactTopbar
      ownerOnly
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.templates(nextCompanyId) })}
    >
      <div style={styles.toolbarGroup}>
        <Button variant={activePanel === 'list' ? 'secondary' : 'ghost'} size="sm" onClick={() => setActivePanel('list')}>
          Список
        </Button>
        <Button variant={activePanel === 'new' ? 'secondary' : 'ghost'} size="sm" onClick={() => setActivePanel('new')}>
          Новый
        </Button>
      </div>

      {activePanel === 'new' ? (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <div>
              <h2 style={styles.sectionTitle}>Новый шаблон</h2>
            </div>
          </div>

          <form onSubmit={handleCreate} style={styles.stack}>
            <div style={styles.formGrid}>
              <div style={styles.fieldStack}>
                <Label htmlFor="template-name">Название</Label>
                <Input id="template-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Например, Продажи B2B" />
              </div>
              <div style={styles.fieldStack}>
                <Label htmlFor="template-description">Описание</Label>
                <Input
                  id="template-description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Для кого и когда используется"
                />
              </div>
            </div>
            <div style={styles.fieldStack}>
              <Label htmlFor="template-instructions">Инструкция для анализа</Label>
              <Textarea
                id="template-instructions"
                value={instructions}
                onChange={(event) => setInstructions(event.target.value)}
                placeholder="Общие указания для анализатора"
              />
            </div>
            {createMutation.isError ? <p style={styles.errorText}>{getErrorMessage(createMutation.error)}</p> : null}
            <div style={styles.rowActions}>
              <Button type="submit" disabled={createMutation.isPending || !name.trim()}>
                <Plus size={15} />
                {createMutation.isPending ? 'Создаем...' : 'Создать шаблон'}
              </Button>
            </div>
          </form>
        </section>
      ) : null}

      {activePanel === 'list' ? (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <div>
              <h2 style={styles.sectionTitle}>Список шаблонов</h2>
            </div>
          </div>

          {templatesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(templatesQuery.error)}</p> : null}
          {!templatesQuery.isError && !templates.length ? <p style={styles.mutedText}>Шаблонов пока нет.</p> : null}

          <div style={styles.list}>
            {templates.map((template) => (
              <div key={template.id} style={styles.listItem}>
                <div style={styles.listItemBody}>
                  <p style={styles.listItemTitle}>{template.name}</p>
                  {template.description ? <p style={styles.sectionText}>{truncateText(template.description, 180)}</p> : null}
                  <p style={styles.listItemMeta}>Обновлен {formatDateTime(template.updated_at)}</p>
                </div>
                <div style={styles.rowActions}>
                  <Button variant="primary" size="sm" onClick={() => navigate({ to: workspacePaths.templateReports(companyId, template.id) })}>
                    Открыть отчет
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => navigate({ to: workspacePaths.template(companyId, template.id) })}>
                    Редактировать
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => handleDelete(template.id)} disabled={deleteMutation.isPending}>
                    <Trash2 size={14} />
                    Удалить
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </WorkspaceShell>
  );
}
