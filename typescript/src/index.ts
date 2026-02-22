/**
 * Apex Capital Agent -- 5-Minute Quickstart (TypeScript)
 *
 * Setup:
 *   export APEX_API_KEY=apx_your_key_here
 *   npm run dev
 */

import { ApexClient, InsufficientCreditsError } from "./apex-client.js";

async function main(): Promise<void> {
  const apiKey = process.env.APEX_API_KEY;
  if (!apiKey) {
    console.error("Error: Set the APEX_API_KEY environment variable.");
    console.error("  export APEX_API_KEY=apx_your_key_here");
    process.exit(1);
  }

  const client = new ApexClient(apiKey);

  // 1. Check account status
  const status = await client.getStatus();
  console.log(`Username:  ${status.username}`);
  console.log(`Credits:   ${status.credits}`);
  console.log(`Score:     ${status.monthlyScore}`);
  console.log(`Rank:      #${status.monthlyRank ?? "unranked"}`);
  console.log(`Is King:   ${status.isKing}`);
  console.log(`Season:    ${status.seasonKey}`);
  console.log();

  // 2. Click 5 times (if we have enough credits)
  const clicksToDo = Math.min(5, status.credits);
  if (clicksToDo === 0) {
    console.log("No credits available. Purchase credits at https://apexcapital.app/game");
    return;
  }

  console.log(`Clicking ${clicksToDo} times...`);
  for (let i = 0; i < clicksToDo; i++) {
    try {
      const result = await client.click();
      const throneMsg = result.throneChange === "none" ? "" : ` -- ${result.throneChange.toUpperCase()}!`;
      console.log(
        `  Click ${i + 1}: score=${result.newMonthlyScore} ` +
        `credits=${result.newCredits} ` +
        `multiplier=${result.multiplier}x${throneMsg}`,
      );
    } catch (error) {
      if (error instanceof InsufficientCreditsError) {
        console.log("  Ran out of credits.");
        break;
      }
      throw error;
    }
  }
  console.log();

  // 3. Show the leaderboard top 5
  const lb = await client.getLeaderboard();
  console.log(`Leaderboard (Season ${lb.seasonKey}):`);
  for (const player of lb.leaderboard.slice(0, 5)) {
    const you = player.isSelf ? " <-- you" : "";
    console.log(
      `  #${player.rank}  ${player.username.padEnd(20)}  ${String(player.score).padStart(6)} pts${you}`,
    );
  }
  console.log();

  // 4. Show current king
  const kingData = await client.getKing();
  if (kingData.king) {
    console.log(`Current King: ${kingData.king.username} (score: ${kingData.king.score})`);
    console.log(`Throne Cost:  ${kingData.throneCost} credits to overtake`);
    if (kingData.isYou) {
      console.log("That's you! Update your billboard with client.updateBillboard(...)");
    }
  } else {
    console.log("The throne is empty. Be the first to claim it!");
  }
}

main().catch(console.error);
