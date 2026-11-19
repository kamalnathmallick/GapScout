import { test, expect } from "@playwright/test";

test.describe("Interactive Gap Map UI", () => {
  const seededJobId = "00000000-0000-0000-0000-000000000001";

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem("gapscout_access_token", "fake-test-token");
    });

    const corsHeaders = {
      "access-control-allow-origin": "*",
      "access-control-allow-methods": "GET, POST, OPTIONS",
      "access-control-allow-headers": "*",
    };

    // Intercept backend requests with seeded fixture data
    await page.route(/.*\/api\/v1\/gap\/.*\/hexes/, async (route) => {
      await route.fulfill({
        status: 200,
        headers: corsHeaders,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: seededJobId,
          category: "cafe",
          resolution: 8,
          hexes: [
            {
              id: "hex-1",
              search_job_id: seededJobId,
              category: "cafe",
              h3_index: "88618925d3fffff",
              resolution: 8,
              supply_count: 1,
              density_per_km2: 1.2,
              avg_rating: 4.5,
              avg_review_count: 150,
              demand_proxy: 80,
              opportunity_score: 85.0,
              label: "underserved",
              explanation: {
                top_reasons: [
                  "0 competitors within 1 km",
                  "14 corporate offices nearby",
                ],
                metrics: {},
              },
              computed_at: new Date().toISOString(),
            },
            {
              id: "hex-2",
              search_job_id: seededJobId,
              category: "cafe",
              h3_index: "88618925d1fffff",
              resolution: 8,
              supply_count: 16,
              density_per_km2: 18.0,
              avg_rating: 3.7,
              avg_review_count: 400,
              demand_proxy: 40,
              opportunity_score: 18.0,
              label: "oversaturated",
              explanation: {
                top_reasons: ["16 competing cafes within 500m"],
                metrics: {},
              },
              computed_at: new Date().toISOString(),
            },
          ],
          geojson: {
            type: "FeatureCollection",
            features: [
              {
                type: "Feature",
                geometry: {
                  type: "Polygon",
                  coordinates: [
                    [
                      [77.63, 12.97],
                      [77.64, 12.97],
                      [77.64, 12.98],
                      [77.63, 12.98],
                      [77.63, 12.97],
                    ],
                  ],
                },
                properties: {
                  h3_index: "88618925d3fffff",
                  opportunity_score: 85.0,
                  label: "underserved",
                },
              },
            ],
          },
        }),
      });
    });

    await page.route(/.*\/api\/v1\/gap\/.*\/summary/, async (route) => {
      await route.fulfill({
        status: 200,
        headers: corsHeaders,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: seededJobId,
          category: "cafe",
          resolution: 8,
          total_hexes: 2,
          underserved_count: 1,
          balanced_count: 0,
          oversaturated_count: 1,
          insufficient_data_count: 0,
          area_median_rating: 4.1,
          best_hexes: [
            {
              h3_index: "88618925d3fffff",
              opportunity_score: 85.0,
              label: "underserved",
              reasons: ["0 competitors within 1 km", "14 offices nearby"],
            },
          ],
          saturated_hexes: [
            {
              h3_index: "88618925d1fffff",
              opportunity_score: 18.0,
              label: "oversaturated",
              reasons: ["16 competing cafes within 500m"],
            },
          ],
        }),
      });
    });

    await page.route(/.*\/api\/v1\/places.*/, async (route) => {
      await route.fulfill({
        status: 200,
        headers: corsHeaders,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: "place-1",
              workspace_id: "ws-1",
              name: "Third Wave Coffee",
              category: "cafe",
              normalized_category: "cafe",
              address: "Indiranagar 12th Main",
              phone_e164: "+918045678901",
              website: "https://thirdwavecoffee.in",
              website_domain: "thirdwavecoffee.in",
              email: "support@thirdwavecoffee.in",
              rating: 4.4,
              review_count: 512,
              price_level: 2,
              h3_r8: "88618925d3fffff",
              is_closed: false,
              latitude: 12.972,
              longitude: 77.635,
              first_seen_at: new Date().toISOString(),
              last_seen_at: new Date().toISOString(),
            },
          ],
          pagination: { total: 1, limit: 50, offset: 0, has_more: false },
        }),
      });
    });
  });

  test("renders map, top summary cards, controls, and opens hex detail drawer", async ({
    page,
  }) => {
    page.on("console", (msg) => console.log("BROWSER LOG:", msg.text()));
    page.on("request", (req) => console.log("REQ:", req.url()));
    page.on("response", (res) => console.log("RES:", res.url(), res.status()));
    page.on("requestfailed", (req) =>
      console.log("REQUEST FAILED:", req.url(), req.failure()?.errorText)
    );

    await page.goto(`http://127.0.0.1:3000/gap/${seededJobId}`);

    // 1. Check title & category in banner
    await expect(page.getByText(/cafe Market Gap/i)).toBeVisible();
    await expect(page.getByText(/2 Hexes/i)).toBeVisible();

    // 2. Check summary cards
    const summaryCards = page.getByTestId("gap-summary-cards");
    await expect(summaryCards).toBeVisible();
    await expect(page.getByText(/Top 3 Places to Open a cafe/i)).toBeVisible();
    await expect(page.getByText(/Most Saturated Areas/i)).toBeVisible();
    await expect(page.getByText("Score 85/100")).toBeVisible();

    // 3. Check map controls and metric switch
    const controls = page.getByTestId("map-controls");
    await expect(controls).toBeVisible();
    const metricSelect = page.getByTestId("metric-select");
    await expect(metricSelect).toBeVisible();

    // Change metric to Competitor Count
    await metricSelect.selectOption("supply");
    await expect(page.getByText(/Legend: Competitor Count/i)).toBeVisible();

    // Change back to Opportunity Score
    await metricSelect.selectOption("opportunity");
    await expect(page.getByText(/Legend: Opportunity Score/i)).toBeVisible();

    // 4. Click a best hex from the summary card
    const bestHexBtn = page.getByText("Score 85/100").locator("..");
    await bestHexBtn.click();

    // 5. Verify the side panel drawer opens
    const drawer = page.getByTestId("hex-drawer");
    await expect(drawer).toBeVisible();
    await expect(drawer.getByText(/Prime Opportunity/i)).toBeVisible();
    await expect(drawer.getByText("0 competitors within 1 km")).toBeVisible();
    await expect(drawer.getByText("Third Wave Coffee")).toBeVisible();
    await expect(drawer.getByText("Indiranagar 12th Main")).toBeVisible();

    // 6. Close the drawer
    const closeBtn = drawer.getByTitle(/Close details/i);
    await closeBtn.click();
    await expect(drawer).not.toBeVisible();

    // 7. Test CSV export button
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "CSV" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("gapscout-hexes-cafe");
  });
});
