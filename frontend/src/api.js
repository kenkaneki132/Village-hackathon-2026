import { getScenario } from './demoData.js'

// VITE_API_URL: base URL of the FastAPI backend ('' = same origin / Vite dev proxy).
// VITE_DEMO_MODE=true forces the backend-free demo (used for the GitHub Pages build).
export const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function asJson(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function verifyDocuments(idFile, supportFile) {
  if (DEMO_MODE) {
    throw new Error('Live analysis needs the FastAPI backend with an Anthropic API key. This hosted build runs in demo mode, so try one of the sample scenarios below.')
  }
  const form = new FormData()
  form.append('id_doc', idFile)
  if (supportFile) form.append('support_doc', supportFile)
  return asJson(await fetch(`${API_BASE}/verify`, { method: 'POST', body: form }))
}

export async function loadDemo(scenarioId = 'warn') {
  if (DEMO_MODE) {
    await sleep(1800 + Math.random() * 900) // let the pipeline animation play
    return { ...getScenario(scenarioId), demo: true }
  }
  try {
    const res = await fetch(`${API_BASE}/synthetic-test`, { method: 'POST' })
    if (scenarioId === 'warn') return await asJson(res)
  } catch { /* backend offline → fall back to bundled scenarios */ }
  await sleep(1200)
  return { ...getScenario(scenarioId), demo: true }
}
