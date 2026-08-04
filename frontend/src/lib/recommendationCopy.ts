import type { Recommendation } from './api'
import type { Locale } from '../i18n/translations'

export type ThesisMetrics = {
  score?: number
  weightPct?: number
  capPct?: number
  return20d?: number
  vol20d?: number
  reasonKeys: string[]
}

const REASON_KEYS = [
  'no_edge_hold',
  'momentum_and_trend_support_entry',
  'weak_momentum_suggests_trim',
  'leveraged_blocked_by_regime_or_profile',
] as const

const ACTION_SUMMARY: Record<string, Record<Locale, (symbol: string) => string>> = {
  HOLD: {
    es: (s) => `Mantener ${s}. No hay ventaja clara para cambiar la posición.`,
    en: (s) => `Hold ${s}. No clear edge to change the position.`,
  },
  BUY: {
    es: (s) => `Comprar ${s}. El momentum y el margen de asignación apoyan una entrada.`,
    en: (s) => `Buy ${s}. Momentum and allocation room support an entry.`,
  },
  INCREASE: {
    es: (s) => `Aumentar ${s}. La señal favorece incrementar dentro del tope.`,
    en: (s) => `Increase ${s}. The signal favors adding within the cap.`,
  },
  SELL: {
    es: (s) => `Vender ${s}. El momentum débil sugiere salir de la posición.`,
    en: (s) => `Sell ${s}. Weak momentum suggests exiting the position.`,
  },
  REDUCE: {
    es: (s) => `Reducir ${s}. El momentum débil sugiere recortar exposición.`,
    en: (s) => `Reduce ${s}. Weak momentum suggests trimming exposure.`,
  },
}

function parseNumber(raw: string | undefined): number | undefined {
  if (!raw) return undefined
  const n = Number(raw)
  return Number.isFinite(n) ? n : undefined
}

export function splitThesis(thesis: string | undefined | null): {
  human: string
  machine: string
} {
  if (!thesis) return { human: '', machine: '' }
  const match = thesis.match(/^(.*?)\s*\[([^\]]+)\]\s*$/)
  if (match) {
    return { human: match[1].trim(), machine: match[2].trim() }
  }
  return { human: thesis.trim(), machine: thesis.trim() }
}

/** Extract machine metrics from thesis dumps / appendix. */
export function parseThesisMetrics(thesis: string | undefined | null): ThesisMetrics {
  const { machine, human } = splitThesis(thesis)
  const source = `${machine} ${human}`

  const score = parseNumber(source.match(/combined_score=(-?\d+(?:\.\d+)?)/)?.[1])
  const weightPct = parseNumber(source.match(/current_weight=(-?\d+(?:\.\d+)?)%/)?.[1])
  const capPct = parseNumber(source.match(/cap=(-?\d+(?:\.\d+)?)%/)?.[1])

  const retRaw = source.match(/Retorno 20d=(-?\d+(?:\.\d+)?|None|null)/i)?.[1]
  const volRaw = source.match(/vol 20d=(-?\d+(?:\.\d+)?|None|null)/i)?.[1]
  const return20d =
    retRaw && retRaw.toLowerCase() !== 'none' && retRaw.toLowerCase() !== 'null'
      ? parseNumber(retRaw)
      : undefined
  const vol20d =
    volRaw && volRaw.toLowerCase() !== 'none' && volRaw.toLowerCase() !== 'null'
      ? parseNumber(volRaw)
      : undefined

  const reasonKeys = REASON_KEYS.filter((key) => source.includes(key))

  return { score, weightPct, capPct, return20d, vol20d, reasonKeys }
}

export function looksLikeTechnicalDump(thesis: string | undefined | null): boolean {
  if (!thesis) return false
  const { human } = splitThesis(thesis)
  return (
    human.includes('Motivos:') ||
    human.includes('combined_score=') ||
    human.includes('current_weight=')
  )
}

export function humanThesis(rec: Recommendation, locale: Locale): string {
  const thesis = rec.explanation?.thesis?.trim()
  const { human } = splitThesis(thesis)

  if (human && !looksLikeTechnicalDump(thesis)) {
    // Prefer locale-native fallback for EN when backend thesis is Spanish template.
    if (locale === 'en' && /^(Mantener|Comprar|Aumentar|Vender|Reducir)\b/.test(human)) {
      const factory = ACTION_SUMMARY[rec.action] ?? ACTION_SUMMARY.HOLD
      return factory.en(rec.symbol)
    }
    return human
  }

  const factory = ACTION_SUMMARY[rec.action] ?? ACTION_SUMMARY.HOLD
  return factory[locale](rec.symbol)
}

export function actionLabel(action: string, locale: Locale): string {
  const labels: Record<string, Record<Locale, string>> = {
    HOLD: { es: 'Mantener', en: 'Hold' },
    BUY: { es: 'Comprar', en: 'Buy' },
    INCREASE: { es: 'Aumentar', en: 'Increase' },
    SELL: { es: 'Vender', en: 'Sell' },
    REDUCE: { es: 'Reducir', en: 'Reduce' },
  }
  return labels[action]?.[locale] ?? action
}

export function reasonLabel(key: string, locale: Locale): string | null {
  const map: Record<string, Record<Locale, string>> = {
    no_edge_hold: {
      es: 'Sin ventaja clara',
      en: 'No clear edge',
    },
    momentum_and_trend_support_entry: {
      es: 'Momentum y tendencia a favor',
      en: 'Momentum and trend support entry',
    },
    weak_momentum_suggests_trim: {
      es: 'Momentum débil sugiere recortar',
      en: 'Weak momentum suggests trim',
    },
    leveraged_blocked_by_regime_or_profile: {
      es: 'Apalancado bloqueado por régimen/perfil',
      en: 'Leveraged blocked by regime/profile',
    },
  }
  return map[key]?.[locale] ?? null
}

export function formatPctRatio(value: number | undefined, digits = 1): string | null {
  if (value === undefined || Number.isNaN(value)) return null
  const pct = Math.abs(value) <= 1.5 ? value * 100 : value
  return `${pct.toFixed(digits)}%`
}
