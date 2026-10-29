// runtime_studio.js — Motor Estatico 3D Three.js & Pizarra WebGL (Intocable, 0 tokens)
// Calibrado estrictamente para 1080x1920 (9:16) respetando Safe Zones (Y: 240 a 1520)

const W = 1080, H = 1920;
const SAFE_TOP = 240, SAFE_BOTTOM = 1520, SAFE_LEFT = 35, SAFE_RIGHT = 970;
const STUDIO_CX = -0.10; // Centrado exacto respecto al Safe Zone de Reels

function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
function lerp(a, b, t) { return a + (b - a) * t; }
function smoothstep(a, b, x) {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
}

function drawRoundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y + x, y, r);
  ctx.closePath();
}

function drawStickerBox(ctx, x, y, w, h, r, fill, borderCol, shadowOff, borderW = 4) {
  if (shadowOff > 0) {
    drawRoundRect(ctx, x, y + shadowOff, w, h, r);
    ctx.fillStyle = borderCol;
    ctx.fill();
  }
  drawRoundRect(ctx, x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.lineWidth = borderW;
  ctx.strokeStyle = borderCol;
  ctx.stroke();
}

// 1. LIENZO Y TEXTURA DE PIZARRA
const boardCanvas = document.createElement('canvas');
boardCanvas.width = 1024;
boardCanvas.height = 680;
const bCtx = boardCanvas.getContext('2d');
const boardTexture = new THREE.CanvasTexture(boardCanvas);
boardTexture.minFilter = THREE.LinearFilter;
boardTexture.magFilter = THREE.LinearFilter;

// 2. RENDERIZADOR POR COMPONENTES DECLARATIVOS
function renderBoardWidgets(sceneObj, localT, globalT) {
  const accent = sceneObj.accent || '#38BDF8';
  bCtx.clearRect(0, 0, 1024, 680);

  const grad = bCtx.createLinearGradient(0, 0, 0, 680);
  grad.addColorStop(0, '#10172A');
  grad.addColorStop(1, '#090D18');
  bCtx.fillStyle = grad;
  bCtx.fillRect(0, 0, 1024, 680);

  // Grilla tecnica de fondo
  bCtx.strokeStyle = 'rgba(148, 163, 184, 0.09)';
  bCtx.lineWidth = 2;
  const gOff = (globalT * 28) % 60;
  for (let x = 30; x < 1024; x += 60) {
    bCtx.beginPath(); bCtx.moveTo(x, 58); bCtx.lineTo(x, 680); bCtx.stroke();
  }
  for (let y = 58 + gOff; y < 680; y += 60) {
    bCtx.beginPath(); bCtx.moveTo(0, y); bCtx.lineTo(1024, y); bCtx.stroke();
  }

  // Barra superior tipo ventana OS
  bCtx.fillStyle = '#1B233B';
  bCtx.fillRect(0, 0, 1024, 58);
  bCtx.fillStyle = accent;
  bCtx.fillRect(0, 54, 1024, 4);
  const dots = ['#EF4444', '#F59E0B', '#22C55E'];
  dots.forEach((col, idx) => {
    bCtx.beginPath();
    bCtx.arc(32 + idx * 28, 28, 9, 0, Math.PI * 2);
    bCtx.fillStyle = col;
    bCtx.fill();
  });

  bCtx.font = 'bold 23px Consolas, monospace';
  bCtx.fillStyle = '#E2E8F0';
  bCtx.fillText(`nova://${sceneObj.tag ? sceneObj.tag.toLowerCase().replace(/[^a-z0-9]/g, '-') : 'studio'}`, 128, 36);

  const sid = sceneObj.scene_id || 1;

  if (sid === 1) {
    // Escena 1: Mito vs Arsenal Real
    const p2 = smoothstep(2.4, 3.3, localT);
    drawStickerBox(bCtx, 42, 88, 440, 215, 20, '#2A1621', '#EF4444', 6, 4);
    bCtx.font = '900 27px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#FCA5A5';
    bCtx.fillText('MITO: "SOLO HACE WEBS"', 68, 142);
    bCtx.font = '600 23px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#E2E8F0';
    bCtx.fillText('Chatbots que solo escupen', 68, 192);
    bCtx.fillText('texto sin tocar tu PC.', 68, 228);
    if (p2 > 0.1) {
      bCtx.strokeStyle = '#EF4444';
      bCtx.lineWidth = 8;
      bCtx.beginPath();
      bCtx.moveTo(62, 110);
      bCtx.lineTo(62 + 390 * p2, 110 + 165 * p2);
      bCtx.stroke();
    }

    drawStickerBox(bCtx, 514, 88, 468, 215, 20, '#12263A', '#38BDF8', 6, 4);
    bCtx.font = '900 27px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#FFD66B';
    bCtx.fillText('NOVA AGENT CORE v2.2', 540, 140);
    bCtx.font = '700 23px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#38BDF8';
    bCtx.fillText('Google Gemini + Antigravity IDE', 540, 184);
    bCtx.font = '600 22px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#F8FAFC';
    bCtx.fillText('+125 Skills reales en tu PC', 540, 228);

    drawStickerBox(bCtx, 42, 335, 940, 300, 24, '#151F34', '#FFD66B', 8, 4);
    bCtx.font = '900 32px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#FFFFFF';
    bCtx.fillText('ARSENAL COMPLETO EN ACCION DIRECTA', 76, 394);

    const modules = ['DISEÑO 60FPS', 'VIDEO 3D', 'CIBERSEGURIDAD', 'MEMORIA CLOUD', 'ROBOTICA IoT', 'LEGAL & EXCEL'];
    modules.forEach((m, idx) => {
      const mx = 74 + (idx % 3) * 295;
      const my = 428 + Math.floor(idx / 3) * 86;
      const active = localT > (2.5 + idx * 0.45);
      drawStickerBox(bCtx, mx, my, 272, 64, 14, active ? '#153528' : '#1E293B', active ? '#22C55E' : '#475569', 4, 3);
      bCtx.font = '800 21px Consolas, monospace';
      bCtx.fillStyle = active ? '#4ADE80' : '#94A3B8';
      bCtx.fillText((active ? '[OK] ' : '[..] ') + m, mx + 18, my + 40);
    });
  } else if (sid === 2) {
    // Escena 2: Web Responsiva + Video 3D
    drawStickerBox(bCtx, 40, 86, 452, 550, 22, '#141E33', '#38BDF8', 7, 4);
    bCtx.font = '900 26px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#38BDF8';
    bCtx.fillText('1. WEBS A MEDIDA (60 FPS)', 66, 134);

    const morph = 0.5 + 0.5 * Math.sin(globalT * 2.8);
    const mw = lerp(200, 385, morph);
    const mx = 266 - mw / 2;
    drawStickerBox(bCtx, mx, 160, mw, 355, 18, '#0B1120', '#FFD66B', 5, 3);
    drawRoundRect(bCtx, mx + 16, 182, mw - 32, 90, 10);
    bCtx.fillStyle = '#38BDF8'; bCtx.fill();
    drawRoundRect(bCtx, mx + 16, 288, (mw - 42) / 2, 105, 10);
    bCtx.fillStyle = '#A855F7'; bCtx.fill();
    drawRoundRect(bCtx, mx + 26 + (mw - 42) / 2, 288, (mw - 42) / 2, 105, 10);
    bCtx.fillStyle = '#22C55E'; bCtx.fill();
    drawRoundRect(bCtx, mx + 16, 410, mw - 32, 78, 10);
    bCtx.fillStyle = '#1E293B'; bCtx.fill();

    bCtx.font = '800 22px Consolas, monospace';
    bCtx.fillStyle = '#FFD66B';
    bCtx.fillText(morph > 0.5 ? 'MODO: DESKTOP WIDESCREEN' : 'MODO: MOBILE 9:16 ADAPTATIVO', 68, 582);

    drawStickerBox(bCtx, 522, 86, 462, 550, 22, '#1C1633', '#A855F7', 7, 4);
    bCtx.font = '900 26px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#C084FC';
    bCtx.fillText('2. VIDEO 3D CON CODIGO', 550, 134);

    for (let i = 0; i < 18; i++) {
      const bx = 554 + i * 22;
      const bh = 16 + 52 * Math.abs(Math.sin(globalT * 5.5 + i * 0.45));
      drawRoundRect(bCtx, bx, 238 - bh, 14, bh * 2, 6);
      bCtx.fillStyle = i % 2 === 0 ? '#A855F7' : '#38BDF8';
      bCtx.fill();
    }

    const tracks = [
      ['THREE.JS ESCENA 3D', '#38BDF8', 332],
      ['VOCES NEURALES + LIPSYNC', '#FFD66B', 418],
      ['MASTER FFMPEG 1080x1920', '#22C55E', 504]
    ];
    tracks.forEach(([label, col, ty]) => {
      drawStickerBox(bCtx, 550, ty, 404, 66, 14, '#111827', col, 4, 3);
      bCtx.font = '800 22px Consolas, monospace';
      bCtx.fillStyle = '#F8FAFC';
      bCtx.fillText(label, 572, ty + 41);
    });
  } else if (sid === 3) {
    // Escena 3: 4 Nodos de Ingenieria
    const nodes = [
      { x: 48,  y: 94,  w: 432, h: 250, title: 'SQL & SUPABASE RLS', sub1: 'Indices B-Tree ultra veloces', sub2: 'Politicas Zero-Trust activas', col: '#10B981' },
      { x: 544, y: 94,  w: 432, h: 250, title: 'REDES CISCO & CLOUD', sub1: 'VLANs, OSPF, Docker & Nginx', sub2: 'Enrutamiento empresarial', col: '#38BDF8' },
      { x: 48,  y: 386, w: 432, h: 250, title: 'ESCUDO CIBERSEGURIDAD', sub1: 'Defensa OWASP Top 10', sub2: 'Bloqueo de fugas .env en Git', col: '#FFD66B' },
      { x: 544, y: 386, w: 432, h: 250, title: 'ROBOTICA & CHIPS IoT', sub1: 'Firmware Arduino y ESP32', sub2: 'Sensores y telemetria MQTT', col: '#F97316' }
    ];

    bCtx.strokeStyle = '#334155';
    bCtx.lineWidth = 8;
    bCtx.beginPath();
    bCtx.moveTo(264, 218); bCtx.lineTo(760, 218);
    bCtx.moveTo(264, 510); bCtx.lineTo(760, 510);
    bCtx.moveTo(264, 218); bCtx.lineTo(264, 510);
    bCtx.moveTo(760, 218); bCtx.lineTo(760, 510);
    bCtx.stroke();

    nodes.forEach((n, idx) => {
      const pulse = (Math.floor(localT * 2) % 4) === idx;
      drawStickerBox(bCtx, n.x, n.y, n.w, n.h, 22, '#141E30', n.col, pulse ? 8 : 5, pulse ? 5 : 4);
      bCtx.font = '900 27px Consolas, monospace';
      bCtx.fillStyle = n.col;
      bCtx.fillText(n.title, n.x + 26, n.y + 58);
      bCtx.font = '700 24px "Segoe UI", sans-serif';
      bCtx.fillStyle = '#F8FAFC';
      bCtx.fillText(n.sub1, n.x + 26, n.y + 118);
      bCtx.font = '600 22px "Segoe UI", sans-serif';
      bCtx.fillStyle = '#94A3B8';
      bCtx.fillText(n.sub2, n.x + 26, n.y + 160);

      drawStickerBox(bCtx, n.x + 26, n.y + 184, 180, 42, 10, '#0D2818', '#22C55E', 0, 2.5);
      bCtx.font = '800 19px Consolas, monospace';
      bCtx.fillStyle = '#4ADE80';
      bCtx.fillText('BLINDADO OK', n.x + 44, n.y + 212);
    });
  } else if (sid === 4) {
    // Escena 4: Memoria SHA-256 + Legal y Finanzas
    drawStickerBox(bCtx, 44, 88, 936, 250, 22, '#162038', '#F59E0B', 7, 4);
    bCtx.font = '900 28px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#FFD66B';
    bCtx.fillText('MEMORIA PERSISTENTE BIDIRECCIONAL (SHA-256)', 76, 138);

    const syncBoxes = [
      { x: 76,  label: 'TU PC SOBREMESA', sub: 'Contexto + Codigo', col: '#38BDF8' },
      { x: 392, label: 'PUENTE CLOUD', sub: 'Manifiesto SHA-256', col: '#FFD66B' },
      { x: 708, label: 'TU LAPTOP', sub: 'Sigue al instante', col: '#22C55E' }
    ];
    syncBoxes.forEach((sb) => {
      drawStickerBox(bCtx, sb.x, 166, 240, 140, 18, '#0E1525', sb.col, 5, 3);
      bCtx.font = '800 22px Consolas, monospace';
      bCtx.fillStyle = sb.col;
      bCtx.fillText(sb.label, sb.x + 20, 218);
      bCtx.font = '600 21px "Segoe UI", sans-serif';
      bCtx.fillStyle = '#E2E8F0';
      bCtx.fillText(sb.sub, sb.x + 20, 264);
    });

    drawStickerBox(bCtx, 44, 372, 450, 265, 22, '#191D32', '#38BDF8', 7, 4);
    bCtx.font = '900 27px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#38BDF8';
    bCtx.fillText('CONTRATOS & LEGAL', 74, 428);
    bCtx.font = '600 23px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#F8FAFC';
    bCtx.fillText('• Auditoria MSA, SLA y NDA', 74, 482);
    bCtx.fillText('• Cumplimiento RGPD / Ley 29733', 74, 526);
    bCtx.fillText('• Cero clausulas trampa', 74, 570);

    drawStickerBox(bCtx, 530, 372, 450, 265, 22, '#191D32', '#22C55E', 7, 4);
    bCtx.font = '900 27px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#4ADE80';
    bCtx.fillText('FINANZAS & METRICAS', 560, 428);
    bCtx.font = '600 23px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#F8FAFC';
    bCtx.fillText('• Modelos en Excel (.xlsx)', 560, 482);
    bCtx.fillText('• Calculo LTV, CAC, Churn y ROI', 560, 526);
    bCtx.fillText('• Presupuestos llave en mano', 560, 570);
  } else if (sid === 5) {
    // Escena 5: Sandbox Fantasma
    drawStickerBox(bCtx, 44, 88, 936, 550, 24, '#121D2F', '#06B6D4', 8, 4);
    bCtx.font = '900 30px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#22D3EE';
    bCtx.fillText('PROTOCOLO: CERO EXPERIMENTOS EN VIVO', 80, 146);

    const steps = [
      { y: 178, title: '1. AISLAMIENTO EN RAMA FANTASMA (SANDBOX)', desc: 'Clono el entorno en privado sin tocar tu rama activa.', col: '#38BDF8' },
      { y: 326, title: '2. BATERIA DE TESTS & CHAOS QA AUTOMATICO', desc: 'Si una prueba falla, la descarto en silencio.', col: '#FFD66B' },
      { y: 474, title: '3. ENTREGA VERIFICADA AL 100% [PASS]', desc: 'Solo aplico el codigo cuando todo da verde.', col: '#22C55E' }
    ];
    steps.forEach((st, idx) => {
      const active = localT >= idx * 1.5;
      drawStickerBox(bCtx, 80, st.y, 864, 122, 18, active ? '#0D1626' : '#161F30', st.col, 5, 3);
      bCtx.font = '900 25px Consolas, monospace';
      bCtx.fillStyle = st.col;
      bCtx.fillText(st.title, 108, st.y + 48);
      bCtx.font = '600 23px "Segoe UI", sans-serif';
      bCtx.fillStyle = '#E2E8F0';
      bCtx.fillText(st.desc, 108, st.y + 90);
    });
  } else if (sid === 6) {
    // Escena 6: GitHub Buscador
    drawStickerBox(bCtx, 42, 86, 940, 554, 26, '#0E1726', '#22C55E', 8, 5);
    bCtx.font = '900 27px Consolas, monospace';
    bCtx.fillStyle = '#4ADE80';
    bCtx.textAlign = 'center';
    bCtx.fillText('REPOSITORIO OFICIAL EN GITHUB (OPEN SOURCE)', 512, 142);

    drawStickerBox(bCtx, 74, 168, 876, 114, 20, '#070B12', '#FFD66B', 6, 4);
    const fullRepo = 'Luaz2021/Nova-Agent-Core-Demo';
    const typedCount = Math.min(fullRepo.length, Math.max(10, Math.floor((localT / 3.8) * fullRepo.length)));
    const shownRepo = fullRepo.slice(0, typedCount);
    bCtx.font = '900 42px Consolas, monospace';
    bCtx.fillStyle = '#FFFFFF';
    bCtx.fillText(shownRepo + (Math.floor(globalT * 3) % 2 === 0 ? '_' : ''), 512, 240);

    const pills = [
      ['+125 SKILLS', '#38BDF8', 74],
      ['GOOGLE GEMINI', '#FFD66B', 376],
      ['100% GRATIS', '#22C55E', 678]
    ];
    pills.forEach(([txt, col, px]) => {
      drawStickerBox(bCtx, px, 316, 272, 92, 18, '#162238', col, 5, 3);
      bCtx.font = '900 28px "Segoe UI", sans-serif';
      bCtx.fillStyle = col;
      bCtx.fillText(txt, px + 136, 373);
    });

    drawStickerBox(bCtx, 74, 444, 876, 146, 22, '#C25E3D', '#5E2511', 8, 4);
    bCtx.font = '900 36px "Segoe UI", sans-serif';
    bCtx.fillStyle = '#FFFFFF';
    bCtx.fillText('BUSCALO EN GITHUB Y PRUEBALO HOY', 512, 508);
    bCtx.font = '700 24px Consolas, monospace';
    bCtx.fillStyle = '#FFE6AE';
    bCtx.fillText('github.com/Luaz2021/Nova-Agent-Core-Demo', 512, 556);
    bCtx.textAlign = 'left';
  }

  boardTexture.needsUpdate = true;
}

window.__novaRuntime = {
  W, H, SAFE_TOP, SAFE_BOTTOM, SAFE_LEFT, SAFE_RIGHT, STUDIO_CX,
  drawRoundRect, drawStickerBox, renderBoardWidgets, boardTexture
};
