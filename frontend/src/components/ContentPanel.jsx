export default function ContentPanel({ content, onGenerate, busy }) {
  const g = content?.grounding
  return (
    <section className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">Generated Content</h2>
        <button className="btn-primary" onClick={onGenerate} disabled={busy}>
          {busy ? 'Generating…' : "Generate Today's Content"}
        </button>
      </div>

      {!content && (
        <p className="mt-6 rounded-lg border border-dashed border-slate-800 p-6 text-center text-sm text-slate-500">
          Pick a trend, then generate grounded content from retrieved sources.
        </p>
      )}

      {content && (
        <>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
            <span className="badge border-slate-700 bg-slate-800/60 text-slate-300">model: {content.model}</span>
            <span
              className={`badge ${
                content.mode === 'live'
                  ? 'border-emerald-700/60 bg-emerald-900/30 text-emerald-300'
                  : 'border-amber-700/60 bg-amber-900/30 text-amber-300'
              }`}
            >
              {content.mode === 'live' ? 'LLM: live API' : 'LLM: offline composer'}
            </span>
            {content.trend?.topic && (
              <span className="badge border-indigo-700/60 bg-indigo-900/30 text-indigo-300">trend: {content.trend.topic}</span>
            )}
          </div>

          <div className="mt-3 whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-sm leading-relaxed text-slate-100">
            {content.post}
          </div>

          {g && (
            <div className={`mt-3 rounded-lg border p-3 text-xs ${
              g.grounded
                ? 'border-emerald-700/50 bg-emerald-900/20 text-emerald-300'
                : 'border-rose-700/50 bg-rose-900/20 text-rose-300'
            }`}>
              <span className="font-semibold">Grounding indicator:</span>{' '}
              {g.grounded ? 'GROUNDED' : 'NOT GROUNDED'} — {g.sources_referenced}/{g.total_sources} sources referenced
              {g.explicit_citations.length > 0 && <> · explicit citations {g.explicit_citations.map((n) => `[${n}]`).join(' ')}</>}
              <div className="mt-1 text-slate-400">{g.note}</div>
            </div>
          )}

          <div className="mt-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">Sources used</h3>
            <ul className="space-y-1.5">
              {content.sources_used?.map((s, i) => (
                <li key={s.id} className="flex items-center justify-between gap-2 rounded-md border border-slate-800 bg-slate-900/40 px-3 py-1.5 text-xs">
                  <span className="truncate text-slate-300"><span className="mr-1.5 font-mono text-cyan-400">[{i + 1}]</span>{s.title} — {s.source_name}</span>
                  <span className="shrink-0 font-mono text-slate-500">{g?.per_source?.[i]?.explicit_citation ? 'cited' : `${g?.per_source?.[i]?.keyword_overlap_pct ?? 0}% overlap`}</span>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </section>
  )
}
