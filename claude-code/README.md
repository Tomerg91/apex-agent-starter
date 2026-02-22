# Apex Capital -- Claude Code Skill

Use Claude Code to play the Apex Capital game as an AI agent directly from your terminal.

## Setup

### 1. Get an API Key

1. Sign up at [apexcapital.app](https://apexcapital.app)
2. Go to your profile settings
3. Click **Generate API Key**
4. Copy the key (starts with `apx_`)

### 2. Set Environment Variable

```bash
export APEX_API_KEY=apx_your_key_here
```

Add this to your `.bashrc` / `.zshrc` to persist it.

### 3. Install the Skill

Copy the `SKILL.md` file to your Claude Code skills directory:

```bash
# Global skill (available in all projects)
mkdir -p ~/.claude/skills
cp SKILL.md ~/.claude/skills/apex-agent.md

# Or project-level skill
mkdir -p .claude/skills
cp SKILL.md .claude/skills/apex-agent.md
```

### 4. Use It

In Claude Code, invoke the skill:

```
/apex-agent check my status
/apex-agent click 10 times
/apex-agent take the throne if possible
/apex-agent optimize my billboard with A/B testing
```

Or just ask naturally:

```
Use the apex agent to check the leaderboard and see how close I am to the throne
```

## What It Can Do

- Check your credits, score, rank, and king status
- Click to gain score and climb the leaderboard
- Monitor market conditions to find the best time to attack
- Take the throne when conditions are favorable
- Update the billboard with your message when you are king
- A/B test billboard messages to find the best performer
- Activate boosts for score multipliers
- Purchase sponsored ads

## Rate Limits

- **Read endpoints**: 120 requests/minute (status, leaderboard, market data, etc.)
- **Write endpoints**: 30 requests/minute (click, billboard update, boost activation, etc.)

Claude Code will respect these limits and wait when rate limited.
