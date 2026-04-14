import { createContext, useContext, useEffect, useMemo, useSyncExternalStore } from 'react';

import { queryClient } from '../app/query-client';
import { logoutAuthLogoutPost, useMeAuthMeGet } from '../api/generated/client';
import { authStore } from './store';
import type { AuthSession, AuthTokensWithUserResponse, CurrentUser } from './types';

type AuthContextValue = {
  session: AuthSession | null;
  user: CurrentUser | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  setSessionFromResponse: (response: AuthTokensWithUserResponse) => void;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function toSession(response: AuthTokensWithUserResponse): AuthSession {
  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    sessionId: response.session_id,
    tokenType: response.token_type ?? 'bearer',
    user: response.user,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const session = useSyncExternalStore(authStore.subscribe, authStore.getSnapshot, authStore.getSnapshot);
  const hasSession = Boolean(session?.accessToken && session.refreshToken && session.sessionId);

  const meQuery = useMeAuthMeGet({
    query: {
      enabled: hasSession,
      retry: false,
      refetchOnMount: 'always',
      staleTime: 0,
    },
  });

  useEffect(() => {
    if (meQuery.data) {
      authStore.setUser(meQuery.data);
    }
  }, [meQuery.data]);

  useEffect(() => {
    if (hasSession && meQuery.isError) {
      authStore.clear();
      queryClient.clear();
    }
  }, [hasSession, meQuery.isError]);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user: session?.user ?? null,
      isAuthenticated: hasSession,
      isBootstrapping: hasSession && meQuery.isPending,
      setSessionFromResponse(response) {
        authStore.setSession(toSession(response));
      },
      async logout() {
        const currentSession = authStore.getSnapshot();
        try {
          if (currentSession) {
            await logoutAuthLogoutPost({
              refresh_token: currentSession.refreshToken,
              session_id: currentSession.sessionId,
            });
          }
        } catch {
          // Best-effort logout.
        } finally {
          authStore.clear();
          queryClient.clear();
        }
      },
    }),
    [hasSession, meQuery.isPending, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return value;
}
