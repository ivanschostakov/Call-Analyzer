import type { CSSProperties } from 'react';

import { getPercentageTone } from '../../lib/utils';
import { useTheme } from '../../theme/theme';

type MetricAnswerSize = 'table' | 'detail';

type PercentageAnswerProps = {
  value: number;
  size?: MetricAnswerSize;
};

type BooleanAnswerProps = {
  value: boolean;
  size?: 'table' | 'detail';
};

function getMetricSizeStyles(size: MetricAnswerSize): CSSProperties {
  const sizeStyles: Record<MetricAnswerSize, CSSProperties> = {
    table: {
      minWidth: 94,
      padding: '10px 12px',
      borderRadius: 16,
    },
    detail: {
      minWidth: 112,
      padding: '14px 16px',
      borderRadius: 18,
    },
  };

  return sizeStyles[size];
}

function getMetricValueStyles(size: MetricAnswerSize): CSSProperties {
  const valueStyles: Record<MetricAnswerSize, CSSProperties> = {
    table: {
      fontSize: 24,
    },
    detail: {
      fontSize: 32,
    },
  };

  return valueStyles[size];
}

function MetricAnswer({
  children,
  size,
  toneStyle,
}: {
  children: string;
  size: MetricAnswerSize;
  toneStyle: CSSProperties;
}) {
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 800,
        lineHeight: 1,
        fontVariantNumeric: 'tabular-nums',
        whiteSpace: 'nowrap',
        ...getMetricSizeStyles(size),
        ...toneStyle,
      }}
    >
      <span style={getMetricValueStyles(size)}>{children}</span>
    </div>
  );
}

export function PercentageAnswer({ value, size = 'detail' }: PercentageAnswerProps) {
  const { tokens } = useTheme();
  const tone = getPercentageTone(value);

  const toneStyles: Record<ReturnType<typeof getPercentageTone>, CSSProperties> = {
    danger: {
      background: 'linear-gradient(135deg, rgba(191, 95, 120, 0.22), rgba(191, 95, 120, 0.12))',
      color: tokens.danger,
      boxShadow: 'inset 0 0 0 1px rgba(191, 95, 120, 0.2)',
    },
    warning: {
      background: 'linear-gradient(135deg, rgba(188, 141, 22, 0.24), rgba(188, 141, 22, 0.12))',
      color: tokens.warning,
      boxShadow: 'inset 0 0 0 1px rgba(188, 141, 22, 0.22)',
    },
    success: {
      background: 'linear-gradient(135deg, rgba(47, 143, 104, 0.22), rgba(47, 143, 104, 0.12))',
      color: tokens.success,
      boxShadow: 'inset 0 0 0 1px rgba(47, 143, 104, 0.2)',
    },
    perfect: {
      background: 'linear-gradient(135deg, #0a6a4d, #0e7f5d)',
      color: '#f7fffb',
      boxShadow: 'inset 0 0 0 1px rgba(255, 255, 255, 0.12)',
    },
  };

  return (
    <MetricAnswer size={size} toneStyle={toneStyles[tone]}>
      {`${value}%`}
    </MetricAnswer>
  );
}

export function BooleanAnswer({ value, size = 'detail' }: BooleanAnswerProps) {
  const { tokens } = useTheme();

  const toneStyle = value
    ? {
        background: 'linear-gradient(135deg, rgba(47, 143, 104, 0.22), rgba(47, 143, 104, 0.12))',
        color: tokens.success,
        boxShadow: 'inset 0 0 0 1px rgba(47, 143, 104, 0.2)',
      }
    : {
        background: 'linear-gradient(135deg, rgba(191, 95, 120, 0.22), rgba(191, 95, 120, 0.12))',
        color: tokens.danger,
        boxShadow: 'inset 0 0 0 1px rgba(191, 95, 120, 0.2)',
      };

  return <MetricAnswer size={size} toneStyle={toneStyle}>{value ? 'Да' : 'Нет'}</MetricAnswer>;
}
