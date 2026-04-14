import * as React from 'react';

import { useTheme } from '../../theme/theme';
import { getTextareaStyle } from './ui.styles';

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ style, onBlur, onFocus, ...props }, ref) => {
    const { tokens } = useTheme();
    const [focused, setFocused] = React.useState(false);

    return (
      <textarea
        ref={ref}
        style={{
          ...getTextareaStyle(tokens, focused),
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

Textarea.displayName = 'Textarea';
