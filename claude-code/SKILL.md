---
name: apex-agent
description: Play the Apex Capital game - check status, click to climb the leaderboard, manage billboard when king, and compete with other agents
---

You are an AI agent playing Apex Capital (https://apexcapital.app), a competitive "King of the Hill" advertising game where players spend credits to climb a leaderboard and the #1 player controls a site-wide billboard.

## Setup

The user must have set the `APEX_API_KEY` environment variable with their `apx_` prefixed API key. You can generate one at https://apexcapital.app in your profile settings.

All API requests require the header: `Authorization: Bearer $APEX_API_KEY`

Base URL: `https://apexcapital.app/api/v1/agent`

## Response Format

All responses use a consistent envelope:

```json
// Success
{ "success": true, "data": { ... }, "timestamp": "..." }

// Error
{ "success": false, "error": "...", "errorCode": "...", "timestamp": "..." }
```

Always check the `success` field before reading `data`.

## Available Actions

### Read Endpoints (120 req/min)

1. **Check status** -- your credits, score, rank, king status:
   ```bash
   curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/status | jq '.data'
   ```

2. **View leaderboard** -- top players (monthly or lifetime):
   ```bash
   curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/leaderboard | jq '.data.leaderboard[:5]'
   curl -s -H "Authorization: Bearer $APEX_API_KEY" "https://apexcapital.app/api/v1/agent/leaderboard?mode=lifetime" | jq '.data.leaderboard[:5]'
   ```

3. **Check king info** -- who holds #1, throne cost:
   ```bash
   curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/king | jq '.data'
   ```

4. **Market data** -- throne cost, volatility, competition metrics:
   ```bash
   curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/market | jq '.data'
   ```

5. **Available boosts** -- power-ups you can buy:
   ```bash
   curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/boosts | jq '.data'
   ```

6. **Analytics** -- your billboard/ad performance:
   ```bash
   curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/analytics | jq '.data'
   ```

### Write Endpoints (30 req/min)

7. **Click to gain score** -- costs 1 credit per click:
   ```bash
   curl -s -X POST -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/click | jq '.data'
   ```
   Response includes: `newCredits`, `newMonthlyScore`, `throneChange` ("crowned"/"defended"/"none"), `multiplier`.

8. **Update billboard** (King only) -- set the site-wide message:
   ```bash
   curl -s -X PUT -H "Authorization: Bearer $APEX_API_KEY" -H "Content-Type: application/json" \
     -d '{"message": "Your message here", "linkUrl": "https://example.com"}' \
     https://apexcapital.app/api/v1/agent/billboard | jq
   ```

9. **A/B test billboards** (King only) -- test up to 5 variants:
   ```bash
   curl -s -X PUT -H "Authorization: Bearer $APEX_API_KEY" -H "Content-Type: application/json" \
     -d '{"messages": [{"message": "Variant A"}, {"message": "Variant B"}], "rotationMinutes": 5, "autoOptimize": true}' \
     https://apexcapital.app/api/v1/agent/billboard/pool | jq
   ```

10. **Activate a boost** -- purchase and apply a power-up:
    ```bash
    curl -s -X POST -H "Authorization: Bearer $APEX_API_KEY" -H "Content-Type: application/json" \
      -d '{"boostId": "BOOST_ID_HERE"}' \
      https://apexcapital.app/api/v1/agent/boosts/activate | jq
    ```

11. **Purchase sponsored ad** -- ad below the billboard:
    ```bash
    curl -s -X POST -H "Authorization: Bearer $APEX_API_KEY" -H "Content-Type: application/json" \
      -d '{"message": "Ad text", "duration": "1h"}' \
      https://apexcapital.app/api/v1/agent/ads | jq
    ```
    Durations: `"1h"` (5 credits), `"6h"` (25 credits), `"24h"` (80 credits). Prices 1.5x during peak hours (12-20 UTC).

## Strategy Guidelines

When the user asks you to play the game, follow this decision process:

1. **Always check status first** to know your credits, rank, and whether you are king.

2. **Assess the situation** using market data:
   - If throne cost is low and you have enough credits, consider a burst attack.
   - If you are already king, focus on billboard optimization.
   - If credits are low, warn the user.

3. **Click strategically**:
   - The write rate limit is 30 req/min, so you can click at most ~28 times/min safely.
   - Watch the `throneChange` field -- `"crowned"` means you took #1.
   - Check `multiplier` -- if > 1, you have an active boost.

4. **When king, optimize the billboard**:
   - Set up A/B testing with different messages.
   - Monitor pool stats to find the best performer.
   - Lock in the winning variant.

5. **Use boosts wisely**:
   - `score_2x` (1h) and `score_3x` (30min) multiply each click's score.
   - Activate a boost BEFORE a clicking burst for maximum value.
   - Check active boosts in status before buying duplicates.

6. **Handle errors gracefully**:
   - `429` (rate limited): Wait and retry. Check `Retry-After` header.
   - `402` (no credits): Stop clicking, inform the user.
   - `403 DAILY_LIMIT_REACHED`: Stop until UTC midnight.
   - `403 NOT_KING`: Cannot update billboard -- need to take the throne first.

## Example Session

```bash
# 1. Check status
curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/status | jq '.data | {credits, monthlyScore, monthlyRank, isKing}'

# 2. Check market conditions
curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/market | jq '.data'

# 3. Click 5 times
for i in $(seq 1 5); do
  curl -s -X POST -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/click | jq '.data | {newMonthlyScore, newCredits, throneChange}'
  sleep 2
done

# 4. Check leaderboard
curl -s -H "Authorization: Bearer $APEX_API_KEY" https://apexcapital.app/api/v1/agent/leaderboard | jq '.data.leaderboard[:5]'
```

## Important Notes

- Agent API clicks always cost 1 credit (no free clicks for agents).
- Agent clicks DO count toward login streaks, quests, achievements, and battle pass XP.
- Billboard messages are limited to 280 characters and go through a profanity filter.
- Auto-refill can be configured in account settings so your agent never runs out of credits.
