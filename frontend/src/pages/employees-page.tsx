import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { MailPlus, Save, Trash2 } from 'lucide-react';

import {
  getListEmployeesRouteEmployeesGetQueryKey,
  useDeleteEmployeeRouteEmployeesEmployeeIdDelete,
  useListEmployeesRouteEmployeesGet,
  useUpdateEmployeeRouteEmployeesEmployeeIdPatch,
} from '../api/generated/client';
import type { EmployeeRead } from '../api/generated/model';
import { createEmployeeInvitation, listEmployeeInvitations } from '../api/employee-invitations';
import { queryClient } from '../app/query-client';
import { invalidateWorkspaceQueries, workspacePaths } from '../app/workspace';
import { useAuth } from '../auth/context';
import { WorkspaceShell } from '../components/workspace/workspace-shell';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { useViewport } from '../hooks/use-viewport';
import { canManageCompany, formatDateTime, formatUserLabel, getErrorMessage, roleLabel } from '../lib/utils';
import { useTheme } from '../theme/theme';
import { getWorkspacePageStyles } from './workspace-page.styles';

type MemberDraft = {
  user_role: 'employee' | 'admin';
  manager_user_id: string;
};

export function EmployeesPage({ companyId }: { companyId: number }) {
  const auth = useAuth();
  const navigate = useNavigate();
  const { tokens } = useTheme();
  const viewport = useViewport();
  const styles = getWorkspacePageStyles(tokens, { compact: viewport.isCompactNav, mobile: viewport.isMobile });
  const isOwner = canManageCompany(auth.user?.role);
  const [inviteEmail, setInviteEmail] = useState('');
  const [memberDrafts, setMemberDrafts] = useState<Record<number, MemberDraft>>({});
  const [activeSaveEmployeeId, setActiveSaveEmployeeId] = useState<number | null>(null);

  const employeesQuery = useListEmployeesRouteEmployeesGet(
    { company_id: companyId },
    {
      query: {
        enabled: Boolean(companyId),
      },
    },
  );
  const invitationsQuery = useQuery({
    queryKey: ['/employees/invitations', { company_id: companyId }],
    queryFn: () => listEmployeeInvitations(companyId),
    enabled: Boolean(companyId && isOwner),
  });
  const inviteMutation = useMutation({
    mutationFn: (email: string) => createEmployeeInvitation(companyId, email),
    onSuccess() {
      setInviteEmail('');
      void invalidateWorkspaceQueries();
    },
  });
  const updateMutation = useUpdateEmployeeRouteEmployeesEmployeeIdPatch({
    mutation: {
      onSuccess(updatedEmployee) {
        queryClient.setQueryData<EmployeeRead[]>(
          getListEmployeesRouteEmployeesGetQueryKey({ company_id: companyId }),
          (current) => current?.map((employee) => (employee.id === updatedEmployee.id ? updatedEmployee : employee)) ?? current,
        );
        setMemberDrafts((current) => ({
          ...current,
          [updatedEmployee.id]: {
            user_role: updatedEmployee.user_role === 'admin' ? 'admin' : 'employee',
            manager_user_id: updatedEmployee.manager_user_id ? String(updatedEmployee.manager_user_id) : '',
          },
        }));
        void invalidateWorkspaceQueries();
      },
    },
  });
  const deleteMutation = useDeleteEmployeeRouteEmployeesEmployeeIdDelete({
    mutation: {
      onSuccess() {
        void invalidateWorkspaceQueries();
      },
    },
  });

  const employees = employeesQuery.data ?? [];
  const invitations = invitationsQuery.data ?? [];
  const managerOptions = useMemo(
    () =>
      employees
        .filter((employee) => employee.user_role === 'admin')
        .map((employee) => ({
          userId: employee.user_id,
          label: formatUserLabel(employee.user_display_name, employee.user_email),
        })),
    [employees],
  );

  useEffect(() => {
    setMemberDrafts(
      Object.fromEntries(
        employees.map((employee) => [
          employee.id,
          {
            user_role: employee.user_role === 'admin' ? 'admin' : 'employee',
            manager_user_id: employee.manager_user_id ? String(employee.manager_user_id) : '',
          },
        ]),
      ),
    );
  }, [employees]);

  async function handleInvite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await inviteMutation.mutateAsync(inviteEmail.trim());
  }

  async function handleSave(employeeId: number) {
    const draft = memberDrafts[employeeId];
    if (!draft) {
      return;
    }

    setActiveSaveEmployeeId(employeeId);

    try {
      await updateMutation.mutateAsync({
        employeeId,
        data: {
          user_role: draft.user_role,
          manager_user_id: draft.user_role === 'admin' ? null : draft.manager_user_id ? Number(draft.manager_user_id) : null,
        },
      });
    } finally {
      setActiveSaveEmployeeId(null);
    }
  }

  async function handleDelete(employeeId: number) {
    if (!window.confirm('Удалить сотрудника из компании?')) {
      return;
    }
    await deleteMutation.mutateAsync({ employeeId });
  }

  return (
    <WorkspaceShell
      title="Сотрудники"
      description="Owner управляет составом компании, а руководитель группы видит только своих прямых сотрудников."
      section="employees"
      companyId={companyId}
      managerOnly
      onCompanyChange={(nextCompanyId) => navigate({ to: workspacePaths.employees(nextCompanyId) })}
    >
      {isOwner ? (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <div>
              <h2 style={styles.sectionTitle}>Пригласить сотрудника</h2>
              <p style={styles.sectionText}>Новый участник приходит как сотрудник, а затем здесь же можно назначить ему роль руководителя группы и подчиненных.</p>
            </div>
          </div>

          <form onSubmit={handleInvite} style={styles.inlineForm}>
            <div style={{ ...styles.fieldStack, ...styles.responsiveField, flex: 1 }}>
              <Label htmlFor="employee-invite-email">Email</Label>
              <Input
                id="employee-invite-email"
                type="email"
                placeholder="name@company.com"
                value={inviteEmail}
                onChange={(event) => setInviteEmail(event.target.value)}
              />
            </div>
            <Button type="submit" disabled={inviteMutation.isPending || !inviteEmail.trim()}>
              <MailPlus size={15} />
              {inviteMutation.isPending ? 'Отправляем...' : 'Отправить приглашение'}
            </Button>
          </form>
          {inviteMutation.isError ? <p style={styles.errorText}>{getErrorMessage(inviteMutation.error)}</p> : null}
        </section>
      ) : null}

      <section style={styles.section}>
        <div style={styles.sectionHeader}>
          <div>
            <h2 style={styles.sectionTitle}>Сотрудники компании</h2>
            <p style={styles.sectionText}>
              {isOwner ? 'Назначайте роли и руководителей прямо в этом списке.' : 'Здесь показаны ваш профиль в компании и ваши прямые сотрудники.'}
            </p>
          </div>
        </div>

        {employeesQuery.isError ? <p style={styles.errorText}>{getErrorMessage(employeesQuery.error)}</p> : null}
        {updateMutation.isError ? <p style={styles.errorText}>{getErrorMessage(updateMutation.error)}</p> : null}
        {!employeesQuery.isError && !employees.length ? <p style={styles.mutedText}>Сотрудники пока не добавлены.</p> : null}

        <div style={styles.list}>
          {employees.map((employee) => {
            const draft = memberDrafts[employee.id];
            const currentRole = (employee.user_role ?? 'employee') as 'owner' | 'employee' | 'admin';

            return (
              <div key={employee.id} style={styles.listItem}>
                <div style={styles.listItemBody}>
                  <p style={styles.listItemTitle}>{employee.user_display_name ?? `Пользователь #${employee.user_id}`}</p>
                  <p style={styles.sectionText}>{employee.user_email ?? 'Email недоступен'}</p>
                  <p style={styles.listItemMeta}>Роль: {roleLabel(currentRole)}</p>
                  {employee.manager_display_name || employee.manager_email ? (
                    <p style={styles.listItemMeta}>Руководитель: {formatUserLabel(employee.manager_display_name, employee.manager_email)}</p>
                  ) : (
                    <p style={styles.listItemMeta}>Руководитель не назначен</p>
                  )}
                  <p style={styles.listItemMeta}>В компании с {formatDateTime(employee.created_at)}</p>
                </div>

                {isOwner ? (
                  <div style={{ ...styles.stack, width: viewport.isMobile ? '100%' : undefined, minWidth: viewport.isMobile ? 0 : 300 }}>
                    <div style={styles.formGrid}>
                      <div style={styles.fieldStack}>
                        <Label htmlFor={`employee-role-${employee.id}`}>Роль</Label>
                        <Select
                          id={`employee-role-${employee.id}`}
                          value={draft?.user_role ?? 'employee'}
                          onChange={(event) =>
                            setMemberDrafts((current) => ({
                              ...current,
                              [employee.id]: {
                                user_role: event.target.value as 'employee' | 'admin',
                                manager_user_id: event.target.value === 'admin' ? '' : current[employee.id]?.manager_user_id ?? '',
                              },
                            }))
                          }
                        >
                          <option value="employee">Сотрудник</option>
                          <option value="admin">Администратор</option>
                        </Select>
                      </div>

                      <div style={styles.fieldStack}>
                        <Label htmlFor={`employee-manager-${employee.id}`}>Руководитель</Label>
                        <Select
                          id={`employee-manager-${employee.id}`}
                          value={draft?.manager_user_id ?? ''}
                          onChange={(event) =>
                            setMemberDrafts((current) => ({
                              ...current,
                              [employee.id]: {
                                user_role: current[employee.id]?.user_role ?? 'employee',
                                manager_user_id: event.target.value,
                              },
                            }))
                          }
                          disabled={(draft?.user_role ?? 'employee') === 'admin'}
                        >
                          <option value="">Без руководителя</option>
                          {managerOptions
                            .filter((option) => option.userId !== employee.user_id)
                            .map((option) => (
                              <option key={option.userId} value={option.userId}>
                                {option.label}
                              </option>
                            ))}
                        </Select>
                      </div>
                    </div>

                    <div style={styles.rowActions}>
                      <Button variant="secondary" size="sm" onClick={() => handleSave(employee.id)} disabled={updateMutation.isPending}>
                        <Save size={14} />
                        {activeSaveEmployeeId === employee.id && updateMutation.isPending ? 'Сохраняем...' : 'Сохранить'}
                      </Button>
                      <Button variant="danger" size="sm" onClick={() => handleDelete(employee.id)} disabled={deleteMutation.isPending}>
                        <Trash2 size={14} />
                        Удалить
                      </Button>
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      {isOwner ? (
        <section style={styles.section}>
          <div style={styles.sectionHeader}>
            <div>
              <h2 style={styles.sectionTitle}>Приглашения</h2>
              <p style={styles.sectionText}>История отправленных инвайтов по этой компании.</p>
            </div>
          </div>

          {invitationsQuery.isError ? <p style={styles.errorText}>{getErrorMessage(invitationsQuery.error)}</p> : null}
          {!invitationsQuery.isError && !invitations.length ? <p style={styles.mutedText}>Приглашений пока нет.</p> : null}

          <div style={styles.list}>
            {invitations.map((invitation) => (
              <div key={invitation.id} style={styles.listItem}>
                <div style={styles.listItemBody}>
                  <p style={styles.listItemTitle}>{invitation.email}</p>
                  <p style={styles.sectionText}>Статус: {invitation.status}</p>
                  <p style={styles.listItemMeta}>Отправил: {invitation.invited_by_display_name ?? invitation.invited_by_email ?? 'Неизвестно'}</p>
                  <p style={styles.listItemMeta}>Создано: {formatDateTime(invitation.created_at)} · Действует до: {formatDateTime(invitation.expires_at)}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </WorkspaceShell>
  );
}
