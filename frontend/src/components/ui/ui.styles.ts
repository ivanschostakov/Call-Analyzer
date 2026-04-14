import type { CSSProperties } from 'react';

import type { ThemeTokens } from '../../theme/theme';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';
type BadgeTone = 'default' | 'success' | 'warning' | 'danger' | 'info';

function getFieldStyle(tokens: ThemeTokens, focused: boolean): CSSProperties {
  return {
    width: '100%',
    border: 'none',
    outline: 'none',
    borderRadius: 14,
    background: focused ? tokens.surfaceStrong : tokens.surfaceMuted,
    color: tokens.text,
    fontSize: 14,
    fontFamily: tokens.fontUi,
    transition: 'background-color 160ms ease',
    boxSizing: 'border-box',
  };
}

export function getButtonStyle(
  tokens: ThemeTokens,
  variant: ButtonVariant,
  size: ButtonSize,
  disabled = false,
): CSSProperties {
  const variantStyles: Record<ButtonVariant, CSSProperties> = {
    primary: {
      background: tokens.accent,
      color: tokens.accentContrast,
    },
    secondary: {
      background: tokens.surfaceStrong,
      color: tokens.text,
    },
    ghost: {
      background: 'transparent',
      color: tokens.textMuted,
    },
    danger: {
      background: tokens.dangerSoft,
      color: tokens.danger,
    },
  };

  const sizeStyles: Record<ButtonSize, CSSProperties> = {
    sm: {
      minHeight: 36,
      padding: '0 12px',
      fontSize: 13,
    },
    md: {
      minHeight: 42,
      padding: '0 16px',
      fontSize: 14,
    },
    lg: {
      minHeight: 48,
      padding: '0 18px',
      fontSize: 15,
    },
  };

  return {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    border: 'none',
    borderRadius: 14,
    fontFamily: tokens.fontUi,
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.45 : 1,
    transition: 'background-color 160ms ease, color 160ms ease, opacity 160ms ease',
    ...sizeStyles[size],
    ...variantStyles[variant],
  };
}

export function getCardStyle(tokens: ThemeTokens): CSSProperties {
  return {
    background: tokens.surface,
    borderRadius: 24,
    padding: 24,
  };
}

export function getInputStyle(tokens: ThemeTokens, focused: boolean): CSSProperties {
  return {
    ...getFieldStyle(tokens, focused),
    minHeight: 48,
    padding: '0 14px',
  };
}

export function getTextareaStyle(tokens: ThemeTokens, focused: boolean): CSSProperties {
  return {
    ...getFieldStyle(tokens, focused),
    minHeight: 120,
    padding: '14px',
    resize: 'vertical',
    lineHeight: 1.6,
  };
}

export function getSelectStyle(tokens: ThemeTokens, focused: boolean): CSSProperties {
  return {
    ...getFieldStyle(tokens, focused),
    minHeight: 48,
    padding: '0 14px',
    appearance: 'none',
    colorScheme: tokens.mode,
  };
}

export function getBadgeStyle(tokens: ThemeTokens, tone: BadgeTone): CSSProperties {
  const toneStyles: Record<BadgeTone, CSSProperties> = {
    default: {
      background: tokens.surfaceStrong,
      color: tokens.textMuted,
    },
    success: {
      background: tokens.successSoft,
      color: tokens.success,
    },
    warning: {
      background: tokens.warningSoft,
      color: tokens.warning,
    },
    danger: {
      background: tokens.dangerSoft,
      color: tokens.danger,
    },
    info: {
      background: tokens.accentSoft,
      color: tokens.accent,
    },
  };

  return {
    display: 'inline-flex',
    alignItems: 'center',
    borderRadius: 999,
    padding: '6px 10px',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    ...toneStyles[tone],
  };
}

export function getLabelStyle(tokens: ThemeTokens): CSSProperties {
  return {
    display: 'block',
    marginBottom: 8,
    color: tokens.textMuted,
    fontSize: 14,
    fontWeight: 600,
  };
}

export function getSkeletonStyle(tokens: ThemeTokens): CSSProperties {
  return {
    background: tokens.surfaceStrong,
    borderRadius: 18,
  };
}
