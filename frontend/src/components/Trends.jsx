function Bar({ pct }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
      <div
        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-cyan-400"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export default function Trends({ trends, selected, onSelect }) {
  return (
    <section className="card p-5">
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wider text-cyan-300">Current Trends</h2>
      <p className="mb-4 text-xs text-slate-500">Derived from the local demo dataset by tag clustering + TF-IDF coverage.</p>
      <ul className="space-y-2">
        {trends.map((t) => (
          <li key={t.id}>
            <button
              onClick={() => onSelect(t)}
              className={`w-full rounded-lg border p-3 text-left transition ${
                selected?.id === t.id
                  ? 'border-indigo-500/60 bg-indigo-500/10'
                  : 'border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-semibold text-slate-100">{t.topic}</span>
                <span className="shrink-0 text-xs font-mono text-cyan-300">{t.relevance_score}%</span>
              </div>
              <div className="mt-2"><Bar pct={t.relevance_score} /></div>
              <div className="mt-2 text-xs text-slate-500">{t.doc_count} source{t.doc_count > 1 ? 's' : ''} · {t.summary}</div>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
