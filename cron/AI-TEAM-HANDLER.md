# 🤖 AI Team Cron Handler
# This file handles cron events for AI Team monitoring
# Place in: ~/clawd/cron/ or reference in HEARTBEAT.md

## Cron Job Handlers

When receiving cron events, execute the corresponding monitoring script:

### Event: "🤖 AI Team: Check agent heartbeats"
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh heartbeat
```

### Event: "🤖 AI Team: Check deadlines"
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh deadlines
```

### Event: "🤖 AI Team: Generate hourly report"
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh hourly
```

### Event: "🤖 AI Team: Daily morning report"
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh daily
```

### Event: "🤖 AI Team: Daily evening summary"
```bash
~/clawd/monitoring/scripts/ai-team-monitor.sh daily
```

## Active Cron Jobs

| ID | Name | Schedule | Status |
|----|------|----------|--------|
| 1991adcd... | ai-team-heartbeat | Every 5 min | ✅ Active |
| 1af2d79d... | ai-team-deadlines | Every 30 min | ✅ Active |
| 6dcecf29... | ai-team-hourly-report | Hourly | ✅ Active |
| 982571e6... | ai-team-daily-morning | 08:00 daily | ✅ Active |
| 4e7b9c8d... | ai-team-daily-evening | 18:00 daily | ✅ Active |

## Manual Execution

```bash
# Check all now
~/clawd/monitoring/scripts/ai-team-monitor.sh heartbeat
~/clawd/monitoring/scripts/ai-team-monitor.sh blocked
~/clawd/monitoring/scripts/ai-team-monitor.sh deadlines

# Generate reports
~/clawd/monitoring/scripts/ai-team-monitor.sh hourly
~/clawd/monitoring/scripts/ai-team-monitor.sh daily
```
