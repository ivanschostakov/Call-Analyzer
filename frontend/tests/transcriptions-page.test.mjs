// Run with node --test tests/transcriptions-page.test.mjs.
// Set PLAYWRIGHT_MODULE and CHROMIUM_PATH to use existing local browser dependencies.
import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
let server;
let browser;
let baseUrl;
const now = '2026-10-20T12:00:00+05:00';
const user = { id: 1, name: 'Test', surname: 'Owner', email: 'owner@example.test', role: 'owner' };

function summary(id, companyId = 1) {
  return {
    id, company_id: companyId, uploaded_by_user_id: 1, detected_employee_user_id: 2,
    file_id: `file-${id}`, original_filename: `call-${id}.wav`, status: 'completed',
    media_url: `/uploads/${companyId}/file-${id}/media`, language: 'ru',
    text_preview: `Preview ${id}`, has_text: true, is_favorite: false,
    call_started_at: null, created_at: now, updated_at: now,
  };
}

before(async () => {
  server = await createServer({ server: { host: '127.0.0.1', port: 0, strictPort: false } });
  await server.listen();
  baseUrl = `http://127.0.0.1:${server.httpServer.address().port}`;
  browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH });
});

after(async () => {
  await browser?.close();
  await server?.close();
});

async function setup(t, { viewport = { width: 1440, height: 1000 }, existingAnalysis = false } = {}) {
  const context = await browser.newContext({ viewport });
  t.after(() => context.close());
  const page = await context.newPage();
  page.setDefaultTimeout(10_000);
  const state = {
    requests: [], details: [], analyses: [], errors: [], delay: 0,
    listError: false, detailError: false, total: 1419, empty: false,
    analysisDelay: 0, status: 'completed',
  };
  page.on('pageerror', (error) => state.errors.push(error.message));
  await context.addInitScript(({ user }) => {
    localStorage.setItem('call-analyzer.auth', JSON.stringify({
      accessToken: 'test', refreshToken: 'test', sessionId: 'test', tokenType: 'bearer', user,
    }));
  }, { user });
  await context.route('**/*', async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== baseUrl) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const path = url.pathname.slice(4);
    const respond = (body, status = 200) => route.fulfill({ status, json: body });
    if (path === '/auth/me') return respond(user);
    if (path === '/companies') return respond([1, 2].map((id) => ({
      id, owner_id: 1, name: `Company ${id}`, created_at: now, updated_at: now,
    })));
    if (path === '/employees') return respond([{
      id: 1, user_id: 2, user_display_name: 'Employee Two', user_email: 'two@example.test',
    }]);
    if (path === '/templates') return respond([{ id: 7, name: 'Template', company_id: 1 }]);
    if (path === '/analysis' && route.request().method() === 'GET') {
      return respond(existingAnalysis ? [{ id: 77, transcription_id: 1419, template_id: 7, created_at: now }] : []);
    }
    if (path === '/analysis' && route.request().method() === 'POST') {
      state.analyses.push(route.request().postDataJSON());
      if (state.analysisDelay) await new Promise((resolve) => setTimeout(resolve, state.analysisDelay));
      return respond({ id: 88 });
    }
    if (/^\/transcriptions\/\d+\/list\/page$/.test(path)) {
      state.requests.push(Object.fromEntries(url.searchParams));
      if (state.delay) await new Promise((resolve) => setTimeout(resolve, state.delay));
      if (state.listError) return respond({ detail: 'List unavailable' }, 500);
      const pageSize = Number(url.searchParams.get('page_size'));
      const total = state.empty ? 0 : state.total;
      const actualPage = Math.min(Number(url.searchParams.get('page')), Math.max(1, Math.ceil(total / pageSize)));
      const start = total - (actualPage - 1) * pageSize;
      return respond({
        items: Array.from({ length: Math.min(pageSize, Math.max(0, start)) }, (_, i) => ({
          ...summary(start - i, Number(path.split('/')[2])), status: state.status,
        })),
        total, page: actualPage, page_size: pageSize,
      });
    }
    if (/^\/transcriptions\/\d+\/file-\d+$/.test(path)) {
      state.details.push(path);
      if (state.detailError) return respond({ detail: 'Detail unavailable' }, 500);
      const id = Number(path.split('file-')[1]);
      return respond({
        ...summary(id), text: `FULL TRANSCRIPT ${id}\n${'complete text '.repeat(1000)}`,
        segments: [{ start: 0, end: 1, text: 'Timestamped segment' }],
      });
    }
    // Fail unexpected legacy list requests instead of silently accepting a regression.
    if (/^\/transcriptions\/\d+$/.test(path)) throw new Error('Legacy unpaginated list requested');
    return respond({ detail: 'Not in test fixture' }, 404);
  });
  return { page, state };
}

const listUrl = () => `${baseUrl}/companies/1/transcriptions`;
const nextPage = (page) => page.getByRole('button', { name: 'Следующая страница', exact: true });
const batchButton = (page) => page.getByRole('button', { name: /Анализировать выбранные/ });

test('loading is not empty; pagination is bounded; full text and timecodes load on demand', async (t) => {
  const { page, state } = await setup(t);
  state.delay = 700;
  await page.goto(listUrl());
  await page.getByText('Загружаем расшифровки...', { exact: true }).waitFor();
  assert.equal(await page.getByText('Расшифровок пока нет.', { exact: true }).count(), 0);
  await page.getByText('call-1419.wav', { exact: true }).waitFor();
  assert.equal(await page.locator('tbody tr').count(), 25);
  assert.equal(state.details.length, 0);
  assert.equal(await page.getByText(/FULL TRANSCRIPT/).count(), 0);
  await page.getByText('Preview 1419', { exact: true }).click();
  await page.getByText(/FULL TRANSCRIPT 1419/).waitFor();
  assert.equal(state.details.length, 1);
  assert.equal(await page.getByText(/Timestamped segment/).count(), 0);
  await page.getByText('Версия с таймкодами', { exact: true }).click();
  await page.getByText(/Timestamped segment/).waitFor();
  await page.getByText('Preview 1419', { exact: true }).click();
  await page.getByText(/FULL TRANSCRIPT 1419/).waitFor({ state: 'detached' });
  await page.getByRole('checkbox', { name: 'Выбрать call-1419.wav', exact: true }).check();
  assert.equal(await batchButton(page).isEnabled(), true);
  await nextPage(page).click();
  await page.getByText('call-1394.wav', { exact: true }).waitFor();
  assert.equal(await page.locator('tbody tr').count(), 25);
  assert.equal(await page.locator('tbody input[type=checkbox]:checked').count(), 0);
  assert.equal(await batchButton(page).isDisabled(), true);
  assert.equal(state.requests.at(-1).page, '2');
  assert.equal(state.requests[0].page_size, '25');
  await page.getByRole('navigation', { name: 'Страницы расшифровок' }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: '/tmp/callanalyzer-transcriptions-desktop.png' });
  assert.deepEqual(state.errors, []);
});

test('filters are server-side, reset page and selection, and distinguish filtered empty state', async (t) => {
  const { page, state } = await setup(t);
  await page.goto(listUrl());
  await page.getByText('call-1419.wav', { exact: true }).waitFor();
  await nextPage(page).click();
  await page.getByText('call-1394.wav', { exact: true }).waitFor();
  await page.getByRole('checkbox', { name: 'Выбрать call-1394.wav', exact: true }).check();
  await page.getByLabel('Сотрудник', { exact: true }).selectOption('2');
  await page.getByText('call-1419.wav', { exact: true }).waitFor();
  assert.equal(state.requests.at(-1).employee, '2');
  assert.equal(state.requests.at(-1).page, '1');
  assert.equal(await batchButton(page).isDisabled(), true);
  await Promise.all([
    page.waitForResponse((response) => response.url().includes('status=completed')),
    page.getByLabel('Статус', { exact: true }).selectOption('completed'),
  ]);
  state.empty = true;
  await page.getByLabel('Только избранные', { exact: true }).check();
  await page.getByText('По выбранным фильтрам расшифровок нет.', { exact: true }).waitFor();
  assert.equal(state.requests.at(-1).favorites_only, 'true');
  assert.equal(await nextPage(page).isDisabled(), true);
  assert.equal(await page.getByText('Расшифровок пока нет.', { exact: true }).count(), 0);
  assert.deepEqual(state.errors, []);
});

test('list and detail errors have retry, never an empty-state fallback', async (t) => {
  const { page, state } = await setup(t);
  state.listError = true;
  await page.goto(listUrl());
  await page.getByText('List unavailable', { exact: true }).waitFor();
  assert.equal(await page.getByText('Расшифровок пока нет.', { exact: true }).count(), 0);
  state.listError = false;
  await page.getByRole('button', { name: 'Повторить загрузку', exact: true }).click();
  await page.getByText('call-1419.wav', { exact: true }).waitFor();
  state.detailError = true;
  await page.getByText('Preview 1419', { exact: true }).click();
  await page.getByText('Detail unavailable', { exact: true }).waitFor();
  state.detailError = false;
  await page.getByRole('button', { name: 'Повторить загрузку', exact: true }).click();
  await page.getByText(/FULL TRANSCRIPT 1419/).waitFor();
  assert.deepEqual(state.errors, []);
});

test('batch analysis uses only current-page selections and skips existing analyses', async (t) => {
  const { page, state } = await setup(t, { existingAnalysis: true });
  state.analysisDelay = 400;
  await page.goto(listUrl());
  await page.getByRole('button', { name: 'К анализу', exact: true }).waitFor();
  await page.getByRole('checkbox', { name: 'Выбрать call-1419.wav', exact: true }).check();
  await page.getByRole('checkbox', { name: 'Выбрать call-1418.wav', exact: true }).check();
  await batchButton(page).click();
  await page.getByRole('button', { name: 'Анализируем...', exact: true }).first().waitFor();
  assert.equal(await nextPage(page).isDisabled(), true);
  await page.getByText('Анализ запущен или найден для 1 расшифровок.', { exact: true }).waitFor();
  assert.deepEqual(state.analyses, [{ transcription_id: 1418, template_id: 7 }]);
  assert.equal(state.details.length, 0);
  assert.equal(await page.locator('tbody input[type=checkbox]:checked').count(), 0);
  await page.getByRole('button', { name: 'К анализу', exact: true }).click();
  await page.waitForURL('**/analysis/77');
  assert.equal(state.analyses.length, 1);
  assert.deepEqual(state.errors, []);
});

test('page size, last-page recovery, company changes and mobile layout', async (t) => {
  const { page, state } = await setup(t, { viewport: { width: 390, height: 844 } });
  state.total = 26;
  await page.goto(listUrl());
  await page.getByText('call-26.wav', { exact: true }).waitFor();
  await Promise.all([
    page.waitForResponse((response) => response.url().includes('page_size=50')),
    page.getByLabel('На странице', { exact: true }).selectOption('50'),
  ]);
  await page.waitForFunction(() => document.querySelectorAll('tbody tr').length === 26);
  assert.equal(await nextPage(page).isDisabled(), true);
  await page.getByLabel('На странице', { exact: true }).selectOption('25');
  await nextPage(page).waitFor({ state: 'visible' });
  await page.waitForFunction(() => document.querySelectorAll('tbody tr').length === 25);
  await nextPage(page).click();
  await page.getByText('call-1.wav', { exact: true }).waitFor();
  assert.equal(await page.locator('tbody tr').count(), 1);
  state.total = 25;
  // A workspace invalidation after batch analysis simulates removal of the last row.
  await page.getByRole('checkbox', { name: 'Выбрать call-1.wav', exact: true }).check();
  await batchButton(page).click();
  await page.getByText('call-25.wav', { exact: true }).waitFor();
  await page.getByText(/Страница 1 из 1/).waitFor();
  assert.equal(await page.locator('tbody tr').count(), 25);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await page.getByRole('navigation', { name: 'Страницы расшифровок' }).scrollIntoViewIfNeeded();
  await page.screenshot({ path: '/tmp/callanalyzer-transcriptions-mobile.png' });
  await page.getByRole('checkbox', { name: 'Выбрать call-25.wav', exact: true }).check();
  await page.locator('header select').selectOption('2');
  await page.waitForURL('**/companies/2/transcriptions');
  await page.getByText('call-25.wav', { exact: true }).waitFor();
  assert.equal(await batchButton(page).isDisabled(), true);
  assert.equal(await page.locator('tbody input[type=checkbox]:checked').count(), 0);
  assert.deepEqual(state.errors, []);
});

test('successful empty list is explicit and queued rows continue polling until complete', async (t) => {
  const { page, state } = await setup(t);
  state.empty = true;
  await page.goto(listUrl());
  await page.getByText('Расшифровок пока нет.', { exact: true }).waitFor();
  assert.equal(await page.locator('tbody tr').count(), 0);
  assert.equal(await batchButton(page).isDisabled(), true);
  state.empty = false;
  state.total = 1;
  state.status = 'queued';
  await page.reload();
  const checkbox = page.getByRole('checkbox', { name: 'Выбрать call-1.wav', exact: true });
  await checkbox.waitFor();
  assert.equal(await checkbox.isDisabled(), true);
  state.status = 'completed';
  await page.waitForFunction(() => {
    const checkbox = document.querySelector('tbody input[type=checkbox]');
    return checkbox && !checkbox.disabled;
  });
  assert.equal(state.requests.length >= 3, true);
  assert.deepEqual(state.errors, []);
});
