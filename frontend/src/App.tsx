import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  fetchFxHistory,
  fetchLiveHealth,
  fetchMarketOverview,
  fetchNotifications,
  fetchPortfolio,
  fetchPublicConfig,
  fetchRecommendations,
  triggerAdvisoryRun,
  triggerMarketIngest,
  type FxQuote,
  type Recommendation,
} from './lib/api'

const bucketLabel: Record<string, string> = {
  conservative: 'Conservador',
  moderate: 'Moderado',
  aggressive: 'Agresivo',
}

const actionTone: Record<string, string> = {
  BUY: 'text-[var(--positive)]',
  INCREASE: 'text-[var(--positive)]',
  SELL: 'text-[var(--danger)]',
  REDUCE: 'text-[var(--warning)]',
  HOLD: 'text-[var(--muted)]',
}

function money(value: number | string | null | undefined) {
  if (value === null || value === undefined) return '—'
  return `$${Number(value).toLocaleString('en-US', { maximumFractionDigits: 2 })}`
}

function formatRate(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

function latestBySymbol(recs: Recommendation[]) {
  const map = new Map<string, Recommendation>()
  for (const rec of recs) {
    if (!map.has(rec.symbol)) map.set(rec.symbol, rec)
  }
  return Array.from(map.values()).sort((a, b) => a.symbol.localeCompare(b.symbol))
}

function App() {
  const queryClient = useQueryClient()

  const healthQuery = useQuery({ queryKey: ['health'], queryFn: fetchLiveHealth, retry: 1 })
  const configQuery = useQuery({ queryKey: ['config'], queryFn: fetchPublicConfig, retry: 1 })
  const recsQuery = useQuery({ queryKey: ['recommendations'], queryFn: () => fetchRecommendations(false) })
  const marketQuery = useQuery({
    queryKey: ['market'],
    queryFn: fetchMarketOverview,
    refetchOnMount: 'always',
  })
  const trmQuery = useQuery({
    queryKey: ['fx', 'USDCOP_TRM'],
    queryFn: async () => {
      const rows = await fetchFxHistory('USDCOP_TRM', 1)
      return rows[0] ?? null
    },
    refetchOnMount: 'always',
  })
  const spotQuery = useQuery({
    queryKey: ['fx', 'USDCOP_SPOT'],
    queryFn: async () => {
      const rows = await fetchFxHistory('USDCOP_SPOT', 1)
      return rows[0] ?? null
    },
    refetchOnMount: 'always',
  })
  const portfolioQuery = useQuery({ queryKey: ['portfolio'], queryFn: fetchPortfolio })
  const notificationsQuery = useQuery({ queryKey: ['notifications'], queryFn: fetchNotifications })

  const runMutation = useMutation({
    mutationFn: () => triggerAdvisoryRun(true),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['recommendations'] }),
        queryClient.invalidateQueries({ queryKey: ['notifications'] }),
        queryClient.invalidateQueries({ queryKey: ['market'] }),
        queryClient.invalidateQueries({ queryKey: ['fx'] }),
      ])
    },
  })

  const ingestMutation = useMutation({
    mutationFn: () => triggerMarketIngest(60),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['market'] }),
        queryClient.invalidateQueries({ queryKey: ['fx'] }),
      ])
    },
  })

  const apiUp = healthQuery.data?.status === 'ok'
  const latestRecs = latestBySymbol(recsQuery.data ?? [])
  const actionable = latestRecs.filter((r) => r.action !== 'HOLD')
  const chartData =
    marketQuery.data?.etf_latest_features.map((f) => ({
      symbol: f.entity,
      return20d: Number(((f.payload.return_20d ?? 0) * 100).toFixed(2)),
    })) ?? []

  const spotQuote: FxQuote | null =
    marketQuery.data?.usdcop_spot ?? marketQuery.data?.usdcop ?? spotQuery.data ?? null
  const trmQuote: FxQuote | null = marketQuery.data?.usdcop_trm ?? trmQuery.data ?? null

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 md:flex-row md:items-end md:justify-between">
        <div className="flex flex-col gap-3">
          <p className="text-xs uppercase tracking-[0.2em] text-[var(--muted)]">
            Personal Advisory
          </p>
          <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">
            AI Investment Advisor
          </h1>
          <p className="text-sm tracking-wide text-[var(--muted)]">
            por <span className="text-[var(--text)]">Juan Fernando Buitrago</span>
          </p>
          <p className="max-w-2xl text-[var(--muted)]">
            Recomendaciones diarias sobre ETFs US, con contexto USD/COP y guardrails de riesgo.
          </p>
          <div className="flex flex-wrap items-center gap-3 text-sm">
            <span
              className={`rounded-full border border-[var(--border)] px-3 py-1 ${
                apiUp ? 'text-[var(--positive)]' : 'text-[var(--danger)]'
              }`}
            >
              API: {apiUp ? 'online' : healthQuery.isLoading ? 'checking…' : 'offline'}
            </span>
            <span className="rounded-full border border-[var(--border)] px-3 py-1 text-[var(--muted)]">
              Email: {notificationsQuery.data?.[0]?.status ?? 'sin envíos'}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={ingestMutation.isPending || !apiUp}
            onClick={() => ingestMutation.mutate()}
            className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm font-medium text-[var(--text)] transition disabled:opacity-50"
          >
            {ingestMutation.isPending ? 'Actualizando FX…' : 'Actualizar mercado'}
          </button>
          <button
            type="button"
            disabled={runMutation.isPending || !apiUp}
            onClick={() => runMutation.mutate()}
            className="rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition disabled:opacity-50"
          >
            {runMutation.isPending ? 'Ejecutando…' : 'Correr advisory ahora'}
          </button>
        </div>
      </header>

      {runMutation.isSuccess && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] px-4 py-3 text-sm">
          Run #{runMutation.data.run_id} · {runMutation.data.actionable_count} acciones · email:{' '}
          {runMutation.data.email_status ?? 'n/a'}
        </div>
      )}
      {runMutation.isError && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] px-4 py-3 text-sm text-[var(--danger)]">
          {(runMutation.error as Error).message}
        </div>
      )}

      <main className="grid gap-6">
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <Stat
            label="Capital perfil"
            value={
              configQuery.data
                ? money(configQuery.data.available_capital_usd)
                : '—'
            }
          />
          <Stat label="Cash portafolio" value={money(portfolioQuery.data?.cash_usd)} />
          <Stat
            label="USD/COP mercado"
            value={formatRate(spotQuote?.rate)}
            hint={
              spotQuote
                ? `${spotQuote.source} · ${new Date(spotQuote.ts).toLocaleString('es-CO')}`
                : 'Google Finance spot'
            }
          />
          <Stat
            label="USD/COP TRM"
            value={formatRate(trmQuote?.rate)}
            hint={
              trmQuote
                ? `${trmQuote.source} · ${new Date(trmQuote.ts).toLocaleDateString('es-CO')}`
                : 'Sin TRM — pulsa Actualizar mercado'
            }
          />
          <Stat
            label="DXY"
            value={
              marketQuery.data?.dxy
                ? Number(marketQuery.data.dxy.rate).toLocaleString('en-US', {
                    maximumFractionDigits: 2,
                  })
                : '—'
            }
          />
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-medium">Recomendaciones</h2>
                <p className="text-sm text-[var(--muted)]">
                  Última señal por ETF · {actionable.length} accionables
                </p>
              </div>
            </div>

            {recsQuery.isLoading && <p className="text-[var(--muted)]">Cargando…</p>}
            {recsQuery.isError && (
              <p className="text-[var(--danger)]">No se pudieron cargar recomendaciones.</p>
            )}

            <ul className="divide-y divide-[var(--border)]">
              {latestRecs.map((rec) => (
                <li key={rec.id} className="py-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-medium tracking-wide">
                        {rec.symbol}{' '}
                        <span className={`text-sm ${actionTone[rec.action] ?? ''}`}>
                          {rec.action}
                        </span>
                      </p>
                      <p className="mt-1 max-w-xl text-sm text-[var(--muted)]">
                        {rec.explanation?.thesis ?? 'Sin explicación'}
                      </p>
                    </div>
                    <div className="text-right text-sm text-[var(--muted)]">
                      <p>{Number(rec.size_pct ?? 0).toFixed(2)}%</p>
                      <p>{money(rec.size_amount_usd)}</p>
                    </div>
                  </div>
                </li>
              ))}
              {!recsQuery.isLoading && latestRecs.length === 0 && (
                <li className="py-6 text-sm text-[var(--muted)]">
                  Aún no hay runs. Pulsa “Correr advisory ahora”.
                </li>
              )}
            </ul>
          </div>

          <div className="grid gap-6">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-5">
              <h2 className="text-lg font-medium">Retorno 20d</h2>
              <p className="mb-4 text-sm text-[var(--muted)]">Features de mercado v1</p>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid stroke="#2a3542" vertical={false} />
                    <XAxis dataKey="symbol" stroke="#8b9aab" fontSize={11} />
                    <YAxis stroke="#8b9aab" fontSize={11} unit="%" />
                    <Tooltip
                      contentStyle={{
                        background: '#1a222c',
                        border: '1px solid #2a3542',
                        borderRadius: 8,
                      }}
                    />
                    <Bar dataKey="return20d" fill="#3d8bfd" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-5">
              <h2 className="text-lg font-medium">Email reciente</h2>
              {notificationsQuery.data?.[0] ? (
                <div className="mt-3 space-y-2 text-sm">
                  <p>
                    Estado:{' '}
                    <span className="text-[var(--accent)]">
                      {notificationsQuery.data[0].status}
                    </span>
                  </p>
                  <p className="text-[var(--muted)]">{notificationsQuery.data[0].subject}</p>
                  {notificationsQuery.data[0].error_message && (
                    <p className="text-[var(--warning)]">
                      {notificationsQuery.data[0].error_message}
                    </p>
                  )}
                  <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded-lg bg-black/20 p-3 text-xs text-[var(--muted)]">
                    {notificationsQuery.data[0].body.slice(0, 600)}
                  </pre>
                </div>
              ) : (
                <p className="mt-3 text-sm text-[var(--muted)]">
                  Sin notificaciones. Configura Gmail en `.env` para envío real; sin credenciales el
                  sistema guarda el email como <code>skipped</code>.
                </p>
              )}
            </div>
          </div>
        </section>

        {configQuery.data && (
          <section className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-5">
            <h2 className="text-lg font-medium">Universo y caps</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Targets {configQuery.data.allocation_targets.conservative_pct}/
              {configQuery.data.allocation_targets.moderate_pct}/
              {configQuery.data.allocation_targets.aggressive_pct} · perfil{' '}
              {configQuery.data.risk_profile}
            </p>
            <ul className="mt-4 grid gap-2 sm:grid-cols-3">
              {configQuery.data.etf_universe.map((etf) => (
                <li
                  key={etf.symbol}
                  className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
                >
                  <span>
                    {etf.symbol}
                    <span className="ml-2 text-xs text-[var(--muted)]">
                      {bucketLabel[etf.bucket]}
                    </span>
                  </span>
                  <span className="text-[var(--muted)]">max {etf.max_allocation_pct}%</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  )
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-elevated)] p-5">
      <p className="text-xs uppercase tracking-[0.16em] text-[var(--muted)]">{label}</p>
      <p className="mt-2 text-xl font-semibold">{value}</p>
      {hint ? <p className="mt-1 text-xs text-[var(--muted)]">{hint}</p> : null}
    </div>
  )
}

export default App
