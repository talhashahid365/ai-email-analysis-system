/**
 * MailNexa AI — k6 Load Test
 *
 * Run: k6 run tests/load/k6_load_test.js
 * Install k6: https://k6.io/docs/get-started/installation/
 *
 * Targets:
 *   - p95 latency < 500ms for standard API
 *   - p95 latency < 5000ms for AI endpoints
 *   - Error rate < 1%
 */
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TEST_EMAIL = __ENV.TEST_EMAIL || 'user@example.com';
const TEST_PASSWORD = __ENV.TEST_PASSWORD || 'password123';

const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency_ms');

export const options = {
  stages: [
    { duration: '1m',  target: 10  },  // Warm up
    { duration: '3m',  target: 50  },  // Normal load
    { duration: '2m',  target: 100 },  // Stress test
    { duration: '2m',  target: 50  },  // Scale down
    { duration: '1m',  target: 0   },  // Cool down
  ],
  thresholds: {
    'http_req_duration{type:api}': ['p(95)<500'],
    errors: ['rate<0.01'],
    http_req_failed: ['rate<0.05'],
  },
};

function getToken() {
  const res = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }),
    { headers: { 'Content-Type': 'application/json' }, tags: { type: 'api' } }
  );
  if (!check(res, { 'login 200': (r) => r.status === 200 })) return null;
  return JSON.parse(res.body).access_token;
}

export default function () {
  const token = getToken();
  if (!token) { errorRate.add(1); sleep(1); return; }

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  // Health check
  let res = http.get(`${BASE_URL}/api/health`, { tags: { type: 'api' } });
  apiLatency.add(res.timings.duration);
  errorRate.add(!check(res, { 'health 200': (r) => r.status === 200 }) ? 1 : 0);
  sleep(0.5);

  // List emails
  res = http.get(`${BASE_URL}/api/emails?limit=20`, { headers, tags: { type: 'api' } });
  apiLatency.add(res.timings.duration);
  errorRate.add(!check(res, { 'emails 200': (r) => r.status === 200 }) ? 1 : 0);
  sleep(0.5);

  // Analytics overview
  res = http.get(`${BASE_URL}/api/analytics/overview`, { headers, tags: { type: 'api' } });
  apiLatency.add(res.timings.duration);
  errorRate.add(!check(res, { 'analytics 200': (r) => r.status === 200 }) ? 1 : 0);
  sleep(0.5);

  // Auth me
  res = http.get(`${BASE_URL}/api/auth/me`, { headers, tags: { type: 'api' } });
  apiLatency.add(res.timings.duration);
  errorRate.add(!check(res, { 'me 200': (r) => r.status === 200 }) ? 1 : 0);
  sleep(1);
}

export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration.values['p(95)'].toFixed(0);
  const errRate = (data.metrics.http_req_failed.values.rate * 100).toFixed(2);
  return {
    stdout: `\n=== MailNexa AI Load Test Results ===\nRequests: ${data.metrics.http_reqs.values.count}\np95 latency: ${p95}ms (target: <500ms)\nError rate: ${errRate}% (target: <5%)\n`,
  };
}
