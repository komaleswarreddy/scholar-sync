/**
 * Shared TypeScript Types
 * 
 * Type definitions shared across web and mobile apps.
 */

import { z } from 'zod';

// Source Types
export const SourceTypeSchema = z.enum(['pdf', 'text', 'url']);
export type SourceType = z.infer<typeof SourceTypeSchema>;

export const SourceSchema = z.object({
  id: z.string(),
  title: z.string(),
  type: SourceTypeSchema,
  created_at: z.string(),
  s3_url: z.string().optional(),
});

export type Source = z.infer<typeof SourceSchema>;

// Chat Types
export const ChatMessageSchema = z.object({
  role: z.enum(['user', 'assistant']),
  content: z.string(),
});

export type ChatMessage = z.infer<typeof ChatMessageSchema>;

export const CitationSchema = z.object({
  source_id: z.string(),
  chunk_id: z.string(),
  text: z.string(),
  page_number: z.number().optional(),
  score: z.number(),
});

export type Citation = z.infer<typeof CitationSchema>;

// Studio Types
export const StudioTaskTypeSchema = z.enum([
  'quiz',
  'flashcards',
  'mind_map',
  'report',
  'infographic',
  'slide_deck',
]);

export type StudioTaskType = z.infer<typeof StudioTaskTypeSchema>;

export const QuizQuestionSchema = z.object({
  question: z.string(),
  options: z.array(z.string()),
  correct_answer: z.string(),
  explanation: z.string(),
});

export type QuizQuestion = z.infer<typeof QuizQuestionSchema>;

export const FlashcardSchema = z.object({
  front: z.string(),
  back: z.string(),
});

export type Flashcard = z.infer<typeof FlashcardSchema>;

// Note Types
export const NoteSchema = z.object({
  id: z.string(),
  content: z.string(),
  source_ref_id: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string().optional(),
});

export type Note = z.infer<typeof NoteSchema>;


