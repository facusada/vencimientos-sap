import * as XLSX from "xlsx";

import { getCurrentPeriod, isValidPeriod } from "./api.js";

const REQUIRED_COLUMNS = ["Cliente", "Componente", "FechaVencimiento"];

export async function parseDashboardWorkbook(file, selectedPeriod = getCurrentPeriod()) {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheet = workbook.Sheets.Base;

  if (!sheet) {
    throw new Error("El Excel debe incluir una hoja Base.");
  }

  const rows = XLSX.utils.sheet_to_json(sheet, {
    defval: "",
    raw: false,
  });

  const firstRow = rows[0] ?? {};
  const missingColumns = REQUIRED_COLUMNS.filter((column) => !(column in firstRow));
  if (missingColumns.length) {
    throw new Error(`Faltan columnas requeridas en Base: ${missingColumns.join(", ")}.`);
  }

  const records = rows
    .map((row) => normalizeWorkbookRow(row))
    .filter(Boolean);

  const period = isValidPeriod(selectedPeriod) ? selectedPeriod : getCurrentPeriod();
  return buildWorkbookSnapshot(records, period);
}

function normalizeWorkbookRow(row) {
  const client = String(row.Cliente ?? "").trim();
  const component = String(row.Componente ?? "").trim();
  const expirationDate = normalizeDate(row.FechaVencimiento);

  if (!client || !component || !expirationDate) {
    return null;
  }

  return {
    client,
    component,
    expirationDate,
  };
}

function normalizeDate(value) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return "";
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    return raw;
  }

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function buildWorkbookSnapshot(records, period) {
  const uniqueClients = new Set(records.map((record) => record.client));
  const uniqueComponents = new Set(records.map((record) => record.component));
  const cutoff = build90DayCutoff(period);

  return {
    period,
    source: "workbook",
    summary: {
      totalClients: uniqueClients.size,
      totalExpirations: records.length,
      expiringIn90Days: records.filter((record) => record.expirationDate <= cutoff).length,
      uniqueComponents: uniqueComponents.size,
    },
    expirationsByMonth: aggregateByMonth(records),
    expirationsByComponent: aggregateByComponent(records),
    clientsAtRisk: aggregateClientsAtRisk(records),
  };
}

function build90DayCutoff(period) {
  const [year, month] = period.split("-").map(Number);
  const baseDate = new Date(year, month - 1, 1);
  baseDate.setDate(baseDate.getDate() + 90);
  const normalizedMonth = String(baseDate.getMonth() + 1).padStart(2, "0");
  const normalizedDay = String(baseDate.getDate()).padStart(2, "0");
  return `${baseDate.getFullYear()}-${normalizedMonth}-${normalizedDay}`;
}

function aggregateByMonth(records) {
  const counts = new Map();

  records.forEach((record) => {
    const month = record.expirationDate.slice(0, 7);
    counts.set(month, (counts.get(month) ?? 0) + 1);
  });

  return [...counts.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([month, count]) => ({ month, count }));
}

function aggregateByComponent(records) {
  const counts = new Map();

  records.forEach((record) => {
    counts.set(record.component, (counts.get(record.component) ?? 0) + 1);
  });

  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([component, count]) => ({ component, count }));
}

function aggregateClientsAtRisk(records) {
  const grouped = new Map();

  records.forEach((record) => {
    const current = grouped.get(record.client) ?? {
      client: record.client,
      expirations: 0,
      nextExpiration: record.expirationDate,
    };
    current.expirations += 1;
    if (record.expirationDate < current.nextExpiration) {
      current.nextExpiration = record.expirationDate;
    }
    grouped.set(record.client, current);
  });

  return [...grouped.values()].sort(
    (left, right) =>
      right.expirations - left.expirations ||
      left.nextExpiration.localeCompare(right.nextExpiration) ||
      left.client.localeCompare(right.client),
  );
}
