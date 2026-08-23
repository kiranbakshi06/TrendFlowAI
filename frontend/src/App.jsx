import { useCallback, useEffect, useRef, useState } from 'react'
import StatCard from './components/StatCard.jsx'
import Header from './components/Header.jsx'
import Trends from './components/Trends.jsx'
import Sources from './components/Sources.jsx'
import ContentPanel from './components/ContentPanel.jsx'
import ExecutionPanel from './components/ExecutionPanel.jsx'
import Automation from './components/Automation.jsx'
import Logs from './components/Logs.jsx'

const api = async (path, options) => {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${res.status})`)
  return data
}

export default function App() {
  const [config, setConfig] = useState(null)
  const [stats, setStats] = useState(null)
  const [trends, setTrends] = useState([])
  const [selectedTrend, setSelectedTrend] = useState(null)
  const [sources, setSources] = useState([])
  const [retrieving, setRetrieving] = useState(false)
  const [content, setContent] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [execution, setExecution] = useState(null)
  const [publishing, setPublishing] = useState(false)
  const [logs, setLogs] = useState([])
  const [automation, setAutomation] = useState(null)
  const [error, setError] = useState(null)
  const selectedRef = useRef(null)

  const refreshCore = useCallback(async () => {
    try {
      const [s, l, a] = await Promise.all([api('/stats'), api('/logs'), api('/automation')])
      setStats(s)
      setLogs(l.logs)
      setAutomation(a.automation ?? a)
    } catch (e) {
      setError(String(e.message || e))
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      try {
        setConfig(await api('/config'))
        const t = await api('/trends')
        setTrends(t.trends)
        if (t.trends.length > 0) selectTrend(t.trends[0])
        refreshCore()
      } catch (e) {
        setError(`Backend unreachable (${e.message}). Start it with: uvicorn backend.main:app --port 8000`)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function selectTrend(trend) {
    setSelectedTrend(trend)
    selectedRef.current = trend
    setRetrieving(true)
    try {
      const data = await api('/retrieve', { method: 'POST', body: JSON.stringify({ trend_id: trend.id }) })
      setSources(data.sources)
    } catch (e) {
      setError(e.message)
    } finally {
      setRetrieving(false)
    }
  }

  async function generate() {
    if (!selectedRef.current) return
    setGenerating(true)
    setError(null)
    try {
      setContent(await api('/generate', { method: 'POST', body: JSON.stringify({ trend_id: selectedRef.current.id }) }))
      refreshCore()
    } catch (e) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  async function publish() {
    setPublishing(true)
    setError(null)
    try {
      const res = await fetch('/api/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const data = await res.json()
      if (!res.ok && data.detail && typeof data.detail === 'object') {
        setExecution(data.detail) // structured failure record from the wrapper
      } else if (!res.ok) {
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Publish failed')
      } else {
        setExecution(data)
      }
      refreshCore()
    } catch (e) {
      setError(e.message)
    } finally {
      setPublishing(false)
    }
  }

  async function toggleAutomation() {
    try {
      setAutomation(
        await api('/automation', {
          method: 'POST',
          body: JSON.stringify({ enabled: !automation.enabled, scheduled_time: automation.scheduled_time }),
        })
      )
      refreshCore()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="min-h-screen glow-header">
      <div className="mx-auto max-w-7xl px-4 py-6 lg:px-8">
        <Header config={config} />

        {error && (
          <div className="mb-4 rounded-lg border border-rose-800/60 bg-rose-950/40 p-3 text-sm text-rose-300">{error}</div>
        )}

        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Trends Found" value={stats?.trends_found ?? '—'} accent="text-indigo-300" />
          <StatCard label="Sources Retrieved" value={stats?.sources_retrieved ?? '—'} accent="text-cyan-300" />
          <StatCard label="Posts Generated" value={stats?.posts_generated ?? '—'} accent="text-violet-300" />
          <StatCard label="Swytchcode Executions" value={stats?.swytchcode_executions ?? '—'} accent="text-emerald-300" />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
          <div className="space-y-6 lg:col-span-2">
            <Trends trends={trends} selected={selectedTrend} onSelect={selectTrend} />
            <Sources sources={sources} trend={selectedTrend} busy={retrieving} notice={config?.dataset_notice} />
            <Automation automation={automation} onToggle={toggleAutomation} busy={!automation} />
          </div>

          <div className="space-y-6 lg:col-span-3">
            <ContentPanel content={content} onGenerate={generate} busy={generating || !selectedTrend} />
            <ExecutionPanel
              execution={execution}
              onPublish={publish}
              busy={publishing}
              disabled={!content}
            />
            <Logs logs={logs} />
          </div>
        </div>

        <footer className="mt-8 pb-4 text-center text-xs text-slate-600">
          TrendFlow AI · RAG pipeline + Swytchcode execution · Publishing uses the Swytchcode sandbox (no real posts/payments)
        </footer>
      </div>
    </div>
  )
}
