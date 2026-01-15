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

        // 🔐 Auth token
        if (this.latestToken) {
          headers['Authorization'] = `Bearer ${this.latestToken}`;
        } else {
          delete headers['Authorization'];
        }

        // 🏢 Tenant ID
        headers['x-tenant-id'] = getTenantIdFromCookie();

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

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.refreshToken();

            if (this.latestToken) {
              originalRequest.headers['Authorization'] =
                `Bearer ${this.latestToken}`;
              return this.client(originalRequest);
            }
          } catch (err) {
            console.error('Token refresh failed', err);
          }

          if (this.logoutFunc) await this.logoutFunc();
        }

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

  async refreshToken() {
    if (!this.getTokenFunc) return;
    try {
      this.latestToken = await this.getTokenFunc();
    } catch (err) {
      console.error('Failed to refresh token', err);
      this.latestToken = null;
    }
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

    if (!response.ok) throw new Error('Chat request failed');

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      for (const line of chunk.split('\n')) {
        if (!line.startsWith('data: ')) continue;

        const payload = line.replace('data: ', '').trim();
        if (!payload) continue;

        const data = JSON.parse(payload);
        if (data.event === 'chunk') onChunk(data.data.text);
        if (data.event === 'citation') onCitation(data.data);
        if (data.event === 'done') {
          onDone();
          return;
        }
      }
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
