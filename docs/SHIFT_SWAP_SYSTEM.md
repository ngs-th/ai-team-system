# Shift Swap Request System

**Version:** 1.0.0  
**Author:** Winston (System Architect)  
**Created:** 2026-02-03  
**Status:** Production Ready

## Overview

The Shift Swap Request System is a complete approval workflow system for managing shift exchanges between AI Team agents. It provides validation rules, automatic notifications, and comprehensive audit trails.

## Features

- ✅ **Swap Request Creation** - Request shift exchanges with reason
- ✅ **Approval Workflow** - Target agent approves/rejects with notes
- ✅ **Validation Rules** - 9 comprehensive validation rules
- ✅ **Auto-Expiry** - Pending requests expire after 48 hours (configurable)
- ✅ **Telegram Notifications** - Integrated with notification system
- ✅ **Conflict Detection** - Prevents overlapping shifts
- ✅ **Statistics & Reporting** - Track approval rates and request history
- ✅ **CLI Interface** - Full command-line management

## Database Schema

### Tables

#### shifts
Stores agent shift assignments.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| agent_id | TEXT | Agent assigned to shift |
| shift_date | DATE | Date of shift (YYYY-MM-DD) |
| start_time | TIME | Shift start (HH:MM) |
| end_time | TIME | Shift end (HH:MM) |
| shift_type | TEXT | regular, on_call, holiday, overtime, maintenance |
| is_recurring | BOOLEAN | Whether shift repeats |
| recurring_pattern | TEXT | Pattern for recurring shifts |
| project_id | TEXT | Optional project assignment |
| notes | TEXT | Additional notes |
| is_active | BOOLEAN | Whether shift is active |

#### swap_requests
Stores swap request workflow.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| requestor_agent_id | TEXT | Agent requesting swap |
| requestor_shift_id | INTEGER | Shift being offered |
| target_agent_id | TEXT | Agent being asked |
| target_shift_id | INTEGER | Shift being requested |
| status | TEXT | pending, approved, rejected, cancelled, expired, completed |
| reason | TEXT | Reason for swap request |
| response_notes | TEXT | Notes from approver/rejector |
| requested_at | DATETIME | When request was created |
| responded_at | DATETIME | When response was given |
| completed_at | DATETIME | When swap was executed |
| expires_at | DATETIME | When request expires |

#### swap_request_history
Audit trail for all swap actions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| swap_request_id | INTEGER | Reference to swap request |
| action | TEXT | Action performed |
| old_status | TEXT | Previous status |
| new_status | TEXT | New status |
| actor_agent_id | TEXT | Agent who performed action |
| notes | TEXT | Additional notes |
| timestamp | DATETIME | When action occurred |

### Views

#### v_swap_request_details
Complete swap request information with agent and shift details.

#### v_agent_shift_summary
Summary of shifts and swap requests per agent.

## Validation Rules

1. **No Self-Swap** - Agents cannot swap with themselves
2. **Agent Existence** - Both agents must exist and be active
3. **Shift Existence** - Both shifts must exist and be active
4. **Ownership** - Requestor must own the offered shift
5. **Target Ownership** - Target must own the requested shift
6. **No Past Shifts** - Cannot swap past shifts
7. **No Conflicts** - No pending requests for same shifts
8. **No Overlap (Requestor)** - Target shift must not conflict with requestor's other shifts
9. **No Overlap (Target)** - Requestor shift must not conflict with target's other shifts

## CLI Usage

### Create a Shift

```bash
./shift_swap_system.py shift-create <agent_id> <date> <start_time> <end_time> [options]
```

**Example:**
```bash
./shift_swap_system.py shift-create architect 2026-02-05 09:00 17:00 \
    --type regular \
    --project PROJ-001 \
    --notes "Architecture review"
```

### Create Swap Request

```bash
./shift_swap_system.py request <requestor> <requestor_shift> <target> <target_shift> [options]
```

**Example:**
```bash
./shift_swap_system.py request architect 1 dev 2 \
    --reason "Need to attend meetings" \
    --expiry 24
```

### Approve Request

```bash
./shift_swap_system.py approve <request_id> <approver> [--notes <notes>]
```

**Example:**
```bash
./shift_swap_system.py approve 1 dev --notes "Sure, I can take that shift"
```

### Reject Request

```bash
./shift_swap_system.py reject <request_id> <rejector> [--notes <notes>]
```

**Example:**
```bash
./shift_swap_system.py reject 1 dev --notes "Sorry, I have conflicts"
```

### Cancel Request

```bash
./shift_swap_system.py cancel <request_id> <requestor>
```

**Example:**
```bash
./shift_swap_system.py cancel 1 architect
```

### List Requests

```bash
./shift_swap_system.py list [--agent <agent>] [--status <status>] [--direction <dir>]
```

**Examples:**
```bash
# All pending requests
./shift_swap_system.py list --status pending

# Winston's outgoing requests
./shift_swap_system.py list --agent architect --direction outgoing

# Incoming requests for dev
./shift_swap_system.py list --agent dev --direction incoming
```

### View Request Details

```bash
./shift_swap_system.py view <request_id>
```

### Show Statistics

```bash
./shift_swap_system.py stats [--agent <agent>]
```

### List Agent Shifts

```bash
./shift_swap_system.py shifts <agent_id> [--from <date>] [--to <date>]
```

**Example:**
```bash
./shift_swap_system.py shifts architect --from 2026-02-01 --to 2026-02-28
```

### Expire Old Requests

```bash
./shift_swap_system.py expire
```

Manually trigger expiration of old pending requests (also runs automatically).

## Python API

### Initialize System

```python
from shift_swap_system import ShiftSwapSystem

system = ShiftSwapSystem()
```

### Create Shift

```python
shift_id = system.create_shift(
    agent_id='architect',
    shift_date='2026-02-05',
    start_time='09:00',
    end_time='17:00',
    shift_type='regular',
    project_id='PROJ-001',
    notes='Architecture review'
)
```

### Create Swap Request

```python
request_id, message = system.create_swap_request(
    requestor_agent_id='architect',
    requestor_shift_id=1,
    target_agent_id='dev',
    target_shift_id=2,
    reason='Need to attend meetings',
    expiry_hours=48
)
```

### Approve/Reject Swap

```python
# Approve
success, message = system.approve_swap_request(
    request_id=1,
    approver_agent_id='dev',
    response_notes='Sure, no problem'
)

# Reject
success, message = system.reject_swap_request(
    request_id=1,
    rejector_agent_id='dev',
    response_notes='I have conflicts that day'
)
```

### Get Requests

```python
# Single request
details = system.get_swap_request(request_id=1)

# List requests
requests = system.get_swap_requests(
    agent_id='architect',
    status='pending',
    direction='outgoing'  # or 'incoming' or None
)
```

### Get Agent Shifts

```python
shifts = system.get_agent_shifts(
    agent_id='architect',
    from_date='2026-02-01',
    to_date='2026-02-28'
)
```

### Statistics

```python
# Overall stats
stats = system.get_swap_statistics()

# Agent-specific stats
stats = system.get_swap_statistics(agent_id='architect')
```

## Data Classes

### SwapRequestDetails

```python
@dataclass
class SwapRequestDetails:
    request_id: int
    status: str
    reason: Optional[str]
    response_notes: Optional[str]
    requested_at: str
    responded_at: Optional[str]
    expires_at: Optional[str]
    requestor_agent_id: str
    requestor_name: str
    requestor_role: str
    target_agent_id: str
    target_name: str
    target_role: str
    # ... shift details
```

## Notifications

The system automatically sends Telegram notifications for:

- **New Request** - Target agent receives notification
- **Approved** - Both agents notified of successful swap
- **Rejected** - Requestor notified
- **Cancelled** - Target notified

## Cron Integration

Add to crontab for automatic expiry:

```bash
# Expire old swap requests every hour
0 * * * * cd /Users/ngs/clawd/projects/ai-team && python3 shift_swap_system.py expire
```

## Testing

Run functional tests:

```bash
# Create test shifts
python3 shift_swap_system.py shift-create architect 2026-02-10 09:00 17:00
python3 shift_swap_system.py shift-create dev 2026-02-10 13:00 21:00

# Create swap request
python3 shift_swap_system.py request architect 1 dev 2 --reason "Test swap"

# View request
python3 shift_swap_system.py view 1

# Approve
python3 shift_swap_system.py approve 1 dev

# Check stats
python3 shift_swap_system.py stats
```

## Integration with AI Team System

The Shift Swap System integrates with the existing AI Team database:

- Uses same `agents` table
- References `projects` table
- Uses existing notification system (`send_telegram_notification`)
- Follows same database conventions

## Future Enhancements

Potential improvements:

1. **Bulk Operations** - Swap multiple shifts at once
2. **Chain Swaps** - A→B→C→A circular swaps
3. **Shift Marketplace** - Open requests without specific target
4. **Calendar View** - Visual calendar integration in dashboard
5. **Availability Management** - Mark unavailable dates
6. **Swap Recommendations** - Suggest compatible swaps

## Changelog

### v1.0.0 (2026-02-03)
- Initial release
- Full swap request workflow
- 9 validation rules
- Telegram notifications
- CLI interface
- Statistics and reporting
