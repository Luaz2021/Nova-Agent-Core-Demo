// NOVA · mascota 2D dentro de Antigravity (la inyecta nova_voz.py por CDP; vive y muere con la ventana de Antigravity).
// Estados: espera · mirando · escuchando · pensando · hablando · error · pausa.  API: window.__novaMascota.set(estado, texto)
(() => {
  // 11/11 (Claude): con VERSION, una mascota nueva sustituye a la vieja sin reiniciar Antigravity
  const VERSION = 2;
  if (window.__novaMascota && (window.__novaMascota.version || 1) >= VERSION) return 'ya';
  if (window.__novaMascota) { try { window.__novaMascota.quitar(); } catch (e) { document.getElementById('nova-mascota')?.remove(); delete window.__novaMascota; } }
  const host = document.createElement('div');
  host.id = 'nova-mascota';
  host.style.cssText = 'position:fixed;left:40px;bottom:60px;width:150px;height:204px;z-index:2147483000;pointer-events:none;';
  const sh = host.attachShadow({ mode: 'open' });
  const css = new CSSStyleSheet();
  css.replaceSync(`
    :host { all: initial; }
    .caja { position: relative; width: 150px; height: 204px; font-family: system-ui, sans-serif; }
    svg { position: absolute; left: 15px; bottom: 0; width: 120px; height: 140px; overflow: visible;
          animation: flotar 3.2s ease-in-out infinite; filter: drop-shadow(0 6px 10px rgba(0,0,0,.35)); }
    @keyframes flotar { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-3px) } }
    #cabeza { transform-origin: 60px 70px; transition: transform .35s cubic-bezier(.3,1.5,.5,1); }
    #ojos { transform-origin: 60px 64px; animation: parpadeo 4.6s infinite; }
    @keyframes parpadeo { 0%,92%,100% { transform: scaleY(1) } 95% { transform: scaleY(.08) } }
    #pupilas { transition: transform .3s ease; }
    #boca-cerrada { transition: opacity .15s; } #boca-abierta { opacity: 0; transform-origin: 60px 86px; }
    #luz { transition: fill .3s; } #luz-halo { transition: fill .3s; animation: halo 2s ease-in-out infinite; }
    @keyframes halo { 0%,100% { opacity: .25 } 50% { opacity: .65 } }
    .bocadillo { position: absolute; left: 50%; top: 2px; height: 28px; padding: 0 11px; border-radius: 14px; white-space: nowrap;
                 background: #1e293b; border: 1.5px solid #38bdf8; color: #e2e8f0; display: flex; align-items: center;
                 justify-content: center; gap: 6px; font-size: 12px; font-weight: 700; letter-spacing: .2px; opacity: 0;
                 transform: translate(-50%, 6px) scale(.8); transition: opacity .2s, transform .25s cubic-bezier(.3,1.6,.5,1); }
    .bocadillo .ico { display: inline-flex; align-items: center; gap: 3px; height: 16px; }
    .bocadillo::after { content: ''; position: absolute; left: calc(50% - 5px); bottom: -7px; width: 10px; height: 10px; background: #1e293b;
                        border-right: 1.5px solid #38bdf8; border-bottom: 1.5px solid #38bdf8; transform: rotate(45deg); }
    .ver .bocadillo { opacity: 1; transform: translate(-50%, 0); }
    .onda { width: 3px; border-radius: 2px; background: #4ade80; animation: onda .7s ease-in-out infinite; }
    .onda:nth-child(2) { animation-delay: .12s } .onda:nth-child(3) { animation-delay: .24s } .onda:nth-child(4) { animation-delay: .36s }
    @keyframes onda { 0%,100% { height: 5px } 50% { height: 16px } }
    .punto { width: 6px; height: 6px; border-radius: 50%; background: #fbbf24; animation: punto 1s ease-in-out infinite; }
    .punto:nth-child(2) { animation-delay: .15s } .punto:nth-child(3) { animation-delay: .3s }
    @keyframes punto { 0%,100% { transform: translateY(0); opacity: .5 } 50% { transform: translateY(-5px); opacity: 1 } }
    /* --- estados --- */
    .mirando #cabeza { transform: rotate(-7deg) translateY(-3px) scale(1.04); }
    .mirando #pupilas { transform: translate(-1px, 2px) scale(1.18); }
    .escuchando #cabeza { transform: rotate(-4deg); }
    .escuchando #pupilas { transform: scale(1.1); }
    .pensando #cabeza { transform: rotate(5deg); }
    .pensando #pupilas { transform: translate(2px, -3px); }
    .hablando #boca-cerrada { opacity: 0; }
    .hablando #boca-abierta { opacity: 1; animation: hablar .28s ease-in-out infinite alternate; }
    @keyframes hablar { from { transform: scaleY(.35) } to { transform: scaleY(1.1) } }
    .error #cabeza { transform: rotate(9deg); }
    .error #ojos { animation: none; transform: scaleY(.45); }
    .pausa svg { opacity: .45; animation: none; }
    .pausa #ojos { animation: none; transform: scaleY(.1); }
  `);
  sh.adoptedStyleSheets = [css];
  sh.innerHTML = `
  <div class="caja" id="caja">
    <div class="bocadillo" id="bocadillo"></div>
    <svg viewBox="0 0 120 140" aria-hidden="true">
      <!-- cuerpo -->
      <path d="M32 140 C32 116 44 106 60 106 C76 106 88 116 88 140 Z" fill="#e2e8f0"/>
      <path d="M44 140 C46 124 52 116 60 116 C68 116 74 124 76 140 Z" fill="#cbd5e1"/>
      <circle cx="60" cy="124" r="5" fill="#0f172a"/><circle id="pecho" cx="60" cy="124" r="2.6" fill="#38bdf8"/>
      <rect x="54" y="98" width="12" height="10" rx="3" fill="#f1d5c4"/>
      <g id="cabeza">
        <!-- pelo de atras -->
        <path d="M24 66 C20 30 42 16 60 16 C80 16 100 30 96 66 C98 86 92 98 86 102 L34 102 C28 98 22 86 24 66 Z" fill="#1e2a4a"/>
        <!-- cara -->
        <path d="M33 62 C33 40 45 30 60 30 C75 30 87 40 87 62 C87 82 75 96 60 96 C45 96 33 82 33 62 Z" fill="#ffe7da"/>
        <!-- auriculares robot -->
        <rect x="22" y="54" width="12" height="22" rx="5" fill="#94a3b8"/><rect x="86" y="54" width="12" height="22" rx="5" fill="#94a3b8"/>
        <rect x="25" y="60" width="6" height="10" rx="3" fill="#0f172a"/><rect x="89" y="60" width="6" height="10" rx="3" fill="#0f172a"/>
        <!-- flequillo con mechas cian -->
        <path d="M30 56 C30 30 46 20 62 20 C80 20 92 32 90 56 C86 46 80 40 74 38 C72 46 66 50 60 52 C62 44 60 40 56 38 C52 46 44 52 36 54 C38 48 38 44 40 40 C34 44 31 50 30 56 Z" fill="#273a66"/>
        <path d="M62 22 C70 24 78 30 82 38" stroke="#22d3ee" stroke-width="2.5" stroke-linecap="round" fill="none" opacity=".85"/>
        <path d="M46 26 C42 30 40 34 39 39" stroke="#22d3ee" stroke-width="2" stroke-linecap="round" fill="none" opacity=".6"/>
        <!-- antena -->
        <line x1="60" y1="20" x2="60" y2="8" stroke="#94a3b8" stroke-width="2.5"/>
        <circle id="luz-halo" cx="60" cy="6" r="7" fill="#38bdf8"/><circle id="luz" cx="60" cy="6" r="3.6" fill="#38bdf8"/>
        <!-- ojos -->
        <g id="ojos">
          <g id="pupilas">
            <ellipse cx="48" cy="64" rx="6.5" ry="8.5" fill="#1e293b"/><ellipse cx="72" cy="64" rx="6.5" ry="8.5" fill="#1e293b"/>
            <ellipse cx="48" cy="66" rx="4.6" ry="6" fill="#0891b2"/><ellipse cx="72" cy="66" rx="4.6" ry="6" fill="#0891b2"/>
            <circle cx="46" cy="61" r="2.4" fill="#fff"/><circle cx="70" cy="61" r="2.4" fill="#fff"/>
            <circle cx="50.5" cy="68.5" r="1.1" fill="#fff" opacity=".8"/><circle cx="74.5" cy="68.5" r="1.1" fill="#fff" opacity=".8"/>
          </g>
        </g>
        <!-- mejillas y boca -->
        <ellipse cx="41" cy="77" rx="5" ry="2.6" fill="#fda4af" opacity=".55"/><ellipse cx="79" cy="77" rx="5" ry="2.6" fill="#fda4af" opacity=".55"/>
        <path id="boca-cerrada" d="M55 84 Q60 88 65 84" stroke="#9f1239" stroke-width="1.8" stroke-linecap="round" fill="none"/>
        <ellipse id="boca-abierta" cx="60" cy="86" rx="4" ry="3.2" fill="#9f1239"/>
      </g>
    </svg>
  </div>`;
  document.body.appendChild(host);
  const caja = sh.getElementById('caja'), bocadillo = sh.getElementById('bocadillo');
  const luz = sh.getElementById('luz'), halo = sh.getElementById('luz-halo'), pecho = sh.getElementById('pecho');
  const LUZ = { espera: '#38bdf8', mirando: '#22d3ee', escuchando: '#4ade80', pensando: '#fbbf24', enviando: '#fbbf24',
                hablando: '#60a5fa', error: '#f87171', pausa: '#64748b', leyendo: '#c084fc' };
  const ONDAS = '<span class="ico"><span class="onda"></span><span class="onda"></span><span class="onda"></span><span class="onda"></span></span>';
  const PUNTOS = '<span class="ico"><span class="punto"></span><span class="punto"></span><span class="punto"></span></span>';
  const BOCADILLO = {
    mirando: '<span style="color:#67e8f9">¡Te oigo!</span>',
    escuchando: ONDAS + '<span style="color:#86efac">Escuchando</span>',
    pensando: PUNTOS + '<span style="color:#fcd34d">Pensando</span>',
    enviando: PUNTOS + '<span style="color:#fcd34d">Pensando</span>',
    hablando: '<span style="color:#93c5fd">♪ Respondiendo</span>',
    error: '<span style="color:#fca5a5">No te entendí</span>',
    pausa: '<span style="color:#94a3b8">En pausa</span>',
    // 11/11 (Claude): la aduana leyendo un adjunto en local. Antes salia "¡Te oigo!" y parecia que el micro escuchaba.
    leyendo: PUNTOS + '<span style="color:#d8b4fe">Leyendo archivo</span>' };
  let temporizador = null;
  function set(estado, texto) {
    caja.className = 'caja ' + estado + (BOCADILLO[estado] ? ' ver' : '');
    bocadillo.innerHTML = BOCADILLO[estado] || '';
    const c = LUZ[estado] || LUZ.espera; luz.setAttribute('fill', c); halo.setAttribute('fill', c); pecho.setAttribute('fill', c);
    host.title = 'Nova · ' + (texto || estado);
    clearTimeout(temporizador);
    if (estado === 'error') temporizador = setTimeout(() => set('espera'), 4000);
    return estado;
  }
  // colocarse justo encima de "Settings" y esconderse si la barra lateral esta cerrada
  function colocar() {
    const s = [...document.querySelectorAll('div,button,a')].find(e => e.childElementCount <= 2 && (e.innerText || '').trim() === 'Settings');
    if (!s) { host.style.display = 'none'; return; }
    const r = s.getBoundingClientRect();
    if (r.width < 60) { host.style.display = 'none'; return; }
    host.style.display = 'block';
    host.style.left = Math.max(4, r.left + r.width / 2 - 75) + 'px';
    host.style.bottom = Math.max(0, innerHeight - r.top + 4) + 'px';
  }
  colocar(); const int = setInterval(colocar, 1500); addEventListener('resize', colocar);
  window.__novaMascota = { version: VERSION, set, quitar: () => { clearInterval(int); host.remove(); delete window.__novaMascota; } };
  set('espera');
  return 'creada';
})();
