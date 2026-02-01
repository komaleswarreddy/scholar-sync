/**
 * Infographic Brief Display Component
 * 
 * Displays visual brief description for infographics with sections
 * (visual elements, data points, layout).
 * Styled to match NotebookLM design system.
 */

'use client';

import { useMemo } from 'react';
import { Image as ImageIcon, Palette, BarChart3, Layout } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface InfographicBriefDisplayProps {
  briefData: string | object;
}

interface InfographicSection {
  title: string;
  content: string;
  icon: React.ReactNode;
}

export function InfographicBriefDisplay({ briefData }: InfographicBriefDisplayProps) {
  // Parse brief data and extract image URL
  const parseBriefData = (): { content: string | null; imageUrl: string | null; revisedPrompt: string | null; imageError: string | null } => {
    try {
      let content: string = '';
      let imageUrl: string | null = null;
      let revisedPrompt: string | null = null;
      let imageError: string | null = null;
      
      if (typeof briefData === 'string') {
        content = briefData;
      } else if (typeof briefData === 'object' && briefData !== null) {
        const parsed = briefData as any;
        // Handle response structure: { task_type: "infographic", content: "...", image_url: "..." }
        if (parsed.content) {
          content = parsed.content;
        } else if (parsed.task_type === 'infographic' && parsed.content) {
          content = parsed.content;
        } else {
          // Try to stringify if it's an object
          content = JSON.stringify(parsed, null, 2);
        }
        
        // Extract image URL if present
        if (parsed.image_url) {
          imageUrl = parsed.image_url;
        }
        if (parsed.revised_prompt) {
          revisedPrompt = parsed.revised_prompt;
        }
        if (parsed.image_error) {
          imageError = parsed.image_error;
        }
      } else {
        return { content: null, imageUrl: null, revisedPrompt: null, imageError: null };
      }

      return { 
        content: content || null, 
        imageUrl, 
        revisedPrompt,
        imageError 
      };
    } catch (error) {
      console.error('Failed to parse infographic brief data:', error);
      return { content: null, imageUrl: null, revisedPrompt: null, imageError: null };
    }
  };

  const { content: markdownContent, imageUrl, revisedPrompt, imageError } = parseBriefData();

  if (!markdownContent && !imageUrl) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <p className="text-sm text-text-secondary">
            Invalid infographic brief data. Please ensure the brief is properly formatted.
          </p>
        </div>
      </div>
    );
  }

  // Parse sections from markdown
  const parseSections = (content: string): InfographicSection[] => {
    const lines = content.split('\n');
    const sections: InfographicSection[] = [];
    let currentSection: InfographicSection | null = null;
    let currentContent: string[] = [];

    // Map section titles to icons
    const getIconForSection = (title: string): React.ReactNode => {
      const lowerTitle = title.toLowerCase();
      if (lowerTitle.includes('visual') || lowerTitle.includes('element') || lowerTitle.includes('design')) {
        return <Palette className="w-5 h-5" />;
      }
      if (lowerTitle.includes('data') || lowerTitle.includes('point') || lowerTitle.includes('statistic')) {
        return <BarChart3 className="w-5 h-5" />;
      }
      if (lowerTitle.includes('layout') || lowerTitle.includes('structure') || lowerTitle.includes('arrangement')) {
        return <Layout className="w-5 h-5" />;
      }
      return <ImageIcon className="w-5 h-5" />;
    };

    lines.forEach((line) => {
      // Match headers (#, ##, ###, etc.)
      const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
      
      if (headerMatch) {
        // Save previous section if exists
        if (currentSection) {
          currentSection.content = currentContent.join('\n').trim();
          sections.push(currentSection);
        }

        // Start new section
        const title = headerMatch[2].trim();
        currentSection = {
          title,
          content: '',
          icon: getIconForSection(title),
        };
        currentContent = [];
      } else {
        // Add to current section content
        if (currentSection) {
          currentContent.push(line);
        } else {
          // Content before first header - create a default section
          if (!currentSection && currentContent.length === 0) {
            currentSection = {
              title: 'Infographic Brief',
              content: '',
              icon: <ImageIcon className="w-5 h-5" />,
            };
          }
          if (currentSection) {
            currentContent.push(line);
          }
        }
      }
    });

    // Save last section
    if (currentSection) {
      currentSection.content = currentContent.join('\n').trim();
      sections.push(currentSection);
    }

    // If no sections found, return entire content as one section
    if (sections.length === 0) {
      return [{
        title: 'Infographic Brief',
        content: markdownContent,
        icon: <ImageIcon className="w-5 h-5" />,
      }];
    }

    return sections;
  };

  const sections = useMemo(() => {
    if (!markdownContent) return [];
    return parseSections(markdownContent);
  }, [markdownContent]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent-purple/10 flex items-center justify-center">
          <ImageIcon className="w-5 h-5 text-accent-purple" />
        </div>
        <div>
          <h3 className="text-xl font-bold text-text-primary">Generated Infographic</h3>
          <p className="text-sm text-text-secondary">
            {imageUrl ? 'Image generated successfully' : imageError ? 'Image generation failed' : 'Text description'}
          </p>
        </div>
      </div>

      {/* Generated Image */}
      {imageUrl && (
        <div className="bg-surface-subtle rounded-xl border border-border-default p-6">
          <div className="mb-4">
            <h4 className="text-lg font-semibold text-text-primary mb-2">Infographic Image</h4>
            {revisedPrompt && (
              <p className="text-sm text-text-secondary italic mb-4">
                "{revisedPrompt}"
              </p>
            )}
          </div>
          <div className="relative w-full rounded-lg overflow-hidden border border-border-default bg-white dark:bg-surface">
            <img 
              src={imageUrl} 
              alt="Generated infographic" 
              className="w-full h-auto"
              style={{ maxHeight: '80vh', objectFit: 'contain' }}
            />
          </div>
        </div>
      )}

      {/* Image Error */}
      {imageError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
          <p className="text-sm text-red-600 dark:text-red-400">
            ⚠️ {imageError}
          </p>
        </div>
      )}

      {/* Text Description (if available) */}
      {markdownContent && (
        <div className="space-y-4">
        {sections.map((section, index) => (
          <div
            key={index}
            className="bg-surface-subtle rounded-xl border border-border-default p-6 hover:border-accent-purple/30 transition-colors"
          >
            {/* Section Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-lg bg-accent-purple/10 flex items-center justify-center text-accent-purple">
                {section.icon}
              </div>
              <h4 className="text-lg font-semibold text-text-primary">
                {section.title}
              </h4>
            </div>

            {/* Section Content */}
            <div className="prose prose-sm dark:prose-invert max-w-none">
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
                    <p className="text-base text-text-primary leading-relaxed mb-3" {...props}>
                      {children}
                    </p>
                  ),
                  ul: ({ children, ...props }) => (
                    <ul className="list-disc list-inside text-base text-text-primary mb-3 space-y-2 ml-4" {...props}>
                      {children}
                    </ul>
                  ),
                  ol: ({ children, ...props }) => (
                    <ol className="list-decimal list-inside text-base text-text-primary mb-3 space-y-2 ml-4" {...props}>
                      {children}
                    </ol>
                  ),
                  li: ({ children, ...props }) => (
                    <li className="text-base text-text-primary leading-relaxed" {...props}>
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
                    <code className="bg-surface-hover px-2 py-1 rounded text-sm font-mono text-text-primary" {...props}>
                      {children}
                    </code>
                  ),
                  pre: ({ children, ...props }) => (
                    <pre className="bg-surface-hover border border-border-default rounded-lg p-4 overflow-x-auto mb-3" {...props}>
                      {children}
                    </pre>
                  ),
                  blockquote: ({ children, ...props }) => (
                    <blockquote className="border-l-4 border-accent-purple pl-4 italic text-text-secondary my-3" {...props}>
                      {children}
                    </blockquote>
                  ),
                }}
              >
                {section.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}
        </div>
      )}
    </div>
  );
}
