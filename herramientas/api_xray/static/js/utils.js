const ESC_MAP = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	'"': "&quot;",
	"'": "&#39;",
};

export function esc(value) {
	return String(value ?? "").replace(/[&<>"']/g, (ch) => ESC_MAP[ch]);
}

export function qs(selector, root = document) {
	return root.querySelector(selector);
}

export function qsa(selector, root = document) {
	return [...root.querySelectorAll(selector)];
}

export function formatBytes(bytes) {
	const num = Number(bytes || 0);
	if (num < 1024) return `${num} B`;
	if (num < 1024 * 1024) return `${(num / 1024).toFixed(1)} KB`;
	return `${(num / (1024 * 1024)).toFixed(2)} MB`;
}

let toastTimer = null;

export function showToast(message) {
	const el = qs("#toast");
	if (!el) return;
	el.textContent = message;
	el.classList.remove("hidden");
	clearTimeout(toastTimer);
	toastTimer = setTimeout(() => el.classList.add("hidden"), 2600);
}

export async function copyText(text) {
	try {
		await navigator.clipboard.writeText(text);
		showToast("Copiado al portapapeles.");
	} catch {
		const area = document.createElement("textarea");
		area.value = text;
		area.style.position = "fixed";
		area.style.opacity = "0";
		document.body.appendChild(area);
		area.select();
		document.execCommand("copy");
		area.remove();
		showToast("Copiado al portapapeles.");
	}
}
