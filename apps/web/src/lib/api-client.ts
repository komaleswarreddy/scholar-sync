import axios, {
  AxiosInstance,
  AxiosRequestHeaders,
  InternalAxiosRequestConfig,
} from 'axios';

type TokenGetter = () => Promise<string | null>;
type LogoutFunc = () => Promise<void>;

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

class ApiClient {
  private client: AxiosInstance;
  private getTokenFunc: TokenGetter | null = null;
  private logoutFunc: LogoutFunc | null = null;
  private latestToken: string | null = null;
  private tokenExpiry: number | null = null; // Unix timestamp when token expires
  private refreshPromise: Promise<void> | null = null; // Prevent concurrent refresh attempts

  constructor(
    baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  ) {
    this.client = axios.create({
      baseURL,
      headers: { 'Content-Type': 'application/json' },
    });

    // ------------------------
    // Request Interceptor
    // ------------------------
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig): InternalAxiosRequestConfig => {
        const headers: AxiosRequestHeaders = config.headers;
        const url = config.url || 'unknown';
        const method = config.method?.toUpperCase() || 'UNKNOWN';

        // 🔐 Auth token
        if (this.latestToken) {
          headers['Authorization'] = `Bearer ${this.latestToken}`;
          console.log(`[🌐 API DEBUG] 📤 ${method} ${url}`);
          console.log(`[🌐 API DEBUG]   ✅ Authorization header added (Bearer token)`);
          // Decode token to show user_id in logs
          try {
            const payload = JSON.parse(atob(this.latestToken.split('.')[1]));
            console.log(`[🌐 API DEBUG]   User ID being sent: ${payload.sub}`);
          } catch (e) {
            // Ignore decode errors
          }
        } else {
          delete headers['Authorization'];
          console.log(`[🌐 API DEBUG] 📤 ${method} ${url}`);
          console.log(`[🌐 API DEBUG]   ⚠️ No Authorization header (no token available)`);
        }

        // 🏢 Tenant ID
        const tenantId = getTenantIdFromCookie();
        headers['x-tenant-id'] = tenantId;
        console.log(`[🌐 API DEBUG]   Tenant ID: ${tenantId}`);

        return config;
      }
    );

    // ------------------------
    // Response Interceptor
    // ------------------------
    this.client.interceptors.response.use(
      (res) => {
        const url = res.config.url || 'unknown';
        const method = res.config.method?.toUpperCase() || 'UNKNOWN';
        console.log(`[🌐 API DEBUG] ✅ ${method} ${url} - Status: ${res.status}`);
        return res;
      },
      async (error) => {
        const originalRequest = error.config;
        const url = originalRequest?.url || 'unknown';
        const method = originalRequest?.method?.toUpperCase() || 'UNKNOWN';
        const status = error.response?.status;

        if (status) {
          console.log(`[🌐 API DEBUG] ❌ ${method} ${url} - Status: ${status}`);
          if (status === 401) {
            console.log(`[🌐 API DEBUG]   ⚠️ 401 Unauthorized - Token might be invalid or expired`);
          }
        } else {
          console.log(`[🌐 API DEBUG] ❌ ${method} ${url} - Network error`);
        }

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            console.log(`[🌐 API DEBUG]   Attempting token refresh...`);
            await this.refreshToken();

            if (this.latestToken) {
              originalRequest.headers['Authorization'] =
                `Bearer ${this.latestToken}`;
              console.log(`[🌐 API DEBUG]   Retrying request with new token...`);
              return this.client(originalRequest);
            }
          } catch (err) {
            console.error('[🌐 API DEBUG] ❌ Token refresh failed', err);
          }

          if (this.logoutFunc) await this.logoutFunc();
        }

        return Promise.reject(error);
      }
    );
  }

  setTokenGetter(getTokenFunc: TokenGetter) {
    console.log('[🌐 API DEBUG] Token getter registered with API client');
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
      console.log('[🌐 API DEBUG] ⚠️ No token getter registered');
      return;
    }

    // If token is still valid and not forcing refresh, skip
    if (!force && !this.isTokenExpired()) {
      return;
    }

    // If a refresh is already in progress, wait for it
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    // Create new refresh promise
    this.refreshPromise = (async () => {
      try {
        console.log('[🌐 API DEBUG] Refreshing token...');
        const token = await this.getTokenFunc!();
        
        if (token) {
          this.latestToken = token;
          this.tokenExpiry = this.getTokenExpiry(token);
          console.log('[🌐 API DEBUG] ✅ Token refreshed successfully');
          
          // Decode token to show user_id (for debugging)
          try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            console.log('[🌐 API DEBUG]   User ID from token:', payload.sub);
            if (this.tokenExpiry) {
              const expiresIn = Math.floor((this.tokenExpiry - Date.now()) / 1000);
              console.log(`[🌐 API DEBUG]   Token expires in: ${expiresIn}s`);
            }
          } catch (e) {
            // Ignore decode errors
          }
        } else {
          this.latestToken = null;
          this.tokenExpiry = null;
          console.log('[🌐 API DEBUG] ⚠️ Token is null (user might not be signed in)');
        }
      } catch (err) {
        console.error('[🌐 API DEBUG] ❌ Failed to refresh token:', err);
        this.latestToken = null;
        this.tokenExpiry = null;
        throw err;
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

  async uploadSource(file: File, title?: string) {
    await this.refreshToken();
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);

    const res = await this.client.post('/api/v1/ingest/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  }

  async listSources() {
    await this.refreshToken();
    const res = await this.client.get('/api/v1/ingest/sources');
    return res.data.sources ?? [];
  }

  async deleteSource(sourceId: string) {
    await this.refreshToken();
    await this.client.delete(`/api/v1/ingest/sources/${sourceId}`);
  }

  // Streaming Chat
  async streamChat(
    message: string,
    history: any[],
    activeSourceIds: string[],
    onChunk: (text: string) => void,
    onCitation: (citation: any) => void,
    onDone: () => void
  ) {
    await this.refreshToken();

    const tenantId = getTenantIdFromCookie();
    const hasToken = !!this.latestToken;

    console.log('[🌐 API DEBUG] 📤 POST /api/v1/chat/stream');
    console.log(`[🌐 API DEBUG]   Tenant ID: ${tenantId}`);
    if (hasToken) {
      console.log(`[🌐 API DEBUG]   ✅ Authorization header will be included`);
      try {
        const payload = JSON.parse(atob(this.latestToken!.split('.')[1]));
        console.log(`[🌐 API DEBUG]   User ID being sent: ${payload.sub}`);
      } catch (e) {
        // Ignore decode errors
      }
    } else {
      console.log(`[🌐 API DEBUG]   ⚠️ No Authorization header (no token)`);
    }

    let retryCount = 0;
    const maxRetries = 1;

    while (retryCount <= maxRetries) {
      const response = await fetch(
        `${this.client.defaults.baseURL}/api/v1/chat/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-tenant-id': tenantId,
            ...(this.latestToken
              ? { Authorization: `Bearer ${this.latestToken}` }
              : {}),
          },
          body: JSON.stringify({
            message,
            history,
            active_source_ids: activeSourceIds,
          }),
        }
      );

      // Handle 401 Unauthorized - try refreshing token and retry once
      if (response.status === 401 && retryCount < maxRetries) {
        console.log('[🌐 API DEBUG]   ⚠️ 401 Unauthorized - Attempting token refresh...');
        try {
          await this.refreshToken(true); // Force refresh
          retryCount++;
          continue; // Retry the request
        } catch (err) {
          console.error('[🌐 API DEBUG] ❌ Token refresh failed', err);
          if (this.logoutFunc) {
            await this.logoutFunc();
          }
          throw new Error('Authentication failed. Please sign in again.');
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `Chat request failed with status ${response.status}`;
        throw new Error(errorMessage);
      }

      // Success - stream the response
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Failed to get response stream');
      }

      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue;

          const payload = line.replace('data: ', '').trim();
          if (!payload) continue;

          try {
            const data = JSON.parse(payload);
            if (data.event === 'chunk') onChunk(data.data.text);
            if (data.event === 'citation') onCitation(data.data);
            if (data.event === 'done') {
              onDone();
              return;
            }
          } catch (e) {
            console.error('[🌐 API DEBUG] Error parsing SSE data:', e);
            // Continue processing other lines
          }
        }
      }
      return; // Successfully completed
    }
  }

  async generateStudio(
    taskType: string,
    sourceIds: string[],
    instructions?: string
  ) {
    await this.refreshToken();
    const res = await this.client.post('/api/v1/studio/generate', {
      task_type: taskType,
      source_ids: sourceIds,
      custom_instructions: instructions,
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
    const res = await this.client.get('/api/v1/notes');
    return res.data.notes ?? [];
  }

  async deleteNote(noteId: string) {
    await this.refreshToken();
    await this.client.delete(`/api/v1/notes/${noteId}`);
  }
}

const apiClient = new ApiClient();

export { apiClient };
export default apiClient;
