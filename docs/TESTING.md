# AI Team System - Manual Testing Checklist

## 1. Task Workflow Test

### 1.1 Create Task
```bash
python3 team_db.py task create "TEST-WORKFLOW" \
  --project PROJ-001 \
  --expected-outcome "Test complete workflow" \
  --prerequisites "- [ ] None" \
  --acceptance "- [ ] All tests pass"
```
**✅ Expect:** Task created with ID

### 1.2 Assign Task
```bash
python3 team_db.py task assign TEST-WORKFLOW solo-dev
```
**✅ Expect:** "Task TEST-WORKFLOW assigned to solo-dev"

### 1.3 Start Task
```bash
python3 team_db.py task start TEST-WORKFLOW
```
**✅ Expect:** Status = in_progress

### 1.4 Update Progress (every 30 min)
```bash
python3 team_db.py task progress TEST-WORKFLOW 50
python3 agent_memory_writer.py working solo-dev \
  --task TEST-WORKFLOW \
  --notes "Making progress" \
  --blockers "None" \
  --next "Finish implementation"
```
**✅ Expect:** Progress updated, memory logged

### 1.5 Complete Task
```bash
python3 team_db.py task done TEST-WORKFLOW
```
**✅ Expect:** Status = review (not done!)

### 1.6 Add Learning (MANDATORY)
```bash
python3 agent_memory_writer.py learn solo-dev \
  "Learned how to test the workflow system"
```
**✅ Expect:** Learning added to agent_context

### 1.7 Approve Task (as QA)
```bash
python3 team_db.py task approve TEST-WORKFLOW --reviewer qa
```
**✅ Expect:** Status = done (only if memory was updated!)

---

## 2. Memory System Test

### 2.1 Check Working Memory
```bash
python3 team_db.py agent memory show solo-dev
```
**✅ Expect:** Shows recent working_notes, blockers, next_steps

### 2.2 Check Context & Learnings
```bash
python3 team_db.py agent context solo-dev
```
**✅ Expect:** Shows context + recent learnings

### 2.3 Verify Memory is Required
Try to approve task WITHOUT updating memory:
```bash
# Create new task, don't update memory, try to approve
# Should FAIL with: "Agent did not update working memory!"
```
**✅ Expect:** Approval blocked until memory updated

---

## 3. Notification System Test

### 3.1 Check HTML Stripping
```bash
python3 -c "
from notifications import NotificationManager
nm = NotificationManager('team.db')
print(nm.strip_html('<b>Test</b>'))
# Should print: 'Test' (no HTML)
"
```
**✅ Expect:** "Test" (HTML removed)

### 3.2 Check Notification Format
```bash
python3 -c "
from notifications import NotificationEvent, NotificationManager
nm = NotificationManager('team.db')
msg = nm.format_message(
    NotificationEvent.COMPLETE,
    'T-001', 'Test', 'Barry'
)
print(msg)
"
```
**✅ Expect:** "✅ T-001 | Barry" (no <b> tags)

---

## 4. Spawn Manager Test

### 4.1 Check Duplicate Prevention
```bash
python3 spawn_manager_fixed.py
```
**✅ Expect:** "Skipped: active session exists" (if task already spawned)

### 4.2 Check Spawn Logging
```bash
sqlite3 team.db "SELECT * FROM task_history WHERE action='spawned' ORDER BY timestamp DESC LIMIT 5"
```
**✅ Expect:** Shows recent spawn logs

---

## 5. Health Monitor Test

### 5.1 Run Health Check
```bash
python3 health_monitor_fixed.py --check
```
**✅ Expect:** Shows current status, no errors

### 5.2 Check Smart Alerts
```bash
sqlite3 team.db "SELECT * FROM alert_history ORDER BY first_seen DESC LIMIT 5"
```
**✅ Expect:** Shows tracked alerts (won't alert twice)

---

## 6. Dashboard Test

### 6.1 Open Dashboard
Open `dashboard.php` in browser

**✅ Expect:**
- Kanban board shows 6 columns
- Tasks in correct columns
- No PHP errors
- Checklist renders correctly (no \n visible)
- Card titles show full text on hover

### 6.2 Check Stats
**✅ Expect:** Duration stats show Bangkok time (+7)

---

## 7. Cron Jobs Test

### 7.1 Check Cron Status
```bash
# In main agent session
cron list
```
**✅ Expect:** All AI Team jobs enabled

### 7.2 Check No Duplicate Spawns
Wait 10 minutes, check if same task spawned twice:
```bash
sqlite3 team.db "SELECT task_id, COUNT(*) FROM task_history WHERE action='spawned' AND timestamp > datetime('now', '-1 hour') GROUP BY task_id HAVING COUNT(*) > 1"
```
**✅ Expect:** Empty result (no duplicates)

### 7.3 Check No Alert Spam
```bash
# Check Telegram - should only see one alert per issue
```
**✅ Expect:** No repeated alerts for same issue

---

## 8. Communication Test

### 8.1 Send Message Between Agents
```bash
python3 team_db.py agent comm send solo-dev "Need help with task" \
  --to qa --task T-001
```

### 8.2 Check Message Received
```bash
python3 team_db.py agent comm list qa
```
**✅ Expect:** Message appears in list

---

## Summary

| Test Area | Status |
|-----------|--------|
| Task Workflow | ⬜ |
| Memory System | ⬜ |
| Notifications | ⬜ |
| Spawn Manager | ⬜ |
| Health Monitor | ⬜ |
| Dashboard | ⬜ |
| Cron Jobs | ⬜ |
| Communication | ⬜ |

**All checked?** ✅ System ready for production!
