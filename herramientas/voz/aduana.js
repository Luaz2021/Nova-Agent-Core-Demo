// NOVA · ADUANA DE ADJUNTOS dentro de Antigravity (la inyecta nova_voz.py por CDP, igual que la mascota). 09/11/2026, Claude.
// Lo que el usuario pega, arrastra o elige con el boton de adjuntar (PDF, imagenes, Word, Excel...) NO entra al chat:
// se le pasa a Python (binding novaAduana), que lo guarda en temporal\ y lo lee EN LOCAL (InternVL / destilador).
// En el chat aparece "[adjunto local: <archivo>]" y el hook de turno le da a Nova el texto ya leido -> 0 tokens de nube.
// - Manteniendo SHIFT al pegar/soltar/elegir, pasa como siempre (por si Gemini tiene que ver el original).
// - Si Python no da senales de vida (latido de menos de 10 s), la aduana NO intercepta: nunca se pierde un archivo.
(() => {
  if (window.__novaAduana) return 'ya';
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

  addEventListener('paste', e => interceptar(e, e.clipboardData && e.clipboardData.files, 'pegar'), true);
  addEventListener('drop', e => interceptar(e, e.dataTransfer && e.dataTransfer.files, 'arrastrar'), true);
  addEventListener('change', e => {
    const t = e.target;
    if (t && t.tagName === 'INPUT' && t.type === 'file' && interceptar(e, t.files, 'boton')) t.value = '';
  }, true);

  window.__novaAduana = { version: 1, ultimo: null };
  return 'creada';
})();
