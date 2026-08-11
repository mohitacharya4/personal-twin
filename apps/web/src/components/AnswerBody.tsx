import { Fragment } from 'react';

import type { Citation } from '../types';

interface Props {
  text: string;
  citations: Citation[];
  streaming: boolean;
  onCite: (marker: number) => void;
}

const MARKER = /\[(\d+)\]/g;

/** Render answer text with inline, clickable [n] citation pills and paragraph breaks. */
export function AnswerBody({ text, citations, streaming, onCite }: Props) {
  const byMarker = new Map(citations.map((c) => [c.marker, c]));
  const paragraphs = text.split(/\n{2,}/);

  return (
    <div className="space-y-2.5 text-[15px] leading-relaxed">
      {paragraphs.map((para, pi) => (
        <p key={pi} className="whitespace-pre-wrap">
          {renderInline(para, byMarker, onCite)}
          {streaming && pi === paragraphs.length - 1 && (
            <span className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[0.15em] animate-blink bg-violet align-baseline" />
          )}
        </p>
      ))}
    </div>
  );
}

function renderInline(
  text: string,
  byMarker: Map<number, Citation>,
  onCite: (marker: number) => void,
) {
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const match of text.matchAll(MARKER)) {
    const marker = Number(match[1]);
    const start = match.index ?? 0;
    if (start > last) nodes.push(<Fragment key={key++}>{text.slice(last, start)}</Fragment>);
    const cite = byMarker.get(marker);
    nodes.push(
      <button
        key={key++}
        type="button"
        onClick={() => onCite(marker)}
        className="cite-pill focus-ring"
        title={cite ? `Source: ${cite.title}` : `Source ${marker}`}
      >
        {marker}
      </button>,
    );
    last = start + match[0].length;
  }
  if (last < text.length) nodes.push(<Fragment key={key++}>{text.slice(last)}</Fragment>);
  return nodes;
}
