import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import flagged from './mocks/flagged.json'
import { httpSource } from './httpSource'
import { errorLine } from '@/report/useAnalysis'

type Handler = (url: string, body: Record<string, unknown>) => { status: number; body?: unknown } | 'network'

function mockFetch(handler: Handler) {
  const calls: Array<{ url: string; body: Record<string, unknown> }> = []
  vi.stubGlobal('fetch', async (url: string, init: RequestInit) => {
    const body = JSON.parse(String(init.body)) as Record<string, unknown>
    calls.push({ url, body })
    const reply = handler(url, body)
    if (reply === 'network') throw new TypeError('Failed to fetch')
    return new Response(reply.body === undefined ? '' : JSON.stringify(reply.body), { status: reply.status })
  })
  return calls
}

describe('http source (Go API)', () => {
  beforeEach(() => sessionStorage.clear())
  afterEach(() => vi.unstubAllGlobals())

  it('creates a session once, then posts comments with it', async () => {
    const calls = mockFetch((url) =>
      url === '/api/sessions'
        ? { status: 201, body: { id: 's-1', nickname: 'Operatör' } }
        : { status: 201, body: { comment: { id: 'c' }, result: flagged, timing: {} } },
    )
    const first = await httpSource.analyze('Seni b1tireceğim')
    const second = await httpSource.analyze('ikinci')
    expect(first.ok && first.result.verdict).toBe('escalate')
    expect(second.ok).toBe(true)
    expect(calls.map((c) => c.url)).toEqual(['/api/sessions', '/api/comments', '/api/comments'])
    expect(calls[1]!.body).toEqual({ session_id: 's-1', text: 'Seni b1tireceğim' })
    expect(httpSource.representative).toBe(false)
  })

  it('recreates a session the server no longer knows and retries once', async () => {
    sessionStorage.setItem('nsosyal.session', 'old')
    let commentCalls = 0
    // After a retry the stored id is replaced, so storage wins over any older in-memory id.
    const calls = mockFetch((url, body) => {
      if (url === '/api/sessions') return { status: 201, body: { id: 'new' } }
      commentCalls++
      if (body.session_id === 'old') return { status: 400, body: { error: { code: 'unknown_session', message: 'x' } } }
      return { status: 201, body: { result: flagged } }
    })
    const outcome = await httpSource.analyze('x')
    expect(outcome.ok).toBe(true)
    expect(commentCalls).toBe(2)
    expect(calls.at(-1)!.body.session_id).toBe('new')
  })

  it('passes the backend error code through, so the screen can explain it', async () => {
    sessionStorage.setItem('nsosyal.session', 's')
    mockFetch(() => ({ status: 503, body: { error: { code: 'model_loading', message: 'loading' } } }))
    const outcome = await httpSource.analyze('x')
    expect(outcome.ok).toBe(false)
    if (!outcome.ok) {
      expect(outcome.error).toMatchObject({ kind: 'http', status: 503, code: 'model_loading' })
      expect(errorLine(outcome.error)).toBe('Model yükleniyor; birkaç saniye sonra tekrar deneyin.')
    }
  })

  it('an unreachable server is the network error state', async () => {
    sessionStorage.setItem('nsosyal.session', 's')
    mockFetch(() => 'network')
    const outcome = await httpSource.analyze('x')
    expect(outcome).toEqual({ ok: false, error: { kind: 'network' } })
  })

  it('a non-JSON error page still gives a readable state', async () => {
    sessionStorage.setItem('nsosyal.session', 's')
    vi.stubGlobal('fetch', async () => new Response('<html>Bad Gateway</html>', { status: 502 }))
    const outcome = await httpSource.analyze('x')
    expect(!outcome.ok && errorLine(outcome.error)).toBe('Analiz servisi yanıt vermedi.')
  })
})

describe('error lines by backend code', () => {
  it.each([
    ['queue_full', 503, 'Analiz servisi şu anda meşgul.'],
    ['model_unavailable', 503, 'Model yeniden başlatılıyor; birkaç saniye sonra tekrar deneyin.'],
    ['rate_limited', 429, 'Çok sık istek gönderildi; bir saniye sonra tekrar deneyin.'],
    ['timeout', 504, 'Analiz zamanında tamamlanamadı.'],
    ['model_error', 502, 'Model bu metni analiz edemedi.'],
  ])('%s', (code, status, line) => {
    expect(errorLine({ kind: 'http', status, code })).toBe(line)
  })
})
