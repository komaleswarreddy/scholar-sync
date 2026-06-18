export type HeatmapLevel = 'strong' | 'good' | 'average' | 'weak' | 'empty';

export const HEATMAP_CELL_COLORS: Record<HeatmapLevel, string> = {
  strong: '#0D3D2E',
  good: '#0F7A52',
  average: '#F59E0B',
  weak: '#F97316',
  empty: '#E8EBE9',
};

export const HEATMAP_LEGEND: Array<{ level: HeatmapLevel; label: string }> = [
  { level: 'strong', label: 'Strong' },
  { level: 'good', label: 'Good' },
  { level: 'average', label: 'Average' },
  { level: 'weak', label: 'Weak' },
  { level: 'empty', label: 'Not studied' },
];

export function normalizeHeatmapCells(raw: unknown): HeatmapLevel[] {
  const allowed = new Set(Object.keys(HEATMAP_CELL_COLORS));
  const cells: HeatmapLevel[] = [];
  if (Array.isArray(raw)) {
    for (const item of raw) {
      if (typeof item === 'string' && allowed.has(item)) {
        cells.push(item as HeatmapLevel);
      }
    }
  }
  while (cells.length < 40) cells.push('empty');
  return cells.slice(0, 40);
}
