import type { CompanyRead } from '../../api/generated/model';
import { useTheme } from '../../theme/theme';
import { getCompanySwitcherStyles } from './dashboard.styles';

export function CompanySwitcher({
  companies,
  value,
  onChange,
}: {
  companies: CompanyRead[];
  value: number | null;
  onChange: (companyId: number) => void;
}) {
  const { tokens } = useTheme();
  const styles = getCompanySwitcherStyles(tokens);

  return (
    <div style={styles.wrapper}>
      <label style={styles.label}>Компания</label>
      <select
        value={value ?? ''}
        onChange={(event) => onChange(Number(event.target.value))}
        style={{
          ...styles.select,
          colorScheme: tokens.mode,
        }}
      >
        {companies.map((company) => (
          <option
            key={company.id}
            value={company.id}
            style={{
              color: tokens.text,
              background: tokens.surface,
            }}
          >
            {company.name}
          </option>
        ))}
      </select>
    </div>
  );
}
