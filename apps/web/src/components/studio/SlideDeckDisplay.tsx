/**
 * Slide Deck Display Component
 * 
 * Displays slides from Markdown outline in sequence with navigation
 * (next/previous slide) and slide counter.
 * Styled to match NotebookLM design system.
 */

'use client';

import { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface SlideDeckDisplayProps {
  slideData: string | object;
}

interface Slide {
  title: string;
  content: string;
  level: number;
}

export function SlideDeckDisplay({ slideData }: SlideDeckDisplayProps) {
  const [currentSlideIndex, setCurrentSlideIndex] = useState(0);

  // Parse slide data
  const parseSlideData = (): string | null => {
    try {
      let content: string = '';
      
      if (typeof slideData === 'string') {
        content = slideData;
      } else if (typeof slideData === 'object' && slideData !== null) {
        const parsed = slideData as any;
        // Handle response structure: { task_type: "slide_deck", content: "..." }
        if (parsed.content) {
          content = parsed.content;
        } else if (parsed.task_type === 'slide_deck' && parsed.content) {
          content = parsed.content;
        } else {
          // Try to stringify if it's an object
          content = JSON.stringify(parsed, null, 2);
        }
      } else {
        return null;
      }

      return content || null;
    } catch (error) {
      console.error('Failed to parse slide deck data:', error);
      return null;
    }
  };

  const markdownContent = parseSlideData();

  if (!markdownContent) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <p className="text-sm text-text-secondary">
            Invalid slide deck data. Please ensure the slide deck is properly formatted.
          </p>
        </div>
      </div>
    );
  }

  // Clean slide title - remove "Slide 1:", "Slide 2:" etc. patterns
  const cleanSlideTitle = (title: string): string => {
    // Remove patterns like "Slide 1:", "Slide 2:", "Slide 1", "Slide 2" at the start
    let cleaned = title.replace(/^Slide\s+\d+\s*:?\s*/i, '').trim();
    // Also handle patterns like "Slide 1: Title" -> "Title"
    cleaned = cleaned.replace(/^Slide\s+\d+\s*:?\s*/i, '');
    // If title is empty after cleaning, use a default
    if (!cleaned) {
      cleaned = 'Untitled Slide';
    }
    return cleaned;
  };

  // Parse slides from markdown
  const parseSlides = (content: string): Slide[] => {
    const lines = content.split('\n');
    const slides: Slide[] = [];
    let currentSlide: Slide | null = null;
    let currentContent: string[] = [];

    lines.forEach((line) => {
      // Match headers (#, ##, ###, etc.)
      // For slide decks, we typically use # for slide titles
      const headerMatch = line.match(/^(#{1,3})\s+(.+)$/);
      
      if (headerMatch) {
        // Save previous slide if exists
        if (currentSlide) {
          currentSlide.content = currentContent.join('\n').trim();
          slides.push(currentSlide);
        }

        // Start new slide (treat # and ## as slide titles)
        const level = headerMatch[1].length;
        const rawTitle = headerMatch[2].trim();
        const title = cleanSlideTitle(rawTitle);
        
        // Only create new slide for level 1 or 2 headers
        if (level <= 2) {
          currentSlide = {
            title,
            content: '',
            level,
          };
          currentContent = [];
        } else {
          // Level 3+ headers are part of the slide content
          if (currentSlide) {
            currentContent.push(line);
          }
        }
      } else {
        // Add to current slide content
        if (currentSlide) {
          currentContent.push(line);
        } else {
          // Content before first header - create a default slide
          if (!currentSlide && currentContent.length === 0) {
            currentSlide = {
              title: 'Untitled Slide',
              content: '',
              level: 1,
            };
          }
          if (currentSlide) {
            currentContent.push(line);
          }
        }
      }
    });

    // Save last slide
    if (currentSlide) {
      currentSlide.content = currentContent.join('\n').trim();
      slides.push(currentSlide);
    }

    // If no slides found, split by double newlines or return entire content as one slide
    if (slides.length === 0) {
      // Try splitting by double newlines
      const sections = content.split(/\n\n+/);
      if (sections.length > 1) {
        sections.forEach((section, index) => {
          const lines = section.split('\n');
          const firstLine = lines[0] || '';
          const rawTitle = firstLine.replace(/^#+\s*/, '').trim();
          const title = rawTitle ? cleanSlideTitle(rawTitle) : 'Untitled Slide';
          const slideContent = lines.slice(1).join('\n') || section;
          
          slides.push({
            title,
            content: slideContent,
            level: 1,
          });
        });
      } else {
        // Return entire content as one slide
        slides.push({
          title: 'Untitled Slide',
          content: markdownContent,
          level: 1,
        });
      }
    }

    return slides;
  };

  const slides = useMemo(() => parseSlides(markdownContent), [markdownContent]);

  const currentSlide = slides[currentSlideIndex];
  const totalSlides = slides.length;

  // Navigation handlers
  const handlePrevious = () => {
    setCurrentSlideIndex((prev) => (prev > 0 ? prev - 1 : prev));
  };

  const handleNext = () => {
    setCurrentSlideIndex((prev) => (prev < totalSlides - 1 ? prev + 1 : prev));
  };

  // Handle click on slide to advance (PowerPoint-style)
  const handleSlideClick = (e: React.MouseEvent) => {
    // Don't advance if clicking on links, buttons, or interactive elements
    const target = e.target as HTMLElement;
    if (target.tagName === 'A' || target.tagName === 'BUTTON' || target.closest('button') || target.closest('a')) {
      return;
    }
    handleNext();
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft') {
      handlePrevious();
    } else if (e.key === 'ArrowRight') {
      handleNext();
    }
  };

  if (slides.length === 0) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <p className="text-sm text-text-secondary">
            No slides found in the slide deck.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="h-full overflow-auto flex items-center justify-center p-4"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Slide Container */}
      <div
        className="bg-white dark:bg-slate-800 rounded-xl shadow-xl border border-border-default w-full max-w-5xl aspect-[16/9] p-10 focus:outline-none cursor-pointer transition-all hover:shadow-2xl relative"
        onClick={handleSlideClick}
      >
        {/* Left Arrow Button - Over the slide */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            handlePrevious();
          }}
          disabled={currentSlideIndex === 0}
          className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/95 dark:bg-slate-800/95 shadow-lg border border-border-default flex items-center justify-center hover:bg-white dark:hover:bg-slate-800 transition-all disabled:opacity-30 disabled:cursor-not-allowed z-20"
          aria-label="Previous slide"
        >
          <ChevronLeft className="w-5 h-5 text-text-primary" />
        </button>

        {/* Right Arrow Button - Over the slide */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleNext();
          }}
          disabled={currentSlideIndex === totalSlides - 1}
          className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/95 dark:bg-slate-800/95 shadow-lg border border-border-default flex items-center justify-center hover:bg-white dark:hover:bg-slate-800 transition-all disabled:opacity-30 disabled:cursor-not-allowed z-20"
          aria-label="Next slide"
        >
          <ChevronRight className="w-5 h-5 text-text-primary" />
        </button>

        {currentSlide && (
          <div className="h-full flex flex-col justify-between">
            <div className="flex-1 flex flex-col justify-center space-y-6">
              {/* Slide Title */}
              {currentSlide.title && currentSlide.title !== 'Untitled Slide' && (
                <div className="border-b-2 border-accent-orange/20 pb-4 mb-6">
                  <h2 className="text-3xl font-bold text-text-primary">
                    {currentSlide.title}
                  </h2>
                </div>
              )}

              {/* Slide Content */}
              <div className="prose prose-lg dark:prose-invert max-w-none flex-1 overflow-auto">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children, ...props }) => (
                      <h1 className="text-2xl font-bold text-text-primary mt-6 mb-3" {...props}>
                        {children}
                      </h1>
                    ),
                    h2: ({ children, ...props }) => (
                      <h2 className="text-xl font-semibold text-text-primary mt-5 mb-2" {...props}>
                        {children}
                      </h2>
                    ),
                    h3: ({ children, ...props }) => (
                      <h3 className="text-lg font-semibold text-text-primary mt-4 mb-2" {...props}>
                        {children}
                      </h3>
                    ),
                    p: ({ children, ...props }) => (
                      <p className="text-lg text-text-primary leading-relaxed mb-4" {...props}>
                        {children}
                      </p>
                    ),
                    ul: ({ children, ...props }) => (
                      <ul className="list-disc list-inside text-lg text-text-primary mb-4 space-y-2 ml-4" {...props}>
                        {children}
                      </ul>
                    ),
                    ol: ({ children, ...props }) => (
                      <ol className="list-decimal list-inside text-lg text-text-primary mb-4 space-y-2 ml-4" {...props}>
                        {children}
                      </ol>
                    ),
                    li: ({ children, ...props }) => (
                      <li className="text-lg text-text-primary leading-relaxed" {...props}>
                        {children}
                      </li>
                    ),
                    strong: ({ children, ...props }) => (
                      <strong className="font-semibold text-text-primary" {...props}>
                        {children}
                      </strong>
                    ),
                    em: ({ children, ...props }) => (
                      <em className="italic text-text-primary" {...props}>
                        {children}
                      </em>
                    ),
                    code: ({ children, ...props }) => (
                      <code className="bg-surface-hover px-2 py-1 rounded text-base font-mono text-text-primary" {...props}>
                        {children}
                      </code>
                    ),
                    pre: ({ children, ...props }) => (
                      <pre className="bg-surface-hover border border-border-default rounded-lg p-4 overflow-x-auto mb-4" {...props}>
                        {children}
                      </pre>
                    ),
                    blockquote: ({ children, ...props }) => (
                      <blockquote className="border-l-4 border-accent-orange pl-4 italic text-text-secondary my-4" {...props}>
                        {children}
                      </blockquote>
                    ),
                  }}
                >
                  {currentSlide.content}
                </ReactMarkdown>
              </div>
            </div>

            {/* Slide Number at Bottom */}
            <div className="mt-4 pt-4 border-t border-border-default/50">
              <p className="text-xs text-text-tertiary text-center">
                {currentSlideIndex + 1} / {totalSlides}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
