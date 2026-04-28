import { Outlet, createRootRoute, createRoute, createRouter, redirect } from '@tanstack/react-router';

import { workspacePaths } from './app/workspace';
import { queryClient } from './app/query-client';
import { useAuth } from './auth/context';
import { authStore } from './auth/store';
import { AnalysisDetailPage } from './pages/analysis-detail-page';
import { AnalysesPage } from './pages/analyses-page';
import { DashboardPage } from './pages/dashboard-page';
import { EmployeesPage } from './pages/employees-page';
import { FavoritesPage } from './pages/favorites-page';
import { IntegrationsPage } from './pages/integrations-page';
import { LoginPage, RegisterPage } from './pages/login-page';
import { MentorPage } from './pages/mentor-page';
import { SettingsPage } from './pages/settings-page';
import { TemplateDetailPage } from './pages/template-detail-page';
import { TemplatesPage } from './pages/templates-page';
import { TranscriptionsPage } from './pages/transcriptions-page';
import { UploadsPage } from './pages/uploads-page';
import { useTheme } from './theme/theme';
import { getContainerStyle, getPageStyle, getSurfaceStyle } from './theme/theme.styles';

function RootLayout() {
  const auth = useAuth();
  const { tokens } = useTheme();

  if (auth.isBootstrapping) {
    return (
      <div
        style={{
          ...getPageStyle(tokens),
          display: 'grid',
          placeItems: 'center',
        }}
      >
        <div
          style={{
            ...getContainerStyle(),
            display: 'flex',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              ...getSurfaceStyle(tokens, {
                background: tokens.surfaceMuted,
                padding: '18px 24px',
                radius: 20,
              }),
              fontSize: 15,
              color: tokens.textMuted,
            }}
          >
            Проверяем сессию...
          </div>
        </div>
      </div>
    );
  }

  return <Outlet />;
}

function requireAuth() {
  if (!authStore.getSnapshot()) {
    throw redirect({ to: '/login' });
  }
}

const rootRoute = createRootRoute({
  component: RootLayout,
});

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  beforeLoad: requireAuth,
  component: DashboardPage,
});

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/login',
  beforeLoad: () => {
    if (authStore.getSnapshot()) {
      throw redirect({ to: '/' });
    }
  },
  component: LoginPage,
});

const registerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/register',
  beforeLoad: () => {
    if (authStore.getSnapshot()) {
      throw redirect({ to: '/' });
    }
  },
  component: RegisterPage,
});

const uploadsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/uploads',
  beforeLoad: requireAuth,
  component: UploadsRouteComponent,
});

const favoritesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/favorites',
  beforeLoad: requireAuth,
  component: FavoritesRouteComponent,
});

const favouritesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/favourites',
  beforeLoad: ({ params }) => {
    requireAuth();
    throw redirect({ to: workspacePaths.favorites(params.companyId) });
  },
});

const transcriptionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/transcriptions',
  beforeLoad: requireAuth,
  component: TranscriptionsRouteComponent,
});

const mentorRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/mentor',
  beforeLoad: requireAuth,
  component: MentorRouteComponent,
});

const analysesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/analyses',
  validateSearch: (search: Record<string, unknown>) => ({
    templateId:
      typeof search.templateId === 'string' && Number.isFinite(Number(search.templateId))
        ? Number(search.templateId)
        : undefined,
  }),
  beforeLoad: ({ params, search }) => {
    requireAuth();

    if (search.templateId) {
      throw redirect({
        to: workspacePaths.templateReports(params.companyId, search.templateId),
      });
    }
  },
  component: AnalysesRouteComponent,
});

const templateReportsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/reports/$templateId',
  beforeLoad: requireAuth,
  component: TemplateReportsRouteComponent,
});

const analysisDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/analysis/$analysisId',
  beforeLoad: requireAuth,
  component: AnalysisDetailRouteComponent,
});

const templatesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/templates',
  beforeLoad: requireAuth,
  component: TemplatesRouteComponent,
});

const templateDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/templates/$templateId',
  beforeLoad: requireAuth,
  component: TemplateDetailRouteComponent,
});

const employeesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/employees',
  beforeLoad: requireAuth,
  component: EmployeesRouteComponent,
});

const settingsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/settings',
  beforeLoad: requireAuth,
  component: SettingsRouteComponent,
});

const integrationsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/companies/$companyId/integrations',
  beforeLoad: requireAuth,
  component: IntegrationsRouteComponent,
});

function UploadsRouteComponent() {
  const { companyId } = uploadsRoute.useParams();
  return <UploadsPage companyId={Number(companyId)} />;
}

function FavoritesRouteComponent() {
  const { companyId } = favoritesRoute.useParams();
  return <FavoritesPage companyId={Number(companyId)} />;
}

function TranscriptionsRouteComponent() {
  const { companyId } = transcriptionsRoute.useParams();
  return <TranscriptionsPage companyId={Number(companyId)} />;
}

function MentorRouteComponent() {
  const { companyId } = mentorRoute.useParams();
  return <MentorPage companyId={Number(companyId)} />;
}

function AnalysesRouteComponent() {
  const { companyId } = analysesRoute.useParams();
  return <AnalysesPage companyId={Number(companyId)} />;
}

function TemplateReportsRouteComponent() {
  const { companyId, templateId } = templateReportsRoute.useParams();
  return <AnalysesPage companyId={Number(companyId)} templateId={Number(templateId)} />;
}

function AnalysisDetailRouteComponent() {
  const { analysisId } = analysisDetailRoute.useParams();
  return <AnalysisDetailPage analysisId={Number(analysisId)} />;
}

function TemplatesRouteComponent() {
  const { companyId } = templatesRoute.useParams();
  return <TemplatesPage companyId={Number(companyId)} />;
}

function TemplateDetailRouteComponent() {
  const { companyId, templateId } = templateDetailRoute.useParams();
  return <TemplateDetailPage companyId={Number(companyId)} templateId={Number(templateId)} />;
}

function EmployeesRouteComponent() {
  const { companyId } = employeesRoute.useParams();
  return <EmployeesPage companyId={Number(companyId)} />;
}

function SettingsRouteComponent() {
  const { companyId } = settingsRoute.useParams();
  return <SettingsPage companyId={Number(companyId)} />;
}

function IntegrationsRouteComponent() {
  const { companyId } = integrationsRoute.useParams();
  return <IntegrationsPage companyId={Number(companyId)} />;
}

const routeTree = rootRoute.addChildren([
  dashboardRoute,
  loginRoute,
  registerRoute,
  uploadsRoute,
  favoritesRoute,
  favouritesRoute,
  transcriptionsRoute,
  mentorRoute,
  analysesRoute,
  templateReportsRoute,
  analysisDetailRoute,
  templatesRoute,
  templateDetailRoute,
  employeesRoute,
  integrationsRoute,
  settingsRoute,
]);

export const router = createRouter({
  routeTree,
  context: {
    queryClient,
  },
  defaultPreload: 'intent',
});

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
