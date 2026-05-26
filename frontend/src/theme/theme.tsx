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
  radiusSm: number;
  radiusMd: number;
  radiusLg: number;
  shadowSm: string;
  shadowMd: string;
  shadowLg: string;
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
    background: '#12171f',
    backgroundSoft: '#1a2330',
    surface: '#1c2533',
    surfaceMuted: '#16212e',
    surfaceStrong: '#2a374a',
    text: '#eef3fb',
    textMuted: '#c5d1e2',
    textSubtle: '#90a0b8',
    accent: '#3f8cff',
    accentSoft: 'rgba(63, 140, 255, 0.22)',
    accentContrast: '#ffffff',
    success: '#5fc783',
    successSoft: 'rgba(95, 199, 131, 0.2)',
    warning: '#d2a548',
    warningSoft: 'rgba(210, 165, 72, 0.2)',
    danger: '#df7d8e',
    dangerSoft: 'rgba(223, 125, 142, 0.2)',
    radiusSm: 10,
    radiusMd: 14,
    radiusLg: 18,
    shadowSm: '0 1px 2px rgba(2, 6, 23, 0.24)',
    shadowMd: '0 8px 20px rgba(2, 8, 20, 0.28)',
    shadowLg: '0 16px 34px rgba(3, 8, 20, 0.34)',
    fontUi: '"Manrope", ui-sans-serif, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", ui-monospace, monospace',
  },
  light: {
    mode: 'light',
    background: '#f2f5f8',
    backgroundSoft: '#edf1f6',
    surface: '#ffffff',
    surfaceMuted: '#f7f9fc',
    surfaceStrong: '#e4eaf2',
    text: '#1f2a3b',
    textMuted: '#56627a',
    textSubtle: '#7d889a',
    accent: '#0f6bff',
    accentSoft: 'rgba(15, 107, 255, 0.14)',
    accentContrast: '#ffffff',
    success: '#33985c',
    successSoft: 'rgba(51, 152, 92, 0.14)',
    warning: '#b28520',
    warningSoft: 'rgba(178, 133, 32, 0.14)',
    danger: '#c45161',
    dangerSoft: 'rgba(196, 81, 97, 0.14)',
    radiusSm: 10,
    radiusMd: 14,
    radiusLg: 18,
    shadowSm: '0 1px 2px rgba(16, 24, 40, 0.06)',
    shadowMd: '0 10px 24px rgba(16, 24, 40, 0.1)',
    shadowLg: '0 20px 40px rgba(16, 24, 40, 0.14)',
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
