# สรุปเปรียบเทียบ: Unified AI Team System vs Mission Control

**Date:** 2026-02-03  
**Reference:** 
- `/docs/ANALYSIS-Mission-Control-vs-AI-Team.md` 
- `/docs/architecture/UNIFIED-SYSTEM-PLAN.md`

---

## Executive Summary

Unified AI Team System เป็น **การต่อยอด AI Team System** โดยดูดจุดแข็งจาก Mission Control มาผสมผสาน แต่ยังคงรักษา foundation ที่แข็งแกร่งของ AI Team (automation, reliability, audit trail) ไว้

---

## 1. ตารางเปรียบเทียบ 3 ระบบ

| Aspect | Mission Control | AI Team System (Current) | Unified AI Team (Planned) |
|--------|-----------------|--------------------------|---------------------------|
| **Paradigm** | Pull-based (agents wait) | Push-based (system spawns) | **Hybrid** (configurable) |
| **Primary Interface** | Web Dashboard | CLI | **CLI + Web Dashboard** |
| **Agent Model** | Standby sessions | Spawn on demand | **Both modes supported** |
| **Task Tracking** | Kanban board | Database + CLI | **Kanban + Database** |
| **Workflow System** | ❌ None | ❌ None | **✅ Full step-files** |
| **Agent Chat** | ✅ Chat Panel | ❌ Isolated | **✅ With context** |
| **Personalities** | ✅ SOUL.md | ❌ Roles only | **✅ SOUL.md** |
| **Real-time Updates** | ✅ WebSocket | ❌ Polling | **✅ WebSocket** |
| **Audit Trail** | ❌ None | ✅ Full logging | **✅ Enhanced** |
| **Retry Logic** | ❌ None | ✅ Retry queue | **✅ Per workflow** |
| **Artifact Management** | ❌ Basic | ❌ Manual | **✅ Registry + versions** |
| **Cross-machine** | ✅ File Upload | ❌ Single machine | **✅ Planned** |
| **Auto-assignment** | ❌ Manual/Charlie | ✅ By agent type | **✅ Smart routing** |
| **Working Dir** | ❌ Not enforced | ✅ Mandatory | **✅ Per workflow** |

---

## 2. จุดที่ Unified System ได้รับจาก Mission Control

### 2.1 UX Layer (จากไม่มี → มี)

| Feature | Mission Control | Unified Implementation |
|---------|-----------------|------------------------|
| **Kanban Board** | React + drag-drop | Vue/React + PHP backend |
| **Live Feed** | Real-time events | WebSocket events |
| **Agent Status Cards** | Visual cards | Dashboard tabs |
| **Progress Visualization** | Progress bars | Step-by-step progress |

**ความแตกต่างสำคัญ:**
- Mission Control: Progress ดูที่ agent level
- Unified: Progress ดูที่ **workflow step level** (ละเอียดกว่า)

### 2.2 Agent Experience (จาก Roles → Personalities)

| Aspect | Mission Control | Unified System |
|--------|-----------------|----------------|
| **Agent Identity** | SOUL.md + USER.md + AGENTS.md | SOUL.md สำหรับแต่ละ agent |
| **Chat System** | Chat Panel real-time | Context-aware messaging |
| **Master Agent** | "Charlie" ประสานงาน | Orchestrator + Master Agent |

**ความแตกต่างสำคัญ:**
- Mission Control: Agents คุยกันเองผ่าน Chat Panel
- Unified: Agents คุยกันผ่าน **comm_bridge + context** (structured กว่า)

### 2.3 State Management (จาก Simple → Rich)

| Feature | Mission Control | Unified System |
|---------|-----------------|----------------|
| **Session Linking** | Agent ↔ OpenClaw link | Agent ↔ Workflow Execution link |
| **Task State** | Column in Kanban | Database + Step executions |
| **Persistence** | In-memory + SQLite | Full audit trail |

**ความแตกต่างสำคัญ:**
- Mission Control: State อยู่ที่ session level
- Unified: State อยู่ที่ **step execution level** (rollback ได้)

---

## 3. จุดที่ Unified System ต่างจาก Mission Control

### 3.1 Workflow Engine (ไม่มีใน Mission Control)

```
Mission Control:
Task → Assign → Agent Work → TASK_COMPLETE → Review → Done
     (ไม่มี step ย่อย)

Unified System:
Task → Workflow → Step 1 → Step 2 → ... → Step 12 → Artifact
              (มี step-by-step tracking)
```

**นวัตกรรม:**
- **Step Execution Table:** บันทึกทุก step ที่ทำ
- **Pause/Resume:** หยุดตอนไหนก็ได้ แล้วกลับมาทำต่อ
- **User Input Points:** กำหนดจุดที่ต้องรอ user
- **Artifact Generation:** Output เป็นเอกสาร structured

### 3.2 Automation Level (จาก Manual → Auto)

| Task | Mission Control | Unified System |
|------|-----------------|----------------|
| **Assignment** | Drag-drop หรือรอ Charlie | Auto-route ตาม capability |
| **Progress Update** | Agent พิมพ์เอง | Auto-update ตาม step |
| **Failure Recovery** | Manual retry | Auto-retry per step |
| **Artifact Storage** | Manual upload | Auto-register |

### 3.3 Data Richness (จาก Minimal → Complete)

| Data Point | Mission Control | Unified System |
|------------|-----------------|----------------|
| **Task Fields** | Title, Priority, ID | + Working dir, Prerequisites, Acceptance |
| **Progress Data** | Status only | Step completion %, Time per step |
| **Agent History** | Session-based | Workflow execution history |
| **Artifacts** | File path | Version, Checksum, Summary, Tags |

---

## 4. จุดแข็งที่เก็บจาก AI Team System

### 4.1 Reliability Features (ไม่มีใน Mission Control)

| Feature | AI Team | Unified |
|---------|---------|---------|
| **Retry Queue** | ✅ Cron-based | ✅ Per-workflow retry |
| **Audit Log** | ✅ All events | ✅ + Step events |
| **Health Monitor** | ✅ Auto-detect stale | ✅ + Workflow health |
| **Timezone Aware** | ✅ Asia/Bangkok | ✅ คงไว้ |

### 4.2 CLI-First Philosophy

```
Mission Control: ต้องเปิด Dashboard ถึงจะทำอะไรได้
Unified System: CLI ทำได้ทุกอย่าง + Dashboard เป็น optional
```

**สำคัญ:** Power users ยังใช้ CLI ได้เหมือนเดิม แต่มี Dashboard สำหรับ oversight

### 4.3 Strict Requirements

| Requirement | AI Team | Unified |
|-------------|---------|---------|
| **Working Dir** | Mandatory | **Per-workflow mandatory** |
| **Acceptance Criteria** | Required | **Enforced ทุก artifact** |
| **Prerequisites** | Checklist | **System validate ก่อนเริ่ม** |

---

## 5. สรุปผล: ระบบไหนเหมาะกับใคร

### Mission Control เหมาะกับ:
- ทีมที่ชอบ **visual, hands-on control**
- ต้องการ **ดู agents คุยกัน** แบบ real-time
- ทำงาน **cross-machine** บ่อย
- ชอบ **drag-drop assignment**

### AI Team System (Current) เหมาะกับ:
- ต้องการ **automation สูง** แทบไม่ต้องดูแล
- ทำงาน **คนเดียว** หรือทีมเล็ก
- ชอบ **CLI workflow** เร็วๆ
- ต้องการ **audit trail ครบถ้วน**

### Unified AI Team เหมาะกับ:
- ต้องการ **ทั้ง automation และ visibility**
- ทำงาน **complex workflows** (หลาย step)
- ต้องการ **เก็บ artifacts** เป็นระบบ
- ทีมที่มี **หลาย roles** (PM, Architect, Dev, QA)

---

## 6. Action Items จากการเปรียบเทียบ

### Priority สูง (เริ่มทันที)
1. **สร้าง SOUL.md** ให้แต่ละ agent (จาก Mission Control)
2. **ปรับ Dashboard** เป็น Kanban style (จาก Mission Control)
3. **สร้าง Workflow Engine** (จุดแข็งเฉพาะตัว)

### Priority กลาง (Phase 2-3)
4. **WebSocket Integration** (จาก Mission Control)
5. **Agent Chat System** (ดัดแปลงจาก Mission Control)
6. **Real-time Progress** (จาก Mission Control)

### Priority ต่ำ (Phase 4-5)
7. **Cross-machine File Upload** (จาก Mission Control)
8. **Artifact Version Control** (จุดแข็งเฉพาะตัว)
9. **Advanced Analytics** (จุดแข็งเฉพาะตัว)

---

## 7. สรุปสั้นๆ

| คำถาม | คำตอบ |
|-------|--------|
| Unified ดีกว่า Mission Control ไหม? | **ต่างกัน** - Mission Control เน้น UX, Unified เน้น Workflow Automation |
| Unified ดีกว่า AI Team ปัจจุบันไหม? | **ใช่** - ได้ UX + Workflow Engine เพิ่ม |
| ควรทำ Unified เลยไหม? | **รอสักครู่** - ลอง SOUL.md + Kanban ก่อน แล้วค่อยตัดสินใจทำ Unified |
| อะไรสำคัญที่สุด? | **Workflow Engine** - จุดที่ไม่มีในระบบอื่นเลย |

---

**แนะนำ:** เริ่มจาก **"Mini Unified"** - ทำ SOUL.md + ปรับ Dashboard เป็น Kanban ก่อน ถ้าใช้ดี ค่อยลงทุนทำ Workflow Engine เต็มรูปแบบ
