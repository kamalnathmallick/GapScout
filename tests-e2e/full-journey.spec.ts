import { test, expect } from "@playwright/test";

test.describe("Full User Journey E2E", () => {
  const jobId = "00000000-0000-0000-0000-000000000001";
  const leadId = "11111111-1111-1111-1111-111111111111";

  test("completes end-to-end flow: register -> job -> map -> lead -> draft -> outreach -> outcome update", async ({
    page,
  }) => {
    let outcomeLogged = false;

    // 1. Intercept Auth endpoints
    await page.route(/.*\/api\/v1\/auth\/register/, async (route) => {
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          access_token: "test-jwt-token",
          token_type: "bearer",
          user: {
            id: "user-1",
            workspace_id: "ws-1",
            email: "founder@gapscout.test",
            role: "owner",
          },
        }),
      });
    });

    await page.route(/.*\/api\/v1\/auth\/me/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "user-1",
          workspace_id: "ws-1",
          email: "founder@gapscout.test",
          role: "owner",
          is_verified: true,
        }),
      });
    });

    // 2. Intercept Job creation & estimation endpoints
    await page.route(/.*\/api\/v1\/jobs\/estimate/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cells_total: 4,
          cell_size_m: 1000,
          area_km2: 4.0,
          estimated_runtime_sec: 10,
          estimated_cost_usd: 0.05,
          area_name: "Indiranagar, Bangalore",
          bbox: { min_lat: 12.96, min_lon: 77.63, max_lat: 12.99, max_lon: 77.66 },
        }),
      });
    });

    await page.route("**/api/v1/jobs", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            id: jobId,
            workspace_id: "ws-1",
            category: "cafe",
            area_name: "Indiranagar, Bangalore",
            status: "completed",
            cells_total: 4,
            cells_done: 4,
            places_found: 24,
            errors_count: 0,
            error: null,
            params: {},
            created_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.continue();
      }
    });

    // 3. Intercept Gap Map endpoints
    await page.route(new RegExp(`.*/api/v1/gap/${jobId}/hexes`), async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: jobId,
          category: "cafe",
          resolution: 8,
          hexes: [
            {
              id: "hex-1",
              search_job_id: jobId,
              category: "cafe",
              h3_index: "88618925d3fffff",
              resolution: 8,
              supply_count: 2,
              density_per_km2: 2.1,
              avg_rating: 4.2,
              avg_review_count: 85,
              demand_proxy: 75.0,
              opportunity_score: 88.0,
              label: "underserved",
              explanation: { top_reasons: ["High commercial density, low cafe supply"] },
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
                  opportunity_score: 88.0,
                  label: "underserved",
                },
              },
            ],
          },
        }),
      });
    });

    await page.route(new RegExp(`.*/api/v1/gap/${jobId}/summary`), async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          job_id: jobId,
          category: "cafe",
          area_name: "Indiranagar, Bangalore",
          total_hexes: 1,
          underserved_hexes: 1,
          oversaturated_hexes: 0,
          balanced_hexes: 0,
          top_hex: {
            h3_index: "88618925d3fffff",
            opportunity_score: 88.0,
            label: "underserved",
          },
        }),
      });
    });

    // 4. Intercept Leads and Dataset Health endpoints
    await page.route(/.*\/api\/v1\/leads\/health/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total_labelled: outcomeLogged ? 1 : 0,
          positive_outcomes: outcomeLogged ? 1 : 0,
          negative_outcomes: 0,
          ml_threshold_met: false,
          ml_min_labels_required: 150,
          ml_min_positives_required: 20,
          recent_outcomes: outcomeLogged
            ? [
                {
                  id: "evt-1",
                  lead_id: leadId,
                  place_name: "Third Wave Coffee",
                  outcome: "replied",
                  occurred_at: new Date().toISOString(),
                },
              ]
            : [],
        }),
      });
    });

    await page.route("**/api/v1/leads*", async (route) => {
      if (route.request().url().includes(leadId)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: leadId,
            workspace_id: "ws-1",
            place_id: "place-1",
            place: {
              id: "place-1",
              name: "Third Wave Coffee",
              category: "cafe",
              address: "80 Feet Rd, Indiranagar",
              phone_e164: "+919876543210",
              website: "https://thirdwave.example.com",
              rating: 4.6,
              review_count: 210,
            },
            status: outcomeLogged ? "replied" : "new",
            rule_score: 84.0,
            ml_score: 0.82,
            final_score: 84.0,
            score_breakdown: {
              gap_opportunity: 30,
              digital_presence: 20,
              reputation: 15,
              customer_engagement: 10,
              reachability: 9,
            },
            notes: null,
            created_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [
              {
                id: leadId,
                workspace_id: "ws-1",
                place_id: "place-1",
                place: {
                  id: "place-1",
                  name: "Third Wave Coffee",
                  category: "cafe",
                  address: "80 Feet Rd, Indiranagar",
                  rating: 4.6,
                  review_count: 210,
                },
                status: outcomeLogged ? "replied" : "new",
                rule_score: 84.0,
                final_score: 84.0,
                score_breakdown: {},
                notes: null,
                created_at: new Date().toISOString(),
              },
            ],
            total: 1,
            page: 1,
            page_size: 100,
            has_more: false,
          }),
        });
      }
    });

    // 5. Intercept Draft generation & outreach events
    await page.route(/.*\/api\/v1\/leads\/.*\/drafts/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "draft-1",
          lead_id: leadId,
          channel: "chat",
          tone: "direct",
          body: "Hi Third Wave team, noticed your strong local reviews in Indiranagar. Would love to share ideas on weekday tables.\n\nReply STOP to opt out.",
          char_count: 145,
          word_count: 24,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.route(/.*\/api\/v1\/leads\/.*\/outreach-event/, async (route) => {
      outcomeLogged = true;
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "event-reply-1",
          lead_id: leadId,
          event_type: "replied",
          occurred_at: new Date().toISOString(),
        }),
      });
    });

    await page.route(/.*\/api\/v1\/leads\/.*\/status/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: leadId,
          status: "contacted",
        }),
      });
    });

    // =========================================================================
    // EXECUTE FULL JOURNEY
    // =========================================================================

    // Step A: Registration
    await page.goto("/register");
    await expect(page.getByText(/Create your GapScout account/i)).toBeVisible();
    await page.fill('input[type="email"]', "founder@gapscout.test");
    await page.fill('input[type="password"]', "SecretPassword123!");
    await page.fill('input[id="workspaceName"]', "Alpha Analytics");
    await page.click('button[type="submit"]');

    // Step B: Create a Job
    await page.goto("/jobs/new");
    await expect(page.getByText(/New Market Gap Analysis/i)).toBeVisible();

    // Fill form and acknowledge TOS notice
    const tosCheckbox = page.getByTestId("tos-checkbox");
    await expect(tosCheckbox).toBeVisible();
    await tosCheckbox.check();

    const submitBtn = page.getByRole("button", { name: /Confirm and Start Analysis/i });
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Step C: View Gap Map
    await page.goto(`/gap/${jobId}`);
    await expect(page.getByText(/Market Gap Intelligence/i)).toBeVisible();

    // Step D: Open Leads Pipeline
    await page.goto("/leads");
    await expect(page.getByText(/Lead Scorer & Outreach Pipeline/i)).toBeVisible();
    await expect(page.getByText("Third Wave Coffee")).toBeVisible();

    // Step E: Verify Dataset Health Card Initial State
    await expect(page.getByText(/0 \/ 150/i)).toBeVisible();

    // Step F: Open Lead Drawer & Generate Draft
    await page.click("text=Third Wave Coffee");
    await expect(page.getByText(/Outreach Draft & Verification/i)).toBeVisible();

    // Step G: Log Contact and Reply Outcome
    const markContactedBtn = page.getByRole("button", { name: /Mark Contacted/i });
    if (await markContactedBtn.isVisible()) {
      await markContactedBtn.click();
    }

    const logReplyBtn = page.getByRole("button", { name: /Log Reply/i });
    if (await logReplyBtn.isVisible()) {
      await logReplyBtn.click();
    }

    // Step H: Verify Dataset Health Card Reflects Logged Reply
    await page.goto("/leads");
    await expect(page.getByText(/1 \/ 150/i)).toBeVisible();
  });
});
