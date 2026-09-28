const numberFormatter = new Intl.NumberFormat('ru-RU', {
  useGrouping: true,
  maximumFractionDigits: 20,
});

const fixedFormatters = new Map<number, Intl.NumberFormat>();

export function formatNumber(value: number, fractionDigits?: number): string {
  if (!Number.isFinite(value)) return '\u2014';
  if (fractionDigits === undefined) return numberFormatter.format(value);

  let formatter = fixedFormatters.get(fractionDigits);
  if (!formatter) {
    formatter = new Intl.NumberFormat('ru-RU', {
      useGrouping: true,
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    });
    fixedFormatters.set(fractionDigits, formatter);
  }
  return formatter.format(value);
}
