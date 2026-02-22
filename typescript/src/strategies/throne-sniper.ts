/**
 * Throne Sniper Strategy (TypeScript)
 *
 * Monitors market conditions and executes burst-click attacks when the
 * throne is cheapest to take. Waits for low cost, then clicks rapidly.
 *
 * Usage:
 *   export APEX_API_KEY=apx_your_key_here
 *   npm run strategy:sniper
 */

import {
  ApexClient,
  InsufficientCreditsError,
  RateLimitError,
  type StatusData,
  type MarketData,
} from "../apex-client.js";

// ── Configuration ──────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 30_000;     // 30s between market checks
const BURST_DELAY_MS = 2_100;        // ~28 clicks/min (under 30 write limit)
const MAX_THRONE_COST = 50;           // Only attack if throne cost <= this
const MIN_CREDITS_RESERVE = 10;       // Keep this many credits in reserve
const BILLBOARD_MESSAGE: string | null = null; // Set to auto-update when crowned
const BILLBOARD_LINK: string | null = null;

// ── Helpers ────────────────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface Assessment {
  shouldAttack: boolean;
  reason: string;
  clicksNeeded: number;
}

function assessOpportunity(market: MarketData, status: StatusData): Assessment {
  const throneCost = market.throneCost ?? Infinity;
  const available = status.credits - MIN_CREDITS_RESERVE;

  if (status.isKing) {
    return { shouldAttack: false, reason: "Already king", clicksNeeded: 0 };
  }
  if (available <= 0) {
    return { shouldAttack: false, reason: "Insufficient credits", clicksNeeded: 0 };
  }
  if (throneCost > MAX_THRONE_COST) {
    return { shouldAttack: false, reason: `Throne cost ${throneCost} > max ${MAX_THRONE_COST}`, clicksNeeded: throneCost };
  }
  if (available < throneCost) {
    return { shouldAttack: false, reason: `Need ${throneCost} clicks but only ${available} available`, clicksNeeded: throneCost };
  }
  return { shouldAttack: true, reason: `Throne cost ${throneCost} is affordable (${available} credits available)`, clicksNeeded: throneCost };
}

async function executeBurst(client: ApexClient, clicksNeeded: number): Promise<boolean> {
  const target = clicksNeeded + 2; // Small buffer
  console.log(`\n  === ATTACKING === Target: ${target} clicks`);

  for (let i = 0; i < target; i++) {
    try {
      const result = await client.click();

      if (result.throneChange === "crowned") {
        console.log(`  Click ${i + 1}/${target}: CROWNED!`);
        return true;
      }

      console.log(
        `  Click ${i + 1}/${target}: ` +
        `score=${result.newMonthlyScore} credits=${result.newCredits}`,
      );

      if (result.newCredits <= MIN_CREDITS_RESERVE) {
        console.log("  Stopping burst: credit reserve reached.");
        return false;
      }
    } catch (error) {
      if (error instanceof InsufficientCreditsError) {
        console.log("  Burst stopped: out of credits.");
        return false;
      }
      if (error instanceof RateLimitError) {
        console.log(`  Rate limited during burst. Waiting ${error.retryAfter}s...`);
        await sleep(error.retryAfter * 1000);
      }
    }

    await sleep(BURST_DELAY_MS);
  }

  // Final check
  const status = await client.getStatus();
  return status.isKing;
}

// ── Main ───────────────────────────────────────────────────────────────────

async function run(): Promise<void> {
  const apiKey = process.env.APEX_API_KEY;
  if (!apiKey) {
    console.error("Error: Set the APEX_API_KEY environment variable.");
    process.exit(1);
  }

  const client = new ApexClient(apiKey);
  const status = await client.getStatus();

  console.log(`[Throne Sniper] Agent: ${status.username}`);
  console.log(`  Credits: ${status.credits}`);
  console.log(`  Score:   ${status.monthlyScore}`);
  console.log(`  Rank:    #${status.monthlyRank ?? "unranked"}`);
  console.log(`  Config:  max throne cost=${MAX_THRONE_COST}, reserve=${MIN_CREDITS_RESERVE}`);
  console.log();

  process.on("SIGINT", async () => {
    console.log("\n\n[Throne Sniper] Stopped by user.");
    try {
      const final = await client.getStatus();
      console.log(`\nFinal state:`);
      console.log(`  Rank:    #${final.monthlyRank ?? "unranked"}`);
      console.log(`  Score:   ${final.monthlyScore}`);
      console.log(`  Credits: ${final.credits}`);
      console.log(`  King:    ${final.isKing ? "Yes" : "No"}`);
    } catch { /* ignore */ }
    process.exit(0);
  });

  while (true) {
    const currentStatus = await client.getStatus();
    const market = await client.getMarketData();

    console.log(
      `[Market] Throne cost: ${market.throneCost} | ` +
      `Credits: ${currentStatus.credits} | ` +
      `Rank: #${currentStatus.monthlyRank ?? "unranked"} | ` +
      `King: ${currentStatus.isKing ? "YOU" : "other"}`,
    );

    const assessment = assessOpportunity(market, currentStatus);

    if (assessment.shouldAttack) {
      console.log(`  Opportunity: ${assessment.reason}`);
      const crowned = await executeBurst(client, assessment.clicksNeeded);

      if (crowned) {
        console.log("\n  *** THRONE CAPTURED! ***");

        if (BILLBOARD_MESSAGE) {
          try {
            await client.updateBillboard(BILLBOARD_MESSAGE, BILLBOARD_LINK ?? undefined);
            console.log(`  Billboard updated: ${BILLBOARD_MESSAGE}`);
          } catch (error) {
            console.log(`  Billboard update failed: ${error}`);
          }
        }

        console.log("  Monitoring for challengers...");
        await sleep(POLL_INTERVAL_MS * 2);
      } else {
        console.log("  Attack did not result in coronation. Waiting...");
        await sleep(POLL_INTERVAL_MS);
      }
    } else {
      console.log(`  Waiting: ${assessment.reason}`);
      await sleep(POLL_INTERVAL_MS);
    }
  }
}

run().catch(console.error);
