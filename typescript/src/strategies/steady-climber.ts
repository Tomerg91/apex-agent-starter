/**
 * Steady Climber Strategy (TypeScript)
 *
 * A simple, conservative strategy that clicks at regular intervals to
 * steadily accumulate score. Useful as a baseline.
 *
 * Usage:
 *   export APEX_API_KEY=apx_your_key_here
 *   npm run strategy:climber
 */

import { ApexClient, InsufficientCreditsError, RateLimitError } from "../apex-client.js";

// ── Configuration ──────────────────────────────────────────────────────────

const CLICK_INTERVAL_MS = 3_000;       // 3 seconds between clicks (~20/min)
const MIN_CREDITS = 5;                  // Stop when credits fall below this
const STATUS_CHECK_INTERVAL_MS = 60_000; // Full status refresh every 60s

// ── Helpers ────────────────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ── Main ───────────────────────────────────────────────────────────────────

async function run(): Promise<void> {
  const apiKey = process.env.APEX_API_KEY;
  if (!apiKey) {
    console.error("Error: Set the APEX_API_KEY environment variable.");
    process.exit(1);
  }

  const client = new ApexClient(apiKey);

  let status = await client.getStatus();
  console.log(`[Steady Climber] Starting as ${status.username}`);
  console.log(`  Credits: ${status.credits}`);
  console.log(`  Score:   ${status.monthlyScore}`);
  console.log(`  Rank:    #${status.monthlyRank ?? "unranked"}`);
  console.log(`  Config:  click every ${CLICK_INTERVAL_MS / 1000}s, stop below ${MIN_CREDITS} credits`);
  console.log();

  let totalClicks = 0;
  const startScore = status.monthlyScore;
  let lastStatusCheck = Date.now();

  const shutdown = (): void => {
    console.log("\n\n[Steady Climber] Stopped by user.");
    client.getStatus().then((final) => {
      const gained = final.monthlyScore - startScore;
      console.log(`\nSession Summary:`);
      console.log(`  Total clicks: ${totalClicks}`);
      console.log(`  Score gained: +${gained}`);
      console.log(`  Final rank:   #${final.monthlyRank ?? "unranked"}`);
      console.log(`  Credits left: ${final.credits}`);
      process.exit(0);
    }).catch(() => {
      console.log(`\nTotal clicks this session: ${totalClicks}`);
      process.exit(0);
    });
  };

  process.on("SIGINT", shutdown);

  // Main loop
  while (true) {
    // Periodic status refresh
    if (Date.now() - lastStatusCheck > STATUS_CHECK_INTERVAL_MS) {
      status = await client.getStatus();
      const gained = status.monthlyScore - startScore;
      console.log(
        `\n[Status] Credits: ${status.credits} | ` +
        `Score: ${status.monthlyScore} (+${gained}) | ` +
        `Rank: #${status.monthlyRank ?? "unranked"} | ` +
        `Clicks: ${totalClicks}\n`,
      );
      lastStatusCheck = Date.now();

      if (status.credits < MIN_CREDITS) {
        console.log(`[Steady Climber] Credits below ${MIN_CREDITS}. Pausing 5 minutes...`);
        await sleep(300_000);
        continue;
      }
    }

    // Click
    try {
      const result = await client.click();
      totalClicks++;

      if (result.throneChange === "crowned") {
        console.log("  *** CROWNED! You are now the King! ***");
      } else if (result.throneChange === "defended") {
        console.log("  -- Defended the throne --");
      }

      console.log(
        `  Click #${totalClicks}: ` +
        `score=${result.newMonthlyScore} ` +
        `credits=${result.newCredits} ` +
        `mult=${result.multiplier}x`,
      );

      if (result.newCredits < MIN_CREDITS) {
        console.log(`\n[Steady Climber] Credits below ${MIN_CREDITS}. Stopping.`);
        break;
      }
    } catch (error) {
      if (error instanceof InsufficientCreditsError) {
        console.log("\n[Steady Climber] Out of credits. Stopping.");
        break;
      }
      if (error instanceof RateLimitError) {
        console.log(`  Rate limited. Waiting ${error.retryAfter}s...`);
        await sleep(error.retryAfter * 1000);
        continue;
      }
      throw error;
    }

    await sleep(CLICK_INTERVAL_MS);
  }
}

run().catch(console.error);
