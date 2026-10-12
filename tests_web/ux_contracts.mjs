import assert from 'node:assert/strict';
import {kyivToday,fmt,setLanguage} from '../web/assets/i18n.mjs';
import {estimateRemaining} from '../web/assets/remaining-core.mjs';
import {predictAtStart} from '../web/assets/forecast-core.mjs';
assert.equal(kyivToday(new Date('2026-10-11T21:30:00Z')),'2026-10-12');
assert.equal(kyivToday(new Date('2026-12-31T22:30:00Z')),'2027-01-01');
setLanguage('uk');assert.equal(fmt(40.894),'40,9');setLanguage('en');assert.equal(fmt(40.894),'40.9');
const origin='2026-10-01T00:00:00Z',boundary='2026-10-12T10:51:36Z',now='2026-10-12T19:00:00Z';
const rows=Array.from({length:40},(_,i)=>{const start=Date.parse('2026-08-01T00:00:00Z')+i*86400000;return {id:String(i+1),location_uid:'31',location_type:'oblast',location_title:'м. Київ',location_oblast:'м. Київ',location_raion:'',started_at:new Date(start).toISOString(),finished_at:new Date(start+(i+1)*60000).toISOString(),alert_type:'air_raid',alert_level:'unknown'};});
const call=(elapsed,extra=[])=>estimateRemaining({rows:[...rows,...extra],originUtc:origin,elapsedMinutes:elapsed,nowUtc:now,boundaryUtc:boundary});
// Independent hand-computable results: eligible lengths 31..40 -> residual 1..10.
assert.equal(call(30).prediction_minutes,5.5);assert.equal(call(30).eligible_n,10);assert.equal(call(35).prediction_minutes,3);assert.equal(call(36).status,'insufficient_tail_support');assert.equal(call(36).prediction_minutes,null);
assert.equal(call(0).prediction_minutes,20.5);
// Conditional residual is not initial rolling median minus elapsed (25.5 - 30).
assert.equal(predictAtStart(rows,origin).prediction_minutes,25.5);
const current={...rows[0],id:'999',started_at:origin,finished_at:'not-a-valid-clear'};
const future={...rows[0],id:'1000',started_at:'2026-10-02T00:00:00Z',finished_at:'also-invalid'};
assert.deepEqual(call(30,[current,future]),call(30));
assert.equal(call(16700).status,'stale_snapshot');
assert.throws(()=>call(-1),e=>e.code==='elapsed');assert.throws(()=>call(NaN),e=>e.code==='elapsed');assert.throws(()=>call(.5),e=>e.code==='elapsed');assert.throws(()=>call(1e20),e=>e.code==='future_assessment');
const unavailable={...rows[39],id:'1001',available_at_utc:'2026-10-02T00:00:00Z'};assert.deepEqual(call(30,[unavailable]),call(30));
console.log('Kyiv date, rounding, conditional residual, support, stale/future guards and causal invariance: PASS');
