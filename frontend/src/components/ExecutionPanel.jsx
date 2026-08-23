export default function ExecutionPanel({ execution, onPublish, busy, disabled }) {
  return (
    <section className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">Swytchcode Execution</h2>
          <p className="mt-1 text-xs text-slate-500">
            Publishes through the real Swytchcode kernel: <code className="text-cyan-400">swytchcode exec stripe.create_payment --demo</code>
          </p>
        </div>
        <button className="btn-secondary border-indigo-500/50 text-indigo-200 hover:bg-indigo-900/30" onClick={onPublish} disabled={busy || disabled}>
          {busy ? 'Executing…' : 'Publish via Swytchcode'}
        </button>
      </div>

      {disabled && !execution && (
        <p className="mt-4 rounded-lg border border-dashed border-slate-800 p-4 text-center text-sm text-slate-500">
          Generate content first — the post is passed to the Swytchcode execution layer.
        </p>
      )}

      {execution && (
        <dl className="mt-4 grid grid-cols-1 gap-2 rounded-lg border border-slate-800 bg-slate-950/60 p-4 text-xs sm:grid-cols-2">
          <Row k="execution requested" v={String(execution.requested)} />
          <Row
            k="status"
            v={
              <span className={`badge ${execution.ok ? 'border-emerald-700/60 bg-emerald-900/30 text-emerald-300' : 'border-rose-700/60 bg-rose-900/30 text-rose-300'}`}>
                {execution.ok ? 'success (exit 0)' : `failed (${execution.error || 'exit ' + execution.exit_code})`}
              </span>
            }
          />
          <Row k="integration / action" v={`${execution.integration}.${execution.action}`} />
          <Row k="mode" v={<span className="badge border-amber-700/60 bg-amber-900/30 text-amber-300">Sandbox execution (demo)</span>} />
          <Row k="timestamp" v={new Date(execution.finished_at).toLocaleString()} />
          <Row k="duration" v={`${execution.duration_ms} ms`} />
          <div className="sm:col-span-2">
            <dt className="mb-1 text-slate-500">returned result</dt>
            <dd>
              <pre className="max-h-40 overflow-auto rounded-md border border-slate-800 bg-black/40 p-3 font-mono text-[11px] text-cyan-100">
{JSON.stringify(execution.data ?? execution, null, 2)}
              </pre>
              {!execution.simulated === false && null}
              {execution.summary && <p className="mt-1 text-slate-400">{execution.summary}</p>}
              {execution.ok && (
                <p className="mt-1 text-amber-400/90">
                  Honest label: this is a Swytchcode sandbox/demo operation. No real social post or live payment was created.
                </p>
              )}
            </dd>
          </div>
        </dl>
      )}
    </section>
  )
}

function Row({ k, v }) {
  return (
    <div>
      <dt className="text-slate-500">{k}</dt>
      <dd className="mt-0.5 font-mono text-[11px] text-slate-200">{v}</dd>
    </div>
  )
}
