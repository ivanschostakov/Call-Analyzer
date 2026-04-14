import '@fontsource/manrope';
import '@fontsource/jetbrains-mono';
import './styles.css';

import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';

import { queryClient } from './app/query-client';
import { AuthProvider } from './auth/context';
import { router } from './router';
import { ThemeProvider } from './theme/theme';
import { WorkspaceProvider } from './workspace/workspace-context';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <WorkspaceProvider>
            <RouterProvider router={router} />
          </WorkspaceProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
