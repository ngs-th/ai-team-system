# AI Team System ERD

> อ้างอิงจาก `team.db` ปัจจุบัน (logical relationships)
> หมายเหตุ: ตารางส่วนใหญ่ไม่ได้ประกาศ `FOREIGN KEY` constraint แบบบังคับใน SQLite แต่มีความสัมพันธ์เชิงตรรกะตามคอลัมน์อ้างอิง

## 1) Core Workflow ERD

```mermaid
erDiagram
    PROJECTS ||--o{ TASKS : "project_id"
    AGENTS ||--o{ TASKS : "assignee_id"
    TASKS ||--o{ TASK_HISTORY : "task_id"
    AGENTS ||--o{ TASK_HISTORY : "agent_id"
    TASKS ||--o{ TASK_DEPENDENCIES : "task_id"
    TASKS ||--o{ TASK_DEPENDENCIES : "depends_on_task_id"

    AGENTS ||--o{ AGENT_CONTEXT : "agent_id"
    AGENTS ||--o{ AGENT_WORKING_MEMORY : "agent_id"
    AGENTS ||--o{ AGENT_COMMUNICATIONS : "from_agent_id"
    AGENTS ||--o{ AGENT_COMMUNICATIONS : "to_agent_id"
    TASKS ||--o{ AGENT_COMMUNICATIONS : "task_id"

    AGENTS ||--o{ NOTIFICATION_LOG : "agent_id"
    TASKS ||--o{ NOTIFICATION_LOG : "task_id"
    AGENTS ||--o{ NOTIFICATION_SETTINGS : "entity_id (agent)"
    PROJECTS ||--o{ NOTIFICATION_SETTINGS : "entity_id (project)"

    AGENTS ||--o{ AUDIT_LOG : "agent_id"
    TASKS ||--o{ AUDIT_LOG : "task_id"

    PROJECTS {
      text id PK
      text name
      text status
    }
    TASKS {
      text id PK
      text project_id
      text assignee_id
      text status
      integer progress
      text prerequisites
      text acceptance_criteria
      text expected_outcome
      text working_dir
    }
    TASK_HISTORY {
      integer id PK
      text task_id
      text agent_id
      text action
      datetime timestamp
    }
    TASK_DEPENDENCIES {
      text task_id PK
      text depends_on_task_id PK
    }
    AGENTS {
      text id PK
      text role
      text model
      text status
      text current_task_id
      datetime last_heartbeat
    }
    AGENT_CONTEXT {
      integer id PK
      text agent_id
      text context
      text learnings
    }
    AGENT_WORKING_MEMORY {
      integer id PK
      text agent_id
      text current_task_id
      text working_notes
      datetime last_updated
    }
    AGENT_COMMUNICATIONS {
      integer id PK
      text from_agent_id
      text to_agent_id
      text task_id
      text message_type
    }
    NOTIFICATION_LOG {
      integer id PK
      text task_id
      text agent_id
      text event_type
      datetime sent_at
    }
    NOTIFICATION_SETTINGS {
      integer id PK
      text entity_type
      text entity_id
      text level
    }
    AUDIT_LOG {
      integer id PK
      text event_type
      text agent_id
      text task_id
      datetime timestamp
    }
```

## 2) Scheduling & Swap ERD

```mermaid
erDiagram
    AGENTS ||--o{ SHIFTS : "agent_id"
    PROJECTS ||--o{ SHIFTS : "project_id"

    AGENTS ||--o{ SWAP_REQUESTS : "requestor_agent_id"
    AGENTS ||--o{ SWAP_REQUESTS : "target_agent_id"
    SHIFTS ||--o{ SWAP_REQUESTS : "requestor_shift_id"
    SHIFTS ||--o{ SWAP_REQUESTS : "target_shift_id"
    SWAP_REQUESTS ||--o{ SWAP_REQUEST_HISTORY : "swap_request_id"
    AGENTS ||--o{ SWAP_REQUEST_HISTORY : "actor_agent_id"

    SHIFTS {
      integer id PK
      text agent_id
      date shift_date
      time start_time
      time end_time
      text shift_type
      text project_id
    }
    SWAP_REQUESTS {
      integer id PK
      text requestor_agent_id
      integer requestor_shift_id
      text target_agent_id
      integer target_shift_id
      text status
      datetime requested_at
    }
    SWAP_REQUEST_HISTORY {
      integer id PK
      integer swap_request_id
      text actor_agent_id
      text action
      datetime timestamp
    }
```

## 3) Operational Tables

```mermaid
erDiagram
    AGENTS ||--o{ AGENT_PRODUCTIVITY_CACHE : "agent_id"
    ORCHESTRATOR_MISSIONS ||--o{ TASKS : "logical mapping (not strict FK)"

    RETRY_QUEUE {
      integer id PK
      text operation
      text status
      integer retry_count
      datetime next_retry_at
    }
    ALERT_HISTORY {
      integer id PK
      text alert_type
      text entity_id
      datetime first_seen
      datetime last_alert
      boolean resolved
    }
    REPORT_SNAPSHOTS {
      integer id PK
      text report_type
      date snapshot_date
      text data_json
    }
    AGENT_PRODUCTIVITY_CACHE {
      integer id PK
      text agent_id
      date calculation_date
      real fairness_score
      text data_json
    }
    ORCHESTRATOR_MISSIONS {
      text id PK
      text goal_type
      text status
      text orchestrator_agent
    }
```
