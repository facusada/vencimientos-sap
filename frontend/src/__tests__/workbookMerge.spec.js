import { describe, expect, it } from "vitest";
import ExcelJS from "exceljs";
import * as XLSX from "xlsx";

import { mergeWorkbookFiles } from "../lib/workbookMerge.js";

describe("workbookMerge", () => {
  it("merges Base rows from multiple workbooks and returns a downloadable workbook", async () => {
    const firstWorkbook = buildWorkbook([
      { Cliente: "ACES", Componente: "SQL SERVER 2012", FechaVencimiento: "2022-07-12" },
      { Cliente: "ACES", Componente: "Windows Server 2012 R2", FechaVencimiento: "2023-10-10" },
    ]);
    const secondWorkbook = buildWorkbook([
      { Cliente: "MRP", Componente: "SAP ACCESS CONTROL 12.0", FechaVencimiento: "2027-12-31" },
    ]);

    const result = await mergeWorkbookFiles([firstWorkbook, secondWorkbook]);
    const mergedBuffer = await result.blob.arrayBuffer();
    const workbook = XLSX.read(mergedBuffer, { type: "array" });
    const sheet = XLSX.utils.sheet_to_json(workbook.Sheets.Base, { defval: "", raw: false });

    expect(result.filename).toBe("ewa-merged.xlsx");
    expect(result.workbookCount).toBe(2);
    expect(result.mergedRowCount).toBe(3);
    expect(sheet).toEqual([
      { Cliente: "ACES", Componente: "SQL SERVER 2012", FechaVencimiento: "2022-07-12" },
      { Cliente: "ACES", Componente: "Windows Server 2012 R2", FechaVencimiento: "2023-10-10" },
      { Cliente: "MRP", Componente: "SAP ACCESS CONTROL 12.0", FechaVencimiento: "2027-12-31" },
    ]);

    const styledWorkbook = new ExcelJS.Workbook();
    await styledWorkbook.xlsx.load(mergedBuffer);
    const baseSheet = styledWorkbook.getWorksheet("Base");

    expect(baseSheet.getCell("A2").fill.fgColor.argb).toBe("00F6E7A1");
    expect(baseSheet.getCell("B2").fill.fgColor.argb).toBe("00F6E7A1");
    expect(baseSheet.getCell("C2").fill.fgColor.argb).toBe("00F6E7A1");
    expect(baseSheet.getCell("A4").fill.fgColor.argb).toBe("00CFE8C6");
    expect(baseSheet.getCell("B4").fill.fgColor.argb).toBe("00CFE8C6");
    expect(baseSheet.getCell("C4").fill.fgColor.argb).toBe("00CFE8C6");
  });
});

function buildWorkbook(rows) {
  const workbook = XLSX.utils.book_new();
  const sheet = XLSX.utils.json_to_sheet(rows);
  XLSX.utils.book_append_sheet(workbook, sheet, "Base");
  const arrayBuffer = XLSX.write(workbook, { type: "array", bookType: "xlsx" });
  const file = new Blob([arrayBuffer], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  file.name = `${rows[0].Cliente}.xlsx`;
  file.arrayBuffer = async () => arrayBuffer;
  return file;
}
