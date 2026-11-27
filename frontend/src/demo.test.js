import { describe, expect, it, vi } from 'vitest'
import { DEMO_SCENARIOS, getScenario } from './demoData.js'

const LEVELS = ['level1', 'level2', 'level3', 'level4', 'summary']
const daysUntil = (iso) => Math.round((new Date(iso) - new Date(new Date().toISOString().slice(0, 10))) / 864e5)

describe('demo scenarios', () => {
  it('offers pass / warn / fail', () => {
    expect(DEMO_SCENARIOS.map((s) => s.id)).toEqual(['pass', 'warn', 'fail'])
  })

  it.each(DEMO_SCENARIOS.map((s) => [s.id]))('%s has every level the dashboard renders', (id) => {
    const r = getScenario(id)
    for (const l of LEVELS) expect(r[l], l).toBeTruthy()
    expect(r.level1.checks.length).toBeGreaterThan(0)
    expect(typeof r.processing_time_ms).toBe('number')
    expect(r.level1.authenticity_score).toBeGreaterThanOrEqual(0)
    expect(r.level1.authenticity_score).toBeLessThanOrEqual(1)
  })

  it('verdicts are consistent with the scenario', () => {
    expect(getScenario('pass').summary.overall_verdict).toBe('PASS')
    expect(getScenario('warn').level4.overall_recommendation).toBe('HOLD')
    expect(getScenario('fail').level4.overall_recommendation).toBe('REJECT')
  })

  it('expiration dates are relative to today, so the demo never goes stale', () => {
    expect(daysUntil(getScenario('warn').level2.extracted_fields.expiration)).toBe(12)
    expect(getScenario('fail').level4.expiration_status.is_expired).toBe(true)
    expect(daysUntil(getScenario('fail').level2.extracted_fields.expiration)).toBeLessThan(0)
    expect(daysUntil(getScenario('pass').level2.extracted_fields.expiration)).toBeGreaterThan(365)
  })

  it('unknown ids fall back to the warn scenario', () => {
    expect(getScenario('nope').summary.overall_verdict).toBe('WARN')
  })

  it('uses only clearly synthetic data (no real-looking SSNs etc.)', () => {
    const text = JSON.stringify(DEMO_SCENARIOS.map((s) => s.build()))
    expect(text).not.toMatch(/\b\d{3}-\d{2}-\d{4}\b/)
  })
})

describe('api in demo mode', () => {
  it('loadDemo returns the bundled scenario without touching the network', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'true')
    vi.resetModules()
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    vi.useFakeTimers()
    const { loadDemo, verifyDocuments, DEMO_MODE } = await import('./api.js')
    expect(DEMO_MODE).toBe(true)
    const p = loadDemo('fail')
    await vi.runAllTimersAsync()
    const r = await p
    expect(r.demo).toBe(true)
    expect(r.summary.overall_verdict).toBe('FAIL')
    await expect(verifyDocuments(new Blob(['x']))).rejects.toThrow(/demo mode/)
    expect(fetchSpy).not.toHaveBeenCalled()
    vi.useRealTimers()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('falls back to bundled scenarios when the backend is unreachable', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'false')
    vi.resetModules()
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch') }))
    vi.useFakeTimers()
    const { loadDemo } = await import('./api.js')
    const p = loadDemo('pass')
    await vi.runAllTimersAsync()
    expect((await p).summary.overall_verdict).toBe('PASS')
    vi.useRealTimers()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('surfaces backend error details on /verify', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'false')
    vi.resetModules()
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'ID document: unsupported type' }), { status: 415 })))
    const { verifyDocuments } = await import('./api.js')
    await expect(verifyDocuments(new Blob(['x']))).rejects.toThrow('unsupported type')
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })
})
