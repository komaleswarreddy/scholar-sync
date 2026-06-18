/**
 * Endpoints Page
 * 
 * Admin page for monitoring and managing API endpoints.
 */

'use client';

import { ExternalLink, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import { useState } from 'react';

interface Endpoint {
  method: string;
  path: string;
  description: string;
  status: 'active' | 'deprecated' | 'beta';
  category: string;
  requiresAuth: boolean;
  requiresAdmin: boolean;
}

const endpoints: Endpoint[] = [
  // Health
  { method: 'GET', path: '/health', description: 'Health check endpoint', status: 'active', category: 'Health', requiresAuth: false, requiresAdmin: false },
  { method: 'GET', path: '/', description: 'Root endpoint', status: 'active', category: 'Health', requiresAuth: false, requiresAdmin: false },
  
  // Chat
  { method: 'POST', path: '/api/v1/chat/stream', description: 'Stream chat messages', status: 'active', category: 'Chat', requiresAuth: true, requiresAdmin: false },
  { method: 'POST', path: '/api/v1/chat', description: 'Create a new chat', status: 'active', category: 'Chat', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/chat', description: 'List all chats', status: 'active', category: 'Chat', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/chat/{chat_id}', description: 'Get chat by ID', status: 'active', category: 'Chat', requiresAuth: true, requiresAdmin: false },
  { method: 'DELETE', path: '/api/v1/chat/{chat_id}', description: 'Delete a chat', status: 'active', category: 'Chat', requiresAuth: true, requiresAdmin: false },
  { method: 'POST', path: '/api/v1/chat/{chat_id}/messages', description: 'Add message to chat', status: 'active', category: 'Chat', requiresAuth: true, requiresAdmin: false },
  
  // Sources/Ingest
  { method: 'POST', path: '/api/v1/ingest/upload', description: 'Upload and index a document', status: 'active', category: 'Sources', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/ingest/sources', description: 'List all sources', status: 'active', category: 'Sources', requiresAuth: true, requiresAdmin: false },
  { method: 'DELETE', path: '/api/v1/ingest/sources/{source_id}', description: 'Delete a source', status: 'active', category: 'Sources', requiresAuth: true, requiresAdmin: false },
  
  // Studio
  { method: 'POST', path: '/api/v1/studio/generate', description: 'Generate content using AI', status: 'active', category: 'Studio', requiresAuth: true, requiresAdmin: false },
  
  // Notes
  { method: 'GET', path: '/api/v1/notes', description: 'List all notes', status: 'active', category: 'Notes', requiresAuth: true, requiresAdmin: false },
  { method: 'POST', path: '/api/v1/notes', description: 'Create a new note', status: 'active', category: 'Notes', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/notes/{note_id}', description: 'Get note by ID', status: 'active', category: 'Notes', requiresAuth: true, requiresAdmin: false },
  { method: 'PUT', path: '/api/v1/notes/{note_id}', description: 'Update a note', status: 'active', category: 'Notes', requiresAuth: true, requiresAdmin: false },
  { method: 'DELETE', path: '/api/v1/notes/{note_id}', description: 'Delete a note', status: 'active', category: 'Notes', requiresAuth: true, requiresAdmin: false },
  
  // Metrics
  { method: 'GET', path: '/api/v1/metrics/summary', description: 'Get metrics summary', status: 'active', category: 'Metrics', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/metrics/dashboard', description: 'Get dashboard data', status: 'active', category: 'Metrics', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/metrics/rag-quality', description: 'Get RAG quality metrics', status: 'active', category: 'Metrics', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/metrics/token-consumption', description: 'Get token consumption data', status: 'active', category: 'Metrics', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/metrics/cost-tracking', description: 'Get cost tracking data', status: 'active', category: 'Metrics', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/metrics/cache-efficiency', description: 'Get cache efficiency metrics', status: 'active', category: 'Metrics', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/metrics/latency', description: 'Get latency metrics', status: 'active', category: 'Metrics', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/metrics/alerts', description: 'Get alerts', status: 'active', category: 'Metrics', requiresAuth: true, requiresAdmin: false },
  
  // Alerts
  { method: 'GET', path: '/api/v1/alerts/status', description: 'Get alerts status', status: 'active', category: 'Alerts', requiresAuth: true, requiresAdmin: false },
  
  // Admin
  { method: 'GET', path: '/api/v1/admin/users', description: 'List all users', status: 'active', category: 'Admin', requiresAuth: true, requiresAdmin: true },
  { method: 'GET', path: '/api/v1/admin/aggregate', description: 'Get aggregate metrics', status: 'active', category: 'Admin', requiresAuth: true, requiresAdmin: true },
  { method: 'GET', path: '/api/v1/admin/me/metrics', description: 'Get current user metrics', status: 'active', category: 'Admin', requiresAuth: true, requiresAdmin: false },
  { method: 'GET', path: '/api/v1/admin/users/{user_id}/metrics', description: 'Get user metrics', status: 'active', category: 'Admin', requiresAuth: true, requiresAdmin: true },
  { method: 'GET', path: '/api/v1/admin/users/{user_id}/sessions', description: 'Get user sessions', status: 'active', category: 'Admin', requiresAuth: true, requiresAdmin: true },
];

export default function EndpointsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const categories = ['all', ...Array.from(new Set(endpoints.map(e => e.category)))];
  
  const filteredEndpoints = endpoints.filter(endpoint => {
    const matchesCategory = selectedCategory === 'all' || endpoint.category === selectedCategory;
    const matchesSearch = searchQuery === '' || 
      endpoint.path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      endpoint.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      endpoint.method.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-500/20 text-green-500 border-green-500/30';
      case 'deprecated':
        return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
      case 'beta':
        return 'bg-blue-500/20 text-blue-500 border-blue-500/30';
      default:
        return 'bg-gray-500/20 text-gray-500 border-gray-500/30';
    }
  };

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET':
        return 'bg-blue-500/20 text-blue-500';
      case 'POST':
        return 'bg-green-500/20 text-green-500';
      case 'PUT':
        return 'bg-yellow-500/20 text-yellow-500';
      case 'DELETE':
        return 'bg-red-500/20 text-red-500';
      case 'PATCH':
        return 'bg-purple-500/20 text-purple-500';
      default:
        return 'bg-gray-500/20 text-gray-500';
    }
  };

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Endpoints</h1>
        <p className="text-sm text-text-secondary mt-1">
          Monitor and manage API endpoints
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search endpoints..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface border border-border-default rounded-lg px-4 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
          />
        </div>
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="bg-surface border border-border-default rounded-lg px-4 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
        >
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat === 'all' ? 'All Categories' : cat}</option>
          ))}
        </select>
      </div>

      {/* Endpoints Table */}
      <div className="bg-surface rounded-2xl border border-border-default overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border-default">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Method</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Endpoint</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Description</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Category</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Status</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Auth</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-text-primary">Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              {filteredEndpoints.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-text-secondary">
                    No endpoints found
                  </td>
                </tr>
              ) : (
                filteredEndpoints.map((endpoint, idx) => (
                  <tr key={idx} className="hover:bg-surface-hover transition-colors">
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getMethodColor(endpoint.method)}`}>
                        {endpoint.method}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <code className="text-sm text-text-primary font-mono">{endpoint.path}</code>
                    </td>
                    <td className="px-6 py-4 text-text-primary">{endpoint.description}</td>
                    <td className="px-6 py-4 text-text-secondary">{endpoint.category}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusColor(endpoint.status)}`}>
                        {endpoint.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {endpoint.requiresAuth && (
                          <span className="text-xs text-text-secondary">Auth</span>
                        )}
                        {endpoint.requiresAdmin && (
                          <span className="text-xs text-red-500">Admin</span>
                        )}
                        {!endpoint.requiresAuth && (
                          <span className="text-xs text-text-tertiary">Public</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <a
                        href={`${baseUrl}${endpoint.path}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent-blue hover:text-accent-blue/80 flex items-center gap-1 text-sm"
                      >
                        Open
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-sm text-text-secondary mb-1">Total Endpoints</p>
          <p className="text-2xl font-bold text-text-primary">{endpoints.length}</p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-sm text-text-secondary mb-1">Active</p>
          <p className="text-2xl font-bold text-green-500">
            {endpoints.filter(e => e.status === 'active').length}
          </p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-sm text-text-secondary mb-1">Requires Auth</p>
          <p className="text-2xl font-bold text-text-primary">
            {endpoints.filter(e => e.requiresAuth).length}
          </p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-4">
          <p className="text-sm text-text-secondary mb-1">Admin Only</p>
          <p className="text-2xl font-bold text-red-500">
            {endpoints.filter(e => e.requiresAdmin).length}
          </p>
        </div>
      </div>
    </div>
  );
}
