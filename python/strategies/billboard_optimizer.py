"""
Billboard Optimizer Strategy

When you are the King, this strategy A/B tests billboard messages to find
the highest-performing variant, then locks in the winner.

How it works:
    1. Verify you are the King
    2. Set up billboard A/B pool with your message variants
    3. Let variants rotate for a test period
    4. Check pool stats and pick the winner (highest CTR)
    5. Set the winning message as the sole billboard

Usage:
    export APEX_API_KEY=apx_your_key_here
    pip install requests
    python strategies/billboard_optimizer.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apex_client import ApexClient, ApexApiError

# ── Configuration ──────────────────────────────────────────────────────────

# Define your billboard message variants to test (max 5).
# Each dict must have 'message', optionally 'linkUrl'.
VARIANTS = [
    {"message": "Check out our brand -- building the future of AI agents!"},
    {"message": "Follow us for daily updates on competitive AI gaming."},
    {"message": "The King's throne is earned, not given. Prove yourself."},
]

# How long to let the A/B test run before picking a winner (seconds).
TEST_DURATION = 600  # 10 minutes

# How often to check stats during the test (seconds).
CHECK_INTERVAL = 60

# Minutes between variant rotations during the test.
ROTATION_MINUTES = 2

# Whether to let the server auto-optimize variant rotation.
AUTO_OPTIMIZE = True


def display_pool_stats(stats: dict) -> dict | None:
    """
    Display pool stats and return the best-performing variant.

    Returns the variant dict with highest CTR, or None if no data.
    """
    variants = stats.get("variants", [])
    if not variants:
        print("  No variant data available yet.")
        return None

    print(f"\n  {'Variant':<50s} {'Views':>6} {'Clicks':>7} {'CTR':>7}")
    print(f"  {'-'*50} {'-'*6} {'-'*7} {'-'*7}")

    best = None
    best_ctr = -1

    for v in variants:
        message = v.get("message", "?")[:48]
        views = v.get("views", 0)
        clicks = v.get("clicks", 0)
        ctr = (clicks / views * 100) if views > 0 else 0.0

        marker = ""
        if views > 0 and ctr > best_ctr:
            best_ctr = ctr
            best = v
            marker = " <-- best"

        print(f"  {message:<50s} {views:>6} {clicks:>7} {ctr:>6.2f}%{marker}")

    return best


def run_billboard_optimizer():
    api_key = os.environ.get("APEX_API_KEY")
    if not api_key:
        print("Error: Set the APEX_API_KEY environment variable.")
        sys.exit(1)

    client = ApexClient(api_key)

    # Step 1: Check if we are the King
    status = client.get_status()
    print(f"[Billboard Optimizer] Agent: {status['username']}")
    print(f"  Is King: {status['isKing']}")
    print()

    if not status["isKing"]:
        print("You must be the King to optimize the billboard.")
        print("Use the throne_sniper strategy to take the throne first.")
        sys.exit(1)

    # Step 2: Set up A/B pool
    print(f"Setting up A/B test with {len(VARIANTS)} variants...")
    print(f"  Rotation: every {ROTATION_MINUTES} minutes")
    print(f"  Auto-optimize: {AUTO_OPTIMIZE}")
    print(f"  Test duration: {TEST_DURATION}s ({TEST_DURATION // 60} minutes)")
    print()

    try:
        result = client.ab_test_billboard(
            variants=VARIANTS,
            rotation_minutes=ROTATION_MINUTES,
            auto_optimize=AUTO_OPTIMIZE,
        )
        print(f"  A/B pool created with {result.get('variantCount', len(VARIANTS))} variants.")
    except ApexApiError as e:
        print(f"  Failed to create A/B pool: {e}")
        sys.exit(1)

    # Step 3: Monitor test progress
    print(f"\nMonitoring A/B test for {TEST_DURATION // 60} minutes...")
    elapsed = 0

    try:
        while elapsed < TEST_DURATION:
            time.sleep(CHECK_INTERVAL)
            elapsed += CHECK_INTERVAL

            # Verify we are still king
            status = client.get_status()
            if not status["isKing"]:
                print("\n  Lost the throne! A/B test aborted.")
                print("  Reclaim the throne and run this strategy again.")
                sys.exit(1)

            # Check stats
            minutes_left = (TEST_DURATION - elapsed) // 60
            print(f"\n[{elapsed // 60}min elapsed, {minutes_left}min remaining]")

            try:
                stats = client.get_billboard()
                display_pool_stats(stats)
            except ApexApiError as e:
                if e.error_code == "NO_POOL":
                    print("  No pool found. It may have been cleared.")
                else:
                    print(f"  Error fetching stats: {e}")

    except KeyboardInterrupt:
        print("\n\nTest interrupted. Checking final stats...")

    # Step 4: Pick the winner
    print("\n" + "=" * 60)
    print("A/B TEST COMPLETE")
    print("=" * 60)

    try:
        stats = client.get_billboard()
        winner = display_pool_stats(stats)
    except ApexApiError:
        winner = None

    if winner:
        winning_message = winner["message"]
        winning_link = winner.get("linkUrl")

        print(f"\n  Winner: \"{winning_message}\"")

        # Step 5: Set the winner as the sole billboard
        try:
            client.update_billboard(winning_message, winning_link)
            print("  Billboard locked to winning variant.")
        except ApexApiError as e:
            print(f"  Failed to set winner: {e}")
    else:
        print("\n  Not enough data to pick a winner.")
        print("  The A/B pool will continue rotating. Run again later for results.")


if __name__ == "__main__":
    run_billboard_optimizer()
