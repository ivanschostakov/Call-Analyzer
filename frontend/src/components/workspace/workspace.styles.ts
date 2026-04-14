import type { CSSProperties } from 'react';

import type { ThemeTokens } from '../../theme/theme';

export const WORKSPACE_TOPBAR_CONTROL_WIDTH = 240;

export function getWorkspaceShellStyles(
  tokens: ThemeTokens,
  options?: {
    wideContent?: boolean;
    compactTopbar?: boolean;
    compactNav?: boolean;
    isMobile?: boolean;
  },
) {
  const compactTopbar = options?.compactTopbar ?? false;
  const wideContent = options?.wideContent ?? false;
  const compactNav = options?.compactNav ?? false;
  const isMobile = options?.isMobile ?? false;
  const shellPadding = compactNav ? (isMobile ? 12 : 16) : 20;
  const shellRadius = isMobile ? 20 : 28;

  return {
    root: {
      minHeight: '100vh',
      background: tokens.background,
      color: tokens.text,
      display: 'flex',
      flexDirection: compactNav ? 'column' : 'row',
      gap: compactNav ? 12 : 24,
      padding: shellPadding,
      boxSizing: 'border-box',
    } satisfies CSSProperties,
    compactBar: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      padding: isMobile ? '12px 14px' : '14px 16px',
      borderRadius: shellRadius,
      background: tokens.surface,
      position: 'sticky',
      top: shellPadding,
      zIndex: 20,
    } satisfies CSSProperties,
    compactBarBrand: {
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      minWidth: 0,
    } satisfies CSSProperties,
    compactBarTitle: {
      margin: 0,
      fontSize: 16,
      fontWeight: 700,
      lineHeight: 1.2,
    } satisfies CSSProperties,
    compactBarMeta: {
      margin: 0,
      fontSize: 12,
      lineHeight: 1.4,
      color: tokens.textSubtle,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    } satisfies CSSProperties,
    compactBarButton: {
      width: 42,
      height: 42,
      border: 'none',
      borderRadius: 14,
      background: tokens.surfaceMuted,
      color: tokens.text,
      display: 'grid',
      placeItems: 'center',
      flexShrink: 0,
      cursor: 'pointer',
    } satisfies CSSProperties,
    sidebarDesktop: {
      width: 236,
      flexShrink: 0,
      minWidth: 0,
    } satisfies CSSProperties,
    drawerBackdrop: {
      position: 'fixed',
      inset: 0,
      background: tokens.mode === 'dark' ? 'rgba(9, 11, 14, 0.62)' : 'rgba(20, 24, 32, 0.18)',
      zIndex: 39,
    } satisfies CSSProperties,
    drawerShell: {
      position: 'fixed',
      inset: 0,
      zIndex: 40,
      display: 'flex',
      alignItems: 'stretch',
      padding: isMobile ? 12 : 16,
      pointerEvents: 'none',
    } satisfies CSSProperties,
    drawerPanel: {
      width: 'min(320px, calc(100vw - 24px))',
      maxWidth: '100%',
      height: '100%',
      maxHeight: '100%',
      pointerEvents: 'auto',
    } satisfies CSSProperties,
    sidebarCard: {
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: 24,
      padding: isMobile ? 18 : 20,
      borderRadius: shellRadius,
      background: tokens.surface,
      boxSizing: 'border-box',
      overflowY: 'auto',
      minWidth: 0,
      ...(compactNav
        ? {}
        : {
            position: 'sticky',
            top: 20,
          }),
    } satisfies CSSProperties,
    brand: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      minWidth: 0,
    } satisfies CSSProperties,
    brandName: {
      margin: 0,
      fontSize: 18,
      fontWeight: 700,
    } satisfies CSSProperties,
    brandMeta: {
      margin: 0,
      fontSize: 13,
      color: tokens.textSubtle,
      lineHeight: 1.45,
    } satisfies CSSProperties,
    nav: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
    } satisfies CSSProperties,
    navLabel: {
      margin: '0 0 8px',
      fontSize: 11,
      letterSpacing: '0.14em',
      textTransform: 'uppercase',
      color: tokens.textSubtle,
    } satisfies CSSProperties,
    navLink: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: compactNav ? '12px 13px' : '11px 12px',
      borderRadius: 14,
      color: tokens.textMuted,
      textDecoration: 'none',
      fontSize: 14,
      fontWeight: 600,
    } satisfies CSSProperties,
    navLinkActive: {
      background: tokens.surfaceMuted,
      color: tokens.text,
    } satisfies CSSProperties,
    navLinkIcon: {
      flexShrink: 0,
    } satisfies CSSProperties,
    spacer: {
      flex: 1,
    } satisfies CSSProperties,
    userCard: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      paddingTop: 16,
      minWidth: 0,
    } satisfies CSSProperties,
    userIdentity: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      alignItems: 'flex-start',
      minWidth: 0,
    } satisfies CSSProperties,
    userActions: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 8,
      marginTop: 8,
      alignItems: 'stretch',
    } satisfies CSSProperties,
    userName: {
      margin: 0,
      fontSize: 14,
      fontWeight: 700,
      lineHeight: 1.35,
    } satisfies CSSProperties,
    userMeta: {
      margin: 0,
      fontSize: 13,
      lineHeight: 1.4,
      color: tokens.textSubtle,
      wordBreak: 'break-word',
    } satisfies CSSProperties,
    main: {
      flex: compactNav ? '1 1 auto' : '1 1 860px',
      minWidth: 0,
      width: compactNav ? '100%' : undefined,
    } satisfies CSSProperties,
    mainInner: {
      width: wideContent ? '100%' : 'min(1600px, 100%)',
      margin: '0 auto',
      display: 'flex',
      flexDirection: 'column',
      gap: compactTopbar ? 12 : compactNav ? 16 : 20,
      minWidth: 0,
    } satisfies CSSProperties,
    topbar: {
      display: 'flex',
      flexDirection: isMobile ? 'column' : 'row',
      flexWrap: 'wrap',
      alignItems: isMobile ? 'stretch' : 'flex-start',
      justifyContent: 'space-between',
      gap: compactTopbar ? 12 : 16,
      padding: compactTopbar ? '0 0 2px' : compactNav ? (isMobile ? 16 : 18) : 20,
      borderRadius: compactTopbar ? 0 : shellRadius,
      background: compactTopbar ? 'transparent' : tokens.surface,
      minWidth: 0,
    } satisfies CSSProperties,
    topbarTitleBlock: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      minWidth: 0,
      flex: '1 1 320px',
    } satisfies CSSProperties,
    pageTitle: {
      margin: 0,
      fontSize: compactTopbar ? 'clamp(22px, 2.2vw, 28px)' : 'clamp(24px, 3.2vw, 36px)',
      lineHeight: 1.05,
      fontWeight: 700,
    } satisfies CSSProperties,
    pageDescription: {
      margin: 0,
      fontSize: compactTopbar ? 13 : 14,
      lineHeight: 1.6,
      color: tokens.textMuted,
      maxWidth: compactNav ? '100%' : 680,
    } satisfies CSSProperties,
    topbarActions: {
      display: 'flex',
      flexDirection: isMobile ? 'column' : 'row',
      flexWrap: 'wrap',
      gap: compactTopbar ? 8 : 10,
      alignItems: isMobile ? 'stretch' : 'center',
      justifyContent: compactNav ? 'flex-start' : 'flex-end',
      width: isMobile ? '100%' : 'auto',
      minWidth: 0,
    } satisfies CSSProperties,
    companyPicker: {
      width: isMobile ? '100%' : WORKSPACE_TOPBAR_CONTROL_WIDTH,
      flex: isMobile ? '1 1 100%' : `0 0 ${WORKSPACE_TOPBAR_CONTROL_WIDTH}px`,
      maxWidth: '100%',
    } satisfies CSSProperties,
    companyMeta: {
      margin: 0,
      fontSize: compactTopbar ? 12 : 13,
      color: tokens.textSubtle,
      lineHeight: 1.45,
    } satisfies CSSProperties,
    content: {
      display: 'flex',
      flexDirection: 'column',
      gap: compactTopbar ? 14 : compactNav ? 16 : 20,
      minWidth: 0,
    } satisfies CSSProperties,
    loadingCard: {
      padding: isMobile ? 18 : 24,
      borderRadius: isMobile ? 20 : 24,
      background: tokens.surface,
      color: tokens.textMuted,
      fontSize: 14,
      lineHeight: 1.6,
    } satisfies CSSProperties,
  };
}
