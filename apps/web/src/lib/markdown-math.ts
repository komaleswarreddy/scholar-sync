/**
 * Normalize LLM markdown + LaTeX before remark-math / rehype-katex parsing.
 */

/** Collapse extra blank lines while preserving paragraph/list structure. */
function normalizeBlankLines(text: string): string {
  return text.replace(/\n{3,}/g, '\n\n').trim();
}

/** Ensure display math delimiters sit on their own lines for reliable parsing. */
function normalizeDisplayMathDelimiters(text: string): string {
  return text
    .replace(/\\\[\s*/g, '\n$$\n')
    .replace(/\s*\\\]/g, '\n$$\n')
    .replace(/\$\$\s*\n\s*\$\$/g, '\n$$\n');
}

/** Convert \( ... \) inline delimiters to $ ... $ for remark-math. */
function normalizeInlineMathDelimiters(text: string): string {
  return text.replace(/\\\((.+?)\\\)/gs, (_, expr: string) => `$${expr.trim()}$`);
}

/** Add spacing around binary operators so ×, ·, and ÷ read clearly. */
function normalizeMathOperators(expr: string): string {
  return expr
    .replace(/(\d)\s*[xX×]\s*(\d)/g, '$1 \\times $2')
    .replace(/(\d)\s*\\times\s*(\d)/g, '$1 \\times $2')
    .replace(/\\times(\d)/g, '\\times $1')
    .replace(/(\d)\\times/g, '$1 \\times')
    .replace(/\\cdot(\d)/g, '\\cdot $1')
    .replace(/(\d)\\cdot/g, '$1 \\cdot')
    .replace(/(\d)\s*\\div\s*(\d)/g, '$1 \\div $2');
}

/** Wrap bare unit literals in \\text{} for upright, readable units. */
function normalizeMathUnits(expr: string): string {
  return expr
    .replace(/(\d)\s+km\/h/gi, '$1\\,\\text{ km/h}')
    .replace(/(\d)\s+m\/s\^2/gi, '$1\\,\\text{ m/s}^2')
    .replace(/(\d)\s+m\/s(?!\^)/gi, '$1\\,\\text{ m/s}');
}

function polishMathExpression(expr: string): string {
  return normalizeMathUnits(normalizeMathOperators(expr.trim()));
}

/** Normalize math inside $$...$$ and $...$ segments. */
function normalizeMathSegments(text: string): string {
  let out = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, math: string) => {
    return `$$\n${polishMathExpression(math)}\n$$`;
  });
  out = out.replace(/(?<!\$)\$([^$\n]+?)\$(?!\$)/g, (_, math: string) => {
    return `$${polishMathExpression(math)}$`;
  });
  return out;
}

/** Normalize PDF dash/minus glyphs to ASCII hyphen for math parsing. */
function normalizePdfDashes(text: string): string {
  return text.replace(/[\u2010\u2011\u2012\u2013\u2014\u2212\uFE58\uFE63\uFF0D]/g, '-');
}

/** Map PDF Symbol-font private-use glyphs (common in exam PDFs) to LaTeX tokens. */
function replacePdfPrivateUseSymbols(text: string): string {
  let out = text;

  // Postfix transpose/prime attached to a variable (e.g. A\uF0A2 or A \uF0A2).
  out = out.replace(/([A-Za-z0-9])\s*\uF0A2/g, '$1^{\\prime}');

  const standalone: Record<string, string> = {
    '\uF0A3': '\\leq ',
    '\uF0B1': '\\pm ',
    '\uF0B3': '\\geq ',
    '\uF0B9': '\\neq ',
    '\uF06C': '\\lambda ',
    '\uF070': '\\pi ',
    '\uF044': '\\Delta ',
  };
  for (const [glyph, latex] of Object.entries(standalone)) {
    out = out.split(glyph).join(latex);
  }

  // Unicode primes/apostrophes on identifiers -> LaTeX prime.
  out = out.replace(/([A-Za-z0-9])['\u02B9\u2032\u2019]/g, '$1^{\\prime}');

  // Drop any remaining private-use symbols that would render as tofu boxes.
  out = out.replace(/[\uF000-\uF0FF]/g, '');
  return out;
}

/** Wrap extracted math fragments so remark-math can render them with KaTeX. */
function isInsideInlineMath(text: string, index: number): boolean {
  let open = false;
  for (let i = 0; i < index; i += 1) {
    if (text[i] === '$') open = !open;
  }
  return open;
}

function wrapExtractedMathFragments(text: string): string {
  let out = text;

  out = out.replace(/\^([ijk])\b/g, '^{\\hat $1}');

  const algebraCore = '[A-Za-z0-9](?:\\s*[+\\-]\\s*[A-Za-z0-9](?:\\^\\{\\\\prime\\})?)';

  // Parenthesized algebra e.g. (A - A^{\prime}).
  out = out.replace(new RegExp(`\\(\\s*(${algebraCore})\\s*\\)`, 'g'), (_, expr: string) => {
    return `$(${expr.replace(/\s+/g, ' ').trim()})$`;
  });

  // Inline algebra in running text e.g. A + A^{\prime}.
  out = out.replace(new RegExp(algebraCore, 'g'), (match, offset, whole) => {
    if (isInsideInlineMath(whole, offset)) return match;
    return `$${match}$`;
  });

  return out;
}

/**
 * Preprocess extracted source-question text (PDF glyphs + math) for RichMarkdown.
 */
export function preprocessSourceQuestionText(raw: string): string {
  if (!raw?.trim()) return '';

  let text = raw.replace(/\r\n/g, '\n');
  text = normalizePdfDashes(text);
  text = replacePdfPrivateUseSymbols(text);
  text = wrapExtractedMathFragments(text);
  // Keep option rows on separate lines when rendered as markdown.
  text = text.replace(/\n(?!\n)/g, '  \n');
  return preprocessMarkdownMath(text);
}

/**
 * Preprocess assistant markdown so lists, paragraphs, and LaTeX render cleanly.
 */
export function preprocessMarkdownMath(raw: string): string {
  if (!raw?.trim()) return '';

  let text = raw.replace(/\r\n/g, '\n');

  // LLM sometimes emits escaped backslashes in JSON — unescape common patterns.
  text = text.replace(/\\\\\[/g, '\\[').replace(/\\\\\]/g, '\\]').replace(/\\\\\(/g, '\\(').replace(/\\\\\)/g, '\\)');

  text = normalizeDisplayMathDelimiters(text);
  text = normalizeInlineMathDelimiters(text);
  text = normalizeMathSegments(text);
  text = normalizeBlankLines(text);

  return text;
}
