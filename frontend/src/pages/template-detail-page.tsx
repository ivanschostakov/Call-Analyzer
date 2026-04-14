import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { ArrowDown, ArrowUp, Plus, Save, Trash2 } from 'lucide-react';

import {
  useCreateCriterionRouteCriteriaPost,
  useDeleteCriterionRouteCriteriaCriterionIdDelete,
  useGetTemplateRouteTemplatesTemplateIdGet,
  useListCriteriaRouteCriteriaGet,
  useUpdateCriterionRouteCriteriaCriterionIdPatch,
  useUpdateTemplateRouteTemplatesTemplateIdPatch,
} from '../api/generated/client';
import { CriterionAnswerType } from '../api/generated/model/criterionAnswerType';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { useViewport } from '../hooks/use-viewport';
import { getErrorMessage } from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

type CriterionDraft = {
  name: string;
  description: string;
  prompt: string;
  answer_type: keyof typeof CriterionAnswerType;
  position: number;
};

export function TemplateDetailPage({ companyId, templateId }: { companyId: number; templateId: number }) {
  const navigate = useNavigate();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const templateQuery = useGetTemplateRouteTemplatesTemplateIdGet(templateId, {
    query: {
      enabled: Boolean(templateId),
    },
  });
  const criteriaQuery = useListCriteriaRouteCriteriaGet(
    { template_id: templateId },
    {
      query: {
        enabled: Boolean(templateId),
      },
    },
  );

  const updateTemplateMutation = useUpdateTemplateRouteTemplatesTemplateIdPatch({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const createCriterionMutation = useCreateCriterionRouteCriteriaPost({
    mutation: {
      onSuccess() {
        setNewCriterion({
          name: '',
          description: '',
          prompt: '',
          answer_type: 'text',
          position: sortedCriteria.length + 1,
        });
        void invalidateWorkspaceQueries();
      },
    },
  });
  const updateCriterionMutation = useUpdateCriterionRouteCriteriaCriterionIdPatch({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const deleteCriterionMutation = useDeleteCriterionRouteCriteriaCriterionIdDelete({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });

  const template = templateQuery.data;
  const sortedCriteria = useMemo(
    () => [...(criteriaQuery.data ?? [])].sort((left, right) => (left.position ?? 0) - (right.position ?? 0)),
    [criteriaQuery.data],
  );

  const [templateDraft, setTemplateDraft] = useState({
    name: '',
    description: '',
    instructions: '',
  });
  const [criteriaDrafts, setCriteriaDrafts] = useState<Record<number, CriterionDraft>>({});
  const [newCriterion, setNewCriterion] = useState<CriterionDraft>({
    name: '',
    description: '',
    prompt: '',
    answer_type: 'text',
    position: 1,
  });

  useEffect(() => {
    if (!template) {
      return;
    }
    setTemplateDraft({
      name: template.name,
      description: template.description ?? '',
      instructions: template.instructions ?? '',
    });
  }, [template]);

  useEffect(() => {
    if (!sortedCriteria.length) {
      setCriteriaDrafts({});
      setNewCriterion((current) => ({ ...current, position: 1 }));
      return;
    }

    setCriteriaDrafts(
      Object.fromEntries(
        sortedCriteria.map((criterion, index) => [
          criterion.id,
          {
            name: criterion.name,
            description: criterion.description ?? '',
            prompt: criterion.prompt ?? '',
            answer_type: (criterion.answer_type ?? 'text') as keyof typeof CriterionAnswerType,
            position: criterion.position ?? index + 1,
          },
        ]),
      ),
    );
    setNewCriterion((current) => ({ ...current, position: sortedCriteria.length + 1 }));
  }, [sortedCriteria]);

  async function handleTemplateSave() {
    await updateTemplateMutation.mutateAsync({
      templateId,
      data: {
        name: templateDraft.name,
        description: templateDraft.description || undefined,
        instructions: templateDraft.instructions || undefined,
      },
    });
  }

  async function handleCriterionCreate() {
    await createCriterionMutation.mutateAsync({
      data: {
        template_id: templateId,
        name: newCriterion.name,
        description: newCriterion.description || undefined,
        prompt: newCriterion.prompt || undefined,
        answer_type: newCriterion.answer_type,
        position: newCriterion.position,
      },
    });
  }

  async function handleCriterionSave(criterionId: number) {
    const draft = criteriaDrafts[criterionId];
    if (!draft) {
      return;
    }
    await updateCriterionMutation.mutateAsync({
      criterionId,
      data: {
        name: draft.name,
        description: draft.description || undefined,
        prompt: draft.prompt || undefined,
        answer_type: draft.answer_type,
        position: draft.position,
      },
    });
  }

  async function handleCriterionDelete(criterionId: number) {
    if (!window.confirm('Удалить критерий?')) {
      return;
    }
    await deleteCriterionMutation.mutateAsync({ criterionId });
  }

  async function moveCriterion(criterionId: number, direction: -1 | 1) {
    const index = sortedCriteria.findIndex((criterion) => criterion.id === criterionId);
    const current = sortedCriteria[index];
    const target = sortedCriteria[index + direction];

    if (!current || !target) {
      return;
    }

    await updateCriterionMutation.mutateAsync({
      criterionId: current.id,
      data: { position: target.position ?? index + direction + 1 },
    });
    await updateCriterionMutation.mutateAsync({
      criterionId: target.id,
      data: { position: current.position ?? index + 1 },
    });
  }

  return (
    <WorkspaceShell
      title={template ? template.name : 'Шаблон'}
      description="Общая инструкция редактируется здесь, а контракт ответа остается системным и управляется на бэкенде."
      section="templates"
      companyId={companyId}
      ownerOnly
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.templates(nextCompanyId) })}
    >
      {templateQuery.isError ? <p style={styles.errorText}>{getErrorMessage(templateQuery.error)}</p> : null}
      {template ? (
        <>
          <section style={styles.section}>
            <div style={styles.sectionHeader}>
              <div>
                <h2 style={styles.sectionTitle}>Основные поля</h2>
                <p style={styles.sectionText}>Инструкция редактируется в шаблоне. Формат ответа анализатора не изменяется из интерфейса.</p>
              </div>
            </div>

            <div style={styles.formGrid}>
              <div style={styles.fieldStack}>
                <Label htmlFor="template-detail-name">Название</Label>
                <Input
                  id="template-detail-name"
                  value={templateDraft.name}
                  onChange={(event) => setTemplateDraft((current) => ({ ...current, name: event.target.value }))}
                />
              </div>
              <div style={styles.fieldStack}>
                <Label htmlFor="template-detail-description">Описание</Label>
                <Input
                  id="template-detail-description"
                  value={templateDraft.description}
                  onChange={(event) => setTemplateDraft((current) => ({ ...current, description: event.target.value }))}
                />
              </div>
            </div>
            <div style={styles.fieldStack}>
              <Label htmlFor="template-detail-instructions">Инструкция</Label>
              <Textarea
                id="template-detail-instructions"
                value={templateDraft.instructions}
                onChange={(event) => setTemplateDraft((current) => ({ ...current, instructions: event.target.value }))}
              />
            </div>
            <p style={styles.note}>Контракт ответа анализатора жестко задается в Python и не редактируется из интерфейса.</p>
            {updateTemplateMutation.isError ? <p style={styles.errorText}>{getErrorMessage(updateTemplateMutation.error)}</p> : null}
            <div style={styles.rowActions}>
              <Button onClick={handleTemplateSave} disabled={updateTemplateMutation.isPending || !templateDraft.name.trim()}>
                <Save size={15} />
                Сохранить шаблон
              </Button>
            </div>
          </section>

          <section style={styles.section}>
            <div style={styles.sectionHeader}>
              <div>
                <h2 style={styles.sectionTitle}>Новый критерий</h2>
                <p style={styles.sectionText}>Критерии идут в порядке позиций и затем превращаются в колонки отчета.</p>
              </div>
            </div>

            <div style={styles.formGrid}>
              <div style={styles.fieldStack}>
                <Label htmlFor="criterion-name">Название</Label>
                <Input id="criterion-name" value={newCriterion.name} onChange={(event) => setNewCriterion((current) => ({ ...current, name: event.target.value }))} />
              </div>
              <div style={styles.fieldStack}>
                <Label htmlFor="criterion-answer-type">Тип ответа</Label>
                <Select
                  id="criterion-answer-type"
                  value={newCriterion.answer_type}
                  onChange={(event) =>
                    setNewCriterion((current) => ({
                      ...current,
                      answer_type: event.target.value as keyof typeof CriterionAnswerType,
                    }))
                  }
                >
                  {Object.values(CriterionAnswerType).map((answerType) => (
                    <option key={answerType} value={answerType}>
                      {answerType}
                    </option>
                  ))}
                </Select>
              </div>
              <div style={styles.fieldStack}>
                <Label htmlFor="criterion-position">Позиция</Label>
                <Input
                  id="criterion-position"
                  type="number"
                  min={1}
                  value={newCriterion.position}
                  onChange={(event) =>
                    setNewCriterion((current) => ({
                      ...current,
                      position: Number(event.target.value) || 1,
                    }))
                  }
                />
              </div>
            </div>
            <div style={styles.fieldStack}>
              <Label htmlFor="criterion-description">Описание</Label>
              <Textarea
                id="criterion-description"
                value={newCriterion.description}
                onChange={(event) => setNewCriterion((current) => ({ ...current, description: event.target.value }))}
              />
            </div>
            <div style={styles.fieldStack}>
              <Label htmlFor="criterion-prompt">Prompt</Label>
              <Textarea
                id="criterion-prompt"
                value={newCriterion.prompt}
                onChange={(event) => setNewCriterion((current) => ({ ...current, prompt: event.target.value }))}
              />
            </div>
            {createCriterionMutation.isError ? <p style={styles.errorText}>{getErrorMessage(createCriterionMutation.error)}</p> : null}
            <div style={styles.rowActions}>
              <Button onClick={handleCriterionCreate} disabled={createCriterionMutation.isPending || !newCriterion.name.trim()}>
                <Plus size={15} />
                Добавить критерий
              </Button>
            </div>
          </section>

          <section style={styles.section}>
            <div style={styles.sectionHeader}>
              <div>
                <h2 style={styles.sectionTitle}>Критерии</h2>
                <p style={styles.sectionText}>Редактируйте поля и переставляйте критерии местами.</p>
              </div>
            </div>

            {criteriaQuery.isError ? <p style={styles.errorText}>{getErrorMessage(criteriaQuery.error)}</p> : null}
            {!criteriaQuery.isError && !sortedCriteria.length ? <p style={styles.mutedText}>Критерии еще не добавлены.</p> : null}

            <div style={styles.list}>
              {sortedCriteria.map((criterion, index) => {
                const draft = criteriaDrafts[criterion.id];
                if (!draft) {
                  return null;
                }

                return (
                  <div key={criterion.id} style={styles.section}>
                    <div style={styles.toolbar}>
                      <div style={styles.toolbarGroup}>
                        <p style={styles.sectionTitle}>{criterion.name}</p>
                        <p style={styles.subtleText}>Позиция {draft.position}</p>
                      </div>
                      <div style={styles.rowActions}>
                        <Button variant="ghost" size="sm" onClick={() => moveCriterion(criterion.id, -1)} disabled={index === 0 || updateCriterionMutation.isPending}>
                          <ArrowUp size={14} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => moveCriterion(criterion.id, 1)}
                          disabled={index === sortedCriteria.length - 1 || updateCriterionMutation.isPending}
                        >
                          <ArrowDown size={14} />
                        </Button>
                        <Button variant="danger" size="sm" onClick={() => handleCriterionDelete(criterion.id)} disabled={deleteCriterionMutation.isPending}>
                          <Trash2 size={14} />
                          Удалить
                        </Button>
                      </div>
                    </div>

                    <div style={styles.formGrid}>
                      <div style={styles.fieldStack}>
                        <Label>Название</Label>
                        <Input
                          value={draft.name}
                          onChange={(event) =>
                            setCriteriaDrafts((current) => ({
                              ...current,
                              [criterion.id]: { ...current[criterion.id], name: event.target.value },
                            }))
                          }
                        />
                      </div>
                      <div style={styles.fieldStack}>
                        <Label>Тип ответа</Label>
                        <Select
                          value={draft.answer_type}
                          onChange={(event) =>
                            setCriteriaDrafts((current) => ({
                              ...current,
                              [criterion.id]: {
                                ...current[criterion.id],
                                answer_type: event.target.value as keyof typeof CriterionAnswerType,
                              },
                            }))
                          }
                        >
                          {Object.values(CriterionAnswerType).map((answerType) => (
                            <option key={answerType} value={answerType}>
                              {answerType}
                            </option>
                          ))}
                        </Select>
                      </div>
                      <div style={styles.fieldStack}>
                        <Label>Позиция</Label>
                        <Input
                          type="number"
                          min={1}
                          value={draft.position}
                          onChange={(event) =>
                            setCriteriaDrafts((current) => ({
                              ...current,
                              [criterion.id]: {
                                ...current[criterion.id],
                                position: Number(event.target.value) || 1,
                              },
                            }))
                          }
                        />
                      </div>
                    </div>
                    <div style={styles.fieldStack}>
                      <Label>Описание</Label>
                      <Textarea
                        value={draft.description}
                        onChange={(event) =>
                          setCriteriaDrafts((current) => ({
                            ...current,
                            [criterion.id]: { ...current[criterion.id], description: event.target.value },
                          }))
                        }
                      />
                    </div>
                    <div style={styles.fieldStack}>
                      <Label>Prompt</Label>
                      <Textarea
                        value={draft.prompt}
                        onChange={(event) =>
                          setCriteriaDrafts((current) => ({
                            ...current,
                            [criterion.id]: { ...current[criterion.id], prompt: event.target.value },
                          }))
                        }
                      />
                    </div>
                    <div style={styles.rowActions}>
                      <Button onClick={() => handleCriterionSave(criterion.id)} disabled={updateCriterionMutation.isPending || !draft.name.trim()}>
                        <Save size={15} />
                        Сохранить критерий
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </>
      ) : null}
    </WorkspaceShell>
  );
}
