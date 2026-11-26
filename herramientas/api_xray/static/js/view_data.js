import { esc, qs, qsa } from "./utils.js";

function renderJsonNode(key, value, depth = 0) {
	const keyHtml =
		key !== null ? `<span class="jt-key">"${esc(key)}"</span>: ` : "";
	if (value === null)
		return `<div class="json-leaf">${keyHtml}<span class="jt-null">null</span></div>`;
	if (typeof value === "string")
		return `<div class="json-leaf">${keyHtml}<span class="jt-str">"${esc(value)}"</span></div>`;
	if (typeof value === "number")
		return `<div class="json-leaf">${keyHtml}<span class="jt-num">${esc(value)}</span></div>`;
	if (typeof value === "boolean")
		return `<div class="json-leaf">${keyHtml}<span class="jt-bool">${value}</span></div>`;
	const isArr = Array.isArray(value);
	const entries = isArr
		? value.map((v, i) => [String(i), v])
		: Object.entries(value);
	const openAttr = depth < 1 ? " open" : "";
	const badge = isArr ? `[${entries.length}]` : `{${entries.length}}`;
	const children = entries
		.map(([k, v]) => renderJsonNode(isArr ? null : k, v, depth + 1))
		.join("");
	return `<details${openAttr}><summary>${keyHtml}<span class="muted">${badge}</span></summary>${children}</details>`;
}

function renderRowDetails(scan, tableName, row) {
	const fields = Object.entries(row)
		.map(
			([k, v]) =>
				`<div class="detail-item"><div class="detail-k">${esc(k)}</div><div class="detail-v mono">${v === null || v === undefined ? '<span class="muted">NULL</span>' : esc(v)}</div></div>`,
		)
		.join("");
	const rels = scan.model.relations.filter((r) => r.to_table === tableName);
	const relatedBlocks = rels
		.map((rel) => {
			const pkVal = row[rel.to_column];
			const matches = (scan.model.table_rows[rel.from_table] || []).filter(
				(cr) => cr[rel.from_column] === pkVal,
			);
			if (!matches.length) return "";
			const preview = matches
				.slice(0, 6)
				.map((m) => esc(JSON.stringify(m)))
				.join("<br>");
			return `<div style="margin-top:8px"><span class="badge badge-fk">${esc(rel.from_table)} (${matches.length})</span><div class="mono muted" style="margin-top:4px">${preview}</div></div>`;
		})
		.join("");
	return `<div class="detail-drawer"><h3 class="section-title">Detalle de fila seleccionada</h3><div class="detail-grid">${fields}</div>${relatedBlocks}</div>`;
}

export function renderDataView(container, scan) {
	const { model, records } = scan;
	const state = {
		mode: "table",
		table: model.root_table,
		search: "",
		sortCol: null,
		sortAsc: true,
		limit: 100,
		jsonLimit: 30,
		selectedIdx: null,
	};

	const paint = () => {
		const tblObj =
			model.tables.find((t) => t.name === state.table) || model.tables[0];
		const tableOpts = model.tables
			.map(
				(t) =>
					`<option value="${esc(t.name)}" ${t.name === tblObj.name ? "selected" : ""}>${esc(t.name)} (${t.row_count} filas · ${t.role})</option>`,
			)
			.join("");
		const topBar = `
      <div class="toolbar card">
        <div class="toolbar-group">
          <button type="button" class="btn ${state.mode === "table" ? "btn-primary" : "btn-ghost"}" data-mode="table">Vista Tabla (DBeaver)</button>
          <button type="button" class="btn ${state.mode === "json" ? "btn-primary" : "btn-ghost"}" data-mode="json">Vista Árbol JSON</button>
        </div>
        <div class="toolbar-group">
          ${state.mode === "table" ? `<select id="data-table-select">${tableOpts}</select><input id="data-search" class="input" type="search" placeholder="Filtrar filas..." value="${esc(state.search)}">` : '<button type="button" id="json-expand" class="btn btn-ghost btn-sm">Expandir nivel</button><button type="button" id="json-collapse" class="btn btn-ghost btn-sm">Plegar todo</button>'}
        </div>
      </div>`;

		if (state.mode === "json") {
			const slice = records.slice(0, state.jsonLimit);
			const nodes = slice
				.map((item, idx) => renderJsonNode(`[${idx}]`, item, 0))
				.join("");
			const more =
				records.length > state.jsonLimit
					? `<button type="button" id="json-more" class="btn btn-ghost">Mostrar más (${records.length - state.jsonLimit} restantes)</button>`
					: "";
			container.innerHTML = `<div class="stack">${topBar}<div class="json-tree">${nodes}</div>${more}</div>`;
			bindCommonEvents();
			qs("#json-expand", container)?.addEventListener("click", () => {
				for (const d of qsa(".json-tree details", container)) d.open = true;
			});
			qs("#json-collapse", container)?.addEventListener("click", () => {
				for (const d of qsa(".json-tree details", container)) d.open = false;
			});
			qs("#json-more", container)?.addEventListener("click", () => {
				state.jsonLimit += 50;
				paint();
			});
			return;
		}

		const rawRows = model.table_rows[tblObj.name] || [];
		const term = state.search.trim().toLowerCase();
		const filtered = term
			? rawRows.filter((r) =>
					Object.values(r).some((v) =>
						String(v ?? "")
							.toLowerCase()
							.includes(term),
					),
				)
			: [...rawRows];
		if (state.sortCol) {
			filtered.sort(
				(a, b) =>
					String(a[state.sortCol] ?? "").localeCompare(
						String(b[state.sortCol] ?? ""),
						undefined,
						{ numeric: true },
					) * (state.sortAsc ? 1 : -1),
			);
		}
		const visible = filtered.slice(0, state.limit);
		const cols = tblObj.columns.map((c) => c.name);
		const ths = cols
			.map(
				(c) =>
					`<th data-col="${esc(c)}">${esc(c)}${state.sortCol === c ? (state.sortAsc ? " ▲" : " ▼") : ""}</th>`,
			)
			.join("");
		const trs = visible
			.map(
				(r, i) =>
					`<tr data-row="${i}" class="${state.selectedIdx === i ? "selected-row" : ""}">${cols.map((c) => `<td class="mono" title="${esc(r[c])}">${r[c] === null || r[c] === undefined ? '<span class="muted">NULL</span>' : esc(r[c])}</td>`).join("")}</tr>`,
			)
			.join("");
		const detailHtml =
			state.selectedIdx !== null && visible[state.selectedIdx]
				? renderRowDetails(scan, tblObj.name, visible[state.selectedIdx])
				: "";
		const moreBtn =
			filtered.length > state.limit
				? `<button type="button" id="table-more" class="btn btn-ghost">Ver todas (${filtered.length})</button>`
				: "";

		container.innerHTML = `<div class="stack">${topBar}<div class="muted" style="font-size:12.5px">Mostrando ${visible.length} de ${filtered.length} filas en <strong>${esc(tblObj.name)}</strong>. Haz clic en una fila para inspeccionar detalles y registros hijos.</div><div class="table-wrap" style="max-height:460px"><table class="data-table"><thead><tr>${ths}</tr></thead><tbody>${trs || '<tr><td colspan="99" class="muted">Sin coincidencias.</td></tr>'}</tbody></table></div>${moreBtn}${detailHtml}</div>`;
		bindCommonEvents();
	};

	const bindCommonEvents = () => {
		for (const btn of qsa("[data-mode]", container)) {
			btn.addEventListener("click", () => {
				state.mode = btn.dataset.mode;
				state.selectedIdx = null;
				paint();
			});
		}
		qs("#data-table-select", container)?.addEventListener("change", (e) => {
			state.table = e.target.value;
			state.selectedIdx = null;
			state.sortCol = null;
			paint();
		});
		qs("#data-search", container)?.addEventListener("input", (e) => {
			state.search = e.target.value;
			state.selectedIdx = null;
			paint();
		});
		qs("#table-more", container)?.addEventListener("click", () => {
			state.limit = 2000;
			paint();
		});
		for (const th of qsa(".data-table th[data-col]", container)) {
			th.addEventListener("click", () => {
				const col = th.dataset.col;
				state.sortAsc = state.sortCol === col ? !state.sortAsc : true;
				state.sortCol = col;
				paint();
			});
		}
		for (const tr of qsa(".data-table tbody tr[data-row]", container)) {
			tr.addEventListener("click", () => {
				state.selectedIdx = Number(tr.dataset.row);
				paint();
			});
		}
	};

	paint();
}
