import {choose,fmt,local,t,ready} from './i18n.mjs';
const $=id=>document.getElementById(id);
let data,current,visible=false;
function renderExample(){
 if(!current)return;
 document.querySelectorAll('[data-example]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.example===current.id)));
 $('case-title').textContent=t(current.id);
 $('case-note').textContent=t('note_'+current.id);
 $('origin').textContent=local(current.origin_local);
 $('case-number').textContent=String(data.examples.indexOf(current)+1).padStart(2,'0');
 $('prediction').textContent=fmt(current.prediction_minutes);$('history-n').textContent=current.history_n;$('used-n').textContent=current.used_n;
 $('outcome').hidden=!visible;$('comparison').hidden=!visible;$('reveal').setAttribute('aria-expanded',String(visible));
 $('reveal').textContent=visible?choose('Сховати результат ↑','Hide outcome ↑'):t('show');
 $('actual').textContent=fmt(current.actual_minutes);$('error').textContent=fmt(current.absolute_error_minutes);
 const delta=current.actual_minutes-current.prediction_minutes;
 $('error-note').textContent=delta>0?choose(`Оцінка коротша за результат прикладу на ${fmt(delta)} хв.`,`The estimate is ${fmt(delta)} minutes shorter than the example outcome.`):choose(`Оцінка довша за результат прикладу на ${fmt(-delta)} хв.`,`The estimate is ${fmt(-delta)} minutes longer than the example outcome.`);
 $('example-lesson').textContent=t('lesson_'+current.id);
 const scale=Math.max(current.prediction_minutes,current.actual_minutes);
 $('prediction-bar').style.width=`${current.prediction_minutes/scale*100}%`;$('actual-bar').style.width=`${current.actual_minutes/scale*100}%`;
 $('prediction-bar-value').textContent=`${fmt(current.prediction_minutes)} ${t('min')}`;$('actual-bar-value').textContent=`${fmt(current.actual_minutes)} ${t('min')}`;
 $('selection-rule').textContent=choose('Для кожного прикладу Python обчислив медіану 30 вигаданих тривалостей: 8–37, 81–110 або 5–34 хв. Окремо задані результати — 24, 180 і 240 хв. Їх не використовували в розрахунку.','Python calculated the median of 30 invented durations per example: 8–37, 81–110 or 5–34 minutes. Separately assigned outcomes are 24, 180 and 240 minutes; they were not used in the prediction.');
}
function renderResults(){
 if(!data)return;
 $('primary-mae').textContent=fmt(data.primary84.MAE);$('within30').textContent=fmt(100*data.primary84.within30_n/data.primary84.n)+'%';
 const rows=[{...data.primary84,label:choose('1–11.10.2026 · основна вибірка, неповний останній день','1–11 Oct 2026 · primary cohort, partial final day')},{...data.latest91,label:choose('1–12.10.2026 · додаткова перевірка, неповний останній день','1–12 Oct 2026 · additional check, partial final day')}];
 $('metric-rows').replaceChildren();for(const r of rows){const tr=document.createElement('tr');[r.label,r.n,...['MAE','RMSE','median_AE','p90_AE'].map(k=>r[k]==null?'—':fmt(r[k]))].forEach((v,i)=>{const c=document.createElement(i?'td':'th');c.textContent=v;if(!i)c.scope='row';tr.append(c);});$('metric-rows').append(tr);}
 $('latest-note').textContent=choose('Основна вибірка: версія 7abc556, межа 11.10.2026 13:07:59 за Києвом. Додаткова вибірка: 91 запис із пізнішої версії. Вона перетинається з основною і не є новим незалежним тестом.','Primary cohort: version 7abc556, boundary 11 Oct 2026, 13:07:59 Kyiv time. The additional cohort uses 91 records from a later version. It overlaps with the primary cohort and is not a new independent test.');
}
await ready;
try{const response=await fetch('assets/demo-data.json');if(!response.ok)throw Error(response.status);data=await response.json();if(data.examples.length!==3||data.examples.some(x=>!x.synthetic||!Number.isFinite(x.prediction_minutes)))throw Error('Invalid examples');current=data.examples[0];
 document.querySelectorAll('[data-example]').forEach(b=>b.addEventListener('click',()=>{current=data.examples.find(x=>x.id===b.dataset.example);visible=false;renderExample();}));
 $('reveal').addEventListener('click',()=>{visible=!visible;renderExample();});renderExample();renderResults();$('load-state').hidden=true;$('demo-content').hidden=false;
}catch(e){$('load-state').textContent=choose('Не вдалося завантажити дані. Оновіть сторінку або відкрийте GitHub.','Data could not be loaded. Refresh the page or open GitHub.');}
document.addEventListener('languagechange',()=>{renderExample();renderResults();});
