import axios, {
  AxiosInstance,
  AxiosRequestHeaders,
  InternalAxiosRequestConfig, 
} from 'axios';
import { handleApiError, redirectToLogin, getUserFriendlyMessage, ApiError, ErrorType } from './error-handler';

type TokenGetter = () => Promise<string | null>;
type LogoutFunc = () => Promise<void>;

/** Tailored report format — must match `apps/api/schemas/studio.py` `report_format` and Studio UI. */
export type StudioReportFormat =
  | 'integrated'
  | 'briefing'
  | 'study_guide'
  | 'newsletter'
  | 'thematic_summary';

export interface NcertTutorChapterOption {
  chapter_no?: number | null;
  chapter_name?: string | null;
  title?: string | null;
}

export interface NcertTutorFiltersResponse {
  classes: number[];
  subjects_by_class: Record<string, string[]>;
  chapters: NcertTutorChapterOption[];
}

/**
 * Read tenantId from cookie (set by middleware)
 */
function getTenantIdFromCookie(): string {
  if (typeof document === 'undefined') return 'default';

  const match = document.cookie
    .split('; ')
    .find(row => row.startsWith('tenantId='));

  return match ? match.split('=')[1] : 'default';
}

/**
 * Extract user ID from JWT token (from 'sub' claim)
 */
function extractUserIdFromToken(token: string | null): string | null {
  if (!token) return null;
  
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    
    const payload = JSON.parse(atob(parts[1]));
    return payload.sub || null;
  } catch (error) {
    console.error('[API Client] Failed to extract user ID from token:', error);
    return null;
  }
}

class ApiClient {
  private client: AxiosInstance;
  private getTokenFunc: TokenGetter | null = null;
  private logoutFunc: LogoutFunc | null = null;
  private latestToken: string | null = null;
  private tokenExpiry: number | null = null; // Unix timestamp when token expires
  private refreshPromise: Promise<void> | null = null; // Prevent concurrent refresh attempts
  private authFailureCount: number = 0; // Track consecutive auth failures
  private maxAuthFailures: number = 3; // Stop trying after 3 failures
  private circuitBreakerOpen: boolean = false; // Circuit breaker state

  constructor(
    baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  ) {
    this.client = axios.create({
      baseURL,
      timeout: 15000, // Default; list/chat/source reads use longer per-request timeouts
      // Don't set default Content-Type - let axios set it based on data type
    });

    // ------------------------
    // Request Interceptor
    // ------------------------
    this.client.interceptors.request.use(
      async (config: InternalAxiosRequestConfig): Promise<InternalAxiosRequestConfig> => {
        const headers: AxiosRequestHeaders = config.headers;
        const url = config.url || 'unknown';
        const method = config.method?.toUpperCase() || 'UNKNOWN';

        // Check if this is a FormData request
        const isFormData = config.data instanceof FormData;

        // Set Content-Type only for non-FormData requests
        // For FormData, axios will set it automatically with boundary
        if (!isFormData && !headers['Content-Type']) {
          headers['Content-Type'] = 'application/json';
        } else if (isFormData) {
          // Remove Content-Type for FormData so axios can set it with boundary
          delete headers['Content-Type'];
        }

        // Task B.d: Handle token refresh - refresh if token is missing or expired
        if (!this.circuitBreakerOpen && !this.latestToken && this.getTokenFunc) {
          try {
            await this.refreshToken(true);
          } catch (e) {
            // Ignore token refresh errors
          }
        }

        // Task B.c: Ensure all requests include Authorization header when token is available
        if (this.circuitBreakerOpen) {
          delete headers['Authorization'];
        } else if (this.latestToken) {
          headers['Authorization'] = `Bearer ${this.latestToken}`;
        } else {
          // Try to get token if available
          if (this.getTokenFunc) {
            try {
              const token = await this.getTokenFunc();
              if (token) {
                this.latestToken = token;
                this.tokenExpiry = this.getTokenExpiry(token);
                headers['Authorization'] = `Bearer ${token}`;
              }
            } catch (e) {
              // Ignore token fetch errors
            }
          }
        }

        // Task B.a: Ensure all requests include X-Tenant-ID
        const tenantId = getTenantIdFromCookie();
        headers['x-tenant-id'] = tenantId;

        // Task B.b: Ensure all requests include X-User-ID (from Clerk token)
        const userId = extractUserIdFromToken(this.latestToken);
        if (userId) {
          headers['x-user-id'] = userId;
        } else {
          // If we don't have a token yet, try to get it to extract user ID
          if (this.getTokenFunc && !this.latestToken) {
            try {
              const token = await this.getTokenFunc();
              if (token) {
                const extractedUserId = extractUserIdFromToken(token);
                if (extractedUserId) {
                  headers['x-user-id'] = extractedUserId;
                }
              }
            } catch (e) {
              // Ignore token fetch errors
            }
          }
        }

        return config;
      }
    );

    // ------------------------
    // Response Interceptor
    // ------------------------
    this.client.interceptors.response.use(
      (res) => res,
      async (error) => {
        const originalRequest = error.config;
        const status = error.response?.status;

        // Handle 401 Unauthorized - try token refresh, then redirect to login
        if (status === 401 && !originalRequest._retry) {
          this.authFailureCount++;

          // If we've exceeded max auth failures, redirect to login
          if (this.authFailureCount >= this.maxAuthFailures) {
            this.circuitBreakerOpen = true;
            console.error(`Circuit breaker opened after ${this.authFailureCount} auth failures. Redirecting to login.`);
            
            // Redirect to login if logout handler is available
            if (this.logoutFunc) {
              try {
                await this.logoutFunc();
              } catch (err) {
                console.error('Logout failed', err);
              }
            }
            
            // Redirect to login page
            redirectToLogin();
            
            // Create standardized error
            const apiError = handleApiError(error);
            return Promise.reject(apiError);
          }

          originalRequest._retry = true;

          try {
            await this.refreshToken();

            if (this.latestToken) {
              this.authFailureCount = 0;
              this.circuitBreakerOpen = false;
              // Task B.c: Update Authorization header with new token
              originalRequest.headers['Authorization'] = `Bearer ${this.latestToken}`;
              // Task B.b: Update X-User-ID header with user ID from refreshed token
              const userId = extractUserIdFromToken(this.latestToken);
              if (userId) {
                originalRequest.headers['x-user-id'] = userId;
              }
              return this.client(originalRequest);
            }
          } catch (err) {
            console.error('Token refresh failed:', err);
          }

          // If token refresh failed and circuit breaker is open, redirect to login
          if (this.circuitBreakerOpen) {
            if (this.logoutFunc) {
              try {
                await this.logoutFunc();
              } catch (err) {
                console.error('Logout failed', err);
              }
            }
            redirectToLogin();
            const apiError = handleApiError(error);
            return Promise.reject(apiError);
          }
        }

        // Handle all other errors with standardized error handling
        const apiError = handleApiError(error);
        
        // Only log errors that are not already handled or retried
        // Skip logging if this is a retryable error that will be retried
        const isRetryableNetworkError = apiError.type === 'NETWORK' && apiError.retryable;
        const willRetry = isRetryableNetworkError && !originalRequest._retry;
        
        // Skip logging if request is marked as silent (e.g., for admin checks)
        const isSilent = originalRequest._silent === true;
        
        // Skip logging 403 errors for admin check requests (expected behavior)
        const isExpected403 = status === 403 && originalRequest._expected403 === true;
        
        // Log error details for debugging (but not for retryable errors that will be retried, silent requests, or expected 403s)
        if (!willRetry && !isSilent && !isExpected403) {
          if (status) {
            console.error(`[API Error] ${status}: ${apiError.message}`);
          } else {
            // Only log network errors if they're not retryable or already retried
            if (!isRetryableNetworkError || originalRequest._retry) {
              console.error(`[API Error] Network: ${apiError.message}`);
            }
          }
        }

        // Attach the ApiError to the error object for easier access
        error.apiError = apiError;
        
        return Promise.reject(error);
      }
    );
  }

  setTokenGetter(getTokenFunc: TokenGetter) {
    this.getTokenFunc = getTokenFunc;
    this.refreshToken();
  }

  setLogoutHandler(logoutFunc: LogoutFunc) {
    this.logoutFunc = logoutFunc;
  }

  /**
   * Check if token is expired or will expire soon (within 60 seconds)
   */
  private isTokenExpired(): boolean {
    if (!this.latestToken || !this.tokenExpiry) {
      return true;
    }
    // Refresh if token expires within 60 seconds
    const bufferTime = 60 * 1000; // 60 seconds in milliseconds
    return Date.now() >= (this.tokenExpiry - bufferTime);
  }

  /**
   * Extract expiration time from JWT token
   */
  private getTokenExpiry(token: string): number | null {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      if (payload.exp) {
        return payload.exp * 1000; // Convert to milliseconds
      }
    } catch (e) {
      // Ignore decode errors
    }
    return null;
  }

  /**
   * Refresh token with race condition protection
   * Only one refresh attempt will be made at a time, even with concurrent requests
   */
  async refreshToken(force: boolean = false): Promise<void> {
    if (!this.getTokenFunc) {
      return;
    }

    if (!force && !this.isTokenExpired()) {
      return;
    }

    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      try {
        const tokenPromise = this.getTokenFunc!();
        const timeoutPromise = new Promise<null>((_, reject) => {
          setTimeout(() => reject(new Error('Token refresh timeout')), 3000);
        });
        
        const token = await Promise.race([tokenPromise, timeoutPromise]);
        
        if (token) {
          this.latestToken = token;
          this.tokenExpiry = this.getTokenExpiry(token);
          this.authFailureCount = 0;
          this.circuitBreakerOpen = false;
        } else {
          this.latestToken = null;
          this.tokenExpiry = null;
        }
      } catch (error: any) {
        console.error('[API] Token refresh failed:', error?.message || error);
        this.latestToken = null;
        this.tokenExpiry = null;
        // Don't open circuit breaker on token refresh failure - user might not be signed in
      } finally {
        // Clear the refresh promise so future calls can refresh again
        this.refreshPromise = null;
      }
    })();
 
    return this.refreshPromise;
  }

  // ------------------------
  // API methods
  // ------------------------

  /**
   * TASK C UPDATED: Added onProgress callback
   * Updated: Added pdfPassword parameter for password-protected PDFs
   */
  async uploadSource(file: File, title?: string, onProgress?: (percent: number) => void, pdfPassword?: string) {
    await this.refreshToken();
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (pdfPassword) formData.append('pdf_password', pdfPassword);

    // Use longer timeout for file uploads (5 minutes)
    const uploadTimeout = 5 * 60 * 1000; // 5 minutes in milliseconds

    const res = await this.client.post('/api/v1/ingest/upload', formData, {
      timeout: uploadTimeout,
      // Don't set Content-Type header - axios will set it automatically with boundary for FormData
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percentCompleted);
        }
      },
    });
    return res.data;
  }

  async listSources() {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/ingest/sources', {
      timeout: 60000, // Presign + DB; backend parallelizes presigns — allow headroom on slow networks
    });
    return res.data.sources ?? [];
  }

  async deleteSource(sourceId: string) {
    await this.refreshToken();
    await this.client.delete(`/api/v1/ingest/sources/${sourceId}`);
  }

  /** Admin: NCERT global corpus (requires admin role). */
  async listNcertGlobalDocuments(params?: {
    class_num?: number;
    subject?: string;
    status?: string;
    limit?: number;
  }) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/admin/ncert-global/documents', {
      params,
      timeout: 120000,
    });
    return res.data;
  }

  async uploadNcertGlobalDocument(formData: FormData) {
    await this.refreshToken();
    const res = await this.client.post('/api/v1/admin/ncert-global/documents', formData, {
      timeout: 10 * 60 * 1000,
      // Omit Content-Type so the browser sets multipart boundary automatically.
    });
    return res.data;
  }

  async deleteNcertGlobalDocument(documentId: string) {
    await this.refreshToken();
    await this.client.delete(`/api/v1/admin/ncert-global/documents/${documentId}`, {
      timeout: 120000,
    });
  }

  async listNcertGlobalIngestionRuns(params?: { document_id?: string; limit?: number }) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/admin/ncert-global/ingestion-runs', {
      params,
      timeout: 120000,
    });
    return res.data;
  }

  async getNcertGlobalIngestionRun(runId: string) {
    await this.refreshToken();
    const res = await this.client.get(`/api/v1/admin/ncert-global/ingestion-runs/${runId}`, {
      timeout: 120000,
    });
    return res.data;
  }

  async getNcertSubjectsByClass() {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/admin/ncert-global/subjects-by-class', {
      timeout: 120000,
    });
    return res.data as Record<string, string[]>;
  }

  async getNcertTutorFilters(params?: { class_num?: number; subject?: string }) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/chat/ncert-filters', {
      params,
      timeout: 30000,
    });
    return res.data as NcertTutorFiltersResponse;
  }

  // Streaming Chat
  async streamChat(
    message: string,
    history: any[],
    activeSourceIds: string[],
    onChunk: (text: string) => void,
    onCitation: (citation: any) => void,
    onDone: () => void,
    onError?: (error: string) => void,
    includeNcertGlobal?: boolean,
    ncertClass?: number,
    ncertSubject?: string,
    ncertChapterNo?: number,
    ncertChapterName?: string,
    forceWholeFileMapReduce?: boolean
  ) {
    await this.refreshToken();

    const tenantId = getTenantIdFromCookie();
    let retryCount = 0;
    const maxRetries = 3; // Increased retries for network resilience
    const retryableStatuses = [408, 429, 500, 502, 503, 504]; // Retryable HTTP statuses
    const retryDelay = (attempt: number) => Math.min(1000 * Math.pow(2, attempt), 10000); // Exponential backoff

    while (retryCount <= maxRetries) {
      let reader: ReadableStreamDefaultReader<Uint8Array> | null | undefined = null;
      let hasReceivedData = false;
      let hasReceivedText = false; // Track if we received any text chunks (separate from citations)
      let accumulatedText = '';

      try {
        // Create AbortController for timeout handling
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
          controller.abort();
        }, 120000); // 2 minute timeout for streaming

        // Task B.b: Get user ID from token for X-User-ID header
        const userId = extractUserIdFromToken(this.latestToken);
        
        // Build headers with all required headers
        const fetchHeaders: Record<string, string> = {
          'Content-Type': 'application/json',
          'x-tenant-id': tenantId,
        };
        
        // Task B.c: Include Authorization header when token is available
        if (this.latestToken) {
          fetchHeaders['Authorization'] = `Bearer ${this.latestToken}`;
        }
        
        // Task B.b: Include X-User-ID header when user ID is available
        if (userId) {
          fetchHeaders['x-user-id'] = userId;
        }

        const response = await fetch(
          `${this.client.defaults.baseURL}/api/v1/chat/stream`,
          {
            method: 'POST',
            headers: fetchHeaders,
            body: JSON.stringify({
              message,
              history,
              active_source_ids: activeSourceIds,
              include_ncert_global: Boolean(includeNcertGlobal),
              ncert_class: ncertClass ?? null,
              ncert_subject: ncertSubject?.trim() || null,
              ncert_chapter_no: ncertChapterNo ?? null,
              ncert_chapter_name: ncertChapterName?.trim() || null,
              force_whole_file_map_reduce: Boolean(forceWholeFileMapReduce),
            }),
            signal: controller.signal,
          }
        );

        // DEBUG: Log the request payload
        console.debug('[streamChat] Sending request to /api/v1/chat/stream:', {
          include_ncert_global: Boolean(includeNcertGlobal),
          active_source_ids: activeSourceIds,
          ncert_class: ncertClass,
          ncert_subject: ncertSubject,
        });

        clearTimeout(timeoutId);

        // Handle 401 Unauthorized - try refreshing token and retry once
        if (response.status === 401 && retryCount < maxRetries) {
          try {
            await this.refreshToken(true); // Force refresh
            retryCount++;
            // Small delay before retry
            await new Promise(resolve => setTimeout(resolve, retryDelay(retryCount - 1)));
            continue; // Retry the request
          } catch (err) {
            // Use standardized error handling
            const mockError = { response: { status: 401, data: {} } };
            const apiError = handleApiError(mockError);
            const errorMsg = getUserFriendlyMessage(apiError);
            
            if (onError) {
              onError(errorMsg);
            }
            if (this.logoutFunc) {
              await this.logoutFunc();
            }
            redirectToLogin();
            throw new Error(errorMsg);
          }
        }

        // Handle non-OK responses with standardized error handling
        if (!response.ok) {
          // Read error response
          const errorText = await response.text().catch(() => "");
          let errorData: any = {};
          
          try {
            errorData = errorText ? JSON.parse(errorText) : {};
          } catch (e) {
            // If not JSON, create a mock error object
            errorData = { detail: errorText || `Request failed with status ${response.status}` };
          }

          // Create a mock axios error for error handler
          const mockError = {
            response: {
              status: response.status,
              data: errorData,
              headers: response.headers,
            },
          };

          const apiError = handleApiError(mockError);
          const errorMessage = getUserFriendlyMessage(apiError);

          // Handle 403 Forbidden - show appropriate message
          if (response.status === 403) {
            if (onError) {
              onError(errorMessage);
            }
            throw new Error(errorMessage);
          }

          // Handle 429 Rate Limit - show retry message
          if (response.status === 429) {
            if (onError) {
              onError(errorMessage);
            }
            // If retryable and haven't exceeded max retries, retry
            if (retryCount < maxRetries) {
              retryCount++;
              const delay = apiError.retryAfter ? apiError.retryAfter * 1000 : retryDelay(retryCount - 1);
              await new Promise(resolve => setTimeout(resolve, delay));
              continue;
            }
            throw new Error(errorMessage);
          }

          // Handle 500 Server Error - show user-friendly message
          if (response.status >= 500) {
            if (retryCount < maxRetries) {
              retryCount++;
              await new Promise(resolve => setTimeout(resolve, retryDelay(retryCount - 1)));
              continue;
            }
            if (onError) {
              onError(errorMessage);
            }
            throw new Error(errorMessage);
          }

          // Handle other errors
          if (onError) {
            onError(errorMessage);
          }
          throw new Error(errorMessage);
        }

        // Success - stream the response
        reader = response.body?.getReader();
        if (!reader) {
          const errorMsg = 'Failed to get response stream';
          if (onError) {
            onError(errorMsg);
          }
          throw new Error(errorMsg);
        }

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          let readResult;
          try {
            readResult = await reader.read();
          } catch (readError: any) {
            // Handle network disconnection during streaming
            if (readError.name === 'AbortError' || readError.name === 'NetworkError' || readError.message?.includes('network')) {
              // If we've received some data, try to recover
              if (hasReceivedData && retryCount < maxRetries) {
                retryCount++;
                await new Promise(resolve => setTimeout(resolve, retryDelay(retryCount - 1)));
                break; // Break inner loop to retry
              } else {
                const errorMsg = 'Network connection lost. Please check your internet connection and try again.';
                if (onError) {
                  onError(errorMsg);
                }
                throw new Error(errorMsg);
              }
            }
            throw readError;
          }

          const { done, value } = readResult;
          
          hasReceivedData = true;
          
          // Decode chunk (handle partial UTF-8 sequences)
          if (!done && value) {
            try {
              buffer += decoder.decode(value, { stream: true });
            } catch (decodeError) {
              // Continue processing - try to decode remaining buffer
              try {
                buffer += decoder.decode(new Uint8Array(0), { stream: false });
              } catch (e) {
                // If still fails, skip this chunk
                buffer = '';
              }
              continue;
            }
          } else if (done && buffer) {
            // When done, decode any remaining buffer
            try {
              buffer += decoder.decode(new Uint8Array(0), { stream: false });
            } catch (e) {
              // Ignore decode errors on final flush
            }
          }

          // Process complete lines
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          let currentEventType: string | null = null;

          for (const line of lines) {
            // Handle SSE format: "event: type\ndata: payload\n\n"
            if (line.startsWith('event: ')) {
              // Extract event type
              currentEventType = line.replace('event: ', '').trim();
              continue;
            }

            if (line.startsWith('data: ')) {
              const payload = line.replace('data: ', '').trim();
              
              // Skip empty data or [DONE] markers
              if (!payload || payload === '[DONE]') {
                currentEventType = null; // Reset for next event
                continue;
              }

              // Use the event type we captured from the previous line
              if (!currentEventType) {
                // If we don't have an event type, try to parse payload as JSON with event field
                try {
                  const parsed = JSON.parse(payload);
                  if (parsed.event) {
                    currentEventType = parsed.event;
                  }
                } catch {
                  // Skip if we can't parse
                  continue;
                }
              }

              try {
                // Parse the data payload (it's JSON)
                const eventData = JSON.parse(payload);

                // Handle error events from server
                if (currentEventType === 'error') {
                  const errorMsg = eventData.error || eventData.data?.error || 'An error occurred during streaming';
                  if (onError) {
                    onError(errorMsg);
                  } else {
                    throw new Error(errorMsg);
                  }
                  return;
                }

                // Handle chunk events
                if (currentEventType === 'chunk') {
                  const text = eventData.text || eventData.data?.text;
                  // Only process non-empty text strings
                  if (text && typeof text === 'string' && text.trim()) {
                    hasReceivedText = true;
                    accumulatedText += text;
                    onChunk(text);
                  } else if (text !== undefined && text !== null) {
                    // Log if we receive a chunk but it's not valid text
                    console.warn('[Stream] Received chunk event but text is invalid:', { text, eventData });
                  }
                }

                // Handle citation events
                if (currentEventType === 'citation') {
                  const citation = eventData.data || eventData;
                  if (citation) {
                    onCitation(citation);
                  }
                }

                // Handle done event
                if (currentEventType === 'done') {
                  const doneText =
                    (eventData as any).final_output_text ||
                    (eventData as any).data?.final_output_text;
                  const tid =
                    (eventData as any).trace_id ||
                    (eventData as any).data?.trace_id;
                  if (tid && typeof tid === 'string') {
                    // Same id as uvicorn [PIPELINE_TRACE] line and API store
                    console.info(
                      '%c[Pipeline trace]%c ' +
                        tid +
                        '\nOpen: /analytics/pipeline?trace_id=' +
                        encodeURIComponent(tid),
                      'color:#38bdf8;font-weight:bold',
                      'color:inherit;font-weight:normal'
                    );
                  }
                  // Verify we received text content (citations alone don't count)
                  if (!hasReceivedText || accumulatedText.trim() === '') {
                    // Fallback: if server included final text in done payload, use it.
                    if (doneText && typeof doneText === 'string' && doneText.trim()) {
                      hasReceivedText = true;
                      accumulatedText = doneText;
                      onChunk(doneText);
                      onDone();
                      return;
                    }
                    // Log for debugging
                    console.warn('[Stream] Done event received but no text was received:', {
                      hasReceivedText,
                      accumulatedTextLength: accumulatedText.length,
                      accumulatedTextPreview: accumulatedText.substring(0, 100),
                    });
                    if (onError) {
                      onError('Stream completed but no text response was received. The model may have been blocked or encountered an error. Please try again.');
                    }
                    return;
                  }
                  onDone();
                  return;
                }

                // Reset event type after processing
                currentEventType = null;
              } catch (parseError: any) {
                // Edge case: malformed JSON - continue processing
                currentEventType = null;
                continue;
              }
            } else if (line.trim() === '') {
              // Empty line indicates end of SSE event, reset event type
              currentEventType = null;
            }
          }
          
          // After processing all lines, if stream is done, check if we received text
          if (done) {
            // Handle empty response edge case (no text received)
            // Only check if we haven't already received a 'done' event (which would have returned)
            if (!hasReceivedText || accumulatedText.trim() === '') {
              if (onError) {
                onError('Received empty text response from server. The model may have been blocked or encountered an error. Please try again.');
              } else {
                throw new Error('Received empty text response from server. Please try again.');
              }
              return;
            }
            break;
          }
        }

        // If we exit the loop normally (not via return), check if we need to retry
        if (reader && !hasReceivedData && retryCount < maxRetries) {
          retryCount++;
          await new Promise(resolve => setTimeout(resolve, retryDelay(retryCount - 1)));
          continue; // Retry
        }

        // Successfully completed
        return;

      } catch (error: any) {
        // Clean up reader if it exists
        if (reader) {
          try {
            await reader.cancel();
          } catch (cancelError) {
            // Ignore cancel errors
          }
        }

        // Use standardized error handling
        const apiError = handleApiError(error);
        const errorMessage = getUserFriendlyMessage(apiError);

        // Handle network and timeout errors with retry
        if ((apiError.type === ErrorType.NETWORK || apiError.type === ErrorType.TIMEOUT) && 
            apiError.retryable && 
            retryCount < maxRetries) {
          retryCount++;
          await new Promise(resolve => setTimeout(resolve, retryDelay(retryCount - 1)));
          continue; // Retry
        }

        // All retries exhausted or non-retryable error
        if (onError) {
          onError(errorMessage);
        } else {
          throw new Error(errorMessage);
        }
        return;
      }
    }

    // If we've exhausted all retries
    const mockError = { response: null, message: 'Failed to connect after multiple attempts' };
    const apiError = handleApiError(mockError);
    const finalError = getUserFriendlyMessage(apiError);
    if (onError) {
      onError(finalError);
    } else {
      throw new Error(finalError);
    }
  }

  async generateStudio(
    taskType: string,
    sourceIds: string[],
    instructions?: string,
    retrievalFocus?: string,
    reportFormat?: StudioReportFormat
  ) {
    await this.refreshToken();
    const body: Record<string, unknown> = {
      task_type: taskType,
      source_ids: sourceIds,
      custom_instructions: instructions,
    };
    if (retrievalFocus && retrievalFocus.trim()) {
      body.retrieval_focus = retrievalFocus.trim();
    }
    if (taskType === 'report' && reportFormat) {
      body.report_format = reportFormat;
    }
    // Use longer timeout for AI generation (60 seconds) as it can take time
    const res = await this.client.post('/api/v1/studio/generate', body, {
      timeout: 60000, // 60 seconds for AI generation
    });
    return res.data;
  }

  async createNote(content: string, sourceRefId?: string) {
    await this.refreshToken();
    const res = await this.client.post('/api/v1/notes', {
      content,
      source_ref_id: sourceRefId,
    });
    return res.data;
  }

  async listNotes() {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/notes', {
      timeout: 30000,
    });
    return res.data.notes ?? [];
  }

  async deleteNote(noteId: string) {
    await this.refreshToken();
    await this.client.delete(`/api/v1/notes/${noteId}`);
  }

  async updateNote(noteId: string, content: string) {
    await this.refreshToken();
    const res = await this.client.put(`/api/v1/notes/${noteId}`, {
      content,
    });
    return res.data;
  }

  async getNote(noteId: string) {
    await this.refreshToken();
    const res = await this.client.get(`/api/v1/notes/${noteId}`);
    return res.data;
  }

  // Task C: Chat History Methods

  async createChat(title?: string) {
    await this.refreshToken();
    const res = await this.client.post('/api/v1/chat', {
      title: title || null,
    });
    return res.data;
  }

  async listChats(limit: number = 50, offset: number = 0) {
    await this.refreshToken();
    // Cold DB / first request after server start can exceed a short timeout; align with getChat.
    const res = await this.client.get('/api/v1/chat', {
      params: { limit, offset },
      timeout: 30000,
    });
    return res.data;
  }

  async getChat(chatId: string) {
    await this.refreshToken();
    const res = await this.client.get(`/api/v1/chat/${chatId}`, {
      timeout: 60000,
    });
    return res.data;
  }

  async updateChatTitle(chatId: string, title: string) {
    await this.refreshToken();
    const res = await this.client.patch(`/api/v1/chat/${chatId}`, {
      title,
    });
    return res.data;
  }

  async deleteChat(chatId: string) {
    await this.refreshToken();
    // Use longer timeout for delete operations (30 seconds) in case there are many messages to cascade delete
    const res = await this.client.delete(`/api/v1/chat/${chatId}`, {
      timeout: 30000, // 30 seconds
    });
    return res.data;
  }

  async addMessageToChat(
    chatId: string,
    role: 'user' | 'assistant',
    content: string,
    citations?: any[]
  ) {
    await this.refreshToken();
    const res = await this.client.post(
      `/api/v1/chat/${chatId}/messages`,
      {
        role,
        content,
        citations: citations || [],
      },
      {
        // Saving assistant messages can be slower than streaming completion,
        // especially if the DB is cold or briefly unavailable.
        timeout: 45000,
      }
    );
    return res.data;
  }

  async deleteAllMessages(chatId: string) {
    await this.refreshToken();
    const res = await this.client.delete(`/api/v1/chat/${chatId}/messages`, {
      timeout: 30000,
    });
    return res.data;
  }

  async summarizeChat(chatId: string) {
    await this.refreshToken();
    const res = await this.client.post(
      `/api/v1/chat/${chatId}/summarize`,
      {},
      {
        timeout: 60000,
      }
    );
    return res.data;
  }

  async updateMessageFeedback(
    messageId: string,
    feedback: 'thumbs_up' | 'thumbs_down' | null
  ) {
    await this.refreshToken();
    const res = await this.client.patch(`/api/v1/chat/messages/${messageId}/feedback`, {
      feedback,
    });
    return res.data;
  }

  // Admin methods
  async listAllUsers() {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/admin/users', {
      timeout: 30000, // Admin/Clerk + DB merge can be slow
    });
    return res.data;
  }

  async getPipelineTrace(traceId: string) {
    await this.refreshToken();
    const res = await this.client.get(`/api/v1/pipeline-traces/${encodeURIComponent(traceId)}`);
    return res.data;
  }

  async getPipelineTraceExplain(traceId: string) {
    await this.refreshToken();
    const res = await this.client.get(`/api/v1/pipeline-traces/${encodeURIComponent(traceId)}/explain`, {
      timeout: 30000,
    });
    return res.data;
  }

  async listPipelineTracesRecent(limit: number = 30) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/pipeline-traces/recent', {
      params: { limit },
      timeout: 15000,
    });
    return res.data;
  }

  /** Always 200 when logged in; no 403 — safe for admin UI detection. */
  async getMyAdminFlags() {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/admin/me/flags');
    return res.data as { is_admin: boolean };
  }

  async getAggregateMetrics(days: number = 30, silent: boolean = false) {
    await this.refreshToken();
    const config: any = {
      params: { days },
      timeout: 30000, // 30 second timeout for metrics queries
    };
    if (silent) {
      config._expected403 = true; // Mark as expected 403 to suppress error logging
    }
    const res = await this.client.get('/api/v1/admin/aggregate', config);
    return res.data;
  }

  async getMyMetrics(days: number = 30) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/admin/me/metrics', {
      params: { days },
      timeout: 30000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getUserMetrics(userId: string, days: number = 30) {
    await this.refreshToken();
    const res = await this.client.get(`/api/v1/admin/users/${userId}/metrics`, {
      params: { days },
      timeout: 30000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getUserSessions(userId: string, days: number = 30) {
    await this.refreshToken();
    const res = await this.client.get(`/api/v1/admin/users/${userId}/sessions`, {
      params: { days },
      timeout: 30000, // 30 second timeout for session queries
    });
    return res.data;
  }

  async getTokenConsumption(days: number = 30, groupBy: string = 'feature') {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/token-consumption', {
      params: { days, group_by: groupBy },
      timeout: 30000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getCostTracking(days: number = 30, groupByUser: boolean = false) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/cost-tracking', {
      params: { days, group_by_user: groupByUser },
      timeout: 30000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getLatencyDashboard(days: number = 30) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/latency', {
      params: { days },
      timeout: 30000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getCacheEfficiency(days: number = 30) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/cache-efficiency', {
      params: { days },
    });
    return res.data;
  }

  async getRagQuality(days: number = 30) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/rag-quality', {
      params: { days },
    });
    return res.data;
  }

  async getAgentSummary(days: number = 30, compareDays: number = 30) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/agents/summary', {
      params: { days, compare_days: compareDays },
      timeout: 30000,
    });
    return res.data;
  }

  async getAgentDetails(days: number = 30) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/agents/details', {
      params: { days },
      timeout: 30000,
    });
    return res.data;
  }

  async getAgentTimeseries(days: number = 30) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/agents/timeseries', {
      params: { days },
      timeout: 30000,
    });
    return res.data;
  }

  async getAgentRecent(limit: number = 50) {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/agents/recent', {
      params: { limit },
      timeout: 30000,
    });
    return res.data;
  }

  async downloadAgentCsv(days: number = 30): Promise<Blob> {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/metrics/agents/export.csv', {
      params: { days },
      responseType: 'blob',
      timeout: 30000,
    });
    return res.data as Blob;
  }

  async getAlertsStatus() {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/alerts/status');
    return res.data;
  }

  async getLogs(days: number = 7, limit: number = 1000, eventType?: string) {
    await this.refreshToken();
    const params: any = { days, limit };
    if (eventType) {
      params.event_type = eventType;
    }
    const res = await this.client.get('/api/v1/metrics/logs', {
      params,
      timeout: 30000,
    });
    return res.data;
  }
}

const apiClient = new ApiClient();

export { apiClient };
export default apiClient;
