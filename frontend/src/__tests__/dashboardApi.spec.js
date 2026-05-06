import { describe, expect, it, vi } from "vitest";

import { dashboardDemoSnapshot, fetchDashboardSnapshot } from "../lib/dashboardApi.js";

describe("dashboardApi", () => {
  it("requests the future dashboard endpoint using the selected period", async () => {
    const fetchSpy = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          period: "2026-09",
          source: "api",
          summary: {
            totalClients: 2,
            totalExpirations: 5,
            expiringIn90Days: 1,
            uniqueComponents: 3,
          },
          expirationsByMonth: [{ month: "2026-09", count: 5 }],
          expirationsByComponent: [{ component: "SAP ERP", count: 5 }],
          clientsAtRisk: [{ client: "Cliente A", expirations: 5, nextExpiration: "2026-09-18" }],
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    const snapshot = await fetchDashboardSnapshot("2026-09", { fetchImpl: fetchSpy });

    expect(fetchSpy).toHaveBeenCalledWith("/api/ewa/dashboard?period=2026-09", {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });
    expect(snapshot.source).toBe("api");
    expect(snapshot.summary.totalExpirations).toBe(5);
  });

  it("falls back to demo data when the endpoint fails", async () => {
    const snapshot = await fetchDashboardSnapshot("2026-10", {
      fetchImpl: vi.fn().mockRejectedValue(new Error("offline")),
    });

    expect(snapshot.source).toBe("demo");
    expect(snapshot.period).toBe("2026-10");
    expect(snapshot.summary.totalClients).toBe(dashboardDemoSnapshot.summary.totalClients);
  });
});
