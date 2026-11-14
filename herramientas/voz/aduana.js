// NOVA · ADUANA DE ADJUNTOS dentro de Antigravity (la inyecta nova_voz.py por CDP, igual que la mascota). 09/11/2026, Claude.
// Lo que Alexander pega, arrastra o elige con el boton de adjuntar (PDF, imagenes, Word, Excel...) NO entra al chat:
// se le pasa a Python (binding novaAduana), que lo guarda en temporal\ y lo lee EN LOCAL (InternVL / destilador).
// En el chat aparece "[adjunto local: <archivo>]" y el hook de turno le da a Nova el texto ya leido -> 0 tokens de nube.
// - Manteniendo SHIFT al pegar/soltar/elegir, pasa como siempre (por si Gemini tiene que ver el original).
// - Si Python no da senales de vida (latido de menos de 10 s), la aduana NO intercepta: nunca se pierde un archivo.
(() => {
  // v1 ya inyectada (adjuntos): se le suma v2 (claves) sin duplicar los adjuntos, que v1 sigue atendiendo antes
  if (window.__novaAduana && window.__novaAduana.version >= 2) return 'ya';
  const soloClaves = !!window.__novaAduana;
  const TIPOS = /\.(pdf|png|jpe?g|webp|gif|bmp|docx|xlsx|xlsm|pptx|txt|md|csv|html?)$/i;
  const MAX_BYTES = 30 * 1024 * 1024;
  let shift = false;
  addEventListener('keydown', e => { if (e.key === 'Shift') shift = true; }, true);
  addEventListener('keyup', e => { if (e.key === 'Shift') shift = false; }, true);
  addEventListener('blur', () => { shift = false; });

  const vivo = () => typeof window.novaAduana === 'function' && Date.now() - (window.__novaAduanaLatido || 0) < 10000;
  const apto = f => (TIPOS.test(f.name || '') || /^image\//.test(f.type || '')) && f.size <= MAX_BYTES;

  function enviar(files, via) {
    for (const f of files) {
      const r = new FileReader();
      r.onload = () => {
        const b64 = String(r.result).split(',')[1] || '';
        window.novaAduana(JSON.stringify({ nombre: f.name || 'imagen.png', tipo: f.type || '', tam: f.size, via, b64 }));
      };
      r.readAsDataURL(f);
    }
  }

  // Solo intercepta si TODOS los archivos son aptos (si hay uno raro, pasa todo como siempre: nada se pierde)
  function interceptar(e, lista, via) {
    const files = [...(lista || [])];
    if (!files.length || shift || !vivo() || !files.every(apto)) return false;
    e.preventDefault(); e.stopImmediatePropagation(); e.stopPropagation();
    enviar(files, via);
    window.__novaAduana.ultimo = { via, n: files.length, t: Date.now() };
    return true;
  }

  // ---- 12/11 (Claude) GUARDIAN DE CLAVES: una clave de API pegada NO llega a la nube. Se quita del texto, Python la
  // guarda en el cofre (vault\google_cloud.env) y en el mensaje queda "[clave guardada en el cofre: NOMBRE]".
  const RE_CLAVE = /\b(sk-(?:gamma-|ant-|or-|proj-)?[A-Za-z0-9_-]{20,}|sk_[a-f0-9]{32,}|AIza[0-9A-Za-z_-]{30,}|(?:ghp|gho|ghs|ghu)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|re_[A-Za-z0-9]{8,}_[A-Za-z0-9]{16,}|gsk_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}|sb_(?:secret|publishable)_[A-Za-z0-9_-]{20,}|(?:sk|rk|pk)_live_[A-Za-z0-9]{20,}|xox[abprs]-[A-Za-z0-9-]{20,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,})\b/g;
  // Claves sin prefijo conocido (Trello...): una tira larga de letras Y numeros pegada sola
  const RE_SUELTA = /^[A-Za-z0-9_\-]{32,}$/;
  const PREFIJOS = [[/^sk-gamma-/, 'GAMMA_API_KEY'], [/^sk-ant-/, 'ANTHROPIC_API_KEY'], [/^sk-or-/, 'OPENROUTER_API_KEY'],
    [/^sk-/, 'OPENAI_API_KEY'], [/^sk_[a-f0-9]{32,}$/, 'ELEVENLABS_API_KEY'], [/^AIza/, 'GOOGLE_API_KEY'],
    [/^(?:ghp|gho|ghs|ghu)_|^github_pat_/, 'GITHUB_TOKEN'], [/^re_/, 'RESEND_API_KEY'], [/^gsk_/, 'GROQ_API_KEY'],
    [/^hf_/, 'HUGGINGFACE_TOKEN'], [/^sb_secret_/, 'SUPABASE_SECRET_KEY'], [/^sb_publishable_/, 'SUPABASE_PUBLISHABLE_KEY'],
    [/^(?:sk|rk)_live_/, 'STRIPE_SECRET_KEY'], [/^pk_live_/, 'STRIPE_PUBLISHABLE_KEY'], [/^xox/, 'SLACK_TOKEN'], [/^AKIA/, 'AWS_ACCESS_KEY_ID']];
  const SERVICIOS = ['gamma', 'trello', 'openai', 'anthropic', 'claude', 'gemini', 'google', 'youtube', 'groq', 'mistral',
    'openrouter', 'supabase', 'resend', 'elevenlabs', 'github', 'stripe', 'huggingface', 'deepseek', 'notion', 'airtable',
    'twilio', 'cloudflare', 'vercel', 'netlify', 'highlevel', 'brevo', 'mailchimp'];

  function textoEditor() {
    const el = document.activeElement;
    return el ? (el.value !== undefined ? el.value : el.innerText || '') : '';
  }

  function nombreClave(clave, antes) {
    for (const [re, n] of PREFIJOS) if (re.test(clave)) return n;
    const bajo = (antes || '').toLowerCase().slice(-120);  // "la api de trello: <clave>"
    let mejor = null, pos = -1;
    for (const s of SERVICIOS) { const i = bajo.lastIndexOf(s); if (i > pos) { pos = i; mejor = s; } }
    if (mejor) return `${mejor.toUpperCase()}_${/token/.test(bajo.slice(-40)) ? 'TOKEN' : 'API_KEY'}`;
    const d = new Date(), p = x => String(x).padStart(2, '0');
    return `CLAVE_${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
  }

  function aviso(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    div.style.cssText = 'position:fixed;bottom:90px;left:50%;transform:translateX(-50%);z-index:2147483647;'
      + 'background:#0F2240;color:#fff;padding:10px 16px;border-radius:8px;font:13px Segoe UI,sans-serif;'
      + 'box-shadow:0 4px 16px rgba(0,0,0,.35);max-width:560px';
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 6000);
  }

  function claves(texto) {
    const halladas = [...new Set(texto.match(RE_CLAVE) || [])];
    const limpio = texto.trim();
    if (!halladas.length && RE_SUELTA.test(limpio) && /[0-9]/.test(limpio) && /[A-Za-z]/.test(limpio)) halladas.push(limpio);
    return halladas;
  }

  function guardarClaves(e) {
    if (shift) return false;
    const texto = e.clipboardData && e.clipboardData.getData('text/plain');
    if (!texto) return false;
    const halladas = claves(texto);
    if (!halladas.length) return false;
    e.preventDefault(); e.stopImmediatePropagation(); e.stopPropagation();
    const previo = textoEditor();
    let resto = texto;
    const nombres = [];
    for (const clave of halladas) {
      const antes = previo + ' ' + texto.slice(0, texto.indexOf(clave));
      let nombre = nombreClave(clave, antes);
      if (nombres.includes(nombre)) nombre += `_${nombres.length + 1}`;  // dos claves del mismo servicio
      if (vivo()) window.novaAduana(JSON.stringify({ clave, nombre }));
      resto = resto.split(clave).join(vivo() ? `[clave guardada en el cofre: ${nombre}]` : '[clave NO enviada]');
      nombres.push(nombre);
    }
    document.execCommand('insertText', false, resto);
    aviso(vivo() ? `Clave guardada en el cofre como ${nombres.join(', ')}. No ha salido de tu ordenador.`
                 : 'Clave retenida: el guardián no responde (¿Nova Voz cerrada?). No se ha enviado a la nube.');
    window.__novaAduana.ultimo = { via: 'clave', n: halladas.length, t: Date.now() };
    return true;
  }

  // Red de seguridad: una clave escrita a mano (o pegada con Shift) no sale al pulsar Enter
  addEventListener('keydown', e => {
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
    const texto = textoEditor();
    if (texto && (texto.match(RE_CLAVE) || []).length) {
      e.preventDefault(); e.stopImmediatePropagation(); e.stopPropagation();
      aviso('Hay una clave de API en el mensaje: no lo envío. Bórrala y pégala con Ctrl+V: la guardo en el cofre.');
    }
  }, true);

  addEventListener('paste', e => {
    if (!soloClaves && interceptar(e, e.clipboardData && e.clipboardData.files, 'pegar')) return;
    guardarClaves(e);
  }, true);
  if (!soloClaves) {
    addEventListener('drop', e => interceptar(e, e.dataTransfer && e.dataTransfer.files, 'arrastrar'), true);
    addEventListener('change', e => {
      const t = e.target;
      if (t && t.tagName === 'INPUT' && t.type === 'file' && interceptar(e, t.files, 'boton')) t.value = '';
    }, true);
  }

  window.__novaAduana = Object.assign(window.__novaAduana || {}, { version: 2, ultimo: null });
  return 'creada';
})();
