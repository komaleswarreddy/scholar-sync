/**
 * Shared API Client
 * Axios-based API client for communicating with FastAPI backend.
 * Handles auth headers and tenant headers.
 */

import axios, { AxiosInstance } from 'axios';
import type { Note, Source, ChatMessage, Citation, StudioTaskType } from '@scholarsync/types';

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

    // Interceptor for tenant header
    this.client.interceptors.request.use((config) => {
      if (this.tenantId && !config.url?.includes('localhost')) {
        config.headers['X-Tenant-ID'] = this.tenantId;
      }
      return config;
    });
  }

  setTenantId(tenantId: string) {
    this.tenantId = tenantId;
  }

  setAuthToken(token: string) {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  }

  // ---------------- Notes API ----------------

  async createNote(content: string, sourceRefId?: string, userId: string = 'dev-user-123'): Promise<Note> {
    const headers: Record<string, string> = { 'X-User-ID': userId };

    const response = await this.client.post(
      '/api/v1/notes',
      { content, source_ref_id: sourceRefId },
      { headers }
    );

    return response.data;
  }

  async listNotes(userId: string = 'dev-user-123'): Promise<Note[]> {
    const headers: Record<string, string> = { 'X-User-ID': userId };
  
    const response = await this.client.get('/api/v1/notes', { headers });
  
    console.log('listNotes response:', response.data); // <-- add this
  
    return response.data.notes || [];
  }
  

  async deleteNote(noteId: string, userId: string = 'dev-user-123'): Promise<void> {
    const headers: Record<string, string> = { 'X-User-ID': userId };

    await this.client.delete(`/api/v1/notes/${noteId}`, { headers });
  }

  // ------------- Other APIs (optional) -------------

  async uploadSource(file: File, title?: string): Promise<Source> {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);

    const response = await this.client.post('/api/v1/ingest/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async listSources(): Promise<Source[]> {
    const response = await this.client.get('/api/v1/ingest/sources');
    return response.data.sources || [];
  }
}

// Singleton export
export const apiClient = new ApiClient();
