import ExcelJS from "exceljs";
import * as XLSX from "xlsx";

const BASE_SHEET_NAME = "Base";
const BASE_COLUMNS = ["Cliente", "Componente", "FechaVencimiento"];
const BODY_FONT_COLOR = "001C1B18";
const HEADER_FONT_COLOR = "001C1B18";
const EXPIRED_FILL_COLOR = "00F6E7A1";
const ACTIVE_FILL_COLOR = "00CFE8C6";

export async function mergeWorkbookFiles(files) {
  if (!Array.isArray(files) || files.length < 2) {
    throw new Error("Selecciona al menos 2 excels para mergear.");
  }

  const mergedRows = [];

  for (const file of files) {
    mergedRows.push(...(await extractWorkbookRows(file)));
  }

  const bytes = await buildMergedWorkbookBytes(mergedRows);
  const blob = new Blob([bytes], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });

  if (typeof blob.arrayBuffer !== "function") {
    blob.arrayBuffer = async () =>
      bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  }

  return {
    blob,
    filename: "ewa-merged.xlsx",
    workbookCount: files.length,
    mergedRowCount: mergedRows.length,
  };
}

async function buildMergedWorkbookBytes(rows) {
  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet(BASE_SHEET_NAME);

  sheet.addRow(BASE_COLUMNS);
  sheet.getRow(1).eachCell({ includeEmpty: true }, (headerCell) => {
    headerCell.font = {
      bold: true,
      color: { argb: HEADER_FONT_COLOR },
    };
  });

  rows.forEach((row) => {
    const nextRow = sheet.addRow(BASE_COLUMNS.map((column) => row[column]));
    applyStatusStyle(nextRow, row.FechaVencimiento);
  });

  const payload = await workbook.xlsx.writeBuffer();
  return payload instanceof Uint8Array ? payload : new Uint8Array(payload);
}

function applyStatusStyle(row, expirationDate) {
  const fillColor = resolveFillColor(expirationDate);

  row.eachCell({ includeEmpty: true }, (cell) => {
    cell.fill = {
      type: "pattern",
      pattern: "solid",
      fgColor: { argb: fillColor },
    };
    cell.font = {
      color: { argb: BODY_FONT_COLOR },
    };
  });
}

function resolveFillColor(expirationDate) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(expirationDate ?? ""))) {
    return ACTIVE_FILL_COLOR;
  }

  const today = new Date();
  const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(
    today.getDate(),
  ).padStart(2, "0")}`;

  return expirationDate < todayIso ? EXPIRED_FILL_COLOR : ACTIVE_FILL_COLOR;
}

async function extractWorkbookRows(file) {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheet = workbook.Sheets[BASE_SHEET_NAME];

  if (!sheet) {
    throw new Error(`El archivo ${file.name} debe incluir la hoja Base.`);
  }

  const rows = XLSX.utils.sheet_to_json(sheet, {
    defval: "",
    raw: false,
  });

  const firstRow = rows[0] ?? {};
  const missingColumns = BASE_COLUMNS.filter((column) => !(column in firstRow));
  if (missingColumns.length) {
    throw new Error(
      `El archivo ${file.name} debe incluir las columnas requeridas: ${BASE_COLUMNS.join(", ")}.`,
    );
  }

  return rows
    .map((row) => ({
      Cliente: String(row.Cliente ?? "").trim(),
      Componente: String(row.Componente ?? "").trim(),
      FechaVencimiento: String(row.FechaVencimiento ?? "").trim(),
    }))
    .filter((row) => Object.values(row).some(Boolean));
}
