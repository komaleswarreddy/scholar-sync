export type TelemetryEventName =
  | 'home.viewed'
  | 'home.continue_learning_clicked'
  | 'home.tutor_clicked'
  | 'home.create_notes_clicked'
  | 'home.analytics_clicked'
  | 'home.studios_view_all_clicked'
  | 'home.notes_view_all_clicked'
  | 'tutor.viewed'
  | 'tutor.start_clicked'
  | 'notes.viewed'
  | 'notes.filtered'
  | 'studios.viewed'
  | 'studios.feature_opened'
  | 'analytics.viewed';

export type TelemetryEvent = {
  name: TelemetryEventName;
  ts: string; // ISO
  props?: Record<string, unknown>;
};

const QUEUE_KEY = 'telemetryQueueV1';

function safeNowIso() {
  try {
    return new Date().toISOString();
  } catch {
    return `${Date.now()}`;
  }
}

function enqueue(evt: TelemetryEvent) {
  if (typeof window === 'undefined') return;
  try {
    const existing = window.localStorage.getItem(QUEUE_KEY);
    const parsed = existing ? (JSON.parse(existing) as TelemetryEvent[]) : [];
    const next = [evt, ...parsed].slice(0, 200);
    window.localStorage.setItem(QUEUE_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

export function track(name: TelemetryEventName, props?: Record<string, unknown>) {
  const evt: TelemetryEvent = { name, ts: safeNowIso(), props };
  enqueue(evt);
  if (typeof window !== 'undefined' && process.env.NODE_ENV !== 'production') {
    // Keep this low-noise in dev; consumers can tail localStorage queue if needed.
    // eslint-disable-next-line no-console
    console.debug('[telemetry]', evt.name, evt.props ?? {});
  }
}

