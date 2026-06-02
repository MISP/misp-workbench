// Build a standalone, print-ready HTML document that mirrors what the
// OutputPanel shows — rendered markdown plus each code cell's outputs — and
// hand it to the browser's print dialog so the user can "Save as PDF".
//
// We deliberately re-render to a self-contained document (inlined CSS, no
// Bootstrap, fixed light palette) rather than printing the live DOM: the
// output panel is often hidden (code-only view) or unmounted, and a print
// window gives a clean, theme-independent page.

import { marked } from "marked";
import DOMPurify from "dompurify";
import { parseCells } from "./cellDelimiterParser";

const ANSI_RE = /\x1B\[[0-9;]*[A-Za-z]/g;

function stripAnsi(text) {
  return String(text || "").replace(ANSI_RE, "");
}

function escapeHtml(text) {
  return String(text == null ? "" : text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function renderMarkdown(source) {
  return DOMPurify.sanitize(marked.parse(source || "", { breaks: true }));
}

function previewLine(source) {
  const firstNonEmpty = (source || "")
    .split("\n")
    .map((l) => l.trim())
    .find((l) => l.length > 0);
  if (!firstNonEmpty) return "(empty)";
  return firstNonEmpty.length > 80
    ? firstNonEmpty.slice(0, 80) + "…"
    : firstNonEmpty;
}

function formatDuration(ms) {
  if (ms == null) return "";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 2 : 1)} s`;
  const minutes = Math.floor(seconds / 60);
  const rem = seconds - minutes * 60;
  return `${minutes}m ${rem.toFixed(0)}s`;
}

function jsonPretty(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function pickRichMime(data) {
  if (!data) return null;
  for (const mime of [
    "text/html",
    "image/svg+xml",
    "image/png",
    "image/jpeg",
    "application/json",
    "text/plain",
  ]) {
    if (mime in data) return mime;
  }
  return null;
}

// Mirror CellOutput.vue → an HTML string for a single output item.
function renderOutputItem(item) {
  if (item.output_type === "stream") {
    const cls =
      item.name === "stderr"
        ? "cell-output-stream is-stderr"
        : "cell-output-stream";
    return `<pre class="${cls}">${escapeHtml(stripAnsi(item.text))}</pre>`;
  }
  if (item.output_type === "error") {
    const text = Array.isArray(item.traceback)
      ? item.traceback.map(stripAnsi).join("\n")
      : `${item.ename || "Error"}: ${item.evalue || ""}`;
    return `<pre class="cell-output-error">${escapeHtml(text)}</pre>`;
  }
  if (
    item.output_type === "execute_result" ||
    item.output_type === "display_data"
  ) {
    const mime = pickRichMime(item.data);
    switch (mime) {
      case "text/html":
        return `<div class="cell-output-html">${DOMPurify.sanitize(
          String(item.data["text/html"] || ""),
        )}</div>`;
      case "image/svg+xml":
        return `<div class="cell-output-svg">${DOMPurify.sanitize(
          String(item.data["image/svg+xml"] || ""),
        )}</div>`;
      case "image/png":
        return `<img class="cell-output-image" src="data:image/png;base64,${item.data["image/png"]}" />`;
      case "image/jpeg":
        return `<img class="cell-output-image" src="data:image/jpeg;base64,${item.data["image/jpeg"]}" />`;
      case "application/json":
        return `<pre class="cell-output-stream">${escapeHtml(
          jsonPretty(item.data["application/json"]),
        )}</pre>`;
      default:
        return `<pre class="cell-output-stream">${escapeHtml(
          item.data && item.data["text/plain"],
        )}</pre>`;
    }
  }
  return `<pre class="cell-output-stream">${escapeHtml(jsonPretty(item))}</pre>`;
}

function renderCellBlock(cell, idx, outputs, meta) {
  if (cell.type === "markdown") {
    return `<div class="markdown-body">${renderMarkdown(cell.source)}</div>`;
  }

  const outputsHtml = outputs.map(renderOutputItem).join("");

  let footer = "";
  if (meta) {
    let status = "";
    if (meta.status === "error") {
      status = `<span class="status-error">error</span>`;
    } else if (meta.status === "interrupted") {
      status = `<span class="status-interrupted">interrupted</span>`;
    }
    footer = `<div class="output-block-footer">${status}<span class="muted">took ${formatDuration(
      meta.durationMs,
    )}</span></div>`;
  }

  return `<div class="output-block">
    <div class="output-block-header">
      <span class="badge">${idx + 1}</span>
      <code>${escapeHtml(previewLine(cell.source))}</code>
    </div>
    <div class="cell-output">${outputsHtml}</div>
    ${footer}
  </div>`;
}

const PRINT_CSS = `
  * { box-sizing: border-box; }
  body {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    color: #212529;
    background: #fff;
    margin: 0;
    padding: 24px 32px;
    font-size: 14px;
  }
  h1.nb-title { font-size: 1.6rem; margin: 0 0 4px; }
  .nb-subtitle { color: #6c757d; font-size: 0.8rem; margin-bottom: 20px; }
  .markdown-body { font-size: 0.9rem; margin: 12px 0; }
  .markdown-body h1 { font-size: 1.4rem; margin: 0.4rem 0; }
  .markdown-body h2 { font-size: 1.2rem; margin: 0.4rem 0; }
  .markdown-body h3 { font-size: 1.05rem; margin: 0.4rem 0; }
  .markdown-body p { margin: 0.3rem 0; }
  .markdown-body ul, .markdown-body ol { margin: 0.3rem 0; padding-left: 1.4rem; }
  .markdown-body code {
    background: #f1f3f5; padding: 0 4px; border-radius: 3px;
    font-family: ui-monospace, Menlo, Monaco, Consolas, monospace;
  }
  .markdown-body pre {
    background: #f1f3f5; border: 1px solid #dee2e6; padding: 6px 10px;
    border-radius: 4px; overflow-x: auto;
  }
  .markdown-body pre code { background: transparent; padding: 0; }
  .markdown-body blockquote {
    border-left: 3px solid #dee2e6; color: #6c757d; margin: 0.4rem 0;
    padding: 0.1rem 0.8rem;
  }
  .markdown-body table { border-collapse: collapse; font-size: 0.8125rem; }
  .markdown-body th, .markdown-body td { border: 1px solid #dee2e6; padding: 4px 8px; }
  .output-block {
    border: 1px solid #dee2e6; border-radius: 4px; margin: 12px 0;
    overflow: hidden; page-break-inside: avoid;
  }
  .output-block-header {
    background: #f8f9fa; display: flex; align-items: center; gap: 8px;
    padding: 4px 8px; font-size: 0.75rem; border-bottom: 1px solid #dee2e6;
  }
  .output-block-header .badge {
    background: #6c757d; color: #fff; border-radius: 4px; padding: 1px 6px;
    font-size: 0.7rem;
  }
  .output-block-header code {
    font-family: ui-monospace, Menlo, Monaco, Consolas, monospace;
    color: #495057;
  }
  .cell-output {
    padding: 6px 12px; background: #f8f9fa; border-left: 3px solid #e9ecef;
    font-size: 0.875rem;
  }
  .cell-output-stream, .cell-output-error {
    margin: 0; white-space: pre-wrap; word-break: break-word;
    font-family: ui-monospace, Menlo, Monaco, Consolas, monospace;
    font-size: 0.8125rem;
  }
  .cell-output-stream.is-stderr, .cell-output-error { color: #dc3545; }
  .cell-output-image { max-width: 100%; height: auto; }
  .cell-output-html table { font-size: 0.8125rem; border-collapse: collapse; }
  .cell-output-html th, .cell-output-html td { border: 1px solid #dee2e6; padding: 4px 8px; }
  .output-block-footer {
    background: #f8f9fa; border-top: 1px solid #dee2e6; padding: 4px 8px;
    font-size: 0.75rem;
  }
  .output-block-footer .status-error { color: #dc3545; margin-right: 8px; }
  .output-block-footer .status-interrupted { color: #ffc107; margin-right: 8px; }
  .output-block-footer .muted { color: #6c757d; }
  @media print { body { padding: 0; } }
`;

/**
 * Open a print window for the notebook and trigger the browser print dialog
 * (which offers "Save as PDF"). Mirrors OutputPanel: rendered markdown cells
 * and code cells that have outputs or execution timing.
 *
 * @param {{name?: string}} notebook
 * @param {string} source       Current notebook source (cell-delimited).
 * @param {Object} cellOutputs  cellId → array of nbformat outputs.
 * @param {Object} cellMeta     cellId → { status, durationMs }.
 */
export function exportNotebookPdf(notebook, source, cellOutputs, cellMeta) {
  const cells = parseCells(source);
  const blocks = cells
    .map((cell, idx) => ({
      cell,
      idx,
      outputs: cellOutputs?.[cell.cellId] || [],
      meta: cellMeta?.[cell.cellId] || null,
    }))
    .filter((c) => c.cell.type === "markdown" || c.outputs.length > 0 || c.meta)
    .map((c) => renderCellBlock(c.cell, c.idx, c.outputs, c.meta))
    .join("\n");

  const title = notebook?.name || "notebook";
  const exportedAt = new Date().toLocaleString();
  const body =
    blocks ||
    `<p class="nb-subtitle">No rendered content — this notebook has no markdown or cell outputs.</p>`;

  const doc = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(title)}</title>
  <style>${PRINT_CSS}</style>
</head>
<body>
  <h1 class="nb-title">${escapeHtml(title)}</h1>
  <div class="nb-subtitle">Exported ${escapeHtml(exportedAt)}</div>
  ${body}
</body>
</html>`;

  const win = window.open("", "_blank");
  if (!win) {
    throw new Error("Popup blocked — allow popups to export as PDF.");
  }
  win.document.open();
  win.document.write(doc);
  win.document.close();

  // Wait for any embedded images (base64 plots) to decode before printing so
  // they aren't dropped from the rendered page.
  const triggerPrint = () => {
    win.focus();
    win.print();
  };
  const imgs = Array.from(win.document.images || []);
  const pending = imgs.filter((img) => !img.complete);
  if (pending.length === 0) {
    // Defer one tick so layout settles.
    win.setTimeout(triggerPrint, 50);
  } else {
    let remaining = pending.length;
    const done = () => {
      remaining -= 1;
      if (remaining <= 0) win.setTimeout(triggerPrint, 50);
    };
    pending.forEach((img) => {
      img.addEventListener("load", done);
      img.addEventListener("error", done);
    });
  }
}
