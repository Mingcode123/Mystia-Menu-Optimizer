const ICON_BASE = "./web/icons";
const ICON_MAP = window.IZAKAYA_ICON_MAP || {};
const ICON_RARE = ICON_MAP.customer_rare || Object.create(null);
const ICON_RECIPE = ICON_MAP.recipe || Object.create(null);

function joinIconPath(rel){
  return rel ? ICON_BASE + "/" + rel : "";
}

function iconRecipe(name){
  return joinIconPath(ICON_RECIPE[normName(name)]);
}

function rareIconCandidates(name){
  const rel = ICON_RARE[normName(name)];
  return rel ? [joinIconPath(rel)] : [];
}

function setImgWithCandidates(img, candidates, onAllFail){
  let i = 0;
  function tryNext(){
    if (i >= candidates.length){
      if (onAllFail) onAllFail();
      return;
    }
    img.src = candidates[i++];
  }
  img.onerror = tryNext;
  tryNext();
}

/* -------------------------
   Helpers (main thread)
------------------------- */
const $ = (id)=>document.getElementById(id);

function readMinScore(value){
  if (String(value).trim() === "") return null;
  const n = Number(value);
  return Number.isInteger(n) && n >= -10 && n <= 10 ? n : null;
}

function stopCalculation(label = "已停止；本次未完成结果已清空"){
  if (ACTIVE_STOP) ACTIVE_STOP(label);
}

function setImportEnabled(enabled){
  $("fileInput").disabled = !enabled;
  $("btnLoadGame").disabled = !enabled;
  $("btnLoadDemo").disabled = !enabled;
}

function setStatus(text, pct){
  $("statusText").textContent = text;
  const p = Math.max(0, Math.min(100, pct|0));
  $("barFill").style.width = p + "%";
  $("statusRight").textContent = p + "%";
}

function warn(msg){
  const box = $("warnBox");
  box.style.display = "block";
  box.textContent = msg;
}
function clearWarn(){
  const box = $("warnBox");
  box.style.display = "none";
  box.textContent = "";
}

function safeStr(x){
  if (x === null || x === undefined) return "";
  return String(x).trim();
}
function normName(s){
  return safeStr(s).replace(/\u3000/g," ").trim();
}

function isNaNLike(x){
  return x === null || x === undefined ||
    (typeof x === "number" && Number.isNaN(x)) ||
    (typeof x === "string" && x.trim().toLowerCase() === "nan");
}

function splitTags(x){
  if (isNaNLike(x)) return [];
  // Recipe base ingredients are a multiset: never remove repeated names here.
  // Array cells preserve each item; text cells accept the same separators as Python.
  if (Array.isArray(x)) return x.map(normName).filter(Boolean);
  return String(x).split(/[、，,;；\/\n\r\t|]+/).map(normName).filter(Boolean);
}


function normalizeTrendTag(t){
  if (!t) return t;
  const s0 = String(t).trim();
  const s = s0.replace(/\s+/g, "");
  if (s === "流行喜爱") return "流行·喜爱";
  if (s === "流行厌恶") return "流行·厌恶";
  return s0;
}
function normalizeTagList(arr){
  return (arr||[]).map(normalizeTrendTag);
}



function splitTagTokens(s){
  // 支持空格、中文顿号/逗号、英文逗号、分号、斜杠等作为分隔符
  // 例如："菌类 水产" / "菌类、 水产" / "菌类，水产" / "菌类,水产" / "菌类/水产"
  const v0 = String(s||"").trim();
  if (!v0) return [];
  const v = v0
    .replace(/[\u3000]/g, " ")
    .replace(/[\n\r\t]+/g, " ")
    .replace(/[、，,;；\/]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!v) return [];
  return v.split(" ").map(x=>x.trim()).filter(Boolean);
}
function parseMultiTagInput(s){
  const toks = splitTagTokens(s).map(normalizeTrendTag).map(t=>String(t||"").trim()).filter(Boolean);
  const seen = new Set();
  const out = [];
  for (const t of toks){
    if (seen.has(t)) continue;
    seen.add(t);
    out.push(t);
  }
  return out;
}
function appendTokenToInput(el, token){
  if (!el) return;
  const t = String(token||"").trim();
  if (!t) return;
  const cur = splitTagTokens(el.value);
  if (cur.includes(t)){
    el.value = cur.join(" ");
    return;
  }
  cur.push(t);
  el.value = cur.join(" ");
}

function toFloat(x, d=0){
  if (isNaNLike(x)) return d;
  const n = Number(x);
  return Number.isFinite(n) ? n : d;
}

function parseSellingPrice(value, dishName){
  // A missing price is represented as zero, with no derived price tag.
  if (value === null || value === undefined || safeStr(value) === "") return 0;
  const number = Number(value);
  if (typeof value === "boolean" || !Number.isFinite(number) || number < 0){
    throw new Error("料理「" + dishName + "」的售价必须为非负有限数值。");
  }
  return number;
}

function toBoolLike(x, d=false){
  if (isNaNLike(x)) return d;
  const s = String(x).trim().toLowerCase();
  if (!s) return d;
  if (["1","true","yes","y","是","有","√","owned"].includes(s)) return true;
  if (["0","false","no","n","否","无","×"].includes(s)) return false;
  const n = Number(s);
  if (Number.isFinite(n)) return n !== 0;
  // 其它非空字符串默认视作 true
  return true;
}

function sheetToJSON(ws){
  return XLSX.utils.sheet_to_json(ws, {defval: null, raw: true});
}

// 统一表头匹配：忽略大小写、首尾空格、多个空格、全角空格
function normKey(k){
  return String(k||"")
    .replace(/\u3000/g, " ")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function pick(obj, keys, preserveInvalidNumbers=false){
  // 先尝试精确匹配（最快）
  for (const k of keys){
    if (k in obj && (preserveInvalidNumbers || !isNaNLike(obj[k])) && safeStr(obj[k]) !== "") return obj[k];
  }

  // 再尝试「归一化表头」匹配（容错：大小写/空格差异）
  const nmap = {};
  for (const kk in obj){
    nmap[normKey(kk)] = obj[kk];
  }
  for (const k of keys){
    const nk = normKey(k);
    if (nk in nmap && (preserveInvalidNumbers || !isNaNLike(nmap[nk])) && safeStr(nmap[nk]) !== "") return nmap[nk];
  }
  return null;
}

/* -------------------------
   Global state
------------------------- */
let DATA = null;
let WORKERS = [];
let ACTIVE_STOP = null;
let RUN_TOKEN = 0;
let WORKER_URL = null;
let RESULTS = [];
let FILTERED = [];
let SORT = {key:"售价", dir:1};
let LAST_META = "";

let CURRENT_GUEST = null;
let EQ_GROUPS = []; // [{tags:[], names:[]}]，用于展示“等价食材组（仅加料）”

function computeEqGroupsFromData(){
  EQ_GROUPS = [];
  if (!DATA || !DATA.ingredients) return;

  const map = new Map(); // sig -> {tags, names}
  for (const ing of (DATA.ingredients||[])){
    const name = normName(ing.name);
    if (!name) continue;

    const tags = (ing.tags||[])
      .map(t => normalizeTrendTag(String(t || "").trim()))
      .filter(Boolean);

    const uniq = Array.from(new Set(tags)).sort((a,b)=>a.localeCompare(b,"zh"));
    if (uniq.length === 0) continue; // 无tag：不参与等价组（避免“无tag”导致错误合并）

    const sig = uniq.join("|");
    let g = map.get(sig);
    if (!g){
      g = {tags: uniq, names: []};
      map.set(sig, g);
    }
    g.names.push(name);
  }

  for (const g of map.values()){
    const names = Array.from(new Set(g.names)).sort((a,b)=>a.localeCompare(b,"zh"));
    if (names.length < 2) continue;
    EQ_GROUPS.push({tags: g.tags, names});
  }

  EQ_GROUPS.sort((a,b)=>a.tags.join("、").localeCompare(b.tags.join("、"), "zh"));
}

function renderEqGroups(){
  const box = $("eqGroupInfo");
  if (!box) return;

  if (!EQ_GROUPS.length){
    box.textContent = "（未发现等价组：同tag的食材）";
    return;
  }

  let html = '<div><span class="pill">等价组</span> 仅用于“加料”视为等价（基础食材不等价）</div>';
  for (const g of EQ_GROUPS){
    const tagStr = g.tags.join("、");
    const ingStr = g.names.join("、");
    html += '<div class="eqGroupRow"><span class="pill">' + escapeHTML(tagStr) + '</span> ' + escapeHTML(ingStr) + '</div>';
  }
  box.innerHTML = html;
}


/* -------------------------
   Parse Excel
------------------------- */
function parseExcel(arrayBuffer){
  const wb = XLSX.read(arrayBuffer, {type:"array"});
  const sheets = Object.create(null);
  for (const name of wb.SheetNames) sheets[name] = sheetToJSON(wb.Sheets[name]);
  return parseDataSheets(sheets);
}

function parseJSONData(data){
  if (!data || data.format !== "mystia-planner-data/v1" || !data.sheets || typeof data.sheets !== "object"){
    throw new Error("JSON 格式不正确，需要 mystia-planner-data/v1 数据文件。");
  }
  return parseDataSheets(data.sheets);
}

function parseDataSheets(sheets){

  // 兼容：sheet 名称大小写/首尾空格差异
  function getSheetByName(name){
    const target = normKey(name);
    const found = Object.keys(sheets).find(n => normKey(n) === target);
    if (!found) return null;
    const rows = sheets[found];
    if (!Array.isArray(rows) || rows.some(row => !row || typeof row !== "object" || Array.isArray(row))){
      throw new Error("数据表必须是记录数组：" + name);
    }
    return rows;
  }

  const wsIng = getSheetByName("食材");
  const wsFood = getSheetByName("料理");
  const wsGuest = getSheetByName("稀客");

  if (!wsIng) throw new Error("缺少 sheet：食材（或名称存在大小写/空格差异）");
  if (!wsFood) throw new Error("缺少 sheet：料理（或名称存在大小写/空格差异）");
  if (!wsGuest) throw new Error("缺少 sheet：稀客（或名称存在大小写/空格差异）");

  const dfIng = wsIng;
  const dfFood = wsFood;
  const dfGuest = wsGuest;

  // 食材采购数据（TDQ）
  const wsMerch = getSheetByName("食材merchant_data");
  if (!wsMerch) throw new Error("缺少 sheet：食材merchant_data（或名称存在大小写/空格差异）");
  const dfMerch = wsMerch;

  const tdqRawMap = Object.create(null);
  for (const r of dfMerch){
    const nm = normName(pick(r, ["Name","name","名称"]));
    if (!nm) continue;
    const tdq = toFloat(pick(r, ["Total Daily Quantity","TDQ","每日采购量"]), NaN);
    if (Number.isFinite(tdq)) tdqRawMap[nm] = tdq;
  }


  // ingredients
  const ingredients = [];
  for (const r of dfIng){
    const name = normName(pick(r, ["name","名称"]));
    if (!name) continue;
    if (name === "黑暗物质" || name.toLowerCase() === "dark matter") continue;
    if (name === "铃仙") continue;
    ingredients.push({
      name,
      tags: splitTags(pick(r, ["Tags","标签","tag","tags"])),
      buyPrice: toFloat(pick(r, ["Buy Price","进货价","成本"]), 0),
      isOwned: toBoolLike(pick(r, ["Owned","持有","拥有","已拥有"]), false),
      level: toFloat(pick(r, ["Level","等级"]), 0),
    });
  }

// foods
  const foods = [];
  for (const r of dfFood){
    const name = normName(pick(r, ["name","名称"]));
    if (!name) continue;
    foods.push({
      name,
      cookware: normName(pick(r, ["cookware","厨具","烹饪","方式"])) || "",
      sellPrice: parseSellingPrice(pick(r, ["Sell Price","售价"], true), name),
      tags: splitTags(pick(r, ["Tags","标签","tag","tags"])),
      requiredIngredients: splitTags(pick(r, ["Required Ingredients","材料","食材","基础食材"])),
      forbiddenIngredients: splitTags(pick(r, ["Forbidden Ingredients","禁忌","不相容","冲突"])),
      isOwned: toBoolLike(pick(r, ["Owned","持有","拥有","已拥有"]), false),
      level: toFloat(pick(r, ["Level","等级"]), 0),
    });
  }

// rare guests (type=rare)
  const guests = [];
  for (const r of dfGuest){
    const typeRaw = pick(r, ["type","类型"]);
    const type = safeStr(typeRaw).replace(/\u3000/g," ").trim();
    const typeL = type.toLowerCase();
    if (typeL !== "rare" && type !== "稀客") continue;

    const name = normName(pick(r, ["name","名称"]));
    if (!name) continue;
    guests.push({
      name,
      budget: pick(r, ["Budget","金钱","金币","资金"]),
      preferredTags: splitTags(pick(r, ["Preferred Tags","喜好","喜欢","偏好"])),
      dislikedTags: splitTags(pick(r, ["Disliked Tags","厌恶","讨厌","不喜欢"])),
      spawnAreas: splitTags(pick(r, ["Spawn Areas","出没地区","地区","地点"])),
      beverageTags: splitTags(pick(r, ["Beverage Tags","酒水tag","酒水","饮料"])),
      level: toFloat(pick(r, ["Level","等级"]), 0),
    });
  }

if (!guests.length){
    const sample = dfGuest && dfGuest.length ? Object.keys(dfGuest[0]).join(", ") : "(稀客表为空)";
    throw new Error("没有解析到稀客（type=rare）。请检查：稀客 sheet 是否有列 type/name，且 type 的值为 'rare'（不区分大小写）或 '稀客'。当前表头示例：" + sample);
  }

  if (!foods.length || !ingredients.length) throw new Error("料理和食材表不能为空。");

  // all tags (for trend anchor selects)
  const tagSet = new Set();
  for (const f of foods) for (const t of (f.tags||[])) tagSet.add(t);
  for (const ing of ingredients) for (const t of (ing.tags||[])) tagSet.add(t);

  // 也把可能用到的“派生tag”放进去，方便你在下拉框里选择作为流行附着 anchor
  ["实惠","昂贵","料理台","蒸锅","油锅","烧烤架","煮锅","大份","小巧","流行·喜爱","流行·厌恶"].forEach(t=>tagSet.add(t));

  return {foods, ingredients, guests, tdqRawMap, allTags: Array.from(tagSet).sort((a,b)=>a.localeCompare(b,"zh"))};
}

function fillSelect(sel, items, emptyLabel){
  sel.innerHTML = "";
  const opt0 = document.createElement("option");
  opt0.value = "";
  opt0.textContent = emptyLabel || "(无)";
  sel.appendChild(opt0);
  for (const it of items){
    const opt = document.createElement("option");
    opt.value = it;
    opt.textContent = it;
    sel.appendChild(opt);
  }
  sel.disabled = false;
}

function fillCookFilterFromData(){
  const sel = $("cookFilter");
  if (!sel || !DATA) return;
  const set = new Set();
  for (const f of (DATA.foods||[])){
    const c = (f.cookware||"").trim();
    if (c) set.add(c);
  }
  const cooks = Array.from(set).sort((a,b)=>a.localeCompare(b,"zh"));
  sel.innerHTML = "";
  const o0 = document.createElement("option");
  o0.value = "";
  o0.textContent = "(全部 cookware)";
  sel.appendChild(o0);
  for (const c of cooks){
    const o = document.createElement("option");
    o.value = c;
    o.textContent = c;
    sel.appendChild(o);
  }
  sel.disabled = false;
}


/* -------------------------
   Guest picker UI
------------------------- */
let ALL_TAGS_CACHE = [];
let FILTERS = { dishSet: new Set(), cookwareSet: new Set(), scoreSet: new Set(), totalCountSet: new Set() };

function fillAllTagsDatalist(favOnly){
  // 只把「当前稀客 preferredTags」放进候选（datalist 下拉）
  const dl = $("allTagsList");
  if (!dl) return;
  dl.innerHTML = "";

  const seen = new Set();
  const list = (favOnly || [])
    .map(t => normalizeTrendTag(String(t || "").trim()))
    .filter(Boolean)
    .filter(t => (seen.has(t) ? false : (seen.add(t), true)))
    .sort((a,b)=>a.localeCompare(b,"zh"));

  for (const t of list){
    const opt = document.createElement("option");
    opt.value = t;
    dl.appendChild(opt);
  }
}

function refreshAllTagsCache(){
  // Tab 自动补全：使用「全 tag」集合
  const seen = new Set();
  const list = [];
  const src = (DATA && DATA.allTags) ? DATA.allTags : [];
  for (const t of src){
    const tt = normalizeTrendTag(String(t || "").trim());
    if (!tt) continue;
    if (seen.has(tt)) continue;
    seen.add(tt);
    list.push(tt);
  }
  ALL_TAGS_CACHE = list;
}

/* -------------------------
   Combo dropdowns（可输入 + 固定候选列表）
------------------------- */
const CLEAR_LABEL = "(清空)";
const UNLIMITED_LABEL = "(不限制)";

function closeAllComboPops(except){
  for (const p of document.querySelectorAll(".comboPop.open")){
    if (except && p === except) continue;
    p.classList.remove("open");
  }
}
function toggleComboPop(pop){
  if (!pop) return;
  if (pop.classList.contains("open")){
    pop.classList.remove("open");
  }else{
    closeAllComboPops(pop);
    pop.classList.add("open");
  }
}
function fillComboPop(pop, items, onPick){
  if (!pop) return;
  pop.innerHTML = "";
  const frag = document.createDocumentFragment();

  if (!items || items.length === 0){
    const d = document.createElement("div");
    d.className = "small";
    d.style.padding = "8px 10px";
    d.textContent = "(无候选)";
    frag.appendChild(d);
  }else{
    for (const it of items){
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "comboItem";
      btn.textContent = it;
      btn.addEventListener("click", function(ev){
        ev.preventDefault();
        if (onPick) onPick(it);
        closeAllComboPops();
      });
      frag.appendChild(btn);
    }
  }
  pop.appendChild(frag);
}

function initTrendCombos(){
  if (!DATA) return;
  const items = [CLEAR_LABEL].concat(DATA.allTags || []);

  fillComboPop($("trendLikePop"), items, function(v){
    if (v === CLEAR_LABEL){
      $("trendLikeInput").value = "";
    }else{
      appendTokenToInput($("trendLikeInput"), v);
    }
    $("trendLikeInput").focus();
  });
  fillComboPop($("trendHatePop"), items, function(v){
    if (v === CLEAR_LABEL){
      $("trendHateInput").value = "";
    }else{
      appendTokenToInput($("trendHateInput"), v);
    }
    $("trendHateInput").focus();
  });

  $("trendLikeInput").disabled = false;
  $("trendHateInput").disabled = false;
}



function initExcludedCombo(){
  if (!DATA) return;
  const items = [CLEAR_LABEL].concat(DATA.allTags || []);
  fillComboPop($("excludedTagPop"), items, function(v){
    if (v === CLEAR_LABEL){
      $("excludedTagInput").value = "";
    }else{
      appendTokenToInput($("excludedTagInput"), v);
    }
    $("excludedTagInput").focus();
  });
  $("excludedTagInput").disabled = false;
}


function closeGuestPopover(){
  $("guestPopover").classList.remove("open");
  $("guestBackdrop").classList.remove("open");
  $("guestBtn").setAttribute("aria-expanded","false");
}
function openGuestPopover(){
  // 打开稀客大弹窗前，先收起所有下拉弹层，避免层级互相遮挡
  closeAllComboPops();
  $("guestPopover").classList.add("open");
  $("guestBackdrop").classList.add("open");
  $("guestBtn").setAttribute("aria-expanded","true");
  $("guestSearch").value = "";
  renderGuestGrid("");
  $("guestSearch").focus();
}

function setCurrentGuest(g){
  CURRENT_GUEST = g;
  $("guestNameText").textContent = g ? g.name : "未选择";

  const av = $("guestAvatar");
  av.innerHTML = "";
  const cands = g ? rareIconCandidates(g.name) : [];
  if (cands.length){
    const img = document.createElement("img");
    img.alt = g.name;
    setImgWithCandidates(img, cands, function(){
      av.textContent = (g.name || "客").slice(0, 1);
    });
    av.appendChild(img);
  }else{
    av.textContent = (g?.name || "客").slice(0, 1);
  }

  // guest info
  const fav = (g && g.preferredTags) ? g.preferredTags : [];
  const diss = (g && g.dislikedTags) ? g.dislikedTags : [];
  const budget = (g && !isNaNLike(g.budget) && safeStr(g.budget) !== "") ? safeStr(g.budget) : "(空)";
  $("guestInfo").innerHTML =
    '<div><span class="pill">预算参考（不参与筛选）</span> ' + escapeHTML(budget) + '</div>' +
    '<div style="margin-top:6px"><span class="pill">preferredTags</span> ' + (fav.length ? escapeHTML(fav.join("、")) : "(空)") + '</div>' +
    '<div style="margin-top:6px"><span class="pill">dislikedTags</span> ' + (diss.length ? escapeHTML(diss.join("、")) : "(空)") + '</div>';

  // requiredTag：
  // - 下拉候选：只来自当前稀客 preferredTags（固定列表，不随输入变化）
  // - Tab 补全：来自全 tag 集合（ALL_TAGS_CACHE）
  fillAllTagsDatalist(fav); // 兼容：保留（即使 input 未用 list=... 也无害）

  const favSeen = new Set();
  const preferredTags = (fav || [])
    .map(t => normalizeTrendTag(String(t || '').trim()))
    .filter(Boolean)
    .filter(t => (favSeen.has(t) ? false : (favSeen.add(t), true)))
    .sort((a,b)=>a.localeCompare(b,'zh'));

  fillComboPop($("requiredTagPop"), [UNLIMITED_LABEL].concat(preferredTags), function(v){
    if (v === UNLIMITED_LABEL){
      $("requiredTagInput").value = "";
    }else{
      appendTokenToInput($("requiredTagInput"), v);
    }
    $("requiredTagInput").focus();
  });

  $("requiredTagInput").disabled = false;
  $("requiredTagInput").value = "";

  // 选了稀客后允许开始计算
  $("btnRun").disabled = false;
}

function renderGuestGrid(query){
  const q = (query||"").trim().toLowerCase();
  const grid = $("guestGrid");
  grid.innerHTML = "";
  const list = DATA.guests.filter(g=>{
    if (!q) return true;
    return g.name.toLowerCase().includes(q);
  });

  const frag = document.createDocumentFragment();
  for (const g of list){
    const div = document.createElement("div");
    div.className = "gItem";
    div.tabIndex = 0;

    const av = document.createElement("div");
    av.className = "avatar";
    const cands = rareIconCandidates(g.name);
    if (cands.length){
      const img = document.createElement("img");
      img.alt = g.name;
      setImgWithCandidates(img, cands, function(){
        av.textContent = g.name.slice(0, 1);
      });
      av.appendChild(img);
    }else{
      av.textContent = g.name.slice(0, 1);
    }

    const nm = document.createElement("div");
    nm.className = "gName";
    nm.textContent = g.name;

    div.appendChild(av);
    div.appendChild(nm);

    div.addEventListener("click", function(){
      setCurrentGuest(g);
      closeGuestPopover();
    });

    frag.appendChild(div);
  }
  grid.appendChild(frag);
}

/* -------------------------
   Rendering table + filters/sort
------------------------- */
function escapeHTML(s){
  return String(s||"").replace(/[&<>"']/g, function(m){
    return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m];
  });
}
function escapeAttr(s){
  return escapeHTML(s).replace(/"/g, "&quot;");
}

function renderTable(rows){
  const tb = $("tbody");
  tb.innerHTML = "";
  if (!rows.length){
    tb.innerHTML = '<tr><td colspan="8" class="small" style="padding:16px;color:var(--muted)">无匹配结果。</td></tr>';
    return;
  }
  const frag = document.createDocumentFragment();
  const maxRender = Math.min(rows.length, 5000);
  for (let i=0;i<maxRender;i++){
    const r = rows[i];
    const tr = document.createElement("tr");

    const recipeIcon = iconRecipe(r["料理"]);
    const recipeCell =
      '<div class="cellWithIcon">' +
        (recipeIcon ? '<img src="'+escapeAttr(recipeIcon)+'" alt="" loading="lazy" onerror="this.style.display=\'none\'">' : '') +
        '<div>'+escapeHTML(r["料理"])+'</div>' +
      '</div>';

    tr.innerHTML =
      '<td class="num">'+Number(r["售价"]||0).toFixed(2)+'</td>' +
      '<td class="num">'+r["得分"]+'</td>' +
      '<td>'+recipeCell+'</td>' +
      '<td>'+escapeHTML(r["cookware"]||"")+'</td>' +
      '<td class="num">'+Number(r["总食材数"]||0)+'</td>' +
      '<td class="ellipsisCell" title="'+escapeAttr(r["基础食材"]||"")+'">'+escapeHTML(r["基础食材"]||"")+'</td>' +
      '<td class="ellipsisCell" title="'+escapeAttr(r["加料"]||"")+'">'+escapeHTML(r["加料"]||"")+'</td>' +
      '<td class="tagsCell" title="'+escapeAttr(r["最终tag"]||"")+'">'+escapeHTML(r["最终tag"]||"")+'</td>';

    frag.appendChild(tr);
  }
  tb.appendChild(frag);
}

function updateSortBtnUI(){
  for (const btn of document.querySelectorAll(".sortBtn")){
    const k = btn.getAttribute("data-sort");
    const active = (SORT.key === k);
    btn.classList.toggle("active", active);
    btn.textContent = active ? (SORT.dir === -1 ? "▼" : "▲") : "↕";
  }
}
function updateFilterBtnUI(){
  for (const btn of document.querySelectorAll(".filterBtn")){
    const m = btn.getAttribute("data-filter");
    let active = false;
    if (m === "cookware") active = (FILTERS.cookwareSet.size > 0);
    else if (m === "料理") active = (FILTERS.dishSet.size > 0);
    else if (m === "得分") active = (FILTERS.scoreSet.size > 0);
    else if (m === "总食材数") active = (FILTERS.totalCountSet.size > 0);
    btn.classList.toggle("active", active);
  }
}


function applyFilters(){
  const q = $("searchBox").value.trim().toLowerCase(); // 全局搜索（可搜料理/食材/tag/cookware）
  const dishSet = FILTERS.dishSet;
  const cookwareSet = FILTERS.cookwareSet;
  const scoreSet = FILTERS.scoreSet;
  const totalCountSet = FILTERS.totalCountSet;


  FILTERED = RESULTS.filter(function(r){
    const dish = String(r["料理"]||"");
    const cookware = String(r["cookware"]||"").trim();
    const scoreStr = String(r["得分"]);
    const totalCountStr = String(r["总食材数"]);


    if (dishSet.size > 0 && !dishSet.has(dish)) return false;
    if (cookwareSet.size > 0 && !cookwareSet.has(cookware)) return false;
    if (scoreSet.size > 0 && !scoreSet.has(scoreStr)) return false;
    if (totalCountSet.size > 0 && !totalCountSet.has(totalCountStr)) return false;


    if (!q) return true;
    const blob = [r["料理"], r["cookware"], r["总食材数"], r["基础食材"], r["加料"], r["最终tag"]].join(" ").toLowerCase();
    return blob.includes(q);
  });

  $("resultMeta").textContent =
    (LAST_META || ("共 " + RESULTS.length.toLocaleString() + " 条")) +
    "；当前 " + FILTERED.length.toLocaleString() + " 条" +
    (FILTERED.length > 5000 ? "（页面显示前 5,000 条；可导出全部筛选结果）" : "");

  $("btnCSV").disabled = FILTERED.length === 0;
  $("btnXLSX").disabled = FILTERED.length === 0;
  sortAndRender();
  updateFilterBtnUI();
}

function sortAndRender(){
  const key = SORT.key;
  const dir = SORT.dir;
  FILTERED.sort(function(a,b){
    const va = a[key], vb = b[key];
    if (typeof va === "number" && typeof vb === "number") return (va - vb) * dir;
    return String(va).localeCompare(String(vb), "zh") * dir;
  });
  renderTable(FILTERED);
  updateSortBtnUI();
}

/* -------------------------
   Header popup (cookware/dish)
------------------------- */
let HDR_POP_MODE = null; // "cookware" | "料理"

function positionHdrPop(anchorEl){
  const pop = $("hdrPop");
  const r = anchorEl.getBoundingClientRect();
  const w = 300;
  const left = Math.min(window.innerWidth - w - 10, Math.max(10, r.left));
  const top  = Math.min(window.innerHeight - 260, r.bottom + 6);
  pop.style.left = left + "px";
  pop.style.top  = top + "px";
}

function openHdrPop(mode, anchorEl){
  HDR_POP_MODE = mode;
  const pop = $("hdrPop");
  const title = $("hdrPopTitle");
  const body = $("hdrPopBody");

  let col = "";
  let curSet = null;
  let titleText = "";
  let placeholder = "";

  if (mode === "cookware"){
    col = "cookware";
    curSet = FILTERS.cookwareSet;
    titleText = "筛选 cookware";
    placeholder = "搜索 cookware…";
  }else if (mode === "料理"){
    col = "料理";
    curSet = FILTERS.dishSet;
    titleText = "筛选 料理";
    placeholder = "搜索料理…";
  }else if (mode === "得分"){
    col = "得分";
    curSet = FILTERS.scoreSet;
    titleText = "筛选 得分";
    placeholder = "搜索得分…";
  }else if (mode === "总食材数"){
    col = "总食材数";
    curSet = FILTERS.totalCountSet;
    titleText = "筛选 总食材数";
    placeholder = "搜索总食材数…";
  }else{
    // 未知模式，直接不打开
    return;
  }

  title.textContent = titleText;
  body.innerHTML = "";

  // ⚠️ 关键：下拉候选只来自「当前结果集 RESULTS」，不会从全料理库里拿
  const set = new Set();
  for (const r of (RESULTS || [])){
    if (col === "得分" || col === "总食材数"){
      const v = String(r[col]);
      if (v && v !== "undefined" && v !== "null") set.add(v);
    }else{
      const v = String(r[col] || "").trim();
      if (v) set.add(v);
    }
  }

  const values = Array.from(set);
  if (col === "得分" || col === "总食材数"){
    values.sort((a,b)=>Number(a)-Number(b));
  }else{
    values.sort((a,b)=>a.localeCompare(b,"zh"));
  }

  // 顶部搜索框（不会影响勾选状态）
  const search = document.createElement("input");
  search.type = "text";
  search.placeholder = placeholder;
  search.style.width = "100%";
  search.style.marginBottom = "8px";
  body.appendChild(search);

  const wrap = document.createElement("div");
  wrap.style.maxHeight = "240px";
  wrap.style.overflow = "auto";

  for (const v of values){
    const row = document.createElement("label");
    row.style.display = "flex";
    row.style.gap = "8px";
    row.style.alignItems = "center";
    row.style.margin = "6px 0";
    row.setAttribute("data-name", String(v).toLowerCase());
    row.innerHTML = `<input type="checkbox" data-v="${escapeAttr(v)}"> <span>${escapeHTML(v)}</span>`;
    const cb = row.querySelector("input");
    cb.checked = curSet.has(String(v));
    wrap.appendChild(row);
  }
  body.appendChild(wrap);

  // 搜索过滤（只影响显示，不改变勾选集合）
  search.addEventListener("input", function(){
    const q = search.value.trim().toLowerCase();
    for (const row of wrap.children){
      const name = row.getAttribute("data-name") || "";
      row.style.display = (!q || name.includes(q)) ? "" : "none";
    }
  });
  setTimeout(()=>search.focus(), 0);

  positionHdrPop(anchorEl);
  pop.style.display = "block";
}


function closeHdrPop(){
  $("hdrPop").style.display = "none";
  HDR_POP_MODE = null;
}

/* -------------------------
   Wire UI
------------------------- */
function afterDataLoaded(){
  $("dataState").textContent = "数据已加载";
  $("dataState").style.color = "#111827";

  $("btnRun").disabled = false;
  $("searchBox").disabled = false;

  closeGuestPopover();
  closeAllComboPops();
  closeHdrPop();
  for (const id of ["trendLikeInput", "trendHateInput", "excludedTagInput"]){
    $(id).value = "";
  }
  initTrendCombos();
  initExcludedCombo();
// Tab 自动补全：全 tag
  refreshAllTagsCache();

  computeEqGroupsFromData();
  renderEqGroups();

  setCurrentGuest(DATA.guests[0]);

  setStatus("已加载数据，准备就绪", 0);
}

function resetResults(){
  RESULTS = [];
  FILTERED = [];
  LAST_META = "";
  for (const key of ["dishSet", "cookwareSet", "scoreSet", "totalCountSet"]) FILTERS[key].clear();
  $("searchBox").value = "";
  renderTable([]);
  $("resultMeta").textContent = "等待计算";
  $("btnCSV").disabled = true;
  $("btnXLSX").disabled = true;
  updateFilterBtnUI();
}

function loadBundledData(kind){
  clearWarn();
  const isGame = kind === "game";
  const label = isGame ? "游戏数据" : "合成示例";
  try{
    const bundled = isGame ? window.MYSTIA_GAME_DATA : window.MYSTIA_DEMO_DATA;
    DATA = parseJSONData(bundled);
    resetResults();
    afterDataLoaded();
    $("dataSource").textContent = isGame
      ? "游戏数据：作者工作簿的数据快照，含 " + bundled.sheets["食材"].length + " 条食材记录（参与规划 " + DATA.ingredients.length + " 种）、" + DATA.foods.length + " 条料理记录、" + DATA.guests.length + " 位稀客。来源与范围见下方说明。"
      : "合成示例数据：人物、配方、价格与供给均为虚构，仅用于规则演示与回归案例。";
    $("dataState").textContent = label;
    setStatus(label + "已加载：选择稀客与参数后点击开始计算", 0);
  }catch(err){
    warn(label + "加载失败：" + err.message + " 请手动导入 data/" + (isGame ? "game" : "demo") + ".json 或自己的游戏数据表。");
    setStatus(DATA ? label + "加载失败，保留原有数据" : "加载失败", 0);
  }
}

function loadGame(){ loadBundledData("game"); }
function loadDemo(){ loadBundledData("demo"); }

$("btnLoadGame").addEventListener("click", loadGame);
$("btnLoadDemo").addEventListener("click", loadDemo);
$("fileInput").addEventListener("change", async function(ev){
  clearWarn();
  const f = ev.target.files && ev.target.files[0];
  if (!f) return;
  $("btnRun").disabled = true;
  setImportEnabled(false);
  try{
    setStatus("读取数据...", 0);
    const isJSON = /\.json$/i.test(f.name);
    const parsed = isJSON ? parseJSONData(JSON.parse(await f.text())) : parseExcel(await f.arrayBuffer());
    DATA = parsed;
    resetResults();
    afterDataLoaded();
    $("dataSource").textContent = "当前导入：" + f.name + "（仅在本机浏览器处理）";
  }catch(err){
    warn("加载失败：" + err.message);
    setStatus(DATA ? "导入失败，保留原有数据" : "加载失败", 0);
    $("btnRun").disabled = !DATA;
  }finally{
    setImportEnabled(true);
    ev.target.value = "";
  }
});

// guest picker events
$("guestBtn").addEventListener("click", function(){
  if (!DATA) return;
  const pop = $("guestPopover");
  if (pop.classList.contains("open")) closeGuestPopover();
  else openGuestPopover();
});
$("guestClose").addEventListener("click", closeGuestPopover);
$("guestBackdrop").addEventListener("click", closeGuestPopover);
$("guestSearch").addEventListener("input", function(){
  renderGuestGrid($("guestSearch").value);
});
document.addEventListener("click", function(ev){
  const wrap = document.querySelector(".pickerWrap");
  if (!wrap) return;
  // 只在未打开遮罩时才使用“点外关闭”（有遮罩时靠遮罩点击关闭）
  if (!$("guestPopover").classList.contains("open")) return;
  if (!wrap.contains(ev.target)) closeGuestPopover();
});

// requiredTag: Tab autocomplete (VSCode style)
$("requiredTagInput").addEventListener("keydown", function(ev){
  if (ev.key !== "Tab") return;
  const el = ev.target;
  const v = (el.value || "").trim();
  if (!v) return;
  const hit = ALL_TAGS_CACHE.find(t => t.startsWith(v));
  if (!hit || hit === v) return;

  ev.preventDefault();
  el.value = hit;
  el.setSelectionRange(v.length, hit.length);
});

/* combo dropdown buttons */
$("excludedTagBtn").addEventListener("click", function(ev){
  if ($("excludedTagInput").disabled) return;
  ev.stopPropagation();
  toggleComboPop($("excludedTagPop"));
});
$("requiredTagBtn").addEventListener("click", function(ev){
  if ($("requiredTagInput").disabled) return;
  ev.stopPropagation();
  toggleComboPop($("requiredTagPop"));
});
$("trendLikeBtn").addEventListener("click", function(ev){
  if ($("trendLikeInput").disabled) return;
  ev.stopPropagation();
  toggleComboPop($("trendLikePop"));
});
$("trendHateBtn").addEventListener("click", function(ev){
  if ($("trendHateInput").disabled) return;
  ev.stopPropagation();
  toggleComboPop($("trendHatePop"));
});

// click outside closes combo dropdowns
document.addEventListener("click", function(ev){
  if (!ev.target.closest(".comboWrap")) closeAllComboPops();
});

// Tab autocomplete for trend inputs（全 tag 集合；候选列表不受影响）
function tabAutocompleteFromAllTags(ev){
  if (ev.key !== "Tab") return;
  const el = ev.target;
  const v = (el.value || "").trim();
  if (!v) return;
  const hit = ALL_TAGS_CACHE.find(t => t.startsWith(v));
  if (!hit || hit === v) return;

  ev.preventDefault();
  el.value = hit;
  el.setSelectionRange(v.length, hit.length);
}
$("trendLikeInput").addEventListener("keydown", tabAutocompleteFromAllTags);
$("trendHateInput").addEventListener("keydown", tabAutocompleteFromAllTags);

// global search
$("searchBox").addEventListener("input", applyFilters);

// header sort buttons
document.addEventListener("click", function(ev){
  const sb = ev.target.closest(".sortBtn");
  if (sb){
    const k = sb.getAttribute("data-sort");
    if (SORT.key === k) SORT.dir *= -1;
    else { SORT.key = k; SORT.dir = -1; } // 默认降序
    sortAndRender();
    return;
  }

  const fb = ev.target.closest(".filterBtn");
  if (fb){
    const mode = fb.getAttribute("data-filter"); // "cookware" or "料理"
    openHdrPop(mode, fb);
    ev.stopPropagation();
    return;
  }

  // 点击弹窗外关闭
  const pop = $("hdrPop");
  if (pop.style.display === "block" && !pop.contains(ev.target)) closeHdrPop();
});

$("hdrPopClose").addEventListener("click", closeHdrPop);
$("hdrPopClear").addEventListener("click", function(){
  if (HDR_POP_MODE === "cookware") FILTERS.cookwareSet.clear();
  if (HDR_POP_MODE === "料理") FILTERS.dishSet.clear();
  if (HDR_POP_MODE === "得分") FILTERS.scoreSet.clear();
  closeHdrPop();
  applyFilters();
});
$("hdrPopApply").addEventListener("click", function(){
  if (HDR_POP_MODE === "cookware"){
    const set = new Set();
    for (const cb of $("hdrPopBody").querySelectorAll('input[type="checkbox"][data-v]')){
      if (cb.checked) set.add(cb.getAttribute("data-v"));
    }
    FILTERS.cookwareSet = set;
  }else if (HDR_POP_MODE === "料理"){
    const set = new Set();
    for (const cb of $("hdrPopBody").querySelectorAll('input[type="checkbox"][data-v]')){
      if (cb.checked) set.add(cb.getAttribute("data-v"));
    }
    FILTERS.dishSet = set;
  }else if (HDR_POP_MODE === "得分"){
    const set = new Set();
    for (const cb of $("hdrPopBody").querySelectorAll('input[type="checkbox"][data-v]')){
      if (cb.checked) set.add(cb.getAttribute("data-v"));
    }
    FILTERS.scoreSet = set;
  }
  closeHdrPop();
  applyFilters();
});


  // 左侧：两个过滤功能的“考虑得分”开关联动（主开关关闭时，得分开关强制关闭）
  function syncExtraFilterToggles(){
    const subOn = $("subsetFilter").checked;
    const subScore = $("subsetScoreFilter");
    subScore.disabled = !subOn;
    if (!subOn) subScore.checked = false;

    const ingOn = $("ingUpgradeFilter").checked;
    const ingScore = $("ingUpgradeScoreFilter");
    ingScore.disabled = !ingOn;
    if (!ingOn) ingScore.checked = false;
  }
  $("subsetFilter").addEventListener("change", syncExtraFilterToggles);
  $("ingUpgradeFilter").addEventListener("change", syncExtraFilterToggles);
  syncExtraFilterToggles();

$("btnRun").addEventListener("click", function(){
  clearWarn();
  if (!DATA){ warn("请先载入游戏数据、合成示例或导入 XLSX / JSON 数据"); return; }
  if (!CURRENT_GUEST){ warn("请先选择稀客"); return; }
  const minScore = readMinScore($("scoreMin").value);
  if (minScore === null){ warn("得分阈值请输入 -10 到 10 之间的整数。"); return; }

  RESULTS = [];
  FILTERED = [];
  renderTable([]);
  $("btnCSV").disabled = true;
  $("btnXLSX").disabled = true;



  const guest = {
    ...CURRENT_GUEST,
    preferredTags: normalizeTagList(CURRENT_GUEST.preferredTags),
    dislikedTags: normalizeTagList(CURRENT_GUEST.dislikedTags)
  };
  const requiredTags = parseMultiTagInput($("requiredTagInput").value || "");
  const excludedTags = parseMultiTagInput($("excludedTagInput").value || "");

  const trendLikeAnchors = parseMultiTagInput($("trendLikeInput").value || "");
  const trendHateAnchors = parseMultiTagInput($("trendHateInput").value || "");


const options = {
  minScore: minScore,
  requiredTags: requiredTags,
  excludedTags: excludedTags,
  trendLikeAnchors: trendLikeAnchors,
  trendHateAnchors: trendHateAnchors,

  // 额外过滤开关（左侧四按钮）
  subsetFilter: $("subsetFilter").checked,
  subsetScoreFilter: $("subsetScoreFilter").checked,
  ingUpgradeFilter: $("ingUpgradeFilter").checked,
  ingUpgradeScoreFilter: $("ingUpgradeScoreFilter").checked,
  eqIngDedup: $("eqIngDedup").checked,
  tdqRecommend: $("tdqRecommend").checked,
  tdqTopN: (parseInt((($("tdqTopN").value)||"3").toString().trim(), 10) || 3)
};

setStatus("开始计算...", 0);

  $("btnRun").disabled = true;
  $("btnStop").disabled = false;
  setImportEnabled(false);

  
  // 清理可能残留的 worker
  try{
    if (WORKERS && WORKERS.length){
      for (const w of WORKERS){ try{ w.terminate(); }catch(_e){} }
    }
  }catch(_e){}
  WORKERS = [];

  const foodsAll = DATA.foods || [];
  const totalFoods = foodsAll.length;

  // 并行 worker 数：优先使用硬件线程数（留一个线程给主线程）
  const hc = (navigator.hardwareConcurrency || 4);
  const desired = Math.max(1, Math.min(8, hc - 1, totalFoods || 1));
  const chunkSize = Math.ceil((totalFoods || 1) / desired);

  const chunks = [];
  for (let i=0;i<desired;i++){
    const s = i * chunkSize;
    const e = Math.min(totalFoods, s + chunkSize);
    if (s >= e) break;
    chunks.push({s,e});
  }

  const W = chunks.length;
  const prog = new Array(W).fill(0);
  const parts = new Array(W);
  let doneWorkers = 0;
  let stopped = false;

  const heart = new Array(W).fill(0).map(()=>({
    dish:"",
    combo:0,
    lastT:0,
    lastC:0,
    rate:0,
    phase:"",
    enumN:null,
    advN:null,
    subsetN:null,
    tdqN:null
  }));
  const outCnt = new Array(W).fill(0);
  let outTotal = 0;
  let lastUiT = 0;

  function fmtRate(x){
    if (!isFinite(x) || x<=0) return "0/s";
    if (x>=1e6) return (x/1e6).toFixed(2)+"M/s";
    if (x>=1e3) return (x/1e3).toFixed(1)+"k/s";
    return x.toFixed(0)+"/s";
  }

  function pickActive(){
    let best = 0;
    let bestT = -1;
    for (let i=0;i<W;i++){
      const t = heart[i].lastT || 0;
      if (t > bestT){ bestT = t; best = i; }
    }
    return best;
  }

  function updateStatusLine(doneSum, pct){
    const i = pickActive();
    const h = heart[i] || {};
    const chain = 
      (h.enumN==null? "-" : String(h.enumN)) + "→" +
      (h.advN==null? "-" : String(h.advN)) + "→" +
      (h.subsetN==null? "-" : String(h.subsetN)) + "→" +
      (h.tdqN==null? "-" : String(h.tdqN));

    const comboStr = Number(h.combo||0).toLocaleString();
    const rateStr = fmtRate(h.rate||0);
    const phaseStr = h.phase || "";

    const txt =
      "计算中... (" + doneSum + "/" + totalFoods + ")" +
      " | W" + i +
      " | 料理：" + (h.dish || "") +
      " | 阶段：" + phaseStr +
      " | 枚举：" + comboStr + "（" + rateStr + "）" +
      " | 候选：" + chain +
      " | 输出：W" + i + " " + outCnt[i].toLocaleString() + " / 总 " + outTotal.toLocaleString();

    setStatus(txt, pct);
  }

  const stopAll = function(label){
    if (stopped) return;
    stopped = true;
    RUN_TOKEN++;
    ACTIVE_STOP = null;
    setImportEnabled(true);
    RESULTS = [];
    FILTERED = [];
    LAST_META = "";
    renderTable([]);
    $("resultMeta").textContent = "本次计算未完成";
    $("btnCSV").disabled = true;
    $("btnXLSX").disabled = true;
    setStatus(label || "已停止", 0);
    $("btnRun").disabled = false;
    $("btnStop").disabled = true;
    try{
      for (const w of WORKERS){ try{ w.terminate(); }catch(_e){} }
    }catch(_e){}
    WORKERS = [];
  };

  ACTIVE_STOP = stopAll;

  const finishAll = function(){
    if (stopped) return;
    stopped = true;
    ACTIVE_STOP = null;
    setImportEnabled(true);
    RESULTS = [];
    for (let i=0;i<parts.length;i++){
      if (parts[i] && parts[i].length) RESULTS = RESULTS.concat(parts[i]);
    }
    FILTERED = RESULTS.slice();
    LAST_META = "共 " + RESULTS.length.toLocaleString() + " 条";
    setStatus("完成", 100);

    $("btnRun").disabled = false;
    $("btnStop").disabled = true;
    $("btnCSV").disabled = RESULTS.length===0;
    $("btnXLSX").disabled = RESULTS.length===0;

    if (RESULTS.length > 200000){
      warn("结果条数非常大（>200k），浏览器可能变慢。建议提高得分阈值、增加必含标签，或开启等价食材去重。");
    }

    // 默认排序：售价升序（从小到大）
    SORT = {key:"售价", dir:1};
    updateSortBtnUI();

    applyFilters();

    try{
      for (const w of WORKERS){ try{ w.terminate(); }catch(_e){} }
    }catch(_e){}
    WORKERS = [];
  };

  const runToken = ++RUN_TOKEN;

  for (let wid=0; wid<W; wid++){
    const c = chunks[wid];
    const foods = foodsAll.slice(c.s, c.e);

    let w;
    try{
      w = makeWorker();
    }catch(err){
      warn("无法启动计算线程：" + err.message);
      stopAll("计算启动失败");
      break;
    }
    WORKERS.push(w);

    w.onerror = function(e){
      if (runToken !== RUN_TOKEN || stopped) return;
      warn("计算线程出错：" + (e && e.message ? e.message : String(e)));
      stopAll("计算失败");
    };

    w.onmessage = function(ev){
      if (runToken !== RUN_TOKEN || stopped) return; // 过期消息
      const msg = ev.data || {};
      if (msg.type === "STOPPED"){
        stopAll("已停止");
        return;
      }
      if (msg.type === "ROWS"){
        const id = Number(msg.wid);
        if (Number.isFinite(id) && id>=0 && id<parts.length){
          if (!parts[id]) parts[id] = [];
          const rows = msg.rows || [];
          if (rows.length){
            parts[id].push.apply(parts[id], rows);
            outCnt[id] += rows.length;
            outTotal += rows.length;
          }
        }
        const now = performance.now();
        if (now - lastUiT > 200){
          lastUiT = now;
          const doneSum = prog.reduce((a,b)=>a+b,0);
          const pct = totalFoods ? Math.floor(doneSum*100/totalFoods) : 0;
          updateStatusLine(doneSum, pct);
        }
        return;
      }
      if (msg.type === "HEART"){
        const id = Number(msg.wid);
        if (Number.isFinite(id) && id>=0 && id<heart.length){
          const h = heart[id];
          const now = performance.now();
          const combo = Number(msg.combo)||0;
          if (h.lastT){
            const dt = (now - h.lastT)/1000;
            const dc = combo - (h.lastC||0);
            if (dt > 0 && dc >= 0) h.rate = dc/dt;
          }
          h.lastT = now;
          h.lastC = combo;
          h.combo = combo;
          h.dish = msg.dish || h.dish;
          if (!h.phase) h.phase = "枚举中";
        }
        const doneSum = prog.reduce((a,b)=>a+b,0);
        const pct = totalFoods ? Math.floor(doneSum*100/totalFoods) : 0;
        updateStatusLine(doneSum, pct);
        return;
      }
      if (msg.type === "PHASE"){
        const id = Number(msg.wid);
        if (Number.isFinite(id) && id>=0 && id<heart.length){
          const h = heart[id];
          h.dish = msg.dish || h.dish;
          const ph = msg.phase || "";
          const n = Number(msg.n);
          if (ph === "enum"){ h.enumN = n; h.phase = "枚举完成"; }
          else if (ph === "adv"){ h.advN = n; h.phase = "高级过滤"; }
          else if (ph === "subset"){ h.subsetN = n; h.phase = "子集过滤"; }
          else if (ph === "tdq"){ h.tdqN = n; h.phase = "TDQ/输出"; }
          else { h.phase = ph; }
          h.lastT = performance.now();
        }
        const doneSum = prog.reduce((a,b)=>a+b,0);
        const pct = totalFoods ? Math.floor(doneSum*100/totalFoods) : 0;
        updateStatusLine(doneSum, pct);
        return;
      }
      if (msg.type === "PROGRESS"){
        const id = Number(msg.wid);
        if (Number.isFinite(id) && id>=0 && id<prog.length){
          prog[id] = Number(msg.done) || 0;
        }
        const doneSum = prog.reduce((a,b)=>a+b,0);
        const pct = totalFoods ? Math.floor(doneSum*100/totalFoods) : 0;
        updateStatusLine(doneSum, pct);
        return;
      }
      if (msg.type === "DONE"){
        doneWorkers++;
        if (doneWorkers >= W){
          finishAll();
        }
        return;
      }
    };


    w.postMessage({
      type:"RUN",
      payload:{
        wid: wid,
        foods: foods,
        ingredients: DATA.ingredients,
        tdqRawMap: DATA.tdqRawMap,
        guest: guest,
        options: options
      }
    });
  }
});

$("btnStop").addEventListener("click", function(){
  // A synchronous Worker cannot receive STOP during enumeration; terminate it here.
  stopCalculation();
});

$("btnCSV").addEventListener("click", exportCSV);
$("btnXLSX").addEventListener("click", exportXLSX);
/* =========================
   Worker + Export (补齐缺失函数)
========================= */

function downloadBlob(blob, filename){
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(()=>URL.revokeObjectURL(url), 1000);
}

function getExportRows(){
  const limit = Number($("exportLimit").value) || 0;
  const base = FILTERED;
  return (limit > 0) ? base.slice(0, limit) : base.slice();
}

function exportCSV(){
  if (!RESULTS || RESULTS.length === 0) return;
  const rows = getExportRows();
  const cols = ["售价","得分","料理","cookware","总食材数","基础食材","加料","最终tag"];
  const esc = (v)=>{
    const s = String(v ?? "");
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
  };
  let out = cols.join(",") + "\r\n";
  for (const r of rows){
    out += cols.map(c=>esc(r[c])).join(",") + "\r\n";
  }
  const blob = new Blob(["\ufeff" + out], {type:"text/csv;charset=utf-8"});
  downloadBlob(blob, `结果_${Date.now()}.csv`);
}

function exportXLSX(){
  if (!RESULTS || RESULTS.length === 0) return;
  const rows = getExportRows();
  const header = ["售价","得分","料理","cookware","总食材数","基础食材","加料","最终tag"];
  const ws = XLSX.utils.json_to_sheet(rows, {header});
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "结果");
  XLSX.writeFile(wb, `结果_${Date.now()}.xlsx`);
}

function makeWorker(){
  if (!WORKER_URL){
    const workerSrc = `
let STOP = false;

function safeStr(x){ return (x===null||x===undefined) ? "" : String(x).trim(); }
function normName(s){ return safeStr(s).replace(/\u3000/g," ").trim(); }

function normalizeTrendTag(t){
  if (!t) return t;
  if (t === "流行喜爱" || t === "流行 喜爱") return "流行·喜爱";
  if (t === "流行厌恶" || t === "流行 厌恶") return "流行·厌恶";
  return t;
}
function normTag(t){ return normalizeTrendTag(normName(t)); }

function tagsSignature(tags){
  // 归一化为「排序去重后的 tag 串」，用于等价食材分组（tag 完全相同）
  if (!tags || !tags.length) return "";
  const seen = Object.create(null);
  const arr = [];
  for (let i=0;i<tags.length;i++){
    const t = normTag(tags[i]);
    if (!t) continue;
    if (seen[t]) continue;
    seen[t] = 1;
    arr.push(t);
  }
  arr.sort((a,b)=>a.localeCompare(b,"zh"));
  return arr.join("|");
}

function dedupEquivalentIngredients(list){
  // 同一 signature（tag 完全相同）的食材只保留一个
  const seen = new Set();
  const out = [];
  for (let i=0;i<list.length;i++){
    const ing = list[i];
    const sig = tagsSignature(ing && ing.tags ? ing.tags : []);
    if (seen.has(sig)) continue;
    seen.add(sig);
    out.push(ing);
  }
  return out;
}


function applyOverrides(tagSet){
  if (tagSet.has("肉")) tagSet.delete("素");
  if (tagSet.has("饱腹")) tagSet.delete("下酒");
  if (tagSet.has("重油")) tagSet.delete("清淡");
  if (tagSet.has("大份")) tagSet.delete("小巧");
}

function formatAdded(names){
  if (!names || names.length===0) return "";
  const m = Object.create(null);
  for (const n of names){
    const k = normName(n);
    m[k] = (m[k]||0) + 1;
  }
  const parts = [];
  for (const k of Object.keys(m)){
    parts.push(m[k] > 1 ? (k + "×" + m[k]) : k);
  }
  return parts.join("、");
}

function buildRow(c){
  const tagArr = Array.from(c.tagSet).filter(Boolean).sort((a,b)=>a.localeCompare(b,"zh"));
  const finalTags = tagArr.join("、");
  const addArr = (c.addedNamesOut || c.addedNames || []);
  return {
    "售价": c.price,
    "得分": c.score,
    "料理": c.dishName || "",
    "cookware": c.cookware || "",
    "总食材数": c.totalIng,
    "基础食材": c.baseJoined || "",
    "加料": formatAdded(addArr),
    "最终tag": finalTags
  };
}

// 组合（可重复，非降序索引）生成：n 选 k（可重复）
function genCombRep(n, k, start, comb, cb){
  if (k === 0) return cb(comb) !== false;
  for (let i=start;i<n;i++){
    comb.push(i);
    const ok = genCombRep(n, k-1, i, comb, cb);
    comb.pop();
    if (ok === false) return false;
    if (STOP) return false;
  }
  return true;
}

/* -------------------------
   Multi-set helpers
------------------------- */
function countMultiset(arr){
  const m = Object.create(null);
  for (const x of (arr||[])){
    const k = normName(x);
    if (!k) continue;
    m[k] = (m[k]||0) + 1;
  }
  return m;
}
function countsKey(m){
  const keys = Object.keys(m).filter(k=>m[k]>0).sort((a,b)=>a.localeCompare(b,"zh"));
  let out = "";
  for (const k of keys){
    out += k + "×" + m[k] + "|";
  }
  return out; // 空串表示空加料
}
function isSubsetCounts(a, b){
  // a ⊆ b (按计数)
  for (const k of Object.keys(a)){
    const ca = a[k]|0;
    if (ca<=0) continue;
    const cb = b[k]|0;
    if (cb < ca) return false;
  }
  return true;
}

/* -------------------------
   Ingredient "upgrade" relation by tag-set inclusion
   (A tags ⊂ B tags) => B is "高级" (advanced), A is base.
------------------------- */
function buildIngTagSets(ingredients){
  const map = Object.create(null); // name -> sorted unique tags
  for (const ing of ingredients){
    const nm = normName(ing.name);
    if (!nm) continue;
    const tags = (ing.tags||[]).map(normTag).filter(Boolean);
    const seen = new Set();
    const uniq = [];
    for (const t of tags){
      if (!seen.has(t)){ seen.add(t); uniq.push(t); }
    }
    uniq.sort((a,b)=>a.localeCompare(b,"zh"));
    map[nm] = uniq;
  }
  return map;
}

function buildTagIndex(ingTagSets, ingredients){
  // 全局 tag -> index（用于 bitset 加速子集判定）
  const idx = Object.create(null);
  let n = 0;
  for (const nm of ingredients){
    const tags = ingTagSets[nm] || [];
    for (const t of tags){
      if (idx[t] === undefined){
        idx[t] = n++;
      }
    }
  }
  return { idx, wordCount: Math.ceil(n / 32) };
}

function buildIngMasks(ingTagSets, ingredients, tagIndex, wordCount){
  const masks = Object.create(null);
  const lens  = Object.create(null);
  for (const nm of ingredients){
    const tags = ingTagSets[nm] || [];
    lens[nm] = tags.length;
    const m = new Uint32Array(wordCount);
    for (const t of tags){
      const k = tagIndex[t];
      if (k === undefined) continue;
      m[k >>> 5] |= (1 << (k & 31));
    }
    masks[nm] = m;
  }
  return { masks, lens };
}

function isStrictSubsetMask(aMask, aLen, bMask, bLen){
  // a ⊂ b（真子集）。同时：不让空 tag（aLen==0）成为 base，避免无 tag 食材“支配”全部。
  if (!aMask || !bMask) return false;
  if (aLen === 0) return false;
  if (aLen >= bLen) return false;
  for (let i=0;i<aMask.length;i++){
    if ((aMask[i] & bMask[i]) !== aMask[i]) return false;
  }
  return true;
}

function isStrictSubsetTags(aTags, bTags){
  // aTags ⊂ bTags, both arrays sorted unique
  if (!aTags || !bTags) return false;
  if (aTags.length >= bTags.length) return false;
  let i=0, j=0;
  while (i<aTags.length && j<bTags.length){
    const a = aTags[i], b = bTags[j];
    const cmp = a.localeCompare(b,"zh");
    if (cmp===0){ i++; j++; }
    else if (cmp>0){ j++; }
    else { return false; }
  }
  return i===aTags.length;
}

onmessage = function(ev){
  const msg = ev.data || {};
  if (msg.type === "STOP"){
    STOP = true;
    return;
  }
  if (msg.type !== "RUN") return;

  STOP = false;
  const payload = msg.payload || {};
  const foods = payload.foods || [];
  let ingredients = payload.ingredients || [];
  const guest = payload.guest || {preferredTags:[], dislikedTags:[]};
  const opt = payload.options || {};
  const wid = Number(payload.wid)||0;

  const minScore = Number(opt.minScore) || 0;
  const requiredTags = Array.isArray(opt.requiredTags) ? opt.requiredTags.map(normTag).filter(Boolean) : [];
  const excludedTags = Array.isArray(opt.excludedTags) ? opt.excludedTags.map(normTag).filter(Boolean) : [];
  const trendLikeAnchors = Array.isArray(opt.trendLikeAnchors) ? opt.trendLikeAnchors.map(normTag).filter(Boolean) : [];
  const trendHateAnchors = Array.isArray(opt.trendHateAnchors) ? opt.trendHateAnchors.map(normTag).filter(Boolean) : [];


  const subsetFilter = !!opt.subsetFilter;
  const subsetScoreFilter = subsetFilter && !!opt.subsetScoreFilter;

  const ingUpgradeFilter = !!opt.ingUpgradeFilter;
  const ingUpgradeScoreFilter = ingUpgradeFilter && !!opt.ingUpgradeScoreFilter;
  const eqIngDedup = !!opt.eqIngDedup;
  const tdqRecommend = !!opt.tdqRecommend;
  let tdqTopN = tdqRecommend ? (Number(opt.tdqTopN) || 3) : 0;
  tdqTopN = Math.max(1, Math.min(999, Math.floor(tdqTopN || 3)));

  const favSet = new Set((guest.preferredTags||[]).map(normTag).filter(Boolean));
  const dissSet = new Set((guest.dislikedTags||[]).map(normTag).filter(Boolean));
  const ingTagMap = Object.create(null);
  const allIngNames = [];
  for (const ing of ingredients){
    const nm = normName(ing.name);
    if (!nm) continue;
    // 一开始就排除“铃仙”（仅影响“加料”候选）
    if (nm === "铃仙") continue;
    allIngNames.push(nm);
    const tags = (ing.tags||[]).map(normTag).filter(Boolean);
    ingTagMap[nm] = tags;
  }

  const ingTagSets = buildIngTagSets(ingredients);

  // ✅ 预计算：每个食材的 tag bitset（用于“食材高级过滤”高速判定子集）
  let ingMaskMap = null;
  let ingLenMap  = null;
  if (ingUpgradeFilter){
    const tagIndexObj = buildTagIndex(ingTagSets, allIngNames);
    const TAG_INDEX = tagIndexObj.idx;
    const TAG_WORDS = tagIndexObj.wordCount;
    const maskLenObj = buildIngMasks(ingTagSets, allIngNames, TAG_INDEX, TAG_WORDS);
    ingMaskMap = maskLenObj.masks;
    ingLenMap  = maskLenObj.lens;
  }

  // 等价食材去重（仅影响“加料”候选）：按“加料食材 tags 签名”去重
  // 注意：无 tag 的食材不视为等价（避免把一堆“无tag食材”压成一个）
  // 你指定的“等价组代表食材”（仅用于加料去重）：若等价组里包含这些食材，则优先保留它作为代表
  const PREFERRED_EQ_REPS = ["猪肉","鳟鱼","三文鱼","河豚","极上金枪鱼","海苔","豆腐","桃子","白果"];
  const PREF_RANK = Object.create(null);
  for (let i=0;i<PREFERRED_EQ_REPS.length;i++) PREF_RANK[PREFERRED_EQ_REPS[i]] = i;

  const ingSigKeyMap = Object.create(null);
  for (const nm of allIngNames){
    const arr = ingTagSets[nm] || [];
    // 无 tag：不视为等价（用“__EMPTY__:+名字”保证每个无tag食材都唯一）
    ingSigKeyMap[nm] = (arr && arr.length) ? arr.join("\u0001") : ("__EMPTY__:" + nm);
  }

  function pickBetterName(a, b){
    if (!a) return b;
    if (!b) return a;
    const ra = (a in PREF_RANK) ? PREF_RANK[a] : 1000000000;
    const rb = (b in PREF_RANK) ? PREF_RANK[b] : 1000000000;
    if (ra !== rb) return (ra < rb) ? a : b;
    return (a.localeCompare(b, "zh") <= 0) ? a : b;
  }

// TDQ（Total Daily Quantity）
// - tdqEff：等价组内（按加料 tags 签名）取平均 TDQ
// - tdqMaxNameBySig：等价组内“真实 TDQ”最大的食材名（仅用于依采购推荐时对加料做替换）
const tdqRawMap = payload.tdqRawMap || {};
const groupSizeBySig = Object.create(null);
const tdqSumBySig = Object.create(null);
const tdqCntBySig = Object.create(null);
const tdqMaxNameBySig = Object.create(null);
const tdqMaxValBySig = Object.create(null);

for (const nm of allIngNames){
  const key = ingSigKeyMap[nm] || ("__EMPTY__:" + nm);
  groupSizeBySig[key] = (groupSizeBySig[key]||0) + 1;

  const v = Number(tdqRawMap[nm]);
  if (Number.isFinite(v)){
    tdqSumBySig[key] = (tdqSumBySig[key]||0) + v;
    tdqCntBySig[key] = (tdqCntBySig[key]||0) + 1;

    const prev = tdqMaxValBySig[key];
    if (prev === undefined || v > prev){
      tdqMaxValBySig[key] = v;
      tdqMaxNameBySig[key] = nm;
    }else if (v === prev){
      // 同 TDQ 并列：用“代表食材优先 + 中文排序”做稳定选择
      tdqMaxNameBySig[key] = pickBetterName(tdqMaxNameBySig[key], nm);
    }
  }
}

function tdqEff(nm){
  const key = ingSigKeyMap[nm] || ("__EMPTY__:" + nm);
  const cnt = tdqCntBySig[key] || 0;
  if (cnt > 0) return (tdqSumBySig[key]||0) / cnt;
  const v = Number(tdqRawMap[nm]);
  return Number.isFinite(v) ? v : 0;
}

function addedSigByTags(addedNames){
  // 仅用于“等价去重（仅加料）”：用加料的 tags 签名（多重集）作为方案签名
  if (!addedNames || !addedNames.length) return "";
  const sigs = [];
  for (const nm of addedNames){
    sigs.push(ingSigKeyMap[nm] || ("__EMPTY__:" + nm));
  }
  sigs.sort();
  return sigs.join("\u0002");
}

  function dedupAllowedBySig(names){
    // 同签名只保留一个：优先“代表食材”，否则按中文排序最小
    const bestByKey = Object.create(null);
    const order = [];
    for (const nm of names){
      const key = ingSigKeyMap[nm] || ("__EMPTY__:" + nm);
      if (!(key in bestByKey)){
        bestByKey[key] = nm;
        order.push(key);
      }else{
        bestByKey[key] = pickBetterName(bestByKey[key], nm);
      }
    }
    const out = [];
    const seen = new Set();
    for (const key of order){
      const nm = bestByKey[key];
      if (seen.has(nm)) continue;
      seen.add(nm);
      out.push(nm);
    }
    return out;
  }

  const CHUNK_SIZE = 2000;
  let OUT_CHUNK = [];
  let outCount = 0;

  function emitRow(row){
    OUT_CHUNK.push(row);
    outCount++;
    if (OUT_CHUNK.length >= CHUNK_SIZE){
      postMessage({type:"ROWS", wid, rows: OUT_CHUNK});
      OUT_CHUNK = [];
    }
  }
  function flushRows(){
    if (OUT_CHUNK.length){
      postMessage({type:"ROWS", wid, rows: OUT_CHUNK});
      OUT_CHUNK = [];
    }
  }

  const total = foods.length;
  let done = 0;

  for (const f of foods){
    if (STOP){
      postMessage({type:"STOPPED", wid: wid});
      return;
    }

    const dishName = normName(f.name||"");
    if (dishName === "黑暗物质" || dishName.toLowerCase() === "dark matter") continue;

    const baseNames = (f.requiredIngredients||[]).map(normName).filter(Boolean);
    const baseCount = baseNames.length;
    const maxExtra = Math.max(0, 5 - baseCount);
    // 仅当 requiredTag 为“大份”且料理本身不含“大份”tag 时，才强制只枚举 k=maxExtra（凑满5个食材）
let dishHasBig = false;
for (const t of (f.tags||[])){
  if (normTag(t) === "大份"){ dishHasBig = true; break; }
}
const kStart = (requiredTags.includes("大份") && !dishHasBig) ? maxExtra : 0;

    const invalidEntries = (f.forbiddenIngredients||[]).map(normName).filter(Boolean);
    const invalidNames = new Set(invalidEntries.filter(n => n in ingTagMap));
    const invalidTags = new Set(invalidEntries.filter(n => !(n in ingTagMap)).map(normTag));
    let allowedIngNamesRaw = allIngNames.filter(n =>
      !invalidNames.has(n) && !(ingTagMap[n] || []).some(tag => invalidTags.has(tag))
    );

    // Choose the TDQ replacement from this dish's legal candidates only.
    const legalTdqRepresentative = Object.create(null);
    for (const nm of allowedIngNamesRaw){
      const key = ingSigKeyMap[nm];
      const previous = legalTdqRepresentative[key];
      const value = Number(tdqRawMap[nm]);
      const previousValue = Number(tdqRawMap[previous]);
      const currentTDQ = Number.isFinite(value) ? value : 0;
      const bestTDQ = Number.isFinite(previousValue) ? previousValue : 0;
      if (!previous || currentTDQ > bestTDQ ||
          (currentTDQ === bestTDQ && pickBetterName(previous, nm) === nm)){
        legalTdqRepresentative[key] = nm;
      }
    }

// 用于“依采购推荐”的 TopN 阈值：在开启“等价食材去重（仅加料）”时，需要保留“去重前”的等价组数量信息，
// 使 TopN 的阈值不因去重而下沉到更差的档位（例如肉类去重后，第三名变成八目鳗）。
const allowedSigCount = Object.create(null);
for (const nm of allowedIngNamesRaw){
  const key = ingSigKeyMap[nm] || ("__EMPTY__:" + nm);
  allowedSigCount[key] = (allowedSigCount[key] || 0) + 1;
}

let allowedIngNames = allowedIngNamesRaw;
// 等价食材仅在“加料”阶段视为等价：先按 forbiddenIngredients 过滤，再按 tags 签名去重
if (eqIngDedup) allowedIngNames = dedupAllowedBySig(allowedIngNamesRaw);

    // baseRep for allowed ingredients
    let baseRep = null;
    if (ingUpgradeFilter){
      baseRep = Object.create(null);

      // ✅ 高性能：用 bitset 判定“真子集”，并按「tag 数量最少」选 base
      // 同时：不让“无 tag 食材”成为 base，避免把所有有 tag 的食材都当成“高级”。
      const candList = allowedIngNames.slice().sort(function(a,b){
        const da = ingLenMap[a] || 0;
        const db = ingLenMap[b] || 0;
        if (da !== db) return da - db;
        return a.localeCompare(b,"zh");
      });

      for (const cur of allowedIngNames){
        const curLen = ingLenMap[cur] || 0;
        const curMask = ingMaskMap[cur];
        let best = cur;

        for (const cand of candList){
          const candLen = ingLenMap[cand] || 0;
          if (candLen === 0) continue;   // 不用“无 tag”做 base
          if (candLen >= curLen) break;  // candList 已按 tag 数升序
          if (cand === cur) continue;

          if (isStrictSubsetMask(ingMaskMap[cand], candLen, curMask, curLen)){
            best = cand;
            break;
          }
        }
        baseRep[cur] = best;
      }
    }

    const addedBefore = outCount;

    const dishCands = [];
    const baseJoined = baseNames.join("、");
    let comboN = 0;

    for (let k=kStart;k<=maxExtra;k++){
      genCombRep(allowedIngNames.length, k, 0, [], function(indices){
        if (STOP) return false;

        comboN++;
        if ((comboN & 131071) === 0){
          postMessage({type:"HEART", wid, dish:(f.name||""), combo: comboN, done, total});
        }

        const addedNames = indices.map(i => allowedIngNames[i]);
        const totalIng = baseCount + k;

        const tagSet = new Set();

        for (const t of (f.tags||[])) {
          const tt = normTag(t);
          if (tt) tagSet.add(tt);
        }

        const ck = normTag(f.cookware||"");
        if (ck) tagSet.add(ck);

        const price = Number(f.sellPrice)||0;
        if (price > 0 && price < 20) tagSet.add("实惠");
        else if (price > 60) tagSet.add("昂贵");

        for (const nm of addedNames){
          const tags = ingTagMap[nm] || [];
          for (const t of tags) tagSet.add(t);
        }

        if (baseCount < 5 && totalIng === 5 && k > 0) tagSet.add("大份");

        applyOverrides(tagSet);
        let hitTrendLike = false;
        for (const a of trendLikeAnchors){
          if (tagSet.has(a)){ hitTrendLike = true; break; }
        }
        if (hitTrendLike) tagSet.add("流行·喜爱");

        let hitTrendHate = false;
        for (const a of trendHateAnchors){
          if (tagSet.has(a)){ hitTrendHate = true; break; }
        }
        if (hitTrendHate) tagSet.add("流行·厌恶");

        for (const rt of requiredTags){
          if (!tagSet.has(rt)) return true;
        }
        for (const et of excludedTags){
          if (tagSet.has(et)) return true;
        }


        let score = 0;
        for (const t of tagSet){
          if (favSet.has(t)) score += 1;
          if (dissSet.has(t)) score -= 1;
        }
        if (score < minScore) return true;

        const origCounts = countMultiset(addedNames);
        const origKey = countsKey(origCounts);

        let normKey = origKey;
        let advanced = false;
        if (ingUpgradeFilter && addedNames.length){
          const normCounts = Object.create(null);
          for (const nm of addedNames){
            const baseNm = baseRep && baseRep[nm] ? baseRep[nm] : nm;
            normCounts[baseNm] = (normCounts[baseNm]||0) + 1;
          }
          normKey = countsKey(normCounts);
          advanced = (normKey !== origKey);
        }

// multiplicity：当开启“等价食材去重（仅加料）”时，一个加料代表可能对应多个同 tags 食材；
// 为了让“依采购推荐”的 TopN 与未去重时一致（阈值不下沉），用 allowedSigCount 计算该方案代表的“原始方案数”。
let mult = 1;
if (tdqRecommend && eqIngDedup && addedNames.length){
  const signatureCounts = Object.create(null);
  for (const nm of addedNames){
    const key = ingSigKeyMap[nm] || ("__EMPTY__:" + nm);
    signatureCounts[key] = (signatureCounts[key] || 0) + 1;
  }
  // Repeated picks from a group are unordered: C(group size + picks - 1, picks).
  for (const key of Object.keys(signatureCounts)){
    const picks = signatureCounts[key];
    const count = allowedSigCount[key] || 1;
    let ways = 1;
    for (let i = 1; i <= picks; i++) ways = ways * (count + i - 1) / i;
    mult *= Math.round(ways);
  }
}

dishCands.push({
          totalAdded: k,
          score: score,
          addedNames: addedNames,
          counts: origCounts,
          origKey: origKey,
          normKey: normKey,
          advanced: advanced,
          mult: mult,
          price: price,
          totalIng: totalIng,
          baseJoined: baseJoined,
          dishName: f.name || "",
          cookware: f.cookware || "",
          tagSet: tagSet
        });

        return true;
      });

      if (STOP){
        postMessage({type:"STOPPED", wid: wid});
        return;
      }
    }

    // 1) 食材高级过滤
    let cands1 = dishCands;
    if (ingUpgradeFilter){
      if (!ingUpgradeScoreFilter){
        // 仅当同一道菜的候选里存在对应 baseKey（normKey）方案时，才过滤 advanced；否则保留
        const hasBase = Object.create(null);
        for (const c of cands1){
          if (!c.advanced) hasBase[c.origKey] = true;
        }
        cands1 = cands1.filter(c => (!c.advanced) || (!hasBase[c.normKey]));
      }else{
        const baseBest = Object.create(null);
        for (const c of cands1){
          if (!c.advanced){
            const k = c.origKey;
            const prev = baseBest[k];
            if (prev === undefined || c.score > prev) baseBest[k] = c.score;
          }
        }
        cands1 = cands1.filter(c=>{
          if (!c.advanced) return true;
          const best = baseBest[c.normKey];
          return !(best !== undefined && best >= c.score);
        });
      }
    }

    postMessage({type:"PHASE", wid, done, total, dish:(f.name||""), phase:"adv", n:cands1.length});

    // 2) 加料子集过滤
    let cands2 = cands1;
    if (subsetFilter){
      cands2 = cands2.slice().sort((a,b)=>{
        if (a.totalAdded !== b.totalAdded) return a.totalAdded - b.totalAdded;
        if (a.score !== b.score) return b.score - a.score;
        return a.origKey.localeCompare(b.origKey, "zh");
      });

      const bestScoreByKey = Object.create(null);
      const kept = [];

      function isDominatedBySubset(counts, score){
        const keys = Object.keys(counts).filter(k => (counts[k]|0) > 0).sort((a,b)=>a.localeCompare(b,"zh"));
        if (!keys.length){
          const s = bestScoreByKey[""];
          return (s !== undefined) && (!subsetScoreFilter || s >= score);
        }
        const parts = new Array(keys.length).fill(0);
        let dominated = false;
        function rec(i){
          if (dominated) return;
          if (i === keys.length){
            let out = "";
            for (let j=0;j<keys.length;j++){
              const c = parts[j];
              if (c > 0) out += keys[j] + "×" + c + "|";
            }
            const s = bestScoreByKey[out];
            if (s !== undefined && (!subsetScoreFilter || s >= score)) dominated = true;
            return;
          }
          const maxC = counts[keys[i]]|0;
          for (let c=0;c<=maxC;c++){
            parts[i] = c;
            rec(i+1);
            if (dominated) return;
          }
        }
        rec(0);
        return dominated;
      }

      for (const c of cands2){
        if (isDominatedBySubset(c.counts, c.score)) continue;
        kept.push(c);
        const k = c.origKey;
        const prev = bestScoreByKey[k];
        if (prev === undefined || c.score > prev) bestScoreByKey[k] = c.score;
      }
      cands2 = kept;
    }

    postMessage({type:"PHASE", wid, done, total, dish:(f.name||""), phase:"subset", n:cands2.length});

if (!tdqRecommend){
  postMessage({type:"PHASE", wid, done, total, dish:(f.name||""), phase:"tdq", n:cands2.length});
  for (const c of cands2){
    emitRow(buildRow(c));
  }
}else{
  if (cands2.length){
    // 依采购推荐：为每个方案构建 tdqVec（方案【基础食材+加料】所有食材的 tdqEff，升序）
// 比较规则：从最小开始逐位比较，谁在第一个不同处更大谁胜；若一方先结束，则视为空位=+∞，更短者胜
const EPS_TDQ = 1e-9;

function tdqVecOfCandidate(c){
  const vals = [];
  for (const nm of baseNames){
    vals.push(tdqEff(nm));
  }
  const addArr = c.addedNames || [];
  for (const nm of addArr){
    vals.push(tdqEff(nm));
  }
  vals.sort((x,y)=>x-y);
  return vals;
}

function eqTdqVec(a, b){
  if (a.length !== b.length) return false;
  for (let i=0;i<a.length;i++){
    if (Math.abs(a[i] - b[i]) > EPS_TDQ) return false;
  }
  return true;
}

function cmpTdqVec(a, b){
  const A = a.tdqVec, B = b.tdqVec;
  const n = Math.max(A.length, B.length);
  for (let i=0;i<n;i++){
    const va = (i < A.length) ? A[i] : Infinity;
    const vb = (i < B.length) ? B[i] : Infinity;
    if (Math.abs(va - vb) <= EPS_TDQ) continue;
    return (va > vb) ? -1 : 1; // 越大越好
  }
  return 0;
}

for (const c of cands2){
  c.tdqVec = tdqVecOfCandidate(c);
}

let sorted = cands2.slice().sort((a,b)=>{
  const d = cmpTdqVec(a,b);
  if (d) return d;
  // 完全相同：稳定排序
  if (a.totalAdded !== b.totalAdded) return a.totalAdded - b.totalAdded;
  return a.origKey.localeCompare(b.origKey, "zh");
});

const TOP_N = tdqTopN;

// 取“第 TOP_N 名”的 tdqVec 作为阈值，保留所有不差于阈值的方案（并列自然全保留）
// 注意：这里的 TOP_N 指“方案个数”（不是“不同 tdqVec 组数”），对应你原先“>= 第三名”的逻辑。
// 取 TopN 的阈值：
// - 未开启“等价食材去重”时：直接取第 TOP_N 名（方案个数）作为阈值
// - 开启“等价食材去重”时：用每个方案的 mult（代表的原始方案数）做“加权排名”，避免阈值因去重而下沉到更差档位
let thrVec;
if (!eqIngDedup){
  const thrIdx = Math.min(TOP_N - 1, sorted.length - 1);
  thrVec = sorted[thrIdx].tdqVec;
}else{
  let acc = 0;
  thrVec = sorted[sorted.length - 1].tdqVec;
  for (const c of sorted){
    acc += (c.mult || 1);
    if (acc >= TOP_N){
      thrVec = c.tdqVec;
      break;
    }
  }
}
const thrObj = { tdqVec: thrVec };
let keep = sorted.filter(c => cmpTdqVec(c, thrObj) <= 0);


    
// 替换：仅当开启“等价食材去重（仅加料）”时，才对“加料”中属于等价组的食材，换成该等价组真实 TDQ 最大的食材
postMessage({type:"PHASE", wid, done, total, dish:(f.name||""), phase:"tdq", n:keep.length});
for (const c of keep){
  if (eqIngDedup){
    const addArr = c.addedNames || [];
    if (addArr.length){
      const newAdded = addArr.map(function(nm){
        const key = ingSigKeyMap[nm] || ("__EMPTY__:" + nm);
        if ((groupSizeBySig[key]||0) < 2) return nm; // 非等价组：不动
        const rep = legalTdqRepresentative[key];
        return rep || nm;
      });
      c.addedNamesOut = newAdded;
    }
  }
  emitRow(buildRow(c));
}
  }
}

    done++;
    postMessage({type:"PROGRESS", wid, done, total, added: outCount - addedBefore});
  }

  flushRows();

  postMessage({type:"DONE", wid, outCount});
};
  `.trim();
    const blob = new Blob([workerSrc], {type:"text/javascript"});
    WORKER_URL = URL.createObjectURL(blob);
  }
  return new Worker(WORKER_URL);
}
loadGame();
