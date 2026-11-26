import { esc, qs, qsa, showToast } from "./utils.js";
import { renderDataView } from "./view_data.js";
import { renderDiagView } from "./view_diag.js";
import { renderErView } from "./view_er.js";
import { renderProbeView } from "./view_probe.js";

const state = { scan: null, activeTab: "probe", refreshEr: null };

function setStatus(text, isError = false) {
	const strip = qs("#status-strip");
	if (!strip) return;
	strip.textContent = text;
	strip.classList.remove("hidden", "is-err");
	if (isError) strip.classList.add("is-err");
}

function updateHeadersCount() {
	const rows = qsa(".header-row", qs("#headers-list"));
	const active = rows.filter((r) => qs(".hdr-key", r)?.value.trim()).length;
	qs("#headers-count").textContent = String(active);
}

function addHeaderRow(key = "", val = "") {
	const row = document.createElement("div");
	row.className = "header-row";
	row.innerHTML = `<input class="input hdr-key" type="text" placeholder="Authorization" value="${esc(key)}"><input class="input hdr-val" type="text" placeholder="Bearer ..." value="${esc(val)}"><button type="button" class="btn btn-ghost btn-sm hdr-del">Quitar</button>`;
	qs(".hdr-key", row).addEventListener("input", updateHeadersCount);
	qs(".hdr-del", row).addEventListener("click", () => {
		row.remove();
		updateHeadersCount();
	});
	qs("#headers-list").appendChild(row);
	updateHeadersCount();
}

function collectHeaders() {
	const result = {};
	for (const row of qsa(".header-row", qs("#headers-list"))) {
		const k = qs(".hdr-key", row)?.value.trim();
		const v = qs(".hdr-val", row)?.value.trim() || "";
		if (k) result[k] = v;
	}
	return result;
}

function switchTab(tabName) {
	state.activeTab = tabName;
	for (const btn of qsa(".tab-btn")) {
		const on = btn.dataset.tab === tabName;
		btn.classList.toggle("active", on);
		btn.setAttribute("aria-selected", String(on));
	}
	if (!state.scan) return;
	qs("#empty-state")?.classList.add("hidden");
	for (const panel of qsa(".tab-panel")) {
		panel.classList.toggle("hidden", panel.id !== `panel-${tabName}`);
	}
	if (tabName === "er" && typeof state.refreshEr === "function") {
		requestAnimationFrame(() => state.refreshEr());
	}
}

async function runApiScan(urlOverride = null) {
	const input = qs("#url-input");
	const targetUrl = (urlOverride || input.value).trim();
	if (!targetUrl) return;
	input.value = targetUrl;
	const btn = qs("#scan-btn");
	btn.disabled = true;
	btn.textContent = "Escaneando...";
	setStatus(`Consultando ${targetUrl} ...`);
	try {
		const resp = await fetch("/api/scan", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				url: targetUrl,
				headers: collectHeaders(),
				fetch_all: qs("#fetch-all-input").checked,
			}),
		});
		const data = await resp.json();
		if (!resp.ok) throw new Error(data.error || `Error HTTP ${resp.status}`);
		state.scan = data;
		renderProbeView(qs("#panel-probe"), data, runApiScan);
		renderDataView(qs("#panel-data"), data);
		state.refreshEr = renderErView(qs("#panel-er"), data);
		renderDiagView(qs("#panel-diag"), data);
		switchTab(state.activeTab);
		setStatus(
			`OK ${data.http.status} · ${data.backend.label} · ${data.pagination.scanned} registros · ${data.model.tables.length} tablas inferidas (${data.http.latency_ms} ms)`,
		);
	} catch (err) {
		setStatus(err.message || "Error al escanear la API.", true);
		showToast(err.message || "Error al escanear.");
	} finally {
		btn.disabled = false;
		btn.textContent = "Escanear";
	}
}

document.addEventListener("DOMContentLoaded", () => {
	qs("#scan-form")?.addEventListener("submit", (e) => {
		e.preventDefault();
		runApiScan();
	});
	qs("#toggle-headers-btn")?.addEventListener("click", () =>
		qs("#headers-drawer")?.classList.toggle("hidden"),
	);
	qs("#add-header-btn")?.addEventListener("click", () => addHeaderRow());
	for (const btn of qsa(".tab-btn")) {
		btn.addEventListener("click", () => switchTab(btn.dataset.tab));
	}
	for (const btn of qsa(".sample-btn")) {
		btn.addEventListener("click", () => runApiScan(btn.dataset.url));
	}
	const initialUrl = new URLSearchParams(window.location.search).get("url");
	if (initialUrl) runApiScan(initialUrl);
});
