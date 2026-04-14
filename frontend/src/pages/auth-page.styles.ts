import type { CSSProperties } from 'react';

import type { ThemeTokens } from '../theme/theme';

export function getAuthPageStyles(
  tokens: ThemeTokens,
  options?: {
    compact?: boolean;
    mobile?: boolean;
  },
) {
  const compact = options?.compact ?? false;
  const mobile = options?.mobile ?? false;

  return {
    shell: {
      minHeight: '100vh',
      padding: mobile ? '16px 0' : compact ? '24px 0' : '32px 0',
      background: tokens.background,
      color: tokens.text,
    } satisfies CSSProperties,
    container: {
      width: mobile ? 'min(1080px, calc(100vw - 24px))' : 'min(1080px, calc(100vw - 32px))',
      margin: '0 auto',
      display: 'grid',
      gap: compact ? 16 : 20,
      alignItems: 'stretch',
      gridTemplateColumns: compact ? '1fr' : 'repeat(auto-fit, minmax(320px, 1fr))',
    } satisfies CSSProperties,
    intro: {
      padding: mobile ? 20 : compact ? 24 : 32,
      borderRadius: mobile ? 22 : 28,
      background: tokens.surfaceMuted,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      gap: compact ? 16 : 20,
      minHeight: compact ? 0 : 420,
    } satisfies CSSProperties,
    introEyebrow: {
      margin: 0,
      fontSize: 12,
      letterSpacing: '0.18em',
      textTransform: 'uppercase',
      color: tokens.textSubtle,
    } satisfies CSSProperties,
    introTitle: {
      margin: 0,
      fontSize: mobile ? 'clamp(28px, 10vw, 38px)' : 'clamp(32px, 5vw, 52px)',
      lineHeight: 1.05,
      fontWeight: 700,
    } satisfies CSSProperties,
    introBody: {
      margin: 0,
      maxWidth: compact ? '100%' : 520,
      fontSize: 16,
      lineHeight: 1.8,
      color: tokens.textMuted,
    } satisfies CSSProperties,
    formCard: {
      padding: mobile ? 20 : compact ? 24 : 32,
      borderRadius: mobile ? 22 : 28,
      background: tokens.surface,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      minWidth: 0,
    } satisfies CSSProperties,
    formEyebrow: {
      margin: 0,
      fontSize: 12,
      letterSpacing: '0.14em',
      textTransform: 'uppercase',
      color: tokens.textSubtle,
    } satisfies CSSProperties,
    formTitle: {
      margin: '16px 0 0',
      fontSize: mobile ? 28 : 32,
      lineHeight: 1.15,
      fontWeight: 700,
    } satisfies CSSProperties,
    formDescription: {
      margin: '10px 0 0',
      fontSize: 14,
      lineHeight: 1.7,
      color: tokens.textMuted,
    } satisfies CSSProperties,
    form: {
      display: 'flex',
      flexDirection: 'column',
      gap: 18,
      marginTop: 28,
    } satisfies CSSProperties,
    row: {
      display: 'grid',
      gap: 16,
      gridTemplateColumns: mobile ? '1fr' : 'repeat(auto-fit, minmax(160px, 1fr))',
    } satisfies CSSProperties,
    footer: {
      marginTop: 20,
      fontSize: 14,
      lineHeight: 1.6,
      color: tokens.textMuted,
    } satisfies CSSProperties,
    link: {
      color: tokens.accent,
      textDecoration: 'none',
      fontWeight: 700,
    } satisfies CSSProperties,
    error: {
      margin: 0,
      fontSize: 13,
      lineHeight: 1.5,
      color: tokens.danger,
    } satisfies CSSProperties,
  };
}
