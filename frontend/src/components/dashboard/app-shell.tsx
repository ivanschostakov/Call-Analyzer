import { Moon, PanelsTopLeft, Sun } from 'lucide-react';

import { useTheme } from '../../theme/theme';
import { getAppShellStyles } from './dashboard.styles';
import { Button } from '../ui/button';

type AppShellProps = {
  children: React.ReactNode;
};

const navItems = [
  { label: 'Панель', active: true },
  { label: 'Расшифровки', active: false },
  { label: 'Анализы', active: false },
  { label: 'Шаблоны', active: false },
];

export function AppShell({ children }: AppShellProps) {
  const { mode, toggleMode, tokens } = useTheme();
  const styles = getAppShellStyles(tokens);

  return (
    <div style={styles.root}>
      <div style={styles.container}>
        <header style={styles.header}>
          <div style={styles.headerTop}>
            <div style={styles.brandBlock}>
              <div style={styles.brandMark}>
                <PanelsTopLeft size={18} />
              </div>
              <div>
                <p style={styles.brandTitle}>Call Analyzer</p>
              </div>
            </div>

            <Button variant="ghost" size="sm" onClick={toggleMode}>
              {mode === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
              {mode === 'dark' ? 'Светлая тема' : 'Темная тема'}
            </Button>
          </div>

          <nav style={styles.nav}>
            {navItems.map((item) => (
              <div
                key={item.label}
                style={{
                  ...styles.navItem,
                  ...(item.active ? styles.navItemActive : undefined),
                }}
              >
                <span>{item.label}</span>
                {!item.active ? <span style={styles.navSoon}>Скоро</span> : null}
              </div>
            ))}
          </nav>
        </header>

        <div style={styles.children}>{children}</div>
      </div>
    </div>
  );
}
