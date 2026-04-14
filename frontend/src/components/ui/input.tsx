import * as React from 'react';

import { useTheme } from '../../theme/theme';
import { getInputStyle } from './ui.styles';

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ style, onBlur, onFocus, ...props }, ref) => {
    const { tokens } = useTheme();
    const [focused, setFocused] = React.useState(false);

    return (
      <input
        ref={ref}
        style={{
          ...getInputStyle(tokens, focused),
          ...style,
        }}
        onFocus={(event) => {
          setFocused(true);
          onFocus?.(event);
        }}
        onBlur={(event) => {
          setFocused(false);
          onBlur?.(event);
        }}
        {...props}
      />
    );
  },
);

Input.displayName = 'Input';
