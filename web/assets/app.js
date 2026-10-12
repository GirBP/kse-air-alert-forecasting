'use strict';
const $ = id => document.getElementById(id);
const fmt = (n, digits = 1) => new Intl.NumberFormat('uk-UA', {minimumFractionDigits: digits, maximumFractionDigits: digits}).format(n);
let data, current;
function selectExample(id) {
  current = data.examples.find(item => item.id === id);
  if (!current) throw new Error('Невідомий приклад');
  document.querySelectorAll('[data-example]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.example === id)));
  $('case-title').textContent = current.title;
  $('case-note').textContent = current.note;
  const date = new Date(current.origin_local);
  $('origin').textContent = new Intl.DateTimeFormat('uk-UA', {timeZone: 'Europe/Kyiv', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'}).format(date);
  $('case-number').textContent = String(data.examples.indexOf(current) + 1).padStart(2, '0');
  $('prediction').textContent = fmt(current.prediction_minutes);
  $('history-n').textContent = current.history_n;
  $('used-n').textContent = current.used_n;
  $('outcome').hidden = true;
  $('comparison').hidden = true;
  $('reveal').setAttribute('aria-expanded', 'false');
  $('reveal').textContent = 'Показати фактичний результат ↗';
}
function toggleOutcome() {
  const visible = $('outcome').hidden;
  $('outcome').hidden = !visible;
  $('comparison').hidden = !visible;
  $('reveal').setAttribute('aria-expanded', String(visible));
  $('reveal').textContent = visible ? 'Сховати фактичний результат ↑' : 'Показати фактичний результат ↗';
  if (!visible) return;
  $('actual').textContent = fmt(current.actual_minutes);
  $('error').textContent = fmt(current.absolute_error_minutes);
  const delta = current.actual_minutes - current.prediction_minutes;
  $('error-note').textContent = delta > 0 ? `Оцінка коротша за вигаданий факт на ${fmt(delta)} хв. Це ілюстрація недооцінки.` : `Оцінка довша за вигаданий факт на ${fmt(-delta)} хв. Це ілюстрація завищення.`;
  const scale = Math.max(current.prediction_minutes, current.actual_minutes);
  $('prediction-bar').style.width = `${current.prediction_minutes / scale * 100}%`;
  $('actual-bar').style.width = `${current.actual_minutes / scale * 100}%`;
  $('prediction-bar-value').textContent = `${fmt(current.prediction_minutes)} хв`;
  $('actual-bar-value').textContent = `${fmt(current.actual_minutes)} хв`;
}
function addLatest(latest) {
  if (!latest) return;
  const row = document.createElement('tr');
  [latest.label || 'latest91 · додаткова діагностика', latest.n, fmt(latest.MAE, 3), fmt(latest.RMSE, 3), latest.median_AE == null ? '—' : fmt(latest.median_AE, 3), latest.p90_AE == null ? '—' : fmt(latest.p90_AE, 3)].forEach((value, i) => {
    const cell = document.createElement(i === 0 ? 'th' : 'td');
    if (i === 0) cell.scope = 'row';
    cell.textContent = value;
    row.appendChild(cell);
  });
  $('metric-rows').appendChild(row);
  $('latest-note').hidden = false;
  $('latest-note').textContent = latest.note;
}
async function init() {
  try {
    const response = await fetch('assets/demo-data.json', {cache: 'no-cache'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
    if (data.schema_version !== 1 || data.method !== 'median_last_30_completed' || data.examples.length !== 3 || data.examples.some(x => !x.synthetic || !Number.isFinite(x.prediction_minutes) || x.used_n !== 30)) throw new Error('Некоректна схема демонстрації');
    $('selection-rule').textContent = data.selection_rule;
    document.querySelectorAll('[data-example]').forEach(button => button.addEventListener('click', () => selectExample(button.dataset.example)));
    $('reveal').addEventListener('click', toggleOutcome);
    selectExample('typical');
    addLatest(data.latest91);
    $('load-state').hidden = true;
    $('demo-content').hidden = false;
  } catch (error) {
    $('load-state').textContent = 'Не вдалося завантажити приклади. Оновіть сторінку або перегляньте інструкцію на GitHub. Таблиця primary84 нижче залишається доступною.';
    console.error('Demo load failed:', error.message);
  }
}
init();
