import type { HTMLAttributes } from 'react';

import { useTheme } from '../../theme/theme';
import { getBadgeStyle } from './ui.styles';

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'info';
};

export function Badge({ tone = 'default', style, ...props }: BadgeProps) {
  const { tokens } = useTheme();

  return <span style={{ ...getBadgeStyle(tokens, tone), ...style }} {...props} />;
}
