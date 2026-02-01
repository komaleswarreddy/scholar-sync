/**
 * Report Display Component
 * 
 * Displays formatted reports with Markdown rendering, section detection,
 * and print/export functionality.
 * Styled to match NotebookLM design system.
 */

'use client';

import { useState, useMemo } from 'react';
import { FileText, Download, Printer, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '../ui/Button';
import { exportAsPDF } from '@/lib/export-utils';

interface ReportDisplayProps {
  reportData: string | object;
}

interface ReportSection {
  title: string;
  content: string;
  level: number;
}

export function ReportDisplay({ reportData }: ReportDisplayProps) {
  const [copied, setCopied] = useState(false);

  // Parse report data
  const parseReportData = (): string | null => {
    try {
      let content: string = '';
      
      if (typeof reportData === 'string') {
        content = reportData;
      } else if (typeof reportData === 'object' && reportData !== null) {
        const parsed = reportData as any;
        // Handle response structure: { task_type: "report", content: "..." }
        if (parsed.content) {
          content = parsed.content;
        } else if (parsed.task_type === 'report' && parsed.content) {
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
      console.error('Failed to parse report data:', error);
      return null;
    }
  };

  const markdownContent = parseReportData();

  if (!markdownContent) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <p className="text-sm text-text-secondary">
            Invalid report data. Please ensure the report is properly formatted.
          </p>
        </div>
      </div>
    );
  }

  // Parse sections from markdown
  const parseSections = (content: string): ReportSection[] => {
    const lines = content.split('\n');
    const sections: ReportSection[] = [];
    let currentSection: ReportSection | null = null;
    let currentContent: string[] = [];

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
        const level = headerMatch[1].length;
        const title = headerMatch[2].trim();
        currentSection = {
          title,
          content: '',
          level,
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
              title: 'Report',
              content: '',
              level: 1,
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
        title: 'Report',
        content: markdownContent,
        level: 1,
      }];
    }

    return sections;
  };

  const sections = useMemo(() => parseSections(markdownContent), [markdownContent]);

  // Common section titles to highlight
  const importantSections = [
    'executive summary',
    'key points',
    'detailed analysis',
    'conclusions',
    'conclusion',
    'summary',
    'introduction',
    'findings',
    'recommendations',
  ];

  const isImportantSection = (title: string): boolean => {
    return importantSections.some(important => 
      title.toLowerCase().includes(important)
    );
  };

  // Handle copy to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(markdownContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Silently fail
    }
  };

  // Handle print
  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>Report</title>
            <style>
              body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                line-height: 1.6;
                color: #202124;
              }
              h1 { font-size: 2em; margin-top: 0; }
              h2 { font-size: 1.5em; margin-top: 1.5em; border-bottom: 2px solid #4285F4; padding-bottom: 0.5em; }
              h3 { font-size: 1.25em; margin-top: 1.25em; }
              p { margin: 1em 0; }
              ul, ol { margin: 1em 0; padding-left: 2em; }
              code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }
              pre { background: #f5f5f5; padding: 1em; border-radius: 5px; overflow-x: auto; }
              @media print {
                body { margin: 0; padding: 20px; }
              }
            </style>
          </head>
          <body>
            ${markdownContent.split('\n').map(line => {
              if (line.match(/^#{1,6}\s/)) {
                const level = line.match(/^(#{1,6})/)?.[1].length || 1;
                const text = line.replace(/^#{1,6}\s+/, '');
                return `<h${level}>${text}</h${level}>`;
              }
              return line;
            }).join('\n')}
          </body>
        </html>
      `);
      printWindow.document.close();
      printWindow.focus();
      setTimeout(() => {
        printWindow.print();
      }, 250);
    }
  };

  // Handle export as PDF
  const handleExport = () => {
    // Convert markdown to HTML for PDF export
    const reportHTML = `
      <h1>Report</h1>
      ${sections.map(section => `
        <div style="margin-bottom: 2em;">
          <h${section.level} style="margin-top: 1.5em; margin-bottom: 0.5em;">
            ${section.title}
          </h${section.level}>
          <div>${section.content.replace(/\n/g, '<br>')}</div>
        </div>
      `).join('')}
    `;
    exportAsPDF(reportHTML, `report-${Date.now()}`, 'Report');
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center">
            <FileText className="w-5 h-5 text-accent-blue" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-text-primary">Report</h3>
            <p className="text-sm text-text-secondary">
              {sections.length} {sections.length === 1 ? 'section' : 'sections'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCopy}
            className="flex items-center gap-2"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy
              </>
            )}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleExport}
            className="flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export PDF
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handlePrint}
            className="flex items-center gap-2"
          >
            <Printer className="w-4 h-4" />
            Print
          </Button>
        </div>
      </div>

      {/* Report Content */}
      <div className="bg-surface-subtle rounded-xl border border-border-default p-6">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h1: ({ children, ...props }) => (
                <h1 className="text-3xl font-bold text-text-primary mt-8 mb-4 pb-3 border-b-2 border-accent-blue/30" {...props}>
                  {children}
                </h1>
              ),
              h2: ({ children, ...props }) => {
                const title = String(children);
                const isImportant = isImportantSection(title);
                return (
                  <h2 
                    className={`text-2xl font-semibold text-text-primary mt-6 mb-3 pb-2 scroll-mt-4 transition-colors ${
                      isImportant ? 'border-b-2 border-accent-blue/20' : 'border-b border-border-default'
                    } highlight-section:bg-accent-blue/10 highlight-section:rounded highlight-section:px-2 highlight-section:py-1`}
                    {...props}
                  >
                    {children}
                  </h2>
                );
              },
              h3: ({ children, ...props }) => (
                <h3 className="text-xl font-semibold text-text-primary mt-5 mb-2" {...props}>
                  {children}
                </h3>
              ),
              h4: ({ children, ...props }) => (
                <h4 className="text-lg font-semibold text-text-primary mt-4 mb-2" {...props}>
                  {children}
                </h4>
              ),
              p: ({ children, ...props }) => (
                <p className="text-base text-text-primary leading-relaxed mb-4" {...props}>
                  {children}
                </p>
              ),
              ul: ({ children, ...props }) => (
                <ul className="list-disc list-inside text-base text-text-primary mb-4 space-y-2 ml-4" {...props}>
                  {children}
                </ul>
              ),
              ol: ({ children, ...props }) => (
                <ol className="list-decimal list-inside text-base text-text-primary mb-4 space-y-2 ml-4" {...props}>
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
                <pre className="bg-surface-hover border border-border-default rounded-lg p-4 overflow-x-auto mb-4" {...props}>
                  {children}
                </pre>
              ),
              blockquote: ({ children, ...props }) => (
                <blockquote className="border-l-4 border-accent-blue pl-4 italic text-text-secondary my-4" {...props}>
                  {children}
                </blockquote>
              ),
              hr: ({ ...props }) => (
                <hr className="border-border-default my-6" {...props} />
              ),
              table: ({ children, ...props }) => (
                <div className="overflow-x-auto my-4">
                  <table className="min-w-full border-collapse border border-border-default rounded-lg" {...props}>
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children, ...props }) => (
                <thead className="bg-surface-hover" {...props}>
                  {children}
                </thead>
              ),
              th: ({ children, ...props }) => (
                <th className="border border-border-default px-4 py-2 text-left font-semibold text-text-primary" {...props}>
                  {children}
                </th>
              ),
              td: ({ children, ...props }) => (
                <td className="border border-border-default px-4 py-2 text-text-primary" {...props}>
                  {children}
                </td>
              ),
            }}
          >
            {markdownContent}
          </ReactMarkdown>
        </div>
      </div>

      {/* Section Navigation (Optional) */}
      {sections.length > 1 && (
        <div className="bg-surface-subtle rounded-xl border border-border-default p-4">
          <p className="text-sm font-semibold text-text-secondary mb-3">Sections:</p>
          <div className="flex flex-wrap gap-2">
            {sections.map((section, index) => {
              const sectionId = `section-${index}-${section.title.toLowerCase().replace(/\s+/g, '-')}`;
              return (
                <button
                  key={index}
                  onClick={() => {
                    // Find the heading element by searching through all headings
                    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                    headings.forEach((heading) => {
                      if (heading.textContent?.trim() === section.title) {
                        heading.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        // Highlight briefly
                        heading.classList.add('highlight-section');
                        setTimeout(() => {
                          heading.classList.remove('highlight-section');
                        }, 1000);
                      }
                    });
                  }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    isImportantSection(section.title)
                      ? 'bg-accent-blue/10 text-accent-blue hover:bg-accent-blue/20'
                      : 'bg-surface-hover text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                  }`}
                >
                  {section.title}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
