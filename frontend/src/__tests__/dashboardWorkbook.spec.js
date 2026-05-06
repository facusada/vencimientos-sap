import { describe, expect, it } from "vitest";
import * as XLSX from "xlsx";

import { parseDashboardWorkbook } from "../lib/dashboardWorkbook.js";

describe("dashboardWorkbook", () => {
  it("builds dashboard aggregates from the Base sheet", async () => {
    const workbook = XLSX.utils.book_new();
    const sheet = XLSX.utils.json_to_sheet([
      {
        Cliente: "MRP",
        Componente: "SAP ERP",
        FechaVencimiento: "2026-05-14",
      },
      {
        Cliente: "MRP",
        Componente: "SAP FIORI",
        FechaVencimiento: "2026-06-30",
      },
      {
        Cliente: "ACME",
        Componente: "SAP ERP",
        FechaVencimiento: "2026-05-21",
      },
    ]);
    XLSX.utils.book_append_sheet(workbook, sheet, "Base");
    const arrayBuffer = XLSX.write(workbook, { type: "array", bookType: "xlsx" });
    const file = new Blob([arrayBuffer], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    file.name = "vencimientos.xlsx";
    file.arrayBuffer = async () => arrayBuffer;

    const snapshot = await parseDashboardWorkbook(file, "2026-05");

    expect(snapshot.source).toBe("workbook");
    expect(snapshot.period).toBe("2026-05");
    expect(snapshot.summary).toEqual({
      totalClients: 2,
      totalExpirations: 3,
      expiringIn90Days: 3,
      uniqueComponents: 2,
    });
    expect(snapshot.expirationsByMonth).toEqual([
      { month: "2026-05", count: 2 },
      { month: "2026-06", count: 1 },
    ]);
    expect(snapshot.expirationsByComponent).toEqual([
      { component: "SAP ERP", count: 2 },
      { component: "SAP FIORI", count: 1 },
    ]);
    expect(snapshot.clientsAtRisk).toEqual([
      { client: "MRP", expirations: 2, nextExpiration: "2026-05-14" },
      { client: "ACME", expirations: 1, nextExpiration: "2026-05-21" },
    ]);
  });
});
