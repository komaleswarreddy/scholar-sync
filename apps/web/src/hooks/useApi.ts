/**
 * API Hook
 *  
 * Custom hook for API operations with error handling and loading states.
 */

import { useState, useCallback } from 'react';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage, ApiError } from '@/lib/error-handler';

export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<ApiError | null>(null);

  const handleRequest = useCallback(
    async <T,>(request: () => Promise<T>): Promise<T | null> => {
      const outcome = await (async () => {
        setLoading(true);
        setError(null);
        setErrorDetails(null);
        try {
          const result = await request();
          return { data: result as T, error: null as ApiError | null, errorMessage: null as string | null };
        } catch (err: any) {
          const apiError = err.apiError || handleApiError(err);
          const errorMessage = getUserFriendlyMessage(apiError);
          setError(errorMessage);
          setErrorDetails(apiError);
          console.error('API Error:', apiError);
          return { data: null as T | null, error: apiError, errorMessage };
        } finally {
          setLoading(false);
        }
      })();
      return outcome.data;
    },
    []
  );

  const executeRequest = useCallback(async <T,>(request: () => Promise<T>) => {
    setLoading(true);
    setError(null);
    setErrorDetails(null);
    try {
      const data = await request();
      return { data, error: null as ApiError | null, errorMessage: null as string | null };
    } catch (err: any) {
      const apiError = err.apiError || handleApiError(err);
      const errorMessage = getUserFriendlyMessage(apiError);
      setError(errorMessage);
      setErrorDetails(apiError);
      console.error('API Error:', apiError);
      return { data: null as T | null, error: apiError, errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
    setErrorDetails(null);
  }, []);

  return {
    loading,
    error,
    errorDetails,
    handleRequest,
    executeRequest,
    clearError,
    apiClient,
  };
}



