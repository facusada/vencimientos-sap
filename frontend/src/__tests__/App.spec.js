import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App.vue";

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
    createObjectUrlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:ewa");
    revokeObjectUrlSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    appendChildSpy = vi.spyOn(document.body, "appendChild").mockImplementation(() => {});
    removeChildSpy = vi.spyOn(document.body, "removeChild").mockImplementation(() => {});
    anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  it("renders consolidated mode only", () => {
    const wrapper = mount(App);

    expect(wrapper.text()).toContain("Exportar");
    expect(wrapper.text()).not.toContain("Individual");
    expect(wrapper.text()).toContain("Unifica EWAs. Exporta la base.");
    expect(wrapper.text()).toContain("ComponentesNoCatalogados");
    expect(wrapper.text()).toContain("Generar Excel");
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
