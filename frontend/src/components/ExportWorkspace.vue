<script setup>
import { computed, nextTick, ref } from "vue";

import { buildApiUrl, extractErrorMessage, getCurrentPeriod, getFilename, isValidPeriod } from "../lib/api.js";

const selectedFiles = ref([]);
const period = ref(getCurrentPeriod());
const clientNamesByFileKey = ref({});
const errorMessage = ref("");
const successMessage = ref("");
const successMessageTone = ref("success");
const isUploading = ref(false);
const isDragging = ref(false);
const fileInput = ref(null);
const fileRowRefs = ref({});
const consolidateUrl = buildApiUrl("/ewa/consolidate");

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

  return (
    selectedFiles.value.length > 0 &&
    isValidPeriod(period.value) &&
    clientEntries.value.length === selectedFiles.value.length
  );
});
const fileLabel = computed(() => {
  if (!selectedFiles.value.length) {
    return "Sin EWAs seleccionados";
  }

  return formatEwaCount(selectedFiles.value.length);
});

function onFileChange(event) {
  void applyFiles(Array.from(event.target.files ?? []));
}

function onDrop(event) {
  if (isUploading.value) {
    isDragging.value = false;
    return;
  }

  isDragging.value = false;
  void applyFiles(Array.from(event.dataTransfer?.files ?? []));
}

async function applyFiles(files) {
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
  const nextFiles = mergeSelectedFiles(files);
  const previousKeys = new Set(selectedFiles.value.map(getFileKey));
  selectedFiles.value = nextFiles;

  const addedFiles = nextFiles.filter((file) => !previousKeys.has(getFileKey(file)));

  if (fileInput.value) {
    fileInput.value.value = "";
  }

  const lastAddedFile = addedFiles.at(-1);
  if (lastAddedFile) {
    await nextTick();
    const rowElement = fileRowRefs.value[getFileKey(lastAddedFile)];
    if (typeof rowElement?.scrollIntoView === "function") {
      rowElement.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
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
    await submitConsolidatedAnalysis();
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "No se pudo completar el analisis.";
  } finally {
    isUploading.value = false;
  }
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

function setFileRowRef(key, element) {
  if (element) {
    fileRowRefs.value[key] = element;
    return;
  }

  delete fileRowRefs.value[key];
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
  <section class="workspace">
    <div
      class="dropzone"
      :class="{
        'dropzone--active': isDragging,
        'dropzone--ready': selectedFiles.length > 0,
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
        multiple
        :disabled="isUploading"
        @change="onFileChange"
      />

      <div class="dropzone__visual">
        <span class="dropzone__badge">Carga</span>
        <h2>{{ selectedFiles.length ? "Archivos listos" : "Subi tus EWAs" }}</h2>
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
            {{ selectedFiles.length ? "Agregar EWAs" : "Elegir EWAs" }}
          </button>
          <span class="dropzone__hint">Formato soportado: .pdf</span>
        </div>
        <ul v-if="selectedFiles.length" class="file-list">
          <li
            v-for="row in consolidatedFileRows"
            :key="row.key"
            :ref="(element) => setFileRowRef(row.key, element)"
          >
            <div class="file-list__meta">
              <span>{{ row.file.name }}</span>
              <input
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
                x
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
      <p class="showcase__kicker">EWA -> IA -> Excel</p>
      <h1>Unifica EWAs. Exporta la base.</h1>
      <p class="showcase__text">
        Genera un Excel con las columnas <code>Cliente</code>, <code>Componente</code> y <code>FechaVencimiento</code>.
      </p>
    </section>

    <aside class="result-card">
      <p class="metadata-panel__hint">
        {{ clientEntries.length }} clientes / {{ formatEwaCount(selectedFiles.length) }}
      </p>

      <div class="result-card__sheet">
        <div>
          <strong>Cliente</strong>
          <span>Nombre del cliente asociado al EWA.</span>
        </div>
        <div>
          <strong>Componente</strong>
          <span>Componente detectado por la IA.</span>
        </div>
        <div>
          <strong>FechaVencimiento</strong>
          <span>Fecha de vencimiento exportada al Excel.</span>
        </div>
      </div>
    </aside>
  </section>

  <form class="action-bar" @submit.prevent="submitForm">
    <div class="action-bar__messages">
      <p v-if="errorMessage" class="message message--error">{{ errorMessage }}</p>
      <p v-else-if="successMessage" :class="`message message--${successMessageTone}`">{{ successMessage }}</p>
      <p v-else class="message message--neutral">
        {{ selectedFiles.length ? "Completa un cliente por EWA para generar el consolidado." : "Selecciona los EWAs del periodo mensual." }}
      </p>
    </div>

    <button class="primary-button" type="submit" :disabled="!canSubmit">
      <span v-if="isUploading">Consolidando...</span>
      <span v-else>Generar Excel</span>
    </button>
  </form>
</template>
