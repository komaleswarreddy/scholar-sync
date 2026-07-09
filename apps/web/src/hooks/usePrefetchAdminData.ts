'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { getPlatformToken } from '@/lib/platform-auth';
import { useSessionQueryEnabled } from '@/hooks/usePlatformSession';

export const adminQueryKeys = {
  accounts: (search?: string, role?: string) => ['admin', 'accounts', search ?? '', role ?? ''] as const,
  ragQuality: (days = 30) => ['admin', 'rag-quality', days] as const,
  // Shared parametrized keys — pages that call the same endpoint with the same
  // args (e.g. admin/users and admin/cost-tokens both call getCostTracking(30,
  // true)) read from the same react-query cache entry instead of each firing
  // their own network request on every sidebar navigation.
  tokenConsumption: (days: number, groupBy: string) => ['admin', 'token-consumption', days, groupBy] as const,
  costTracking: (days: number, breakdown: boolean) => ['admin', 'cost-tracking', days, breakdown] as const,
  cacheEfficiency: (days: number) => ['admin', 'cache-efficiency', days] as const,
  latencyDashboard: (days: number) => ['admin', 'latency-dashboard', days] as const,
  alertsStatus: () => ['admin', 'alerts-status'] as const,
  aggregateMetrics: (days: number) => ['admin', 'aggregate-metrics', days] as const,
  usersList: () => ['admin', 'users', 'list'] as const,
  agents: (days: number, compareDays: number, compareEnabled: boolean) =>
    ['admin', 'agents', days, compareDays, compareEnabled] as const,
  documents: () => ['admin', 'documents', 'sources'] as const,
  logs: (days: number, limit: number, filterType?: string) =>
    ['admin', 'logs', days, limit, filterType ?? 'all'] as const,
  userMetrics: (userId: string, days: number) => ['admin', 'user-metrics', userId, days] as const,
  userSessions: (userId: string, days: number) => ['admin', 'user-sessions', userId, days] as const,
};

/** Prime API token for admin routes (sync, no useEffect delay). */
export function primeAdminApiToken(): void {
  const token = getPlatformToken();
  if (token) {
    apiClient.setTokenGetter(async () => getPlatformToken());
    apiClient.primeAuthToken(token);
  }
}

/** Prefetch common admin list endpoints after login / layout mount. */
export function prefetchAdminPortalData(queryClient: ReturnType<typeof useQueryClient>) {
  primeAdminApiToken();

  void queryClient.prefetchQuery({
    queryKey: adminQueryKeys.accounts(),
    queryFn: () => apiClient.listAccounts(),
    staleTime: 2 * 60 * 1000,
  });

  void queryClient.prefetchQuery({
    queryKey: adminQueryKeys.ragQuality(30),
    queryFn: () => apiClient.getRagQuality(30),
    staleTime: 2 * 60 * 1000,
  });

  // Admin login lands on /admin/users, which needs this exact 6-call bundle —
  // warm it here (fired at login click / layout mount) so first paint of that
  // page reads from cache instead of waiting on 6 fresh network round trips.
  void queryClient.prefetchQuery({
    queryKey: adminQueryKeys.usersList(),
    queryFn: () => apiClient.listAllUsers(),
    staleTime: 2 * 60 * 1000,
  });
  void queryClient.prefetchQuery({
    queryKey: adminQueryKeys.tokenConsumption(30, 'user'),
    queryFn: () => apiClient.getTokenConsumption(30, 'user'),
    staleTime: 2 * 60 * 1000,
  });
  void queryClient.prefetchQuery({
    queryKey: adminQueryKeys.costTracking(30, true),
    queryFn: () => apiClient.getCostTracking(30, true),
    staleTime: 2 * 60 * 1000,
  });
  void queryClient.prefetchQuery({
    queryKey: adminQueryKeys.cacheEfficiency(30),
    queryFn: () => apiClient.getCacheEfficiency(30),
    staleTime: 2 * 60 * 1000,
  });
  void queryClient.prefetchQuery({
    queryKey: adminQueryKeys.latencyDashboard(30),
    queryFn: () => apiClient.getLatencyDashboard(30),
    staleTime: 2 * 60 * 1000,
  });
  void queryClient.prefetchQuery({
    queryKey: adminQueryKeys.alertsStatus(),
    queryFn: () => apiClient.getAlertsStatus(),
    staleTime: 2 * 60 * 1000,
  });
}

export function usePrefetchAdminData() {
  const queryClient = useQueryClient();
  const ready = useSessionQueryEnabled();

  useEffect(() => {
    if (!ready) return;
    prefetchAdminPortalData(queryClient);
  }, [ready, queryClient]);
}
