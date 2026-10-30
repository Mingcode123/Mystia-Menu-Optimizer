// Run with: node --test tests/web-regression.cjs
// Exercises the published app and its actual generated Worker without a browser.
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const appPath = path.join(__dirname, '..', 'web', 'app.js');
const source = fs.readFileSync(appPath, 'utf8');
new vm.Script(source, { filename: appPath });
const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const scripts = [...html.matchAll(/<script src="\.\/([^\"]+)"><\/script>/g)].map(match => match[1].split('?')[0]);

function createApp() {
  const elements = new Map();
  function element(id = '') {
    return {
      id, value: '', checked: false, disabled: false, textContent: '',
      get innerHTML() { return this.html || ''; },
      set innerHTML(value) { this.html = value; this.children = []; },
      style: {}, dataset: {}, handlers: {}, children: [],
      classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
      addEventListener(type, fn) { this.handlers[type] = fn; },
      appendChild(child) { this.children.push(...(child.isFragment ? child.children : [child])); },
      setAttribute() {}, getAttribute() { return null; },
      querySelectorAll() { return []; }, contains() { return false; },
      focus() {}, remove() {}, click() { return this.handlers.click?.({ target: this }); },
    };
  }
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element(id));
      return elements.get(id);
    },
    createElement: () => element(), createDocumentFragment: () => ({ ...element(), isFragment: true }),
    querySelectorAll: () => [], addEventListener() {}, body: element(),
  };
  const workers = [];
  const blobs = new Map();
  const context = {
    document, window: {}, navigator: { hardwareConcurrency: 4 },
    performance: { now: () => 1 }, console, setTimeout() {},
    XLSX: require('../web/vendor/xlsx.full.min.js'),
    Blob: class { constructor(parts) { this.text = parts.join(''); } },
    URL: {
      createObjectURL(blob) { const id = 'blob:' + blobs.size; blobs.set(id, blob); return id; },
      revokeObjectURL() {},
    },
    Worker: class {
      constructor(url) { this.url = url; this.terminated = false; workers.push(this); }
      postMessage(message) { this.sent = message; }
      terminate() { this.terminated = true; }
    },
  };
  vm.createContext(context);
  for (const script of scripts) {
    // SheetJS is already supplied through require; run the published local bundles in page order.
    if (script === 'web/vendor/xlsx.full.min.js') continue;
    const filename = path.join(root, script);
    vm.runInContext(fs.readFileSync(filename, 'utf8'), context, { filename });
  }
  return { context, elements, workers, blobs, document };
}

function runWorker(payload) {
  const app = createApp();
  const worker = app.context.makeWorker();
  const messages = [];
  const context = { postMessage(message) { messages.push(JSON.parse(JSON.stringify(message))); } };
  vm.createContext(context);
  vm.runInContext(app.blobs.get(worker.url).text, context);
  context.onmessage({ data: { type: 'RUN', payload } });
  assert.equal(messages.at(-1).type, 'DONE');
  return messages.filter(m => m.type === 'ROWS').flatMap(m => m.rows);
}

function input(overrides = {}) {
  return {
    wid: 0,
    foods: [{ name: '测试菜', tags: [], cookware: '料理台', sellPrice: 30,
      requiredIngredients: ['基础', '基础', '基础', '基础'], forbiddenIngredients: [] }],
    ingredients: [{ name: '甲', tags: ['甜'] }, { name: '乙', tags: ['肉'] }],
    guest: { name: '测试客人', preferredTags: [], dislikedTags: [] },
    tdqRawMap: {}, options: { minScore: 0, requiredTags: ['大份'] },
    ...overrides,
  };
}

test('published page defaults to the game snapshot and real guests are selectable', () => {
  const { context, document } = createApp();
  assert.ok(scripts.indexOf('web/game-data.js') < scripts.indexOf('web/app.js'));
  const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'data/game.json'), 'utf8'));
  assert.deepEqual(JSON.parse(JSON.stringify(context.window.MYSTIA_GAME_DATA)), snapshot);
  assert.equal(snapshot.metadata.kind, 'game-data');
  assert.equal(snapshot.sheets['食材'].length, 62);
  const counts = vm.runInContext('[DATA.ingredients.length, DATA.foods.length, DATA.guests.length]', context);
  // The existing planner excludes the special ingredient 铃仙 from its candidate pool.
  assert.deepEqual(Array.from(counts), [61, 164, 58]);
  assert.equal(document.getElementById('dataState').textContent, '游戏数据');
  assert.match(document.getElementById('dataSource').textContent, /作者工作簿的数据快照/);
  assert.equal(document.getElementById('btnRun').disabled, false);
  assert.equal(document.getElementById('warnBox').style.display, 'none');
  document.getElementById('guestBtn').click();
  assert.equal(document.getElementById('guestGrid').children.length, 58);
  context.renderGuestGrid('博丽灵梦');
  const guestCard = document.getElementById('guestGrid').children[0];
  assert.equal(guestCard.children[0].children[0].src, './web/icons/customer_rare/007_博丽灵梦.png');
  guestCard.click();
  assert.equal(document.getElementById('guestNameText').textContent, '博丽灵梦');
  assert.equal(document.getElementById('guestAvatar').children[0].src, './web/icons/customer_rare/007_博丽灵梦.png');
  context.renderTable([{ '料理': '饭团', '售价': 6, '得分': 0, '总食材数': 1 }]);
  assert.match(document.getElementById('tbody').children[0].innerHTML, /src="\.\/web\/icons\/recipe\/007_饭团\.png"/);
  for (const [kind, entries] of Object.entries(context.window.IZAKAYA_ICON_MAP)) {
    assert.ok(['recipe', 'customer_rare'].includes(kind));
    for (const relative of Object.values(entries)) {
      assert.ok(fs.existsSync(path.join(root, 'web', 'icons', relative)), 'missing icon: ' + relative);
    }
  }
});

test('switching between game and synthetic data clears old results and data-specific inputs', () => {
  const { context, document } = createApp();
  const demo = JSON.parse(fs.readFileSync(path.join(root, 'data/demo.json'), 'utf8'));
  assert.deepEqual(JSON.parse(JSON.stringify(context.window.MYSTIA_DEMO_DATA)), demo);
  const gameNames = vm.runInContext('DATA.guests.map(g => g.name)', context);
  const seedPreviousState = () => {
    vm.runInContext('RESULTS = [{"料理":"旧数据"}]; FILTERED = RESULTS; FILTERS.dishSet.add("旧数据");', context);
    for (const id of ['trendLikeInput', 'trendHateInput', 'excludedTagInput', 'requiredTagInput']) {
      document.getElementById(id).value = '旧标签';
    }
  };
  const checkClearedState = () => {
    assert.equal(vm.runInContext('RESULTS.length + FILTERED.length + FILTERS.dishSet.size', context), 0);
    assert.equal(document.getElementById('btnCSV').disabled, true);
    for (const id of ['trendLikeInput', 'trendHateInput', 'excludedTagInput', 'requiredTagInput']) {
      assert.equal(document.getElementById(id).value, '');
    }
  };
  seedPreviousState();
  document.getElementById('btnLoadDemo').click();
  assert.equal(document.getElementById('dataState').textContent, '合成示例');
  assert.match(document.getElementById('dataSource').textContent, /均为虚构/);
  const demoNames = vm.runInContext('DATA.guests.map(g => g.name)', context);
  assert.equal(demoNames.length, 3);
  assert.ok(demoNames.every(name => !gameNames.includes(name)));
  checkClearedState();
  seedPreviousState();
  document.getElementById('btnLoadGame').click();
  assert.equal(document.getElementById('dataState').textContent, '游戏数据');
  assert.deepEqual(Array.from(vm.runInContext('DATA.guests.map(g => g.name)', context)), Array.from(gameNames));
  checkClearedState();
});

test('forbidden entries exclude ingredient names and ingredient tags', () => {
  const data = input({ ingredients: [
    { name: '甜豆', tags: ['甜'] }, { name: '青菜', tags: ['素'] }, { name: '肉片', tags: ['肉'] },
  ] });
  data.foods[0].forbiddenIngredients = ['甜豆', '肉'];
  const rows = runWorker(data);
  assert.equal(rows.length, 1);
  assert.equal(rows[0]['加料'], '青菜');
  assert.ok(!rows[0]['最终tag'].includes('肉'));
});

test('TDQ replacement stays inside the current dish legal equivalent members', () => {
  const data = input({
    ingredients: [{ name: '合法豆', tags: ['甜'] }, { name: '禁用豆', tags: ['甜'] }],
    tdqRawMap: { '合法豆': 1, '禁用豆': 99 },
    options: { minScore: 0, requiredTags: ['大份'], eqIngDedup: true, tdqRecommend: true, tdqTopN: 3 },
  });
  data.foods[0].forbiddenIngredients = ['禁用豆'];
  const rows = runWorker(data);
  assert.equal(rows.length, 1);
  assert.equal(rows[0]['加料'], '合法豆');
});

test('repeated equivalent picks count unordered combinations for Top N', () => {
  const data = input({
    ingredients: [{ name: '甲', tags: ['甜'] }, { name: '乙', tags: ['甜'] }, { name: '丙', tags: ['素'] }],
    tdqRawMap: { '甲': 10, '乙': 10, '丙': 5 },
    options: { minScore: 0, requiredTags: ['大份'], eqIngDedup: true, tdqRecommend: true, tdqTopN: 4 },
  });
  data.foods[0].requiredIngredients = ['基础', '基础', '基础'];
  const deduped = runWorker(data);
  assert.equal(deduped.length, 2, 'three high-ranked original pairs must not fill four ranking places');
  assert.ok(deduped.some(row => row['加料'].includes('丙')));
  data.options.eqIngDedup = false;
  const expanded = runWorker(data);
  assert.equal(expanded.length, 5, 'three best pairs plus two tied next-best pairs');
});

test('tag overrides, unique scoring, required and excluded tags retain their rules', () => {
  const data = input({
    ingredients: [{ name: '肉片', tags: ['肉', '肉'] }, { name: '甜豆', tags: ['甜'] }],
    guest: { preferredTags: ['肉', '实惠'], dislikedTags: ['素'] },
    options: { minScore: 2, requiredTags: ['大份', '肉'], excludedTags: ['甜'] },
  });
  data.foods[0].tags = ['素'];
  data.foods[0].sellPrice = 18;
  const rows = runWorker(data);
  assert.equal(rows.length, 1);
  assert.equal(rows[0]['得分'], 2);
  assert.ok(!rows[0]['最终tag'].includes('素'));
});

test('zero is a valid threshold, while malformed and out-of-range input are rejected', () => {
  const { context } = createApp();
  assert.equal(context.readMinScore('0'), 0);
  assert.equal(context.readMinScore('-2'), -2);
  for (const value of ['', 'x', 'Infinity', '1.5', '11']) assert.equal(context.readMinScore(value), null);
});

test('an empty filtered result exports zero rows rather than all hidden results', () => {
  const { context } = createApp();
  vm.runInContext('RESULTS = [{"料理":"隐藏项"}]; FILTERED = [];', context);
  assert.equal(context.getExportRows().length, 0);
  vm.runInContext('FILTERED = [{"料理":"可见项"}];', context);
  assert.equal(context.getExportRows()[0]['料理'], '可见项');
});

test('stop immediately terminates all active Workers, resets controls and ignores stale messages', () => {
  const app = createApp();
  app.context.testInput = input();
  app.context.testInput.foods = Array.from({ length: 3 }, (_, i) => ({ ...app.context.testInput.foods[0], name: '测试菜' + i }));
  vm.runInContext('DATA = testInput; CURRENT_GUEST = testInput.guest;', app.context);
  app.document.getElementById('scoreMin').value = '0';
  app.document.getElementById('btnRun').click();
  assert.equal(app.workers.length, 3);
  const worker = app.workers[0];
  assert.equal(worker.sent.payload.options.minScore, 0);
  assert.equal(app.document.getElementById('fileInput').disabled, true);
  assert.equal(app.document.getElementById('btnLoadGame').disabled, true);
  assert.equal(app.document.getElementById('btnLoadDemo').disabled, true);
  app.document.getElementById('btnStop').click();
  assert.ok(app.workers.every(w => w.terminated));
  assert.equal(app.document.getElementById('btnRun').disabled, false);
  assert.equal(app.document.getElementById('btnStop').disabled, true);
  assert.equal(app.document.getElementById('fileInput').disabled, false);
  assert.equal(app.document.getElementById('btnLoadGame').disabled, false);
  assert.equal(app.document.getElementById('btnLoadDemo').disabled, false);
  const status = app.document.getElementById('statusText').textContent;
  assert.match(status, /已停止/);
  worker.onmessage({ data: { type: 'DONE', wid: 0 } });
  assert.equal(app.document.getElementById('statusText').textContent, status);
  assert.equal(app.document.getElementById('btnCSV').disabled, true);
});

test('published JSON data contract validates its version and requires row arrays', () => {
  const { context } = createApp();
  assert.throws(() => context.parseJSONData({ format: 'unknown', sheets: {} }), /格式/);
  assert.throws(() => context.parseJSONData({ format: 'mystia-planner-data/v1', sheets: { '食材': {} } }), /记录数组/);
  const data = context.parseJSONData({ format: 'mystia-planner-data/v1', metadata: { synthetic: true }, sheets: {
    '食材': [{ name: '测试豆', Tags: '甜' }],
    '料理': [{ name: '测试菜', Tags: '甜', 'Required Ingredients': '测试豆' }],
    '稀客': [{ name: '测试客人', type: 'rare', 'Preferred Tags': '甜' }],
    '食材merchant_data': [{ Name: '测试豆', 'Total Daily Quantity': 5 }],
  } });
  assert.equal(data.guests[0].name, '测试客人');
  assert.equal(data.tdqRawMap['测试豆'], 5);
});

test('XLSX and JSON imports produce the same normalized rules and data', () => {
  const { context } = createApp();
  const data = { format: 'mystia-planner-data/v1', sheets: {
    '食材': [{ name: '测试豆', Tags: '甜、素' }],
    '料理': [{ name: '测试菜', Tags: '素', cookware: '煮锅', 'Sell Price': 18, 'Required Ingredients': '测试豆', 'Forbidden Ingredients': '肉' }],
    '稀客': [{ name: '测试客人', type: 'rare', 'Preferred Tags': '甜、素', 'Disliked Tags': '肉' }],
    '食材merchant_data': [{ Name: '测试豆', 'Total Daily Quantity': 5 }],
  } };
  const xlsx = context.XLSX;
  const workbook = xlsx.utils.book_new();
  for (const [name, rows] of Object.entries(data.sheets)) {
    xlsx.utils.book_append_sheet(workbook, xlsx.utils.json_to_sheet(rows), name);
  }
  const bytes = xlsx.write(workbook, { type: 'buffer', bookType: 'xlsx' });
  const fromJSON = JSON.parse(JSON.stringify(context.parseJSONData(data)));
  const fromXLSX = JSON.parse(JSON.stringify(context.parseExcel(bytes)));
  assert.deepEqual(fromXLSX, fromJSON);
});

test('repeated base ingredients survive import and consume four of the five slots', () => {
  const { context } = createApp();
  const payload = { format: 'mystia-planner-data/v1', sheets: {
    '食材': [{ name: '基础豆', Tags: '素' }, { name: '甜豆', Tags: '甜' }],
    '料理': [{ name: '四份豆菜', 'Required Ingredients': '基础豆\n基础豆/基础豆、基础豆', cookware: '煮锅', 'Sell Price': 30 }],
    '稀客': [{ name: '客人', type: 'rare', 'Preferred Tags': '甜' }],
    '食材merchant_data': [{ Name: '基础豆', TDQ: 10 }, { Name: '甜豆', TDQ: 10 }],
  } };
  const parsed = context.parseJSONData(payload);
  assert.equal(parsed.foods[0].requiredIngredients.length, 4);
  const rows = runWorker({ ...parsed, guest: parsed.guests[0], options: { minScore: 1, requiredTags: ['大份'] } });
  assert.equal(rows.length, 1);
  assert.equal(rows[0]['总食材数'], 5);
  assert.equal(rows[0]['加料'], '甜豆');
  assert.equal(rows[0]['基础食材'], '基础豆、基础豆、基础豆、基础豆');
  payload.sheets['料理'][0]['Required Ingredients'] = ['基础豆', '基础豆', '基础豆', '基础豆'];
  assert.equal(context.parseJSONData(payload).foods[0].requiredIngredients.length, 4);
});

test('zero and missing prices add no price tag; boundary prices match the Python model', () => {
  for (const [price, expected] of [[0, null], [18, '实惠'], [20, null], [60, null], [61, '昂贵']]) {
    const data = input();
    data.foods[0].sellPrice = price;
    for (const row of runWorker(data)) {
      const tags = row['最终tag'].split('、');
      assert.equal(tags.includes('实惠'), expected === '实惠', 'price=' + price);
      assert.equal(tags.includes('昂贵'), expected === '昂贵', 'price=' + price);
    }
  }
  const { context } = createApp();
  assert.equal(context.parseSellingPrice(null, '测试菜'), 0);
  assert.equal(context.parseSellingPrice('', '测试菜'), 0);
  for (const value of [-1, Infinity, NaN, true, 'NaN', '?']) {
    assert.throws(() => context.parseSellingPrice(value, '测试菜'), /售价/);
  }
  assert.equal(context.pick({ 'Sell Price': 'NaN' }, ['Sell Price'], true), 'NaN', 'invalid values must reach price validation');
});
