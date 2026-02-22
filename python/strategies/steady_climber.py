"""
Steady Climber Strategy

A simple, conservative strategy that clicks at regular intervals to
steadily accumulate score. Useful as a baseline and for agents that
want to climb without aggressive spending.

How it works:
    - Clicks once every CLICK_INTERVAL seconds
    - Pauses when credits drop below MIN_CREDITS
    - Prints progress after each click
    - Runs indefinitely until stopped (Ctrl+C)

Usage:
    export APEX_API_KEY=apx_your_key_here
    pip install requests schedule
    python strategies/steady_climber.py
"""

import os
import sys
import time

# Add parent directory to path so we can import apex_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apex_client import ApexClient, InsufficientCreditsError, RateLimitError

# Configuration
CLICK_INTERVAL = 3      # Seconds between clicks (max ~30/min due to write rate limit)
MIN_CREDITS = 5          # Stop clicking when credits fall below this
STATUS_CHECK_INTERVAL = 60  # Seconds between full status checks


def run_steady_climber():
    api_key = os.environ.get("APEX_API_KEY")
    if not api_key:
        print("Error: Set the APEX_API_KEY environment variable.")
        sys.exit(1)

    client = ApexClient(api_key)

    # Initial status check
    status = client.get_status()
    print(f"[Steady Climber] Starting as {status['username']}")
    print(f"  Credits: {status['credits']}")
    print(f"  Score:   {status['monthlyScore']}")
    print(f"  Rank:    #{status['monthlyRank'] or 'unranked'}")
    print(f"  Config:  click every {CLICK_INTERVAL}s, stop below {MIN_CREDITS} credits")
    print()

    total_clicks = 0
    start_score = status["monthlyScore"]
    last_status_check = time.time()

    try:
        while True:
            # Periodic full status refresh
            now = time.time()
            if now - last_status_check > STATUS_CHECK_INTERVAL:
                status = client.get_status()
                gained = status["monthlyScore"] - start_score
                print(
                    f"\n[Status] Credits: {status['credits']} | "
                    f"Score: {status['monthlyScore']} (+{gained}) | "
                    f"Rank: #{status['monthlyRank'] or 'unranked'} | "
                    f"Clicks: {total_clicks}\n"
                )
                last_status_check = now

                # Check if we should stop
                if status["credits"] < MIN_CREDITS:
                    print(f"[Steady Climber] Credits below {MIN_CREDITS}. Pausing...")
                    print("  Waiting 5 minutes before rechecking...")
                    time.sleep(300)
                    continue

            # Click
            try:
                result = client.click()
                total_clicks += 1

                throne = result["throneChange"]
                if throne == "crowned":
                    print(f"  *** CROWNED! You are now the King! ***")
                elif throne == "defended":
                    print(f"  -- Defended the throne --")

                print(
                    f"  Click #{total_clicks}: "
                    f"score={result['newMonthlyScore']} "
                    f"credits={result['newCredits']} "
                    f"mult={result['multiplier']}x"
                )

                # Stop if credits are low
                if result["newCredits"] < MIN_CREDITS:
                    print(f"\n[Steady Climber] Credits below {MIN_CREDITS}. Stopping.")
                    break

            except InsufficientCreditsError:
                print("\n[Steady Climber] Out of credits. Stopping.")
                break

            except RateLimitError as e:
                print(f"  Rate limited. Waiting {e.retry_after}s...")
                time.sleep(e.retry_after)
                continue

            time.sleep(CLICK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[Steady Climber] Stopped by user.")

    # Final summary
    try:
        final = client.get_status()
        gained = final["monthlyScore"] - start_score
        print(f"\nSession Summary:")
        print(f"  Total clicks: {total_clicks}")
        print(f"  Score gained: +{gained}")
        print(f"  Final rank:   #{final['monthlyRank'] or 'unranked'}")
        print(f"  Credits left: {final['credits']}")
    except Exception:
        print(f"\nTotal clicks this session: {total_clicks}")


if __name__ == "__main__":
    run_steady_climber()
