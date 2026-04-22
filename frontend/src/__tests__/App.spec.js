import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App.vue";

describe("App upload flow", () => {
  let createObjectUrlSpy;
  let revokeObjectUrlSpy;
  let appendChildSpy;
  let removeChildSpy;
  let anchorClickSpy;

  async function selectFile(wrapper, file) {
    const input = wrapper.get("input[type='file']");
    Object.defineProperty(input.element, "files", {
      value: [file],
      configurable: true,
    });
    await input.trigger("change");
  }

  beforeEach(() => {
    createObjectUrlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:ewa");
    revokeObjectUrlSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    appendChildSpy = vi.spyOn(document.body, "appendChild").mockImplementation(() => {});
    removeChildSpy = vi.spyOn(document.body, "removeChild").mockImplementation(() => {});
    anchorClickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  it("disables submit until a supported file is selected", async () => {
    const wrapper = mount(App);
    const button = wrapper.get("button[type='submit']");

    expect(button.attributes("disabled")).toBeDefined();

    await selectFile(wrapper, new File(["ewa"], "ewa.pdf", { type: "application/pdf" }));

    expect(button.attributes("disabled")).toBeUndefined();
  });

  it("accepts pdf files in the picker", async () => {
    const wrapper = mount(App);

    await selectFile(wrapper, new File(["ewa"], "ewa.pdf", { type: "application/pdf" }));

    expect(wrapper.text()).toContain("ewa.pdf");
    expect(wrapper.text()).toContain("EWA → IA → Excel");
    expect(wrapper.text()).toContain("Formato soportado: PDF con texto extraible");
  });

  it("shows a validation message for unsupported files", async () => {
    const wrapper = mount(App);
    await selectFile(wrapper, new File(["bad"], "ewa.csv", { type: "text/csv" }));

    expect(wrapper.text()).toContain("Solo se admiten archivos .pdf.");
  });

  it("posts the selected file and triggers the Excel download", async () => {
    let resolveFetch;
    const fetchSpy = vi.spyOn(window, "fetch").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );

    const wrapper = mount(App);
    await selectFile(wrapper, new File(["ewa"], "ewa.pdf", { type: "application/pdf" }));

    await wrapper.get("form").trigger("submit.prevent");

    expect(wrapper.get("button[type='submit']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("button[type='button']").attributes("disabled")).toBeDefined();
    expect(wrapper.get("input[type='file']").attributes("disabled")).toBeDefined();

    resolveFetch(
      new Response(
        new Blob(["xlsx"], {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }),
        {
          status: 200,
          headers: {
            "Content-Disposition": 'attachment; filename="ewa-expirations.xlsx"',
          },
        },
      ),
    );
    await flushPromises();

    expect(fetchSpy).toHaveBeenCalledWith(
      "/ewa/analyze",
      expect.objectContaining({
        method: "POST",
        body: expect.any(FormData),
      }),
    );
    expect(anchorClickSpy).toHaveBeenCalledOnce();
    expect(createObjectUrlSpy).toHaveBeenCalledOnce();
    expect(revokeObjectUrlSpy).toHaveBeenCalledWith("blob:ewa");
    expect(appendChildSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Analisis completado. El Excel ya esta listo.");
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
    await selectFile(wrapper, new File(["ewa"], "ewa.pdf", { type: "application/pdf" }));

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("PDF does not contain extractable text");
  });

  it("shows a clear message when the EWA has no expiration dates", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "No se detectaron fechas de vencimiento en el EWA enviado." }), {
        status: 400,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    const wrapper = mount(App);
    await selectFile(wrapper, new File(["ewa"], "ewa.pdf", { type: "application/pdf" }));

    await wrapper.get("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("No se detectaron fechas de vencimiento en el EWA enviado.");
    expect(anchorClickSpy).not.toHaveBeenCalled();
  });
});
