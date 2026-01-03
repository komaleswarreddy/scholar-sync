/**
 * API Client Setup
 * 
 * Initializes and configures the API client for the frontend.
 */

import axios, { AxiosInstance } from 'axios';

// Create API client directly
class ApiClient {
  private client: AxiosInstance;
  private tenantId: string | null = null;

  constructor(baseURL: string = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  setTenantId(tenantId: string) {
    this.tenantId = tenantId;
  }

  setAuthToken(token: string) {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  // Source Management
  async uploadSource(file: File, title?: string): Promise<any> {
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

  async listSources(): Promise<any[]> {
    const response = await this.client.get('/api/v1/ingest/sources');
    return response.data.sources || [];
  }

  async deleteSource(sourceId: string): Promise<void> {
    await this.client.delete(`/api/v1/ingest/sources/${sourceId}`);
  }

  // Chat
  async streamChat(
    message: string,
    history: any[],
    activeSourceIds: string[],
    onChunk: (text: string) => void,
    onCitation: (citation: any) => void,
    onDone: () => void,
  ): Promise<void> {
    const userId = 'dev-user-123';
    
    const requestBody = {
      message,
      history,
      active_source_ids: activeSourceIds,
    };
    
    console.log('Chat request body:', requestBody);
    console.log('Active source IDs:', activeSourceIds);
    console.log('Source IDs length:', activeSourceIds.length);
    
    const response = await fetch(`${this.client.defaults.baseURL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': this.tenantId || 'default',
        'X-User-ID': userId,
        'Authorization': this.client.defaults.headers.common['Authorization'] as string || '',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to start chat' }));
      throw new Error(errorData.detail || 'Chat request failed');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) return;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (!line.trim()) continue;
        
        if (line.startsWith('event: ')) {
          continue;
        }
        if (line.startsWith('data: ')) {
          try {
            const jsonStr = line.substring(6).trim();
            if (!jsonStr) continue;
            
            const data = JSON.parse(jsonStr);
            
            if (data.event === 'chunk' && data.data?.text) {
              onChunk(data.data.text);
            } else if (data.event === 'citation' && data.data) {
              onCitation(data.data);
            } else if (data.event === 'done') {
              onDone();
              return;
            }
          } catch (err) {
            console.warn('Failed to parse SSE data:', line, err);
          }
        }
      }
    }
  }

  // Studio
  async generateStudio(
    taskType: string,
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
  async createNote(content: string, sourceRefId?: string): Promise<any> {
    const userId = 'dev-user-123';
    
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

  async listNotes(): Promise<any[]> {
    const userId = 'dev-user-123';
    
    const response = await this.client.get('/api/v1/notes', {
      headers: {
        'X-User-ID': userId,
      },
    });
    return response.data.notes || [];
  }

  async deleteNote(noteId: string): Promise<void> {
    const userId = 'dev-user-123';
    
    await this.client.delete(`/api/v1/notes/${noteId}`, {
      headers: {
        'X-User-ID': userId,
      },
    });
  }
}

// Initialize API client with default tenant
const apiClient = new ApiClient();
apiClient.setTenantId('default');

export { apiClient };

