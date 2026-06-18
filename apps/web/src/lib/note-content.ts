const NOTE_TITLE_SEPARATOR = '\n---\n';

export function stripHtml(html: string): string {
  if (!html) return '';
  if (typeof document !== 'undefined') {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
  }
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

export function serializeNoteContent(title: string, bodyHtml: string): string {
  const safeTitle = title.trim() || 'New Note';
  const body = bodyHtml.trim();
  if (!body) return safeTitle;
  return `${safeTitle}${NOTE_TITLE_SEPARATOR}${body}`;
}

export function parseNoteContent(raw: string): { title: string; bodyHtml: string } {
  const content = raw || '';
  const sepIndex = content.indexOf(NOTE_TITLE_SEPARATOR);
  if (sepIndex >= 0) {
    const title = content.slice(0, sepIndex).trim() || 'Untitled note';
    const bodyHtml = content.slice(sepIndex + NOTE_TITLE_SEPARATOR.length);
    return { title, bodyHtml };
  }

  const plain = stripHtml(content);
  const firstLine = plain.split('\n').map((l) => l.trim()).find(Boolean) || 'Untitled note';
  const looksLikeHtml = /<\/?[a-z][\s\S]*>/i.test(content);
  return {
    title: firstLine.length > 80 ? `${firstLine.slice(0, 80)}…` : firstLine,
    bodyHtml: looksLikeHtml ? content : content ? `<p>${escapeHtml(content)}</p>` : '',
  };
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export { escapeHtml };

export function notePreviewTitle(content?: string): string {
  const { title } = parseNoteContent(content || '');
  if (!title || title === 'Untitled note') return 'Untitled note';
  return title.length > 48 ? `${title.slice(0, 48)}…` : title;
}
