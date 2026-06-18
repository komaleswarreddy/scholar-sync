/**
 * Mirror of config/ncert_subjects_by_class.yaml — used as instant wizard data and API fallback.
 * Keep in sync when editing the YAML on the backend.
 */
export const DEFAULT_NCERT_SUBJECTS_BY_CLASS: Record<string, string[]> = {
  '12': ['physics', 'chemistry', 'mathematics', 'biology'],
};
