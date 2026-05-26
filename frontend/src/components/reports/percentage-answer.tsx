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
      minWidth: 98,
      padding: '9px 12px',
      borderRadius: 6,
    },
    detail: {
      minWidth: 118,
      padding: '12px 16px',
      borderRadius: 8,
    },
  };

  return sizeStyles[size];
}

function getMetricValueStyles(size: MetricAnswerSize): CSSProperties {
  const valueStyles: Record<MetricAnswerSize, CSSProperties> = {
    table: {
      fontSize: 28,
    },
    detail: {
      fontSize: 34,
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
        border: '1px solid rgba(0, 0, 0, 0.06)',
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
      background: '#f3c964',
      color: '#4f4321',
    },
    warning: {
      background: '#d6d166',
      color: '#454122',
    },
    success: {
      background: '#b9d55b',
      color: '#364117',
    },
    perfect: {
      background: '#a9cc45',
      color: '#2f390f',
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
        background: '#b9d55b',
        color: '#2f3a11',
      }
    : {
        background: '#f1f2f6',
        color: '#59647a',
      };

  return <MetricAnswer size={size} toneStyle={toneStyle}>{value ? 'Да' : 'Нет'}</MetricAnswer>;
}
