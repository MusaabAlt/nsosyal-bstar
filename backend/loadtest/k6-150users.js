// Load test: 150 concurrent users, double the expected demo audience of ~70.
//
//   make mock            (terminal 1: mock Python service)
//   make run-loadtest    (terminal 2: server with rate limits raised)
//   make loadtest        (terminal 3)
//
// Each virtual user behaves like a phone at the demo: it creates a session,
// then repeatedly writes a comment, reads the feed, and sometimes looks at
// the flagged list and the stats. 503 "busy" answers are EXPECTED under
// overload: they prove the queue protects the model. What must never happen
// is a timeout, a 500, or a server that stops answering.
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Counter, Rate, Trend } from 'k6/metrics'

const BASE = __ENV.BASE_URL || 'http://127.0.0.1:8080'

const busy = new Counter('busy_503')
const serverErrors = new Rate('server_errors') // 5xx other than 503, and network failures
const analyzeLatency = new Trend('analyze_latency', true)

export const options = {
  scenarios: {
    demo_crowd: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '20s', target: 70 }, // the real audience arrives
        { duration: '40s', target: 150 }, // double it
        { duration: '60s', target: 150 }, // hold
        { duration: '15s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    server_errors: ['rate<0.01'], // under 1% real failures
    http_req_failed: ['rate<0.30'], // includes expected 503 "busy"
    'analyze_latency{status:201}': ['p(95)<3000'], // successful analyses under 3s at p95
    'http_req_duration{endpoint:feed}': ['p(95)<500'],
  },
}

const TEXTS = [
  'Seni b1tireceğim',
  'amcam geldi',
  'Bu bir test cumlesi',
  'Bugün maç çok güzeldi',
  's4l4k mısın sen',
  'Senin gibilerin oyu yüzünden bu haldeyiz',
  'Harika bir sunumdu, tebrikler 👏',
  'Çantayı götürmek zorundayım',
]

const JSON_HEADERS = { headers: { 'Content-Type': 'application/json' } }

function unique(text) {
  // Half the traffic repeats a text (cache hits), half is new (reaches the model).
  return Math.random() < 0.5 ? text : `${text} ${__VU}-${__ITER}`
}

function record(res) {
  if (res.status === 503) busy.add(1)
  serverErrors.add(res.status === 0 || (res.status >= 500 && res.status !== 503))
}

export function setup() {
  const health = http.get(`${BASE}/api/health`)
  check(health, { 'server reachable': (r) => r.status === 200 })
}

export default function () {
  const session = http.post(`${BASE}/api/sessions`, JSON.stringify({ nickname: `vu-${__VU}` }), {
    ...JSON_HEADERS,
    tags: { endpoint: 'session' },
  })
  record(session)
  if (session.status !== 201) {
    sleep(1)
    return
  }
  const sessionId = session.json('id')

  for (let i = 0; i < 5; i++) {
    const text = unique(TEXTS[Math.floor(Math.random() * TEXTS.length)])
    const res = http.post(`${BASE}/api/comments`, JSON.stringify({ session_id: sessionId, text }), {
      ...JSON_HEADERS,
      tags: { endpoint: 'analyze' },
      timeout: '20s',
    })
    record(res)
    analyzeLatency.add(res.timings.duration, { status: String(res.status) })
    check(res, {
      'analyze answered (201 or 503 busy)': (r) => r.status === 201 || r.status === 503,
      'result present on success': (r) => r.status !== 201 || r.json('result.explanation') !== undefined,
    })

    const feed = http.get(`${BASE}/api/comments?limit=20`, { tags: { endpoint: 'feed' } })
    record(feed)
    check(feed, { 'feed ok': (r) => r.status === 200 })

    if (Math.random() < 0.2) {
      record(http.get(`${BASE}/api/moderation/flagged?limit=20`, { tags: { endpoint: 'flagged' } }))
      record(http.get(`${BASE}/api/stats`, { tags: { endpoint: 'stats' } }))
    }
    // A person reads before writing again.
    sleep(1 + Math.random() * 2)
  }
}

export function teardown() {
  const stats = http.get(`${BASE}/api/stats`)
  if (stats.status === 200) {
    const s = stats.json()
    console.log(`queue rejected=${s.queue.rejected} batches=${s.queue.batches} cache hits=${s.cache.hits}`)
    console.log(`writer written=${s.writer.analyses_written} dropped=${s.writer.analyses_dropped}`)
  }
}
