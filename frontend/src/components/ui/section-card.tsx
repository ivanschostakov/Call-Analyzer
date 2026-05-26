import { useMemo, useState, type CSSProperties } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

import { useTheme } from '../../theme/theme';
import { Button } from './button';

type SectionCardProps = {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
  collapsible?: boolean;
  expanded?: boolean;
  defaultExpanded?: boolean;
  onExpandedChange?: (expanded: boolean) => void;
  style?: CSSProperties;
  bodyStyle?: CSSProperties;
};

export function SectionCard({
  title,
  description,
  actions,
  children,
  collapsible = false,
  expanded,
  defaultExpanded = true,
  onExpandedChange,
  style,
  bodyStyle,
}: SectionCardProps) {
  const { tokens } = useTheme();
  const [internalExpanded, setInternalExpanded] = useState(defaultExpanded);
  const isControlled = typeof expanded === 'boolean';
  const isExpanded = isControlled ? expanded : internalExpanded;

  const sectionStyle = useMemo<CSSProperties>(
    () => ({
      display: 'flex',
      flexDirection: 'column',
      gap: 14,
      padding: 18,
      borderRadius: 18,
      background: tokens.surface,
      border: `1px solid ${tokens.surfaceStrong}`,
      minWidth: 0,
      ...style,
    }),
    [style, tokens.surface, tokens.surfaceStrong],
  );

  function toggleExpanded() {
    const next = !isExpanded;
    if (!isControlled) {
      setInternalExpanded(next);
    }
    onExpandedChange?.(next);
  }

  return (
    <section style={sectionStyle}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
          minWidth: 0,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 0, flex: '1 1 320px' }}>
          <h2
            style={{
              margin: 0,
              fontSize: 18,
              lineHeight: 1.25,
              color: tokens.text,
            }}
          >
            {title}
          </h2>
          {description ? (
            <p
              style={{
                margin: 0,
                fontSize: 13,
                lineHeight: 1.55,
                color: tokens.textMuted,
              }}
            >
              {description}
            </p>
          ) : null}
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            flexWrap: 'wrap',
            marginLeft: 'auto',
          }}
        >
          {actions}
          {collapsible ? (
            <Button variant="ghost" size="sm" onClick={toggleExpanded} aria-expanded={isExpanded}>
              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              {isExpanded ? 'Свернуть' : 'Развернуть'}
            </Button>
          ) : null}
        </div>
      </div>

      {!collapsible || isExpanded ? <div style={{ minWidth: 0, ...bodyStyle }}>{children}</div> : null}
    </section>
  );
}
