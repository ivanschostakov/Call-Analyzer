import type { CSSProperties } from 'react';

import type { ThemeTokens } from '../../theme/theme';

type Accent = 'default' | 'info' | 'warning' | 'success' | 'danger';

export function getAppShellStyles(tokens: ThemeTokens) {
  return {
    root: {
      minHeight: '100vh',
      background: tokens.background,
      color: tokens.text,
    } satisfies CSSProperties,
    container: {
      width: 'min(1180px, calc(100vw - 32px))',
      margin: '0 auto',
      padding: '24px 0 32px',
    } satisfies CSSProperties,
    header: {
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
      marginBottom: 24,
      padding: 20,
      borderRadius: 24,
      background: tokens.surfaceMuted,
    } satisfies CSSProperties,
    headerTop: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 16,
    } satisfies CSSProperties,
    brandBlock: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
    } satisfies CSSProperties,
    brandMark: {
      width: 40,
      height: 40,
      display: 'grid',
      placeItems: 'center',
      borderRadius: 14,
      background: tokens.surfaceStrong,
      color: tokens.accent,
    } satisfies CSSProperties,
    brandTitle: {
      margin: 0,
      fontSize: 16,
      fontWeight: 700,
    } satisfies CSSProperties,
    brandText: {
      margin: '2px 0 0',
      fontSize: 13,
      color: tokens.textSubtle,
    } satisfies CSSProperties,
    nav: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 8,
    } satisfies CSSProperties,
    navItem: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '8px 12px',
      borderRadius: 12,
      fontSize: 13,
      color: tokens.textMuted,
      background: 'transparent',
    } satisfies CSSProperties,
    navItemActive: {
      background: tokens.accentSoft,
      color: tokens.accent,
    } satisfies CSSProperties,
    navSoon: {
      fontSize: 11,
      color: tokens.textSubtle,
    } satisfies CSSProperties,
    children: {
      display: 'block',
    } satisfies CSSProperties,
  };
}

export function getCompanySwitcherStyles(tokens: ThemeTokens) {
  return {
    wrapper: {
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      padding: 14,
      borderRadius: 18,
      background: tokens.surfaceMuted,
      minWidth: 220,
    } satisfies CSSProperties,
    label: {
      fontSize: 11,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color: tokens.textSubtle,
    } satisfies CSSProperties,
    select: {
      border: 'none',
      outline: 'none',
      background: 'transparent',
      color: tokens.text,
      fontSize: 14,
      fontWeight: 600,
      fontFamily: tokens.fontUi,
      appearance: 'none',
    } satisfies CSSProperties,
  };
}

export function getStatCardStyles(tokens: ThemeTokens, accent: Accent) {
  const accentStyles: Record<Accent, CSSProperties> = {
    default: {
      color: tokens.text,
      background: tokens.surface,
    },
    info: {
      color: tokens.accent,
      background: tokens.accentSoft,
    },
    warning: {
      color: tokens.warning,
      background: tokens.warningSoft,
    },
    success: {
      color: tokens.success,
      background: tokens.successSoft,
    },
    danger: {
      color: tokens.danger,
      background: tokens.dangerSoft,
    },
  };

  return {
    root: {
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      padding: 20,
      borderRadius: 22,
      background: tokens.surface,
      minHeight: 148,
    } satisfies CSSProperties,
    topRow: {
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: 16,
    } satisfies CSSProperties,
    copy: {
      display: 'flex',
      flexDirection: 'column',
      minWidth: 0,
      flex: 1,
    } satisfies CSSProperties,
    label: {
      margin: 0,
      fontSize: 12,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color: tokens.textSubtle,
      lineHeight: 1.35,
    } satisfies CSSProperties,
    value: {
      margin: 0,
      fontSize: 32,
      fontWeight: 700,
      fontFamily: tokens.fontMono,
      fontVariantNumeric: 'tabular-nums',
      lineHeight: 1,
      color: tokens.text,
    } satisfies CSSProperties,
    iconWrap: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      color: accentStyles[accent].color,
      marginTop: 2,
    } satisfies CSSProperties,
  };
}

export function getSectionCardStyles(tokens: ThemeTokens) {
  return {
    root: {
      height: '100%',
      padding: 24,
      borderRadius: 24,
      background: tokens.surface,
    } satisfies CSSProperties,
    header: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: 16,
      marginBottom: 18,
    } satisfies CSSProperties,
    title: {
      margin: 0,
      fontSize: 20,
      fontWeight: 700,
    } satisfies CSSProperties,
    description: {
      margin: '6px 0 0',
      fontSize: 14,
      lineHeight: 1.6,
      color: tokens.textMuted,
    } satisfies CSSProperties,
  };
}

export function getEmptyStateStyles(tokens: ThemeTokens) {
  return {
    root: {
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
      padding: 28,
      borderRadius: 28,
      background: tokens.surface,
      maxWidth: 760,
    } satisfies CSSProperties,
    title: {
      margin: 0,
      fontSize: 24,
      fontWeight: 700,
    } satisfies CSSProperties,
    description: {
      margin: 0,
      fontSize: 15,
      lineHeight: 1.7,
      color: tokens.textMuted,
    } satisfies CSSProperties,
  };
}
