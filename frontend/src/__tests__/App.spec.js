import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App.vue";

vi.mock("../lib/dashboardWorkbook.js", () => ({
  parseDashboardWorkbook: vi.fn(),
}));
vi.mock("../lib/workbookMerge.js", () => ({
  mergeWorkbookFiles: vi.fn(),
}));

const { parseDashboardWorkbook } = await import("../lib/dashboardWorkbook.js");
const { mergeWorkbookFiles } = await import("../lib/workbookMerge.js");

describe("App consolidated upload flow", () => {
  let createObjectUrlSpy;
  let revokeObjectUrlSpy;
  let appendChildSpy;
  let removeChildSpy;
  let anchorClickSpy;
  const currentPeriod = `${new Date().getFullYear()}-${String(new Date().getMonth() + 1).padStart(2, "0")}`;

  async function selectFiles(wrapper, files) {
    const input = wrapper.get("input[type='file']");
    Object.defineProperty(input.element, "files", {
      value: files,
      configurable: true,
    });
    await input.trigger("change");
  }

  async function setClientForFile(wrapper, filename, clientName) {
    await wrapper.get(`[aria-label='Cliente para ${filename}']`).setValue(clientName);
  }

  beforeEach(() => {
    vi.clearAllMocks();
    createObjectUrlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:ewa");
    revokeObjectUrlSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    appendChildSpy = vi.spyOn(document.body, "appendChild").mockImplementation(() => {});
    removeChildSpy = vi.spyOn(document.body, "removeChild").mockImplementation(() => {});
    anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  it("renders export mode by default and exposes dashboard navigation", () => {
    const wrapper = mount(App);

    expect(wrapper.get("[aria-label='Vista Exportar']").attributes("aria-pressed")).toBe("true");
    expect(wrapper.get("[aria-label='Vista Graficos']").attributes("aria-pressed")).toBe("false");
    expect(wrapper.get("[aria-label='Vista Merge']").attributes("aria-pressed")).toBe("false");
    expect(wrapper.text()).toContain("Unifica EWAs. Exporta la base.");
    expect(wrapper.text()).toContain("Generar Excel");
  });

  it("shows an empty state in merge before selecting workbooks", async () => {
    const wrapper = mount(App);
    await wrapper.get("[aria-label='Vista Merge']").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Todavia no cargaste excels para mergear");
    expect(wrapper.text()).toContain("Subi al menos 2 archivos");
    expect(wrapper.get("button[type='button'][aria-label='Generar merge']").attributes("disabled")).toBeDefined();
  });

  it("merges selected workbooks and downloads the resulting file", async () => {
    mergeWorkbookFiles.mockResolvedValue({
      blob: new Blob(["xlsx"]),
      filename: "ewa-merged.xlsx",
      workbookCount: 2,
      mergedRowCount: 5,
    });

    const wrapper = mount(App);
    await wrapper.get("[aria-label='Vista Merge']").trigger("click");
    await flushPromises();

    const mergeInput = wrapper.get("input[type='file'][accept='.xlsx'][multiple]");
    Object.defineProperty(mergeInput.element, "files", {
      value: [
        new File(["a"], "ACES_vencimientos_Mayo_2026.xlsx", {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
        new File(["b"], "MRP_vencimientos_Mayo_2026.xlsx", {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      ],
      configurable: true,
    });
    await mergeInput.trigger("change");
    await flushPromises();

    await wrapper.get("button[type='button'][aria-label='Generar merge']").trigger("click");
    await flushPromises();

    expect(mergeWorkbookFiles).toHaveBeenCalledTimes(1);
    expect(mergeWorkbookFiles.mock.calls[0][0].map((file) => file.name)).toEqual([
      "ACES_vencimientos_Mayo_2026.xlsx",
      "MRP_vencimientos_Mayo_2026.xlsx",
    ]);
    expect(anchorClickSpy).toHaveBeenCalledOnce();
    expect(createObjectUrlSpy).toHaveBeenCalledOnce();
    expect(revokeObjectUrlSpy).toHaveBeenCalledWith("blob:ewa");
    expect(wrapper.text()).toContain("Merge listo");
    expect(wrapper.text()).toContain("2 excels");
  });

  it("shows an empty state in dashboard before loading any excel or remote data", async () => {
    const fetchSpy = vi.spyOn(window, "fetch");

    const wrapper = mount(App);
    await wrapper.get("[aria-label='Vista Graficos']").trigger("click");
    await flushPromises();

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Todavia no cargaste un Excel");
    expect(wrapper.text()).toContain("Subi un consolidado");
    expect(wrapper.text()).not.toContain("Clientes monitoreados");
  });

  it("loads demo data when the endpoint is unavailable after a manual refresh", async () => {
    vi.spyOn(window, "fetch").mockRejectedValue(new Error("network down"));

    const wrapper = mount(App);
    await wrapper.get("[aria-label='Vista Graficos']").trigger("click");
    await wrapper.get("button[type='button'][aria-label='Actualizar graficos']").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Vencimientos en foco.");
    expect(wrapper.text()).toContain("Clientes monitoreados");
    expect(wrapper.text()).toContain("Mostrando datos demo");
    expect(wrapper.text()).toContain("Supervielle");
  });

  it("loads dashboard data from the configured endpoint for the selected period", async () => {
    const buildDashboardResponse = () =>
      new Response(
        JSON.stringify({
          period: "2026-08",
          source: "api",
          summary: {
            totalClients: 4,
            totalExpirations: 9,
            expiringIn90Days: 3,
            uniqueComponents: 5,
          },
          expirationsByMonth: [
            { month: "2026-08", count: 2 },
            { month: "2026-09", count: 7 },
          ],
          expirationsByComponent: [
            { component: "SAP ERP", count: 4 },
            { component: "SAP PI", count: 3 },
          ],
          clientsAtRisk: [
            { client: "Acme", expirations: 5, nextExpiration: "2026-08-19" },
          ],
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      );

    const fetchSpy = vi.spyOn(window, "fetch").mockResolvedValueOnce(buildDashboardResponse());

    const wrapper = mount(App);
    await wrapper.get("[aria-label='Vista Graficos']").trigger("click");
    await wrapper.get("input[type='month']").setValue("2026-08");
    await wrapper.get("button[type='button'][aria-label='Actualizar graficos']").trigger("click");
    await flushPromises();

    expect(fetchSpy).toHaveBeenNthCalledWith(1, "/api/ewa/dashboard?period=2026-08", {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });
    expect(wrapper.text()).toContain("Datos sincronizados");
    expect(wrapper.text()).toContain("Acme");
    expect(wrapper.text()).toContain("9");
  });

  it("loads dashboard data from a local Excel file and prioritizes it over demo data", async () => {
    vi.spyOn(window, "fetch").mockRejectedValue(new Error("network down"));
    parseDashboardWorkbook.mockResolvedValue({
      period: "2026-05",
      source: "workbook",
      summary: {
        totalClients: 1,
        totalExpirations: 2,
        expiringIn90Days: 1,
        uniqueComponents: 2,
      },
      expirationsByMonth: [
        { month: "2026-05", count: 1 },
        { month: "2026-06", count: 1 },
      ],
      expirationsByComponent: [
        { component: "SAP ERP", count: 1 },
        { component: "SAP FIORI", count: 1 },
      ],
      clientsAtRisk: [
        { client: "MRP", expirations: 2, nextExpiration: "2026-05-14" },
      ],
    });

    const wrapper = mount(App);
    await wrapper.get("[aria-label='Vista Graficos']").trigger("click");
    await flushPromises();

    const workbookInput = wrapper.get("input[type='file'][accept='.xlsx']");
    Object.defineProperty(workbookInput.element, "files", {
      value: [
        new File(["excel"], "MRP_vencimientos_Mayo_2026.xlsx", {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
      ],
      configurable: true,
    });
    await workbookInput.trigger("change");
    await flushPromises();

    expect(parseDashboardWorkbook).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Datos cargados desde Excel local");
    expect(wrapper.text()).toContain("MRP");
    expect(wrapper.text()).toContain("2");
  });

  it("keeps submit disabled until each EWA has one client", async () => {
    const wrapper = mount(App);
    await selectFiles(wrapper, [
      new File(["a"], "a.pdf", { type: "application/pdf" }),
      new File(["b"], "b.pdf", { type: "application/pdf" }),
    ]);
    await setClientForFile(wrapper, "a.pdf", "Cliente A");

    expect(wrapper.get("button[type='submit']").attributes("disabled")).toBeDefined();

    await setClientForFile(wrapper, "b.pdf", "Cliente B");

    expect(wrapper.get("button[type='submit']").attributes("disabled")).toBeUndefined();
  });

  it("shows a validation message for unsupported files", async () => {
    const wrapper = mount(App);
    await selectFiles(wrapper, [new File(["bad"], "ewa.csv", { type: "text/csv" })]);

    expect(wrapper.text()).toContain("Solo se admiten archivos .pdf.");
  });

  it("posts multiple EWAs with clients and period for the consolidated workbook", async () => {
    const fetchSpy = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(new Blob(["xlsx"]), {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="ewa-consolidated.xlsx"',
        },
      }),
    );

    const wrapper = mount(App);
    await selectFiles(wrapper, [
      new File(["a"], "a.pdf", { type: "application/pdf" }),
      new File(["b"], "b.pdf", { type: "application/pdf" }),
    ]);
    await setClientForFile(wrapper, "a.pdf", "Cliente A");
    await setClientForFile(wrapper, "b.pdf", "Cliente B");

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/ewa/consolidate",
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      }),
    );

    const body = fetchSpy.mock.calls[0][1].body;
    expect(body.get("period")).toBe(currentPeriod);
    expect(body.getAll("clients")).toEqual(["Cliente A", "Cliente B"]);
    expect(body.getAll("files").map((file) => file.name)).toEqual(["a.pdf", "b.pdf"]);
    expect(anchorClickSpy).toHaveBeenCalledOnce();
    expect(createObjectUrlSpy).toHaveBeenCalledOnce();
    expect(revokeObjectUrlSpy).toHaveBeenCalledWith("blob:ewa");
    expect(appendChildSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Consolidado mensual generado. El Excel ya esta listo.");
  });

  it("shows the assigned client next to each uploaded EWA", async () => {
    const wrapper = mount(App);
    await selectFiles(wrapper, [
      new File(["a"], "a.pdf", { type: "application/pdf" }),
      new File(["b"], "b.pdf", { type: "application/pdf" }),
    ]);
    await setClientForFile(wrapper, "a.pdf", "Cliente A");
    await setClientForFile(wrapper, "b.pdf", "Cliente B");

    const fileItems = wrapper.findAll(".file-list li");

    expect(fileItems[0].text()).toContain("a.pdf");
    expect(wrapper.get("[aria-label='Cliente para a.pdf']").element.value).toBe("Cliente A");
    expect(fileItems[1].text()).toContain("b.pdf");
    expect(wrapper.get("[aria-label='Cliente para b.pdf']").element.value).toBe("Cliente B");
  });

  it("shows a warning when a consolidated EWA has no expiration results", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(new Blob(["xlsx"]), {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="ewa-consolidated.xlsx"',
          "X-EWA-No-Results": JSON.stringify([
            {
              client: "Aces",
              filename: "EWA_PS4_Travel_Abril-2026.pdf",
              reason: "Sin vencimientos detectados",
            },
          ]),
        },
      }),
    );

    const wrapper = mount(App);
    await selectFiles(wrapper, [
      new File(["a"], "diarco.pdf", { type: "application/pdf" }),
      new File(["b"], "EWA_PS4_Travel_Abril-2026.pdf", { type: "application/pdf" }),
    ]);
    await setClientForFile(wrapper, "diarco.pdf", "Diarco");
    await setClientForFile(wrapper, "EWA_PS4_Travel_Abril-2026.pdf", "Aces");

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("Consolidado mensual generado. Sin vencimientos detectados en: Aces (EWA_PS4_Travel_Abril-2026.pdf).");
    expect(wrapper.get(".message").classes()).toContain("message--warning");
  });

  it("adds EWAs incrementally instead of replacing the previous selection", async () => {
    const fetchSpy = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(new Blob(["xlsx"]), {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="ewa-consolidated.xlsx"',
        },
      }),
    );

    const wrapper = mount(App);
    await selectFiles(wrapper, [new File(["a"], "a.pdf", { type: "application/pdf" })]);

    expect(wrapper.text()).toContain("1 EWA seleccionado");

    await selectFiles(wrapper, [new File(["b"], "b.pdf", { type: "application/pdf" })]);
    await setClientForFile(wrapper, "a.pdf", "Cliente A");
    await setClientForFile(wrapper, "b.pdf", "Cliente B");

    expect(wrapper.text()).toContain("2 EWAs seleccionados");
    expect(wrapper.text()).toContain("a.pdf");
    expect(wrapper.text()).toContain("b.pdf");

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    const body = fetchSpy.mock.calls[0][1].body;
    expect(body.getAll("files").map((file) => file.name)).toEqual(["a.pdf", "b.pdf"]);
  });

  it("removes one uploaded EWA from the list before submitting", async () => {
    const fetchSpy = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(new Blob(["xlsx"]), {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="ewa-consolidated.xlsx"',
        },
      }),
    );

    const wrapper = mount(App);
    await selectFiles(wrapper, [
      new File(["a"], "a.pdf", { type: "application/pdf" }),
      new File(["b"], "b.pdf", { type: "application/pdf" }),
    ]);

    await wrapper.get("[aria-label='Eliminar a.pdf']").trigger("click");
    await setClientForFile(wrapper, "b.pdf", "Cliente B");

    expect(wrapper.text()).not.toContain("a.pdf");
    expect(wrapper.text()).toContain("1 EWA seleccionado");

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    const body = fetchSpy.mock.calls[0][1].body;
    expect(body.getAll("files").map((file) => file.name)).toEqual(["b.pdf"]);
    expect(body.getAll("clients")).toEqual(["Cliente B"]);
  });

  it("renders backend error detail when the request fails", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "PDF does not contain extractable text" }), {
        status: 400,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    const wrapper = mount(App);
    await selectFiles(wrapper, [new File(["ewa"], "ewa.pdf", { type: "application/pdf" })]);
    await setClientForFile(wrapper, "ewa.pdf", "Cliente A");

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("PDF does not contain extractable text");
  });

  it("uses the configured API base URL when provided", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "/backend");
    const fetchSpy = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(new Blob(["xlsx"]), {
        status: 200,
        headers: {
          "Content-Disposition": 'attachment; filename="ewa-consolidated.xlsx"',
        },
      }),
    );

    const wrapper = mount(App);
    await selectFiles(wrapper, [new File(["ewa"], "ewa.pdf", { type: "application/pdf" })]);
    await setClientForFile(wrapper, "ewa.pdf", "Cliente A");

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(fetchSpy).toHaveBeenCalledWith(
      "/backend/ewa/consolidate",
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      }),
    );
  });
});
