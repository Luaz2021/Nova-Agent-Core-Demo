import { esc, formatBytes, qsa } from "./utils.js";

export function renderProbeView(container, scan, onScanUrl) {
	const {
		http,
		backend,
		pagination,
		related_routes: routes,
		root_name: root,
		root_shape: shape,
		wrapper_key: wrapper,
	} = scan;
	const persistBadge = backend.writes_persist
		? '<span class="badge badge-ok">Escritura persistente</span>'
		: '<span class="badge badge-warn">Solo lectura / Mock</span>';
	const statusBadge = http.status < 400 ? "badge-ok" : "badge-err";
	const hdrRows = Object.entries(http.headers || {});

	const methodsHtml = (http.methods || [])
		.map(
			(m) =>
				`<span class="badge ${m === "GET" || m === "HEAD" ? "badge-ok" : "badge-pk"}">${esc(m)}</span>`,
		)
		.join("");

	const routesHtml = routes?.length
		? routes
				.map(
					(r) =>
						`<button type="button" class="btn btn-ghost btn-sm route-jump" data-url="${esc(r.url)}">${esc(r.url)} (${esc(r.status)})</button>`,
				)
				.join("")
		: '<span class="muted">No se detectaron rutas hijas automáticas (/id o /categories).</span>';

	const headerTable = hdrRows.length
		? hdrRows
				.map(
					([k, v]) =>
						`<tr><td class="mono">${esc(k)}</td><td class="mono">${esc(v)}</td></tr>`,
				)
				.join("")
		: '<tr><td colspan="2" class="muted">Sin cabeceras registradas.</td></tr>';

	container.innerHTML = `
    <div class="stack">
      <div class="card">
        <div class="verdict-head">
          <div>
            <h2 class="section-title">${esc(backend.label)}</h2>
            <p class="muted" style="margin:0">${esc(backend.summary)}</p>
          </div>
          ${persistBadge}
        </div>
        <div class="pill-wrap">
          <span class="badge badge-null">Forma raíz: ${esc(shape)}</span>
          <span class="badge badge-null">Entidad: ${esc(root)}</span>
          ${wrapper ? `<span class="badge badge-null">Wrapper: ${esc(wrapper)}</span>` : ""}
          <span class="badge badge-null">CORS: ${esc(http.cors_origin)}</span>
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card"><div class="kpi-label">Estado HTTP</div><div class="kpi-val"><span class="badge ${statusBadge}">${esc(http.status)}</span></div></div>
        <div class="kpi-card"><div class="kpi-label">Latencia</div><div class="kpi-val">${esc(http.latency_ms)} ms</div></div>
        <div class="kpi-card"><div class="kpi-label">Registros</div><div class="kpi-val">${esc(pagination.scanned)} / ${esc(pagination.total)}</div></div>
        <div class="kpi-card"><div class="kpi-label">Paginación</div><div class="kpi-val">${pagination.detected ? `Sí (${esc(pagination.pages_fetched)} pág.)` : "No"}</div></div>
        <div class="kpi-card"><div class="kpi-label">Tamaño respuesta</div><div class="kpi-val">${esc(formatBytes(http.size_bytes))}</div></div>
      </div>

      <div class="two-col">
        <div class="card">
          <h3 class="section-title">Métodos HTTP detectados</h3>
          <div class="pill-wrap">${methodsHtml}</div>
          <h3 class="section-title" style="margin-top:16px">Rutas relacionadas explorables</h3>
          <div class="pill-wrap">${routesHtml}</div>
        </div>
        <div class="card">
          <h3 class="section-title">Cabeceras de respuesta (${hdrRows.length})</h3>
          <div class="table-wrap" style="max-height:240px">
            <table class="data-table"><thead><tr><th>Cabecera</th><th>Valor</th></tr></thead><tbody>${headerTable}</tbody></table>
          </div>
        </div>
      </div>
    </div>`;

	for (const btn of qsa(".route-jump", container)) {
		btn.addEventListener("click", () => onScanUrl(btn.dataset.url));
	}
}
