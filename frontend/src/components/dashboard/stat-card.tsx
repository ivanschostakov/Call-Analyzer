import type { ReactNode } from 'react';

import { useTheme } from '../../theme/theme';
import { getStatCardStyles } from './dashboard.styles';

export function StatCard({
  label,
  value,
  icon,
  accent = 'default',
}: {
  label: string;
  value: number;
  icon: ReactNode;
  accent?: 'default' | 'info' | 'warning' | 'success' | 'danger';
}) {
  const { tokens } = useTheme();
  const styles = getStatCardStyles(tokens, accent);

  return (
    <div style={styles.root}>
      <div style={styles.topRow}>
        <div style={styles.copy}>
          <p style={styles.label}>{label}</p>
        </div>
        <div style={styles.iconWrap}>{icon}</div>
      </div>
      <p style={styles.value}>{value}</p>
    </div>
  );
}
