# ERD (team.db)

```mermaid
erDiagram
  projects ||--o{ tasks : has
  agents ||--o{ tasks : assigned_to
  tasks ||--o{ task_history : logs
  agents ||--o{ task_history : acts

  tasks ||--o{ task_dependencies : parent
  tasks ||--o{ task_dependencies : child

  agents ||--|| agent_context : has
  agents ||--|| agent_working_memory : has
  agents ||--o{ agent_communications : sends
  tasks ||--o{ agent_communications : discusses

  projects {
    text id PK
    text name
    text status
    datetime start_date
    datetime end_date
  }

  agents {
    text id PK
    text name
    text role
    text status
    text current_task_id FK
    datetime last_heartbeat
    text health_status
  }

  tasks {
    text id PK
    text project_id FK
    text assignee_id FK
    text title
    text status
    text priority
    int progress
    datetime created_at
    datetime started_at
    datetime completed_at
    text prerequisites
    text acceptance_criteria
    text expected_outcome
    text working_dir
    text blocked_reason
    datetime blocked_at
    text review_feedback
    datetime review_feedback_at
    text runtime
    datetime runtime_at
  }

  task_history {
    int id PK
    text task_id FK
    text agent_id FK
    text action
    text old_status
    text new_status
    int old_progress
    int new_progress
    datetime timestamp
    text notes
  }

  task_dependencies {
    int id PK
    text task_id FK
    text depends_on_task_id FK
    text dependency_type
    datetime created_at
  }

  agent_context {
    text agent_id PK, FK
    text context
    text learnings
    text preferences
    datetime last_updated
  }

  agent_working_memory {
    text agent_id PK, FK
    text current_task_id FK
    text working_notes
    text blockers
    text next_steps
    datetime last_updated
  }

  agent_communications {
    int id PK
    text from_agent_id FK
    text to_agent_id FK
    text task_id FK
    text message_type
    text message
    int is_read
    datetime timestamp
  }
```

หมายเหตุ:
- ERD นี้โฟกัสเฉพาะส่วน “AI Team System” หลัก ๆ (ไม่รวม shift swap / orchestrator / notifications ทั้งหมด)
- สถานะสำคัญของ task: `backlog`, `todo`, `in_progress`, `review`, `reviewing`, `done`, `blocked`, `info_needed`

