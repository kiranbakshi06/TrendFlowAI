export default function Logs({ logs }) {
  return (
    <section className="card p-5">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-cyan-300">Execution Logs</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-slate-500">
              <th className="pb-2 pr-3 font-medium uppercase tracking-wider">Timestamp</th>
              <th className="pb-2 pr-3 font-medium uppercase tracking-wider">Action</th>
              <th className="pb-2 pr-3 font-medium uppercase tracking-wider">Integration</th>
              <th className="pb-2 pr-3 font-medium uppercase tracking-wider">Status</th>
              <th className="pb-2 font-medium uppercase tracking-wider">Result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/70">
            {logs.map((log, i) => (
              <tr key={`${log.timestamp}-${i}`} className="align-top text-slate-300">
                <td className="whitespace-nowrap py-2 pr-3 font-mono text-[11px] text-slate-500">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </td>
                <td className="py-2 pr-3">{log.action}</td>
                <td className="py-2 pr-3 font-mono text-[11px] text-cyan-300">{log.integration}</td>
                <td className="py-2 pr-3">
                  <span className={`badge ${log.status === 'success' ? 'border-emerald-700/60 bg-emerald-900/30 text-emerald-300' : 'border-rose-700/60 bg-rose-900/30 text-rose-300'}`}>
                    {log.status}
                  </span>
                </td>
                <td className="py-2 text-slate-400">{log.result_summary}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr><td colSpan={5} className="py-4 text-center text-slate-500">No executions yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
