function Row({ k, v }) {
  return (
    <div>
      <dt className="text-slate-500">{k}</dt>
      <dd className="mt-0.5 font-mono text-[11px] text-slate-200">{v}</dd>
    </div>
  )
}

export default function ExecutionPanel({ execution, onPublish, busy, disabled }) {
  return (
    <section className="card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-cyan-300">Swytchcode Execution</h2>
          <p className="mt-1 text-xs text-slate-500">
            Step 1 — real kernel validation: <code className="text-cyan-400">swytchcode exec ahrefs.social-media.post.create --explain</code> (no network).{' '}
            Step 2 — clearly-labeled simulated publish.
          </p>
        </div>
        <button className="btn-secondary border-indigo-500/50 text-indigo-200 hover:bg-indigo-900/30" onClick={onPublish} disabled={busy || disabled}>
          {busy ? 'Executing…' : 'Publish via Swytchcode'}
        </button>
      </div>

      {disabled && !execution && (
        <p className="mt-4 rounded-lg border border-dashed border-slate-800 p-4 text-center text-sm text-slate-500">
          Generate content first — the post is passed through the Swytchcode execution layer.
        </p>
      )}

      {execution?.preflight && (
        <dl className="mt-4 grid grid-cols-1 gap-2 rounded-lg border border-cyan-900/60 bg-slate-950/60 p-4 text-xs sm:grid-cols-2">
          <div className="sm:col-span-2 text-[11px] font-semibold uppercase tracking-wider text-cyan-400">
            1 · Swytchcode preflight (explain mode)
          </div>
          <Row k="execution requested" v={String(execution.preflight.requested)} />
          <Row
            k="validation status"
            v={
              <span className={`badge ${execution.preflight.ok ? 'border-emerald-700/60 bg-emerald-900/30 text-emerald-300' : 'border-rose-700/60 bg-rose-900/30 text-rose-300'}`}>
                {execution.preflight.ok ? 'validated (exit 0)' : 'failed'}
              </span>
            }
          />
          <Row k="integration / action" v={`${execution.preflight.integration}.${execution.preflight.action}`} />
          <Row k="mode" v={`swytchcode:${execution.preflight.mode} — no network call`} />
          <Row k="timestamp" v={new Date(execution.preflight.finished_at).toLocaleString()} />
          <Row k="duration" v={`${execution.preflight.duration_ms} ms`} />
        </dl>
      )}

      {execution?.publish && (
        <dl className="mt-3 grid grid-cols-1 gap-2 rounded-lg border border-amber-900/60 bg-slate-950/60 p-4 text-xs sm:grid-cols-2">
          <div className="sm:col-span-2 text-[11px] font-semibold uppercase tracking-wider text-amber-400">
            2 · Publish action
          </div>
          <Row k="status" v={<span className="badge border-emerald-700/60 bg-emerald-900/30 text-emerald-300">success</span>} />
          <Row k="integration / action" v={`${execution.publish.integration}.${execution.publish.action}`} />
          <Row k="mode" v={<span className="badge border-amber-700/60 bg-amber-900/30 text-amber-300">SIMULATED — sandbox only</span>} />
          <Row k="post id" v={execution.publish.post_id} />
          <Row k="timestamp" v={new Date(execution.publish.timestamp).toLocaleString()} />
          <Row k="platform" v={execution.publish.platform} />
          <div className="sm:col-span-2 mt-1 rounded-md border border-amber-800/40 bg-amber-950/20 p-2 text-[11px] text-amber-200/90">
            Honest label: this post was <b>not</b> published to any real social network. No real social publishing integration was available without provider credentials; the Swytchcode preflight above demonstrates the genuine kernel execution path.
          </div>
        </dl>
      )}
    </section>
  )
}
