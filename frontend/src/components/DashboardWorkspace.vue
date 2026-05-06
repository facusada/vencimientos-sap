<script setup>
import { computed, ref } from "vue";

import { getCurrentPeriod } from "../lib/api.js";
import { fetchDashboardSnapshot } from "../lib/dashboardApi.js";
import { parseDashboardWorkbook } from "../lib/dashboardWorkbook.js";

const selectedPeriod = ref(getCurrentPeriod());
const isLoading = ref(false);
const workbookInput = ref(null);
const snapshot = ref(buildEmptySnapshot(selectedPeriod.value));
const statusMessage = ref("Subi un Excel consolidado o actualiza para probar la fuente remota.");
const workbookName = ref("");
const hasLoadedSnapshot = ref(false);

const summaryCards = computed(() => [
  {
    label: "Clientes monitoreados",
    value: snapshot.value.summary.totalClients,
  },
  {
    label: "Vencimientos totales",
    value: snapshot.value.summary.totalExpirations,
  },
  {
    label: "En 90 dias",
    value: snapshot.value.summary.expiringIn90Days,
  },
  {
    label: "Componentes unicos",
    value: snapshot.value.summary.uniqueComponents,
  },
]);

const monthlyBars = computed(() => {
  const maxValue = Math.max(...snapshot.value.expirationsByMonth.map((item) => item.count), 1);
  return snapshot.value.expirationsByMonth.map((item) => ({
    ...item,
    height: `${Math.max(18, (item.count / maxValue) * 100)}%`,
    label: formatPeriodLabel(item.month),
  }));
});

const componentBars = computed(() => {
  const maxValue = Math.max(...snapshot.value.expirationsByComponent.map((item) => item.count), 1);
  return snapshot.value.expirationsByComponent.map((item) => ({
    ...item,
    width: `${Math.max(8, (item.count / maxValue) * 100)}%`,
  }));
});

const shouldShowEmptyState = computed(() => !hasLoadedSnapshot.value && !isLoading.value);

async function loadSnapshot() {
  isLoading.value = true;

  try {
    const nextSnapshot = await fetchDashboardSnapshot(selectedPeriod.value);
    snapshot.value = nextSnapshot;
    hasLoadedSnapshot.value = true;
    statusMessage.value =
      nextSnapshot.source === "api"
        ? "Datos sincronizados con el endpoint de dashboard."
        : "Mostrando datos demo mientras se desarrolla el endpoint de dashboard.";
  } finally {
    isLoading.value = false;
  }
}

async function onWorkbookChange(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  isLoading.value = true;

  try {
    const nextSnapshot = await parseDashboardWorkbook(file, selectedPeriod.value);
    snapshot.value = nextSnapshot;
    hasLoadedSnapshot.value = true;
    workbookName.value = file.name;
    statusMessage.value = `Datos cargados desde Excel local: ${file.name}.`;
  } catch (error) {
    statusMessage.value =
      error instanceof Error ? error.message : "No se pudo leer el Excel seleccionado.";
  } finally {
    isLoading.value = false;
    if (workbookInput.value) {
      workbookInput.value.value = "";
    }
  }
}

function buildEmptySnapshot(period) {
  return {
    period,
    source: "demo",
    summary: {
      totalClients: 0,
      totalExpirations: 0,
      expiringIn90Days: 0,
      uniqueComponents: 0,
    },
    expirationsByMonth: [],
    expirationsByComponent: [],
    clientsAtRisk: [],
  };
}

function formatPeriodLabel(period) {
  const [year, month] = String(period).split("-");
  const monthIndex = Number(month) - 1;
  const fallback = String(period);

  if (!year || Number.isNaN(monthIndex) || monthIndex < 0 || monthIndex > 11) {
    return fallback;
  }

  return new Intl.DateTimeFormat("es-AR", {
    month: "short",
    year: "2-digit",
  }).format(new Date(Number(year), monthIndex, 1));
}

function formatDate(value) {
  if (!value) {
    return "Sin fecha";
  }

  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("es-AR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}
</script>

<template>
  <section class="dashboard-shell">
    <section class="dashboard-hero">
      <div class="dashboard-hero__copy">
        <p class="showcase__kicker">Dashboard operativo</p>
        <h1>Vencimientos en foco.</h1>
        <p class="showcase__text">
          Carga un Excel consolidado y transforma la hoja <code>Base</code> en metricas y graficos para seguimiento operativo.
        </p>
      </div>

      <div class="dashboard-controls">
        <label class="dashboard-controls__field">
          <span>Periodo</span>
          <input v-model="selectedPeriod" type="month" />
        </label>
        <input
          ref="workbookInput"
          class="sr-only"
          type="file"
          accept=".xlsx"
          @change="onWorkbookChange"
        />
        <button
          class="secondary-button secondary-button--dark"
          type="button"
          :disabled="isLoading"
          @click="workbookInput?.click()"
        >
          {{ workbookName ? "Reemplazar Excel" : "Cargar Excel" }}
        </button>
        <button
          class="secondary-button"
          type="button"
          aria-label="Actualizar graficos"
          :disabled="isLoading"
          @click="loadSnapshot"
        >
          {{ isLoading ? "Actualizando..." : "Actualizar" }}
        </button>
        <p v-if="workbookName" class="dashboard-controls__hint">
          Fuente actual: {{ workbookName }}
        </p>
      </div>
    </section>

    <section class="dashboard-summary">
      <article v-if="shouldShowEmptyState" class="dashboard-card dashboard-card--empty">
        <span class="dashboard-card__eyebrow">Empty state</span>
        <h2>Todavia no cargaste un Excel.</h2>
        <p class="dashboard-card__note">
          Subi un consolidado con hoja <code>Base</code> para ver los graficos reales, o usa
          <code>Actualizar</code> para probar la fuente remota/demo.
        </p>
      </article>
    </section>

    <template v-if="!shouldShowEmptyState">
      <section class="dashboard-summary">
      <article v-for="card in summaryCards" :key="card.label" class="dashboard-card dashboard-card--metric">
        <span class="dashboard-card__eyebrow">{{ card.label }}</span>
        <strong class="dashboard-card__value">{{ card.value }}</strong>
        <p class="dashboard-card__note">Periodo {{ snapshot.period }}</p>
      </article>
    </section>

    <section class="dashboard-grid">
      <article class="dashboard-card">
        <div class="dashboard-card__header">
          <div>
            <span class="dashboard-card__eyebrow">Cadencia mensual</span>
            <h2>Vencimientos por mes</h2>
          </div>
          <p class="dashboard-card__note">{{ statusMessage }}</p>
        </div>

        <div class="month-chart" aria-label="Grafico mensual de vencimientos">
          <div v-for="item in monthlyBars" :key="item.month" class="month-chart__item">
            <span class="month-chart__count">{{ item.count }}</span>
            <div class="month-chart__bar-wrap">
              <div class="month-chart__bar" :style="{ height: item.height }" />
            </div>
            <span class="month-chart__label">{{ item.label }}</span>
          </div>
        </div>
      </article>

      <article class="dashboard-card">
        <div class="dashboard-card__header">
          <div>
            <span class="dashboard-card__eyebrow">Concentracion</span>
            <h2>Componentes mas expuestos</h2>
          </div>
          <p class="dashboard-card__note">Priorizacion por cantidad de vencimientos.</p>
        </div>

        <div class="component-chart" aria-label="Grafico por componente">
          <div v-for="item in componentBars" :key="item.component" class="component-chart__row">
            <div class="component-chart__meta">
              <strong>{{ item.component }}</strong>
              <span>{{ item.count }}</span>
            </div>
            <div class="component-chart__track">
              <div class="component-chart__fill" :style="{ width: item.width }" />
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="dashboard-grid dashboard-grid--clients">
      <article class="dashboard-card">
        <div class="dashboard-card__header">
          <div>
            <span class="dashboard-card__eyebrow">Seguimiento</span>
            <h2>Clientes con mas riesgo</h2>
          </div>
          <p class="dashboard-card__note">Ordenados por cantidad de vencimientos detectados.</p>
        </div>

        <div class="risk-table" aria-label="Clientes con mayor riesgo">
          <div class="risk-table__head">
            <span>Cliente</span>
            <span>Vencimientos</span>
            <span>Proximo hito</span>
          </div>
          <div v-for="item in snapshot.clientsAtRisk" :key="`${item.client}:${item.nextExpiration}`" class="risk-table__row">
            <strong>{{ item.client }}</strong>
            <span>{{ item.expirations }}</span>
            <span>{{ formatDate(item.nextExpiration) }}</span>
          </div>
        </div>
      </article>
    </section>
    </template>
  </section>
</template>
