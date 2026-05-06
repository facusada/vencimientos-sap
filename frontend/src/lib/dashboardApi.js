import { buildApiUrl, getCurrentPeriod, isValidPeriod } from "./api.js";

export const dashboardDemoSnapshot = Object.freeze({
  summary: {
    totalClients: 6,
    totalExpirations: 18,
    expiringIn90Days: 5,
    uniqueComponents: 7,
  },
  expirationsByComponent: [
    { component: "SAP ERP", count: 5 },
    { component: "SAP HANA", count: 4 },
    { component: "SAP Solution Manager", count: 3 },
    { component: "SAP PI", count: 2 },
    { component: "SAP BW", count: 2 },
  ],
  clientsAtRisk: [
    { client: "Supervielle", expirations: 4, nextExpiration: "2026-05-21" },
    { client: "Diarco", expirations: 3, nextExpiration: "2026-06-04" },
    { client: "Aces", expirations: 3, nextExpiration: "2026-06-18" },
    { client: "Newsan", expirations: 2, nextExpiration: "2026-07-02" },
  ],
});

export async function fetchDashboardSnapshot(
  period = getCurrentPeriod(),
  { fetchImpl = window.fetch.bind(window) } = {},
) {
  const resolvedPeriod = isValidPeriod(period) ? period : getCurrentPeriod();

  try {
    const response = await fetchImpl(
      buildApiUrl(`/ewa/dashboard?period=${encodeURIComponent(resolvedPeriod)}`),
      {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      },
    );

    if (!response.ok) {
      throw new Error(`Dashboard request failed with status ${response.status}`);
    }

    const payload = await response.json();
    return normalizeDashboardSnapshot(payload, resolvedPeriod);
  } catch {
    return buildDemoSnapshot(resolvedPeriod);
  }
}

function normalizeDashboardSnapshot(payload, resolvedPeriod) {
  if (!payload || typeof payload !== "object") {
    return buildDemoSnapshot(resolvedPeriod);
  }

  const summary = payload.summary ?? {};
  const expirationsByMonth = normalizeCollection(payload.expirationsByMonth, "month", resolvedPeriod);
  const expirationsByComponent = normalizeCollection(
    payload.expirationsByComponent,
    "component",
    "Componente sin nombre",
  );
  const clientsAtRisk = Array.isArray(payload.clientsAtRisk)
    ? payload.clientsAtRisk
        .filter((item) => item && typeof item === "object")
        .map((item) => ({
          client: String(item.client ?? "Cliente sin nombre"),
          expirations: Number(item.expirations ?? 0),
          nextExpiration: String(item.nextExpiration ?? ""),
        }))
    : [];

  return {
    period: String(payload.period ?? resolvedPeriod),
    source: "api",
    summary: {
      totalClients: Number(summary.totalClients ?? 0),
      totalExpirations: Number(summary.totalExpirations ?? 0),
      expiringIn90Days: Number(summary.expiringIn90Days ?? 0),
      uniqueComponents: Number(summary.uniqueComponents ?? 0),
    },
    expirationsByMonth,
    expirationsByComponent,
    clientsAtRisk,
  };
}

function normalizeCollection(collection, labelKey, fallbackLabel) {
  if (!Array.isArray(collection)) {
    return [];
  }

  return collection
    .filter((item) => item && typeof item === "object")
    .map((item) => ({
      [labelKey]: String(item[labelKey] ?? fallbackLabel),
      count: Number(item.count ?? 0),
    }));
}

function buildDemoSnapshot(period) {
  return {
    period,
    source: "demo",
    summary: { ...dashboardDemoSnapshot.summary },
    expirationsByMonth: buildDemoMonthlySeries(period),
    expirationsByComponent: dashboardDemoSnapshot.expirationsByComponent.map((item) => ({ ...item })),
    clientsAtRisk: dashboardDemoSnapshot.clientsAtRisk.map((item) => ({ ...item })),
  };
}

function buildDemoMonthlySeries(period) {
  const [year, month] = period.split("-").map(Number);
  const cursor = new Date(year, month - 1, 1);
  const counts = [3, 5, 2, 4, 3];

  return counts.map((count, index) => {
    const current = new Date(cursor.getFullYear(), cursor.getMonth() + index, 1);
    const label = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, "0")}`;
    return {
      month: label,
      count,
    };
  });
}
