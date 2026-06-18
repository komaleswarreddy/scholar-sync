'use client';

import type { Components } from 'react-markdown';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { preprocessMarkdownMath, preprocessSourceQuestionText } from '@/lib/markdown-math';
import psStyles from '@/components/tutor/tutor-mode.module.css';

export type RichMarkdownVariant = 'chat' | 'problem-solver' | 'source-question';

type RichMarkdownProps = {
  content: string;
  className?: string;
  variant?: RichMarkdownVariant;
};

function chatComponents(): Components {
  return {
    h1: ({ children, ...props }) => (
      <h1 className="text-2xl font-bold text-text-primary mt-6 mb-3 first:mt-0" {...props}>
        {children}
      </h1>
    ),
    h2: ({ children, ...props }) => (
      <h2 className="text-xl font-semibold text-text-primary mt-6 mb-2 first:mt-0" {...props}>
        {children}
      </h2>
    ),
    h3: ({ children, ...props }) => (
      <h3 className="text-lg font-semibold text-text-primary mt-5 mb-2 first:mt-0" {...props}>
        {children}
      </h3>
    ),
    ul: ({ children, ...props }) => (
      <ul className="list-disc list-outside space-y-2 my-4 ml-5 pl-1" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }) => (
      <ol className="list-decimal list-outside space-y-2 my-4 ml-5 pl-1" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => (
      <li className="text-text-primary" {...props}>
        {children}
      </li>
    ),
    code: ({ children, className, ...props }) => {
      const isInline = !className;
      return isInline ? (
        <code
          className="bg-surface-subtle px-1.5 py-0.5 rounded text-sm font-mono text-text-primary"
          {...props}
        >
          {children}
        </code>
      ) : (
        <code
          className="block bg-surface-subtle p-3 rounded-lg text-sm font-mono text-text-primary overflow-x-auto my-3"
          {...props}
        >
          {children}
        </code>
      );
    },
    p: ({ children, ...props }) => (
      <p className="mb-3 last:mb-0 leading-relaxed" {...props}>
        {children}
      </p>
    ),
    br: () => <br />,
    hr: () => <hr className="my-5 border-0 border-t border-border-default" />,
    strong: ({ children, ...props }) => (
      <strong className="font-semibold text-text-primary" {...props}>
        {children}
      </strong>
    ),
    em: ({ children, ...props }) => (
      <em className="italic" {...props}>
        {children}
      </em>
    ),
  };
}

function sourceQuestionComponents(): Components {
  return {
    p: ({ children, ...props }) => (
      <p className="mb-2 last:mb-0 leading-relaxed text-text-primary" {...props}>
        {children}
      </p>
    ),
    ul: ({ children, ...props }) => (
      <ul className="list-disc list-outside space-y-1 my-2 ml-4" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }) => (
      <ol className="list-decimal list-outside space-y-1 my-2 ml-4" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => (
      <li className="text-text-primary" {...props}>
        {children}
      </li>
    ),
    strong: ({ children, ...props }) => (
      <strong className="font-semibold text-text-primary" {...props}>
        {children}
      </strong>
    ),
  };
}

function problemSolverComponents(): Components {
  return {
    h1: ({ children, ...props }) => (
      <h3 className={psStyles.psResponseHeading} {...props}>
        {children}
      </h3>
    ),
    h2: ({ children, ...props }) => (
      <h3 className={psStyles.psResponseHeading} {...props}>
        {children}
      </h3>
    ),
    h3: ({ children, ...props }) => (
      <h4 className={psStyles.psResponseHeading} {...props}>
        {children}
      </h4>
    ),
    ul: ({ children, ...props }) => (
      <ul className={psStyles.psMarkdownList} {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }) => (
      <ol className={psStyles.psMarkdownOrderedList} {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => (
      <li className={psStyles.psMarkdownListItem} {...props}>
        {children}
      </li>
    ),
    p: ({ children, ...props }) => (
      <p {...props}>{children}</p>
    ),
    strong: ({ children, ...props }) => (
      <strong className={psStyles.psMarkdownStrong} {...props}>
        {children}
      </strong>
    ),
    code: ({ children, className, ...props }) => {
      const isInline = !className;
      return isInline ? (
        <code className={psStyles.psMarkdownCode} {...props}>
          {children}
        </code>
      ) : (
        <code className={psStyles.psMarkdownCodeBlock} {...props}>
          {children}
        </code>
      );
    },
  };
}

export function RichMarkdown({
  content,
  className,
  variant = 'chat',
}: RichMarkdownProps) {
  const processed =
    variant === 'source-question'
      ? preprocessSourceQuestionText(content)
      : preprocessMarkdownMath(content);
  if (!processed) return null;

  const components =
    variant === 'problem-solver'
      ? problemSolverComponents()
      : variant === 'source-question'
        ? sourceQuestionComponents()
        : chatComponents();
  const rootClass =
    variant === 'problem-solver'
      ? [psStyles.psRichMarkdown, className].filter(Boolean).join(' ')
      : variant === 'source-question'
        ? [psStyles.psRichMarkdown, 'source-question-detail', className].filter(Boolean).join(' ')
        : className;

  return (
    <div className={rootClass || undefined}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}
