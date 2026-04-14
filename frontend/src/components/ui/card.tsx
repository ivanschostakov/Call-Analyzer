import type { HTMLAttributes } from 'react';

import { useTheme } from '../../theme/theme';
import { getCardStyle } from './ui.styles';

export function Card({ style, ...props }: HTMLAttributes<HTMLDivElement>) {
  const { tokens } = useTheme();

  return <div style={{ ...getCardStyle(tokens), ...style }} {...props} />;
}
