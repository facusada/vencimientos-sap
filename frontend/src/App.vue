<script setup>
import { computed, ref } from "vue";

const mode = ref("single");
const selectedFiles = ref([]);
const period = ref(getCurrentPeriod());
const clientNamesByFileKey = ref({});
const errorMessage = ref("");
const successMessage = ref("");
const successMessageTone = ref("success");
const isUploading = ref(false);
const isDragging = ref(false);
const fileInput = ref(null);
const analyzeUrl = buildApiUrl("/ewa/analyze");
const consolidateUrl = buildApiUrl("/ewa/consolidate");

const selectedFile = computed(() => selectedFiles.value[0] ?? null);
const clientEntries = computed(() =>
  selectedFiles.value.map((file) => getClientNameForFile(file)).filter(Boolean),
);
const consolidatedFileRows = computed(() =>
  selectedFiles.value.map((file) => ({
    file,
    client: getClientNameForFile(file),
    key: getFileKey(file),
  })),
);
const canSubmit = computed(() => {
  if (isUploading.value) {
    return false;
  }

  if (mode.value === "single") {
    return Boolean(selectedFile.value);
  }

  return (
    selectedFiles.value.length > 0
    && isValidPeriod(period.value)
    && clientEntries.value.length === selectedFiles.value.length
  );
});
const fileLabel = computed(() => {
  if (!selectedFiles.value.length) {
    return mode.value === "single" ? "Sin archivo seleccionado" : "Sin EWAs seleccionados";
  }

  if (mode.value === "single") {
    return `${selectedFile.value.name} · ${formatBytes(selectedFile.value.size)}`;
  }

  return formatEwaCount(selectedFiles.value.length);
});

function onFileChange(event) {
  applyFiles(Array.from(event.target.files ?? []));
}

function onDrop(event) {
  if (isUploading.value) {
    isDragging.value = false;
    return;
  }

  isDragging.value = false;
  applyFiles(Array.from(event.dataTransfer?.files ?? []));
}

function applyFiles(files) {
  successMessage.value = "";
  successMessageTone.value = "success";

  if (!files.length) {
    return;
  }

  if (files.some((file) => !isSupportedFile(file.name))) {
    selectedFiles.value = [];
    clientNamesByFileKey.value = {};
    errorMessage.value = "Solo se admiten archivos .pdf.";
    if (fileInput.value) {
      fileInput.value.value = "";
    }
    return;
  }

  errorMessage.value = "";
  selectedFiles.value = mode.value === "single" ? [files[0]] : mergeSelectedFiles(files);

  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

async function submitForm() {
  if (!canSubmit.value) {
    validateConsolidatedMetadata();
    return;
  }

  isUploading.value = true;
  errorMessage.value = "";
  successMessage.value = "";
  successMessageTone.value = "success";

  try {
    if (mode.value === "single") {
      await submitSingleAnalysis();
    } else {
      await submitConsolidatedAnalysis();
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "No se pudo completar el analisis.";
  } finally {
    isUploading.value = false;
  }
}

async function submitSingleAnalysis() {
  const formData = new FormData();
  formData.append("file", selectedFile.value);

  const response = await fetch(analyzeUrl, {
    method: "POST",
    body: formData,
  });

  await downloadResponse(response, "ewa-expirations.xlsx");
  successMessage.value = "Analisis completado. El Excel ya esta listo.";
  successMessageTone.value = "success";
}

async function submitConsolidatedAnalysis() {
  validateConsolidatedMetadata();

  const formData = new FormData();
  formData.append("period", period.value);
  selectedFiles.value.forEach((file) => formData.append("files", file));
  clientEntries.value.forEach((client) => formData.append("clients", client));

  const response = await fetch(consolidateUrl, {
    method: "POST",
    body: formData,
  });

  await downloadResponse(response, "ewa-consolidated.xlsx");
  const consolidatedFeedback = buildConsolidatedSuccessMessage(response);
  successMessage.value = consolidatedFeedback.message;
  successMessageTone.value = consolidatedFeedback.tone;
}

async function downloadResponse(response, fallbackFilename) {
  if (!response.ok) {
    throw new Error(await extractErrorMessage(response));
  }

  const blob = await response.blob();
  const filename = getFilename(response.headers.get("Content-Disposition"), fallbackFilename);
  triggerDownload(blob, filename);
}

function validateConsolidatedMetadata() {
  if (mode.value !== "consolidated") {
    return;
  }

  if (!isValidPeriod(period.value)) {
    throw new Error("El periodo debe tener formato YYYY-MM.");
  }

  if (clientEntries.value.length !== selectedFiles.value.length) {
    throw new Error("Carga un cliente por cada EWA seleccionado.");
  }
}

function openFilePicker() {
  if (isUploading.value) {
    return;
  }

  fileInput.value?.click();
}

function updateClientName(file, nextValue) {
  const fileKey = getFileKey(file);
  clientNamesByFileKey.value = {
    ...clientNamesByFileKey.value,
    [fileKey]: nextValue,
  };
}

function getClientNameForFile(file) {
  return (clientNamesByFileKey.value[getFileKey(file)] ?? "").trim();
}

function removeSelectedFile(fileToRemove) {
  if (isUploading.value) {
    return;
  }

  const fileKey = getFileKey(fileToRemove);
  selectedFiles.value = selectedFiles.value.filter((file) => getFileKey(file) !== fileKey);
  const { [fileKey]: _removed, ...rest } = clientNamesByFileKey.value;
  clientNamesByFileKey.value = rest;
  errorMessage.value = "";
  successMessage.value = "";
  successMessageTone.value = "success";

  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

function setMode(nextMode) {
  if (isUploading.value || mode.value === nextMode) {
    return;
  }

  mode.value = nextMode;
  selectedFiles.value = [];
  clientNamesByFileKey.value = {};
  errorMessage.value = "";
  successMessage.value = "";
  successMessageTone.value = "success";
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

function mergeSelectedFiles(files) {
  const merged = [...selectedFiles.value];
  const seen = new Set(merged.map(getFileKey));

  files.forEach((file) => {
    const key = getFileKey(file);
    if (!seen.has(key)) {
      seen.add(key);
      merged.push(file);
    }
  });

  return merged;
}

function getFileKey(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function isSupportedFile(filename) {
  return filename.toLowerCase().endsWith(".pdf");
}

function buildApiUrl(path) {
  const rawBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";
  const normalizedBaseUrl = rawBaseUrl.endsWith("/")
    ? rawBaseUrl.slice(0, -1)
    : rawBaseUrl;

  return `${normalizedBaseUrl}${path}`;
}

function getCurrentPeriod() {
  const today = new Date();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  return `${today.getFullYear()}-${month}`;
}

function isValidPeriod(value) {
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(value);
}

function formatBytes(size) {
  if (!size) {
    return "0 KB";
  }

  const kilobytes = size / 1024;
  if (kilobytes < 1024) {
    return `${kilobytes.toFixed(1)} KB`;
  }

  return `${(kilobytes / 1024).toFixed(1)} MB`;
}

function formatEwaCount(count) {
  return count === 1 ? "1 EWA seleccionado" : `${count} EWAs seleccionados`;
}

async function extractErrorMessage(response) {
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

function buildConsolidatedSuccessMessage(response) {
  const noResultItems = parseNoResultItems(response.headers.get("X-EWA-No-Results"));
  if (!noResultItems.length) {
    return {
      message: "Consolidado mensual generado. El Excel ya esta listo.",
      tone: "success",
    };
  }

  const affectedEwas = noResultItems
    .map((item) => formatNoResultItem(item))
    .join(", ");
  return {
    message: `Consolidado mensual generado. Sin vencimientos detectados en: ${affectedEwas}.`,
    tone: "warning",
  };
}

function parseNoResultItems(rawHeader) {
  if (!rawHeader) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawHeader);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter((item) => item && typeof item === "object");
  } catch {
    return [];
  }
}

function formatNoResultItem(item) {
  const client = String(item.client ?? "Cliente sin nombre").trim();
  const filename = String(item.filename ?? "").trim();

  if (filename) {
    return `${client} (${filename})`;
  }

  return client;
}

function getFilename(contentDisposition, fallbackFilename = "ewa-expirations.xlsx") {
  const match = contentDisposition?.match(/filename="?([^"]+)"?/i);
  return match?.[1] ?? fallbackFilename;
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">SAP EarlyWatch Alert</p>
        <strong class="brand">Vencimientos SAP</strong>
      </div>
      <div class="mode-switch" aria-label="Tipo de exportacion">
        <button
          type="button"
          :class="{ 'mode-switch__button--active': mode === 'single' }"
          :disabled="isUploading"
          class="mode-switch__button"
          @click="setMode('single')"
        >
          Individual
        </button>
        <button
          type="button"
          :class="{ 'mode-switch__button--active': mode === 'consolidated' }"
          :disabled="isUploading"
          class="mode-switch__button"
          @click="setMode('consolidated')"
        >
          Consolidado mensual
        </button>
      </div>
    </header>

    <section class="workspace">
      <div
        class="dropzone"
        :class="{
          'dropzone--active': isDragging,
          'dropzone--ready': selectedFile,
          'dropzone--disabled': isUploading,
        }"
        @dragenter.prevent="!isUploading && (isDragging = true)"
        @dragover.prevent="!isUploading && (isDragging = true)"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <input
          ref="fileInput"
          class="sr-only"
          type="file"
          accept=".pdf"
          :multiple="mode === 'consolidated'"
          :disabled="isUploading"
          @change="onFileChange"
        />

        <div class="dropzone__visual">
          <span class="dropzone__badge">Carga</span>
          <h2>{{ selectedFiles.length ? (mode === "single" ? "Archivo listo" : "Archivos listos") : "Subi tu EWA" }}</h2>
          <p>
            {{ selectedFiles.length ? fileLabel : "Arrastra el documento aca o elegilo manualmente." }}
          </p>

          <div class="dropzone__actions">
            <button
              class="secondary-button"
              type="button"
              :disabled="isUploading"
              @click="openFilePicker"
            >
              {{
                selectedFiles.length
                  ? (mode === "single" ? "Cambiar archivo" : "Agregar EWAs")
                  : (mode === "single" ? "Elegir archivo" : "Elegir EWAs")
              }}
            </button>
            <span class="dropzone__hint">Formato soportado: .pdf</span>
          </div>
          <ul v-if="selectedFiles.length" class="file-list">
            <li v-for="row in consolidatedFileRows" :key="row.key">
              <div class="file-list__meta">
                <span>{{ row.file.name }}</span>
                <input
                  v-if="mode === 'consolidated'"
                  :value="row.client"
                  :disabled="isUploading"
                  :aria-label="`Cliente para ${row.file.name}`"
                  class="file-list__client-input"
                  type="text"
                  placeholder="Cliente"
                  @input="updateClientName(row.file, $event.target.value)"
                />
              </div>
              <div class="file-list__controls">
                <small>{{ formatBytes(row.file.size) }}</small>
                <button
                  class="file-list__remove"
                  type="button"
                  :aria-label="`Eliminar ${row.file.name}`"
                  :disabled="isUploading"
                  title="Eliminar"
                  @click="removeSelectedFile(row.file)"
                >
                  ×
                </button>
              </div>
            </li>
          </ul>
          <p class="dropzone__note">
            Formato soportado: PDF con texto extraible.
          </p>
        </div>
      </div>

      <section class="showcase">
        <p class="showcase__kicker">EWA → IA → Excel</p>
        <h1>{{ mode === "single" ? "Carga el EWA. Descarga el Excel." : "Unifica EWAs. Exporta la base." }}</h1>
        <p class="showcase__text">
          <template v-if="mode === 'single'">
            Un unico paso para transformar el reporte en una planilla simple con
            <code>Seccion</code>, <code>Nombre</code>, <code>Hito</code> y <code>Fecha</code>.
          </template>
          <template v-else>
            Genera un Excel mensual con <code>Base</code>, <code>VistaClientes</code> y componentes no catalogados.
          </template>
        </p>
      </section>

      <aside class="result-card">
        <span class="result-card__label">{{ mode === "single" ? "Salida" : "Consolidado" }}</span>

        <div v-if="mode === 'consolidated'" class="metadata-panel">
          <label class="field">
            <span>Periodo</span>
            <input v-model="period" type="month" :disabled="isUploading" />
          </label>
          <p class="metadata-panel__hint">
            {{ clientEntries.length }} clientes / {{ formatEwaCount(selectedFiles.length) }}
          </p>
        </div>

        <div class="result-card__sheet">
          <div>
            <strong>{{ mode === "single" ? "Seccion" : "Base" }}</strong>
            <span>{{ mode === "single" ? "Bloque del EWA" : "Formato largo para Power BI" }}</span>
          </div>
          <div>
            <strong>{{ mode === "single" ? "Nombre" : "VistaClientes" }}</strong>
            <span>{{ mode === "single" ? "Componente o producto" : "Una fila por cliente" }}</span>
          </div>
          <div>
            <strong>{{ mode === "single" ? "Hito" : "Catalogo" }}</strong>
            <span>{{ mode === "single" ? "Tipo de vencimiento" : "Componentes canonicos" }}</span>
          </div>
          <div>
            <strong>{{ mode === "single" ? "Fecha" : "No catalogados" }}</strong>
            <span>{{ mode === "single" ? "Vencimiento normalizado" : "Insumo para relevar faltantes" }}</span>
          </div>
        </div>
      </aside>
    </section>

    <form class="action-bar" @submit.prevent="submitForm">
      <div class="action-bar__messages">
        <p v-if="errorMessage" class="message message--error">{{ errorMessage }}</p>
        <p v-else-if="successMessage" :class="`message message--${successMessageTone}`">{{ successMessage }}</p>
        <p v-else class="message message--neutral">
          <template v-if="mode === 'single'">
            {{ selectedFile ? "Archivo preparado para ejecutar el analisis." : "Selecciona un archivo para empezar." }}
          </template>
          <template v-else>
            {{ selectedFiles.length ? "Completa un cliente por EWA para generar el consolidado." : "Selecciona los EWAs del periodo mensual." }}
          </template>
        </p>
      </div>

      <button class="primary-button" type="submit" :disabled="!canSubmit">
        <span v-if="isUploading">{{ mode === "single" ? "Analizando..." : "Consolidando..." }}</span>
        <span v-else>{{ mode === "single" ? "Generar Excel" : "Generar consolidado" }}</span>
      </button>
    </form>
  </main>
</template>
