import { copyText, esc, qs, qsa } from "./utils.js";

export function renderErView(container, scan) {
	const { model, ddl } = scan;
	const positions = Object.fromEntries(
		model.tables.map((t) => [t.name, { x: t.x, y: t.y }]),
	);
	const state = {
		selected: model.root_table,
		dialect: "sqlite",
		scope: "table",
		scale: 1,
		panX: 12,
		panY: 12,
	};

	const tableCardHtml = (tbl) => {
		const pos = positions[tbl.name];
		const colsHtml = tbl.columns
			.map((c) => {
				const badge = c.pk
					? '<span class="badge badge-pk">PK</span>'
					: c.fk_target
						? '<span class="badge badge-fk">FK</span>'
						: "";
				return `<div class="er-col-row"><span class="er-col-left">${badge}<span>${esc(c.name)}</span></span><span class="er-col-type">${esc(c.primary_type)}${c.nullable ? "?" : ""}</span></div>`;
			})
			.join("");
		return `<div class="er-node ${tbl.name === state.selected ? "active-node" : ""}" data-table="${esc(tbl.name)}" style="left:${pos.x}px;top:${pos.y}px"><div class="er-node-head"><span class="er-node-title">${esc(tbl.name)}</span><span class="badge badge-null">${esc(tbl.role)} · ${tbl.row_count}</span></div><div class="er-node-cols">${colsHtml}</div></div>`;
	};

	container.innerHTML = `
    <div class="er-workspace">
      <div class="er-canvas-card">
        <div class="er-toolbar">
          <div class="toolbar-group"><span class="mono">Diagrama ER (${model.tables.length} tablas · ${model.relations.length} relaciones)</span></div>
          <div class="toolbar-group">
            <button type="button" id="er-zoom-out" class="btn btn-ghost btn-sm">-</button>
            <button type="button" id="er-zoom-in" class="btn btn-ghost btn-sm">+</button>
            <button type="button" id="er-fit" class="btn btn-ghost btn-sm">Ajustar</button>
            <button type="button" id="er-reset" class="btn btn-ghost btn-sm">Reordenar</button>
          </div>
        </div>
        <div id="er-viewport" class="er-viewport">
          <div id="er-stage" class="er-stage">
            <svg id="er-edges" class="er-edges"></svg>
            ${model.tables.map(tableCardHtml).join("")}
          </div>
        </div>
      </div>
      <aside id="er-inspector" class="er-inspector card"></aside>
    </div>`;

	const viewport = qs("#er-viewport", container);
	const stage = qs("#er-stage", container);
	const svg = qs("#er-edges", container);
	const inspector = qs("#er-inspector", container);

	const applyTransform = () => {
		stage.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.scale})`;
	};

	const drawEdges = () => {
		const nodes = Object.fromEntries(
			qsa(".er-node", stage).map((el) => [el.dataset.table, el]),
		);
		const paths = model.relations
			.map((rel) => {
				const parent = nodes[rel.to_table];
				const child = nodes[rel.from_table];
				if (!parent || !child) return "";
				const pLeft = parent.offsetLeft,
					pW = parent.offsetWidth || 290,
					pY = parent.offsetTop + 42;
				const cLeft = child.offsetLeft,
					cW = child.offsetWidth || 290,
					cY = child.offsetTop + 42;
				const sameCol = Math.abs(pLeft - cLeft) < pW - 20;
				const rightToLeft = pLeft + pW <= cLeft;
				const x1 = sameCol ? pLeft + pW : rightToLeft ? pLeft + pW : pLeft;
				const x2 = sameCol
					? cLeft + cW
					: rightToLeft
						? cLeft
						: cLeft + cW <= pLeft
							? cLeft + cW
							: cLeft;
				const dx = sameCol ? 58 : Math.max(Math.abs(x2 - x1) * 0.45, 50);
				const c1x = sameCol || rightToLeft ? x1 + dx : x1 - dx;
				const c2x = sameCol
					? x2 + dx
					: rightToLeft
						? x2 - dx
						: cLeft + cW <= pLeft
							? x2 + dx
							: x2 - dx;
				const mx = sameCol ? Math.max(x1, x2) + 42 : (x1 + x2) / 2;
				const my = (pY + cY) / 2;
				const stroke = rel.cardinality === "1:1" ? "#3b82f6" : "#f59e0b";
				return `<path d="M ${x1} ${pY} C ${c1x} ${pY}, ${c2x} ${cY}, ${x2} ${cY}" fill="none" stroke="${stroke}" stroke-width="2" marker-end="url(#er-arrow)"/><rect x="${mx - 16}" y="${my - 10}" width="32" height="18" rx="4" fill="#12161f" stroke="${stroke}"/><text x="${mx}" y="${my + 3}" text-anchor="middle" fill="#e6edf3" font-size="10" font-family="monospace">${esc(rel.cardinality)}</text>`;
			})
			.join("");
		svg.innerHTML = `<defs><marker id="er-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 1 L 10 5 L 0 9 z" fill="#94a3b8"/></marker></defs>${paths}`;
	};

	const renderInspector = () => {
		const tbl =
			model.tables.find((t) => t.name === state.selected) || model.tables[0];
		const tableSql =
			(ddl[state.dialect] || "")
				.split("\n\n")
				.find(
					(b) => b.includes(`"${tbl.name}"`) || b.includes(`\`${tbl.name}\``),
				) || ddl[state.dialect];
		const shownSql = state.scope === "all" ? ddl[state.dialect] : tableSql;
		const colRows = tbl.columns
			.map(
				(c) =>
					`<tr><td class="mono">${esc(c.name)}</td><td class="mono">${esc(c.primary_type)}</td><td>${c.nullable ? "NULL" : "NOT NULL"}</td><td>${esc(c.fill_pct)}%</td></tr>`,
			)
			.join("");
		inspector.innerHTML = `
      <div class="verdict-head"><h3 class="section-title" style="margin:0">${esc(tbl.name)}</h3><span class="badge badge-pk">${esc(tbl.role)} · ${tbl.row_count} filas</span></div>
      <div class="table-wrap" style="max-height:190px"><table class="data-table"><thead><tr><th>Columna</th><th>Tipo</th><th>Nulo</th><th>Lleno</th></tr></thead><tbody>${colRows}</tbody></table></div>
      <div class="toolbar">
        <select id="er-dialect"><option value="sqlite" ${state.dialect === "sqlite" ? "selected" : ""}>SQLite</option><option value="mysql" ${state.dialect === "mysql" ? "selected" : ""}>MySQL</option><option value="postgres" ${state.dialect === "postgres" ? "selected" : ""}>PostgreSQL</option></select>
        <button type="button" id="er-scope" class="btn btn-ghost btn-sm">${state.scope === "table" ? "Solo tabla" : "Todo SQL"}</button>
        <button type="button" id="er-copy" class="btn btn-primary btn-sm">Copiar SQL</button>
      </div>
      <pre class="sql-box">${esc(shownSql)}</pre>`;
		qs("#er-dialect", inspector)?.addEventListener("change", (e) => {
			state.dialect = e.target.value;
			renderInspector();
		});
		qs("#er-scope", inspector)?.addEventListener("click", () => {
			state.scope = state.scope === "table" ? "all" : "table";
			renderInspector();
		});
		qs("#er-copy", inspector)?.addEventListener("click", () =>
			copyText(shownSql),
		);
	};

	const fitDiagram = () => {
		const nodes = qsa(".er-node", stage);
		if (!nodes.length || !viewport.clientWidth) return;
		const maxX =
			Math.max(...nodes.map((n) => n.offsetLeft + n.offsetWidth)) + 48;
		const maxY =
			Math.max(...nodes.map((n) => n.offsetTop + n.offsetHeight)) + 48;
		state.scale = Math.max(
			0.45,
			Math.min(
				1,
				Math.min(viewport.clientWidth / maxX, viewport.clientHeight / maxY),
			),
		);
		state.panX = 12;
		state.panY = 12;
		applyTransform();
	};

	for (const node of qsa(".er-node", stage)) {
		node.addEventListener("pointerdown", (ev) => {
			if (
				ev.target.closest(".er-node-cols") &&
				!ev.target.closest(".er-node-head")
			)
				return;
			ev.stopPropagation();
			state.selected = node.dataset.table;
			for (const n of qsa(".er-node", stage))
				n.classList.toggle("active-node", n === node);
			renderInspector();
			const startX = ev.clientX,
				startY = ev.clientY,
				orig = { ...positions[state.selected] };
			const onMove = (m) => {
				positions[state.selected] = {
					x: Math.max(10, orig.x + (m.clientX - startX) / state.scale),
					y: Math.max(10, orig.y + (m.clientY - startY) / state.scale),
				};
				node.style.left = `${positions[state.selected].x}px`;
				node.style.top = `${positions[state.selected].y}px`;
				drawEdges();
			};
			const onUp = () => {
				window.removeEventListener("pointermove", onMove);
				window.removeEventListener("pointerup", onUp);
			};
			window.addEventListener("pointermove", onMove);
			window.addEventListener("pointerup", onUp);
		});
		node.addEventListener("click", () => {
			state.selected = node.dataset.table;
			for (const n of qsa(".er-node", stage))
				n.classList.toggle("active-node", n === node);
			renderInspector();
		});
	}

	viewport.addEventListener("pointerdown", (ev) => {
		if (ev.target.closest(".er-node")) return;
		const sx = ev.clientX - state.panX,
			sy = ev.clientY - state.panY;
		const onMove = (m) => {
			state.panX = m.clientX - sx;
			state.panY = m.clientY - sy;
			applyTransform();
		};
		const onUp = () => {
			window.removeEventListener("pointermove", onMove);
			window.removeEventListener("pointerup", onUp);
		};
		window.addEventListener("pointermove", onMove);
		window.addEventListener("pointerup", onUp);
	});

	qs("#er-zoom-in", container)?.addEventListener("click", () => {
		state.scale = Math.min(1.5, +(state.scale + 0.12).toFixed(2));
		applyTransform();
	});
	qs("#er-zoom-out", container)?.addEventListener("click", () => {
		state.scale = Math.max(0.35, +(state.scale - 0.12).toFixed(2));
		applyTransform();
	});
	qs("#er-fit", container)?.addEventListener("click", () => {
		fitDiagram();
		drawEdges();
	});
	qs("#er-reset", container)?.addEventListener("click", () => {
		for (const t of model.tables) {
			positions[t.name] = { x: t.x, y: t.y };
			const el = qs(`.er-node[data-table="${t.name}"]`, stage);
			if (el) {
				el.style.left = `${t.x}px`;
				el.style.top = `${t.y}px`;
			}
		}
		fitDiagram();
		drawEdges();
	});

	renderInspector();
	requestAnimationFrame(() => {
		fitDiagram();
		drawEdges();
	});
	return () => {
		fitDiagram();
		drawEdges();
	};
}
