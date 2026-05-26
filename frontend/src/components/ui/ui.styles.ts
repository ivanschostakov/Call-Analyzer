import type { CSSProperties } from 'react';

import type { ThemeTokens } from '../../theme/theme';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md' | 'lg';
type BadgeTone = 'default' | 'success' | 'warning' | 'danger' | 'info';

function getFieldStyle(tokens: ThemeTokens, focused: boolean): CSSProperties {
  return {
    width: '100%',
    border: `1px solid ${focused ? tokens.accent : tokens.surfaceStrong}`,
    outline: 'none',
    borderRadius: 10,
    background: tokens.surface,
    color: tokens.text,
    fontSize: 14,
    fontFamily: tokens.fontUi,
    transition: 'border-color 160ms ease, box-shadow 160ms ease',
    boxShadow: focused ? `0 0 0 2px ${tokens.accentSoft}` : 'none',
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
      boxShadow: '0 2px 8px rgba(22, 119, 255, 0.18)',
    },
    secondary: {
      background: tokens.surfaceMuted,
      color: tokens.textMuted,
      border: `1px solid ${tokens.surfaceStrong}`,
    },
    ghost: {
      background: 'transparent',
      color: tokens.textMuted,
      border: `1px solid ${tokens.surfaceStrong}`,
    },
    danger: {
      background: tokens.dangerSoft,
      color: tokens.danger,
      border: '1px solid transparent',
    },
  };

  const sizeStyles: Record<ButtonSize, CSSProperties> = {
    sm: {
      minHeight: 34,
      padding: '0 12px',
      fontSize: 12,
    },
    md: {
      minHeight: 40,
      padding: '0 16px',
      fontSize: 14,
    },
    lg: {
      minHeight: 44,
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
    borderRadius: 10,
    fontFamily: tokens.fontUi,
    fontWeight: 700,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.45 : 1,
    transition: 'background-color 160ms ease, color 160ms ease, opacity 160ms ease, transform 120ms ease',
    ...sizeStyles[size],
    ...variantStyles[variant],
  };
}

export function getCardStyle(tokens: ThemeTokens): CSSProperties {
  return {
    background: tokens.surface,
    borderRadius: 16,
    padding: 24,
    border: `1px solid ${tokens.surfaceStrong}`,
  };
}

export function getInputStyle(tokens: ThemeTokens, focused: boolean): CSSProperties {
  return {
    ...getFieldStyle(tokens, focused),
    minHeight: 40,
    padding: '0 12px',
  };
}

export function getTextareaStyle(tokens: ThemeTokens, focused: boolean): CSSProperties {
  return {
    ...getFieldStyle(tokens, focused),
    minHeight: 110,
    padding: '12px',
    resize: 'vertical',
    lineHeight: 1.6,
  };
}

export function getSelectStyle(tokens: ThemeTokens, focused: boolean): CSSProperties {
  return {
    ...getFieldStyle(tokens, focused),
    minHeight: 40,
    padding: '0 12px',
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
    padding: '5px 10px',
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
    marginBottom: 6,
    color: tokens.textMuted,
    fontSize: 13,
    fontWeight: 600,
  };
}

export function getSkeletonStyle(tokens: ThemeTokens): CSSProperties {
  return {
    background: tokens.surfaceStrong,
    borderRadius: 18,
  };
}
