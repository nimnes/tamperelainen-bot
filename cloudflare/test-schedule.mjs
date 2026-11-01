import assert from 'node:assert/strict';
import worker from './worker.mjs';

// Exercise every cron invocation through winter, summer and both DST changes.
const local = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/Helsinki', dateStyle: 'short', timeStyle: 'short',
});
const days = new Map();
let dispatched = 0;
globalThis.fetch = async () => { dispatched++; return { ok: true }; };
const originalLog = console.log;
console.log = () => {};
for (let time = Date.parse('2026-01-01T00:00:00Z'); time < Date.parse('2027-01-01T00:00:00Z'); time += 30 * 60 * 1000) {
  const date = new Date(time);
  const helsinki = new Date(date.toLocaleString('en-US', { timeZone: 'Europe/Helsinki' }));
  const weekend = [0, 6].includes(helsinki.getDay());
  const hour = helsinki.getHours();
  const expected = weekend
    ? helsinki.getMinutes() === 0 && hour >= 9 && hour <= 22
    : helsinki.getMinutes() === 30 && hour >= 7 && hour <= 21;
  const before = dispatched;
  await worker.scheduled({ scheduledTime: time }, { GITHUB_TOKEN: 'test' }, {});
  assert.equal(dispatched - before, Number(expected), local.format(date));
  if (expected) {
    const key = local.format(date).split(',')[0];
    days.set(key, (days.get(key) || 0) + 1);
  }
}
assert.equal(days.size, 365);
assert.equal(dispatched, 261 * 15 + 104 * 14);
console.log = originalLog;
console.log(`Passed: ${dispatched} dispatches over 365 days, including both DST changes.`);
