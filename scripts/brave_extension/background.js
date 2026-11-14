// Nova Agent para Brave - Service Worker (MV3) · v4.0 (09/11/2026, Claude, a pedido de Luaz)
// Mantiene el WebSocket con el puente local de Nova y enruta los comandos.
// Las acciones de navegador (pestañas, capturas) se resuelven aqui; las de pagina van al content script.
// v4: CLICK, TYPE, PRESS_KEY, HOVER, CLICK_AT y UPLOAD_FILE usan RATON Y TECLADO REALES (chrome.debugger -> CDP Input.*),
//     como si fuera Alexander: las webs no los distinguen de una persona, llegan a iframes y permiten subir archivos.
//     Brave muestra la barra "esta depurando este navegador" solo mientras Nova actua (se suelta a los 8 s).
//     args.real === false -> modo simulado de la v3 (por si una web va mejor asi).
// Pagos: bloqueados salvo PASE DE PAGO de un solo uso (10 min) que solo llega desde el puente (/pase_pago con la
//     clave secreta que solo tiene el hook de Alexander). Campos de contraseña y de tarjeta: bloqueo fijo.

const WS_URL = "ws://127.0.0.1:5005/ws";
const VERSION = chrome.runtime.getManifest().version;
const TAB_MSG_TIMEOUT_MS = 20000;
const LOAD_TIMEOUT_MS = 15000;

let ws = null;
let pingTimer = null;
let reconnectTimer = null;

// Peticiones de la extension AL puente (p. ej. "trae Brave delante"): el puente responde con type respuesta_puente.
const pendientesPuente = new Map();
function pedirAlPuente(msg, timeoutMs = 3000) {
  return new Promise((resolve) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return resolve({ ok: false });
    const ref = "p" + Math.random().toString(36).slice(2, 10);
    pendientesPuente.set(ref, resolve);
    setTimeout(() => { if (pendientesPuente.delete(ref)) resolve({ ok: false, error: "timeout" }); }, timeoutMs);
    ws.send(JSON.stringify({ ...msg, ref }));
  });
}

// ---------------------------------------------------------------------------
// Conexion con el puente
// ---------------------------------------------------------------------------
function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

  let sock;
  try {
    sock = new WebSocket(WS_URL);
  } catch (e) {
    scheduleReconnect();
    return;
  }
  ws = sock;

  sock.onopen = () => {
    console.log("[Nova] Conectado al puente en 127.0.0.1:5005");
    sock.send(JSON.stringify({ type: "hello", client: "nova-brave-extension", version: VERSION }));
    startKeepAlive(sock);
  };

  sock.onmessage = async (event) => {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    if (!msg || msg.type === "pong" || msg.type === "welcome") return;
    if (msg.type === "respuesta_puente" && pendientesPuente.has(msg.ref)) {
      pendientesPuente.get(msg.ref)(msg);
      pendientesPuente.delete(msg.ref);
      return;
    }
    if (!msg.id || !msg.action) return;

    const response = await handleCommand(msg);
    if (sock.readyState === WebSocket.OPEN) {
      sock.send(JSON.stringify({ id: msg.id, ...response }));
    }
  };

  sock.onclose = () => {
    if (ws === sock) {
      ws = null;
      stopKeepAlive();
    }
    scheduleReconnect();
  };

  sock.onerror = () => {
    try { sock.close(); } catch {}
  };
}

// Ping cada 20 s: en Chromium 116+ el trafico WebSocket mantiene vivo el service worker.
function startKeepAlive(sock) {
  stopKeepAlive();
  pingTimer = setInterval(() => {
    if (sock.readyState === WebSocket.OPEN) {
      sock.send(JSON.stringify({ type: "ping", timestamp: Date.now() }));
    } else {
      stopKeepAlive();
    }
  }, 20000);
}

function stopKeepAlive() {
  if (pingTimer) clearInterval(pingTimer);
  pingTimer = null;
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, 3000);
}

// Si Nova arranca despues que Brave, el service worker puede estar dormido y los setTimeout
// mueren con el. La alarma (cada 30 s) lo despierta y reintenta la conexion.
chrome.alarms.get("nova-reconnect", (alarm) => {
  if (!alarm) chrome.alarms.create("nova-reconnect", { periodInMinutes: 0.5 });
});
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "nova-reconnect") connect();
});
chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
// Los content scripts avisan al cargar una pagina: otra forma de despertar al worker.
chrome.runtime.onMessage.addListener((req) => {
  if (req && req.type === "nova-wake") connect();
});

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------
function isWebUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

// Paginas donde Chromium no permite scripts de extensiones.
function isRestrictedUrl(url) {
  if (!url || !isWebUrl(url)) return true;
  const host = new URL(url).hostname;
  return host === "chromewebstore.google.com" || (host === "chrome.google.com" && url.includes("/webstore"));
}

function normalizeUrl(raw) {
  if (typeof raw !== "string" || !raw.trim()) return null;
  let url = raw.trim();
  if (!/^[a-z][a-z0-9+.-]*:/i.test(url)) url = "https://" + url;
  return isWebUrl(url) ? url : null;
}

function simpleTab(t) {
  return { tabId: t.id, windowId: t.windowId, title: t.title, url: t.url, active: t.active, audible: !!t.audible, status: t.status };
}

// v4: tras navegar, primero hay que ver que la pestaña EMPIEZA a cargar (antes devolvia "complete" de la pagina
// anterior y Nova actuaba sobre la vieja). Si en 3 s no empieza (p. ej. cambio solo de #ancla), se da por hecha.
function waitForNavigation(tabId, timeoutMs = LOAD_TIMEOUT_MS) {
  return new Promise((resolve) => {
    let done = false, empezo = false;
    const finish = (status) => {
      if (done) return;
      done = true;
      chrome.tabs.onUpdated.removeListener(listener);
      clearTimeout(timer);
      clearTimeout(arranque);
      resolve(status);
    };
    const listener = (id, info) => {
      if (id !== tabId) return;
      if (info.status === "loading") empezo = true;
      else if (info.status === "complete" && empezo) finish("complete");
    };
    const timer = setTimeout(() => finish("timeout"), timeoutMs);
    const arranque = setTimeout(() => { if (!empezo) finish("sin_recarga"); }, 3000);
    chrome.tabs.onUpdated.addListener(listener);
  });
}

function waitForLoad(tabId, timeoutMs = LOAD_TIMEOUT_MS) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (status) => {
      if (done) return;
      done = true;
      chrome.tabs.onUpdated.removeListener(listener);
      clearTimeout(timer);
      resolve(status);
    };
    const listener = (id, info) => {
      if (id === tabId && info.status === "complete") finish("complete");
    };
    const timer = setTimeout(() => finish("timeout"), timeoutMs);
    chrome.tabs.onUpdated.addListener(listener);
    chrome.tabs.get(tabId).then((t) => { if (t.status === "complete") finish("complete"); }).catch(() => finish("closed"));
  });
}

async function getTargetTab(action, args) {
  if (args.tabId !== undefined) {
    return chrome.tabs.get(Number(args.tabId));
  }
  const preferHost = action === "YOUTUBE_CONTROL" ? "*://*.youtube.com/*" : action === "WHATSAPP" ? "*://web.whatsapp.com/*" : null;
  if (preferHost) {
    const tabs = await chrome.tabs.query({ url: preferHost });
    if (tabs.length) return tabs.find((t) => t.active) || tabs[0];
  }
  let [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (!tab) [tab] = await chrome.tabs.query({ active: true });
  return tab;
}

function sendToTab(tabId, msg) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => resolve({ ok: false, error: "Timeout esperando al content script" }), TAB_MSG_TIMEOUT_MS);
    chrome.tabs.sendMessage(tabId, msg, (response) => {
      clearTimeout(timer);
      if (chrome.runtime.lastError) resolve({ ok: false, error: chrome.runtime.lastError.message });
      else resolve(response || { ok: false, error: "Sin respuesta del content script" });
    });
  });
}

// ---------------------------------------------------------------------------
// v4 · Pase de pago (un solo uso, lo concede Alexander via hook -> puente)
// ---------------------------------------------------------------------------
let pase = null; // { hasta: ms, motivo }
function paseActivo() {
  if (pase && Date.now() < pase.hasta) return true;
  pase = null;
  return false;
}
function gastarPase(detalle) {
  console.log("[Nova] Pase de pago USADO:", detalle);
  pase = null;
}

// ---------------------------------------------------------------------------
// v4 · Raton y teclado reales (chrome.debugger -> Chrome DevTools Protocol)
// ---------------------------------------------------------------------------
const DBG = { tabId: null, timer: null, soltarMs: 8000 };

async function dbgAttach(tabId) {
  if (DBG.tabId === tabId) { programarSoltar(); return; }
  if (DBG.tabId !== null) await dbgDetach();
  try {
    await chrome.debugger.attach({ tabId }, "1.3");
  } catch (e) {
    if (!/already attached/i.test(String(e && e.message))) throw e;
  }
  DBG.tabId = tabId;
  programarSoltar();
}
function programarSoltar() {
  clearTimeout(DBG.timer);
  DBG.timer = setTimeout(dbgDetach, DBG.soltarMs);
}
async function dbgDetach() {
  clearTimeout(DBG.timer);
  const t = DBG.tabId;
  DBG.tabId = null;
  if (t !== null) { try { await chrome.debugger.detach({ tabId: t }); } catch {} }
}
chrome.debugger.onDetach.addListener((src) => { if (src.tabId === DBG.tabId) DBG.tabId = null; });
// Si Brave solto el depurador (el usuario pulso "Cancelar" en la barra, la pagina se recargo...), se reengancha y reintenta.
async function cdp(tabId, method, params = {}) {
  try {
    return await chrome.debugger.sendCommand({ tabId }, method, params);
  } catch (e) {
    if (!/not attached|Detached/i.test(String(e && e.message))) throw e;
    DBG.tabId = null;
    await dbgAttach(tabId);
    return chrome.debugger.sendCommand({ tabId }, method, params);
  }
}
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

// Las acciones reales van de una en una (dos a la vez se pisaban el depurador: "Detached while handling command").
let colaReal = Promise.resolve();
function enCola(fn) {
  const p = colaReal.then(fn, fn);
  colaReal = p.catch(() => {});
  return p;
}

// El raton/teclado real solo llega a la pestaña VISIBLE (Brave no procesa input en pestañas de fondo y antes
// devolvia ok sin hacer nada). Se pone delante; con args.activar === false se usa el modo simulado.
// Ademas de ser la pestaña activa, la ventana tiene que VERSE: si otra ventana la tapa entera o esta minimizada,
// Windows/Brave marcan la pagina como oculta (visibilityState "hidden"), la pausan y TIRAN el input real
// (la bateria del 09/11 lo cazo: el clic devolvia ok y la pagina no recibia nada). Entonces se trae Brave delante.
async function visibilidad(tabId) {
  try {
    const [r] = await chrome.scripting.executeScript({ target: { tabId }, func: () => document.visibilityState });
    return r ? r.result : "desconocida";
  } catch {
    return "desconocida";
  }
}

async function asegurarVisible(tab, args) {
  if (!tab.active) {
    if (args.activar === false) return false;
    await chrome.tabs.update(tab.id, { active: true });
    await esperar(250);
  }
  let v = await visibilidad(tab.id);
  if (v === "hidden") {
    if (args.activar === false) return false;
    const w = await chrome.windows.get(tab.windowId);
    await chrome.windows.update(tab.windowId, w.state === "minimized" ? { state: "normal", focused: true } : { focused: true });
    for (let i = 0; i < 6 && v === "hidden"; i++) {
      await esperar(150);
      v = await visibilidad(tab.id);
    }
    if (v === "hidden") {
      // Windows no deja que Brave se ponga delante solo: se lo pido al puente (programa local), que si puede.
      const t = await chrome.tabs.get(tab.id);
      await pedirAlPuente({ type: "traer_delante", titulo: t.title || "" });
      for (let i = 0; i < 10 && v === "hidden"; i++) {
        await esperar(150);
        v = await visibilidad(tab.id);
      }
    }
    if (v === "hidden") throw new Error("Brave esta tapado o minimizado y no pude traerlo delante");
  }
  return true;
}

async function ratonClic(tabId, x, y, veces = 1) {
  await dbgAttach(tabId);
  await cdp(tabId, "Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none" });
  for (let i = 1; i <= veces; i++) {
    await cdp(tabId, "Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", buttons: 1, clickCount: i });
    await cdp(tabId, "Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", buttons: 0, clickCount: i });
  }
}

const TECLAS = {
  Enter: [13, "Enter", "\r"], Tab: [9, "Tab"], Escape: [27, "Escape"], Backspace: [8, "Backspace"], Delete: [46, "Delete"],
  Space: [32, "Space", " "], ArrowUp: [38, "ArrowUp"], ArrowDown: [40, "ArrowDown"], ArrowLeft: [37, "ArrowLeft"],
  ArrowRight: [39, "ArrowRight"], PageUp: [33, "PageUp"], PageDown: [34, "PageDown"], Home: [36, "Home"], End: [35, "End"],
  F5: [116, "F5"], F11: [122, "F11"]
};
async function teclaReal(tabId, key, mods = {}) {
  await dbgAttach(tabId);
  let [vk, code, text] = TECLAS[key] || (key.length === 1
    ? [key.toUpperCase().charCodeAt(0), /[a-z]/i.test(key) ? "Key" + key.toUpperCase() : /[0-9]/.test(key) ? "Digit" + key : "", key]
    : [0, key]);
  const m = (mods.alt ? 1 : 0) | (mods.ctrl ? 2 : 0) | (mods.meta ? 4 : 0) | (mods.shift ? 8 : 0);
  if (m & 7) text = undefined; // atajos (Ctrl+A, Alt+...): sin texto
  const k = key === "Space" ? " " : key;
  await cdp(tabId, "Input.dispatchKeyEvent", { type: text ? "keyDown" : "rawKeyDown", key: k, code, windowsVirtualKeyCode: vk,
    nativeVirtualKeyCode: vk, modifiers: m, text, unmodifiedText: text });
  await cdp(tabId, "Input.dispatchKeyEvent", { type: "keyUp", key: k, code, windowsVirtualKeyCode: vk, nativeVirtualKeyCode: vk, modifiers: m });
}

async function escribirReal(tabId, texto) {
  await dbgAttach(tabId);
  await cdp(tabId, "Input.insertText", { text: texto });
}

// Pide al content script donde esta el objetivo (y si esta bloqueado). Con pase de pago activo reintenta permitido.
async function localizar(tab, accion, args) {
  let r = await enviarPagina(tab, { action: accion, args });
  if (r && !r.ok && r.code === "HUMAN_REQUIRED" && r.kind === "payment" && paseActivo()) {
    r = await enviarPagina(tab, { action: accion, args: { ...args, _permitirPago: true } });
    if (r && r.ok) r.data.conPase = true;
  }
  return r;
}

async function enviarPagina(tab, forward) {
  let res = await sendToTab(tab.id, forward);
  if (!res.ok && /Receiving end does not exist|Could not establish connection/i.test(res.error || "")) {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["content.js"] });
    res = await sendToTab(tab.id, forward);
  }
  return res;
}

const ACCIONES_REALES = new Set(["CLICK", "TYPE", "PRESS_KEY", "HOVER", "CLICK_AT", "UPLOAD_FILE"]);

async function accionReal(action, args, tab) {
  // Subir a un <input type=file> no usa raton: no hace falta que Brave se vea (se comprueba mas abajo si hace falta clic)
  if (action !== "UPLOAD_FILE" && !(await asegurarVisible(tab, args))) return null; // activar:false -> simulado
  const fin = async (data) => {
    await esperar(Number(args.waitMs) || 300);
    let url = tab.url;
    try { url = (await chrome.tabs.get(tab.id)).url; } catch {}
    return { ok: true, data: { ...data, url, modo: "real", tabId: tab.id } };
  };
  const usarPase = (loc, que) => { if (loc.data && loc.data.conPase && loc.data.buy) gastarPase(`${que}: ${loc.data.name || ""}`); };

  if (action === "CLICK_AT") {
    const x = Number(args.x), y = Number(args.y);
    const loc = await localizar(tab, "POINT_CHECK", { x, y });
    if (!loc.ok) return loc;
    await ratonClic(tab.id, x, y, Number(args.clicks) || 1);
    usarPase(loc, "clic por coordenadas");
    return fin({ status: "clicked", x, y, sobre: loc.data.name, iframe: loc.data.iframe });
  }

  if (action === "PRESS_KEY") {
    const key = args.key || "Enter";
    // Enter y Espacio activan el boton enfocado: se revisan igual que un clic (Tab hasta "Pagar" + Espacio = bloqueado)
    if (key === "Enter" || key === "Space" || key === " ") {
      const loc = await localizar(tab, "LOCATE", { ...args, purpose: "enter" });
      if (!loc.ok) return loc;
      if (args.ref !== undefined || args.selector || args.text) await ratonClic(tab.id, loc.data.x, loc.data.y);
      await teclaReal(tab.id, key === " " ? "Space" : key);
      usarPase(loc, key);
    } else {
      await teclaReal(tab.id, key, { ctrl: !!args.ctrl, shift: !!args.shift, alt: !!args.alt, meta: !!args.meta });
    }
    return fin({ status: "key_pressed", key });
  }

  const proposito = action === "TYPE" ? "type" : action === "UPLOAD_FILE" ? "upload" : action === "HOVER" ? "hover" : "click";
  const loc = await localizar(tab, "LOCATE", { ...args, purpose: proposito });
  if (!loc.ok) return loc;
  const { x, y, hidden } = loc.data;

  if (action === "HOVER") {
    await dbgAttach(tab.id);
    await cdp(tab.id, "Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "none" });
    return fin({ status: "hovered", name: loc.data.name });
  }

  if (action === "CLICK") {
    if (hidden) return null; // invisible: que lo haga el modo simulado
    await ratonClic(tab.id, x, y, Number(args.clicks) || 1);
    usarPase(loc, "clic");
    return fin({ status: "clicked", name: loc.data.name });
  }

  if (action === "TYPE") {
    if (loc.data.select || hidden) return null; // <select> y campos invisibles: modo simulado
    const texto = args.text !== undefined ? String(args.text) : "";
    await ratonClic(tab.id, x, y);
    if (args.clear !== false) {
      await teclaReal(tab.id, "a", { ctrl: true });
      await teclaReal(tab.id, "Backspace");
    } else {
      await teclaReal(tab.id, "End", { ctrl: true }); // añadir al FINAL, no donde cayo el clic
    }
    if (texto) await escribirReal(tab.id, texto);
    if (args.enter) {
      const locE = await localizar(tab, "LOCATE", { ...args, purpose: "enter" });
      if (!locE.ok) return locE;
      await teclaReal(tab.id, "Enter");
      usarPase(locE, "Enter tras escribir");
    }
    return fin({ status: "typed", chars: texto.length, enterPressed: !!args.enter });
  }

  if (action === "UPLOAD_FILE") {
    const files = (Array.isArray(args.files) ? args.files : [args.file || args.path]).filter(Boolean).map(String);
    if (!files.length) return { ok: false, error: "Falta args.files (rutas completas de los archivos a subir)" };
    await dbgAttach(tab.id);
    if (loc.data.fileInput) {
      const { root } = await cdp(tab.id, "DOM.getDocument", { depth: 0 });
      const { nodeId } = await cdp(tab.id, "DOM.querySelector", { nodeId: root.nodeId, selector: `[data-nova-up="${loc.data.uploadId}"]` });
      if (!nodeId) return { ok: false, error: "No encontre el campo de archivo (¿esta dentro de un shadow DOM?)" };
      await cdp(tab.id, "DOM.setFileInputFiles", { nodeId, files });
      return fin({ status: "uploaded", files: files.length });
    }
    // Boton que abre el selector de archivos: intercepto el dialogo y le doy los archivos directamente.
    if (!(await asegurarVisible(tab, args))) return { ok: false, error: "Para pulsar ese boton Brave tiene que verse (activar:false lo impide)" };
    const abierto = new Promise((resolve) => {
      const oyente = (src, method, params) => {
        if (src.tabId === tab.id && method === "Page.fileChooserOpened") {
          chrome.debugger.onEvent.removeListener(oyente);
          resolve(params);
        }
      };
      chrome.debugger.onEvent.addListener(oyente);
      setTimeout(() => { chrome.debugger.onEvent.removeListener(oyente); resolve(null); }, 6000);
    });
    await cdp(tab.id, "Page.enable");
    await cdp(tab.id, "Page.setInterceptFileChooserDialog", { enabled: true });
    try {
      await ratonClic(tab.id, x, y);
      const p = await abierto;
      if (!p || !p.backendNodeId) return { ok: false, error: "Ese boton no abrio un selector de archivos en 6 s" };
      await cdp(tab.id, "DOM.setFileInputFiles", { backendNodeId: p.backendNodeId, files });
    } finally {
      try { await cdp(tab.id, "Page.setInterceptFileChooserDialog", { enabled: false }); } catch {}
    }
    return fin({ status: "uploaded", files: files.length });
  }
  return null;
}

// ---------------------------------------------------------------------------
// Enrutador de comandos
// ---------------------------------------------------------------------------
async function handleCommand(msg) {
  const action = String(msg.action).toUpperCase();
  // Blindaje: _permitirPago solo lo pone ESTE service worker cuando hay pase. Si viene de fuera (Nova), se borra.
  const args = { ...(msg.args && typeof msg.args === "object" ? msg.args : {}) };
  delete args._permitirPago;
  try {
    switch (action) {
      case "PING_EXTENSION":
        return { ok: true, data: { version: VERSION, raton_real: true, depurando: DBG.tabId,
          pase_pago: paseActivo() ? Math.round((pase.hasta - Date.now()) / 1000) + " s" : "no" } };

      // Solo llega desde el puente (/pase_pago con la clave del hook): /execute la rechaza.
      case "GRANT_PAYMENT_PASS": {
        const min = Math.min(Math.max(Number(args.minutes) || 10, 1), 30);
        pase = { hasta: Date.now() + min * 60000, motivo: String(args.motivo || "").slice(0, 200) };
        console.log("[Nova] Pase de pago concedido por Alexander:", min, "min ·", pase.motivo);
        return { ok: true, data: { pase: `activo ${min} min, un solo pago` } };
      }

      case "REVOKE_PAYMENT_PASS":
        pase = null;
        return { ok: true, data: { pase: "retirado" } };

      case "LIST_TABS": {
        const tabs = await chrome.tabs.query({});
        return { ok: true, data: { tabs: tabs.map(simpleTab) } };
      }

      case "NEW_TAB": {
        const url = args.url ? normalizeUrl(args.url) : null;
        if (args.url && !url) return { ok: false, error: "URL no valida: solo se permiten http/https" };
        const tab = await chrome.tabs.create({ url: url || undefined, active: args.active !== false });
        const status = url && args.wait !== false ? await waitForLoad(tab.id) : "skipped";
        return { ok: true, data: { ...simpleTab(await chrome.tabs.get(tab.id)), load: status } };
      }

      case "NAVIGATE_TAB": {
        const url = normalizeUrl(args.url);
        if (!url) return { ok: false, error: "URL no valida: solo se permiten http/https" };
        const tab = await getTargetTab(action, args);
        if (!tab) return { ok: false, error: "No hay pestaña disponible para navegar" };
        const nav = args.wait !== false ? waitForNavigation(tab.id) : null;
        await chrome.tabs.update(tab.id, { url });
        const status = nav ? await nav : "skipped";
        return { ok: true, data: { ...simpleTab(await chrome.tabs.get(tab.id)), load: status } };
      }

      case "SWITCH_TAB": {
        if (args.tabId === undefined) return { ok: false, error: "Falta args.tabId (usa LIST_TABS)" };
        const tab = await chrome.tabs.update(Number(args.tabId), { active: true });
        await chrome.windows.update(tab.windowId, { focused: true });
        return { ok: true, data: simpleTab(tab) };
      }

      case "CLOSE_TAB": {
        if (args.tabId === undefined) return { ok: false, error: "Falta args.tabId (usa LIST_TABS)" };
        await chrome.tabs.remove(Number(args.tabId));
        return { ok: true, data: { closed: Number(args.tabId) } };
      }

      case "GO_BACK":
      case "GO_FORWARD":
      case "RELOAD_TAB": {
        const tab = await getTargetTab(action, args);
        if (!tab) return { ok: false, error: "No hay pestaña activa" };
        const nav = waitForNavigation(tab.id);
        if (action === "GO_BACK") await chrome.tabs.goBack(tab.id);
        else if (action === "GO_FORWARD") await chrome.tabs.goForward(tab.id);
        else await chrome.tabs.reload(tab.id);
        const status = await nav;
        return { ok: true, data: { ...simpleTab(await chrome.tabs.get(tab.id)), load: status } };
      }

      case "SCREENSHOT": {
        const tab = await getTargetTab(action, args);
        if (!tab) return { ok: false, error: "No hay pestaña activa" };
        if (!tab.active) return { ok: false, error: "La pestaña no esta visible. Usa SWITCH_TAB antes de capturar." };
        const quality = Math.min(Math.max(Number(args.quality) || 60, 20), 90);
        const image = await chrome.tabs.captureVisibleTab(tab.windowId, { format: "jpeg", quality });
        return { ok: true, data: { image, title: tab.title, url: tab.url } };
      }

      case "WAIT": {
        const ms = Math.min(Math.max(Number(args.ms) || 1000, 0), 10000);
        await new Promise((r) => setTimeout(r, ms));
        return { ok: true, data: { waited: ms } };
      }

      case "RELOAD_EXTENSION":
        setTimeout(() => chrome.runtime.reload(), 200);
        return { ok: true, data: { status: "reloading" } };
    }

    // Acciones sobre la pagina: van al content script.
    const tab = await getTargetTab(action, args);
    if (!tab || !tab.id) return { ok: false, error: "No se encontro ninguna pestaña para esta accion" };
    if (isRestrictedUrl(tab.url)) {
      return { ok: false, error: `No se pueden ejecutar scripts en esta pagina (${tab.url}). Solo paginas http/https.` };
    }

    // v4: raton y teclado reales (si falla el debugger o el elemento es invisible, sigue en modo simulado)
    let notaReal;
    if (ACCIONES_REALES.has(action) && args.real !== false) {
      try {
        const real = await enCola(() => accionReal(action, args, tab));
        if (real) return real;
      } catch (e) {
        notaReal = `raton real no disponible (${e && e.message ? e.message : e}); hecho en modo simulado`;
      }
    }
    if (action === "CLICK_AT" || action === "UPLOAD_FILE") {
      return { ok: false, error: notaReal || `${action} necesita el raton real (chrome.debugger)` };
    }

    // Modo simulado (v3). Con pase de pago activo, el content script lo respeta igual que en modo real.
    let args2 = args;
    let res = await enviarPagina(tab, { action, args: args2 });
    if (res && !res.ok && res.code === "HUMAN_REQUIRED" && res.kind === "payment" && paseActivo()) {
      args2 = { ...args, _permitirPago: true };
      res = await enviarPagina(tab, { action, args: args2 });
      if (res && res.ok && res.data && res.data.pagoUsado) gastarPase(`${action} (simulado)`);
    }
    if (res && res.data && typeof res.data === "object") {
      res.data.tabId = tab.id;
      if (notaReal) res.data.nota = notaReal;
    }
    return res;
  } catch (err) {
    return { ok: false, error: err && err.message ? err.message : String(err) };
  }
}

connect();
