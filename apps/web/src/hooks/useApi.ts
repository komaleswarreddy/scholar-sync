/**
 * API Hook
 * 
 * Custom hook for API operations with error handling and loading states.
 */

import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api-client';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRequest = useCallback(
    async <T,>(request: () => Promise<T>): Promise<T | null> => {
      setLoading(true);
      setError(null);
      try {
        const result = await request();
        return result;
      } catch (err: any) {
        const errorMessage =
          err.response?.data?.detail ||
          err.message ||
          'An error occurred';
        setError(errorMessage);
        console.error('API Error:', err);
        return null;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return {
    loading,
    error,
    handleRequest,
    apiClient,
  };
}



