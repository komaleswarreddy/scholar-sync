/**
 * Dashboard Page
 * 
 * Main chat interface with source-grounded RAG.
 */

'use client';

import { ChatInterface } from '@/components/chat/ChatInterface';

export default function DashboardPage() {
  return <ChatInterface mode="dashboard" />;
}
