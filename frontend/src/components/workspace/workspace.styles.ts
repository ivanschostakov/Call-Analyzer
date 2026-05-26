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
  const shellPadding = compactNav ? (isMobile ? 10 : 14) : 14;
  const shellRadius = isMobile ? tokens.radiusMd : tokens.radiusLg;

  return {
    root: {
      minHeight: '100vh',
      background: tokens.background,
      color: tokens.text,
      display: 'flex',
      flexDirection: compactNav ? 'column' : 'row',
      gap: compactNav ? 12 : 14,
      padding: shellPadding,
      boxSizing: 'border-box',
    } satisfies CSSProperties,
    compactBar: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      padding: isMobile ? '10px 12px' : '12px 14px',
      borderRadius: shellRadius,
      background: tokens.surface,
      border: `1px solid ${tokens.surfaceStrong}`,
      boxShadow: tokens.shadowSm,
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
      fontSize: 15,
      fontWeight: 700,
      lineHeight: 1.2,
    } satisfies CSSProperties,
    compactBarMeta: {
      margin: 0,
      fontSize: 11,
      lineHeight: 1.4,
      color: tokens.textSubtle,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    } satisfies CSSProperties,
    compactBarButton: {
      width: 38,
      height: 38,
      border: `1px solid ${tokens.surfaceStrong}`,
      borderRadius: tokens.radiusSm,
      background: tokens.surface,
      color: tokens.text,
      display: 'grid',
      placeItems: 'center',
      flexShrink: 0,
      cursor: 'pointer',
    } satisfies CSSProperties,
    sidebarDesktop: {
      width: 260,
      flexShrink: 0,
      minWidth: 0,
    } satisfies CSSProperties,
    drawerBackdrop: {
      position: 'fixed',
      inset: 0,
      background: tokens.mode === 'dark' ? 'rgba(9, 11, 14, 0.62)' : 'rgba(20, 24, 32, 0.16)',
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
      gap: 14,
      padding: isMobile ? 14 : 18,
      borderRadius: shellRadius,
      background: tokens.surface,
      border: `1px solid ${tokens.surfaceStrong}`,
      boxShadow: tokens.shadowSm,
      boxSizing: 'border-box',
      overflowY: 'auto',
      minWidth: 0,
      ...(compactNav
        ? {}
        : {
            position: 'sticky',
            top: 12,
          }),
    } satisfies CSSProperties,
    brand: {
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
      minWidth: 0,
    } satisfies CSSProperties,
    brandName: {
      margin: 0,
      fontSize: 20,
      fontWeight: 700,
    } satisfies CSSProperties,
    brandMeta: {
      margin: 0,
      fontSize: 12,
      color: tokens.textSubtle,
      lineHeight: 1.4,
    } satisfies CSSProperties,
    nav: {
      display: 'flex',
      flexDirection: 'column',
      gap: 5,
    } satisfies CSSProperties,
    navLabel: {
      margin: '6px 0 10px',
      fontSize: 13,
      fontWeight: 700,
      color: tokens.textMuted,
    } satisfies CSSProperties,
    navLink: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: compactNav ? '10px 12px' : '10px 12px',
      borderRadius: tokens.radiusSm,
      color: tokens.textMuted,
      textDecoration: 'none',
      fontSize: 14,
      fontWeight: 600,
      border: `1px solid transparent`,
    } satisfies CSSProperties,
    navLinkActive: {
      background: tokens.accent,
      color: tokens.accentContrast,
      boxShadow: tokens.shadowSm,
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
      gap: 8,
      paddingTop: 14,
      borderTop: `1px solid ${tokens.surfaceStrong}`,
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
      marginTop: 4,
      alignItems: 'stretch',
    } satisfies CSSProperties,
    userName: {
      margin: 0,
      fontSize: 15,
      fontWeight: 700,
      lineHeight: 1.35,
    } satisfies CSSProperties,
    userMeta: {
      margin: 0,
      fontSize: 12,
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
      gap: compactTopbar ? 12 : compactNav ? 14 : 16,
      minWidth: 0,
    } satisfies CSSProperties,
    topbar: {
      display: 'flex',
      flexDirection: isMobile ? 'column' : 'row',
      flexWrap: 'wrap',
      alignItems: isMobile ? 'stretch' : 'flex-start',
      justifyContent: 'space-between',
      gap: compactTopbar ? 10 : 12,
      padding: compactTopbar ? '0 0 2px' : compactNav ? (isMobile ? 12 : 16) : 16,
      borderRadius: compactTopbar ? 0 : tokens.radiusLg,
      background: compactTopbar ? tokens.surface : tokens.surface,
      border: compactTopbar ? `1px solid ${tokens.surfaceStrong}` : `1px solid ${tokens.surfaceStrong}`,
      boxShadow: compactTopbar ? 'none' : tokens.shadowSm,
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
      fontSize: compactTopbar ? 'clamp(20px, 2vw, 24px)' : 'clamp(22px, 2.2vw, 27px)',
      lineHeight: 1.1,
      fontWeight: 700,
    } satisfies CSSProperties,
    pageDescription: {
      margin: 0,
      fontSize: compactTopbar ? 12 : 13,
      lineHeight: 1.5,
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
      fontSize: compactTopbar ? 11 : 12,
      color: tokens.textSubtle,
      lineHeight: 1.45,
    } satisfies CSSProperties,
    content: {
      display: 'flex',
      flexDirection: 'column',
      gap: compactTopbar ? 12 : compactNav ? 14 : 18,
      minWidth: 0,
    } satisfies CSSProperties,
    loadingCard: {
      padding: isMobile ? 18 : 24,
      borderRadius: isMobile ? tokens.radiusLg : 24,
      background: tokens.surface,
      border: `1px solid ${tokens.surfaceStrong}`,
      boxShadow: tokens.shadowSm,
      color: tokens.textMuted,
      fontSize: 14,
      lineHeight: 1.6,
    } satisfies CSSProperties,
  };
}
