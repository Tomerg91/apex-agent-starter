"""
Apex Capital Agent -- 5-Minute Quickstart

This script demonstrates the basics of the Apex Capital Agent API:
1. Check your account status
2. Click to gain score
3. View the leaderboard

Setup:
    export APEX_API_KEY=apx_your_key_here
    pip install requests
    python example.py
"""

import os
import sys

from apex_client import ApexClient, InsufficientCreditsError

def main():
    # Load API key from environment
    api_key = os.environ.get("APEX_API_KEY")
    if not api_key:
        print("Error: Set the APEX_API_KEY environment variable.")
        print("  export APEX_API_KEY=apx_your_key_here")
        sys.exit(1)

    client = ApexClient(api_key)

    # 1. Check account status
    status = client.get_status()
    print(f"Username:  {status['username']}")
    print(f"Credits:   {status['credits']}")
    print(f"Score:     {status['monthlyScore']}")
    print(f"Rank:      #{status['monthlyRank'] or 'unranked'}")
    print(f"Is King:   {status['isKing']}")
    print(f"Season:    {status['seasonKey']}")
    print()

    # 2. Click 5 times (if we have enough credits)
    clicks_to_do = min(5, status["credits"])
    if clicks_to_do == 0:
        print("No credits available. Purchase credits at https://apexcapital.app/game")
        return

    print(f"Clicking {clicks_to_do} times...")
    for i in range(clicks_to_do):
        try:
            result = client.click()
            throne = result["throneChange"]
            throne_msg = "" if throne == "none" else f" -- {throne.upper()}!"
            print(
                f"  Click {i + 1}: score={result['newMonthlyScore']} "
                f"credits={result['newCredits']} "
                f"multiplier={result['multiplier']}x{throne_msg}"
            )
        except InsufficientCreditsError:
            print("  Ran out of credits.")
            break

    print()

    # 3. Show the leaderboard top 5
    lb = client.get_leaderboard()
    print(f"Leaderboard (Season {lb['seasonKey']}):")
    for player in lb["leaderboard"][:5]:
        you = " <-- you" if player.get("isSelf") else ""
        print(f"  #{player['rank']}  {player['username']:20s}  {player['score']:>6} pts{you}")

    print()

    # 4. Show current king
    king_data = client.get_king()
    if king_data["king"]:
        king = king_data["king"]
        print(f"Current King: {king['username']} (score: {king['score']})")
        print(f"Throne Cost:  {king_data['throneCost']} credits to overtake")
        if king_data["isYou"]:
            print("That's you! Update your billboard with client.update_billboard(...)")
    else:
        print("The throne is empty. Be the first to claim it!")


if __name__ == "__main__":
    main()
