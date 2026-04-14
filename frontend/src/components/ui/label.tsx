import type { LabelHTMLAttributes } from 'react';

import { useTheme } from '../../theme/theme';
import { getLabelStyle } from './ui.styles';

export function Label({ style, ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  const { tokens } = useTheme();

  return <label style={{ ...getLabelStyle(tokens), ...style }} {...props} />;
}
