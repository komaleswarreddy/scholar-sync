import apiClient from '@/lib/api-client';

export type ContinueLearningResolution =
  | { kind: 'dashboard'; reason: string }
  | { kind: 'dashboard_with_recent_chat'; reason: string };

function hasSelectedSources(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    const raw = window.localStorage.getItem('selected_source_ids');
    if (!raw) return false;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length > 0;
  } catch {
    return false;
  }
}

/**
 * V1: The product currently behaves like a workspace (sources + chat) rather than
 * a URL-addressable “notebook”. We resolve Continue Learning into the existing
 * `/dashboard` workspace, letting it auto-load recents safely.
 */
export async function resolveContinueLearning(): Promise<ContinueLearningResolution> {
  // Prefer “unfinished” workspace signals.
  if (hasSelectedSources()) {
    return { kind: 'dashboard', reason: 'selected_sources_present' };
  }

  // Fallback to most recent chat.
  try {
    const res = await apiClient.listChats(1, 0);
    const chats = (res?.chats ?? []) as Array<{ id?: string }>;
    if (chats.length > 0 && chats[0]?.id) {
      return { kind: 'dashboard_with_recent_chat', reason: 'recent_chat_exists' };
    }
  } catch {
    // If the API is cold/unavailable, still land in dashboard safely.
  }

  // Final fallback: workspace landing where user can upload sources / start chat.
  return { kind: 'dashboard', reason: 'fallback' };
}

