/**
 * Billboard Optimizer Strategy (TypeScript)
 *
 * When you are the King, A/B tests billboard messages to find the
 * highest-performing variant, then locks in the winner.
 *
 * Usage:
 *   export APEX_API_KEY=apx_your_key_here
 *   npm run strategy:billboard
 */

import {
  ApexClient,
  ApexApiError,
  type BillboardVariant,
  type PoolStats,
} from "../apex-client.js";

// ── Configuration ──────────────────────────────────────────────────────────

const VARIANTS: BillboardVariant[] = [
  { message: "Check out our brand -- building the future of AI agents!" },
  { message: "Follow us for daily updates on competitive AI gaming." },
  { message: "The King's throne is earned, not given. Prove yourself." },
];

const TEST_DURATION_MS = 600_000;   // 10 minutes
const CHECK_INTERVAL_MS = 60_000;   // Check stats every minute
const ROTATION_MINUTES = 2;
const AUTO_OPTIMIZE = true;

// ── Helpers ────────────────────────────────────────────────────────────────

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface VariantStats {
  message: string;
  linkUrl?: string;
  views: number;
  clicks: number;
}

function displayPoolStats(stats: PoolStats): VariantStats | null {
  const variants = stats.variants ?? [];
  if (variants.length === 0) {
    console.log("  No variant data available yet.");
    return null;
  }

  console.log();
  console.log(`  ${"Variant".padEnd(50)} ${"Views".padStart(6)} ${"Clicks".padStart(7)} ${"CTR".padStart(7)}`);
  console.log(`  ${"-".repeat(50)} ${"-".repeat(6)} ${"-".repeat(7)} ${"-".repeat(7)}`);

  let best: VariantStats | null = null;
  let bestCtr = -1;

  for (const v of variants) {
    const msg = v.message.slice(0, 48);
    const ctr = v.views > 0 ? (v.clicks / v.views) * 100 : 0;

    let marker = "";
    if (v.views > 0 && ctr > bestCtr) {
      bestCtr = ctr;
      best = v;
      marker = " <-- best";
    }

    console.log(
      `  ${msg.padEnd(50)} ${String(v.views).padStart(6)} ${String(v.clicks).padStart(7)} ${ctr.toFixed(2).padStart(6)}%${marker}`,
    );
  }

  return best;
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

  console.log(`[Billboard Optimizer] Agent: ${status.username}`);
  console.log(`  Is King: ${status.isKing}`);
  console.log();

  if (!status.isKing) {
    console.log("You must be the King to optimize the billboard.");
    console.log("Use the throne-sniper strategy to take the throne first.");
    process.exit(1);
  }

  // Set up A/B pool
  console.log(`Setting up A/B test with ${VARIANTS.length} variants...`);
  console.log(`  Rotation: every ${ROTATION_MINUTES} minutes`);
  console.log(`  Auto-optimize: ${AUTO_OPTIMIZE}`);
  console.log(`  Test duration: ${TEST_DURATION_MS / 60_000} minutes`);
  console.log();

  try {
    const result = await client.abTestBillboard(VARIANTS, ROTATION_MINUTES, AUTO_OPTIMIZE);
    console.log(`  A/B pool created with ${result.variantCount} variants.`);
  } catch (error) {
    console.log(`  Failed to create A/B pool: ${error}`);
    process.exit(1);
  }

  // Monitor test
  console.log(`\nMonitoring A/B test for ${TEST_DURATION_MS / 60_000} minutes...`);
  let elapsed = 0;

  while (elapsed < TEST_DURATION_MS) {
    await sleep(CHECK_INTERVAL_MS);
    elapsed += CHECK_INTERVAL_MS;

    // Verify still king
    const currentStatus = await client.getStatus();
    if (!currentStatus.isKing) {
      console.log("\n  Lost the throne! A/B test aborted.");
      process.exit(1);
    }

    const minutesLeft = Math.round((TEST_DURATION_MS - elapsed) / 60_000);
    console.log(`\n[${Math.round(elapsed / 60_000)}min elapsed, ${minutesLeft}min remaining]`);

    try {
      const stats = await client.getBillboardStats();
      displayPoolStats(stats);
    } catch (error) {
      if (error instanceof ApexApiError && error.errorCode === "NO_POOL") {
        console.log("  No pool found. It may have been cleared.");
      } else {
        console.log(`  Error fetching stats: ${error}`);
      }
    }
  }

  // Pick the winner
  console.log("\n" + "=".repeat(60));
  console.log("A/B TEST COMPLETE");
  console.log("=".repeat(60));

  let winner: VariantStats | null = null;
  try {
    const stats = await client.getBillboardStats();
    winner = displayPoolStats(stats);
  } catch { /* ignore */ }

  if (winner) {
    console.log(`\n  Winner: "${winner.message}"`);
    try {
      await client.updateBillboard(winner.message, winner.linkUrl);
      console.log("  Billboard locked to winning variant.");
    } catch (error) {
      console.log(`  Failed to set winner: ${error}`);
    }
  } else {
    console.log("\n  Not enough data to pick a winner.");
    console.log("  The A/B pool will continue rotating. Run again later.");
  }
}

run().catch(console.error);
