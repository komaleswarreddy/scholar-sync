import axios, {
  AxiosInstance,
  AxiosRequestHeaders,
  InternalAxiosRequestConfig, 
} from 'axios';
import { handleApiError, redirectToLogin, getUserFriendlyMessage, ApiError, ErrorType } from './error-handler';
import { clearAdminSession, getAdminToken, redirectToAdminLogin, setAdminToken } from './admin-auth';

type TokenGetter = () => Promise<string | null>;
type LogoutFunc = () => Promise<void>;

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
  private adminPortalMode: boolean = false;

  constructor(
    baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  ) {
    this.client = axios.create({
      baseURL,
      timeout: 12000, // Default; uploads/streams/studio use longer per-request timeouts
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

        // Refresh JWT when missing or near expiry (single path for all API methods)
        if (!this.circuitBreakerOpen && this.getTokenFunc && (!this.latestToken || this.isTokenExpired())) {
          try {
            await this.refreshToken(true);
          } catch (e) {
            // Ignore token refresh errors
          }
        }

        if (this.circuitBreakerOpen) {
          delete headers['Authorization'];
        } else if (this.latestToken) {
          headers['Authorization'] = `Bearer ${this.latestToken}`;
        }

        const tenantId = getTenantIdFromCookie();
        headers['x-tenant-id'] = tenantId;

        const userId = extractUserIdFromToken(this.latestToken);
        if (userId) {
          headers['x-user-id'] = userId;
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
            if (this.adminPortalMode) {
              clearAdminSession();
              this.clearAuthSession();
              redirectToAdminLogin();
            } else {
              redirectToLogin();
            }
            
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
            if (this.adminPortalMode) {
              clearAdminSession();
              this.clearAuthSession();
              redirectToAdminLogin();
            } else {
              redirectToLogin();
            }
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
    if (this.adminPortalMode) return;
    this.getTokenFunc = getTokenFunc;
    this.refreshToken();
  }

  /** Use admin portal JWT from sessionStorage for API calls (ops dashboard). */
  setAdminPortalMode(enabled: boolean) {
    this.adminPortalMode = enabled;
    if (enabled) {
      this.getTokenFunc = async () => getAdminToken();
      const token = getAdminToken();
      if (token) {
        this.latestToken = token;
        this.tokenExpiry = this.getTokenExpiry(token);
      }
    }
  }

  setLogoutHandler(logoutFunc: LogoutFunc) {
    this.logoutFunc = logoutFunc;
  }

  /** Drop cached JWT and auth failure state (e.g. after sign-out). */
  clearAuthSession() {
    this.latestToken = null;
    this.tokenExpiry = null;
    this.authFailureCount = 0;
    this.circuitBreakerOpen = false;
    this.refreshPromise = null;
    if (this.adminPortalMode) {
      this.adminPortalMode = false;
    }
  }

  async adminLogin(email: string, password: string): Promise<void> {
    const tenantId = getTenantIdFromCookie();
    const res = await this.client.post(
      '/api/v1/admin/auth/login',
      { email, password },
      {
        headers: {
          'Content-Type': 'application/json',
          'x-tenant-id': tenantId,
        },
      }
    );
    const accessToken = res.data?.access_token as string | undefined;
    if (!accessToken) {
      throw new Error('Login succeeded but no access token was returned');
    }
    setAdminToken(accessToken);
    this.setAdminPortalMode(true);
    this.latestToken = accessToken;
    this.tokenExpiry = this.getTokenExpiry(accessToken);
    this.authFailureCount = 0;
    this.circuitBreakerOpen = false;
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
  async uploadSource(
    file: File,
    title?: string,
    onProgress?: (percent: number) => void,
    pdfPassword?: string,
    notebookId?: string,
  ) {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (pdfPassword) formData.append('pdf_password', pdfPassword);
    if (notebookId) formData.append('notebook_id', notebookId);

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

  async listSources(notebookId?: string) {
    const res = await this.client.get('/api/v1/ingest/sources', {
      params: notebookId ? { notebook_id: notebookId } : undefined,
      timeout: 60000, // Presign + DB; backend parallelizes presigns — allow headroom on slow networks
    });
    return res.data.sources ?? [];
  }

  async deleteSource(sourceId: string) {
    await this.client.delete(`/api/v1/ingest/sources/${sourceId}`);
  }

  async listSourceQuestions(sourceId: string) {
    const res = await this.client.get(`/api/v1/ingest/sources/${sourceId}/questions`, {
      timeout: 60000,
    });
    return res.data;
  }

  async extractSourceQuestions(sourceId: string, force = false) {
    const res = await this.client.post(
      `/api/v1/ingest/sources/${sourceId}/extract-questions`,
      {},
      { params: force ? { force: true } : undefined, timeout: 30000 },
    );
    return res.data;
  }

  async getSourceQuestion(sourceId: string, questionId: string) {
    const res = await this.client.get(
      `/api/v1/ingest/sources/${sourceId}/questions/${questionId}`,
      { timeout: 60000 },
    );
    return res.data;
  }

  /** Admin: NCERT global corpus (requires admin role). */
  async listNcertGlobalDocuments(params?: {
    class_num?: number;
    subject?: string;
    status?: string;
    limit?: number;
  }) {
    const res = await this.client.get('/api/v1/admin/ncert-global/documents', {
      params,
      timeout: 120000,
    });
    return res.data;
  }

  async uploadNcertGlobalDocument(formData: FormData) {
    const res = await this.client.post('/api/v1/admin/ncert-global/documents', formData, {
      timeout: 10 * 60 * 1000,
      // Omit Content-Type so the browser sets multipart boundary automatically.
    });
    return res.data;
  }

  async deleteNcertGlobalDocument(documentId: string) {
    await this.client.delete(`/api/v1/admin/ncert-global/documents/${documentId}`, {
      timeout: 120000,
    });
  }

  async listNcertGlobalIngestionRuns(params?: { document_id?: string; limit?: number }) {
    const res = await this.client.get('/api/v1/admin/ncert-global/ingestion-runs', {
      params,
      timeout: 120000,
    });
    return res.data;
  }

  async getNcertGlobalIngestionRun(runId: string) {
    const res = await this.client.get(`/api/v1/admin/ncert-global/ingestion-runs/${runId}`, {
      timeout: 120000,
    });
    return res.data;
  }

  async getNcertSubjectsByClass() {
    const res = await this.client.get('/api/v1/admin/ncert-global/subjects-by-class', {
      timeout: 120000,
    });
    return res.data as Record<string, string[]>;
  }

  async getNcertTutorFilters(params?: { class_num?: number; subject?: string }) {
    const res = await this.client.get('/api/v1/chat/ncert-filters', {
      params,
      timeout: 15000,
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
    forceWholeFileMapReduce?: boolean,
    ncertConcept?: string
  ) {
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
              ncert_concept: ncertConcept?.trim() || null,
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
                  if (typeof text === 'string' && text.length > 0) {
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
                        '\nOpen: /admin/pipeline?trace_id=' +
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
    studioExtras?: {
      contextMode?: 'sources_only' | 'chat_hybrid' | 'selection_only';
      chatTranscript?: string;
      selectionText?: string;
      include_ncert_global?: boolean;
      ncert_class?: number;
      ncert_subject?: string;
      ncert_chapter_no?: number;
      ncert_chapter_name?: string;
    },
    options?: { timeoutMs?: number }
  ) {
    const body: Record<string, unknown> = {
      task_type: taskType,
      source_ids: sourceIds,
      custom_instructions: instructions,
    };
    if (studioExtras?.contextMode) {
      body.context_mode = studioExtras.contextMode;
    }
    if (studioExtras?.chatTranscript != null && studioExtras.chatTranscript.trim()) {
      body.chat_transcript = studioExtras.chatTranscript.trim();
    }
    if (studioExtras?.selectionText != null && studioExtras.selectionText.trim()) {
      body.selection_text = studioExtras.selectionText.trim();
    }
    if (studioExtras?.include_ncert_global) {
      body.include_ncert_global = true;
      if (studioExtras.ncert_class != null) {
        body.ncert_class = studioExtras.ncert_class;
      }
      if (studioExtras.ncert_subject) {
        body.ncert_subject = studioExtras.ncert_subject;
      }
      if (studioExtras.ncert_chapter_no != null) {
        body.ncert_chapter_no = studioExtras.ncert_chapter_no;
      }
      if (studioExtras.ncert_chapter_name) {
        body.ncert_chapter_name = studioExtras.ncert_chapter_name;
      }
    }
    if (retrievalFocus && retrievalFocus.trim()) {
      body.retrieval_focus = retrievalFocus.trim();
    }
    // Use longer timeout for AI generation; tutor bootstrap prep may pass extended limits.
    const timeoutMs = options?.timeoutMs ?? 60000;
    const res = await this.client.post('/api/v1/studio/generate', body, {
      timeout: timeoutMs,
    });
    return res.data;
  }

  async createNote(content: string, sourceRefId?: string, notebookId?: string) {
    const res = await this.client.post('/api/v1/notes', {
      content,
      source_ref_id: sourceRefId,
      notebook_id: notebookId,
    });
    return res.data;
  }

  async listNotes(notebookId?: string) {
    const res = await this.client.get('/api/v1/notes', {
      params: notebookId ? { notebook_id: notebookId } : undefined,
      timeout: 15000,
    });
    return res.data.notes ?? [];
  }

  async deleteNote(noteId: string) {
    await this.client.delete(`/api/v1/notes/${noteId}`);
  }

  async updateNote(noteId: string, content: string) {
    const res = await this.client.put(`/api/v1/notes/${noteId}`, {
      content,
    });
    return res.data;
  }

  async getNote(noteId: string) {
    const res = await this.client.get(`/api/v1/notes/${noteId}`);
    return res.data;
  }

  // Task C: Chat History Methods

  async createChat(title?: string, notebookId?: string) {
    const res = await this.client.post('/api/v1/chat', {
      title: title || null,
      notebook_id: notebookId,
    });
    return res.data;
  }

  async listChats(limit: number = 50, offset: number = 0, notebookId?: string) {
    // Cold DB / first request after server start can exceed a short timeout; align with getChat.
    const res = await this.client.get('/api/v1/chat', {
      params: {
        limit,
        offset,
        ...(notebookId ? { notebook_id: notebookId } : {}),
      },
      timeout: 15000,
    });
    return res.data;
  }

  async createNotebook(
    payload: {
      title?: string;
      mode?: string;
      class_level?: string;
      subject?: string;
      focus?: string;
      settings?: Record<string, unknown>;
    },
    options?: { timeoutMs?: number },
  ) {
    const res = await this.client.post(
      '/api/v1/notebooks',
      {
        title: payload.title || 'Untitled notebook',
        mode: payload.mode || 'exploratory',
        class_level: payload.class_level ?? null,
        subject: payload.subject ?? null,
        focus: payload.focus ?? null,
        settings: payload.settings ?? null,
      },
      { timeout: options?.timeoutMs ?? 120000 },
    );
    return res.data;
  }

  async getTutorCatalog(params: {
    class_num: number;
    subject?: string;
    chapter_no?: number;
  }) {
    const res = await this.client.get('/api/v1/tutor/catalog', { params, timeout: 15000 });
    return res.data as {
      subjects?: Array<{
        id: string;
        label: string;
        icon: string;
        chapter_count: number;
        subject_slug: string;
        subsubject?: string | null;
      }>;
      chapters?: Array<{
        chapter_no: number;
        title: string;
        chapter_title?: string;
        filter_chapter_name?: string | null;
        subject_slug?: string;
        ncert_document_id?: string | null;
        chunks_count?: number;
        summary?: string | null;
        featured_count: number;
        concept_count: number;
        is_featured_chapter: boolean;
        indexed: boolean;
        ingest_status: string;
      }>;
      concepts?: Array<{ id: string; label: string }>;
    };
  }

  async getTutorFeaturedNotebooks(params: {
    class_num: number;
    subject: string;
    chapter_no: number;
  }) {
    const res = await this.client.get('/api/v1/tutor/featured-notebooks', {
      params,
      timeout: 15000,
    });
    return res.data as {
      notebooks: Array<{
        id: string;
        title: string;
        slug: string;
        focus?: string | null;
        mastery_percent?: number | null;
      }>;
    };
  }

  async bootstrapTutorNotebook(notebookId: string, options?: { timeoutMs?: number }) {
    const res = await this.client.post(
      `/api/v1/tutor/notebooks/${encodeURIComponent(notebookId)}/bootstrap`,
      {},
      { timeout: options?.timeoutMs ?? 180000 },
    );
    return res.data;
  }

  async prepareTutorNotebook(
    payload: {
      title: string;
      class_level?: string;
      subject?: string;
      focus?: string;
      tutor_scope: Record<string, unknown>;
    },
    options?: { timeoutMs?: number; signal?: AbortSignal },
  ) {
    const res = await this.client.post('/api/v1/tutor/notebooks/prepare', payload, {
      timeout: options?.timeoutMs ?? 180000,
      signal: options?.signal,
    });
    return res.data as {
      notebook_id: string;
      slug: string;
      opening_summary: string;
      suggestions: Array<{ label: string; prompt: string }>;
      studio_recommendations: Array<{
        type: string;
        reason?: string;
        auto_generate?: boolean;
      }>;
      chat_id?: string | null;
      assets_created: number;
      assets: Array<{ id: string; type: string; title: string }>;
      auto_types: string[];
      timing: {
        create_notebook_ms: number;
        ncert_retrieval_ms: number;
        ncert_cache_hit: number;
        bootstrap_llm_ms: number;
        studio_parallel_ms: number;
        persist_ms: number;
        total_ms: number;
      };
      partial_failure: boolean;
    };
  }

  async warmTutorNcertContext(tutorScope: Record<string, unknown>) {
    const res = await this.client.post(
      '/api/v1/tutor/ncert-context/warm',
      { tutor_scope: tutorScope },
      { timeout: 60000 },
    );
    return res.data as {
      ok: boolean;
      cached: boolean;
      context_chars: number;
      duration_ms: number;
    };
  }

  async getTutorFollowUps(payload: {
    notebook_id: string;
    user_message: string;
    assistant_message: string;
  }) {
    const res = await this.client.post('/api/v1/tutor/follow-ups', payload, { timeout: 15000 });
    return res.data as { follow_ups: string[] };
  }

  async markTutorStudioGenerationStarted(notebookId: string) {
    const res = await this.client.post(
      `/api/v1/tutor/notebooks/${encodeURIComponent(notebookId)}/studio-generation-started`,
      {},
    );
    return res.data;
  }

  async listNotebooks() {
    const res = await this.client.get('/api/v1/notebooks', { timeout: 15000 });
    return res.data;
  }

  async getNotebookBySlug(slug: string) {
    const res = await this.client.get(`/api/v1/notebooks/by-slug/${encodeURIComponent(slug)}`, {
      timeout: 15000,
    });
    return res.data;
  }

  async updateNotebook(
    notebookId: string,
    payload: {
      title?: string;
      subtitle?: string;
      focus?: string;
      settings?: Record<string, unknown>;
      touch_last_studied?: boolean;
    },
  ) {
    const res = await this.client.patch(`/api/v1/notebooks/${notebookId}`, payload);
    return res.data;
  }

  async listStudioFeatures(params?: {
    notebook_id?: string;
    type?: string;
    limit?: number;
  }) {
    const res = await this.client.get('/api/v1/studio/features', {
      params,
      timeout: 15000,
    });
    return res.data;
  }

  async createStudioFeature(payload: {
    notebook_id: string;
    type: string;
    title: string;
    content: unknown;
    source_ids?: string[];
  }) {
    const res = await this.client.post('/api/v1/studio/features', payload);
    return res.data;
  }

  async deleteStudioFeature(featureId: string) {
    const res = await this.client.delete(`/api/v1/studio/features/${featureId}`);
    return res.data;
  }

  async getHomeSummary() {
    const res = await this.client.get('/api/v1/home/summary', { timeout: 15000 });
    return res.data;
  }

  async getChat(chatId: string) {
    const res = await this.client.get(`/api/v1/chat/${chatId}`, {
      timeout: 60000,
    });
    return res.data;
  }

  async updateChatTitle(chatId: string, title: string) {
    const res = await this.client.patch(`/api/v1/chat/${chatId}`, {
      title,
    });
    return res.data;
  }

  async deleteChat(chatId: string) {
    // Use longer timeout for delete operations (30 seconds) in case there are many messages to cascade delete
    const res = await this.client.delete(`/api/v1/chat/${chatId}`, {
      timeout: 15000, // 30 seconds
    });
    return res.data;
  }

  async addMessageToChat(
    chatId: string,
    role: 'user' | 'assistant',
    content: string,
    citations?: any[]
  ) {
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
    const res = await this.client.delete(`/api/v1/chat/${chatId}/messages`, {
      timeout: 15000,
    });
    return res.data;
  }

  async summarizeChat(chatId: string) {
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
    feedback: 'thumbs_up' | 'thumbs_down' | null,
    feedbackReason?: string | null
  ) {
    const res = await this.client.patch(`/api/v1/chat/messages/${messageId}/feedback`, {
      feedback,
      feedback_reason: feedbackReason ?? null,
    });
    return res.data;
  }

  // Admin methods
  async listAllUsers() {
    const res = await this.client.get('/api/v1/admin/users', {
      timeout: 15000, // Admin/Clerk + DB merge can be slow
    });
    return res.data;
  }

  async getPipelineTrace(traceId: string) {
    const res = await this.client.get(`/api/v1/pipeline-traces/${encodeURIComponent(traceId)}`);
    return res.data;
  }

  async getPipelineTraceExplain(traceId: string) {
    const res = await this.client.get(`/api/v1/pipeline-traces/${encodeURIComponent(traceId)}/explain`, {
      timeout: 15000,
    });
    return res.data;
  }

  async listPipelineTracesRecent(limit: number = 30) {
    const res = await this.client.get('/api/v1/pipeline-traces/recent', {
      params: { limit },
      timeout: 15000,
    });
    return res.data;
  }

  /** Always 200 when logged in; no 403 — safe for admin UI detection. */
  async getMyAdminFlags() {
    const res = await this.client.get('/api/v1/admin/me/flags');
    return res.data as { is_admin: boolean };
  }

  async getAggregateMetrics(days: number = 30, silent: boolean = false) {
    const config: any = {
      params: { days },
      timeout: 15000, // 30 second timeout for metrics queries
    };
    if (silent) {
      config._expected403 = true; // Mark as expected 403 to suppress error logging
    }
    const res = await this.client.get('/api/v1/admin/aggregate', config);
    return res.data;
  }

  async getMyMetrics(days: number = 30) {
    const res = await this.client.get('/api/v1/admin/me/metrics', {
      params: { days },
      timeout: 15000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getUserMetrics(userId: string, days: number = 30) {
    const res = await this.client.get(`/api/v1/admin/users/${userId}/metrics`, {
      params: { days },
      timeout: 15000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getUserSessions(userId: string, days: number = 30) {
    const res = await this.client.get(`/api/v1/admin/users/${userId}/sessions`, {
      params: { days },
      timeout: 15000, // 30 second timeout for session queries
    });
    return res.data;
  }

  async getTokenConsumption(days: number = 30, groupBy: string = 'feature') {
    const res = await this.client.get('/api/v1/metrics/token-consumption', {
      params: { days, group_by: groupBy },
      timeout: 15000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getCostTracking(days: number = 30, groupByUser: boolean = false) {
    const res = await this.client.get('/api/v1/metrics/cost-tracking', {
      params: { days, group_by_user: groupByUser },
      timeout: 15000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getLatencyDashboard(days: number = 30) {
    const res = await this.client.get('/api/v1/metrics/latency', {
      params: { days },
      timeout: 15000, // 30 second timeout for metrics queries
    });
    return res.data;
  }

  async getCacheEfficiency(days: number = 30) {
    const res = await this.client.get('/api/v1/metrics/cache-efficiency', {
      params: { days },
    });
    return res.data;
  }

  async getRagQuality(days: number = 30) {
    const res = await this.client.get('/api/v1/metrics/rag-quality', {
      params: { days },
    });
    return res.data;
  }

  async getAgentSummary(days: number = 30, compareDays: number = 30) {
    const res = await this.client.get('/api/v1/metrics/agents/summary', {
      params: { days, compare_days: compareDays },
      timeout: 15000,
    });
    return res.data;
  }

  async getAgentDetails(days: number = 30) {
    const res = await this.client.get('/api/v1/metrics/agents/details', {
      params: { days },
      timeout: 15000,
    });
    return res.data;
  }

  async getAgentTimeseries(days: number = 30) {
    const res = await this.client.get('/api/v1/metrics/agents/timeseries', {
      params: { days },
      timeout: 15000,
    });
    return res.data;
  }

  async getAgentRecent(limit: number = 50) {
    const res = await this.client.get('/api/v1/metrics/agents/recent', {
      params: { limit },
      timeout: 15000,
    });
    return res.data;
  }

  async downloadAgentCsv(days: number = 30): Promise<Blob> {
    const res = await this.client.get('/api/v1/metrics/agents/export.csv', {
      params: { days },
      responseType: 'blob',
      timeout: 15000,
    });
    return res.data as Blob;
  }

  async getAlertsStatus() {
    const res = await this.client.get('/api/v1/alerts/status');
    return res.data;
  }

  async getLogs(days: number = 7, limit: number = 1000, eventType?: string) {
    const params: any = { days, limit };
    if (eventType) {
      params.event_type = eventType;
    }
    const res = await this.client.get('/api/v1/metrics/logs', {
      params,
      timeout: 15000,
    });
    return res.data;
  }

  // ── Problem Solver ────────────────────────────────────────────────────────

  async createProblemSolverSession(payload: {
    notebook_id: string;
    problem_text: string;
    input_type?: string;
    source_refs?: Array<Record<string, unknown>>;
  }) {
    const res = await this.client.post('/api/v1/problem-solver/sessions', payload, {
      timeout: 120000,
    });
    return res.data;
  }

  async getActiveProblemSolverSession(notebookId: string) {
    try {
      const res = await this.client.get(`/api/v1/problem-solver/sessions/active/${notebookId}`, {
        timeout: 15000,
        validateStatus: (status) => status === 200 || status === 404,
      });
      if (res.status === 404) return null;
      return res.data ?? null;
    } catch {
      return null;
    }
  }

  async getProblemSolverSession(sessionId: string) {
    const res = await this.client.get(`/api/v1/problem-solver/sessions/${sessionId}`, {
      timeout: 15000,
    });
    return res.data;
  }

  async extractProblemSolverFromSource(sourceId: string) {
    const res = await this.client.post(
      '/api/v1/problem-solver/extract-from-source',
      { source_id: sourceId },
      { timeout: 120000 },
    );
    return res.data as { normalized_text: string };
  }

  async selectProblemSolverMode(sessionId: string, solvingMode: string) {
    const res = await this.client.post(
      `/api/v1/problem-solver/sessions/${sessionId}/mode`,
      { solving_mode: solvingMode },
      { timeout: 30000 },
    );
    return res.data;
  }

  async submitProblemSolverCheckpoint(
    sessionId: string,
    checkpointNumber: number,
    selectedOption: string,
  ) {
    const res = await this.client.post(
      `/api/v1/problem-solver/sessions/${sessionId}/checkpoint`,
      { checkpoint_number: checkpointNumber, selected_option: selectedOption },
      { timeout: 120000 },
    );
    return res.data;
  }

  async triggerProblemSolverFollowUp(
    sessionId: string,
    action: string,
    userFollowUp?: string,
  ) {
    const res = await this.client.post(
      `/api/v1/problem-solver/sessions/${sessionId}/follow-up`,
      { action, user_follow_up: userFollowUp ?? null },
      { timeout: 120000 },
    );
    return res.data;
  }

  async resetProblemSolverSession(notebookId: string) {
    const res = await this.client.post(
      `/api/v1/problem-solver/sessions/reset/${notebookId}`,
      {},
      { timeout: 30000 },
    );
    return res.data;
  }

  async streamProblemSolverResponse(
    sessionId: string,
    handlers: {
      onStart?: (data: { title?: string; mode?: string }) => void;
      onSection?: (data: { index: number; heading?: string; bodyMarkdown?: string }) => void;
      onDone?: (data: Record<string, unknown>) => void;
      onError?: (message: string) => void;
    },
  ) {
    const tenantId = getTenantIdFromCookie();
    const userId = extractUserIdFromToken(this.latestToken);
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'x-tenant-id': tenantId,
    };
    if (this.latestToken) {
      headers.Authorization = `Bearer ${this.latestToken}`;
    }
    if (userId) {
      headers['x-user-id'] = userId;
    }

    const response = await fetch(
      `${this.client.defaults.baseURL}/api/v1/problem-solver/sessions/${sessionId}/respond/stream`,
      { method: 'POST', headers },
    );

    if (!response.ok) {
      const errText = await response.text().catch(() => 'Stream failed');
      handlers.onError?.(errText || `HTTP ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      handlers.onError?.('No response stream');
      return;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() ?? '';

      for (const part of parts) {
        const lines = part.split('\n');
        let eventType = 'message';
        let dataStr = '';
        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            dataStr += line.slice(5).trim();
          }
        }
        if (!dataStr) continue;
        try {
          const data = JSON.parse(dataStr);
          if (eventType === 'start') handlers.onStart?.(data);
          else if (eventType === 'section') handlers.onSection?.(data);
          else if (eventType === 'done') handlers.onDone?.(data);
          else if (eventType === 'error') handlers.onError?.(data.error || 'Stream error');
        } catch {
          handlers.onError?.('Failed to parse stream event');
        }
      }
    }
  }
}

const apiClient = new ApiClient();

export { apiClient };
export default apiClient;
