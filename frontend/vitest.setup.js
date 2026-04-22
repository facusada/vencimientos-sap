import { afterEach, vi } from "vitest";

if (!URL.createObjectURL) {
  URL.createObjectURL = () => "blob:mock";
}

if (!URL.revokeObjectURL) {
  URL.revokeObjectURL = () => {};
}

afterEach(() => {
  vi.restoreAllMocks();
});
