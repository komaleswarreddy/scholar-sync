/**
 * Error Handler Utility
 * 
 * Standardized error handling for API requests with user-friendly messages
 */

export enum ErrorType {
  NETWORK = 'NETWORK',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  RATE_LIMIT = 'RATE_LIMIT',
  SERVER_ERROR = 'SERVER_ERROR',
  CLIENT_ERROR = 'CLIENT_ERROR',
  TIMEOUT = 'TIMEOUT',
  UNKNOWN = 'UNKNOWN',
}

export interface ApiError { 
  type: ErrorType;
  message: string;
  statusCode?: number;
  retryable: boolean;
  retryAfter?: number; // Seconds to wait before retry (for 429)
}

/**
 * Standardized error messages
 */
const ERROR_MESSAGES = {
  [ErrorType.NETWORK]: 'Unable to connect to the server. Please check your internet connection and try again.',
  [ErrorType.UNAUTHORIZED]: 'Your session has expired. Please sign in again.',
  [ErrorType.FORBIDDEN]: 'You do not have permission to perform this action.',
  [ErrorType.RATE_LIMIT]: 'Too many requests. Please wait a moment and try again.',
  [ErrorType.SERVER_ERROR]: 'The server encountered an error. Please try again later.',
  [ErrorType.CLIENT_ERROR]: 'There was an error with your request. Please check your input and try again.',
  [ErrorType.TIMEOUT]: 'The request took too long to complete. Please try again.',
  [ErrorType.UNKNOWN]: 'An unexpected error occurred. Please try again.',
};

/**
 * Extract error message from axios error response
 */
function extractErrorMessage(error: any): string {
  // Try to get error message from response data
  if (error.response?.data) {
    const data = error.response.data;
    
    // FastAPI typically returns { detail: "message" }
    if (data.detail) {
      if (typeof data.detail === 'object' && data.detail.message) {
        return data.detail.message;
      }
      return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
    
    // Some APIs return { message: "..." }
    if (data.message) {
      return data.message;
    }
    
    // Some APIs return { error: "..." }
    if (data.error) {
      return data.error;
    }
  }
  
  // Fall back to error message
  if (error.message) {
    return error.message;
  }
  
  return ERROR_MESSAGES[ErrorType.UNKNOWN];
}

/**
 * Client-side timeouts (Axios ECONNABORTED, slow server) are not "offline" — avoid mislabeling as NETWORK.
 */
function isTimeoutError(error: any): boolean {
  if (!error) return false;
  const msg = String(error.message || '').toLowerCase();
  if (msg.includes('timeout')) return true;
  if (error.code === 'ETIMEDOUT') return true;
  // Axios aborts timed-out XHRs with ECONNABORTED + "timeout of Nms exceeded"
  if (error.code === 'ECONNABORTED' && msg.includes('exceeded')) return true;
  return false;
}

/**
 * Determine if error is a network error
 */
function isNetworkError(error: any): boolean {
  if (isTimeoutError(error)) {
    return false;
  }

  // Plain application errors (e.g. throw new Error('...')) are not network failures
  if (error instanceof Error && !('response' in error) && !error?.isAxiosError) {
    return false;
  }

  // Axios: no HTTP response can mean offline — only treat known network codes/messages
  if (!error.response) {
    const networkErrorCodes = ['ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT', 'ENETUNREACH', 'ERR_NETWORK'];
    if (error.code && networkErrorCodes.includes(error.code)) {
      return true;
    }
    if (
      error.message?.includes('Network Error') ||
      error.message?.includes('Network request failed') ||
      error.message?.includes('Failed to fetch')
    ) {
      return true;
    }
    return false;
  }

  // Check for specific network error codes (not ECONNABORTED alone — often used for timeouts)
  const networkErrorCodes = ['ECONNREFUSED', 'ENOTFOUND', 'ETIMEDOUT', 'ENETUNREACH'];

  if (error.code && networkErrorCodes.includes(error.code)) {
    return true;
  }
  
  // Check for fetch API network errors
  if (error.name === 'TypeError' && error.message?.includes('fetch')) {
    return true;
  }
  
  if (error.message?.includes('network')) {
    return true;
  }
  
  return false;
}

/**
 * Get retry-after header value in seconds
 */
function getRetryAfter(error: any): number | undefined {
  const retryAfter = error.response?.headers?.['retry-after'] || 
                     error.response?.headers?.['Retry-After'];
  
  if (retryAfter) {
    const seconds = parseInt(retryAfter, 10);
    if (!isNaN(seconds) && seconds > 0) {
      return seconds;
    }
  }
  
  return undefined;
}

/**
 * Handle HTTP error and return standardized ApiError
 */
export function handleApiError(error: any): ApiError {
  if (isTimeoutError(error)) {
    return {
      type: ErrorType.TIMEOUT,
      message: ERROR_MESSAGES[ErrorType.TIMEOUT],
      retryable: true,
    };
  }

  // Non-HTTP errors thrown in app code (polling failures, validation, etc.)
  if (error instanceof Error && !error.response && !error?.isAxiosError) {
    return {
      type: ErrorType.CLIENT_ERROR,
      message: error.message || ERROR_MESSAGES[ErrorType.UNKNOWN],
      retryable: false,
    };
  }

  // Network errors (no response)
  if (isNetworkError(error)) {
    return {
      type: ErrorType.NETWORK,
      message: ERROR_MESSAGES[ErrorType.NETWORK],
      retryable: true,
    };
  }
  
  const statusCode = error.response?.status;
  
  if (!statusCode) {
    return {
      type: ErrorType.UNKNOWN,
      message: extractErrorMessage(error),
      retryable: false,
    };
  }
  
  // Handle specific HTTP status codes
  switch (statusCode) {
    case 401:
      return {
        type: ErrorType.UNAUTHORIZED,
        message: ERROR_MESSAGES[ErrorType.UNAUTHORIZED],
        statusCode: 401,
        retryable: false,
      };
    
    case 403:
      return {
        type: ErrorType.FORBIDDEN,
        message: ERROR_MESSAGES[ErrorType.FORBIDDEN],
        statusCode: 403,
        retryable: false,
      };
    
    case 429:
      const retryAfter = getRetryAfter(error);
      return {
        type: ErrorType.RATE_LIMIT,
        message: retryAfter 
          ? `Too many requests. Please wait ${retryAfter} second${retryAfter !== 1 ? 's' : ''} and try again.`
          : ERROR_MESSAGES[ErrorType.RATE_LIMIT],
        statusCode: 429,
        retryable: true,
        retryAfter,
      };
    
    case 408:
    case 504:
      return {
        type: ErrorType.TIMEOUT,
        message: ERROR_MESSAGES[ErrorType.TIMEOUT],
        statusCode,
        retryable: true,
      };
    
    case 500:
    case 502:
    case 503:
      return {
        type: ErrorType.SERVER_ERROR,
        message: ERROR_MESSAGES[ErrorType.SERVER_ERROR],
        statusCode,
        retryable: true,
      };
    
    case 400:
    case 404:
    case 422:
      return {
        type: ErrorType.CLIENT_ERROR,
        message: extractErrorMessage(error),
        statusCode,
        retryable: false,
      };
    
    default:
      // For other 4xx errors, treat as client error
      if (statusCode >= 400 && statusCode < 500) {
        return {
          type: ErrorType.CLIENT_ERROR,
          message: extractErrorMessage(error),
          statusCode,
          retryable: false,
        };
      }
      
      // For other 5xx errors, treat as server error
      if (statusCode >= 500) {
        return {
          type: ErrorType.SERVER_ERROR,
          message: ERROR_MESSAGES[ErrorType.SERVER_ERROR],
          statusCode,
          retryable: true,
        };
      }
      
      return {
        type: ErrorType.UNKNOWN,
        message: extractErrorMessage(error),
        statusCode,
        retryable: false,
      };
  }
}

/**
 * Redirect to login page
 * Used when authentication fails and token refresh is not possible
 */
export function redirectToLogin(): void {
  if (typeof window !== 'undefined') {
    // Get current path to redirect back after login
    const currentPath = window.location.pathname + window.location.search;
    const redirectUrl = currentPath !== '/' ? `?redirect_url=${encodeURIComponent(currentPath)}` : '';
    window.location.href = `/sign-in${redirectUrl}`;
  }
}

/**
 * Get user-friendly error message from ApiError
 */
export function getUserFriendlyMessage(error: ApiError): string {
  return error.message;
}
