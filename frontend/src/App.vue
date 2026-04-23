<script setup>
import { computed, ref } from "vue";

const selectedFile = ref(null);
const errorMessage = ref("");
const successMessage = ref("");
const isUploading = ref(false);
const isDragging = ref(false);
const fileInput = ref(null);
const analyzeUrl = buildAnalyzeUrl();

const canSubmit = computed(() => Boolean(selectedFile.value) && !isUploading.value);
const fileLabel = computed(() => {
  if (!selectedFile.value) {
    return "Sin archivo seleccionado";
  }

  return `${selectedFile.value.name} · ${formatBytes(selectedFile.value.size)}`;
});

function onFileChange(event) {
  const [file] = event.target.files ?? [];
  applyFile(file);
}

function onDrop(event) {
  if (isUploading.value) {
    isDragging.value = false;
    return;
  }

  isDragging.value = false;
  const [file] = event.dataTransfer?.files ?? [];
  applyFile(file);
}

function applyFile(file) {
  successMessage.value = "";

  if (!file) {
    selectedFile.value = null;
    return;
  }

  if (!isSupportedFile(file.name)) {
    selectedFile.value = null;
    errorMessage.value = "Solo se admiten archivos .pdf.";
    if (fileInput.value) {
      fileInput.value.value = "";
    }
    return;
  }

  errorMessage.value = "";
  selectedFile.value = file;
}

async function submitForm() {
  if (!selectedFile.value || isUploading.value) {
    return;
  }

  isUploading.value = true;
  errorMessage.value = "";
  successMessage.value = "";

  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);

    const response = await fetch(analyzeUrl, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await extractErrorMessage(response));
    }

    const blob = await response.blob();
    const filename = getFilename(response.headers.get("Content-Disposition"));
    triggerDownload(blob, filename);
    successMessage.value = "Analisis completado. El Excel ya esta listo.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "No se pudo completar el analisis.";
  } finally {
    isUploading.value = false;
  }
}

function openFilePicker() {
  if (isUploading.value) {
    return;
  }

  fileInput.value?.click();
}

function isSupportedFile(filename) {
  return filename.toLowerCase().endsWith(".pdf");
}

function buildAnalyzeUrl() {
  const rawBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";
  const normalizedBaseUrl = rawBaseUrl.endsWith("/")
    ? rawBaseUrl.slice(0, -1)
    : rawBaseUrl;

  return `${normalizedBaseUrl}/ewa/analyze`;
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

function getFilename(contentDisposition) {
  const match = contentDisposition?.match(/filename="?([^"]+)"?/i);
  return match?.[1] ?? "ewa-expirations.xlsx";
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
      <span class="topbar__pill">Excel instantaneo</span>
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
          :disabled="isUploading"
          @change="onFileChange"
        />

        <div class="dropzone__visual">
          <span class="dropzone__badge">Carga</span>
          <h2>{{ selectedFile ? "Archivo listo" : "Subi tu EWA" }}</h2>
          <p>
            {{ selectedFile ? fileLabel : "Arrastra el documento aca o elegilo manualmente." }}
          </p>

          <div class="dropzone__actions">
            <button
              class="secondary-button"
              type="button"
              :disabled="isUploading"
              @click="openFilePicker"
            >
              {{ selectedFile ? "Cambiar archivo" : "Elegir archivo" }}
            </button>
            <span class="dropzone__hint">Formato soportado: .pdf</span>
          </div>
          <p class="dropzone__note">
            Formato soportado: PDF con texto extraible.
          </p>
        </div>
      </div>

      <section class="showcase">
        <p class="showcase__kicker">EWA → IA → Excel</p>
        <h1>Carga el EWA. Descarga el Excel.</h1>
        <p class="showcase__text">
          Un unico paso para transformar el reporte en una planilla simple con
          <code>Seccion</code>, <code>Nombre</code>, <code>Hito</code> y <code>Fecha</code>.
        </p>
      </section>

      <aside class="result-card">
        <span class="result-card__label">Salida</span>
        <div class="result-card__sheet">
          <div>
            <strong>Seccion</strong>
            <span>Bloque del EWA</span>
          </div>
          <div>
            <strong>Nombre</strong>
            <span>Componente o producto</span>
          </div>
          <div>
            <strong>Hito</strong>
            <span>Tipo de vencimiento</span>
          </div>
          <div>
            <strong>Fecha</strong>
            <span>Vencimiento normalizado</span>
          </div>
        </div>
      </aside>
    </section>

    <form class="action-bar" @submit.prevent="submitForm">
      <div class="action-bar__messages">
        <p v-if="errorMessage" class="message message--error">{{ errorMessage }}</p>
        <p v-else-if="successMessage" class="message message--success">{{ successMessage }}</p>
        <p v-else class="message message--neutral">
          {{ selectedFile ? "Archivo preparado para ejecutar el analisis." : "Selecciona un archivo para empezar." }}
        </p>
      </div>

      <button class="primary-button" type="submit" :disabled="!canSubmit">
        <span v-if="isUploading">Analizando...</span>
        <span v-else>Generar Excel</span>
      </button>
    </form>
  </main>
</template>
