// Nova Agent para Brave - Content Script (v4.0, 09/11/2026)
// Modelo PULL: no envia nada por su cuenta, solo responde a comandos.
// Reglas fijas (no configurables desde Nova): no escribe en campos de contraseña ni de tarjeta.
// Botones de compra/pago y paginas de checkout: bloqueados SALVO que el service worker mande _permitirPago,
// que solo existe si Alexander dio un permiso de pago de un solo uso (hook -> puente /pase_pago -> extension).
// v4: LOCATE devuelve donde esta el elemento para que el service worker haga un clic/tecleo REAL (chrome.debugger).

(function () {
  // Registro de referencias en memoria (no se marca el DOM: la pagina no puede ver ni falsificar refs).
  let refs = new Map(); // ref -> WeakRef<Element>
  let nextRef = 1;

  // -------------------------------------------------------------------------
  // Barreras de seguridad
  // -------------------------------------------------------------------------
  // Tokens largos: en cualquier parte (creditCard, cardnumber...). Tokens cortos: solo como palabra suelta.
  const PAYMENT_FIELD_RE = /(cc-|ccnum|card|tarjeta|cvv|cvc|security.?code|codigo.?de.?seguridad|expir|caducidad|vencimiento|iban|routing|account.?number|numero.?de.?cuenta|sort.?code|(^|[^a-z])(csc|cid|bic|swift)([^a-z]|$))/i;
  const BUY_LABEL_RE = /\b(buy now|buy it now|place (your )?order|complete (your )?(purchase|order)|confirm (purchase|order|payment|and pay)|pay now|pay with|proceed to (checkout|payment)|checkout|subscribe and pay|add payment|comprar( ya| ahora)?|pagar|realizar (el )?pedido|tramitar (el )?pedido|finalizar (la )?(compra|pedido)|confirmar (la )?(compra|pedido|pago)|proceder al pago|ir a pagar|ir a caja|suscribirse y pagar|anadir (metodo|tarjeta)|agregar (metodo|tarjeta))\b/i;
  const PAYMENT_URL_RE = /(\/checkout|\/payment|\/payments|\/pago|\/pagos|\/billing|\/order[-_/]?review|\/finalizar|\/buy\/|paypal\.com|pay\.google\.com|checkout\.stripe\.com|\.stripe\.com\/pay|js\.stripe\.com|mercadopago\.|mercadolibre\.com\/checkout|niubiz|culqi|izipay|payu\.|adyen\.com|braintree|apple\.com\/shop\/checkout|yape\.com\.pe|plin)/i;

  function norm(s) {
    return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  // kind "payment": se puede desbloquear con el permiso de un solo uso de Alexander. Sin kind: bloqueo fijo.
  function humanRequired(reason, kind) {
    const extra = kind === "payment" ? " Si Alexander quiere que lo hagas tu, tiene que decirte 'autorizo el pago' (vale para un solo pago)." : "";
    return { ok: false, code: "HUMAN_REQUIRED", kind: kind || "fixed", error: `Bloqueado: ${reason}. Esta accion debe hacerla Alexander manualmente.${extra}` };
  }

  function isPaymentPage() {
    return PAYMENT_URL_RE.test(location.href);
  }

  // iframe de pasarela (Stripe, PayPal, Niubiz...) o elemento dentro de uno
  function esMarcoPago(el) {
    const f = el && el.closest ? el.closest("iframe, frame") : null;
    return !!(f && PAYMENT_URL_RE.test(f.src || f.getAttribute("src") || ""));
  }

  // Devuelve "password", "payment" o null.
  function sensitiveKind(el) {
    if (!el || !el.tagName) return null;
    if (el.tagName === "INPUT" && (el.type || "").toLowerCase() === "password") return "password";
    const ac = (el.getAttribute("autocomplete") || "").toLowerCase();
    if (ac.startsWith("cc-") || ac.includes(" cc-")) return "payment";
    if (ac.includes("current-password") || ac.includes("new-password")) return "password";
    const hints = norm([el.name, el.id, el.getAttribute("placeholder"), el.getAttribute("aria-label"), labelFor(el)].join(" "));
    if (PAYMENT_FIELD_RE.test(hints)) return "payment";
    return null;
  }

  const CONTROLES = "button, a, [role=button], [role=link], [role=menuitem], input[type=submit], input[type=button], input[type=image], summary";

  function isBuyControl(el) {
    if (!el || !el.closest) return false;
    const control = el.closest(CONTROLES);
    const target = control || el;
    // Un contenedor grande (body, una seccion...) no es "un boton de pagar" aunque dentro ponga "Pagar"
    if (!control && (target.innerText || "").length > 80) return false;
    const text = norm(accessibleName(target) || target.value || "");
    if (BUY_LABEL_RE.test(text)) return true;
    const form = target.form || target.closest("form");
    if (form && form.action && PAYMENT_URL_RE.test(form.action) && (target.type === "submit" || target.tagName === "BUTTON")) return true;
    return false;
  }

  // -------------------------------------------------------------------------
  // Mensajeria
  // -------------------------------------------------------------------------
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (!request || !request.action) return false;
    handle(request.action, request.args || {})
      .then(sendResponse)
      .catch((err) => sendResponse({ ok: false, error: err && err.message ? err.message : String(err) }));
    return true; // respuesta asincrona
  });

  // Despierta al service worker por si estaba dormido sin conexion.
  try { chrome.runtime.sendMessage({ type: "nova-wake" }).catch(() => {}); } catch {}

  async function handle(action, args) {
    switch (action) {
      case "LOCATE": return locate(args);
      case "POINT_CHECK": return pointCheck(args);
      case "SNAPSHOT": return { ok: true, data: snapshot(args) };
      case "FIND": return find(args);
      case "GET_TEXT": return getText(args);
      case "GET_SELECTION": return { ok: true, data: { selection: String(window.getSelection() || "") } };
      case "CLICK": return click(args);
      case "HOVER": return hover(args);
      case "TYPE": return type(args);
      case "PRESS_KEY": return pressKey(args);
      case "SCROLL": return scroll(args);
      case "YOUTUBE_CONTROL": return youtube(args);
      case "WHATSAPP": return whatsapp(args);
      default: return { ok: false, error: `Accion desconocida: ${action}` };
    }
  }

  // -------------------------------------------------------------------------
  // Lectura de la pagina
  // -------------------------------------------------------------------------
  const INTERACTIVE_SEL = [
    "a[href]", "button", "input:not([type=hidden])", "select", "textarea", "summary",
    "[contenteditable='']", "[contenteditable='true']",
    "[role=button]", "[role=link]", "[role=checkbox]", "[role=radio]", "[role=switch]", "[role=tab]",
    "[role=menuitem]", "[role=option]", "[role=textbox]", "[role=combobox]", "[role=searchbox]", "[role=slider]",
    "h1", "h2", "h3"
  ].join(",");

  // querySelectorAll que tambien entra en shadow DOM abiertos.
  function deepQueryAll(selector, root = document) {
    const out = [...root.querySelectorAll(selector)];
    for (const host of root.querySelectorAll("*")) {
      if (host.shadowRoot) out.push(...deepQueryAll(selector, host.shadowRoot));
    }
    return out;
  }

  function isVisible(el) {
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    const style = getComputedStyle(el);
    return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0";
  }

  function inViewport(el) {
    const r = el.getBoundingClientRect();
    return r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth;
  }

  function labelFor(el) {
    if (el.labels && el.labels.length) return [...el.labels].map((l) => l.innerText).join(" ");
    return "";
  }

  function accessibleName(el) {
    const by = el.getAttribute("aria-labelledby");
    if (by) {
      const txt = by.split(/\s+/).map((id) => document.getElementById(id)?.innerText || "").join(" ").trim();
      if (txt) return txt;
    }
    const img = el.querySelector && el.querySelector("img[alt]");
    const candidates = [
      el.getAttribute("aria-label"),
      labelFor(el),
      el.getAttribute("placeholder"),
      el.isContentEditable || el.tagName === "SELECT" ? "" : el.innerText,
      el.getAttribute("title"),
      el.getAttribute("alt"),
      img ? img.getAttribute("alt") : "",
      ["submit", "button", "reset"].includes(el.type) ? el.value : ""
    ];
    for (const c of candidates) {
      const t = String(c || "").replace(/\s+/g, " ").trim();
      if (t) return t.length > 100 ? t.slice(0, 97) + "..." : t;
    }
    return "";
  }

  function roleOf(el) {
    const explicit = el.getAttribute("role");
    if (explicit) return explicit;
    const tag = el.tagName.toLowerCase();
    if (/^h[1-6]$/.test(tag)) return "heading";
    if (tag === "a") return "link";
    if (tag === "select") return "combobox";
    if (tag === "textarea" || el.isContentEditable) return "textbox";
    if (tag === "summary") return "button";
    if (tag === "input") {
      const t = (el.type || "text").toLowerCase();
      if (["checkbox", "radio", "range"].includes(t)) return t === "range" ? "slider" : t;
      if (["submit", "button", "reset", "image"].includes(t)) return "button";
      return t === "search" ? "searchbox" : "textbox";
    }
    return tag;
  }

  function register(el) {
    const ref = nextRef++;
    refs.set(ref, new WeakRef(el));
    return ref;
  }

  function describe(el, ref) {
    const role = roleOf(el);
    const item = { ref, role, name: accessibleName(el) };
    const sens = sensitiveKind(el);
    if (sens) item.sensitive = sens;
    if (el.tagName === "INPUT" && ["checkbox", "radio"].includes(el.type)) item.checked = el.checked;
    else if (el.getAttribute("aria-checked")) item.checked = el.getAttribute("aria-checked") === "true";
    if (el.tagName === "SELECT") item.value = el.options[el.selectedIndex]?.text || "";
    else if ("value" in el && el.tagName !== "BUTTON" && el.tagName !== "LI" && typeof el.value === "string" && role !== "button") {
      item.value = sens ? "[oculto]" : el.value.slice(0, 80);
    } else if (el.isContentEditable && role === "textbox") {
      item.value = el.innerText.replace(/\s+/g, " ").trim().slice(0, 80);
    }
    if (el.disabled || el.getAttribute("aria-disabled") === "true") item.disabled = true;
    if (role === "link" && el.href) item.href = el.href.slice(0, 120);
    if (!inViewport(el)) item.offscreen = true;
    return item;
  }

  function collectCandidates() {
    const seen = new Set();
    const list = [];
    for (const el of deepQueryAll(INTERACTIVE_SEL)) {
      if (seen.has(el)) continue;
      seen.add(el);
      if (!isVisible(el)) continue;
      const role = roleOf(el);
      if ((role === "heading" || role === "link") && !accessibleName(el)) continue;
      list.push(el);
    }
    return list;
  }

  function snapshot(args) {
    refs = new Map();
    nextRef = 1;
    const max = Math.min(Math.max(Number(args.max) || 120, 10), 400);
    let candidates = collectCandidates();
    if (args.onlyViewport) candidates = candidates.filter(inViewport);
    // Lo visible en pantalla primero; luego el resto en orden del documento.
    candidates.sort((a, b) => Number(inViewport(b)) - Number(inViewport(a)));
    const elements = candidates.slice(0, max).map((el) => describe(el, register(el)));
    return {
      title: document.title,
      url: location.href,
      paymentPage: isPaymentPage(),
      selection: String(window.getSelection() || "").trim().slice(0, 500),
      scroll: { y: Math.round(scrollY), maxY: Math.max(0, document.documentElement.scrollHeight - innerHeight) },
      total: candidates.length,
      truncated: candidates.length > max,
      elements
    };
  }

  function find(args) {
    const q = norm(args.text || args.query || "");
    if (!q) return { ok: false, error: "Falta args.text" };
    const max = Math.min(Number(args.max) || 10, 50);
    const matches = collectCandidates()
      .filter((el) => norm(accessibleName(el) + " " + (el.getAttribute("href") || "")).includes(q))
      .slice(0, max)
      .map((el) => describe(el, register(el)));
    return { ok: true, data: { query: args.text, count: matches.length, elements: matches } };
  }

  function getText(args) {
    const maxChars = Math.min(Math.max(Number(args.maxChars) || 8000, 200), 50000);
    let root;
    if (args.ref) root = deref(args.ref);
    else if (args.selector) root = document.querySelector(args.selector);
    else root = document.querySelector("main, article, [role=main]") || document.body;
    if (!root) return { ok: false, error: "No se encontro el contenedor indicado" };
    const text = (root.innerText || "").replace(/\n{3,}/g, "\n\n").trim();
    return { ok: true, data: { title: document.title, url: location.href, chars: text.length, truncated: text.length > maxChars, text: text.slice(0, maxChars) } };
  }

  // -------------------------------------------------------------------------
  // Acciones
  // -------------------------------------------------------------------------
  function deref(ref) {
    const w = refs.get(Number(ref));
    const el = w && w.deref();
    return el && el.isConnected ? el : null;
  }

  function resolve(args) {
    if (args.ref !== undefined) return deref(args.ref);
    if (args.selector) {
      try { return document.querySelector(args.selector); } catch { return null; }
    }
    if (args.text) {
      const q = norm(args.text);
      const all = collectCandidates();
      return all.find((el) => norm(accessibleName(el)) === q) || all.find((el) => norm(accessibleName(el)).includes(q)) || null;
    }
    return null;
  }

  function notFound(args) {
    return { ok: false, error: `Elemento no encontrado (${JSON.stringify(args).slice(0, 120)}). Haz un SNAPSHOT nuevo: las refs caducan al cambiar la pagina.` };
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  function mouseSequence(el) {
    const r = el.getBoundingClientRect();
    const opts = { bubbles: true, cancelable: true, composed: true, view: window, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2, button: 0 };
    el.dispatchEvent(new PointerEvent("pointerover", opts));
    el.dispatchEvent(new MouseEvent("mouseover", opts));
    el.dispatchEvent(new PointerEvent("pointerdown", opts));
    el.dispatchEvent(new MouseEvent("mousedown", opts));
    if (typeof el.focus === "function") el.focus({ preventScroll: true });
    el.dispatchEvent(new PointerEvent("pointerup", opts));
    el.dispatchEvent(new MouseEvent("mouseup", opts));
    el.click();
  }

  // _permitirPago solo lo pone el service worker cuando Alexander dio un permiso de pago (una web no puede mandarlo:
  // los mensajes a este content script solo pueden venir de la propia extension).
  const permitido = (args) => args && args._permitirPago === true;

  // v4: donde esta el elemento (centro, en px del viewport) para el clic/tecleo real. Aplica las mismas barreras.
  async function locate(args) {
    const proposito = args.purpose || "click";
    const tieneObjetivo = args.ref !== undefined || args.selector || args.text;
    const el = tieneObjetivo ? resolve(args) : (document.activeElement || document.body);
    if (!el) return notFound(args);
    if (proposito === "type") {
      const kind = sensitiveKind(el);
      if (kind === "password") return humanRequired("campo de contraseña (las rellena Alexander o el autocompletado de Brave)");
      if (kind === "payment") return humanRequired("campo de tarjeta o cuenta bancaria (los datos de pago los pone Alexander)");
    }
    const pago = isPaymentPage();
    const activa = proposito === "click" || proposito === "enter";
    let compra = activa && isBuyControl(el);
    const formPago = proposito === "enter" && !!(el.form && el.form.action && PAYMENT_URL_RE.test(el.form.action));
    let marcoPago = activa && esMarcoPago(el); // pasar el raton por encima no paga nada; clic/Enter si
    if (tieneObjetivo) {
      el.scrollIntoView({ block: "center", inline: "center", behavior: "instant" });
      await sleep(80);
    }
    const r0 = el.getBoundingClientRect();
    // Lo que de verdad recibira el clic en ese punto (una capa encima, un iframe de pasarela...). Si el elemento no
    // tiene tamaño (oculto) no hay punto que mirar: ira por el modo simulado sobre el propio elemento.
    const visible0 = r0.width >= 1 && r0.height >= 1;
    const encima = activa && visible0 ? document.elementFromPoint(r0.left + r0.width / 2, r0.top + r0.height / 2) : null;
    if (encima && encima !== el && !el.contains(encima)) {
      if (isBuyControl(encima)) compra = true;
      if (esMarcoPago(encima)) marcoPago = true;
    }
    if ((pago || compra || formPago || marcoPago) && !permitido(args)) {
      const motivo = compra ? `boton de compra o pago ("${accessibleName(encima && isBuyControl(encima) ? encima : el)}")`
        : marcoPago ? "formulario de pago incrustado" : formPago ? "formulario de pago" : "pagina de pago/checkout";
      return humanRequired(motivo, "payment");
    }
    compra = compra || formPago || marcoPago;
    const data = { name: accessibleName(el), role: roleOf(el), gated: pago || compra, buy: compra, url: location.href };
    if (proposito === "type" && el.tagName === "SELECT") return { ok: true, data: { ...data, select: true } };
    if (proposito === "upload") {
      const id = "u" + Math.random().toString(36).slice(2, 10);
      el.setAttribute("data-nova-up", id);
      data.uploadId = id;
      data.fileInput = el.tagName === "INPUT" && (el.type || "").toLowerCase() === "file";
    }
    const r = el.getBoundingClientRect();
    data.hidden = r.width < 1 || r.height < 1 || !isVisible(el);
    data.x = Math.round(r.left + r.width / 2);
    data.y = Math.round(r.top + r.height / 2);
    data.dpr = devicePixelRatio;
    return { ok: true, data };
  }

  // v4: antes de un clic por coordenadas (iframes, videollamadas, canvas) mira que hay debajo.
  function pointCheck(args) {
    const vacio = (v) => v === undefined || v === null || v === "" || typeof v === "boolean";
    const x = Number(args.x), y = Number(args.y);
    if (vacio(args.x) || vacio(args.y) || !Number.isFinite(x) || !Number.isFinite(y)) return { ok: false, error: "Faltan args.x y args.y (px del viewport)" };
    const el = document.elementFromPoint(x, y);
    if (!el) return { ok: false, error: `No hay nada en (${x}, ${y}): fuera de la pagina visible` };
    const pago = isPaymentPage();
    const compra = isBuyControl(el);
    const marco = esMarcoPago(el);
    if ((pago || compra || marco) && !permitido(args)) {
      return humanRequired(marco ? "formulario de pago incrustado" : compra ? `boton de compra o pago ("${accessibleName(el)}")` : "pagina de pago/checkout", "payment");
    }
    return { ok: true, data: { name: accessibleName(el) || el.tagName.toLowerCase(), tag: el.tagName.toLowerCase(), iframe: el.tagName === "IFRAME", gated: pago || compra || marco, buy: compra || marco, url: location.href } };
  }

  async function click(args) {
    const el = resolve(args);
    if (!el) return notFound(args);
    if (isPaymentPage() && !permitido(args)) return humanRequired("pagina de pago/checkout", "payment");
    if (isBuyControl(el) && !permitido(args)) return humanRequired(`boton de compra o pago ("${accessibleName(el)}")`, "payment");
    if (esMarcoPago(el) && !permitido(args)) return humanRequired("formulario de pago incrustado", "payment");
    // El pase solo se gasta si lo que se pulsa ES el pago (no "Continuar" en la pagina de checkout)
    const pagoUsado = permitido(args) && (isBuyControl(el) || esMarcoPago(el));
    el.scrollIntoView({ block: "center", inline: "center", behavior: "instant" });
    await sleep(50);
    mouseSequence(el);
    await sleep(Number(args.waitMs) || 300);
    return { ok: true, data: { status: "clicked", name: accessibleName(el), url: location.href, pagoUsado } };
  }

  async function hover(args) {
    const el = resolve(args);
    if (!el) return notFound(args);
    el.scrollIntoView({ block: "center", behavior: "instant" });
    const r = el.getBoundingClientRect();
    const opts = { bubbles: true, composed: true, clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 };
    for (const t of ["pointerover", "pointerenter", "mouseover", "mouseenter", "mousemove"]) {
      el.dispatchEvent(t.startsWith("pointer") ? new PointerEvent(t, opts) : new MouseEvent(t, opts));
    }
    await sleep(300);
    return { ok: true, data: { status: "hovered", name: accessibleName(el) } };
  }

  function insertIntoEditable(el, text, clear) {
    el.focus();
    const sel = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(el);
    if (!clear) range.collapse(false);
    sel.removeAllRanges();
    sel.addRange(range);
    // execCommand sigue siendo la via mas compatible con editores (Lexical/WhatsApp, Draft.js, ProseMirror).
    if (!document.execCommand("insertText", false, text)) {
      el.dispatchEvent(new InputEvent("beforeinput", { inputType: "insertText", data: text, bubbles: true, cancelable: true }));
      if (clear) el.textContent = "";
      el.append(document.createTextNode(text));
      el.dispatchEvent(new InputEvent("input", { inputType: "insertText", data: text, bubbles: true }));
    }
  }

  function setNativeValue(el, value) {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function type(args) {
    const el = resolve(args);
    if (!el) return notFound(args);
    const kind = sensitiveKind(el);
    if (kind === "password") return humanRequired("campo de contraseña");
    if (kind === "payment") return humanRequired("campo de pago o tarjeta");
    if (isPaymentPage() && !permitido(args)) return humanRequired("pagina de pago/checkout", "payment");

    const text = args.text !== undefined ? String(args.text) : "";
    const clear = args.clear !== false;
    el.scrollIntoView({ block: "center", behavior: "instant" });

    if (el.tagName === "SELECT") {
      const q = norm(text);
      const opt = [...el.options].find((o) => norm(o.text) === q || norm(o.value) === q) || [...el.options].find((o) => norm(o.text).includes(q));
      if (!opt) return { ok: false, error: `Opcion "${text}" no existe. Opciones: ${[...el.options].map((o) => o.text).slice(0, 30).join(" | ")}` };
      el.value = opt.value;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
      return { ok: true, data: { status: "selected", option: opt.text } };
    }

    if (el.isContentEditable) {
      insertIntoEditable(el, text, clear);
    } else if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
      el.focus();
      setNativeValue(el, clear ? text : el.value + text);
    } else {
      return { ok: false, error: `El elemento (${roleOf(el)}) no admite texto. Busca un textbox en el SNAPSHOT.` };
    }

    if (args.enter) {
      await sleep(80);
      const blocked = pressEnterOn(el, args);
      if (blocked) return blocked;
    }
    return { ok: true, data: { status: "typed", chars: text.length, enterPressed: !!args.enter } };
  }

  const KEYS = {
    Enter: [13, "Enter"], Escape: [27, "Escape"], Tab: [9, "Tab"], Backspace: [8, "Backspace"], Delete: [46, "Delete"], Space: [32, "Space"],
    ArrowUp: [38, "ArrowUp"], ArrowDown: [40, "ArrowDown"], ArrowLeft: [37, "ArrowLeft"], ArrowRight: [39, "ArrowRight"],
    PageUp: [33, "PageUp"], PageDown: [34, "PageDown"], Home: [36, "Home"], End: [35, "End"]
  };

  function dispatchKey(el, key, mods = {}) {
    const [keyCode, code] = KEYS[key] || [key.length === 1 ? key.toUpperCase().charCodeAt(0) : 0, key.length === 1 ? "Key" + key.toUpperCase() : key];
    const opts = { key: key === "Space" ? " " : key, code, keyCode, which: keyCode, bubbles: true, cancelable: true, composed: true, ...mods };
    const down = new KeyboardEvent("keydown", opts);
    el.dispatchEvent(down);
    if (key.length === 1 || key === "Enter") el.dispatchEvent(new KeyboardEvent("keypress", opts));
    el.dispatchEvent(new KeyboardEvent("keyup", opts));
    return down.defaultPrevented;
  }

  function pressEnterOn(el, args) {
    const handled = dispatchKey(el, "Enter");
    // Formularios clasicos: si nadie gestiono el Enter, enviar el formulario de verdad.
    if (!handled && el.form && el.tagName === "INPUT") {
      if ((isPaymentPage() || (el.form.action && PAYMENT_URL_RE.test(el.form.action))) && !permitido(args)) return humanRequired("formulario de pago", "payment");
      try { el.form.requestSubmit(); } catch {}
    }
    return null;
  }

  async function pressKey(args) {
    const key = args.key || "Enter";
    const el = args.ref !== undefined || args.selector ? resolve(args) : (document.activeElement || document.body);
    if (!el) return notFound(args);
    // Enter y Espacio activan el boton enfocado: mismo control que un clic
    if ((key === "Enter" || key === "Space" || key === " ") && !permitido(args)) {
      if (isPaymentPage()) return humanRequired("pagina de pago/checkout", "payment");
      if (isBuyControl(el) || esMarcoPago(el)) return humanRequired(`boton de compra o pago ("${accessibleName(el)}")`, "payment");
    }
    const pagoUsado = permitido(args) && (key === "Enter" || key === "Space" || key === " ") && (isBuyControl(el) || esMarcoPago(el));
    if (key === "Enter") {
      const blocked = pressEnterOn(el, args);
      if (blocked) return blocked;
    } else {
      dispatchKey(el, key, { ctrlKey: !!args.ctrl, shiftKey: !!args.shift, altKey: !!args.alt });
    }
    await sleep(150);
    return { ok: true, data: { status: "key_pressed", key, pagoUsado } };
  }

  function scroll(args) {
    const dir = args.direction || "down";
    const amount = Number(args.pixels) || Math.round(innerHeight * 0.8);
    const target = args.ref !== undefined || args.selector ? resolve(args) : null;
    if ((args.ref !== undefined || args.selector) && !target) return notFound(args);
    if (target && !args.direction) {
      target.scrollIntoView({ block: "center", behavior: "instant" });
      return { ok: true, data: { status: "scrolled_into_view" } };
    }
    const box = target || document.scrollingElement || document.documentElement;
    if (dir === "down") box.scrollBy({ top: amount, behavior: "instant" });
    else if (dir === "up") box.scrollBy({ top: -amount, behavior: "instant" });
    else if (dir === "top") box.scrollTo({ top: 0, behavior: "instant" });
    else if (dir === "bottom") box.scrollTo({ top: box.scrollHeight, behavior: "instant" });
    else return { ok: false, error: `Direccion no valida: ${dir} (up, down, top, bottom)` };
    return { ok: true, data: { status: "scrolled", direction: dir, y: Math.round(box === document.scrollingElement ? scrollY : box.scrollTop) } };
  }

  // -------------------------------------------------------------------------
  // YouTube
  // -------------------------------------------------------------------------
  async function youtube(args) {
    const video = document.querySelector("video");
    if (!video) return { ok: false, error: "No hay reproductor de video en esta pagina" };
    const cmd = args.command || "toggle";
    try {
      if (cmd === "play") await video.play();
      else if (cmd === "pause") video.pause();
      else if (cmd === "toggle") video.paused ? await video.play() : video.pause();
      else if (cmd === "speed") video.playbackRate = Math.min(Math.max(parseFloat(args.speed) || 1, 0.25), 4);
      else if (cmd === "seek") video.currentTime = Math.max(0, Number(args.seconds) || 0);
      else if (cmd === "forward") video.currentTime += Number(args.seconds) || 10;
      else if (cmd === "back") video.currentTime = Math.max(0, video.currentTime - (Number(args.seconds) || 10));
      else if (cmd === "volume") video.volume = Math.min(Math.max(Number(args.volume), 0), 1);
      else if (cmd === "mute") video.muted = !video.muted;
      else if (cmd === "next") document.querySelector(".ytp-next-button")?.click();
      else if (cmd !== "status") return { ok: false, error: `Comando de YouTube desconocido: ${cmd}` };
    } catch (e) {
      return { ok: false, error: `El navegador bloqueo la reproduccion: ${e.message}` };
    }
    await sleep(150);
    const titleEl = document.querySelector("h1.ytd-watch-metadata yt-formatted-string, h1.title");
    const channel = document.querySelector("ytd-channel-name a, #owner #channel-name a");
    return {
      ok: true,
      data: {
        title: titleEl ? titleEl.innerText : document.title.replace(/ - YouTube$/, ""),
        channel: channel ? channel.innerText : undefined,
        paused: video.paused,
        currentTime: Math.round(video.currentTime),
        duration: Math.round(video.duration || 0),
        speed: video.playbackRate,
        volume: Math.round(video.volume * 100),
        muted: video.muted
      }
    };
  }

  // -------------------------------------------------------------------------
  // WhatsApp Web (los selectores de WhatsApp cambian a menudo: si algo falla, SNAPSHOT + CLICK/TYPE sirve igual)
  // -------------------------------------------------------------------------
  function waChatItems() {
    const pane = document.querySelector("#pane-side");
    if (!pane) return [];
    const items = pane.querySelectorAll("[role=listitem], [role=row]");
    return [...items].filter((it) => it.querySelector("span[title]"));
  }

  function waChatInfo(item) {
    const titleSpan = item.querySelector("span[title]");
    const lines = item.innerText.split("\n").map((l) => l.trim()).filter(Boolean);
    const unreadEl = item.querySelector("[aria-label*='unread' i], [aria-label*='no leído' i], [aria-label*='sin leer' i]");
    const unreadMatch = unreadEl ? (unreadEl.getAttribute("aria-label") || "").match(/\d+/) : null;
    const name = titleSpan ? titleSpan.getAttribute("title") : lines[0];
    return {
      name,
      time: lines[1] && lines[1].length <= 12 ? lines[1] : undefined,
      preview: lines.slice(2).filter((l) => !/^\d+$/.test(l)).join(" ").slice(0, 120),
      unread: unreadMatch ? Number(unreadMatch[0]) : unreadEl ? 1 : 0
    };
  }

  function waCurrentChat() {
    const header = document.querySelector("#main header");
    if (!header) return null;
    const t = header.querySelector("span[title]");
    return (t && t.getAttribute("title")) || header.innerText.split("\n")[0];
  }

  function waComposer() {
    return document.querySelector("#main footer [contenteditable='true'], #main footer [role=textbox]");
  }

  async function whatsapp(args) {
    if (location.hostname !== "web.whatsapp.com") return { ok: false, error: "Abre web.whatsapp.com primero (NAVIGATE_TAB o NEW_TAB)" };
    if (!document.querySelector("#pane-side")) return { ok: false, error: "WhatsApp Web no ha cargado o no hay sesion (¿codigo QR?)" };
    const cmd = args.command || "chats";

    if (cmd === "chats") {
      const max = Math.min(Number(args.max) || 20, 60);
      let list = waChatItems().map((it) => ({ it, info: waChatInfo(it) }));
      if (args.unreadOnly) list = list.filter((x) => x.info.unread > 0);
      const chats = list.slice(0, max).map((x) => ({ ref: register(x.it), ...x.info }));
      return { ok: true, data: { openChat: waCurrentChat(), count: chats.length, chats } };
    }

    if (cmd === "open") {
      const q = norm(args.name);
      if (!q) return { ok: false, error: "Falta args.name" };
      const items = waChatItems();
      const item = items.find((it) => norm(waChatInfo(it).name) === q) || items.find((it) => norm(waChatInfo(it).name).includes(q));
      if (!item) return { ok: false, error: `No veo el chat "${args.name}" en la lista visible. Usa la busqueda: TYPE en el buscador del SNAPSHOT y luego CLICK.` };
      mouseSequence(item.querySelector("span[title]") || item);
      for (let i = 0; i < 20 && norm(waCurrentChat() || "") !== norm(waChatInfo(item).name); i++) await sleep(100);
      return { ok: true, data: { openChat: waCurrentChat() } };
    }

    if (cmd === "read") {
      const chat = waCurrentChat();
      if (!chat) return { ok: false, error: "No hay ningun chat abierto (usa command: open)" };
      const max = Math.min(Number(args.max) || 30, 200);
      const nodes = [...document.querySelectorAll("#main [data-pre-plain-text]")];
      const messages = nodes.slice(-max).map((n) => {
        const meta = n.getAttribute("data-pre-plain-text") || ""; // "[10:32, 5/11/2026] Juan: "
        const m = meta.match(/^\[(.*?)\]\s*(.*?):\s*$/);
        const textEl = n.querySelector(".selectable-text") || n;
        return {
          from: m ? m[2] : undefined,
          when: m ? m[1] : undefined,
          outgoing: !!n.closest(".message-out"),
          text: textEl.innerText.trim()
        };
      });
      return { ok: true, data: { chat, count: messages.length, messages } };
    }

    if (cmd === "send") {
      const text = String(args.text || "");
      if (!text.trim()) return { ok: false, error: "Falta args.text" };
      const chat = waCurrentChat();
      if (!chat) return { ok: false, error: "No hay ningun chat abierto (usa command: open)" };
      if (args.expectChat && norm(chat) !== norm(args.expectChat)) {
        return { ok: false, error: `El chat abierto es "${chat}", no "${args.expectChat}". No envio nada.` };
      }
      const box = waComposer();
      if (!box) return { ok: false, error: "No encuentro la caja de texto del chat" };
      insertIntoEditable(box, text, true);
      await sleep(150);
      const sendIcon = document.querySelector("#main footer [data-icon='send'], #main footer [data-icon='wds-ic-send-filled']");
      const sendBtn = (sendIcon && sendIcon.closest("button, [role=button]")) ||
        document.querySelector("#main footer button[aria-label='Enviar'], #main footer button[aria-label='Send']");
      if (sendBtn) mouseSequence(sendBtn);
      else dispatchKey(box, "Enter");
      await sleep(300);
      const pending = (waComposer()?.innerText || "").trim();
      return { ok: !pending, data: { chat, sent: !pending }, error: pending ? "El texto quedo escrito pero no se envio" : undefined };
    }

    return { ok: false, error: `Comando de WhatsApp desconocido: ${cmd} (chats, open, read, send)` };
  }
})();
