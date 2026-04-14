import type { CSSProperties } from 'react';

const ACTIVE_STAR_COLOR = '#f7c948';
const INACTIVE_STAR_COLOR = '#efe5c9';

export function getFavoriteButtonStyle(): CSSProperties {
  return {
    width: 36,
    minWidth: 36,
    padding: 0,
    flexShrink: 0,
  };
}

export function getFavoriteStarStyle(isFavorite: boolean): CSSProperties {
  const color = isFavorite ? ACTIVE_STAR_COLOR : INACTIVE_STAR_COLOR;

  return {
    color,
    fill: color,
    fillOpacity: isFavorite ? 0.94 : 0.82,
    filter: isFavorite
      ? 'drop-shadow(0 0 6px rgba(247, 201, 72, 0.35))'
      : 'drop-shadow(0 0 4px rgba(239, 229, 201, 0.2))',
  };
}
