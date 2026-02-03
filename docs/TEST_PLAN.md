# AI Team System v4.0 - Test Plan

**Version:** 1.0  
**Created:** 2026-02-03  
**Status:** Draft  
**Tester:** AI Team + Manual Verification

---

## 1. Test Overview

### 1.1 Scope
ทดสอบฟีเจอร์ใหม่ทั้งหมดใน AI Team System v4.0:
- Multi-Agent Standby System
- Agent Reporter (status reporting)
- Agent Sync (stale detection)
- Retry Queue
- Audit Logging
- Real Spawn with retry logic

### 1.2 Test Environment
```
Location: /Users/ngs/Herd/ai-team-system
Database: team.db (use test data)
OpenClaw: Gateway must be running
Timezone: Asia/Bangkok (UTC+7)
```

### 1.3 Test Data Setup
```bash
# Create test task
cd /Users/ngs/Herd/ai-team-system
python3 team_db.py task create "TEST: Spawn Manager" \
  --project TEST-001 \
  --working-dir /Users/ngs/Herd/nurse-ai \
  --assign solo-dev \
  --expected-outcome "Test spawn functionality" \
  --prerequisites "- [ ] Test environment ready" \
  --acceptance "- [ ] Spawn successful"
```

---

## 2. Test Cases

### Phase 1: Unit Tests (Individual Components)

#### TC-001: Agent Reporter - Start Command
**Objective:** Test agent start reporting
**Steps:**
1. Run: `python3 agent_reporter.py start --agent test-agent --task TEST-001`
2. Check database: `SELECT status, current_task_id FROM agents WHERE id='test-agent'`
3. Check audit_log: `SELECT * FROM audit_log WHERE event_type='STATUS_CHANGE'`

**Expected Result:**
- Agent status = 'active'
- Agent current_task_id = 'TEST-001'
- Task status = 'in_progress'
- Audit log entry created

**Pass Criteria:** All checks pass

---

#### TC-002: Agent Reporter - Heartbeat Command
**Objective:** Test heartbeat updates timestamp
**Steps:**
1. Note current last_heartbeat: `SELECT last_heartbeat FROM agents WHERE id='test-agent'`
2. Run: `python3 agent_reporter.py heartbeat --agent test-agent`
3. Check new last_heartbeat

**Expected Result:**
- last_heartbeat updated to current time

**Pass Criteria:** Timestamp changed

---

#### TC-003: Agent Reporter - Progress Command
**Objective:** Test progress reporting
**Steps:**
1. Run: `python3 agent_reporter.py progress --agent test-agent --task TEST-001 --progress 50 --message "Halfway"`
2. Check task: `SELECT progress, notes FROM tasks WHERE id='TEST-001'`

**Expected Result:**
- Task progress = 50
- Notes contain "Halfway"

**Pass Criteria:** Progress and notes updated

---

#### TC-004: Agent Reporter - Complete Command
**Objective:** Test task completion reporting
**Steps:**
1. Run: `python3 agent_reporter.py complete --agent test-agent --task TEST-001 --message "Done"`
2. Check agent: `SELECT status, current_task_id FROM agents WHERE id='test-agent'`
3. Check task: `SELECT status FROM tasks WHERE id='TEST-001'`
4. Check audit_log

**Expected Result:**
- Agent status = 'idle'
- Agent current_task_id = NULL
- Task status = 'review'
- Audit log entry created

**Pass Criteria:** All checks pass

---

#### TC-005: Audit Log - Event Recording
**Objective:** Test all event types are logged
**Steps:**
1. Run various reporter commands
2. Run: `python3 audit_log.py --recent 20`
3. Check database: `SELECT DISTINCT event_type FROM audit_log`

**Expected Result:**
- Events: AGENT_SPAWN, STATUS_CHANGE, TASK_UPDATE, HEARTBEAT

**Pass Criteria:** All event types present

---

#### TC-006: Retry Queue - Add and Process
**Objective:** Test retry queue functionality
**Steps:**
1. Add item: Create a mock failed spawn in retry_queue
2. Run: `python3 retry_queue.py --stats`
3. Run: `python3 retry_queue.py --process`
4. Check: `python3 retry_queue.py --stats`

**Expected Result:**
- Stats show pending items
- After process, items completed or failed

**Pass Criteria:** Queue processes correctly

---

#### TC-007: Agent Sync - Stale Detection
**Objective:** Test stale agent detection
**Steps:**
1. Manually set agent heartbeat to old time:
   ```sql
   UPDATE agents SET last_heartbeat = datetime('now', '-1 hour') WHERE id='test-agent';
   ```
2. Run: `python3 agent_sync.py --run`
3. Check agent status

**Expected Result:**
- Agent status = 'idle'
- Agent current_task_id = NULL
- Audit log shows STALE_DETECTED

**Pass Criteria:** Stale agent reset

---

### Phase 2: Integration Tests (Component Interaction)

#### TC-101: Spawn Manager → Database Update
**Objective:** Test spawn updates database correctly
**Steps:**
1. Create test task with assignee
2. Run: `python3 spawn_manager_fixed.py`
3. Check:
   - Task status changed to 'in_progress'
   - Agent status changed to 'active'
   - Audit log entry created

**Expected Result:** Database reflects spawned state

**Pass Criteria:** All database fields updated

---

#### TC-102: Full Workflow - Spawn to Complete
**Objective:** Test complete workflow
**Steps:**
1. Spawn manager spawns agent
2. Agent reports start
3. Agent sends heartbeats (simulate 2-3)
4. Agent reports progress
5. Agent reports complete
6. Check final state

**Expected Result:**
- Task: todo → in_progress → review
- Agent: idle → active → idle
- Audit log: Complete trail

**Pass Criteria:** Workflow completes correctly

---

#### TC-103: Retry Queue with Failed Spawn
**Objective:** Test spawn failure and retry
**Steps:**
1. Configure spawn to fail (mock)
2. Run spawn manager
3. Check retry_queue has item
4. Wait for retry cron (or run manually)
5. Check retry attempts

**Expected Result:**
- Failed spawn queued
- Retried up to 3 times
- Audit log shows retries

**Pass Criteria:** Retry mechanism works

---

#### TC-104: Agent Sync with Active Agent
**Objective:** Test sync doesn't affect active agents
**Steps:**
1. Spawn agent
2. Agent reports start
3. Agent sends heartbeat (recent)
4. Run agent_sync
5. Check agent not reset

**Expected Result:**
- Agent remains active
- Task remains in_progress

**Pass Criteria:** Active agents preserved

---

### Phase 3: End-to-End Tests (Full System)

#### TC-201: Multi-Agent Standby Spawn
**Objective:** Test spawning all 9 agents
**Steps:**
1. Run: `python3 multi_agent_standby.py --spawn-all`
2. Check active sessions: `openclaw sessions_list`
3. Verify all 9 agents spawned
4. Check database: `SELECT id, status FROM agents`

**Expected Result:**
- 9 active sessions
- All agents in standby mode

**Pass Criteria:** All agents spawned

---

#### TC-202: Agent Communication
**Objective:** Test agent-to-agent communication
**Steps:**
1. Spawn PM and Dev agents
2. Send message from PM to Dev
3. Check agent receives message
4. Verify in database: `SELECT * FROM agent_communications`

**Expected Result:**
- Message delivered
- Database record created

**Pass Criteria:** Communication works

---

#### TC-203: Stale Agent Auto-Reset
**Objective:** Test full stale detection flow
**Steps:**
1. Spawn agent with task
2. Agent reports start
3. Wait 30+ minutes (or manually set old heartbeat)
4. Run agent_sync (or wait for cron)
5. Check agent reset and task blocked

**Expected Result:**
- Agent reset to idle
- Task blocked with reason
- Notifications sent

**Pass Criteria:** Auto-reset works

---

#### TC-204: Cron Job Integration
**Objective:** Test all cron jobs work together
**Steps:**
1. Setup all cron jobs
2. Create test tasks
3. Wait for cron cycles (or trigger manually)
4. Check:
   - Spawn manager spawns
   - Agent sync runs
   - Retry queue processes
   - Health monitor checks

**Expected Result:**
- All cron jobs execute
- No conflicts
- Database consistent

**Pass Criteria:** All jobs work together

---

### Phase 4: Edge Cases & Error Handling

#### TC-301: Duplicate Spawn Prevention
**Objective:** Test spawn manager prevents duplicates
**Steps:**
1. Spawn agent for task
2. Immediately run spawn manager again
3. Check no duplicate spawned

**Expected Result:**
- Second spawn skipped
- Message: "Already has active session"

**Pass Criteria:** Duplicates prevented

---

#### TC-302: Missing Working Directory
**Objective:** Test validation of working_dir
**Steps:**
1. Create task with invalid working_dir
2. Run spawn manager
3. Check error handling

**Expected Result:**
- Spawn skipped
- Error: "Working dir does not exist"

**Pass Criteria:** Validation works

---

#### TC-303: Network Failure During Spawn
**Objective:** Test retry on network failure
**Steps:**
1. Simulate network failure
2. Run spawn manager
3. Check retry queue
4. Restore network
5. Run retry queue

**Expected Result:**
- Failed spawn queued
- Retry successful after restore

**Pass Criteria:** Network resilience

---

#### TC-304: Database Lock/Conflict
**Objective:** Test concurrent database access
**Steps:**
1. Run multiple operations simultaneously
2. Check for database locks
3. Verify data integrity

**Expected Result:**
- No deadlocks
- Data consistent

**Pass Criteria:** Concurrent access safe

---

## 3. Test Schedule

| Phase | Duration | Tester |
|-------|----------|--------|
| Phase 1: Unit Tests | 1 hour | Automated + Manual |
| Phase 2: Integration Tests | 2 hours | Manual |
| Phase 3: End-to-End Tests | 3 hours | Manual |
| Phase 4: Edge Cases | 1 hour | Manual |
| **Total** | **7 hours** | |

---

## 4. Test Execution

### Pre-Test Checklist
- [ ] OpenClaw gateway running
- [ ] Database backup created
- [ ] Test environment isolated
- [ ] Telegram bot configured (optional)

### Test Execution Commands
```bash
# 1. Backup database
cp team.db team.db.backup

# 2. Run unit tests
python3 -m pytest tests/unit/ -v

# 3. Run integration tests
python3 test_plan.py --phase integration

# 4. Run end-to-end tests
python3 test_plan.py --phase e2e

# 5. Run edge case tests
python3 test_plan.py --phase edge

# 6. Generate report
python3 test_plan.py --report
```

---

## 5. Success Criteria

### Must Pass (Critical)
- [ ] TC-001: Agent start reporting
- [ ] TC-002: Heartbeat updates
- [ ] TC-004: Task completion
- [ ] TC-007: Stale detection
- [ ] TC-101: Spawn database update
- [ ] TC-102: Full workflow
- [ ] TC-301: Duplicate prevention

### Should Pass (Important)
- [ ] TC-003: Progress reporting
- [ ] TC-005: Audit logging
- [ ] TC-006: Retry queue
- [ ] TC-103: Retry with failure
- [ ] TC-201: Multi-agent spawn
- [ ] TC-302: Working dir validation

### Nice to Pass (Enhancement)
- [ ] TC-104: Sync with active agents
- [ ] TC-202: Agent communication
- [ ] TC-203: Auto-reset flow
- [ ] TC-204: Cron integration
- [ ] TC-303: Network failure
- [ ] TC-304: Concurrent access

---

## 6. Post-Test Actions

### If All Pass
1. Mark v4.0.0 as stable
2. Update production deployment
3. Archive test plan

### If Issues Found
1. Create bug reports
2. Fix and retest
3. Update documentation

---

**Last Updated:** 2026-02-03 09:20 AM  
**Test Lead:** Orchestrator Agent  
**Status:** Ready for execution
