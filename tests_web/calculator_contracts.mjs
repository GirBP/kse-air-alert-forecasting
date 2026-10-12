import assert from 'node:assert/strict';
import fs from 'node:fs';
import {predictAtStart,kyivLocalToUTC,evaluateRequest,parseCSV,parseTimestamp} from '../web/assets/forecast-core.mjs';
const payload=JSON.parse(fs.readFileSync(0,'utf8'));
const results=[];
for(const fixture of payload.fixtures){
  try{results.push({name:fixture.name,result:predictAtStart(fixture.rows,fixture.origin,fixture.city||'31')});}
  catch(error){results.push({name:fixture.name,error:error.code});}
}
assert.equal(new Date(kyivLocalToUTC('2026-10-01','02:50')).toISOString(),'2026-09-30T23:50:00.000Z');
assert.equal(new Date(kyivLocalToUTC('2026-12-01','02:50')).toISOString(),'2026-12-01T00:50:00.000Z');
for(const [date,time,code] of [['2026-03-29','03:30','nonexistent_local_time'],['2026-10-25','03:30','ambiguous_local_time'],['2026-02-30','12:00','invalid_start'],['','12:00','missing_start'],['2026-10-01','','missing_start']]){
  assert.throws(()=>kyivLocalToUTC(date,time),e=>e.code===code);
}
const rows=payload.fixtures[0].rows;
let request={rows,city:'31',date:'2026-09-04',time:'03:00',nowUtc:'2026-10-12T18:00:00Z',boundaryUtc:'2026-10-12T10:51:36Z'};
const historical=evaluateRequest(request);assert.equal(historical.mode,'historical_event_clock');assert.equal(historical.estimate_exceeded,true);assert.equal(historical.forecast.prediction_minutes,24.5);assert.ok(!('remaining_minutes' in historical));
assert.throws(()=>evaluateRequest({...request,date:'2026-10-13'}),e=>e.code==='future_start');
assert.throws(()=>evaluateRequest({...request,city:'lviv'}),e=>e.code==='unsupported_city');
const stale=evaluateRequest({...request,date:'2026-10-12',time:'16:00'});assert.equal(stale.mode,'stale_snapshot');assert.equal(stale.forecast,null);assert.equal(stale.historical_reference.prediction_minutes,24.5);assert.equal(stale.estimate_exceeded,null);
const equalEdge=evaluateRequest({...request,date:'2026-10-12',time:'13:52'});assert.equal(equalEdge.mode,'stale_snapshot');
const csv='id,location_uid,location_type,location_title,location_oblast,location_raion,started_at,finished_at,alert_type,alert_level\n1,31,oblast,"м. Київ","м. Київ",,2026-09-01T00:00:00Z,2026-09-01T00:10:00Z,air_raid,yellow\n';assert.equal(parseCSV(csv)[0].location_title,'м. Київ');
assert.throws(()=>parseCSV('id\n1\n'),e=>e.code==='schema');assert.throws(()=>parseTimestamp('2026-09-01T00:00:00.000001Z'),e=>e.code==='unsupported_precision');
console.log(JSON.stringify({results,timezone:process.env.TZ||'system',kyiv_origin:'2026-09-30T23:50:00.000Z',DST_gap_rejected:true,DST_fold_rejected:true,stale_no_forecast:true,future_start_rejected:true,exceeded_no_remaining:true}));
