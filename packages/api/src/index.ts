/**
 * Shared API Client
 * 
 * Axios-based API client for communicating with FastAPI backend.
 * Handles authentication, tenant headers, and error handling.
 */

import axios, { AxiosInstance } from 'axios';
import type {
  Source,
  ChatMessage,
  Citation,
  StudioTaskType,
  Note,
} from '@scholarsync/types';

export class ApiClient {
  private client: AxiosInstance;
  private tenantId: string | null = null;

  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for auth and tenant headers
    this.client.interceptors.request.use((config) => {
      // For development, tenant is handled by middleware via host header
      // No need to send X-Tenant-ID header for localhost
      // In production with subdomains, this would be set
      if (this.tenantId && !config.url?.includes('localhost')) {
        config.headers['X-Tenant-ID'] = this.tenantId;
      }
      // Add auth token from Clerk in frontend
      return config;
    });
  }

  setTenantId(tenantId: string) {
    this.tenantId = tenantId;
  }

  setAuthToken(token: string) {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  // Source Management
  async uploadSource(file: File, title?: string): Promise<Source> {
    const formData = new FormData();
    formData.append('file', file);
    if (title) {
      formData.append('title', title);
    }

    const response = await this.client.post('/api/v1/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  async listSources(): Promise<Source[]> {
    const response = await this.client.get('/api/v1/ingest/sources');
    return response.data.sources || [];
  }

  async deleteSource(sourceId: string): Promise<void> {
    await this.client.delete(`/api/v1/ingest/sources/${sourceId}`);
  }

  // Chat
  async streamChat(
    message: string,
    history: ChatMessage[],
    activeSourceIds: string[],
    onChunk: (text: string) => void,
    onCitation: (citation: Citation) => void,
    onDone: () => void,
  ): Promise<void> {
    const response = await fetch(`${this.client.defaults.baseURL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': this.tenantId || '',
        'Authorization': this.client.defaults.headers.common['Authorization'] as string,
      },
      body: JSON.stringify({
        message,
        history,
        active_source_ids: activeSourceIds,
      }),
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) return;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventType = line.substring(7);
          continue;
        }
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.substring(6));
          
          if (data.event === 'chunk') {
            onChunk(data.data.text);
          } else if (data.event === 'citation') {
            onCitation(data.data);
          } else if (data.event === 'done') {
            onDone();
            return;
          }
        }
      }
    }
  }

  // Studio
  async generateStudio(
    taskType: StudioTaskType,
    sourceIds: string[],
    customInstructions?: string,
  ): Promise<any> {
    const response = await this.client.post('/api/v1/studio/generate', {
      task_type: taskType,
      source_ids: sourceIds,
      custom_instructions: customInstructions,
    });

    return response.data;
  }

  // Notes
  async createNote(content: string, sourceRefId?: string): Promise<Note> {
    // Add default user ID for development
    const userId = 'dev-user-123'; // TODO: Get from Clerk
    
    const response = await this.client.post(
      '/api/v1/notes',
      {
        content,
        source_ref_id: sourceRefId,
      },
      {
        headers: {
          'X-User-ID': userId,
        },
      }
    );

    return response.data;
  }

  async listNotes(): Promise<Note[]> {
    // Add default user ID for development
    const userId = 'dev-user-123'; // TODO: Get from Clerk
    
    const response = await this.client.get('/api/v1/notes', {
      headers: {
        'X-User-ID': userId,
      },
    });
    return response.data.notes || [];
  }

  async deleteNote(noteId: string): Promise<void> {
    // Add default user ID for development
    const userId = 'dev-user-123'; // TODO: Get from Clerk
    
    await this.client.delete(`/api/v1/notes/${noteId}`, {
      headers: {
        'X-User-ID': userId,
      },
    });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

