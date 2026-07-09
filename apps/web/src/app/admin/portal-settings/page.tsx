/**
 * Portal Settings Page
 *
 * Admin page to turn student-portal tabs on/off (e.g. hide Analytics).
 */

'use client';

import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { apiClient } from '@/lib/api-client';
import { AdminTableSkeleton } from '@/components/skeleton';

const TAB_LABELS: Record<string, string> = {
  analytics: 'Analytics',
  study_planner: 'Study Planner',
  problem_solver: 'Problem Solver',
  assets: 'Assets',
};

const TAB_ORDER = ['analytics', 'study_planner', 'problem_solver', 'assets'];

export default function PortalSettingsPage() {
  const { ready } = useAdminPortalApi();
  const queryClient = useQueryClient();

  const { data, isPending: loading, error: queryError } = useQuery({
    queryKey: ['admin-portal-config'],
    queryFn: () => apiClient.getAdminPortalConfig(),
    enabled: ready,
    staleTime: 60 * 1000,
  });

  const mutation = useMutation({
    mutationFn: (body: { tab: string; enabled: boolean }) => apiClient.updateAdminPortalConfig(body),
    onSuccess: (result) => {
      queryClient.setQueryData(['admin-portal-config'], result);
      // Student nav reads the same config — invalidate so it picks up the change.
      queryClient.invalidateQueries({ queryKey: ['portal-config'] });
    },
  });

  const error = queryError ? ((queryError as any)?.message || 'Failed to load portal settings') : null;

  if (loading && !data) return <AdminTableSkeleton />;

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">Portal Settings</h1>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  const enabledTabs = data?.enabled_tabs || {};

  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Portal Settings</h1>
        <p className="text-sm text-text-secondary mt-1">
          Turn student-portal tabs on or off. Disabled tabs disappear from the student navigation immediately.
        </p>
      </div>

      <div className="bg-surface rounded-2xl border border-border-default p-6">
        <div className="space-y-1">
          {TAB_ORDER.map((tab) => {
            const enabled = enabledTabs[tab] !== false;
            return (
              <div
                key={tab}
                className="flex items-center justify-between px-4 py-3 rounded-lg hover:bg-surface-hover"
              >
                <span className="text-sm font-medium text-text-primary">{TAB_LABELS[tab] ?? tab}</span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={enabled}
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate({ tab, enabled: !enabled })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    enabled ? 'bg-accent-blue' : 'bg-border-default'
                  } disabled:opacity-50`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
