import type { ReactNode } from 'react';

import { useTheme } from '../../theme/theme';
import { getEmptyStateStyles } from './dashboard.styles';

export function EmptyStatePanel({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  const { tokens } = useTheme();
  const styles = getEmptyStateStyles(tokens);

  return (
    <div style={styles.root}>
      <div style={{ maxWidth: 640 }}>
        <p style={styles.title}>{title}</p>
        <p style={styles.description}>{description}</p>
        {action ? <div style={{ marginTop: 20 }}>{action}</div> : null}
      </div>
    </div>
  );
}
