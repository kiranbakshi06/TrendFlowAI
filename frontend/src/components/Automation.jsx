export default function Automation({ automation, onToggle, busy }) {
  if (!automation) return null
  const enabled = automation.enabled
  return (
    <section className="card p-5">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">Automation</h2>
      <div className="mt-3 flex items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg">🕖</span>
            <span className="text-sm font-semibold text-slate-100">Daily at 7:00 PM</span>
          </div>
          <p className="mt-1 max-w-xs text-xs text-slate-500">
            Backend asyncio scheduler runs retrieve → generate → sandbox publish once per day at/after 19:00 local time.
            {automation.last_run_date && <> Last run: {automation.last_run_date}.</>}
          </p>
        </div>
        <button
          onClick={onToggle}
          disabled={busy}
          className={`relative h-7 w-13 shrink-0 rounded-full border transition ${
            enabled ? 'border-emerald-600 bg-emerald-900/50' : 'border-slate-700 bg-slate-800'
          }`}
          style={{ width: '3.25rem' }}
          aria-label="Toggle daily automation"
        >
          <span
            className={`absolute top-0.5 h-5.5 w-5.5 rounded-full transition-all ${
              enabled ? 'left-[1.6rem] bg-emerald-400' : 'left-0.5 bg-slate-500'
            }`}
            style={{ height: '1.375rem', width: '1.375rem' }}
          />
        </button>
      </div>
      <p className={`mt-3 badge ${enabled ? 'border-emerald-700/60 bg-emerald-900/30 text-emerald-300' : 'border-slate-700 bg-slate-800/60 text-slate-400'}`}>
        {enabled ? 'Active — scheduled workflow enabled' : 'Inactive'}
      </p>
    </section>
  )
}
