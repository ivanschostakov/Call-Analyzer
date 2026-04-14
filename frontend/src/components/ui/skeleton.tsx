import type { HTMLAttributes } from 'react';

import { useTheme } from '../../theme/theme';
import { getSkeletonStyle } from './ui.styles';

export function Skeleton({ style, ...props }: HTMLAttributes<HTMLDivElement>) {
  const { tokens } = useTheme();

  return <div className="app-skeleton" style={{ ...getSkeletonStyle(tokens), ...style }} {...props} />;
}
