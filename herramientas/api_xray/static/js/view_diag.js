import { esc, qs } from "./utils.js";

export function renderDiagView(container, scan) {
	const { alerts, quality_matrix: matrix } = scan.diagnostics;
	const sevBadge = { alta: "badge-err", media: "badge-warn", info: "badge-pk" };

	const alertsHtml = alerts.length
		? alerts
				.map(
					(a) => `
        <div class="alert-item sev-${esc(a.severity)}">
          <div class="verdict-head" style="margin-bottom:4px">
            <strong>${esc(a.title)}</strong>
            <span class="badge ${sevBadge[a.severity] || "badge-null"}">${esc(a.severity.toUpperCase())}</span>
          </div>
          <div class="muted">${esc(a.detail)}</div>
        </div>`,
				)
				.join("")
		: '<div class="card muted">Sin incidencias detectadas en los campos analizados.</div>';

	const matrixRows = matrix
		.map(
			(m) => `
    <tr>
      <td class="mono">${esc(m.table)}</td>
      <td class="mono">${esc(m.column)}</td>
      <td>${m.role === "PK" ? '<span class="badge badge-pk">PK</span>' : m.role === "FK" ? '<span class="badge badge-fk">FK</span>' : "-"}</td>
      <td class="mono">${esc(m.type)}</td>
      <td>${m.nullable ? '<span class="badge badge-warn">NULL</span>' : '<span class="badge badge-ok">NOT NULL</span>'}</td>
      <td class="mono">${esc(m.fill_pct)}%</td>
      <td class="mono">${esc(m.max_length)}</td>
      <td class="mono">${esc(m.format)}</td>
    </tr>`,
		)
		.join("");

	container.innerHTML = `
    <div class="stack">
      <div class="card">
        <h2 class="section-title">Exportar esquema y base de datos</h2>
        <div class="export-grid">
          <div class="export-card">
            <div><strong>Base SQLite (.sqlite)</strong><p class="muted" style="margin:4px 0 0;font-size:12.5px">Lista para abrir en DBeaver con tablas y claves foráneas reales.</p></div>
            <a class="btn btn-primary" href="/api/export/sqlite">Descargar .sqlite</a>
          </div>
          <div class="export-card">
            <div><strong>Script SQL (CREATE TABLE)</strong><p class="muted" style="margin:4px 0 0;font-size:12.5px">Elige motor destino y descarga el script DDL completo.</p></div>
            <div class="toolbar-group">
              <select id="diag-sql-dialect"><option value="sqlite">SQLite</option><option value="mysql">MySQL</option><option value="postgres">PostgreSQL</option></select>
              <a id="diag-sql-link" class="btn btn-ghost" href="/api/export/sql?dialect=sqlite">Descargar .sql</a>
            </div>
          </div>
          <div class="export-card">
            <div><strong>Informe técnico (.md)</strong><p class="muted" style="margin:4px 0 0;font-size:12.5px">Documentación en Markdown con diagnóstico y modelo.</p></div>
            <a class="btn btn-ghost" href="/api/export/report">Descargar .md</a>
          </div>
          <div class="export-card">
            <div><strong>Datos completos (.json)</strong><p class="muted" style="margin:4px 0 0;font-size:12.5px">Volcado limpio de los ${esc(scan.pagination.scanned)} registros escaneados.</p></div>
            <a class="btn btn-ghost" href="/api/export/json">Descargar .json</a>
          </div>
        </div>
      </div>

      <div class="card">
        <h2 class="section-title">Diagnóstico y trampas detectadas (${alerts.length})</h2>
        <div class="alert-list">${alertsHtml}</div>
      </div>

      <div class="card">
        <h2 class="section-title">Matriz de calidad por columna (${matrix.length})</h2>
        <div class="table-wrap" style="max-height:420px">
          <table class="data-table">
            <thead><tr><th>Tabla</th><th>Columna</th><th>Rol</th><th>Tipo</th><th>Nulidad</th><th>Relleno</th><th>Long. máx</th><th>Formato</th></tr></thead>
            <tbody>${matrixRows}</tbody>
          </table>
        </div>
      </div>
    </div>`;

	qs("#diag-sql-dialect", container)?.addEventListener("change", (e) => {
		const link = qs("#diag-sql-link", container);
		if (link)
			link.href = `/api/export/sql?dialect=${encodeURIComponent(e.target.value)}`;
	});
}
