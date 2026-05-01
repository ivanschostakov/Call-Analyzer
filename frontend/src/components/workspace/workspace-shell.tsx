import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart2,
  Bell,
  Building2,
  Link2,
  FileAudio2,
  FileText,
  GraduationCap,
  LogOut,
  Menu,
  Moon,
  Settings2,
  Sparkles,
  Star,
  Sun,
  X,
  Users,
} from 'lucide-react';

import { getDailyReport } from '../../api/daily-report';

import { workspacePaths, type WorkspaceSection } from '../../app/workspace';
import { useAuth } from '../../auth/context';
import { canManageCompany, canManageTeam, getErrorMessage, roleLabel } from '../../lib/utils';
import { useTheme } from '../../theme/theme';
import { useViewport } from '../../hooks/use-viewport';
import { useWorkspace } from '../../workspace/workspace-context';
import { CreateCompanyForm } from '../dashboard/create-company-form';
import { EmptyStatePanel } from '../dashboard/empty-state-panel';
import { Button } from '../ui/button';
import { Select } from '../ui/select';
import { getWorkspaceShellStyles } from './workspace.styles';

type WorkspaceShellProps = {
  title: string;
  description?: string;
  section: WorkspaceSection;
  companyId?: number | null;
  wideContent?: boolean;
  compactTopbar?: boolean;
  managerOnly?: boolean;
  ownerOnly?: boolean;
  companyOwnerOnly?: boolean;
  onCompanyChange?: (companyId: number) => void;
  actions?: React.ReactNode;
  children: React.ReactNode;
};

function getDailyReportDismissKey(companyId: number) {
  return `daily_report_dismissed_${companyId}`;
}

function getDismissedDate(companyId: number): string | null {
  try {
    return localStorage.getItem(getDailyReportDismissKey(companyId));
  } catch {
    return null;
  }
}

function setDismissedDate(companyId: number, date: string) {
  try {
    localStorage.setItem(getDailyReportDismissKey(companyId), date);
  } catch {
    // ignore
  }
}

export function WorkspaceShell({
  title,
  description,
  section,
  companyId,
  wideContent = false,
  compactTopbar = false,
  managerOnly = false,
  ownerOnly = false,
  companyOwnerOnly = false,
  onCompanyChange,
  actions,
  children,
}: WorkspaceShellProps) {
  const auth = useAuth();
  const workspace = useWorkspace();
  const { mode, toggleMode, tokens } = useTheme();
  const location = useLocation();
  const viewport = useViewport();
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [notificationDismissed, setNotificationDismissed] = useState(false);
  const notificationChecked = useRef(false);
  const styles = getWorkspaceShellStyles(tokens, {
    wideContent,
    compactTopbar,
    compactNav: viewport.isCompactNav,
    isMobile: viewport.isMobile,
  });
  const canManageCurrentCompany = canManageCompany(auth.user?.role);
  const canManageCurrentTeam = canManageTeam(auth.user?.role);
  const activeCompanyId = companyId ?? workspace.currentCompanyId;

  const yesterday = (() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().slice(0, 10);
  })();

  const dailyReportQuery = useQuery({
    queryKey: ['/daily-report/notification', activeCompanyId, yesterday],
    queryFn: () => getDailyReport(activeCompanyId!, yesterday),
    enabled: canManageCurrentTeam && Boolean(activeCompanyId) && !notificationDismissed,
    retry: false,
    staleTime: 1000 * 60 * 10,
  });

  const showNotification = (() => {
    if (notificationDismissed) return false;
    if (!dailyReportQuery.data) return false;
    if (!activeCompanyId) return false;
    const dismissed = getDismissedDate(activeCompanyId);
    return dismissed !== yesterday;
  })();

  useEffect(() => {
    if (!notificationChecked.current && activeCompanyId) {
      const dismissed = getDismissedDate(activeCompanyId);
      if (dismissed === yesterday) {
        setNotificationDismissed(true);
      }
      notificationChecked.current = true;
    }
  }, [activeCompanyId, yesterday]);
  const currentCompany = companyId ? workspace.getCompanyById(companyId) : workspace.currentCompany;
  const isCurrentCompanyOwner = Boolean(currentCompany && auth.user?.id === currentCompany.owner_id);
  const selectedCompanyId = workspace.selectedCompanyId;
  const getCompanyById = workspace.getCompanyById;
  const setCurrentCompanyId = workspace.setCurrentCompanyId;

  useEffect(() => {
    if (companyId && selectedCompanyId !== companyId && getCompanyById(companyId)) {
      setCurrentCompanyId(companyId);
    }
  }, [companyId, getCompanyById, selectedCompanyId, setCurrentCompanyId]);

  useEffect(() => {
    if (!viewport.isCompactNav) {
      setDrawerOpen(false);
    }
  }, [viewport.isCompactNav]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [activeCompanyId, location.pathname]);

  useEffect(() => {
    if (!drawerOpen || !viewport.isCompactNav || typeof document === 'undefined') {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [drawerOpen, viewport.isCompactNav]);

  if (!auth.isAuthenticated) {
    return <Navigate to="/login" />;
  }

  function handleCompanySelect(nextCompanyId: number) {
    workspace.setCurrentCompanyId(nextCompanyId);
    onCompanyChange?.(nextCompanyId);
    setDrawerOpen(false);
  }

  function renderSidebarContent() {
    return (
      <>
        <div style={styles.brand}>
          <p style={styles.brandName}>Call Analyzer</p>
          <p style={styles.brandMeta}>Рабочее пространство компании</p>
        </div>

        <div style={styles.nav}>
          <p style={styles.navLabel}>Разделы</p>
          <WorkspaceNavLink
            label="Обзор"
            icon={<Building2 size={16} />}
            href={workspacePaths.dashboard()}
            active={section === 'dashboard'}
            compact={viewport.isCompactNav}
            onNavigate={() => setDrawerOpen(false)}
          />
          <WorkspaceNavLink
            label="Отчеты"
            icon={<Sparkles size={16} />}
            href={activeCompanyId ? workspacePaths.analyses(activeCompanyId) : workspacePaths.dashboard()}
            active={section === 'reports'}
            disabled={!activeCompanyId}
            compact={viewport.isCompactNav}
            onNavigate={() => setDrawerOpen(false)}
          />
          <WorkspaceNavLink
            label="Расшифровки"
            icon={<FileText size={16} />}
            href={activeCompanyId ? workspacePaths.transcriptions(activeCompanyId) : workspacePaths.dashboard()}
            active={section === 'transcriptions'}
            disabled={!activeCompanyId}
            compact={viewport.isCompactNav}
            onNavigate={() => setDrawerOpen(false)}
          />
          <WorkspaceNavLink
            label="Ментор"
            icon={<GraduationCap size={16} />}
            href={activeCompanyId ? workspacePaths.mentor(activeCompanyId) : workspacePaths.dashboard()}
            active={section === 'mentor'}
            disabled={!activeCompanyId}
            compact={viewport.isCompactNav}
            onNavigate={() => setDrawerOpen(false)}
          />
          {canManageCurrentTeam ? (
            <WorkspaceNavLink
              label="График роста"
              icon={<BarChart2 size={16} />}
              href={activeCompanyId ? workspacePaths.performanceChart(activeCompanyId) : workspacePaths.dashboard()}
              active={section === 'performance-chart'}
              disabled={!activeCompanyId}
              compact={viewport.isCompactNav}
              onNavigate={() => setDrawerOpen(false)}
            />
          ) : null}
          {canManageCurrentTeam ? (
            <WorkspaceNavLink
              label="Дневной отчёт"
              icon={<Bell size={16} />}
              href={activeCompanyId ? workspacePaths.dailyReport(activeCompanyId) : workspacePaths.dashboard()}
              active={section === 'daily-report'}
              disabled={!activeCompanyId}
              compact={viewport.isCompactNav}
              onNavigate={() => setDrawerOpen(false)}
              badge={showNotification}
            />
          ) : null}
          <WorkspaceNavLink
            label="Загрузки"
            icon={<FileAudio2 size={16} />}
            href={activeCompanyId ? workspacePaths.uploads(activeCompanyId) : workspacePaths.dashboard()}
            active={section === 'uploads'}
            disabled={!activeCompanyId}
            compact={viewport.isCompactNav}
            onNavigate={() => setDrawerOpen(false)}
          />
          <WorkspaceNavLink
            label="Избранное"
            icon={<Star size={16} />}
            href={activeCompanyId ? workspacePaths.favorites(activeCompanyId) : workspacePaths.dashboard()}
            active={section === 'favorites'}
            disabled={!activeCompanyId}
            compact={viewport.isCompactNav}
            onNavigate={() => setDrawerOpen(false)}
          />
          {canManageCurrentTeam ? (
            <WorkspaceNavLink
              label="Сотрудники"
              icon={<Users size={16} />}
              href={activeCompanyId ? workspacePaths.employees(activeCompanyId) : workspacePaths.dashboard()}
              active={section === 'employees'}
              disabled={!activeCompanyId}
              compact={viewport.isCompactNav}
              onNavigate={() => setDrawerOpen(false)}
            />
          ) : null}
          {canManageCurrentCompany ? (
            <WorkspaceNavLink
              label="Интеграции"
              icon={<Link2 size={16} />}
              href={activeCompanyId ? workspacePaths.integrations(activeCompanyId) : workspacePaths.dashboard()}
              active={section === 'integrations'}
              disabled={!activeCompanyId}
              compact={viewport.isCompactNav}
              onNavigate={() => setDrawerOpen(false)}
            />
          ) : null}
          {canManageCurrentCompany ? (
            <WorkspaceNavLink
              label="Настройки"
              icon={<Settings2 size={16} />}
              href={activeCompanyId ? workspacePaths.settings(activeCompanyId) : workspacePaths.dashboard()}
              active={section === 'settings'}
              disabled={!activeCompanyId}
              compact={viewport.isCompactNav}
              onNavigate={() => setDrawerOpen(false)}
            />
          ) : null}
        </div>

        <div style={styles.spacer} />

        <div style={styles.userCard}>
          <p style={styles.userName}>
            {auth.user?.name} {auth.user?.surname}
          </p>
          <div style={styles.userIdentity}>
            <p style={styles.userMeta}>{auth.user?.email}</p>
            <p style={styles.userMeta}>{roleLabel(auth.user?.role ?? 'employee')}</p>
          </div>
          <div style={styles.userActions}>
            <Button variant="ghost" size="sm" onClick={toggleMode}>
              {mode === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              {mode === 'dark' ? 'Light' : 'Dark'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setDrawerOpen(false);
                auth.logout();
              }}
            >
              <LogOut size={15} />
              Выйти
            </Button>
          </div>
        </div>
      </>
    );
  }

  function handleDismissNotification() {
    if (activeCompanyId) {
      setDismissedDate(activeCompanyId, yesterday);
    }
    setNotificationDismissed(true);
  }

  function renderDailyReportNotification() {
    if (!showNotification || !dailyReportQuery.data) return null;
    const report = dailyReportQuery.data;
    return (
      <div
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: 1000,
          width: 320,
          borderRadius: 18,
          background: tokens.surface,
          boxShadow: `0 8px 32px rgba(0,0,0,0.18)`,
          border: `1.5px solid ${tokens.surfaceMuted}`,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '14px 16px 10px',
            borderBottom: `1px solid ${tokens.surfaceMuted}`,
          }}
        >
          <Bell size={16} color={tokens.warning} />
          <p style={{ margin: 0, fontSize: 14, fontWeight: 700, flex: 1 }}>Ежедневный отчёт готов</p>
          <button
            type="button"
            onClick={handleDismissNotification}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: tokens.textMuted,
              padding: 2,
              display: 'flex',
              alignItems: 'center',
            }}
            aria-label="Закрыть"
          >
            <X size={16} />
          </button>
        </div>
        <div style={{ padding: '10px 16px' }}>
          <p style={{ margin: '0 0 4px', fontSize: 13, color: tokens.textMuted }}>
            За вчерашний день · {report.total_calls} {report.total_calls === 1 ? 'звонок' : report.total_calls < 5 ? 'звонка' : 'звонков'}
          </p>
          <p style={{ margin: 0, fontSize: 13, color: tokens.textMuted }}>
            Среднее качество: <strong style={{ color: tokens.text }}>{report.average_score.toFixed(1)}%</strong>
            {' · '}Лучших: <strong style={{ color: tokens.success }}>{report.best_calls.length}</strong>
            {' · '}Худших: <strong style={{ color: tokens.danger }}>{report.worst_calls.length}</strong>
          </p>
        </div>
        <div style={{ padding: '8px 16px 14px', display: 'flex', gap: 8 }}>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              handleDismissNotification();
              if (activeCompanyId) {
                void navigate({ to: workspacePaths.dailyReport(activeCompanyId) });
              }
            }}
          >
            Открыть отчёт
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDismissNotification}>
            Скрыть
          </Button>
        </div>
      </div>
    );
  }

  function renderMainContent(content: React.ReactNode) {
    return (
      <div style={styles.root}>
        {viewport.isCompactNav ? (
          <>
            <div style={styles.compactBar}>
              <div style={styles.compactBarBrand}>
                <p style={styles.compactBarTitle}>Call Analyzer</p>
                <p style={styles.compactBarMeta}>{currentCompany?.name ?? 'Рабочее пространство компании'}</p>
              </div>
              <button
                type="button"
                style={styles.compactBarButton}
                onClick={() => setDrawerOpen((current) => !current)}
                aria-label={drawerOpen ? 'Закрыть меню' : 'Открыть меню'}
                aria-expanded={drawerOpen}
              >
                {drawerOpen ? <X size={18} /> : <Menu size={18} />}
              </button>
            </div>

            {drawerOpen ? <div style={styles.drawerBackdrop} onClick={() => setDrawerOpen(false)} /> : null}
            {drawerOpen ? (
              <div style={styles.drawerShell}>
                <div style={styles.drawerPanel} onClick={(event) => event.stopPropagation()}>
                  <aside style={styles.sidebarCard}>{renderSidebarContent()}</aside>
                </div>
              </div>
            ) : null}
          </>
        ) : (
          <aside style={styles.sidebarDesktop}>
            <div style={styles.sidebarCard}>{renderSidebarContent()}</div>
          </aside>
        )}

        <main style={styles.main}>
          <div style={styles.mainInner}>{content}</div>
        </main>
        {renderDailyReportNotification()}
      </div>
    );
  }

  if (auth.isBootstrapping || workspace.isLoading) {
    return renderMainContent(<div style={styles.loadingCard}>Загружаем рабочее пространство...</div>);
  }

  if (workspace.isError) {
    return renderMainContent(
      <EmptyStatePanel
        title="Не удалось загрузить компании"
        description={getErrorMessage(workspace.error)}
        action={
          <Button variant="secondary" onClick={() => workspace.refetchCompanies()}>
            Повторить
          </Button>
        }
      />,
    );
  }

  if (!workspace.companies.length) {
    return renderMainContent(
      canManageCurrentCompany ? (
        <EmptyStatePanel
          title="Пока нет компаний"
          description="Создайте первую компанию, и после этого станут доступны загрузки, шаблоны и отчеты."
          action={<CreateCompanyForm onCreated={() => workspace.refetchCompanies()} />}
        />
      ) : (
        <EmptyStatePanel
          title="Нет доступа к компаниям"
          description="Вас еще не подключили ни к одной компании. Обратитесь к владельцу или администратору."
          action={<Button onClick={() => auth.logout()}>Выйти</Button>}
        />
      ),
    );
  }

  if (companyId && !currentCompany) {
    return renderMainContent(
      <EmptyStatePanel
        title="Компания недоступна"
        description="Эта компания не найдена в вашем списке доступа."
        action={
          <Button onClick={() => workspace.setCurrentCompanyId(workspace.companies[0].id)}>Открыть доступную компанию</Button>
        }
      />,
    );
  }

  if (managerOnly && !canManageCurrentTeam) {
    return renderMainContent(
        <EmptyStatePanel
          title="Недостаточно прав"
          description="Этот раздел доступен только владельцу и администраторам."
        action={
          <Link to={workspacePaths.dashboard()} style={{ textDecoration: 'none' }}>
            <Button variant="secondary">Вернуться на обзор</Button>
          </Link>
        }
      />,
    );
  }

  if (ownerOnly && !canManageCurrentCompany) {
    return renderMainContent(
        <EmptyStatePanel
          title="Недостаточно прав"
          description="Этот раздел доступен только владельцу компании или администратору."
        action={
          <Link to={workspacePaths.dashboard()} style={{ textDecoration: 'none' }}>
            <Button variant="secondary">Вернуться на обзор</Button>
          </Link>
        }
      />,
    );
  }

  if (companyOwnerOnly && !isCurrentCompanyOwner) {
    return renderMainContent(
      <EmptyStatePanel
        title="Недостаточно прав"
        description="Этот раздел доступен только владельцу текущей компании."
        action={
          <Link to={workspacePaths.dashboard()} style={{ textDecoration: 'none' }}>
            <Button variant="secondary">Вернуться на обзор</Button>
          </Link>
        }
      />,
    );
  }

  const displayedCompany = currentCompany ?? workspace.currentCompany;

  return renderMainContent(
    <>
      <header style={styles.topbar}>
        <div style={styles.topbarTitleBlock}>
          <h1 style={styles.pageTitle}>{title}</h1>
          {description ? <p style={styles.pageDescription}>{description}</p> : null}
          {displayedCompany ? <p style={styles.companyMeta}>{displayedCompany.name}</p> : null}
        </div>

        <div style={styles.topbarActions}>
          <Select
            value={activeCompanyId ?? ''}
            onChange={(event) => {
              const nextCompanyId = Number(event.target.value);
              handleCompanySelect(nextCompanyId);
            }}
            style={styles.companyPicker}
          >
            {workspace.companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </Select>

          {actions}
        </div>
      </header>

      <div key={location.pathname} style={styles.content}>
        {children}
      </div>
    </>,
  );
}

function WorkspaceNavLink({
  label,
  icon,
  href,
  active,
  disabled = false,
  compact = false,
  badge = false,
  onNavigate,
}: {
  label: string;
  icon: React.ReactNode;
  href: string;
  active: boolean;
  disabled?: boolean;
  compact?: boolean;
  badge?: boolean;
  onNavigate?: () => void;
}) {
  const { tokens } = useTheme();
  const styles = getWorkspaceShellStyles(tokens, { compactNav: compact });

  if (disabled) {
    return (
      <span
        style={{
          ...styles.navLink,
          opacity: 0.45,
          cursor: 'not-allowed',
        }}
      >
        <span style={styles.navLinkIcon}>{icon}</span>
        {label}
      </span>
    );
  }

  return (
    <Link
      to={href}
      onClick={onNavigate}
      style={{
        ...styles.navLink,
        ...(active ? styles.navLinkActive : undefined),
        position: 'relative',
      }}
    >
      <span style={styles.navLinkIcon}>{icon}</span>
      {label}
      {badge ? (
        <span
          style={{
            position: 'absolute',
            top: 6,
            right: 8,
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: tokens.warning,
          }}
        />
      ) : null}
    </Link>
  );
}
