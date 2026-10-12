import {parseCSV,parseTimestamp,kyivLocalToUTC,predictAtStart,evaluateRequest,ForecastError} from './forecast-core.mjs';
const $=id=>document.getElementById(id);
const config={url:'https://raw.githubusercontent.com/JustJimer/ukraine-air-alert-stats/c5b3bd012c7694e63115999a7bbd0b683eaa8d24/archive/alerts_in_ua.csv',sha:'fe79c5726a1a9db9f560d6dad1de1b46f16d93b9b44ff54a2078228cf56cbc0d',version:'c5b3bd012c7694e63115999a7bbd0b683eaa8d24',boundary:'2026-10-12T10:51:36Z'};
const local=iso=>new Intl.DateTimeFormat('uk-UA',{timeZone:'Europe/Kyiv',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(iso));
let source=null;
function clearResult(){ $('calc-result').hidden=true; $('calc-result').replaceChildren(); }
function paragraph(text,cls=''){const p=document.createElement('p');p.textContent=text;if(cls)p.className=cls;$('calc-result').appendChild(p);return p;}
function sourceText(){
  $('calc-source').hidden=false;
  $('calc-receipt').textContent=local(source.received_at)+' Europe/Kyiv';
  $('calc-version').textContent=config.version;
  $('calc-sha').textContent=config.sha;
  $('calc-boundary').textContent=local(config.boundary)+' Europe/Kyiv (час коміту; не підтвердження повноти)';
  $('calc-last-clear').textContent=local(source.last_clear)+' Europe/Kyiv';
  $('calc-source-n').textContent=source.city_n;
}
async function loadSource(){
  if(source)return source;
  $('calc-state').textContent='Отримуємо справжню історію з upstream і перевіряємо SHA-256…';
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),20000);
  let response;
  try{response=await fetch(config.url,{mode:'cors',credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',signal:controller.signal});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const bytes=await response.arrayBuffer();
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(v=>v.toString(16).padStart(2,'0')).join('');
    if(digest!==config.sha)throw new ForecastError('checksum','SHA-256 не відповідає зафіксованому знімку. Дані відхилено.');
    const rows=parseCSV(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
    const city=rows.filter(row=>row.location_uid==='31'&&row.alert_type==='air_raid');
    if(city.length!==247)throw new ForecastError('source_support','Кількість рядків не відповідає перевіреному знімку.');
    const closed=city.filter(row=>row.finished_at).map(row=>parseTimestamp(row.finished_at,true));
    // Validate complete-city history independently of the user's entered origin.
    predictAtStart(rows,config.boundary);
    source={rows,city_n:city.length,last_clear:new Date(Math.max(...closed)).toISOString(),received_at:new Date().toISOString()};
    sourceText();return source;
  }finally{clearTimeout(timer);}
}
$('calculator-form').addEventListener('submit',async event=>{
  event.preventDefault();clearResult();
  const city=$('calc-city').value,date=$('calc-date').value,time=$('calc-time').value;
  const now=new Date().toISOString();
  $('calc-submit').disabled=true;for(const id of ['calc-city','calc-date','calc-time'])$(id).disabled=true;$('calculator-form').setAttribute('aria-busy','true');
  try{
    if(city!=='31')throw new ForecastError('unsupported_city','Для цього міста метод ще не перевірено.');
    const origin=kyivLocalToUTC(date,time);
    if(origin>parseTimestamp(now))throw new ForecastError('future_start','Початок у майбутньому. Вкажіть час, який уже настав.');
    const loaded=await loadSource();
    const result=evaluateRequest({rows:loaded.rows,city,date,time,nowUtc:now,boundaryUtc:config.boundary});
    $('calc-result').hidden=false;
    if(result.mode==='stale_snapshot'){
      paragraph('Для введеного початку актуальний прогноз недоступний: історія закінчується раніше.','calc-unavailable');
      const reference=result.historical_reference;
      if(reference.status==='predicted'){
        paragraph(`Історичний орієнтир за даними до ${local(config.boundary)} Europe/Kyiv: приблизно ${Math.round(reference.prediction_minutes)} хв.`,'calc-reference');
        paragraph('Це медіана на межі знімка, а не прогноз введеної події. Пізніші завершені події могли змінити оцінку.');
        paragraph(`Завершень в історії на цій межі: ${reference.completed_history_n}; використано ${reference.used_history_n}.`);
      }
      $('calc-state').textContent='Застарілий знімок для введеного моменту; звичайний прогноз відсутній.';
    }else if(result.forecast.status!=='predicted'){
      paragraph(`Прогноз відсутній: до введеного початку доступно лише ${result.forecast.completed_history_n} придатних завершень; потрібно 30.`,'calc-unavailable');
      $('calc-state').textContent='Недостатньо завершеної історії. Нуль замість прогнозу не підставляємо.';
    }else{
      const f=result.forecast;
      paragraph(`Оцінка загальної тривалості від початку: приблизно ${Math.round(f.prediction_minutes)} хв.`,'calc-main-value');
      paragraph(`Історичний розрахунок для ${local(result.origin_utc)} Europe/Kyiv. Завершень в історії: ${f.completed_history_n}; використано останні ${f.used_history_n}.`);
      paragraph(`Останнє використане завершення: ${local(f.latest_available_clear_utc)} Europe/Kyiv.`);
      paragraph('Перевірено порядок часу подій. Час доступності саме цих версій записів у минулому невідомий; оперативну доступність не доведено.');
      if(result.estimate_exceeded)paragraph('Від введеного початку на момент перегляду минуло більше, ніж ця початкова оцінка. Це не доводить, що подія завершилася. Залишкова тривалість тут не прогнозується.','calc-warning');
      $('calc-state').textContent='Історичний розрахунок готовий. Існування або активність введеної події не перевіряли.';
    }
    paragraph('Завершення зареєстрованого інтервалу не є сигналом офіційного відбою.','calc-safety');
  }catch(error){
    const message=error instanceof ForecastError?error.message:'Історія недоступна: завантаження, CORS або з’єднання не працює. Число не обчислено; синтетична історія не підставляється.';
    $('calc-state').textContent=message;
    if(source)sourceText();
  }finally{$('calc-submit').disabled=false;for(const id of ['calc-city','calc-date','calc-time'])$(id).disabled=false;$('calculator-form').setAttribute('aria-busy','false');}
});
