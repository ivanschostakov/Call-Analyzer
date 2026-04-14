import * as React from 'react';

import { useTheme } from '../../theme/theme';
import { getButtonStyle } from './ui.styles';

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ size = 'md', variant = 'primary', type = 'button', style, ...props }, ref) => {
    const { tokens } = useTheme();

    return (
      <button
        ref={ref}
        type={type}
        style={{
          ...getButtonStyle(tokens, variant, size, props.disabled),
          ...style,
        }}
        {...props}
      />
    );
  },
);

Button.displayName = 'Button';
