<script setup>
import { ref } from "vue";

import DashboardWorkspace from "./components/DashboardWorkspace.vue";
import ExportWorkspace from "./components/ExportWorkspace.vue";
import MergeWorkspace from "./components/MergeWorkspace.vue";

const activeView = ref("export");

const views = [
  {
    id: "export",
    label: "Exportar",
    ariaLabel: "Vista Exportar",
  },
  {
    id: "dashboard",
    label: "Graficos",
    ariaLabel: "Vista Graficos",
  },
  {
    id: "merge",
    label: "Merge",
    ariaLabel: "Vista Merge",
  },
];
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">SAP EarlyWatch Alert</p>
        <strong class="brand">Vencimientos SAP</strong>
      </div>

      <nav class="topbar__nav" aria-label="Vistas principales">
        <button
          v-for="view in views"
          :key="view.id"
          class="topbar__nav-button"
          :class="{ 'topbar__nav-button--active': activeView === view.id }"
          :aria-label="view.ariaLabel"
          :aria-pressed="String(activeView === view.id)"
          type="button"
          @click="activeView = view.id"
        >
          {{ view.label }}
        </button>
      </nav>
    </header>

    <ExportWorkspace v-if="activeView === 'export'" />
    <DashboardWorkspace v-else-if="activeView === 'dashboard'" />
    <MergeWorkspace v-else />
  </main>
</template>
