import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useUserContext } from '@/contexts/UserContext';

/** Tenant-level tab visibility (admin can turn tabs off). Defaults to all-on while loading. */
export function usePortalConfig() {
  const { isSignedIn } = useUserContext();

  const { data } = useQuery({
    queryKey: ['portal-config'],
    queryFn: () => apiClient.getPortalConfig(),
    enabled: isSignedIn,
    staleTime: 5 * 60 * 1000,
  });

  return {
    isTabEnabled: (tab: string) => data?.enabled_tabs?.[tab] !== false,
  };
}
