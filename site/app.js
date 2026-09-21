'use strict';

const state = {
  pyodide: null,
  runtime: 'initializing',
  batchCsv: null,
  batchFilename: 'cdi-results.csv'
};

const PRIMARY_LIMIT = 25;
const SECONDARY_LIMIT = 12;
const STATUS_KEYWORDS = ['DISCORDANT', 'ANOMALY', 'EQUIVOCAL', 'SUSPICIOUS', 'FAIL', 'REJECT'];

const byId = (id) => document.getElementById(id);

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem('theme', theme);
  byId('themeToggle').setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
}

function initTheme() {
  const stored = localStorage.getItem('theme');
  setTheme(stored === 'dark' ? 'dark' : 'light');
}

function setRuntime(runtime, message) {
  state.runtime = runtime;
  const badge = byId('runtimeBadge');
  badge.textContent = message;
  badge.className = 'badge ' + (runtime === 'python' ? 'ready' : runtime === 'fallback' ? 'fallback' : '');
  byId('runtimeValue').textContent = runtime === 'python' ? 'Python' : runtime === 'fallback' ? 'JS fallback' : '—';
}

function fallbackEvaluate(payload) {
  const primary = Number(payload.primary_metric);
  const secondary = Number(payload.secondary_metric);
  const priority = Boolean(payload.is_stat);
  const status = String(payload.status_flag || 'NORMAL');
  const alerts = [];

  if (primary > PRIMARY_LIMIT) {
    alerts.push({
      code: 'PRIMARY_THRESHOLD',
      level: 'REVIEW',
      title: 'Primary metric review trigger',
      detail: primary.toFixed(2) + ' exceeds the configured demonstration threshold of ' + PRIMARY_LIMIT.toFixed(2) + '.'
    });
  }

  if (priority || secondary > SECONDARY_LIMIT) {
    alerts.push({
      code: 'PRIORITY_THRESHOLD',
      level: priority ? 'PRIORITY' : 'REVIEW',
      title: 'Priority review trigger',
      detail: 'Secondary metric=' + secondary.toFixed(2) + '; priority flag=' + priority + '; configured threshold=' + SECONDARY_LIMIT.toFixed(2) + '.'
    });
  }

  const upper = status.toUpperCase();
  if (STATUS_KEYWORDS.some((keyword) => upper.includes(keyword))) {
    alerts.push({
      code: 'STATUS_KEYWORD',
      level: 'REVIEW',
      title: 'Status descriptor review trigger',
      detail: "'" + status + "' matched a configured review keyword."
    });
  }

  let outcome = 'NO_RULE_TRIGGERED';
  if (alerts.some((alert) => alert.level === 'PRIORITY')) outcome = 'PRIORITY_REVIEW';
  else if (alerts.length) outcome = 'REVIEW_RECOMMENDED';

  return {
    case_id: String(payload.case_id || 'CASE-001'),
    outcome,
    alert_count: alerts.length,
    alerts,
    notice: 'Prototype output only; human validation is required.'
  };
}

async function initializePython() {
  if (typeof loadPyodide !== 'function') {
    setRuntime('fallback', 'JS fallback');
    return;
  }
  try {
    const pyodide = await loadPyodide({
      indexURL: 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/'
    });
    const response = await fetch('./runtime_engine.py', { cache: 'no-store' });
    if (!response.ok) throw new Error('runtime_engine.py could not be loaded');
    const source = await response.text();
    pyodide.runPython(source);
    state.pyodide = pyodide;
    setRuntime('python', 'Python ready');
  } catch (error) {
    console.warn('Python runtime unavailable; using deterministic JavaScript fallback.', error);
    setRuntime('fallback', 'JS fallback');
  }
}

function payloadFromForm() {
  return {
    case_id: byId('caseId').value.trim() || 'CASE-001',
    primary_metric: Number(byId('primaryMetric').value),
    secondary_metric: Number(byId('secondaryMetric').value),
    status_flag: byId('statusFlag').value,
    is_stat: byId('priorityFlag').checked
  };
}

function analyzeWithPython(payload) {
  state.pyodide.globals.set('payload_json', JSON.stringify(payload));
  return JSON.parse(state.pyodide.runPython('evaluate_case_json(payload_json)'));
}

function renderResult(result) {
  byId('outcomeValue').textContent = result.outcome;
  byId('alertCount').textContent = String(result.alert_count);
  byId('resultHint').textContent = result.case_id + ' · ' + result.notice;

  const pill = byId('outcomePill');
  pill.textContent = result.outcome.replaceAll('_', ' ');
  pill.className = 'outcome ' + (
    result.outcome === 'NO_RULE_TRIGGERED' ? 'good' :
    result.outcome === 'PRIORITY_REVIEW' ? 'priority' : 'review'
  );

  const alerts = byId('alerts');
  alerts.replaceChildren();
  if (!result.alerts.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'No configured rule was triggered.';
    alerts.appendChild(empty);
    return;
  }

  for (const alert of result.alerts) {
    const card = document.createElement('article');
    card.className = 'alert-card ' + (alert.level === 'PRIORITY' ? 'priority' : '');
    const title = document.createElement('strong');
    title.textContent = alert.title;
    const detail = document.createElement('p');
    detail.textContent = alert.detail;
    card.append(title, detail);
    alerts.appendChild(card);
  }
}

async function runCase(event) {
  event.preventDefault();
  const button = byId('analyzeButton');
  button.disabled = true;
  button.textContent = 'Analyzing…';
  try {
    const payload = payloadFromForm();
    const result = state.pyodide ? analyzeWithPython(payload) : fallbackEvaluate(payload);
    renderResult(result);
  } catch (error) {
    byId('resultHint').textContent = 'Analysis failed: ' + error.message;
    byId('outcomePill').textContent = 'Error';
    byId('outcomePill').className = 'outcome priority';
  } finally {
    button.disabled = false;
    button.textContent = 'Analyze case';
  }
}

function resetForm() {
  byId('caseForm').reset();
  byId('caseId').value = 'CASE-001';
  byId('primaryMetric').value = '28.5';
  byId('secondaryMetric').value = '14.2';
  byId('statusFlag').value = 'DISCORDANT';
  byId('resultHint').textContent = 'Run the configured rules to see a result.';
  byId('outcomeValue').textContent = '—';
  byId('alertCount').textContent = '0';
  byId('outcomePill').textContent = 'Ready';
  byId('outcomePill').className = 'outcome neutral';
  byId('alerts').innerHTML = '<div class="empty-state">No analysis has been run.</div>';
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = '';
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        cell += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      row.push(cell);
      cell = '';
    } else if (ch === '\n') {
      row.push(cell.replace(/\r$/, ''));
      rows.push(row);
      row = [];
      cell = '';
    } else {
      cell += ch;
    }
  }
  if (cell.length || row.length) {
    row.push(cell.replace(/\r$/, ''));
    rows.push(row);
  }
  return rows.filter((item) => item.some((cellValue) => cellValue !== ''));
}

function csvEscape(value) {
  const text = String(value == null ? '' : value);
  return /[",\n\r]/.test(text) ? '"' + text.replaceAll('"', '""') + '"' : text;
}

function parseBoolean(value) {
  return ['true', '1', 'yes', 'y', 'on'].includes(String(value || '').trim().toLowerCase());
}

function fallbackProcessCsv(text) {
  const rows = parseCsv(text);
  if (!rows.length) throw new Error('CSV must contain a header row.');
  const headers = rows[0];
  const outputHeaders = headers.concat(['outcome', 'alert_count'].filter((h) => !headers.includes(h)));
  const output = [outputHeaders.map(csvEscape).join(',')];
  let reviewRows = 0;

  for (let i = 1; i < rows.length; i += 1) {
    const values = rows[i];
    const record = {};
    headers.forEach((header, index) => { record[header] = values[index] || ''; });

    const result = fallbackEvaluate({
      case_id: record.case_id || record.task_id || 'ROW-' + (i + 1),
      primary_metric: record.metric_primary || record.primary_metric || 0,
      secondary_metric: record.metric_secondary || record.secondary_metric || 0,
      status_flag: record.status_flag || record.status_descriptor || 'NORMAL',
      is_stat: parseBoolean(Object.prototype.hasOwnProperty.call(record, 'is_stat') ? record.is_stat : record.is_critical_flag)
    });
    if (result.alert_count) reviewRows += 1;

    const resultRecord = Object.assign({}, record, {
      outcome: result.outcome,
      alert_count: result.alert_count
    });
    output.push(outputHeaders.map((header) => csvEscape(resultRecord[header])).join(','));
  }

  return {
    rows: Math.max(0, rows.length - 1),
    review_rows: reviewRows,
    csv: output.join('\n') + '\n'
  };
}

async function processBatch() {
  const file = byId('csvFile').files[0];
  if (!file) {
    byId('batchStatus').textContent = 'Select a CSV file first.';
    return;
  }

  const button = byId('batchButton');
  button.disabled = true;
  button.textContent = 'Processing…';
  try {
    const text = await file.text();
    let result;
    if (state.pyodide) {
      state.pyodide.globals.set('csv_text', text);
      result = JSON.parse(state.pyodide.runPython('evaluate_csv(csv_text)'));
    } else {
      result = fallbackProcessCsv(text);
    }

    state.batchCsv = result.csv;
    state.batchFilename = file.name.replace(/\.csv$/i, '') + '-results.csv';
    byId('downloadButton').disabled = false;
    byId('batchStatus').textContent = result.rows + ' row(s) processed; ' + result.review_rows + ' row(s) triggered review rules.';
  } catch (error) {
    state.batchCsv = null;
    byId('downloadButton').disabled = true;
    byId('batchStatus').textContent = 'Batch failed: ' + error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'Process CSV';
  }
}

function downloadBatch() {
  if (!state.batchCsv) return;
  const blob = new Blob([state.batchCsv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = state.batchFilename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function wireEvents() {
  byId('caseForm').addEventListener('submit', runCase);
  byId('resetButton').addEventListener('click', resetForm);
  byId('themeToggle').addEventListener('click', () => {
    setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  });
  byId('batchButton').addEventListener('click', processBatch);
  byId('downloadButton').addEventListener('click', downloadBatch);
  byId('csvFile').addEventListener('change', () => {
    const file = byId('csvFile').files[0];
    byId('batchStatus').textContent = file ? file.name + ' selected.' : 'No file selected.';
    byId('downloadButton').disabled = true;
    state.batchCsv = null;
  });
}

initTheme();
wireEvents();
initializePython();
