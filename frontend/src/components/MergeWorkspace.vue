<script setup>
import { computed, ref } from "vue";

import { mergeWorkbookFiles } from "../lib/workbookMerge.js";

const selectedFiles = ref([]);
const isMerging = ref(false);
const workbookInput = ref(null);
const statusMessage = ref("Subi 2 o mas excels EWA para unificar sus filas.");
const successMessage = ref("");
const errorMessage = ref("");

const canMerge = computed(() => selectedFiles.value.length >= 2 && !isMerging.value);
const selectedCountLabel = computed(() =>
  selectedFiles.value.length === 1
    ? "1 excel seleccionado"
    : `${selectedFiles.value.length} excels seleccionados`,
);

function openWorkbookPicker() {
  if (isMerging.value) {
    return;
  }

  workbookInput.value?.click();
}

function onWorkbookChange(event) {
  const files = Array.from(event.target.files ?? []);
  applyFiles(files);

  if (workbookInput.value) {
    workbookInput.value.value = "";
  }
}

function applyFiles(files) {
  successMessage.value = "";
  errorMessage.value = "";

  if (!files.length) {
    return;
  }

  if (files.some((file) => !file.name.toLowerCase().endsWith(".xlsx"))) {
    selectedFiles.value = [];
    errorMessage.value = "Solo se admiten archivos .xlsx.";
    return;
  }

  const merged = [...selectedFiles.value];
  const seen = new Set(merged.map(getFileKey));

  files.forEach((file) => {
    const key = getFileKey(file);
    if (!seen.has(key)) {
      seen.add(key);
      merged.push(file);
    }
  });

  selectedFiles.value = merged;
}

function removeSelectedFile(fileToRemove) {
  if (isMerging.value) {
    return;
  }

  const fileKey = getFileKey(fileToRemove);
  selectedFiles.value = selectedFiles.value.filter((file) => getFileKey(file) !== fileKey);
  successMessage.value = "";
  errorMessage.value = "";
}

async function runMerge() {
  if (!canMerge.value) {
    errorMessage.value = "Selecciona al menos 2 excels para mergear.";
    return;
  }

  isMerging.value = true;
  successMessage.value = "";
  errorMessage.value = "";

  try {
    const result = await mergeWorkbookFiles(selectedFiles.value);
    triggerDownload(result.blob, result.filename);
    successMessage.value = `Merge listo. ${result.workbookCount} excels unidos en ${result.mergedRowCount} filas.`;
    statusMessage.value = "Workbook merged descargado.";
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "No se pudo completar el merge.";
  } finally {
    isMerging.value = false;
  }
}

function getFileKey(file) {
  return `${file.name}:${file.size}:${file.lastModified}`;
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
  <section class="dashboard-shell">
    <section class="dashboard-hero">
      <div class="dashboard-hero__copy">
        <p class="showcase__kicker">Merge operativo</p>
        <h1>Unifica excels EWA.</h1>
        <p class="showcase__text">
          Carga 2 o mas archivos con hoja <code>Base</code> y genera una sola salida lista para seguir trabajando.
        </p>
      </div>

      <div class="dashboard-controls">
        <input
          ref="workbookInput"
          class="sr-only"
          type="file"
          accept=".xlsx"
          multiple
          @change="onWorkbookChange"
        />
        <button
          class="secondary-button secondary-button--dark"
          type="button"
          :disabled="isMerging"
          @click="openWorkbookPicker"
        >
          {{ selectedFiles.length ? "Agregar excels" : "Cargar excels" }}
        </button>
        <button
          class="secondary-button"
          type="button"
          aria-label="Generar merge"
          :disabled="!canMerge"
          @click="runMerge"
        >
          {{ isMerging ? "Mergeando..." : "Generar merge" }}
        </button>
        <p class="dashboard-controls__hint">{{ statusMessage }}</p>
      </div>
    </section>

    <section v-if="!selectedFiles.length" class="dashboard-summary">
      <article class="dashboard-card dashboard-card--empty">
        <span class="dashboard-card__eyebrow">Empty state</span>
        <h2>Todavia no cargaste excels para mergear.</h2>
        <p class="dashboard-card__note">
          Subi al menos 2 archivos <code>.xlsx</code> con hoja <code>Base</code> para generar un workbook unificado.
        </p>
      </article>
    </section>

    <template v-else>
      <section class="dashboard-summary">
        <article class="dashboard-card dashboard-card--metric">
          <span class="dashboard-card__eyebrow">Entrada</span>
          <strong class="dashboard-card__value">{{ selectedFiles.length }}</strong>
          <p class="dashboard-card__note">{{ selectedCountLabel }}</p>
        </article>

        <article class="dashboard-card dashboard-card--metric">
          <span class="dashboard-card__eyebrow">Contrato</span>
          <strong class="dashboard-card__value">Base</strong>
          <p class="dashboard-card__note">Columnas: Cliente, Componente, FechaVencimiento.</p>
        </article>
      </section>

      <section class="dashboard-grid dashboard-grid--clients">
        <article class="dashboard-card">
          <div class="dashboard-card__header">
            <div>
              <span class="dashboard-card__eyebrow">Seleccion</span>
              <h2>Excels listos para merge</h2>
            </div>
            <p class="dashboard-card__note">
              {{ selectedCountLabel }}
            </p>
          </div>

          <ul class="merge-file-list" aria-label="Excels seleccionados para merge">
            <li v-for="file in selectedFiles" :key="getFileKey(file)">
              <div class="merge-file-list__meta">
                <strong>{{ file.name }}</strong>
                <span>{{ formatBytes(file.size) }}</span>
              </div>
              <button
                class="file-list__remove"
                type="button"
                :disabled="isMerging"
                :aria-label="`Eliminar ${file.name}`"
                @click="removeSelectedFile(file)"
              >
                x
              </button>
            </li>
          </ul>

          <p v-if="errorMessage" class="message message--error">{{ errorMessage }}</p>
          <p v-else-if="successMessage" class="message message--success">{{ successMessage }}</p>
          <p v-else class="message message--neutral">
            El merge conserva las filas en el orden de los excels cargados.
          </p>
        </article>
      </section>
    </template>
  </section>
</template>
