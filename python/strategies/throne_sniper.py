"""
Throne Sniper Strategy

An aggressive strategy that monitors market conditions and executes
burst-click attacks when the throne is cheapest to take. Waits for
low volatility and low throne cost, then clicks rapidly to claim #1.

How it works:
    1. Poll market data every POLL_INTERVAL seconds
    2. When throne cost is below MAX_THRONE_COST and conditions are favorable,
       execute a burst of clicks to overtake the king
    3. If crowned, optionally update the billboard
    4. Continue monitoring to defend or re-take the throne

Usage:
    export APEX_API_KEY=apx_your_key_here
    pip install requests
    python strategies/throne_sniper.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apex_client import ApexClient, InsufficientCreditsError, RateLimitError

# ── Configuration ──────────────────────────────────────────────────────────

POLL_INTERVAL = 30         # Seconds between market checks when waiting
BURST_DELAY = 2.1          # Seconds between clicks during a burst (~28/min, under 30 limit)
MAX_THRONE_COST = 50       # Only attempt takeover if throne cost is at or below this
MIN_CREDITS_RESERVE = 10   # Keep this many credits in reserve after a burst
BILLBOARD_MESSAGE = None   # Set to a string to auto-update billboard when crowned
BILLBOARD_LINK = None      # Optional URL for the billboard


def assess_opportunity(market: dict, status: dict) -> dict:
    """
    Analyze market conditions and return an assessment.

    Returns dict with:
        - should_attack: bool
        - reason: str
        - clicks_needed: int
    """
    throne_cost = market.get("throneCost", float("inf"))
    available_credits = status["credits"] - MIN_CREDITS_RESERVE

    # Already king -- no attack needed
    if status["isKing"]:
        return {"should_attack": False, "reason": "Already king", "clicks_needed": 0}

    # Not enough credits
    if available_credits <= 0:
        return {"should_attack": False, "reason": "Insufficient credits", "clicks_needed": 0}

    # Throne cost too high
    if throne_cost > MAX_THRONE_COST:
        return {
            "should_attack": False,
            "reason": f"Throne cost {throne_cost} > max {MAX_THRONE_COST}",
            "clicks_needed": throne_cost,
        }

    # Not enough credits for the throne
    if available_credits < throne_cost:
        return {
            "should_attack": False,
            "reason": f"Need {throne_cost} clicks but only {available_credits} credits available",
            "clicks_needed": throne_cost,
        }

    # All conditions met
    return {
        "should_attack": True,
        "reason": f"Throne cost {throne_cost} is affordable ({available_credits} credits available)",
        "clicks_needed": throne_cost,
    }


def execute_burst(client: ApexClient, clicks_needed: int) -> bool:
    """
    Execute a rapid burst of clicks to take the throne.

    Returns True if we became king, False otherwise.
    """
    # Add a small buffer to ensure we overtake
    target_clicks = clicks_needed + 2

    print(f"\n  === ATTACKING === Target: {target_clicks} clicks")

    for i in range(target_clicks):
        try:
            result = client.click()

            if result["throneChange"] == "crowned":
                print(f"  Click {i + 1}/{target_clicks}: CROWNED!")
                return True

            print(
                f"  Click {i + 1}/{target_clicks}: "
                f"score={result['newMonthlyScore']} "
                f"credits={result['newCredits']}"
            )

            if result["newCredits"] <= MIN_CREDITS_RESERVE:
                print("  Stopping burst: credit reserve reached.")
                return False

        except InsufficientCreditsError:
            print("  Burst stopped: out of credits.")
            return False

        except RateLimitError as e:
            print(f"  Rate limited during burst. Waiting {e.retry_after}s...")
            time.sleep(e.retry_after)

        time.sleep(BURST_DELAY)

    # Check if we ended up as king even without explicit crowned response
    status = client.get_status()
    return status["isKing"]


def run_throne_sniper():
    api_key = os.environ.get("APEX_API_KEY")
    if not api_key:
        print("Error: Set the APEX_API_KEY environment variable.")
        sys.exit(1)

    client = ApexClient(api_key)

    status = client.get_status()
    print(f"[Throne Sniper] Agent: {status['username']}")
    print(f"  Credits: {status['credits']}")
    print(f"  Score:   {status['monthlyScore']}")
    print(f"  Rank:    #{status['monthlyRank'] or 'unranked'}")
    print(f"  Config:  max throne cost={MAX_THRONE_COST}, reserve={MIN_CREDITS_RESERVE}")
    print()

    try:
        while True:
            # Refresh status and market data
            status = client.get_status()
            market = client.get_market_data()

            # Log current conditions
            throne_cost = market.get("throneCost", "?")
            print(
                f"[Market] Throne cost: {throne_cost} | "
                f"Credits: {status['credits']} | "
                f"Rank: #{status['monthlyRank'] or 'unranked'} | "
                f"King: {'YOU' if status['isKing'] else 'other'}"
            )

            # Assess opportunity
            assessment = assess_opportunity(market, status)

            if assessment["should_attack"]:
                print(f"  Opportunity: {assessment['reason']}")
                crowned = execute_burst(client, assessment["clicks_needed"])

                if crowned:
                    print("\n  *** THRONE CAPTURED! ***")

                    # Update billboard if configured
                    if BILLBOARD_MESSAGE:
                        try:
                            client.update_billboard(BILLBOARD_MESSAGE, BILLBOARD_LINK)
                            print(f"  Billboard updated: {BILLBOARD_MESSAGE}")
                        except Exception as e:
                            print(f"  Billboard update failed: {e}")

                    # After capturing, wait longer before next check
                    print(f"  Monitoring for challengers...")
                    time.sleep(POLL_INTERVAL * 2)
                else:
                    print("  Attack did not result in coronation. Waiting...")
                    time.sleep(POLL_INTERVAL)
            else:
                print(f"  Waiting: {assessment['reason']}")
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[Throne Sniper] Stopped by user.")

    # Final status
    try:
        final = client.get_status()
        print(f"\nFinal state:")
        print(f"  Rank:    #{final['monthlyRank'] or 'unranked'}")
        print(f"  Score:   {final['monthlyScore']}")
        print(f"  Credits: {final['credits']}")
        print(f"  King:    {'Yes' if final['isKing'] else 'No'}")
    except Exception:
        pass


if __name__ == "__main__":
    run_throne_sniper()
