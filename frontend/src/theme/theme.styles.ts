import type { CSSProperties } from 'react';

import type { ThemeTokens } from './theme';

export function getPageStyle(tokens: ThemeTokens): CSSProperties {
  return {
    minHeight: '100vh',
    background: tokens.background,
    color: tokens.text,
    fontFamily: tokens.fontUi,
  };
}

export function getContainerStyle(): CSSProperties {
  return {
    width: 'min(1180px, calc(100vw - 32px))',
    margin: '0 auto',
  };
}

export function getSurfaceStyle(
  tokens: ThemeTokens,
  options?: {
    background?: string;
    padding?: number | string;
    radius?: number;
  },
): CSSProperties {
  return {
    background: options?.background ?? tokens.surface,
    borderRadius: options?.radius ?? 24,
    padding: options?.padding ?? 24,
  };
}

export function getEyebrowStyle(tokens: ThemeTokens): CSSProperties {
  return {
    margin: 0,
    fontSize: 12,
    letterSpacing: '0.18em',
    textTransform: 'uppercase',
    color: tokens.textSubtle,
  };
}

export function getMonoStyle(tokens: ThemeTokens): CSSProperties {
  return {
    fontFamily: tokens.fontMono,
  };
}

export function getMutedTextStyle(tokens: ThemeTokens): CSSProperties {
  return {
    color: tokens.textMuted,
  };
}

export function getSubtleTextStyle(tokens: ThemeTokens): CSSProperties {
  return {
    color: tokens.textSubtle,
  };
}
