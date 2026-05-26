import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

export type ThemeMode = 'dark' | 'light';

export type ThemeTokens = {
  mode: ThemeMode;
  background: string;
  backgroundSoft: string;
  surface: string;
  surfaceMuted: string;
  surfaceStrong: string;
  text: string;
  textMuted: string;
  textSubtle: string;
  accent: string;
  accentSoft: string;
  accentContrast: string;
  success: string;
  successSoft: string;
  warning: string;
  warningSoft: string;
  danger: string;
  dangerSoft: string;
  fontUi: string;
  fontMono: string;
};

type ThemeContextValue = {
  mode: ThemeMode;
  tokens: ThemeTokens;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
};

const THEME_STORAGE_KEY = 'call-analyzer-theme';

const themes: Record<ThemeMode, ThemeTokens> = {
  dark: {
    mode: 'dark',
    background: '#121820',
    backgroundSoft: '#1a2330',
    surface: '#1c2735',
    surfaceMuted: '#16212e',
    surfaceStrong: '#253447',
    text: '#eef3fb',
    textMuted: '#becbde',
    textSubtle: '#8e9db5',
    accent: '#4f97ff',
    accentSoft: 'rgba(79, 151, 255, 0.2)',
    accentContrast: '#ffffff',
    success: '#66bd82',
    successSoft: 'rgba(102, 189, 130, 0.2)',
    warning: '#d6aa4b',
    warningSoft: 'rgba(214, 170, 75, 0.2)',
    danger: '#e08795',
    dangerSoft: 'rgba(224, 135, 149, 0.2)',
    fontUi: '"Manrope", ui-sans-serif, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", ui-monospace, monospace',
  },
  light: {
    mode: 'light',
    background: '#f3f5f9',
    backgroundSoft: '#e9edf3',
    surface: '#ffffff',
    surfaceMuted: '#f6f8fb',
    surfaceStrong: '#e6ebf2',
    text: '#243044',
    textMuted: '#59647a',
    textSubtle: '#7f899d',
    accent: '#1677ff',
    accentSoft: 'rgba(22, 119, 255, 0.14)',
    accentContrast: '#ffffff',
    success: '#3d9d5a',
    successSoft: 'rgba(61, 157, 90, 0.14)',
    warning: '#bd922a',
    warningSoft: 'rgba(189, 146, 42, 0.14)',
    danger: '#c5626e',
    dangerSoft: 'rgba(197, 98, 110, 0.14)',
    fontUi: '"Manrope", ui-sans-serif, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", ui-monospace, monospace',
  },
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'light';
  }

  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (storedTheme === 'dark' || storedTheme === 'light') {
    return storedTheme;
  }

  return 'light';
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(getInitialTheme);
  const tokens = themes[mode];

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
    document.documentElement.style.colorScheme = mode;
    document.documentElement.dataset.theme = mode;
    document.body.style.backgroundColor = tokens.background;
    document.body.style.color = tokens.text;
  }, [mode, tokens.background, tokens.text]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      mode,
      tokens,
      setMode,
      toggleMode() {
        setMode((currentMode) => (currentMode === 'dark' ? 'light' : 'dark'));
      },
    }),
    [mode, tokens],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return value;
}
