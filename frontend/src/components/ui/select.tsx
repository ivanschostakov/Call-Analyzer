import * as React from 'react';

import { useTheme } from '../../theme/theme';
import { getSelectStyle } from './ui.styles';

export const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ style, onBlur, onFocus, children, ...props }, ref) => {
    const { tokens } = useTheme();
    const [focused, setFocused] = React.useState(false);

    return (
      <select
        ref={ref}
        style={{
          ...getSelectStyle(tokens, focused),
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
      >
        {children}
      </select>
    );
  },
);

Select.displayName = 'Select';
