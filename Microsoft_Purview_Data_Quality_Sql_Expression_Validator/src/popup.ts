declare const browser: {
  storage: {
    local: {
      get(keys: string[]): Promise<Record<string, unknown>>;
      set(items: Record<string, unknown>): Promise<void>;
    };
  };
};

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
    errors.push(`Window function${usedWindow.length > 1 ? 's' : ''} (${usedWindow.join(', ')}) ${usedWindow.length > 1 ? 'are' : 'is'} not supported in Purview data quality expressions — rules are evaluated row-by-row and cannot perform set-based window operations.`);
  }

  // ROW_NUMBER, RANK, DENSE_RANK require ORDER BY inside OVER()
  const orderRequiringFns = ['row_number', 'rank', 'dense_rank'];
  for (const fn of orderRequiringFns) {
    const fnRe = new RegExp(`\\b${fn}\\s*\\(\\s*\\)\\s*OVER\\s*\\(([^)]+)\\)`, 'i');
    const m = fnRe.exec(t);
    if (m && !/\bORDER\s+BY\b/i.test(m[1])) {
      errors.push(`${fn.toUpperCase()}() requires ORDER BY inside OVER() to produce deterministic results — e.g. OVER (PARTITION BY Phone ORDER BY id).`);
    }
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

// ---- Purview API ----

interface PurviewConfig {
  clientId: string;
  clientSecret: string;
  tenantId: string;
  accountName: string;
  endpoint: string;
  scanEndpoint: string;
  foundryResponsesUrl: string;
  foundryApiKey: string;
}

interface GovDomain {
  id: string;
  name?: string;
  status?: string;
  type?: string;
}

interface DataProduct {
  id: string;
  name?: string;
  status?: string;
}

interface DataAsset {
  id: string;
  name?: string;
  assetType?: string;
}

interface ColumnInfo {
  name: string;
  dataType: string;
}

interface RuleContext {
  domainId: string;
  productId: string;
  assetId: string;
  assetName: string;
  columnName: string;
}

const NIL_UUID = '00000000-0000-0000-0000-000000000000';

type DataTypeCategory = 'string' | 'numeric' | 'date' | 'boolean' | 'other';

function classifyDataType(rawType: string): DataTypeCategory {
  const t = rawType.toLowerCase();
  if (/string|varchar|nvarchar|char|nchar|text|clob/.test(t)) return 'string';
  if (/\bint\b|integer|bigint|smallint|tinyint|float|double|decimal|numeric|real|number|money/.test(t)) return 'numeric';
  if (/date|datetime|timestamp|time/.test(t)) return 'date';
  if (/bool/.test(t)) return 'boolean';
  return 'other';
}

interface DimTemplate {
  condition: string;
  filterCriteria: string;
  emptyCriteria: string;
  typeWarning?: string;
}

function getDimTemplate(dim: string, dataType: string): DimTemplate {
  const cat = classifyDataType(dataType);
  switch (dim) {
    case 'Accuracy':
      if (cat === 'string')  return { condition: "{COL} IS NOT NULL AND TRIM({COL}) <> ''",                              filterCriteria: '', emptyCriteria: "{COL} IS NULL OR TRIM({COL}) = ''" };
      if (cat === 'date')    return { condition: '{COL} IS NOT NULL AND {COL} <= current_date()',                        filterCriteria: '', emptyCriteria: '{COL} IS NULL' };
      return                        { condition: '{COL} IS NOT NULL',                                                     filterCriteria: '', emptyCriteria: '{COL} IS NULL' };

    case 'Completeness':
      if (cat === 'string')  return { condition: "{COL} IS NOT NULL AND TRIM({COL}) <> ''",                              filterCriteria: '', emptyCriteria: "{COL} IS NULL OR TRIM({COL}) = ''" };
      return                        { condition: '{COL} IS NOT NULL',                                                     filterCriteria: '', emptyCriteria: '{COL} IS NULL' };

    case 'Conformity':
      if (cat === 'string')  return { condition: "{COL} RLIKE '^\\\\S.*\\\\S$'",                                        filterCriteria: '', emptyCriteria: "{COL} IS NULL OR TRIM({COL}) = ''" };
      if (cat === 'date')    return { condition: "{COL} IS NOT NULL AND {COL} BETWEEN '1900-01-01' AND current_date()", filterCriteria: '', emptyCriteria: '{COL} IS NULL' };
      if (cat === 'boolean') return { condition: '{COL} IN (true, false)',                                               filterCriteria: '', emptyCriteria: '{COL} IS NULL' };
      if (cat === 'numeric') return { condition: '{COL} IS NOT NULL',                                                    filterCriteria: '', emptyCriteria: '{COL} IS NULL' };
      return                        { condition: "{COL} RLIKE '^\\\\S.*\\\\S$'",                                        filterCriteria: '', emptyCriteria: "{COL} IS NULL OR TRIM(CAST({COL} AS STRING)) = ''" };

    case 'Consistency':
      if (cat === 'string')  return { condition: "{COL} IS NOT NULL AND LENGTH(TRIM({COL})) > 0",                       filterCriteria: '', emptyCriteria: "{COL} IS NULL OR TRIM({COL}) = ''" };
      if (cat === 'date')    return { condition: "{COL} IS NOT NULL AND {COL} >= '1900-01-01'",                         filterCriteria: '', emptyCriteria: '{COL} IS NULL' };
      return                        { condition: '{COL} IS NOT NULL',                                                    filterCriteria: '', emptyCriteria: '{COL} IS NULL' };

    case 'Timeliness':
      if (cat === 'date')    return { condition: '{COL} >= date_sub(current_date(), 365)',                               filterCriteria: '', emptyCriteria: '{COL} IS NULL' };
      return { condition: '{COL} IS NOT NULL', filterCriteria: '', emptyCriteria: '{COL} IS NULL',
               typeWarning: `Timeliness is designed for date/timestamp columns — '${dataType || 'unknown type'}' may not produce meaningful results.` };

    case 'Uniqueness':
      return { condition: '{COL} IS NOT NULL', filterCriteria: '', emptyCriteria: '{COL} IS NULL' };

    default:
      return { condition: '{COL} IS NOT NULL', filterCriteria: '', emptyCriteria: '{COL} IS NULL' };
  }
}

const GOV_BASE = 'https://api.purview-service.microsoft.com';
const PURVIEW_API_VER = '2025-09-15-preview';

let _lastRulePayload: Record<string, unknown> | null = null;
let _lastRuleUrl      = '';
let _lastRuleHeaders: Record<string, string> = {};
let _lastRuleResponse = '';

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function getToken(cfg: PurviewConfig, scope = 'https://purview.azure.net/.default'): Promise<string> {
  const body = new URLSearchParams({
    grant_type:    'client_credentials',
    client_id:     cfg.clientId,
    client_secret: cfg.clientSecret,
    scope,
  });
  const res = await fetch(
    `https://login.microsoftonline.com/${cfg.tenantId}/oauth2/v2.0/token`,
    {
      method:  'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body:    body.toString(),
    }
  );
  if (!res.ok) {
    const errBody = await res.text().catch(() => '');
    throw new Error(`Token request failed (${res.status}): ${errBody}`);
  }
  const data = await res.json() as { access_token: string };
  return data.access_token;
}

async function fetchDomains(token: string): Promise<GovDomain[]> {
  const all: GovDomain[] = [];
  let nextLink: string | undefined;
  for (;;) {
    const url = nextLink ??
      `${GOV_BASE}/datagovernance/catalog/businessdomains?api-version=${PURVIEW_API_VER}`;
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error(`Domains request failed (${res.status})`);
    const data = await res.json() as { value?: GovDomain[]; nextLink?: string };
    all.push(...(data.value ?? []));
    nextLink = data.nextLink;
    if (!nextLink) break;
  }
  return all;
}

async function fetchDataProducts(token: string, domainId: string): Promise<DataProduct[]> {
  const all: DataProduct[] = [];
  let skip = 0;
  const top = 100;
  for (;;) {
    const url = new URL(`${GOV_BASE}/datagovernance/catalog/dataProducts`);
    url.searchParams.set('api-version', PURVIEW_API_VER);
    url.searchParams.set('top', String(top));
    url.searchParams.set('domainId', domainId);
    if (skip > 0) url.searchParams.set('skip', String(skip));
    const res = await fetch(url.toString(), { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error(`Data products request failed (${res.status})`);
    const data = await res.json() as { value?: DataProduct[]; nextLink?: string };
    const batch = data.value ?? [];
    all.push(...batch);
    if (!data.nextLink || batch.length < top) break;
    skip += top;
  }
  return all;
}

async function fetchDomainAssets(token: string, domainId: string): Promise<DataAsset[]> {
  // List all domain assets and keep only those not linked to a product
  // (dataProductId === NIL_UUID means standalone)
  const listUrl = new URL(`${GOV_BASE}/datagovernance/catalog/dataAssets`);
  listUrl.searchParams.set('api-version', PURVIEW_API_VER);
  listUrl.searchParams.set('domainId', domainId);
  listUrl.searchParams.set('top', '200');
  const listRes = await fetch(listUrl.toString(), { headers: { Authorization: `Bearer ${token}` } });
  if (listRes.ok) {
    const data = await listRes.json() as { value?: Array<Record<string, unknown>> };
    return (data.value ?? [])
      .filter(a => a['dataProductId'] === NIL_UUID)
      .map(a => ({ id: a['id'] as string, name: a['name'] as string | undefined }));
  }

  const errBody = await listRes.text().catch(() => '');
  throw new Error(`Domain assets request failed (${listRes.status}): ${errBody}`);
}

async function fetchProductDetail(token: string, productId: string): Promise<{ id?: string }> {
  const url =
    `${GOV_BASE}/datagovernance/catalog/dataProducts/${encodeURIComponent(productId)}` +
    `?api-version=${PURVIEW_API_VER}`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) return {};
  const data = await res.json() as Record<string, unknown>;
  return { id: data['id'] as string | undefined };
}

async function fetchProductAssets(token: string, productId: string): Promise<DataAsset[]> {
  const url =
    `${GOV_BASE}/datagovernance/catalog/dataProducts/${encodeURIComponent(productId)}/relationships` +
    `?api-version=${PURVIEW_API_VER}&entityType=DATAASSET`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Relationships request failed (${res.status})`);
  const data = await res.json() as { value?: Array<{ entityId: string }> };
  return (data.value ?? []).map(r => ({ id: r.entityId }));
}

async function fetchAssetDetail(
  token: string,
  assetId: string
): Promise<{ id?: string; name?: string; assetType?: string; columns: ColumnInfo[] }> {
  const url =
    `${GOV_BASE}/datagovernance/catalog/dataAssets/${encodeURIComponent(assetId)}` +
    `?api-version=${PURVIEW_API_VER}`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Asset detail request failed (${res.status})`);
  const asset = await res.json() as Record<string, unknown>;

  // Extract columns from asset.schema — the dataAssets API returns schema inline.
  // Possible shapes: array of column objects, or { columns: [...] }
  let columns: ColumnInfo[] = [];
  const raw = asset['schema'];
  if (Array.isArray(raw)) {
    columns = extractColumns(raw);
  } else if (raw && typeof raw === 'object') {
    const schemaObj = raw as Record<string, unknown>;
    const inner = schemaObj['columns'] ?? schemaObj['fields'] ?? schemaObj['items'];
    if (Array.isArray(inner)) columns = extractColumns(inner);
  }

  return {
    id:        (asset['id']) as string | undefined,
    name:      (asset['name'] ?? asset['displayName']) as string | undefined,
    assetType: (asset['type'] ?? asset['assetType'] ?? asset['entityType']) as string | undefined,
    columns,
  };
}

function extractColumns(arr: unknown[]): ColumnInfo[] {
  return arr
    .map(c => {
      const col = c as Record<string, unknown>;
      const name = (col['name'] ?? col['columnName'] ?? col['displayName'] ?? '') as string;
      const dataType = (
        col['dataType'] ?? col['type'] ?? col['data_type'] ?? col['nativeDataType'] ?? ''
      ) as string;
      return { name, dataType };
    })
    .filter(c => c.name)
    .sort((a, b) => a.name.localeCompare(b.name));
}

async function fetchSchema(
  token: string,
  purviewEndpoint: string,
  guid: string
): Promise<ColumnInfo[]> {
  const base = purviewEndpoint.replace(/\/$/, '');
  const url =
    `${base}/datamap/api/atlas/v2/entity/bulk` +
    `?guid=${encodeURIComponent(guid)}&minExtInfo=true&ignoreRelationships=false`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) {
    const errBody = await res.text().catch(() => '');
    throw new Error(`Schema request failed (${res.status}): ${errBody}`);
  }
  const data = await res.json() as Record<string, unknown>;
  // referredEntities (populated via minExtInfo=true) contains all related entities
  // keyed by guid. Filter to those whose typeName ends with "column" (e.g. azure_sql_column,
  // databricks_column, etc.) — this is the canonical way per the DataMap REST docs.
  const referred = (data['referredEntities'] ?? {}) as Record<string, Record<string, unknown>>;
  const colEntities = Object.values(referred).filter(e =>
    typeof e['typeName'] === 'string' && e['typeName'].toLowerCase().endsWith('column')
  );
  return colEntities
    .map(col => {
      const attrs = (col['attributes'] ?? {}) as Record<string, unknown>;
      const name = (attrs['name'] as string | undefined) ?? '';
      const dataType =
        (attrs['dataType']  as string | undefined) ??
        (attrs['data_type'] as string | undefined) ??
        '';
      return { name, dataType };
    })
    .filter(c => c.name)
    .sort((a, b) => a.name.localeCompare(b.name));
}

async function createRule(
  token: string,
  cfg: PurviewConfig,
  ctx: RuleContext,
  ruleName: string,
  dimension: string,
  condition: string,
  filterCriteria: string,
  emptyCriteria: string,
  description = '',
): Promise<void> {
  const ruleId = crypto.randomUUID();
  const body = {
    id: ruleId,
    name: ruleName,
    type: 'CustomSQL',
    status: 'Active',
    description: description || `${dimension} rule for ${ctx.columnName}`,
    dimension,
    filters: ['_global'],
    typeProperties: {
      condition,
      ruleDialect: 'SparkSQL',
      columns: [{ value: ctx.columnName, type: 'Column' }],
    },
    businessDomain: { referenceId: ctx.domainId,  type: 'BusinessDomainReference' },
    dataProduct:    { referenceId: ctx.productId,  type: 'DataProductReference' },
    dataAsset:      { referenceId: ctx.assetId,    type: 'DataAssetReference' },
  };
  _lastRulePayload  = body;
  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
  _lastRuleHeaders  = {
    ...headers,
    'Authorization': `Bearer ${token.slice(0, 12)}…${token.slice(-6)}`,
  };

  const domId = encodeURIComponent(ctx.domainId);
  const prdId = encodeURIComponent(ctx.productId);
  const astId = encodeURIComponent(ctx.assetId);
  const ruleIdEnc = encodeURIComponent(ruleId);
  const base  = cfg.endpoint.replace(/\/$/, '');
  const url   = `${base}/purviewdataquality/api/business-domains/${domId}/data-products/${prdId}/data-assets/${astId}/rules/${ruleIdEnc}?api-version=2026-01-12-preview`;

  _lastRuleUrl      = url;
  _lastRuleResponse = '';
  const res = await fetch(url, { method: 'PUT', headers, body: JSON.stringify(body) });
  const resBody = await res.text().catch(() => '');
  _lastRuleResponse = `${res.status} ${res.statusText}\n\n${resBody || '(empty response body)'}`;
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
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

  // ---- Cog button / config overlay ----
  const cogBtn        = document.getElementById('cog-btn')!    as HTMLButtonElement;
  const configOverlay = document.getElementById('config-overlay')! as HTMLElement;
  const configClose   = document.getElementById('config-close')!   as HTMLButtonElement;

  cogBtn.addEventListener('click', () => {
    configOverlay.classList.remove('hidden');
    cogBtn.classList.add('active');
  });

  configClose.addEventListener('click', () => {
    configOverlay.classList.add('hidden');
    cogBtn.classList.remove('active');
  });

  // ---- Eye toggles ----
  document.querySelectorAll<HTMLButtonElement>('.eye-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.target!) as HTMLInputElement;
      const nowHidden = input.type === 'text';
      input.type = nowHidden ? 'password' : 'text';
      btn.classList.toggle('revealed', !nowHidden);
    });
  });

  // ---- Config: auto-derive endpoints from account name ----
  const cfgAccount  = document.getElementById('cfg-accountname') as HTMLInputElement;
  const cfgEndpoint = document.getElementById('cfg-endpoint')    as HTMLInputElement;
  const cfgScanEp   = document.getElementById('cfg-scanendpoint') as HTMLInputElement;

  cfgAccount.addEventListener('input', () => {
    const n = cfgAccount.value.trim();
    cfgEndpoint.value = n ? `https://${n}.purview.azure.com`      : '';
    cfgScanEp.value   = n ? `https://${n}.scan.purview.azure.com` : '';
  });

  // ---- Config: save ----
  const configForm   = document.getElementById('config-form')   as HTMLFormElement;
  const configStatus = document.getElementById('config-status') as HTMLElement;

  configForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const cfg = {
      clientId:        (document.getElementById('cfg-clientid')        as HTMLInputElement).value.trim(),
      clientSecret:    (document.getElementById('cfg-clientsecret')    as HTMLInputElement).value.trim(),
      tenantId:        (document.getElementById('cfg-tenantid')        as HTMLInputElement).value.trim(),
      accountName:     cfgAccount.value.trim(),
      endpoint:        cfgEndpoint.value.trim(),
      scanEndpoint:    cfgScanEp.value.trim(),
      foundryResponsesUrl: (document.getElementById('cfg-foundry-responses-url') as HTMLInputElement).value.trim(),
      foundryApiKey:        (document.getElementById('cfg-foundry-apikey')        as HTMLInputElement).value.trim(),
    };
    browser.storage.local.set({ purviewConfig: JSON.stringify(cfg) }).then(() => {
      configStatus.textContent = 'Configuration saved.';
      configStatus.className = 'config-status ok';
      setTimeout(() => {
        configStatus.textContent = '';
        configStatus.className = 'config-status';
      }, 2500);
    });
  });

  // ---- Config: load on open ----
  browser.storage.local.get(['purviewConfig']).then((result) => {
    const raw = result['purviewConfig'];
    if (typeof raw !== 'string') return;
    try {
      const cfg = JSON.parse(raw);
      (document.getElementById('cfg-clientid')        as HTMLInputElement).value = cfg.clientId         ?? '';
      (document.getElementById('cfg-clientsecret')    as HTMLInputElement).value = cfg.clientSecret     ?? '';
      (document.getElementById('cfg-tenantid')        as HTMLInputElement).value = cfg.tenantId         ?? '';
      cfgAccount.value  = cfg.accountName  ?? '';
      cfgEndpoint.value = cfg.endpoint     ?? '';
      cfgScanEp.value   = cfg.scanEndpoint ?? '';
      (document.getElementById('cfg-foundry-responses-url') as HTMLInputElement).value = cfg.foundryResponsesUrl ?? '';
      (document.getElementById('cfg-foundry-apikey')         as HTMLInputElement).value = cfg.foundryApiKey       ?? '';
    } catch { /* corrupt storage — ignore */ }
  });

  // ---- Browse panel ----
  const browseRefreshBtn = document.getElementById('browse-refresh-btn') as HTMLButtonElement;
  const browseStatusEl   = document.getElementById('browse-status')      as HTMLElement;
  const browseTree       = document.getElementById('browse-tree')         as HTMLElement;

  let _cachedToken = '';
  let _tokenExpiry = 0;

  async function getOrRefreshToken(cfg: PurviewConfig): Promise<string> {
    if (_cachedToken && Date.now() < _tokenExpiry) return _cachedToken;
    _cachedToken = await getToken(cfg);
    _tokenExpiry = Date.now() + 55 * 60 * 1000;
    return _cachedToken;
  }

  // ── Shared tree renderer (renders into any tree container, with a column renderer callback) ──

  // Validator tab — column chips insert column name into row expression
  function renderColumns(container: HTMLElement, columns: ColumnInfo[], _assetCtx: Omit<RuleContext, 'columnName'>) {
    container.innerHTML = '';
    if (!columns.length) {
      container.innerHTML = '<span class="browse-empty-cols">No columns found</span>';
      return;
    }
    for (const col of columns) {
      const chip = document.createElement('button');
      chip.className = 'col-chip';
      chip.title = col.dataType ? `${col.name} \u00b7 ${col.dataType}` : col.name;
      chip.innerHTML =
        `<span class="col-name">${escapeHtml(col.name)}</span>` +
        (col.dataType ? `<span class="col-type">${escapeHtml(col.dataType)}</span>` : '');
      chip.addEventListener('click', () => {
        const prev = rowField.value.trimEnd();
        rowField.value = prev ? prev + ' ' + col.name : col.name;
        rowField.focus();
        debouncedRun();
      });
      container.appendChild(chip);
    }
  }

  type ColRenderer = (container: HTMLElement, columns: ColumnInfo[], assetCtx: Omit<RuleContext, 'columnName'>) => void;

  function renderAssets(container: HTMLElement, assets: DataAsset[], token: string, cfg: PurviewConfig, assetCtx: { domainId: string; productId: string }, colRenderer: ColRenderer) {
    container.innerHTML = '';
    if (!assets.length) {
      container.innerHTML = '<span class="browse-empty-cols">No assets</span>';
      return;
    }
    for (const asset of assets) {
      const assetItem = document.createElement('div');
      assetItem.className = 'browse-asset';

      const assetHdr = document.createElement('button');
      assetHdr.className = 'browse-asset-hdr';
      assetHdr.innerHTML =
        `<svg class="browse-chevron" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>` +
        `<svg class="asset-icon" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>` +
        `<span class="browse-asset-name">${escapeHtml(asset.name ?? asset.id.slice(-8))}</span>` +
        (asset.assetType ? `<span class="browse-asset-type">${escapeHtml(asset.assetType)}</span>` : '');

      const colContainer = document.createElement('div');
      colContainer.className = 'browse-col-container';

      assetItem.appendChild(assetHdr);
      assetItem.appendChild(colContainer);
      container.appendChild(assetItem);

      let cachedDetail: Awaited<ReturnType<typeof fetchAssetDetail>> | null = null;
      let detailPromise: Promise<void> | null = null;
      let colsLoaded = false;

      detailPromise = fetchAssetDetail(token, asset.id).then(detail => {
        cachedDetail = detail;
        const nameEl = assetHdr.querySelector<HTMLElement>('.browse-asset-name');
        if (nameEl && detail.name) nameEl.textContent = detail.name;
      }).catch(() => { /* name stays as short id */ });

      assetHdr.addEventListener('click', async () => {
        const open = assetItem.classList.toggle('open');
        if (!open || colsLoaded) return;
        colContainer.innerHTML = '<span class="browse-loading-msg">Loading columns\u2026</span>';
        try {
          if (!cachedDetail) await detailPromise;
          if (!cachedDetail) throw new Error('Asset detail unavailable');
          if (!cachedDetail.columns.length) throw new Error('No columns found in asset schema');
          colsLoaded = true;
          // cachedDetail.id is the real DQ-API GUID from the asset detail response;
          // asset.id may be a catalog relationship entityId (different ID space).
          colRenderer(colContainer, cachedDetail.columns, {
            domainId:  assetCtx.domainId,
            productId: assetCtx.productId,
            assetId:   cachedDetail.id ?? asset.id,
            assetName: cachedDetail.name ?? asset.id.slice(-8),
          });
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          colContainer.innerHTML = `<span class="browse-err-msg">${escapeHtml(msg)}</span>`;
        }
      });
    }
  }

  function renderDomains(treeEl: HTMLElement, domains: GovDomain[], token: string, cfg: PurviewConfig, colRenderer: ColRenderer) {
    treeEl.innerHTML = '';
    if (!domains.length) {
      treeEl.innerHTML = '<p class="browse-empty-msg">No governance domains found.</p>';
      return;
    }
    for (const domain of domains) {
      const item = document.createElement('div');
      item.className = 'browse-domain';

      const hdr = document.createElement('button');
      hdr.className = 'browse-domain-hdr';
      hdr.innerHTML =
        `<svg class="browse-chevron" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>` +
        `<svg class="domain-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>` +
        `<span class="browse-domain-name">${escapeHtml(domain.name ?? domain.id)}</span>` +
        (domain.type ? `<span class="browse-domain-type">${escapeHtml(domain.type)}</span>` : '');

      const body = document.createElement('div');
      body.className = 'browse-domain-body';

      item.appendChild(hdr);
      item.appendChild(body);
      treeEl.appendChild(item);

      let loaded = false;
      hdr.addEventListener('click', async () => {
        const open = item.classList.toggle('open');
        if (!open || loaded) return;
        body.innerHTML = '<span class="browse-loading-msg">Loading\u2026</span>';
        try {
          const [products, standaloneAssets] = await Promise.all([
            fetchDataProducts(token, domain.id),
            fetchDomainAssets(token, domain.id),
          ]);
          loaded = true;
          body.innerHTML = '';
          if (products.length) {
            renderProducts(body, products, token, cfg, domain.id, colRenderer);
          }
          if (standaloneAssets.length) {
            const section = document.createElement('div');
            section.className = 'browse-standalone-section';
            const sectionHdr = document.createElement('div');
            sectionHdr.className = 'browse-standalone-hdr';
            sectionHdr.innerHTML =
              `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>` +
              `<span>Standalone Assets (${standaloneAssets.length})</span>`;
            section.appendChild(sectionHdr);
            renderAssets(section, standaloneAssets, token, cfg, { domainId: domain.id, productId: NIL_UUID }, colRenderer);
            body.appendChild(section);
          }
          if (!products.length && !standaloneAssets.length) {
            body.innerHTML = '<span class="browse-empty-cols">No data products or assets</span>';
          }
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          body.innerHTML = `<span class="browse-err-msg">${escapeHtml(msg)}</span>`;
        }
      });
    }
  }

  function renderProducts(container: HTMLElement, products: DataProduct[], token: string, cfg: PurviewConfig, domainId: string, colRenderer: ColRenderer) {
    container.innerHTML = '';
    if (!products.length) {
      container.innerHTML = '<span class="browse-empty-cols">No data products</span>';
      return;
    }
    for (const product of products) {
      const item = document.createElement('div');
      item.className = 'browse-product';

      const statusClass = 'status-' + (product.status ?? 'unknown').toLowerCase().replace(/\s+/g, '-');
      const hdr = document.createElement('button');
      hdr.className = 'browse-product-hdr';
      hdr.innerHTML =
        `<svg class="browse-chevron" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>` +
        `<span class="browse-product-name">${escapeHtml(product.name ?? 'Unnamed')}</span>` +
        (product.status
          ? `<span class="browse-status-tag ${statusClass}">${escapeHtml(product.status)}</span>`
          : '');

      const body = document.createElement('div');
      body.className = 'browse-product-body';

      item.appendChild(hdr);
      item.appendChild(body);
      container.appendChild(item);

      let loaded = false;
      hdr.addEventListener('click', async () => {
        const open = item.classList.toggle('open');
        if (!open || loaded) return;
        body.innerHTML = '<span class="browse-loading-msg">Loading assets\u2026</span>';
        try {
          // Fetch product detail to get real DQ product ID (catalog ID ≠ DQ API ID)
          const productDetail = await fetchProductDetail(token, product.id);
          const realProductId = productDetail.id ?? product.id;
          const assets = await fetchProductAssets(token, product.id);
          loaded = true;
          renderAssets(body, assets, token, cfg, { domainId, productId: realProductId }, colRenderer);
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err);
          body.innerHTML = `<span class="browse-err-msg">${escapeHtml(msg)}</span>`;
        }
      });
    }
  }

  // ── Tab switching ──
  const tabBtns   = document.querySelectorAll<HTMLButtonElement>('.tab-btn');
  const tabPanels = document.querySelectorAll<HTMLElement>('.tab-panel');
  let rgLoaded = false;
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab!;
      tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === target));
      tabPanels.forEach(p => p.classList.toggle('hidden', p.id !== `tab-${target}`));
      // Auto-load RG domains on first visit to the tab
      if (target === 'generator' && !rgLoaded) {
        rgLoaded = true;
        rgRefreshBtn.click();
      }
    });
  });

  // ── Validator tab: browse panel ──
  // Auto-load on page open
  browseRefreshBtn.click();

  browseRefreshBtn.addEventListener('click', async () => {
    const stored = await browser.storage.local.get(['purviewConfig']);
    const raw    = stored['purviewConfig'];
    if (typeof raw !== 'string') {
      browseStatusEl.textContent = 'No credentials saved \u2014 open \u2699 to configure.';
      browseStatusEl.className   = 'browse-status-msg err';
      return;
    }
    let cfg: PurviewConfig;
    try { cfg = JSON.parse(raw as string); } catch {
      browseStatusEl.textContent = 'Stored configuration is corrupt.';
      browseStatusEl.className   = 'browse-status-msg err';
      return;
    }
    browseStatusEl.textContent = 'Authenticating\u2026';
    browseStatusEl.className   = 'browse-status-msg';
    browseTree.innerHTML       = '';
    browseRefreshBtn.disabled  = true;
    try {
      const token   = await getOrRefreshToken(cfg);
      browseStatusEl.textContent = 'Loading governance domains\u2026';
      const domains = await fetchDomains(token);
      browseStatusEl.textContent = `${domains.length} domain${domains.length !== 1 ? 's' : ''}`;
      browseStatusEl.className   = 'browse-status-msg ok';
      renderDomains(browseTree, domains, token, cfg, renderColumns);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      browseStatusEl.textContent = msg;
      browseStatusEl.className   = 'browse-status-msg err';
    } finally {
      browseRefreshBtn.disabled = false;
    }
  });

  // ══ Rule Generator tab ══
  const rgRefreshBtn    = document.getElementById('rg-refresh-btn')     as HTMLButtonElement;
  const rgBrowseStatus  = document.getElementById('rg-browse-status')   as HTMLElement;
  const rgBrowseTree    = document.getElementById('rg-browse-tree')     as HTMLElement;
  const rgColSection    = document.getElementById('rg-col-section')     as HTMLElement;
  const rgColList       = document.getElementById('rg-col-list')        as HTMLElement;
  const rgColCountEl    = document.getElementById('rg-col-count')       as HTMLElement;
  const rgSelectAllCols = document.getElementById('rg-select-all-cols') as HTMLButtonElement;
  const rgDimCountEl    = document.getElementById('rg-dim-count')       as HTMLElement;
  const rgSelectAllDims = document.getElementById('rg-select-all-dims') as HTMLButtonElement;
  const rgSummary       = document.getElementById('rg-summary')         as HTMLElement;
  const rgCreateBtn     = document.getElementById('rg-create-btn')      as HTMLButtonElement;
  const rgProgress      = document.getElementById('rg-progress')        as HTMLElement;
  const rgProgressBar   = document.getElementById('rg-progress-bar')    as HTMLElement;
  const rgCreateStatus  = document.getElementById('rg-create-status')   as HTMLElement;
  const rgPreviewBtn    = document.getElementById('rg-preview-btn')      as HTMLButtonElement;
  const rgPreviewSection = document.getElementById('rg-preview-section') as HTMLElement;
  const rgTroubleshoot  = document.getElementById('rg-troubleshoot')!        as HTMLElement;
  const rgTsHeaders     = document.getElementById('rg-troubleshoot-headers')! as HTMLElement;
  const rgTsPayload     = document.getElementById('rg-troubleshoot-payload')! as HTMLElement;
  const rgTsError       = document.getElementById('rg-troubleshoot-error')!   as HTMLElement;
  document.getElementById('rg-troubleshoot-toggle')!.addEventListener('click', () => rgTroubleshoot.classList.toggle('open'));

  // RG state: columns available for the selected asset, plus which are checked
  let rgAssetCtx: Omit<RuleContext, 'columnName'> | null = null;
  let rgAllColumns: ColumnInfo[] = [];
  const rgSelectedCols = new Set<string>();
  type PreviewItem = { colName: string; dataType: string; dim: string; condition: string; filterCriteria: string; emptyCriteria: string; description: string; verdict: 'valid' | 'warning' | 'invalid'; messages: string[] };
  let rgPreviewItems: PreviewItem[] = [];

  function rgGetSelectedDims(): string[] {
    return Array.from(
      document.querySelectorAll<HTMLButtonElement>('.rg-dim-chip.active')
    ).map(b => b.dataset.dim!);
  }

  function rgUpdateSummary() {
    const cols = rgSelectedCols.size;
    const dims = rgGetSelectedDims().length;
    const total = cols * dims;
    rgColCountEl.textContent = cols ? `${cols} selected` : '';
    rgDimCountEl.textContent = dims ? `${dims} selected` : '';
    if (total === 0) {
      rgSummary.textContent  = 'Select columns and dimensions above';
      rgCreateBtn.disabled   = true;
    } else {
      rgSummary.textContent  = `${total} rule${total !== 1 ? 's' : ''} will be created (${cols} column${cols !== 1 ? 's' : ''} \u00d7 ${dims} dimension${dims !== 1 ? 's' : ''})`;
      rgCreateBtn.disabled   = false;
    }
    rgPreviewBtn.disabled = (total === 0);
    if (total === 0) rgPreviewSection.classList.add('hidden');
  }

  // Updates the preview header count badge based on current rgPreviewItems verdicts
  function rgUpdatePreviewCount() {
    const countEl  = document.getElementById('rg-preview-count')!;
    const invalids = rgPreviewItems.filter(i => i.verdict === 'invalid').length;
    const warns    = rgPreviewItems.filter(i => i.verdict === 'warning').length;
    if (invalids > 0) {
      countEl.textContent = `${invalids} invalid`;
      countEl.className   = 'rg-sel-count rg-preview-count-err';
    } else if (warns > 0) {
      countEl.textContent = `${warns} warning${warns !== 1 ? 's' : ''}`;
      countEl.className   = 'rg-sel-count rg-preview-count-warn';
    } else {
      countEl.textContent = `${rgPreviewItems.length} valid`;
      countEl.className   = 'rg-sel-count rg-preview-count-ok';
    }
  }

  // ---- Azure AI Foundry agent call ----
  // {project_endpoint}/applications/{agent_name}/protocols/openai/responses?api-version=2025-11-15-preview

  async function callFoundryAgent(
    assetName: string, colName: string, dataType: string, dim: string,
    cfg: PurviewConfig
  ): Promise<{ condition: string; filterCriteria: string; emptyCriteria: string; description: string }> {
    // Use the fully-configured URL directly — append api-version if not already present
    const url = cfg.foundryResponsesUrl.includes('api-version')
      ? cfg.foundryResponsesUrl
      : `${cfg.foundryResponsesUrl.replace(/\/+$/, '')}?api-version=2025-11-15-preview`;

    const userMsg =
      `You are generating Microsoft Purview Data Quality rule expressions in Spark SQL.\n` +
      `Always respond with EXACTLY the three labeled sections below — no questions, no clarifications.\n` +
      `Make reasonable assumptions based on the column name and data type.\n\n` +
      `Asset: ${assetName}\n` +
      `Column: ${colName}\n` +
      `Data type: ${dataType || 'STRING'}\n` +
      `Dimension: ${dim}\n\n` +
      `Respond in this exact format:\n` +
      `**Row Expression:** <Spark SQL boolean expression using \`${colName}\` that returns true for VALID rows>\n` +
      `**Filter Expression:** <expression to pre-filter rows before checking, or "None" if not needed>\n` +
      `**Null Expression:** <expression to identify null/empty rows, or "None" if not needed>\n` +
      `**Description:** <one or two sentences explaining what this rule validates and why it matters>\n\n` +
      `Rules:\n` +
      `- Row Expression must reference the column \`${colName}\` and be a valid Spark SQL boolean\n` +
      `- For Accuracy on STRING: use \`${colName} IS NOT NULL AND LENGTH(TRIM(${colName})) > 0\` as baseline if unsure\n` +
      `- For Completeness: check IS NOT NULL and non-empty\n` +
      `- For Uniqueness: \`${colName} IS NOT NULL\` (uniqueness is checked by the rule engine separately)\n` +
      `- Never ask for more information — always generate the best expression you can`;

    let authHeader: Record<string, string>;
    if (cfg.foundryApiKey) {
      authHeader = { 'api-key': cfg.foundryApiKey };
    } else {
      const foundryToken = await getToken(cfg, 'https://ai.azure.com/.default');
      authHeader = { 'Authorization': `Bearer ${foundryToken}` };
    }

    const MAX_RETRIES = 4;
    let res!: Response;
    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeader },
        body: JSON.stringify({ input: userMsg }),
      });
      if (res.status !== 429) break;
      if (attempt < MAX_RETRIES) {
        const retryAfter = Number(res.headers.get('Retry-After') ?? '0');
        const delay = retryAfter > 0 ? retryAfter * 1000 : (2 ** attempt) * 1000;
        await new Promise(r => setTimeout(r, delay));
      }
    }

    if (!res.ok) throw new Error(`Foundry ${res.status}: ${await res.text()}`);
    const json = await res.json() as { output_text?: string; output?: Array<{ type: string; content?: Array<{ type: string; text: string }> }> };

    // output_text is the convenience property; fall back to output array
    const rawText: string =
      json.output_text ??
      (json.output ?? [])
        .flatMap(o => o.content ?? [])
        .filter(c => c.type === 'output_text')
        .map(c => c.text)
        .join('') ?? '';

    if (!rawText) throw new Error('Empty response from Foundry agent.');

    function extractBlock(label: string): string {
      const re = new RegExp(`\\*\\*${label}:?\\*\\*[:\\s]*([\\s\\S]*?)(?=\\*\\*|$)`, 'i');
      const m = re.exec(rawText);
      if (!m) return '';
      return m[1].trim().replace(/^```[\w]*\n?|```$/gm, '').trim();
    }

    const condition      = extractBlock('Row Expression');
    const filterRaw      = extractBlock('Filter Expression');
    const nullRaw        = extractBlock('Null Expression');
    const description    = extractBlock('Description');
    const filterCriteria = /^none$/i.test(filterRaw) ? '' : filterRaw;
    const emptyCriteria  = /^none$/i.test(nullRaw)   ? '' : nullRaw;

    if (!condition) throw new Error(`Agent response did not contain a Row Expression.\n\nRaw response:\n${rawText}`);
    return { condition, filterCriteria, emptyCriteria, description };
  }

  // Builds rgPreviewItems from current col/dim selections (calls Foundry agent if configured)
  async function buildRulePreview(cfg: PurviewConfig | null) {
    rgPreviewItems = [];
    for (const colName of Array.from(rgSelectedCols)) {
      const colInfo  = rgAllColumns.find(c => c.name === colName);
      const dataType = colInfo?.dataType ?? '';
      for (const dim of rgGetSelectedDims()) {
        let condition: string;
        let filterCriteria = '';
        let emptyCriteria  = '';
        let agentError     = '';

        let description = '';
        if (cfg?.foundryResponsesUrl) {
          try {
            const res = await callFoundryAgent(
              rgAssetCtx?.assetName ?? '', colName, dataType, dim, cfg
            );
            condition      = res.condition;
            filterCriteria = res.filterCriteria;
            emptyCriteria  = res.emptyCriteria;
            description    = res.description;
          } catch (err) {
            agentError = err instanceof Error ? err.message : String(err);
            // Fall back to template
            const tpl = getDimTemplate(dim, dataType);
            condition      = tpl.condition.replace(/\{COL\}/g, colName);
            filterCriteria = tpl.filterCriteria.replace(/\{COL\}/g, colName);
            emptyCriteria  = tpl.emptyCriteria.replace(/\{COL\}/g, colName);
          }
        } else {
          const tpl = getDimTemplate(dim, dataType);
          condition      = tpl.condition.replace(/\{COL\}/g, colName);
          filterCriteria = tpl.filterCriteria.replace(/\{COL\}/g, colName);
          emptyCriteria  = tpl.emptyCriteria.replace(/\{COL\}/g, colName);
        }

        const vr = validateExpression(condition);
        const messages: string[] = agentError
          ? [`Agent error (using template fallback): ${agentError}`, ...vr.warnings]
          : [...vr.errors, ...vr.warnings];
        const verdict: 'valid' | 'warning' | 'invalid' =
          vr.verdict === 'invalid' && !agentError ? 'invalid' :
          (messages.length > 0) ? 'warning' : 'valid';
        rgPreviewItems.push({ colName, dataType, dim, condition, filterCriteria, emptyCriteria, description, verdict, messages });
      }
    }
  }

  function rgRenderPreview() {
    const list = document.getElementById('rg-preview-list')!;
    list.innerHTML = '';

    for (const item of rgPreviewItems) {
      const row = document.createElement('div');
      row.className = 'rg-preview-row';

      // Header: col name, type, dimension, verdict icon
      const header = document.createElement('div');
      header.className = 'rg-preview-header';

      const meta = document.createElement('div');
      meta.className = 'rg-preview-meta';

      const colSpan = document.createElement('span');
      colSpan.className = 'col-name';
      colSpan.textContent = item.colName;
      meta.appendChild(colSpan);

      if (item.dataType) {
        const typeSpan = document.createElement('span');
        typeSpan.className = 'col-type';
        typeSpan.textContent = item.dataType;
        meta.appendChild(typeSpan);
      }

      const dimSpan = document.createElement('span');
      dimSpan.className = 'rg-preview-dim';
      dimSpan.textContent = item.dim;
      meta.appendChild(dimSpan);

      const verdictSpan = document.createElement('span');

      function refreshVerdictSpan() {
        const cls = item.verdict === 'valid' ? 'ok' : item.verdict === 'warning' ? 'warn' : 'err';
        verdictSpan.className = `rg-preview-verdict ${cls}`;
        verdictSpan.textContent = item.verdict === 'valid' ? '\u2713' : item.verdict === 'warning' ? '\u26a0\ufe0f' : '\u2717';
      }
      refreshVerdictSpan();

      header.appendChild(meta);
      header.appendChild(verdictSpan);

      // Editable expression textarea
      const textarea = document.createElement('textarea');
      textarea.className = 'rg-preview-expr-edit';
      textarea.value = item.condition;
      textarea.rows = 2;
      textarea.spellcheck = false;

      // Validation note
      const noteEl = document.createElement('div');

      function refreshNote() {
        if (item.messages.length) {
          const cls = item.verdict === 'valid' ? '' : item.verdict === 'warning' ? 'warn' : 'err';
          noteEl.className = `rg-preview-note ${cls}`;
          noteEl.innerHTML = item.messages.map(m => escapeHtml(m)).join('<br>');
          noteEl.style.display = '';
        } else {
          noteEl.style.display = 'none';
        }
      }
      refreshNote();

      // Live re-validation on edit
      textarea.addEventListener('input', () => {
        item.condition = textarea.value;
        const vr = validateExpression(item.condition);
        item.messages = [...vr.errors, ...vr.warnings];
        item.verdict  = vr.verdict === 'invalid' ? 'invalid' : vr.warnings.length > 0 ? 'warning' : 'valid';
        refreshVerdictSpan();
        refreshNote();
        rgUpdatePreviewCount();
      });

      row.appendChild(header);
      row.appendChild(textarea);
      row.appendChild(noteEl);
      list.appendChild(row);
    }

    rgPreviewSection.classList.remove('hidden');
    rgUpdatePreviewCount();
  }

  // Renders checkbox column list in the Rule Generator tab
  function rgRenderColChips(columns: ColumnInfo[], assetCtx: Omit<RuleContext, 'columnName'>) {
    rgAllColumns  = columns;
    rgAssetCtx    = assetCtx;
    rgSelectedCols.clear();
    rgColList.innerHTML = '';
    rgSelectAllCols.disabled = false;
    rgPreviewItems = [];
    rgPreviewSection.classList.add('hidden');

    for (const col of columns) {
      const chip = document.createElement('button');
      chip.className = 'col-chip';
      chip.title = col.dataType ? `${col.name} \u00b7 ${col.dataType}` : col.name;
      chip.innerHTML =
        `<span class="col-name">${escapeHtml(col.name)}</span>` +
        (col.dataType ? `<span class="col-type">${escapeHtml(col.dataType)}</span>` : '');
      chip.addEventListener('click', () => {
        const isActive = chip.classList.toggle('active');
        if (isActive) rgSelectedCols.add(col.name);
        else          rgSelectedCols.delete(col.name);
        rgSelectAllCols.textContent =
          rgSelectedCols.size === columns.length ? 'Deselect All' : 'Select All';
        rgUpdateSummary();
      });
      rgColList.appendChild(chip);
    }
    rgUpdateSummary();
  }

  // Called when user clicks an asset in the RG browse tree
  function rgColRenderer(container: HTMLElement, columns: ColumnInfo[], assetCtx: Omit<RuleContext, 'columnName'>) {
    // Populate the column chip panel
    rgRenderColChips(columns, assetCtx);
    // Show a lightweight note in the tree slot
    container.innerHTML = '';
    const info = document.createElement('span');
    info.className   = 'browse-loading-msg';
    info.textContent = `${columns.length} column${columns.length !== 1 ? 's' : ''} loaded \u2014 select below`;
    container.appendChild(info);
    // Scroll to column section
    rgColSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Select / Deselect All columns
  rgSelectAllCols.addEventListener('click', () => {
    const allSelected = rgSelectedCols.size === rgAllColumns.length && rgAllColumns.length > 0;
    rgColList.querySelectorAll<HTMLButtonElement>('.col-chip').forEach(chip => {
      const colName = chip.querySelector<HTMLElement>('.col-name')!.textContent!;
      if (!allSelected) { chip.classList.add('active'); rgSelectedCols.add(colName); }
      else              { chip.classList.remove('active'); rgSelectedCols.delete(colName); }
    });
    rgSelectAllCols.textContent = allSelected ? 'Select All' : 'Deselect All';
    rgUpdateSummary();
  });

  // Select / Deselect All dimensions
  rgSelectAllDims.addEventListener('click', () => {
    const dimChips = document.querySelectorAll<HTMLButtonElement>('.rg-dim-chip');
    const allActive = Array.from(dimChips).every(c => c.classList.contains('active'));
    dimChips.forEach(c => c.classList.toggle('active', !allActive));
    rgSelectAllDims.textContent = allActive ? 'Select All' : 'Deselect All';
    rgUpdateSummary();
  });

  // Individual dimension chip toggles
  document.querySelectorAll<HTMLButtonElement>('.rg-dim-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chip.classList.toggle('active');
      const dimChips = document.querySelectorAll<HTMLButtonElement>('.rg-dim-chip');
      const allActive = Array.from(dimChips).every(c => c.classList.contains('active'));
      rgSelectAllDims.textContent = allActive ? 'Deselect All' : 'Select All';
      rgUpdateSummary();
    });
  });

  // Viewport-safe tooltip for dimension chips
  const dimTooltipEl = document.getElementById('dim-tooltip-overlay') as HTMLElement;
  document.querySelectorAll<HTMLButtonElement>('.rg-dim-chip[data-tooltip]').forEach(chip => {
    chip.addEventListener('mouseenter', () => {
      const text = chip.dataset['tooltip'] ?? '';
      if (!text || !dimTooltipEl) return;
      dimTooltipEl.textContent = text;
      // Park off-screen before measuring so layout is accurate at current viewport width
      dimTooltipEl.style.left = '-9999px';
      dimTooltipEl.style.top  = '-9999px';
      dimTooltipEl.classList.add('visible');
      const rect   = chip.getBoundingClientRect();
      const tw     = dimTooltipEl.offsetWidth;
      const th     = dimTooltipEl.offsetHeight;
      const MARGIN = 6;
      let left = rect.left + rect.width / 2 - tw / 2;
      left = Math.max(MARGIN, Math.min(left, window.innerWidth - tw - MARGIN));
      // Prefer above the chip; flip below if not enough vertical room
      const topAbove = rect.top - th - 6;
      const top = topAbove >= MARGIN ? topAbove : rect.bottom + 6;
      dimTooltipEl.style.left = `${left}px`;
      dimTooltipEl.style.top  = `${top}px`;
    });
    chip.addEventListener('mouseleave', () => dimTooltipEl.classList.remove('visible'));
  });

  // Preview expressions
  rgPreviewBtn.addEventListener('click', async () => {
    const stored = await browser.storage.local.get(['purviewConfig']);
    const raw    = stored['purviewConfig'];
    let cfg: PurviewConfig | null = null;
    if (typeof raw === 'string') { try { cfg = JSON.parse(raw); } catch { /* ignore */ } }

    const usingAgent = !!(cfg?.foundryResponsesUrl);
    const total = rgSelectedCols.size * rgGetSelectedDims().length;

    rgPreviewBtn.disabled  = true;
    rgPreviewBtn.textContent = usingAgent
      ? `Asking AI agent\u2026 (0 / ${total})`
      : 'Building preview\u2026';

    // Patch buildRulePreview to update button progress when using agent
    if (usingAgent) {
      rgPreviewItems = [];
      let done = 0;
      for (const colName of Array.from(rgSelectedCols)) {
        const colInfo  = rgAllColumns.find(c => c.name === colName);
        const dataType = colInfo?.dataType ?? '';
        for (const dim of rgGetSelectedDims()) {
          let condition: string;
          let filterCriteria = '';
          let emptyCriteria  = '';
          let agentError = '';
          let description = '';
          try {
            const res = await callFoundryAgent(
              rgAssetCtx?.assetName ?? '', colName, dataType, dim, cfg!
            );
            condition      = res.condition;
            filterCriteria = res.filterCriteria;
            emptyCriteria  = res.emptyCriteria;
            description    = res.description;
          } catch (err) {
            agentError = err instanceof Error ? err.message : String(err);
            const tpl = getDimTemplate(dim, dataType);
            condition      = tpl.condition.replace(/\{COL\}/g, colName);
            filterCriteria = tpl.filterCriteria.replace(/\{COL\}/g, colName);
            emptyCriteria  = tpl.emptyCriteria.replace(/\{COL\}/g, colName);
          }
          const vr = validateExpression(condition);
          const messages: string[] = agentError
            ? [`AI agent error \u2014 using template fallback: ${agentError}`, ...vr.warnings]
            : [...vr.errors, ...vr.warnings];
          const verdict: 'valid' | 'warning' | 'invalid' =
            vr.verdict === 'invalid' && !agentError ? 'invalid' :
            messages.length > 0 ? 'warning' : 'valid';
          rgPreviewItems.push({ colName, dataType, dim, condition, filterCriteria, emptyCriteria, description, verdict, messages });
          done++;
          rgPreviewBtn.textContent = `Asking AI agent\u2026 (${done} / ${total})`;
        }
      }
    } else {
      await buildRulePreview(cfg);
    }

    rgRenderPreview();
    rgPreviewBtn.disabled    = false;
    rgPreviewBtn.textContent = 'Preview Expressions';
  });

  // RG browse refresh
  rgRefreshBtn.addEventListener('click', async () => {
    const stored = await browser.storage.local.get(['purviewConfig']);
    const raw    = stored['purviewConfig'];
    if (typeof raw !== 'string') {
      rgBrowseStatus.textContent = 'No credentials saved \u2014 open \u2699 to configure.';
      rgBrowseStatus.className   = 'browse-status-msg err';
      return;
    }
    let cfg: PurviewConfig;
    try { cfg = JSON.parse(raw as string); } catch {
      rgBrowseStatus.textContent = 'Stored configuration is corrupt.';
      rgBrowseStatus.className   = 'browse-status-msg err';
      return;
    }
    rgBrowseStatus.textContent = 'Authenticating\u2026';
    rgBrowseStatus.className   = 'browse-status-msg';
    rgBrowseTree.innerHTML     = '';
    rgRefreshBtn.disabled      = true;
    try {
      const token   = await getOrRefreshToken(cfg);
      rgBrowseStatus.textContent = 'Loading governance domains\u2026';
      const domains = await fetchDomains(token);
      rgBrowseStatus.textContent = `${domains.length} domain${domains.length !== 1 ? 's' : ''} \u2014 expand an asset to load columns`;
      rgBrowseStatus.className   = 'browse-status-msg ok';
      renderDomains(rgBrowseTree, domains, token, cfg, rgColRenderer);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      rgBrowseStatus.textContent = msg;
      rgBrowseStatus.className   = 'browse-status-msg err';
    } finally {
      rgRefreshBtn.disabled = false;
    }
  });

  // Bulk create
  rgCreateBtn.addEventListener('click', async () => {
    if (!rgAssetCtx || rgSelectedCols.size === 0) return;
    const dims = rgGetSelectedDims();
    if (dims.length === 0) return;

    const stored = await browser.storage.local.get(['purviewConfig']);
    const raw = stored['purviewConfig'];
    if (typeof raw !== 'string') {
      rgCreateStatus.textContent = 'No credentials saved.';
      rgCreateStatus.className   = 'rule-create-status err';
      return;
    }
    let cfg: PurviewConfig;
    try { cfg = JSON.parse(raw as string); } catch {
      rgCreateStatus.textContent = 'Credentials corrupt.';
      rgCreateStatus.className   = 'rule-create-status err';
      return;
    }

    const cols  = Array.from(rgSelectedCols);
    const total = cols.length * dims.length;
    let done = 0;
    let failed = 0;
    let lastError = '';
    let lastPayload: Record<string, unknown> | null = null;

    rgCreateBtn.disabled           = true;
    rgCreateStatus.textContent     = '';
    rgCreateStatus.className       = 'rule-create-status';
    rgProgress.classList.remove('hidden');
    rgProgressBar.style.width      = '0%';
    rgTroubleshoot.classList.add('hidden');
    rgTroubleshoot.classList.remove('open');

    try {
      const token = await getOrRefreshToken(cfg);
      for (const col of cols) {
        for (const dim of dims) {
          const colInfo = rgAllColumns.find(c => c.name === col);
          const tpl = getDimTemplate(dim, colInfo?.dataType ?? '');
          const colRef = col;
          // Use the (possibly user-edited) condition from preview if available
          const previewItem = rgPreviewItems.find(i => i.colName === col && i.dim === dim);
          const condition      = previewItem ? previewItem.condition      : tpl.condition.replace(/\{COL\}/g, colRef);
          const filterCriteria = previewItem ? previewItem.filterCriteria : tpl.filterCriteria.replace(/\{COL\}/g, colRef);
          const emptyCriteria  = previewItem ? previewItem.emptyCriteria  : tpl.emptyCriteria.replace(/\{COL\}/g, colRef);
          const description    = previewItem?.description ?? '';
          const ruleName = `${rgAssetCtx.assetName} \u2013 ${col} \u2013 ${dim}`;
          const ctx: RuleContext = { ...rgAssetCtx, columnName: col };
          try {
            await createRule(token, cfg, ctx, ruleName, dim, condition, filterCriteria, emptyCriteria, description);
          } catch (err: unknown) {
            failed++;
            lastError = err instanceof Error ? err.message : String(err);
            lastPayload = _lastRulePayload;
          }
          done++;
          rgProgressBar.style.width = `${Math.round((done / total) * 100)}%`;
          rgCreateStatus.textContent = `Creating rules\u2026 ${done}/${total}`;
        }
      }
      if (failed === 0) {
        rgCreateStatus.textContent = `\u2713 ${total} rule${total !== 1 ? 's' : ''} created successfully`;
        rgCreateStatus.className   = 'rule-create-status ok';
      } else {
        rgCreateStatus.textContent = `${total - failed} created, ${failed} failed${lastError ? `\n${lastError}` : ''}`;
        rgCreateStatus.className   = 'rule-create-status err';
      }
      rgTsHeaders.textContent = `POST ${_lastRuleUrl}\n\n${Object.entries(_lastRuleHeaders).map(([k, v]) => `${k}: ${v}`).join('\n')}`;
      rgTsPayload.textContent = _lastRulePayload ? JSON.stringify(_lastRulePayload, null, 2) : '';
      rgTsError.textContent   = _lastRuleResponse;
      if (failed > 0) {
        rgTroubleshoot.classList.remove('hidden');
        rgTroubleshoot.classList.add('open');
      } else {
        rgTroubleshoot.classList.remove('hidden');
        rgTroubleshoot.classList.remove('open');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      rgCreateStatus.textContent = msg;
      rgCreateStatus.className   = 'rule-create-status err';
      rgTsHeaders.textContent = `POST ${_lastRuleUrl}\n\n${Object.entries(_lastRuleHeaders).map(([k, v]) => `${k}: ${v}`).join('\n')}`;
      rgTsPayload.textContent = _lastRulePayload ? JSON.stringify(_lastRulePayload, null, 2) : '';
      rgTsError.textContent   = _lastRuleResponse;
      rgTroubleshoot.classList.remove('hidden');
      rgTroubleshoot.classList.add('open');
    } finally {
      rgCreateBtn.disabled = false;
    }
  });
});
