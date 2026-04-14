import type { CSSProperties } from 'react';

import type { ThemeTokens } from '../theme/theme';

export function getDashboardPageStyles(tokens: ThemeTokens) {
  return {
    page: {
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
    } satisfies CSSProperties,
    loadingStack: {
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
    } satisfies CSSProperties,
    hero: {
      padding: 28,
      borderRadius: 28,
      background: tokens.surface,
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
    } satisfies CSSProperties,
    heroTop: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      gap: 20,
    } satisfies CSSProperties,
    heroCopy: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      maxWidth: 760,
    } satisfies CSSProperties,
    heroTitle: {
      margin: 0,
      fontSize: 'clamp(28px, 4vw, 42px)',
      fontWeight: 700,
      lineHeight: 1.1,
    } satisfies CSSProperties,
    heroDescription: {
      margin: 0,
      fontSize: 15,
      lineHeight: 1.7,
      color: tokens.textMuted,
    } satisfies CSSProperties,
    heroControls: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 12,
      alignItems: 'stretch',
      justifyContent: 'flex-end',
    } satisfies CSSProperties,
    userBlock: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      padding: 14,
      borderRadius: 18,
      background: tokens.surfaceMuted,
      minWidth: 220,
    } satisfies CSSProperties,
    userName: {
      margin: 0,
      fontSize: 14,
      fontWeight: 700,
    } satisfies CSSProperties,
    userActions: {
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      gap: 8,
    } satisfies CSSProperties,
    quickActions: {
      padding: 24,
      borderRadius: 24,
      background: tokens.surface,
      display: 'flex',
      flexDirection: 'column',
      gap: 18,
    } satisfies CSSProperties,
    quickActionsHeader: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 12,
      alignItems: 'baseline',
      justifyContent: 'space-between',
    } satisfies CSSProperties,
    sectionHeading: {
      margin: 0,
      fontSize: 20,
      fontWeight: 700,
    } satisfies CSSProperties,
    quickActionsBody: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: 10,
    } satisfies CSSProperties,
    grid: {
      display: 'grid',
      gap: 20,
      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
      alignItems: 'stretch',
    } satisfies CSSProperties,
    list: {
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    } satisfies CSSProperties,
    listItem: {
      display: 'flex',
      justifyContent: 'space-between',
      gap: 16,
      padding: 16,
      borderRadius: 18,
      background: tokens.surfaceMuted,
      alignItems: 'flex-start',
    } satisfies CSSProperties,
    listItemBody: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      minWidth: 0,
    } satisfies CSSProperties,
    listItemTitle: {
      margin: 0,
      fontSize: 15,
      fontWeight: 700,
    } satisfies CSSProperties,
    listItemSummary: {
      margin: 0,
      fontSize: 14,
      lineHeight: 1.6,
      color: tokens.textMuted,
    } satisfies CSSProperties,
    listItemMeta: {
      margin: 0,
      fontSize: 12,
      color: tokens.textSubtle,
    } satisfies CSSProperties,
    analysisTemplateName: {
      margin: 0,
      fontSize: 12,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color: tokens.accent,
    } satisfies CSSProperties,
    templateAccent: {
      width: 36,
      height: 36,
      borderRadius: 12,
      background: tokens.accentSoft,
      color: tokens.accent,
      display: 'grid',
      placeItems: 'center',
      flexShrink: 0,
    } satisfies CSSProperties,
    textMuted: {
      margin: 0,
      fontSize: 14,
      lineHeight: 1.7,
      color: tokens.textMuted,
    } satisfies CSSProperties,
    error: {
      margin: 0,
      fontSize: 14,
      lineHeight: 1.6,
      color: tokens.danger,
    } satisfies CSSProperties,
  };
}
