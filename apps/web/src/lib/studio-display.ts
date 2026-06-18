/**

 * Central routing for studio asset display kinds.

 * studioType from API / generation wins over content heuristics.

 */



export type StudioDisplayKind =

  | 'quiz'

  | 'flashcards'

  | 'mind_map'

  | 'slide_deck'

  | 'json'

  | 'markdown'

  | 'text';



const FULLSCREEN_TYPES = new Set(['mind_map', 'slide_deck']);



/** Normalize API / legacy type strings to canonical studio type keys. */

export function normalizeStudioType(type?: string): string | undefined {

  if (!type) return undefined;

  const t = type.toLowerCase().trim().replace(/[\s-]+/g, '_');

  if (t === 'mindmap') return 'mind_map';

  if (t === 'slidedeck') return 'slide_deck';

  return t;

}



export function isFullscreenStudioType(studioType?: string, displayKind?: StudioDisplayKind): boolean {

  const normalized = normalizeStudioType(studioType);

  if (normalized && FULLSCREEN_TYPES.has(normalized)) return true;

  if (displayKind && FULLSCREEN_TYPES.has(displayKind)) return true;

  return false;

}



function getContentString(content: unknown): string {

  if (typeof content === 'string') return content;

  if (content && typeof content === 'object') {

    const obj = content as Record<string, unknown>;

    if (typeof obj.content === 'string') return obj.content;

    if (typeof obj.task_type === 'string' && obj.content) {

      return typeof obj.content === 'string' ? obj.content : JSON.stringify(obj.content);

    }

  }

  return '';

}



function heuristicKind(content: unknown): StudioDisplayKind | null {

  if (content === null || content === undefined) return null;



  let parsed: Record<string, unknown> | null = null;

  let contentString = '';



  if (typeof content === 'string') {

    contentString = content;

    try {

      parsed = JSON.parse(content) as Record<string, unknown>;

    } catch {

      parsed = null;

    }

  } else if (typeof content === 'object') {

    parsed = content as Record<string, unknown>;

    if (typeof parsed.content === 'string') contentString = parsed.content;

  }



  const taskType = parsed?.task_type as string | undefined;



  if (taskType === 'quiz' || (parsed?.questions && Array.isArray(parsed.questions))) return 'quiz';

  if (taskType === 'flashcards') return 'flashcards';

  if (Array.isArray(parsed) && parsed[0] && typeof parsed[0] === 'object' && 'front' in (parsed[0] as object)) {

    return 'flashcards';

  }

  if (parsed?.data && Array.isArray((parsed.data as unknown[])) && (parsed.data as unknown[])[0]) {

    const first = (parsed.data as Record<string, unknown>[])[0];

    if (first?.front && first?.back) return 'flashcards';

  }

  if (taskType === 'quiz' || (parsed?.data && (parsed.data as { questions?: unknown[] }).questions)) {

    return 'quiz';

  }



  if (taskType === 'slide_deck') return 'slide_deck';

  if (taskType === 'mind_map') return 'mind_map';



  const text = contentString || (typeof content === 'string' ? content : '');



  if (text) {

    const slidePattern = /(?:^#+\s+.*[Ss]lide\s+\d+|^#+\s+Slide\s+\d+)/m;

    if (slidePattern.test(text)) return 'slide_deck';



    const lines = text.split('\n');

    const topLevelHeaders = lines.filter((line) => {

      const trimmed = line.trim();

      return trimmed.match(/^#{1,2}\s+/) && !trimmed.match(/^#{3,}/);

    });



    if (topLevelHeaders.length >= 3) {

      const hasSlideKeywords = topLevelHeaders.some((h) => /slide|presentation|deck/i.test(h));

      if (hasSlideKeywords) return 'slide_deck';

    }



    if (

      text.match(/^#\s+.+$/m) ||

      (text.includes('# ') && text.split('\n').filter((l) => l.trim().startsWith('#')).length >= 2)

    ) {

      return 'mind_map';

    }



    if (text.includes('```') || text.includes('# ') || text.includes('## ')) return 'markdown';

  }



  if (parsed?.data) return 'json';

  if (typeof content === 'object' && content !== null) return 'json';



  return null;

}



const STUDIO_TYPE_MAP: Record<string, StudioDisplayKind> = {

  quiz: 'quiz',

  flashcards: 'flashcards',

  mind_map: 'mind_map',

  slide_deck: 'slide_deck',

};



export function resolveStudioDisplayKind(

  studioType: string | undefined,

  content: unknown,

): StudioDisplayKind {

  const normalized = normalizeStudioType(studioType);

  if (normalized && STUDIO_TYPE_MAP[normalized]) {

    return STUDIO_TYPE_MAP[normalized];

  }



  const guessed = heuristicKind(content);

  if (guessed) return guessed;



  const text = getContentString(content);

  if (text.includes('```') || text.includes('# ')) return 'markdown';

  if (typeof content === 'object' && content !== null) return 'json';

  return 'text';

}



export function hasStudioContent(content: unknown): boolean {

  if (content === null || content === undefined) return false;

  if (typeof content === 'string') return content.trim().length > 0;

  if (typeof content === 'object') {

    if (Array.isArray(content)) return content.length > 0;

    return Object.keys(content as object).length > 0;

  }

  return false;

}


