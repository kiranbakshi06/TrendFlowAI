export default function Sources({ sources, trend, busy, notice }) {
  return (
    <section className="card p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">RAG Sources</h2>
      <p className="mt-1 mb-4 text-xs text-slate-500">
        Retrieved for <span className="text-indigo-300">{trend?.topic || '—'}</span> · TF-IDF cosine similarity over the local dataset.
        {notice && <span className="ml-1 text-amber-400/80">{notice}</span>}
      </p>

      {busy && <p className="animate-pulse text-xs text-slate-500">Retrieving…</p>}

      <ul className="space-y-3">
        {sources.map((s) => (
          <li key={s.id} className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-100">
                  {s.url ? (
                    <a href={s.url} target="_blank" rel="noreferrer" className="hover:text-cyan-300 hover:underline">{s.title}</a>
                  ) : s.title}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {s.source_name} · {s.published_at}
                  {s.origin === 'live' && <span className="ml-2 badge border-emerald-700/60 bg-emerald-900/30 text-emerald-300">LIVE</span>}
                  {s.origin === 'demo' && <span className="ml-2 badge border-slate-700 bg-slate-800/60 text-slate-400">DEMO</span>}
                </p>
              </div>
              <span className="shrink-0 rounded-md border border-cyan-800/60 bg-cyan-900/20 px-2 py-0.5 font-mono text-[11px] text-cyan-300">
                {s.relevance_pct}%
              </span>
            </div>
            <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-400">{s.excerpt}</p>
          </li>
        ))}
      </ul>
      {!busy && sources.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-800 p-4 text-center text-xs text-slate-500">No sources yet.</p>
      )}
    </section>
  )
}
