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
    background: '#07101d',
    backgroundSoft: '#0b1627',
    surface: '#0f1d33',
    surfaceMuted: '#0a1525',
    surfaceStrong: '#173050',
    text: '#f7fbff',
    textMuted: '#c3d4ee',
    textSubtle: '#8ba2c4',
    accent: '#69a4ff',
    accentSoft: 'rgba(105, 164, 255, 0.18)',
    accentContrast: '#07101d',
    success: '#63bb97',
    successSoft: 'rgba(99, 187, 151, 0.16)',
    warning: '#e4bc55',
    warningSoft: 'rgba(228, 188, 85, 0.18)',
    danger: '#de7f93',
    dangerSoft: 'rgba(222, 127, 147, 0.18)',
    fontUi: '"Manrope", ui-sans-serif, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", ui-monospace, monospace',
  },
  light: {
    mode: 'light',
    background: '#f4f8ff',
    backgroundSoft: '#eaf1ff',
    surface: '#ffffff',
    surfaceMuted: '#edf4ff',
    surfaceStrong: '#dbe8ff',
    text: '#10213d',
    textMuted: '#496280',
    textSubtle: '#7288a6',
    accent: '#1f6bff',
    accentSoft: 'rgba(31, 107, 255, 0.14)',
    accentContrast: '#ffffff',
    success: '#2f8f68',
    successSoft: 'rgba(47, 143, 104, 0.14)',
    warning: '#bc8d16',
    warningSoft: 'rgba(188, 141, 22, 0.14)',
    danger: '#bf5f78',
    dangerSoft: 'rgba(191, 95, 120, 0.14)',
    fontUi: '"Manrope", ui-sans-serif, system-ui, sans-serif',
    fontMono: '"JetBrains Mono", ui-monospace, monospace',
  },
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function getInitialTheme(): ThemeMode {
  if (typeof window === 'undefined') {
    return 'dark';
  }

  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (storedTheme === 'dark' || storedTheme === 'light') {
    return storedTheme;
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
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
