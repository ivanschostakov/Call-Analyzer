import type { ReactNode } from 'react';

import { ChevronRight } from 'lucide-react';

import { useTheme } from '../../theme/theme';
import { getSectionCardStyles } from './dashboard.styles';
import { Button } from '../ui/button';

export function SectionCard({
  id,
  title,
  description,
  actionLabel,
  actionDisabled = false,
  onAction,
  children,
}: {
  id?: string;
  title: string;
  description?: string;
  actionLabel?: string;
  actionDisabled?: boolean;
  onAction?: () => void;
  children: ReactNode;
}) {
  const { tokens } = useTheme();
  const styles = getSectionCardStyles(tokens);

  return (
    <div id={id} style={styles.root}>
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>{title}</h2>
          {description ? <p style={styles.description}>{description}</p> : null}
        </div>
        {actionLabel ? (
          <Button variant="ghost" size="sm" onClick={onAction} disabled={actionDisabled}>
            {actionLabel}
            <ChevronRight size={16} />
          </Button>
        ) : null}
      </div>
      {children}
    </div>
  );
}
