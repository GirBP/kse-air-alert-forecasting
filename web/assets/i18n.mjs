export let language='uk';
let dictionary={};
try {language=localStorage.getItem('kse-language')==='en'?'en':'uk';}catch{}
export const choose=(uk,en)=>language==='uk'?uk:en;
export const fmt=n=>new Intl.NumberFormat(language==='uk'?'uk-UA':'en-GB',{minimumFractionDigits:1,maximumFractionDigits:1}).format(n);
export const local=iso=>new Intl.DateTimeFormat(language==='uk'?'uk-UA':'en-GB',{timeZone:'Europe/Kyiv',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(new Date(iso));
export function kyivToday(now=new Date()) {const p=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Kyiv',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now).map(x=>[x.type,x.value]));return `${p.year}-${p.month}-${p.day}`;}
export const t=key=>dictionary[key]?.[language==='uk'?0:1]??key;
export function setLanguage(lang){
 language=lang==='en'?'en':'uk';try{localStorage.setItem('kse-language',language);}catch{}
 if(typeof document==='undefined')return;
 document.documentElement.lang=language;
 document.title=choose('Скільки може тривати тривога? · Київ','How long might an air alert last? · Kyiv');
 document.querySelector('meta[name="description"]').content=choose('Оцінка тривалості тривоги для Києва, результати експериментів і пояснення дослідження.','Kyiv alert duration estimates, experiment results and the research process.');
 document.querySelectorAll('[data-i18n]').forEach(el=>el.textContent=t(el.dataset.i18n));
 document.querySelectorAll('[data-language]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.language===language)));
 document.dispatchEvent(new Event('languagechange'));
}
export const ready=typeof document==='undefined'?Promise.resolve():fetch('assets/translations.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(d=>{dictionary=d;document.querySelectorAll('[data-language]').forEach(b=>b.addEventListener('click',()=>setLanguage(b.dataset.language)));setLanguage(language);}).catch(()=>{document.querySelectorAll('[data-language]').forEach(b=>b.disabled=true);});
