import { useMemo, useState } from 'react';
import { CheckSquare2, Search, Square } from 'lucide-react';

import type { ReportColumnDefinition } from '../../lib/reporting';
import { useTheme } from '../../theme/theme';
import { Button } from '../ui/button';
import { Input } from '../ui/input';

type CriteriaSelectionPanelProps = {
  columns: ReportColumnDefinition[];
  selectedColumnKeys: Set<string>;
  onToggleColumn: (columnKey: string) => void;
  onSelectAllColumns: () => void;
  onClearColumns: () => void;
};

type ColumnGroup = {
  title: string;
  items: ReportColumnDefinition[];
};

export function CriteriaSelectionPanel({
  columns,
  selectedColumnKeys,
  onToggleColumn,
  onSelectAllColumns,
  onClearColumns,
}: CriteriaSelectionPanelProps) {
  const { tokens } = useTheme();
  const [search, setSearch] = useState('');
  const [showOnlySelected, setShowOnlySelected] = useState(false);

  const normalizedSearch = search.trim().toLowerCase();

  const groups = useMemo<ColumnGroup[]>(() => {
    const filtered = columns.filter((column) => {
      if (showOnlySelected && !selectedColumnKeys.has(column.key)) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      return column.label.toLowerCase().includes(normalizedSearch);
    });

    const baseColumns = filtered.filter((column) => column.kind === 'base');
    const criteriaColumns = filtered.filter((column) => column.kind === 'criterion');

    const nextGroups: ColumnGroup[] = [];
    if (baseColumns.length) {
      nextGroups.push({ title: 'Базовые колонки', items: baseColumns });
    }
    if (criteriaColumns.length) {
      nextGroups.push({ title: 'Критерии', items: criteriaColumns });
    }
    return nextGroups;
  }, [columns, normalizedSearch, selectedColumnKeys, showOnlySelected]);

  return (
    <section
      aria-label="Выбор критериев"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        padding: 14,
        borderRadius: 14,
        background: tokens.surfaceMuted,
        border: `1px solid ${tokens.surfaceStrong}`,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'row',
          flexWrap: 'wrap',
          gap: 8,
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <p style={{ margin: 0, fontSize: 12, color: tokens.textSubtle }}>
          Колонок выбрано: {selectedColumnKeys.size} из {columns.length}
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <Button variant="ghost" size="sm" onClick={onSelectAllColumns} disabled={!columns.length}>
            <CheckSquare2 size={14} />
            Выбрать все
          </Button>
          <Button variant="ghost" size="sm" onClick={onClearColumns} disabled={!selectedColumnKeys.size}>
            <Square size={14} />
            Очистить
          </Button>
          <Button
            variant={showOnlySelected ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => setShowOnlySelected((current) => !current)}
            disabled={!selectedColumnKeys.size}
          >
            {showOnlySelected ? 'Показать все' : 'Только выбранные'}
          </Button>
        </div>
      </div>

      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <Search size={16} style={{ position: 'absolute', left: 12, color: tokens.textSubtle }} />
        <Input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Поиск по колонкам и критериям"
          style={{ paddingLeft: 36 }}
        />
      </div>

      <div
        role="group"
        aria-label="Список колонок"
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          maxHeight: 260,
          overflowY: 'auto',
          paddingRight: 4,
        }}
      >
        {!groups.length ? (
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55, color: tokens.textMuted }}>
            По текущему фильтру колонок не найдено.
          </p>
        ) : null}

        {groups.map((group) => (
          <fieldset
            key={group.title}
            style={{
              margin: 0,
              padding: 0,
              border: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              minWidth: 0,
            }}
          >
            <legend
              style={{
                padding: 0,
                marginBottom: 2,
                fontSize: 12,
                fontWeight: 700,
                color: tokens.textMuted,
              }}
            >
              {group.title}
            </legend>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: 8,
              }}
            >
              {group.items.map((column) => {
                const checked = selectedColumnKeys.has(column.key);

                return (
                  <label
                    key={column.key}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '10px 12px',
                      borderRadius: 12,
                      border: `1px solid ${checked ? tokens.accent : tokens.surfaceStrong}`,
                      background: checked ? tokens.accentSoft : tokens.surface,
                      fontSize: 13,
                      color: tokens.text,
                      cursor: 'pointer',
                      minWidth: 0,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => onToggleColumn(column.key)}
                      style={{ accentColor: tokens.accent }}
                    />
                    <span
                      style={{
                        display: 'inline-block',
                        minWidth: 0,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      title={column.label}
                    >
                      {column.label}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>
    </section>
  );
}
