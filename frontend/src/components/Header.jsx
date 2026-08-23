export default function Header({ config }) {
  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 text-lg font-black text-white">TF</div>
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">
            TrendFlow <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">AI</span>
          </h1>
          <p className="text-xs text-slate-500">Autonomous RAG Content Engine</p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {config && (
          <>
            <span className={`badge ${config.llm_mode === 'live' ? 'border-emerald-700/60 bg-emerald-900/30 text-emerald-300' : 'border-amber-700/60 bg-amber-900/30 text-amber-300'}`}>
              LLM: {config.llm_mode === 'live' ? 'live API' : 'offline composer'}
            </span>
            <span className={`badge ${config.swytchcode_available ? 'border-cyan-700/60 bg-cyan-900/30 text-cyan-300' : 'border-rose-700/60 bg-rose-900/30 text-rose-300'}`}>
              Swytchcode CLI: {config.swytchcode_available ? 'detected' : 'missing'}
            </span>
          </>
        )}
        <span className="badge border-slate-700 bg-slate-800/60 text-slate-400">demo source data</span>
      </div>
    </header>
  )
}
