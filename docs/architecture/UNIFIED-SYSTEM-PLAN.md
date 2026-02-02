# 🏗️ Unified AI Team System - Architecture Plan

**Version:** 1.0.0  
**Date:** 2026-02-02  
**Status:** PLANNED (Future Implementation)  
**Priority:** Medium  
**Estimated Effort:** 10 weeks (2.5 months)  

> 📝 **Note:** This is a planned feature for future implementation. Not currently active.
> 
> **Trigger for starting:** When AI-TEAM-SYSTEM and BMAD Workflows need integration, or when step-by-step workflow tracking becomes critical.  

---

## 📋 Executive Summary

ระบบ Unified AI Team ผสมผสานจุดแข็งของสองระบบ:
- **AI-TEAM-SYSTEM:** Agent personas, database state, monitoring
- **BMAD Workflows:** Step-file architecture, output artifacts, process rigor

**ผลลัพธ์:** Agent ที่มีบุคลิก ทำงานตาม workflow ละเอียด เก็บ state ในฐานข้อมูล สร้าง artifacts เป็นเอกสาร

---

## 🎯 System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED AI TEAM SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│  │   AGENTS     │────▶│  WORKFLOWS   │────▶│   OUTPUTS    │            │
│  │  (Personas)  │     │  (Steps)     │     │ (Artifacts)  │            │
│  └──────────────┘     └──────────────┘     └──────────────┘            │
│         │                    │                    │                     │
│         ▼                    ▼                    ▼                     │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                    STATE LAYER (SQLite)                       │      │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐     │      │
│  │  │ agents  │  │  tasks  │  │workflows│  │  artifacts   │     │      │
│  │  │ state   │  │  state  │  │execution│  │   registry   │     │      │
│  │  └─────────┘  └─────────┘  └─────────┘  └──────────────┘     │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                      DASHBOARD (PHP/Vue)                      │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │      │
│  │  │  Agents  │  │  Tasks   │  │Workflows │  │ Artifacts│      │      │
│  │  │  Status  │  │  Board   │  │ Progress │  │  Viewer  │      │      │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Architecture Components

### 1. Agent Layer (Personas)

```yaml
# Agent Definition Structure
agent:
  id: "agent-pm-001"
  name: "John"
  role: "Product Manager"
  icon: "📋"
  model: "anthropic/claude-opus-4-5"
  
  # Persona (from AI-TEAM)
  persona:
    traits: ["strategic", "user-focused", "business-driven"]
    communication: "Thai for user, English for docs"
    strengths: ["roadmap planning", "prioritization", "stakeholder management"]
    
  # Workflow Capabilities (from BMAD)
  workflows:
    can_execute:
      - "create-prd"
      - "create-product-brief"
      - "research"
    preferred_mode:
      "create-prd": "create"  # or "validate", "edit"
    
  # State
  status: "idle"  # idle, active, executing_workflow
  current_workflow_execution_id: null
  current_task_id: null
  
  # Context (persistent memory)
  context:
    learnings: []  # สิ่งที่เรียนรู้จากงานก่อน
    preferences: {}  # preferences ที่สะสม
    last_workflow: null  # workflow ล่าสุดที่ทำ
```

### 2. Workflow Layer (Step-Files)

```yaml
# Workflow Definition
workflow:
  id: "create-prd"
  name: "Create Product Requirements Document"
  category: "2-plan-workflows"
  
  # Modes (from BMAD)
  modes:
    create:
      steps_path: "./steps-c/"
      total_steps: 12
    validate:
      steps_path: "./steps-v/"
      total_steps: 13
    edit:
      steps_path: "./steps-e/"
      total_steps: 4
  
  # Output Artifact
  output:
    type: "document"
    template: "./templates/prd-template.md"
    destination: "{project-root}/_output/prd-{timestamp}.md"
    
  # Agent Assignment
  default_agent: "pm"
  can_be_executed_by: ["pm", "analyst"]
  
  # Requirements
  requires:
    - "product-brief"  # ต้องมี brief ก่อน
  
  # Estimated Duration
  estimated_duration:
    create: "2-4 hours"
    validate: "1-2 hours"
    edit: "30-60 minutes"
```

### 3. State Layer (Database)

#### Extended Schema

```sql
-- ============================================
-- EXISTING TABLES (from AI-TEAM)
-- ============================================
-- agents, tasks, projects, task_history, task_dependencies

-- ============================================
-- NEW TABLES for Unified System
-- ============================================

-- Workflow Definitions Registry
CREATE TABLE workflow_definitions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,  -- 1-analysis, 2-plan, etc.
    description TEXT,
    modes TEXT,  -- JSON: ["create", "validate", "edit"]
    default_agent_role TEXT,
    total_steps_create INTEGER,
    total_steps_validate INTEGER,
    total_steps_edit INTEGER,
    output_template_path TEXT,
    estimated_duration_minutes INTEGER,
    prerequisites TEXT,  -- JSON array of workflow_ids
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Workflow Executions (Active + Historical)
CREATE TABLE workflow_executions (
    id TEXT PRIMARY KEY,  -- WF-YYYYMMDD-NNN
    workflow_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    task_id TEXT,  -- optional link to tasks table
    
    -- Execution State
    mode TEXT NOT NULL,  -- create, validate, edit
    status TEXT DEFAULT 'pending',  -- pending, running, paused, completed, failed
    current_step_number INTEGER DEFAULT 0,
    total_steps INTEGER NOT NULL,
    
    -- Progress
    progress_percent INTEGER DEFAULT 0,  -- calculated: (current_step/total_steps)*100
    steps_completed TEXT,  -- JSON array of completed step numbers
    
    -- Input/Output
    input_parameters TEXT,  -- JSON: initial inputs
    output_artifact_path TEXT,  -- path to generated document
    
    -- Timing
    started_at DATETIME,
    completed_at DATETIME,
    estimated_completion_at DATETIME,
    
    -- State Management
    last_step_executed_at DATETIME,
    next_step_id TEXT,  -- which step to load next
    
    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- Step Executions (Detailed Log)
CREATE TABLE step_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_execution_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    step_id TEXT NOT NULL,  -- e.g., "step-02-discovery"
    
    -- Execution Details
    status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
    started_at DATETIME,
    completed_at DATETIME,
    duration_seconds INTEGER,
    
    -- Content
    input_context TEXT,  -- what was provided to the step
    output_summary TEXT,  -- what the step produced
    decisions_made TEXT,  -- JSON: key decisions
    
    -- User Interaction
    required_user_input BOOLEAN DEFAULT FALSE,
    user_input_received TEXT,
    user_input_at DATETIME,
    
    -- Artifacts Produced
    artifacts_created TEXT,  -- JSON array of file paths
    
    FOREIGN KEY (workflow_execution_id) REFERENCES workflow_executions(id)
);

-- Artifacts Registry
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,  -- ART-YYYYMMDD-NNN
    workflow_execution_id TEXT,
    task_id TEXT,
    agent_id TEXT NOT NULL,
    
    -- Artifact Info
    name TEXT NOT NULL,
    type TEXT NOT NULL,  -- prd, ux-design, architecture, code, etc.
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    
    -- Metadata
    version INTEGER DEFAULT 1,
    previous_version_id TEXT,  -- for tracking versions
    checksum TEXT,  -- file hash for integrity
    
    -- Content Summary (for search/indexing)
    summary TEXT,  -- AI-generated summary
    tags TEXT,  -- JSON array
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (workflow_execution_id) REFERENCES workflow_executions(id),
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
);

-- Agent Workflow Capabilities (What can each agent do?)
CREATE TABLE agent_workflow_capabilities (
    agent_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    proficiency_level TEXT DEFAULT 'intermediate',  -- novice, intermediate, expert
    executions_count INTEGER DEFAULT 0,
    success_rate REAL,  -- calculated from history
    preferred_mode TEXT,
    
    PRIMARY KEY (agent_id, workflow_id),
    FOREIGN KEY (agent_id) REFERENCES agents(id),
    FOREIGN KEY (workflow_id) REFERENCES workflow_definitions(id)
);

-- Workflow Dependencies (Prerequisites)
CREATE TABLE workflow_dependencies (
    workflow_id TEXT NOT NULL,
    requires_workflow_id TEXT NOT NULL,
    requires_artifact_type TEXT,  -- e.g., "product-brief"
    is_blocking BOOLEAN DEFAULT TRUE,
    
    PRIMARY KEY (workflow_id, requires_workflow_id)
);

-- Views for Dashboard
CREATE VIEW v_workflow_execution_status AS
SELECT 
    we.id as execution_id,
    we.workflow_id,
    wd.name as workflow_name,
    we.agent_id,
    a.name as agent_name,
    we.mode,
    we.status,
    we.current_step_number,
    we.total_steps,
    we.progress_percent,
    we.started_at,
    we.estimated_completion_at,
    we.output_artifact_path,
    CASE 
        WHEN we.status = 'running' THEN 'active'
        WHEN we.status IN ('pending', 'paused') THEN 'idle'
        ELSE 'completed'
    END as agent_status_for_dashboard
FROM workflow_executions we
JOIN workflow_definitions wd ON we.workflow_id = wd.id
JOIN agents a ON we.agent_id = a.id;

CREATE VIEW v_agent_workload_with_workflows AS
SELECT 
    a.id as agent_id,
    a.name,
    a.status,
    COUNT(DISTINCT t.id) as active_tasks,
    COUNT(DISTINCT we.id) as active_workflows,
    GROUP_CONCAT(DISTINCT we.workflow_id) as executing_workflows
FROM agents a
LEFT JOIN tasks t ON a.id = t.assignee_id AND t.status IN ('todo', 'in_progress')
LEFT JOIN workflow_executions we ON a.id = we.agent_id AND we.status = 'running'
GROUP BY a.id;
```

### 4. Output Layer (Artifacts)

```
_bmad-output/  (หรือชื่อใหม่: artifacts/)
├── 2026/
│   ├── 02/
│   │   ├── 02/
│   │   │   ├── prd-login-system-v1.md
│   │   │   ├── prd-login-system-v2.md  (edited)
│   │   │   ├── ux-design-dashboard-v1.md
│   │   │   └── architecture-payment-v1.md
│   │   └── 03/
│   │       └── ...
│   └── 03/
│       └── ...
└── index.json  (registry of all artifacts)
```

**Artifact Format:**
```yaml
---
artifact_id: "ART-20260202-001"
workflow_execution_id: "WF-20260202-001"
workflow: "create-prd"
mode: "create"
agent: "agent-pm-001"
agent_name: "John"
created_at: "2026-02-02T14:30:00+07:00"
duration_minutes: 145
steps_completed: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
version: 1
previous_version: null
tags: ["login", "authentication", "v1.0"]
---

# Product Requirements Document: Login System
...
```

### 5. Dashboard Layer

#### Dashboard Components

```
dashboard.php (Unified Dashboard)
├── Header
│   ├── System Status: Healthy/Warning/Critical
│   └── Quick Actions: [Create Task] [Start Workflow] [View Artifacts]
│
├── Tab 1: Agent Status
│   ├── Agent Cards
│   │   ├── Avatar + Name + Role
│   │   ├── Status Badge (idle/active/executing)
│   │   ├── Current Task (if any)
│   │   ├── Current Workflow + Step (if any)
│   │   └── Progress Bar
│   └── Agent Filter: [All] [Idle] [Active] [Executing]
│
├── Tab 2: Task Board (Kanban)
│   ├── Columns: Backlog → Todo → In Progress → Review → Done
│   ├── Task Cards
│   │   ├── Title + Priority
│   │   ├── Assignee
│   │   └── Linked Workflow (if any)
│   └── Drag & Drop
│
├── Tab 3: Workflow Progress
│   ├── Active Executions List
│   │   ├── Workflow Name + Mode
│   │   ├── Executing Agent
│   │   ├── Step X of Y
│   │   ├── Progress Bar
│   │   └── Time Elapsed / Estimated
│   └── Completed Executions
│
├── Tab 4: Artifacts
│   ├── Grid/List View
│   ├── Artifact Cards
│   │   ├── Type Icon (PRD, UX, Arch, etc.)
│   │   ├── Title + Version
│   │   ├── Created By
│   │   └── Preview/Download
│   └── Filter: [Type] [Agent] [Date] [Tag]
│
└── Tab 5: Timeline
    ├── Combined Timeline
    │   ├── Task events
    │   ├── Workflow step completions
    │   └── Artifact creations
    └── Filter by Agent/Workflow/Date
```

---

## 🔄 Execution Flow

### Scenario: Agent Executes Workflow

```
User: "Create PRD for login system"
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: ORCHESTRATOR DECIDES                                 │
└─────────────────────────────────────────────────────────────┘
    ↓
Pattern Analysis: "This requires PRD creation"
    ↓
Select Agent: PM (John) - has create-prd capability
    ↓
Check Prerequisites: Need product brief? → No, brief included
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: CREATE TASK IN DATABASE                              │
└─────────────────────────────────────────────────────────────┘
    ↓
INSERT INTO tasks (id, title, assignee_id, status)
VALUES ('T-20260203-001', 'Create PRD: Login System', 'agent-pm-001', 'todo')
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: AGENT ACCEPTS & STARTS WORKFLOW                      │
└─────────────────────────────────────────────────────────────┘
    ↓
Agent (John) queries: "What workflows can I execute?"
    ↓
SELECT * FROM agent_workflow_capabilities WHERE agent_id = 'agent-pm-001'
→ Can execute: create-prd, create-product-brief, research
    ↓
Agent decides: "I'll use create-prd workflow"
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: CREATE WORKFLOW EXECUTION                            │
└─────────────────────────────────────────────────────────────┘
    ↓
INSERT INTO workflow_executions (
    id, workflow_id, agent_id, task_id, mode, 
    status, total_steps, next_step_id
) VALUES (
    'WF-20260203-001', 'create-prd', 'agent-pm-001', 'T-20260203-001',
    'create', 'running', 12, 'step-01-init'
)
    ↓
UPDATE agents SET 
    status = 'executing_workflow',
    current_workflow_execution_id = 'WF-20260203-001',
    current_task_id = 'T-20260203-001'
WHERE id = 'agent-pm-001'
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: EXECUTE STEPS SEQUENTIALLY                           │
└─────────────────────────────────────────────────────────────┘
    ↓
FOR step_number FROM 1 TO 12:
    ↓
    LOAD step file: steps-c/step-{step_number:02d}-*.md
    ↓
    INSERT INTO step_executions (
        workflow_execution_id, step_number, step_id, status, started_at
    ) VALUES ('WF-20260203-001', step_number, 'step-{step_id}', 'running', NOW())
    ↓
    EXECUTE step content (agent follows instructions)
    ↓
    IF step requires user input:
        PAUSE and wait for input
        UPDATE step_executions SET 
            required_user_input = TRUE,
            status = 'paused'
        NOTIFY user via Telegram: "Need input at step X"
        WAIT for user_response
        UPDATE step_executions SET user_input_received = response
    ↓
    COMPLETE step
    UPDATE step_executions SET 
        status = 'completed',
        completed_at = NOW(),
        duration_seconds = calculated,
        output_summary = summary
    ↓
    UPDATE workflow_executions SET
        current_step_number = step_number,
        progress_percent = (step_number / 12) * 100,
        steps_completed = JSON_APPEND(steps_completed, step_number)
    ↓
    IF step produces artifacts:
        SAVE artifact to disk
        INSERT INTO artifacts (...)
    ↓
    LOAD next step...
    ↓
END FOR
    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: COMPLETION                                           │
└─────────────────────────────────────────────────────────────┘
    ↓
UPDATE workflow_executions SET
    status = 'completed',
    completed_at = NOW(),
    output_artifact_path = 'artifacts/2026/02/03/prd-login-system-v1.md'
WHERE id = 'WF-20260203-001'
    ↓
UPDATE agents SET
    status = 'idle',
    current_workflow_execution_id = NULL,
    total_workflows_completed = total_workflows_completed + 1
WHERE id = 'agent-pm-001'
    ↓
UPDATE tasks SET
    status = 'done',
    completed_at = NOW()
WHERE id = 'T-20260203-001'
    ↓
NOTIFY user via Telegram:
"✅ John completed PRD for Login System
📄 Artifact: prd-login-system-v1.md
⏱️ Duration: 145 minutes
📊 Steps: 12/12 completed"
    ↓
Dashboard auto-refreshes showing:
- Agent John: Idle (last workflow: create-prd)
- Task T-20260203-001: Done
- New Artifact: prd-login-system-v1.md (click to view)
```

---

## 🛠️ Implementation Plan

### Phase 1: Foundation (Week 1-2)

#### 1.1 Database Migration
```sql
-- Create new tables
-- workflow_definitions
-- workflow_executions
-- step_executions
-- artifacts
-- agent_workflow_capabilities
```

#### 1.2 Workflow Registry
```python
# Load all BMAD workflows into database
def register_workflows():
    for workflow_dir in Path('_bmad/bmm/workflows').glob('**/'):
        if (workflow_dir / 'workflow.md').exists():
            parse_workflow_md(workflow_dir)
            insert_into_workflow_definitions(...)
```

#### 1.3 Agent Capabilities Mapping
```sql
-- Link agents to workflows they can execute
INSERT INTO agent_workflow_capabilities (agent_id, workflow_id, proficiency_level)
VALUES
    ('agent-pm-001', 'create-prd', 'expert'),
    ('agent-pm-001', 'create-product-brief', 'expert'),
    ('agent-architect-001', 'create-architecture', 'expert'),
    ('agent-ux-001', 'create-ux-design', 'expert');
```

### Phase 2: Core Engine (Week 3-4)

#### 2.1 Workflow Execution Engine
```python
class WorkflowExecutionEngine:
    def __init__(self, agent_id, workflow_id, mode='create'):
        self.agent = Agent.load(agent_id)
        self.workflow = Workflow.load(workflow_id)
        self.mode = mode
        self.execution_id = self.create_execution_record()
    
    def execute(self):
        for step in self.workflow.get_steps(self.mode):
            self.execute_step(step)
            self.save_state()
    
    def execute_step(self, step):
        # Load step file content
        step_content = step.load_content()
        
        # Agent executes (with persona context)
        result = self.agent.execute(step_content)
        
        # Save step execution record
        self.record_step_completion(step, result)
        
        # Handle user input if required
        if step.requires_user_input:
            self.pause_for_input()
    
    def pause_for_input(self):
        self.update_status('paused')
        self.notify_user()
        # Wait for external trigger to resume
```

#### 2.2 State Persistence
```python
# Save execution state after each step
def save_execution_state(execution_id):
    state = {
        'current_step': current_step,
        'progress_percent': calculate_progress(),
        'completed_steps': completed_steps,
        'agent_context': agent.get_current_context(),
        'last_output': last_step_output
    }
    
    db.execute('''
        UPDATE workflow_executions 
        SET state_json = ?,
            current_step_number = ?,
            progress_percent = ?
        WHERE id = ?
    ''', [json.dumps(state), current_step, progress, execution_id])
```

### Phase 3: Integration (Week 5-6)

#### 3.1 Agent-Workflow Integration
```python
# Modify Agent class
class Agent:
    def can_execute_workflow(self, workflow_id):
        return db.query('''
            SELECT 1 FROM agent_workflow_capabilities
            WHERE agent_id = ? AND workflow_id = ?
        ''', [self.id, workflow_id])
    
    def start_workflow(self, workflow_id, mode='create', task_id=None):
        if not self.can_execute_workflow(workflow_id):
            raise WorkflowNotAllowedError()
        
        engine = WorkflowExecutionEngine(
            agent_id=self.id,
            workflow_id=workflow_id,
            mode=mode
        )
        
        # Link to task if provided
        if task_id:
            engine.link_to_task(task_id)
        
        # Update agent status
        self.status = 'executing_workflow'
        self.current_workflow_execution_id = engine.execution_id
        self.save()
        
        # Start execution (async or sync)
        return engine.execute()
```

#### 3.2 CLI Integration
```bash
# Unified commands
./team_db.py workflow list                    # List available workflows
./team_db.py workflow execute <workflow-id>   # Start workflow
./team_db.py workflow status <execution-id>   # Check progress
./team_db.py workflow resume <execution-id>   # Resume paused workflow

# Agent commands with workflow awareness
./team_db.py agent start-workflow <agent-id> <workflow-id>
./team_db.py agent pause-workflow <execution-id>
./team_db.py agent cancel-workflow <execution-id>
```

### Phase 4: Dashboard (Week 7-8)

#### 4.1 Dashboard API Endpoints
```php
// dashboard.php API endpoints
GET /api/agents/status           // Agent cards data
GET /api/tasks/board             // Kanban board data
GET /api/workflows/executions    // Active + completed workflows
GET /api/workflows/progress/<id> // Real-time progress
GET /api/artifacts/list          // Artifact registry
GET /api/timeline                // Combined timeline

POST /api/workflows/start        // Start new execution
POST /api/workflows/<id>/pause   // Pause execution
POST /api/workflows/<id>/resume  // Resume execution
POST /api/workflows/<id>/input   // Submit user input
```

#### 4.2 Real-Time Updates
```javascript
// WebSocket or polling for real-time updates
setInterval(() => {
    fetch('/api/workflows/progress/' + executionId)
        .then(r => r.json())
        .then(data => {
            updateProgressBar(data.progress_percent);
            updateCurrentStep(data.current_step);
            updateTimeEstimate(data.estimated_completion);
        });
}, 5000);  // Every 5 seconds
```

### Phase 5: Polish (Week 9-10)

#### 5.1 Notifications
- Telegram bot for workflow events
- Email for long-running workflows
- Dashboard alerts for blocked workflows

#### 5.2 Artifact Management
- Version control for artifacts
- Diff viewer between versions
- Search/indexing across artifacts

#### 5.3 Analytics
- Agent performance metrics
- Workflow completion rates
- Step duration analytics
- Bottleneck identification

---

## 📊 Database Schema Summary

### New Tables (9 tables)

| Table | Purpose | Records |
|-------|---------|---------|
| `workflow_definitions` | Registry of all workflows | ~20-30 workflows |
| `workflow_executions` | Active & historical executions | 100s-1000s |
| `step_executions` | Detailed step-by-step log | 1000s-10000s |
| `artifacts` | Output document registry | 100s-1000s |
| `agent_workflow_capabilities` | What agents can do | ~50-100 rows |
| `workflow_dependencies` | Prerequisite chains | ~20-50 rows |
| `v_workflow_execution_status` | Dashboard view | - |
| `v_agent_workload_with_workflows` | Agent workload view | - |

### Total Schema Size
- **Existing:** 5 tables (agents, tasks, projects, task_history, task_dependencies)
- **New:** 6 tables + 2 views
- **Total:** 11 tables + 2 views

---

## 🎯 Success Metrics

### Technical Metrics
- [ ] Agent can execute workflow end-to-end
- [ ] State persists after restart
- [ ] Dashboard shows real-time progress
- [ ] Artifacts generated and tracked
- [ ] Notifications delivered

### User Experience Metrics
- [ ] Workflow completion time vs manual
- [ ] User intervention frequency
- [ ] Artifact quality scores
- [ ] System uptime

### Business Metrics
- [ ] Tasks completed per day
- [ ] Workflow reuse rate
- [ ] Agent utilization
- [ ] Time saved vs old process

---

## 🚀 Deployment Strategy

### Option A: Parallel Run (Recommended)
1. Keep AI-TEAM-SYSTEM running
2. Deploy Unified System alongside
3. Migrate workflows gradually
4. Switch over when stable

### Option B: Big Bang
1. Freeze AI-TEAM-SYSTEM
2. Deploy Unified System
3. Migrate all data
4. Switch immediately

---

## 📝 Next Steps

1. **Review this plan** with stakeholders
2. **Create detailed tickets** for each phase
3. **Set up development branch**
4. **Start Phase 1:** Database migration

---

**Estimated Timeline:** 10 weeks (2.5 months)  
**Team Size:** 1-2 developers  
**Risk Level:** Medium (integration complexity)

**Ready to start Phase 1?** 🚀
