// Parse a notebook source blob into cells based on `# %% [id=<uuid>] code|markdown`
// delimiter lines. Mirrors the server-side parser in api/app/services/tech_lab/lab/cell_parser.py.
//
// Returns an array of:
//   { cellId, type, delimiterLine, sourceStartLine, sourceEndLine, source }
// Line numbers are 1-indexed (Monaco convention). For cells whose delimiter is
// missing an `[id=...]`, we fabricate a uuid (callers can rewrite the source
// to bake it in for stable round-trips).

const DELIMITER_RE =
  /^#\s*%%(?:\s*\[id=([0-9a-fA-F-]+)\])?(?:\s+(code|markdown))?\s*(.*)$/;

function uuid() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function parseCells(source) {
  if (!source) return [];
  const lines = source.split("\n");
  const cells = [];
  let curId = null;
  let curType = "code";
  let curBody = [];
  let curDelimLine = 0;
  let curStart = 1;

  function flush(endLine) {
    if (curId == null && curBody.length === 0) return;
    cells.push({
      cellId: curId || uuid(),
      type: curType,
      delimiterLine: curDelimLine,
      sourceStartLine: curStart,
      sourceEndLine: endLine,
      source: curBody.join("\n"),
    });
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = line.match(DELIMITER_RE);
    if (m) {
      // Close out the previous cell.
      flush(i); // endLine = line before delimiter (1-indexed: i lines processed → i)
      curId = m[1] || null;
      curType = m[2] || "code";
      curBody = [];
      curDelimLine = i + 1;
      curStart = i + 2; // body starts on the next line
      continue;
    }
    curBody.push(line);
  }
  flush(lines.length);
  return cells;
}

// Locate the cell containing a given Monaco line number. Returns the cell
// object or null when the cursor sits on a delimiter line / before any cell.
export function findCellAtLine(cells, lineNumber) {
  for (const c of cells) {
    if (lineNumber >= c.sourceStartLine && lineNumber <= c.sourceEndLine) {
      return c;
    }
    if (lineNumber === c.delimiterLine) return c;
  }
  return null;
}
