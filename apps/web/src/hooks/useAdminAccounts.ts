'use client';

import { useMutation, useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { adminQueryKeys } from '@/hooks/usePrefetchAdminData';

export function useAdminAccounts(search?: string, role?: string) {
  const { ready } = useAdminPortalApi();
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: adminQueryKeys.accounts(search, role),
    queryFn: () => apiClient.listAccounts({ search, role }),
    enabled: ready,
    staleTime: 2 * 60 * 1000,
    placeholderData: keepPreviousData,
  });

  const createMutation = useMutation({
    mutationFn: apiClient.createAccount.bind(apiClient),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'accounts'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof apiClient.updateAccount>[1] }) =>
      apiClient.updateAccount(id, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'accounts'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteAccount(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin', 'accounts'] });
    },
  });

  return { listQuery, createMutation, updateMutation, deleteMutation, ready };
}
