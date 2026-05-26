import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Database, RefreshCw, Save, Trash2, Upload } from 'lucide-react';

import {
  useClearCompanyVectorStoreRouteCompaniesCompanyIdVectorStoreDelete,
  useGetCompanyVectorStoreRouteCompaniesCompanyIdVectorStoreGet,
  useUpdateCompanyRouteCompaniesCompanyIdPatch,
} from '../api/generated/client';
import { createCompanyVectorStore, listCompanyVectorStoreFiles, uploadCompanyVectorStoreFiles } from '../api/vector-store';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { Badge } from '../components/ui/badge';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { SectionCard } from '../components/ui/section-card';
import { Textarea } from '../components/ui/textarea';
import { useViewport } from '../hooks/use-viewport';
import { formatDateTime, getErrorMessage } from '../lib/utils';
import { useTheme } from '../theme/theme';
import { useWorkspace } from '../workspace/workspace-context';
import { getWorkspacePageStyles } from './workspace-page.styles';

function formatBytes(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  if (bytes < 1024 * 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function vectorStoreFileTone(status: string): 'success' | 'warning' | 'danger' | 'default' {
  if (status === 'completed') {
    return 'success';
  }
  if (status === 'failed' || status === 'cancelled') {
    return 'danger';
  }
  if (status === 'in_progress') {
    return 'warning';
  }
  return 'default';
}

export function SettingsPage({ companyId }: { companyId: number }) {
  const navigate = useNavigate();
  const workspace = useWorkspace();
  const currentCompany = workspace.getCompanyById(companyId);
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [name, setName] = useState(currentCompany?.name ?? '');
  const [description, setDescription] = useState(currentCompany?.description ?? '');
  const [transcriptionHintPrompt, setTranscriptionHintPrompt] = useState(currentCompany?.transcription_hint_prompt ?? '');
  const [newVectorStoreName, setNewVectorStoreName] = useState(currentCompany?.name ?? '');

  const vectorStoreQuery = useGetCompanyVectorStoreRouteCompaniesCompanyIdVectorStoreGet(companyId, {
    query: {
      enabled: Boolean(companyId),
    },
  });
  const vectorStoreId = vectorStoreQuery.data?.vector_store_id?.trim() ?? '';

  const vectorStoreFilesQuery = useQuery({
    queryKey: [`/companies/${companyId}/vector-store/files`, { companyId, vectorStoreId }],
    queryFn: () => listCompanyVectorStoreFiles(companyId),
    enabled: Boolean(companyId && vectorStoreId),
    refetchInterval(query) {
      const items = query.state.data ?? [];
      return items.some((item) => item.status === 'in_progress') ? 5_000 : false;
    },
  });
  const updateCompanyMutation = useUpdateCompanyRouteCompaniesCompanyIdPatch({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });
  const createVectorStoreMutation = useMutation({
    mutationFn: (storeName: string) => createCompanyVectorStore(companyId, storeName),
    onSuccess() {
      void invalidateWorkspaceQueries();
    },
  });
  const uploadVectorStoreFilesMutation = useMutation({
    mutationFn: (files: File[]) => uploadCompanyVectorStoreFiles(companyId, files),
    onSuccess() {
      void invalidateWorkspaceQueries();
      void vectorStoreFilesQuery.refetch();
    },
  });
  const clearVectorStoreMutation = useClearCompanyVectorStoreRouteCompaniesCompanyIdVectorStoreDelete({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });

  useEffect(() => {
    setName(currentCompany?.name ?? '');
    setDescription(currentCompany?.description ?? '');
    setTranscriptionHintPrompt(currentCompany?.transcription_hint_prompt ?? '');
  }, [currentCompany]);

  useEffect(() => {
    if (!vectorStoreId) {
      setNewVectorStoreName(currentCompany?.name ?? '');
    }
  }, [currentCompany?.name, vectorStoreId]);

  async function handleCompanySave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await updateCompanyMutation.mutateAsync({
      companyId,
      data: {
        name,
        description: description || undefined,
        transcription_hint_prompt: transcriptionHintPrompt || undefined,
      },
    });
  }

  async function handleVectorStoreCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createVectorStoreMutation.mutateAsync(newVectorStoreName.trim() || currentCompany?.name || `Company ${companyId}`);
  }

  async function handleKnowledgeFilesUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) {
      return;
    }

    try {
      await uploadVectorStoreFilesMutation.mutateAsync(files);
    } finally {
      event.target.value = '';
    }
  }

  async function handleVectorStoreClear() {
    if (!window.confirm('Отключить vector store от этой компании?')) {
      return;
    }
    await clearVectorStoreMutation.mutateAsync({ companyId });
  }

  return (
    <WorkspaceShell
      title="Настройки"
      description="Название компании, описание и настройка knowledge base для retrieval для владельца или администратора."
      section="settings"
      companyId={companyId}
      ownerOnly
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.settings(nextCompanyId) })}
    >
      <SectionCard
        title="Компания"
        description="Короткое описание можно использовать как внутренний ориентир для команды, а hint поможет локальной и удаленной транскрибации лучше распознавать ваши термины."
      >
        <form onSubmit={handleCompanySave} style={styles.stack}>
          <div style={styles.formGrid}>
            <div style={styles.fieldStack}>
              <Label htmlFor="settings-name">Название</Label>
              <Input id="settings-name" value={name} onChange={(event) => setName(event.target.value)} />
            </div>
          </div>
          <div style={styles.fieldStack}>
            <Label htmlFor="settings-description">Описание</Label>
            <Textarea id="settings-description" value={description} onChange={(event) => setDescription(event.target.value)} />
          </div>
          <div style={styles.fieldStack}>
            <Label htmlFor="settings-transcription-hint">Hint для транскрибации</Label>
            <Textarea
              id="settings-transcription-hint"
              value={transcriptionHintPrompt}
              onChange={(event) => setTranscriptionHintPrompt(event.target.value)}
              placeholder="Например: названия продуктов, имена менеджеров, внутренние термины, бренды, городские названия."
            />
          </div>
          <p style={styles.note}>
            Этот hint будет передаваться и локальной, и удаленной транскрибации как подсказка по терминологии компании.
          </p>
          {updateCompanyMutation.isError ? <p style={styles.errorText}>{getErrorMessage(updateCompanyMutation.error)}</p> : null}
          <div style={styles.rowActions}>
            <Button type="submit" disabled={updateCompanyMutation.isPending || !name.trim()}>
              <Save size={15} />
              Сохранить компанию
            </Button>
          </div>
        </form>
      </SectionCard>

      <SectionCard
        title="Knowledge Base"
        description="Владелец или администратор создает vector store один раз, затем загружает в него файлы для retrieval. Эти файлы не сохраняются у нас локально и сразу уходят в OpenAI vector store."
      >
        {vectorStoreQuery.isError ? <p style={styles.errorText}>{getErrorMessage(vectorStoreQuery.error)}</p> : null}
        {createVectorStoreMutation.isError ? <p style={styles.errorText}>{getErrorMessage(createVectorStoreMutation.error)}</p> : null}
        {uploadVectorStoreFilesMutation.isError ? <p style={styles.errorText}>{getErrorMessage(uploadVectorStoreFilesMutation.error)}</p> : null}
        {clearVectorStoreMutation.isError ? <p style={styles.errorText}>{getErrorMessage(clearVectorStoreMutation.error)}</p> : null}
        {vectorStoreFilesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(vectorStoreFilesQuery.error)}</p> : null}

        {!vectorStoreId ? (
          <form onSubmit={handleVectorStoreCreate} style={styles.stack}>
            <div style={styles.inlineForm}>
              <div style={{ ...styles.fieldStack, ...styles.responsiveField, flex: 1 }}>
                <Label htmlFor="settings-vector-store-name">Название vector store</Label>
                <Input
                  id="settings-vector-store-name"
                  value={newVectorStoreName}
                  onChange={(event) => setNewVectorStoreName(event.target.value)}
                  placeholder={currentCompany?.name ?? 'Knowledge Base'}
                />
              </div>
              <Button type="submit" disabled={createVectorStoreMutation.isPending}>
                <Database size={15} />
                {createVectorStoreMutation.isPending ? 'Создаем...' : 'Создать vector store'}
              </Button>
            </div>
            <p style={styles.note}>
              После создания store привяжется к текущей компании, и сюда можно будет загружать PDF, DOCX, TXT, Markdown и другие knowledge-файлы для retrieval.
            </p>
          </form>
        ) : (
          <>
            <input ref={fileInputRef} type="file" multiple hidden onChange={handleKnowledgeFilesUpload} />

            <div style={styles.triple}>
              <div style={styles.infoCard}>
                <p style={styles.infoTitle}>Vector store ID</p>
                <p style={styles.monoText}>{vectorStoreId}</p>
              </div>
              <div style={styles.infoCard}>
                <p style={styles.infoTitle}>Файлов в store</p>
                <p style={styles.sectionText}>{vectorStoreFilesQuery.data?.length ?? 0}</p>
              </div>
              <div style={styles.infoCard}>
                <p style={styles.infoTitle}>Хранение у нас</p>
                <p style={styles.sectionText}>Не храним</p>
                <p style={styles.subtleText}>Файлы идут только в OpenAI vector store</p>
              </div>
            </div>

            <div style={styles.rowActions}>
              <Button onClick={() => fileInputRef.current?.click()} disabled={uploadVectorStoreFilesMutation.isPending}>
                <Upload size={15} />
                {uploadVectorStoreFilesMutation.isPending ? 'Загружаем в store...' : 'Загрузить файлы в vector store'}
              </Button>
              <Button variant="ghost" onClick={() => vectorStoreFilesQuery.refetch()} disabled={vectorStoreFilesQuery.isFetching}>
                <RefreshCw size={15} />
                Обновить список
              </Button>
              <Button variant="ghost" onClick={handleVectorStoreClear} disabled={clearVectorStoreMutation.isPending}>
                <Trash2 size={15} />
                Отключить store
              </Button>
            </div>

            <p style={styles.note}>
              Загружаемые файлы не попадают в раздел `Загрузки` и не сохраняются в нашем файловом хранилище. Они используются только как база знаний для анализа.
            </p>

            {vectorStoreFilesQuery.isPending ? <p style={styles.mutedText}>Загружаем список файлов...</p> : null}
            {!vectorStoreFilesQuery.isPending && !vectorStoreFilesQuery.data?.length ? (
              <p style={styles.mutedText}>В этом vector store пока нет файлов.</p>
            ) : null}

            <div style={styles.list}>
              {(vectorStoreFilesQuery.data ?? []).map((item) => (
                <div key={item.id} style={styles.listItem}>
                  <div style={styles.listItemBody}>
                    <p style={styles.listItemTitle}>{item.filename}</p>
                    <p style={styles.listItemMeta}>
                      {formatBytes(item.usage_bytes)} · {formatDateTime(item.created_at)}
                    </p>
                    {item.last_error_message ? <p style={{ ...styles.subtleText, color: tokens.danger }}>{item.last_error_message}</p> : null}
                  </div>
                  <Badge tone={vectorStoreFileTone(item.status)}>{item.status}</Badge>
                </div>
              ))}
            </div>
          </>
        )}
      </SectionCard>
    </WorkspaceShell>
  );
}
