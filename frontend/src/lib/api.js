export function buildApiUrl(path) {
  const rawBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";
  const normalizedBaseUrl = rawBaseUrl.endsWith("/")
    ? rawBaseUrl.slice(0, -1)
    : rawBaseUrl;

  return `${normalizedBaseUrl}${path}`;
}

export function getCurrentPeriod() {
  const today = new Date();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  return `${today.getFullYear()}-${month}`;
}

export function isValidPeriod(value) {
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(value);
}

export function getFilename(contentDisposition, fallbackFilename = "ewa-expirations.xlsx") {
  const match = contentDisposition?.match(/filename="?([^"]+)"?/i);
  return match?.[1] ?? fallbackFilename;
}

export async function extractErrorMessage(response) {
  const contentType = response.headers.get("Content-Type") ?? "";

  if (contentType.includes("application/json")) {
    const payload = await response.json();
    if (payload?.detail) {
      return payload.detail;
    }
  }

  const fallbackText = await response.text();
  return fallbackText || "No se pudo completar el analisis.";
}
