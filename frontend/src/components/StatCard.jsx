export default function StatCard({ label, value, accent }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 text-3xl font-bold tabular-nums ${accent || 'text-slate-100'}`}>{value}</div>
    </div>
  )
}
