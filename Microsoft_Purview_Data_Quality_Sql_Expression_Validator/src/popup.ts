type Verdict = 'valid' | 'invalid' | 'warning' | 'empty';

interface ValidationResult {
  verdict: Verdict;
  errors: string[];
  warnings: string[];
}

const DISALLOWED = [
  { re: /\bINSERT\b/i, msg: 'INSERT is a DML statement and cannot appear in a predicate.' },
  { re: /\bUPDATE\b/i, msg: 'UPDATE is a DML statement and cannot appear in a predicate.' },
  { re: /\bDELETE\b/i, msg: 'DELETE is a DML statement and cannot appear in a predicate.' },
  { re: /\bTRUNCATE\b/i, msg: 'TRUNCATE is not allowed in data quality rules.' },
  { re: /\bDROP\b/i, msg: 'DROP is not allowed in data quality rules.' },
  { re: /\bALTER\b/i, msg: 'ALTER is not allowed in data quality rules.' },
  { re: /\bGRANT\b/i, msg: 'GRANT is a DCL statement and cannot appear in a predicate.' },
  { re: /\bREVOKE\b/i, msg: 'REVOKE is a DCL statement and cannot appear in a predicate.' },
  { re: /\bMERGE\b/i, msg: 'MERGE is not allowed in data quality rules.' },
];

const UNSUPPORTED_FN = ['isDelete', 'isError', 'isIgnore', 'isInsert', 'isUpdate', 'isUpsert', 'partitionId'];

const WINDOW_FN = ['row_number', 'rank', 'dense_rank', 'lag', 'lead', 'first_value', 'last_value', 'ntile', 'percent_rank', 'cume_dist'];

const BOOLEAN_INDICATORS = [
  />=|<=|<>|!=/,
  /[<>=]/,
  /\bBETWEEN\b/i,
  /\bIN\b\s*\(/i,
  /\bLIKE\b/i,
  /\bRLIKE\b/i,
  /\bIS\s+(NOT\s+)?NULL\b/i,
  /\bEXISTS\b/i,
  /\bAND\b/i,
  /\bOR\b/i,
  /\bNOT\b/i,
  /\bTRUE\b|\bFALSE\b/i,
];

function validateExpression(expr: string): ValidationResult {
  const t = expr.trim();
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!t) return { verdict: 'empty', errors, warnings };

  if (!BOOLEAN_INDICATORS.some(p => p.test(t))) {
    errors.push('Expression must evaluate to a Boolean — add a comparison (=, >, <, LIKE, IN, IS NULL, BETWEEN) or logical operator (AND, OR, NOT).');
  }

  for (const { re, msg } of DISALLOWED) {
    if (re.test(t)) errors.push(msg);
  }

  if (/\bJOIN\b/i.test(t)) {
    errors.push('JOINs are not supported — rules must operate on a single dataset.');
  }

  for (const fn of UNSUPPORTED_FN) {
    if (new RegExp(`\\b${fn}\\b`, 'i').test(t)) {
      errors.push(`${fn}() is not supported in Purview SQL rules.`);
    }
  }

  const usedWindow = WINDOW_FN.filter(fn => new RegExp(`\\b${fn}\\b`, 'i').test(t));
  if (usedWindow.length) {
    warnings.push(`Window function${usedWindow.length > 1 ? 's' : ''} (${usedWindow.join(', ')}) can be expensive on large datasets — test on a small sample first.`);
  }

  if (/\bSELECT\b/i.test(t) && !/\bAS\s+\w+\b/i.test(t)) {
    warnings.push('Subquery detected — alias inner columns (e.g. payment_type AS pt) to avoid ambiguous column references.');
  }

  const verdict = errors.length > 0 ? 'invalid' : warnings.length > 0 ? 'warning' : 'valid';
  return { verdict, errors, warnings };
}

function debounce<T extends (...args: unknown[]) => void>(fn: T, ms: number): T {
  let timer: ReturnType<typeof setTimeout>;
  return ((...args: unknown[]) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  }) as T;
}

function renderVerdict(
  badge: HTMLElement,
  messages: HTMLElement,
  results: Array<{ label: string; result: ValidationResult }>
) {
  messages.innerHTML = '';
  badge.className = 'verdict-badge';

  const allEmpty = results.every(r => r.result.verdict === 'empty');
  if (allEmpty) {
    badge.className = 'verdict-badge hidden';
    return;
  }

  const hasError = results.some(r => r.result.verdict === 'invalid');
  const hasWarn = !hasError && results.some(r => r.result.verdict === 'warning');

  if (hasError) {
    badge.textContent = '\u2717  INVALID';
    badge.classList.add('verdict-invalid');
  } else if (hasWarn) {
    badge.textContent = '\u26a0  VALID WITH WARNINGS';
    badge.classList.add('verdict-warning');
  } else {
    badge.textContent = '\u2713  VALID';
    badge.classList.add('verdict-valid');
  }

  for (const { label, result } of results) {
    if (result.verdict === 'empty') continue;
    for (const err of result.errors) {
      const p = document.createElement('p');
      p.className = 'msg msg-error';
      p.textContent = `${label}: ${err}`;
      messages.appendChild(p);
    }
    for (const warn of result.warnings) {
      const p = document.createElement('p');
      p.className = 'msg msg-warning';
      p.textContent = `${label}: ${warn}`;
      messages.appendChild(p);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const rowField    = document.querySelector<HTMLTextAreaElement>('#row-expr')!;
  const filterField = document.querySelector<HTMLTextAreaElement>('#filter-expr')!;
  const nullField   = document.querySelector<HTMLTextAreaElement>('#null-expr')!;
  const badge       = document.querySelector<HTMLElement>('#verdict-badge')!;
  const messages    = document.querySelector<HTMLElement>('#messages')!;

  function run() {
    renderVerdict(badge, messages, [
      { label: 'Row',    result: validateExpression(rowField.value) },
      { label: 'Filter', result: validateExpression(filterField.value) },
      { label: 'Null',   result: validateExpression(nullField.value) },
    ]);
  }

  const debouncedRun = debounce(run as (...args: unknown[]) => void, 300);

  rowField.addEventListener('input', debouncedRun);
  filterField.addEventListener('input', debouncedRun);
  nullField.addEventListener('input', debouncedRun);
});
