// Faithful event-clock implementation of kse_latest.forecast; no model fitting.
export class ForecastError extends Error {
  constructor(code,message) { super(message); this.code=code; }
}
const fail=(code,message)=>{throw new ForecastError(code,message);};
const count=(counts,key,n=1)=>{counts[key]=(counts[key]||0)+n;};
const utc=(y,m,d,h=0,min=0,s=0,ms=0)=>{
  const v=new Date(0);v.setUTCFullYear(y,m-1,d);v.setUTCHours(h,min,s,ms);return v.getTime();
};
export function parseTimestamp(value,utcOnly=false) {
  if (typeof value!=='string' || !value) fail('invalid_timestamp','Потрібен час ISO з явною часовою зоною.');
  const m=value.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?(Z|[+-]\d{2}:\d{2})$/);
  if (!m) fail('invalid_timestamp','Некоректна часова мітка джерела.');
  const [y,mo,d,h,mi,s]=m.slice(1,7).map(v=>Number(v||0));
  const fraction=m[7]||'';
  if (fraction.slice(3).replace(/0/g,'')) fail('unsupported_precision','Мітка має точність, яку браузер не може зберегти; розрахунок відхилено.');
  const ms=Number((fraction+'000').slice(0,3));
  const base=utc(y,mo,d,h,mi,s,ms);const test=new Date(base);
  if (mo<1||mo>12||d<1||h>23||mi>59||s>59||test.getUTCFullYear()!==y||test.getUTCMonth()+1!==mo||test.getUTCDate()!==d) fail('invalid_timestamp','Некоректна дата чи час джерела.');
  let offset=0;
  if (m[8]!=='Z') {
    const hh=Number(m[8].slice(1,3)),mm=Number(m[8].slice(4,6));
    if(hh>23||mm>59)fail('invalid_timestamp','Некоректний UTC-зсув.');
    offset=(hh*60+mm)*60000*(m[8][0]==='+'?1:-1);
  }
  if (utcOnly&&offset!==0)fail('source_timezone','Час подій джерела повинен мати явний UTC.');
  return base-offset;
}
export function parseCSV(text) {
  if(typeof text!=='string')fail('schema','CSV недоступний.');
  text=text.replace(/^\uFEFF/,'');
  const records=[];let row=[],field='',quoted=false,closed=false;
  for(let i=0;i<text.length;i++) {
    const c=text[i];
    if(quoted) {
      if(c==='"') {if(text[i+1]==='"'){field+='"';i++;}else{quoted=false;closed=true;}}
      else field+=c;
      continue;
    }
    if(c==='"') {if(field||closed)fail('schema','Пошкоджені лапки CSV.');quoted=true;continue;}
    if(c===','||c==='\n'||c==='\r') {
      row.push(field);field='';closed=false;
      if(c!==',') {if(c==='\r'&&text[i+1]==='\n')i++;if(row.some(v=>v!==''))records.push(row);row=[];}
      continue;
    }
    if(closed)fail('schema','Символ після закритих лапок CSV.');
    field+=c;
  }
  if(quoted)fail('schema','Незакриті лапки CSV.');
  if(field||row.length){row.push(field);if(row.some(v=>v!==''))records.push(row);}
  const headers=records.shift();
  const required=['id','location_uid','location_type','location_title','location_oblast','location_raion','started_at','finished_at','alert_type','alert_level'];
  if(!headers||new Set(headers).size!==headers.length||required.some(k=>!headers.includes(k)))fail('schema','Формат CSV не відповідає перевіреному джерелу.');
  return records.map(values=>{if(values.length!==headers.length)fail('schema','Некоректна кількість полів CSV.');return Object.fromEntries(headers.map((k,i)=>[k,values[i]]));});
}
const numericId=id=>typeof id==='string'&&/^[0-9]+$/.test(id);
const signature=v=>JSON.stringify([v.start,v.end,v.alert_type]);
export function completedHistory(rows,origin,city='31') {
  if(String(city)!=='31')fail('unsupported_city','Для цього міста метод ще не перевірено.');
  const originMs=typeof origin==='number'?origin:parseTimestamp(origin);
  if(!Number.isFinite(originMs)||!Array.isArray(rows))fail('input','Некоректна історія чи початок.');
  const counts={},groups=new Map(),future=[];
  for(const row of rows) {
    if(!row||typeof row!=='object'||!('location_uid' in row))fail('schema','Рядок історії потребує location_uid.');
    if(String(row.location_uid)!=='31'){count(counts,'other_location');continue;}
    const available=row.available_at_utc?parseTimestamp(row.available_at_utc):null;
    if(available!==null&&available>originMs){count(counts,'not_yet_available');continue;}
    const start=parseTimestamp(row.started_at,true);
    if(start>=originMs) {
      count(counts,'current_or_future_start');
      if(numericId(row.id))future.push({id:row.id,start,end:null,available,alert_type:row.alert_type});
      continue; // Current/future CLEAR is never inspected.
    }
    if(!numericId(row.id))fail('invalid_id','ID завершеної події повинен бути числовим ASCII-рядком.');
    if(row.location_title!=='м. Київ'||row.location_oblast!=='м. Київ'||row.location_type!=='oblast'||row.location_raion)fail('city_identity','UID31 повинен зберігати власну ідентичність міста Київ.');
    const end=row.finished_at?parseTimestamp(row.finished_at,true):null;
    const item={id:row.id,start,end,available,alert_type:row.alert_type};
    if(!groups.has(row.id))groups.set(row.id,[]);groups.get(row.id).push(item);
  }
  for(const version of future)if(groups.has(version.id))groups.get(version.id).push(version);
  const history=[];
  for(const [id,versions] of groups) {
    let chosen;
    if(new Set(versions.map(signature)).size===1){chosen=versions[0];count(counts,'identical_repeats',versions.length-1);}
    else {
      if(versions.some(v=>v.available===null))fail('version_conflict',`Конфліктні версії без часу доступності: ${id}.`);
      const newest=Math.max(...versions.map(v=>v.available));const latest=versions.filter(v=>v.available===newest);
      if(new Set(latest.map(signature)).size!==1)fail('version_conflict',`Конфліктні версії в один момент доступності: ${id}.`);
      chosen=latest[0];count(counts,'superseded_available_versions',versions.length-1);
    }
    if(chosen.start>=originMs)continue;
    if(chosen.alert_type!=='air_raid'){count(counts,'other_alert_type');continue;}
    if(chosen.end===null){count(counts,'open_event');continue;}
    if(chosen.end>originMs){count(counts,'not_yet_cleared');continue;}
    if(chosen.end<=chosen.start)fail('nonpositive','Недодатна тривалість завершеної події.');
    history.push({...chosen,duration:(chosen.end-chosen.start)/60000});
  }
  const idOrder=(a,b)=>BigInt(a.id)<BigInt(b.id)?-1:BigInt(a.id)>BigInt(b.id)?1:0;
  const ordered=[...history].sort((a,b)=>a.start-b.start||idOrder(a,b));
  for(let i=1;i<ordered.length;i++)if(ordered[i-1].end>ordered[i].start)fail('overlap','Завершені інтервали Києва перекриваються; розрахунок відхилено.');
  history.sort((a,b)=>a.end-b.end||idOrder(a,b));
  return {history,counts};
}
export function predictAtStart(rows,origin,city='31') {
  const {history,counts}=completedHistory(rows,origin,city);
  const used=history.length>=30?history.slice(-30):[];
  const durations=used.map(v=>v.duration).sort((a,b)=>a-b);
  return {method:'median_last_30_completed',target:'total_registered_duration_at_new_start',status:used.length?'predicted':'insufficient_completed_history',prediction_minutes:used.length?(durations[14]+durations[15])/2:null,completed_history_n:history.length,used_history_n:used.length,used_history_ids:used.map(v=>v.id),used_history_clears_utc:used.map(v=>new Date(v.end).toISOString()),used_history_durations_minutes:used.map(v=>v.duration),latest_available_clear_utc:used.length?new Date(used.at(-1).end).toISOString():null,ignored_record_counts:counts};
}
const kyivFormatter=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Kyiv',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
function parts(ms) {return Object.fromEntries(kyivFormatter.formatToParts(new Date(ms)).filter(p=>p.type!=='literal').map(p=>[p.type,Number(p.value)]));}
export function kyivLocalToUTC(date,time) {
  if(!date||!time)fail('missing_start','Вкажіть і дату, і час початку.');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!/^\d{2}:\d{2}$/.test(time))fail('invalid_start','Вкажіть коректну дату та час HH:MM.');
  const [year,month,day]=date.split('-').map(Number),[hour,minute]=time.split(':').map(Number);
  const guess=utc(year,month,day,hour,minute);const d=new Date(guess);
  if(year<1900||month<1||month>12||day<1||hour>23||minute>59||d.getUTCFullYear()!==year||d.getUTCMonth()+1!==month||d.getUTCDate()!==day)fail('invalid_start','Некоректна календарна дата чи час.');
  const offsets=new Set();
  for(const hours of [-36,-12,0,12,36]) {const probe=guess+hours*3600000,p=parts(probe);offsets.add(utc(p.year,p.month,p.day,p.hour,p.minute,p.second)-probe);}
  const matches=[];
  for(const offset of offsets){const candidate=guess-offset,p=parts(candidate);if(p.year===year&&p.month===month&&p.day===day&&p.hour===hour&&p.minute===minute&&p.second===0)matches.push(candidate);}
  if(matches.length===0)fail('nonexistent_local_time','Цього місцевого часу не існує через перехід літнього часу. Оберіть інший час.');
  if(matches.length!==1)fail('ambiguous_local_time','Ця місцева година повторюється при переході літнього часу. Без уточнення початок неоднозначний; розрахунок відхилено.');
  return matches[0];
}
export function evaluateRequest({rows,city,date,time,nowUtc,boundaryUtc}) {
  if(String(city)!=='31')fail('unsupported_city','Для цього міста метод ще не перевірено.');
  const origin=kyivLocalToUTC(date,time),now=parseTimestamp(nowUtc),boundary=parseTimestamp(boundaryUtc);
  if(origin>now)fail('future_start','Початок у майбутньому. Вкажіть час, який уже настав.');
  if(origin>=boundary) {
    const reference=predictAtStart(rows,boundary,city);
    return {mode:'stale_snapshot',origin_utc:new Date(origin).toISOString(),forecast:null,historical_reference:reference,reference_origin_utc:new Date(boundary).toISOString(),estimate_exceeded:null};
  }
  const forecast=predictAtStart(rows,origin,city);
  return {mode:'historical_event_clock',origin_utc:new Date(origin).toISOString(),forecast,historical_reference:null,estimate_exceeded:forecast.prediction_minutes!==null&&(now-origin)/60000>forecast.prediction_minutes};
}
