<?php
/**
 * AI Team Dashboard - Kanban Board View
 * No frameworks, no external libraries - Pure PHP + SQLite3
 */

// Set timezone to Bangkok (+7)
date_default_timezone_set('Asia/Bangkok');

// Database path (same directory)
$dbPath = __DIR__ . '/team.db';

// Initialize SQLite3 connection
$db = null;
$error = null;

try {
    if (!file_exists($dbPath)) {
        throw new Exception("Database not found: $dbPath");
    }
    $db = new SQLite3($dbPath, SQLITE3_OPEN_READONLY);
    $db->enableExceptions(true);
} catch (Exception $e) {
    $error = $e->getMessage();
}

// Helper function to fetch all rows from a query
function fetchAll($db, $sql) {
    if (!$db) return [];
    $result = $db->query($sql);
    $rows = [];
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
        $rows[] = $row;
    }
    return $rows;
}

// Helper function to fetch single row
function fetchOne($db, $sql) {
    if (!$db) return [];
    $result = $db->query($sql);
    return $result->fetchArray(SQLITE3_ASSOC) ?: [];
}

// Helper function to fetch single row with parameters
function fetchOneParams($db, $sql, $params) {
    if (!$db) return [];
    $stmt = $db->prepare($sql);
    foreach ($params as $i => $value) {
        $stmt->bindValue($i + 1, $value);
    }
    $result = $stmt->execute();
    return $result->fetchArray(SQLITE3_ASSOC) ?: [];
}

// Note: Health monitoring fields should be added via team_db.py schema migration
// Dashboard is read-only, schema changes require write access

// Fetch all dashboard data
$stats = fetchOne($db, 'SELECT * FROM v_dashboard_stats');
$agents = fetchAll($db, '
    SELECT 
        a.id,
        a.name,
        a.role,
        a.status,
        a.current_task_id,
        a.total_tasks_completed,
        a.total_tasks_assigned,
        a.last_heartbeat,
        a.health_status,
        (SELECT COUNT(*) FROM tasks WHERE assignee_id = a.id AND status IN ("todo", "in_progress", "review", "reviewing")) as active_tasks,
        (SELECT COUNT(*) FROM tasks WHERE assignee_id = a.id AND status = "in_progress") as in_progress_tasks,
        ROUND((strftime("%s", "now") - strftime("%s", a.last_heartbeat)) / 60.0, 1) as minutes_since_heartbeat
    FROM agents a
    ORDER BY a.name
');
$projects = fetchAll($db, 'SELECT * FROM v_project_status ORDER BY name');
$tasks = fetchAll($db, 'SELECT t.*, p.name as project_name, a.name as assignee_name FROM tasks t LEFT JOIN projects p ON t.project_id = p.id LEFT JOIN agents a ON t.assignee_id = a.id ORDER BY t.due_date, t.priority');
$activities = fetchAll($db, 'SELECT th.*, t.title as task_title, a.name as agent_name 
    FROM task_history th 
    LEFT JOIN tasks t ON th.task_id = t.id 
    LEFT JOIN agents a ON th.agent_id = a.id 
    ORDER BY th.timestamp DESC LIMIT 20');

// Build active task map (agent currently working)
$activeTaskIds = [];
foreach ($agents as $agent) {
    if (!empty($agent['current_task_id']) && ($agent['status'] ?? '') === 'active') {
        $activeTaskIds[$agent['current_task_id']] = $agent['name'] ?? $agent['id'];
    }
}

// Fetch duration statistics
$durationStats = fetchOne($db, '
    SELECT 
        COUNT(*) as total_completed,
        ROUND(AVG(actual_duration_minutes), 1) as avg_duration_minutes,
        MIN(actual_duration_minutes) as min_duration,
        MAX(actual_duration_minutes) as max_duration
    FROM tasks 
    WHERE status = "done" 
      AND actual_duration_minutes IS NOT NULL
      AND actual_duration_minutes > 0
');

$agentDurationStats = fetchAll($db, '
    SELECT 
        a.name as agent_name,
        COUNT(*) as tasks_completed,
        ROUND(AVG(t.actual_duration_minutes), 1) as avg_duration_minutes
    FROM tasks t
    JOIN agents a ON t.assignee_id = a.id
    WHERE t.status = "done" 
      AND t.actual_duration_minutes IS NOT NULL
      AND t.actual_duration_minutes > 0
    GROUP BY t.assignee_id
    ORDER BY tasks_completed DESC
    LIMIT 5
');

// Format duration helper
function formatDurationMinutes($minutes) {
    if (!$minutes || $minutes <= 0) return 'N/A';
    $minutes = (int) round($minutes); // Convert float to int to avoid deprecation warning
    $hours = floor($minutes / 60);
    $mins = $minutes % 60;
    if ($hours > 0) {
        return $hours . 'h ' . $mins . 'm';
    }
    return $mins . 'm';
}

// Determine active review sessions (if any agent is actively reviewing a task)
$activeReviewing = [];
$activeReviewers = fetchAll($db, 'SELECT current_task_id FROM agents WHERE status = "active" AND current_task_id IS NOT NULL');
foreach ($activeReviewers as $ar) {
    $activeReviewing[$ar['current_task_id']] = true;
}

// Infer the lane for blocked tasks using task history
function inferBlockedLane($db, $taskId) {
    $row = fetchOneParams($db, '
        SELECT new_status FROM task_history 
        WHERE task_id = ? AND new_status IS NOT NULL AND new_status != "blocked"
        ORDER BY timestamp DESC LIMIT 1
    ', [$taskId]);
    if (!empty($row['new_status'])) {
        // Blocked cards must never appear in Done lane.
        if ($row['new_status'] === 'done' || $row['new_status'] === 'cancelled') {
            return 'todo';
        }
        return $row['new_status'];
    }

    $row = fetchOneParams($db, '
        SELECT old_status FROM task_history 
        WHERE task_id = ? AND new_status = "blocked" AND old_status IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
    ', [$taskId]);
    if (!empty($row['old_status'])) {
        // Blocked cards must never appear in Done lane.
        if ($row['old_status'] === 'done' || $row['old_status'] === 'cancelled') {
            return 'todo';
        }
        return $row['old_status'];
    }

    return 'todo';
}

// Group tasks by status (blocked is an attribute, not a column)
$kanbanColumns = [
    'backlog' => ['label' => 'Backlog', 'tasks' => []],
    'todo' => ['label' => 'Todo', 'tasks' => []],
    'doing' => ['label' => 'Doing', 'tasks' => []],
    'waiting_review' => ['label' => 'Waiting for Review', 'tasks' => []],
    'reviewing' => ['label' => 'Reviewing', 'tasks' => []],
    'done' => ['label' => 'Done', 'tasks' => []],
];

foreach ($tasks as $task) {
    $status = $task['status'] ?? 'todo';
    $isBlocked = ($status === 'blocked');
    $task['_blocked'] = $isBlocked;

    if ($status === 'blocked') {
        $status = inferBlockedLane($db, $task['id']);
    }

    if ($status === 'in_progress') {
        $kanbanColumns['doing']['tasks'][] = $task;
        continue;
    }

    if ($status === 'reviewing') {
        $kanbanColumns['reviewing']['tasks'][] = $task;
        continue;
    }

    if ($status === 'review') {
        if (!empty($activeReviewing[$task['id']])) {
            $kanbanColumns['reviewing']['tasks'][] = $task;
        } else {
            $kanbanColumns['waiting_review']['tasks'][] = $task;
        }
        continue;
    }

    if (isset($kanbanColumns[$status])) {
        $kanbanColumns[$status]['tasks'][] = $task;
    } else {
        $kanbanColumns['todo']['tasks'][] = $task;
    }
}

// Sort blocked tasks to the top of each column
foreach ($kanbanColumns as $key => $column) {
    usort($kanbanColumns[$key]['tasks'], function ($a, $b) {
        $aBlocked = !empty($a['_blocked']);
        $bBlocked = !empty($b['_blocked']);
        if ($aBlocked === $bBlocked) {
            return 0;
        }
        return $aBlocked ? -1 : 1;
    });
}

// Format timestamp
$lastUpdated = date('Y-m-d H:i:s');

// Helper to get badge class
function badgeClass($status) {
    $map = [
        'idle' => 'badge-idle',
        'active' => 'badge-active',
        'blocked' => 'badge-blocked',
        'offline' => 'badge-offline',
        'todo' => 'badge-todo',
        'in_progress' => 'badge-in_progress',
        'done' => 'badge-done',
        'review' => 'badge-review',
        'cancelled' => 'badge-cancelled',
        'high' => 'badge-high',
        'normal' => 'badge-normal',
        'low' => 'badge-low',
        'critical' => 'badge-critical',
        'planning' => 'badge-planning',
    ];
    return $map[$status] ?? 'badge-idle';
}

// Helper to get health status class
function healthClass($healthStatus, $minutesSinceHeartbeat) {
    if ($healthStatus === 'healthy') return 'health-healthy';
    if ($healthStatus === 'stale') return 'health-stale';
    if ($healthStatus === 'offline') return 'health-offline';
    // Fallback to time-based calculation
    if ($minutesSinceHeartbeat === null) return 'health-unknown';
    if ($minutesSinceHeartbeat > 60) return 'health-offline';
    if ($minutesSinceHeartbeat > 30) return 'health-stale';
    return 'health-healthy';
}

// Helper to get health status emoji
function healthEmoji($healthStatus, $minutesSinceHeartbeat) {
    if ($healthStatus === 'healthy') return '✅';
    if ($healthStatus === 'stale') return '🟡';
    if ($healthStatus === 'offline') return '🔴';
    // Fallback to time-based calculation
    if ($minutesSinceHeartbeat === null) return '⚪';
    if ($minutesSinceHeartbeat > 60) return '🔴';
    if ($minutesSinceHeartbeat > 30) return '🟡';
    return '✅';
}

// Helper to format last seen time
function formatLastSeen($minutesSinceHeartbeat) {
    if ($minutesSinceHeartbeat === null) return 'Never';
    if ($minutesSinceHeartbeat < 1) return 'Just now';
    if ($minutesSinceHeartbeat < 60) return intval($minutesSinceHeartbeat) . 'm ago';
    $hours = round($minutesSinceHeartbeat / 60, 1);
    return $hours . 'h ago';
}

// Get priority color
function priorityColor($priority) {
    $map = [
        'critical' => '#9f7aea',
        'high' => '#f56565',
        'normal' => '#4299e1',
        'low' => '#48bb78',
    ];
    return $map[$priority] ?? '#888';
}

// Calculate duration based on task status
// For done tasks: show actual duration (completed - started)
// For active tasks: show elapsed time (now - started)
// For todo tasks: show time since created
function getDuration($task) {
    if (!$task) return 'N/A';
    
    $status = $task['status'] ?? 'todo';
    $startedAt = $task['started_at'] ?? null;
    $completedAt = $task['completed_at'] ?? null;
    $actualDuration = $task['actual_duration_minutes'] ?? null;
    $createdAt = $task['created_at'] ?? null;
    
    // For done tasks: use actual duration or calculate from started/completed
    if ($status === 'done') {
        if ($actualDuration) {
            $actualDuration = (int) round($actualDuration);
            $hours = floor($actualDuration / 60);
            $mins = $actualDuration % 60;
            if ($hours > 0) {
                return $hours . 'h ' . $mins . 'm';
            } else {
                return $mins . 'm';
            }
        }
        // Calculate from started_at -> completed_at
        if ($startedAt && $completedAt) {
            $started = new DateTime($startedAt);
            $completed = new DateTime($completedAt);
            $diff = $started->diff($completed);
            
            if ($diff->d > 0) {
                return $diff->d . 'd ' . $diff->h . 'h';
            } elseif ($diff->h > 0) {
                return $diff->h . 'h ' . $diff->i . 'm';
            } else {
                return $diff->i . 'm';
            }
        }
        // Fallback: calculate from created_at -> completed_at
        if ($createdAt && $completedAt) {
            $created = new DateTime($createdAt);
            $completed = new DateTime($completedAt);
            $diff = $created->diff($completed);
            
            if ($diff->d > 0) {
                return $diff->d . 'd ' . $diff->h . 'h';
            } elseif ($diff->h > 0) {
                return $diff->h . 'h ' . $diff->i . 'm';
            } else {
                return $diff->i . 'm';
            }
        }
        return 'Done';
    }
    
    // For in_progress tasks: calculate from started_at to now
    if ($status === 'in_progress' && $startedAt) {
        $started = new DateTime($startedAt);
        $now = new DateTime();
        $diff = $started->diff($now);
        
        if ($diff->d > 0) {
            return $diff->d . 'd ' . $diff->h . 'h';
        } elseif ($diff->h > 0) {
            return $diff->h . 'h ' . $diff->i . 'm';
        } else {
            return $diff->i . 'm';
        }
    }
    
    // For todo/blocked tasks: show time since created
    if ($createdAt) {
        $created = new DateTime($createdAt);
        $now = new DateTime();
        $diff = $created->diff($now);
        
        if ($diff->d > 0) {
            return $diff->d . 'd ' . $diff->h . 'h';
        } elseif ($diff->h > 0) {
            return $diff->h . 'h ' . $diff->i . 'm';
        } else {
            return $diff->i . 'm';
        }
    }
    
    return 'N/A';
}

// Stats configuration for display
$statConfig = [
    ['key' => 'total_agents', 'label' => 'Total Agents'],
    ['key' => 'active_agents', 'label' => 'Active'],
    ['key' => 'idle_agents', 'label' => 'Idle'],
    ['key' => 'blocked_agents', 'label' => 'Blocked'],
    ['key' => 'total_projects', 'label' => 'Total Projects'],
    ['key' => 'active_projects', 'label' => 'Active Projects'],
    ['key' => 'total_tasks', 'label' => 'Total Tasks'],
    ['key' => 'todo_tasks', 'label' => 'To Do'],
    ['key' => 'in_progress_tasks', 'label' => 'In Progress'],
    ['key' => 'completed_tasks', 'label' => 'Completed'],
    ['key' => 'blocked_tasks', 'label' => 'Blocked'],
];
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>AI Team Dashboard - Kanban</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eaeaea;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 100%;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00d9ff;
            margin-bottom: 10px;
            font-size: 2.5rem;
            text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
        }
        .last-updated {
            text-align: center;
            color: #888;
            margin-bottom: 20px;
            font-size: 0.9rem;
        }
        .success-message {
            background: rgba(72, 187, 120, 0.2);
            border: 1px solid #48bb78;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            color: #48bb78;
            margin-bottom: 20px;
            animation: fadeOut 3s forwards;
            animation-delay: 2s;
        }
        @keyframes fadeOut {
            to { opacity: 0; visibility: hidden; }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #00d9ff;
        }
        .stat-label {
            color: #888;
            font-size: 0.85rem;
            margin-top: 5px;
        }
        .section {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .section h2 {
            color: #00d9ff;
            margin-bottom: 15px;
            font-size: 1.3rem;
            border-bottom: 1px solid rgba(0, 217, 255, 0.3);
            padding-bottom: 10px;
        }
        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            display: inline-block;
        }
        .badge-idle { background: #4a5568; color: #fff; }
        .badge-active { background: #48bb78; color: #fff; }
        .badge-blocked { background: #f56565; color: #fff; }
        .badge-offline { background: #718096; color: #fff; }
        .badge-todo { background: #718096; color: #fff; }
        .badge-in_progress { background: #4299e1; color: #fff; }
        .badge-done { background: #48bb78; color: #fff; }
        .badge-review { background: #ed8936; color: #fff; }
        .badge-cancelled { background: #4a5568; color: #fff; }
        .badge-high { background: #f56565; color: #fff; }
        .badge-normal { background: #4299e1; color: #fff; }
        .badge-low { background: #48bb78; color: #fff; }
        .badge-critical { background: #9f7aea; color: #fff; }
        .badge-planning { background: #ed8936; color: #fff; }
        
        /* Health Status Styles */
        .health-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .health-healthy {
            background: rgba(72, 187, 120, 0.2);
            color: #48bb78;
            border: 1px solid rgba(72, 187, 120, 0.3);
        }
        .health-stale {
            background: rgba(237, 137, 54, 0.2);
            color: #ed8936;
            border: 1px solid rgba(237, 137, 54, 0.3);
        }
        .health-offline {
            background: rgba(245, 101, 101, 0.2);
            color: #f56565;
            border: 1px solid rgba(245, 101, 101, 0.3);
        }
        .health-unknown {
            background: rgba(113, 128, 150, 0.2);
            color: #718096;
            border: 1px solid rgba(113, 128, 150, 0.3);
        }
        .agent-card {
            border-left: 4px solid transparent;
        }
        .agent-card.health-healthy { border-left-color: #48bb78; }
        .agent-card.health-stale { border-left-color: #ed8936; }
        .agent-card.health-offline { border-left-color: #f56565; }
        .agent-card.health-unknown { border-left-color: #718096; }
        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d9ff, #0099cc);
            transition: width 0.3s;
        }

        /* Kanban Board Styles */
        .kanban-board {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 15px;
            overflow-x: auto;
            min-height: 500px;
        }
        .kanban-column {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            padding: 15px;
            min-width: 280px;
            display: flex;
            flex-direction: column;
        }
        .kanban-column-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }
        .kanban-column-title {
            font-weight: 600;
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .kanban-column-count {
            background: rgba(255, 255, 255, 0.1);
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .kanban-column.backlog .kanban-column-title { color: #9f7aea; }
        .kanban-column.todo .kanban-column-title { color: #a0aec0; }
        .kanban-column.doing .kanban-column-title { color: #4299e1; }
        .kanban-column.waiting_review .kanban-column-title { color: #ed8936; }
        .kanban-column.reviewing .kanban-column-title { color: #f6ad55; }
        .kanban-column.done .kanban-column-title { color: #48bb78; }

        .kanban-cards {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
            min-height: 100px;
        }
.kanban-card {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            cursor: grab;
            transition: all 0.2s ease;
            position: relative;
        }
        .kanban-card.working {
            border-color: rgba(72, 187, 120, 0.6);
            box-shadow: 0 0 12px rgba(72, 187, 120, 0.35);
        }
        .kanban-card.blocked {
            border-left: 5px solid #e53e3e;
            background: rgba(229, 62, 62, 0.08);
        }
        .kanban-card .blocked-flag {
            position: absolute;
            top: 10px;
            right: 10px;
            font-size: 0.7rem;
            background: #e53e3e;
            color: #fff;
            padding: 2px 6px;
            border-radius: 6px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .kanban-card .blocked-reason {
            margin-top: 10px;
            padding: 8px 10px;
            border-radius: 6px;
            background: rgba(229, 62, 62, 0.12);
            color: #ffb3b3;
            font-size: 0.85rem;
        }
        .kanban-card:hover {
            background: rgba(255, 255, 255, 0.12);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        .kanban-card.dragging {
            opacity: 0.5;
            cursor: grabbing;
        }
        .kanban-card-header {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
            margin-bottom: 8px;
        }
        .kanban-card-title {
            font-weight: 600;
            font-size: 0.95rem;
            line-height: 1.4;
            width: 100%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .kanban-card-id {
            font-size: 0.75rem;
            color: #888;
            background: rgba(0, 0, 0, 0.3);
            padding: 2px 6px;
            border-radius: 4px;
        }
        .kanban-card-id-wrap {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .kanban-card-id-row {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .copy-btn {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #cbd5e0;
            border-radius: 6px;
            padding: 2px 6px;
            font-size: 0.75rem;
            cursor: pointer;
            line-height: 1;
        }
        .copy-btn:hover {
            background: rgba(255, 255, 255, 0.15);
        }
        .kanban-card-project {
            font-size: 0.8rem;
            color: #888;
            margin-bottom: 10px;
        }
        .kanban-card-runtime {
            display: inline-block;
            font-size: 0.72rem;
            color: #e2e8f0;
            background: rgba(99, 179, 237, 0.15);
            border: 1px solid rgba(99, 179, 237, 0.35);
            border-radius: 6px;
            padding: 2px 6px;
            margin-bottom: 10px;
        }
        .kanban-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
        }
        .kanban-card-meta {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .kanban-card-avatar {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
            color: #fff;
            overflow: hidden;
        }
        .kanban-card-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .work-indicator {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #48bb78;
            box-shadow: 0 0 10px rgba(72, 187, 120, 0.9);
            animation: pulse 1.2s infinite;
            z-index: 2;
        }
        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.7; }
            50% { transform: scale(1.2); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.7; }
        }
        .kanban-card-priority {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .kanban-card-duration {
            font-size: 0.75rem;
            color: #666;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .kanban-card-due {
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
        }
        .kanban-card-due.overdue {
            background: rgba(245, 101, 101, 0.3);
            color: #f56565;
        }
        .kanban-card-due.soon {
            background: rgba(237, 137, 54, 0.3);
            color: #ed8936;
        }
        .kanban-card-blocked-reason {
            background: rgba(245, 101, 101, 0.15);
            border-left: 3px solid #f56565;
            padding: 8px;
            margin-top: 10px;
            border-radius: 0 6px 6px 0;
            font-size: 0.8rem;
            color: #fc8181;
        }
        .kanban-card-actions {
            display: flex;
            gap: 5px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .status-btn {
            font-size: 0.7rem;
            padding: 4px 8px;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            background: rgba(255, 255, 255, 0.1);
            color: #ccc;
            transition: all 0.2s;
        }
        .status-btn:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        .status-btn.todo:hover { background: #718096; color: #fff; }
        .status-btn.in_progress:hover { background: #4299e1; color: #fff; }
        .status-btn.review:hover { background: #ed8936; color: #fff; }
        .status-btn.done:hover { background: #48bb78; color: #fff; }
        .status-btn.blocked:hover { background: #f56565; color: #fff; }

        .drop-zone {
            border: 2px dashed rgba(0, 217, 255, 0.5);
            background: rgba(0, 217, 255, 0.05);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            color: #00d9ff;
            display: none;
        }
        .drop-zone.active {
            display: block;
        }

        .agent-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        .agent-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .agent-name {
            font-weight: 600;
            color: #fff;
        }
        .agent-role {
            color: #888;
            font-size: 0.85rem;
        }
        .activity-item {
            padding: 10px;
            border-left: 3px solid #00d9ff;
            background: rgba(0, 217, 255, 0.05);
            margin-bottom: 10px;
            border-radius: 0 8px 8px 0;
        }
        .activity-time {
            color: #888;
            font-size: 0.8rem;
        }
        .two-columns {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .project-card {
            padding: 15px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .project-stats {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 10px;
        }
        .progress-text {
            text-align: center;
            font-size: 0.8rem;
            color: #888;
            margin-top: 5px;
        }
        .error {
            background: rgba(245, 101, 101, 0.2);
            border: 1px solid #f56565;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            color: #f56565;
        }
        .agent-stats {
            font-size: 0.85rem;
            color: #888;
        }
        
        /* Modal Styles */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal-overlay.active {
            display: flex;
        }
        .modal-content {
            background: #1a1a2e;
            border-radius: 12px;
            padding: 25px;
            max-width: 400px;
            width: 90%;
            border: 1px solid rgba(0, 217, 255, 0.3);
        }
        .modal-content.modal-task-details {
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .modal-title {
            color: #00d9ff;
            margin-bottom: 20px;
            font-size: 1.2rem;
        }
        .modal-task-title {
            font-weight: 700;
            line-height: 1.35;
        }
        .modal-task-id-row {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-top: 6px;
        }
        .modal-task-id {
            font-size: 0.82rem;
            color: #a0aec0;
        }
        .modal-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .modal-btn {
            padding: 12px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            transition: all 0.2s;
        }
        .modal-btn:hover {
            transform: translateY(-2px);
        }
        .modal-btn.todo { background: #718096; color: #fff; }
        .modal-btn.in_progress { background: #4299e1; color: #fff; }
        .modal-btn.review { background: #ed8936; color: #fff; }
        .modal-btn.done { background: #48bb78; color: #fff; }
        .modal-btn.blocked { background: #f56565; color: #fff; }
        .modal-btn.cancel {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: #888;
            grid-column: span 2;
        }
        
        /* Task Requirements Styles */
        .task-goal {
            background: rgba(0, 217, 255, 0.1);
            border-left: 4px solid #00d9ff;
            padding: 12px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
        }
        .task-goal-title {
            color: #00d9ff;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        .task-goal-content {
            color: #eaeaea;
            line-height: 1.6;
        }
        .task-checklist {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            padding: 12px;
            margin: 15px 0;
        }
        .task-checklist-title {
            color: #a0aec0;
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .task-checklist-content {
            color: #eaeaea;
            white-space: pre-wrap;
            font-family: inherit;
            line-height: 1.8;
        }
        .task-checklist-content input[type="checkbox"] {
            margin-right: 8px;
            accent-color: #00d9ff;
        }
        .task-checklist-content ul {
            margin: 0;
            padding-left: 20px;
        }
        .task-checklist-content li {
            margin: 5px 0;
        }
        .task-checklist-content li.checked {
            color: #9ae6b4;
            text-decoration: line-through;
        }
        .task-checklist-summary {
            font-size: 0.8rem;
            color: #a0aec0;
            margin-bottom: 6px;
        }
        .task-meta-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        .task-meta-item {
            background: rgba(255, 255, 255, 0.04);
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 0.85rem;
        }
        .task-section-divider {
            border: none;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            margin: 20px 0;
        }

        @media (max-width: 1600px) {
            .kanban-board {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        @media (max-width: 1000px) {
            .kanban-board {
                grid-template-columns: repeat(2, 1fr);
            }
            .two-columns {
                grid-template-columns: 1fr;
            }
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            h1 {
                font-size: 1.8rem;
            }
        }
        @media (max-width: 600px) {
            .kanban-board {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Team Dashboard</h1>
        <p class="last-updated">Last updated: <?= htmlspecialchars($lastUpdated) ?> (auto-refreshes every 60s)</p>

        <?php if ($error): ?>
        <div class="error">
            <strong>Error:</strong> <?= htmlspecialchars($error) ?>
        </div>
        <?php else: ?>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <?php foreach ($statConfig as $stat): ?>
                <?php $value = $stats[$stat['key']] ?? 0; ?>
                <div class="stat-card">
                    <div class="stat-value"><?= htmlspecialchars($value) ?></div>
                    <div class="stat-label"><?= htmlspecialchars($stat['label']) ?></div>
                </div>
            <?php endforeach; ?>
            <?php if (isset($stats['avg_progress'])): ?>
            <div class="stat-card">
                <div class="stat-value"><?= htmlspecialchars($stats['avg_progress'] ?? 0) ?>%</div>
                <div class="stat-label">Avg Progress</div>
            </div>
            <?php endif; ?>
            <?php if (isset($stats['due_today'])): ?>
            <div class="stat-card">
                <div class="stat-value"><?= htmlspecialchars($stats['due_today'] ?? 0) ?></div>
                <div class="stat-label">Due Today</div>
            </div>
            <?php endif; ?>
            <?php if (isset($stats['overdue_tasks'])): ?>
            <div class="stat-card">
                <div class="stat-value"><?= htmlspecialchars($stats['overdue_tasks'] ?? 0) ?></div>
                <div class="stat-label">Overdue</div>
            </div>
            <?php endif; ?>
        </div>

        <!-- Duration Stats Section -->
        <?php if ($durationStats && $durationStats['total_completed'] > 0): ?>
        <div class="section">
            <h2>⏱️ Task Duration Statistics</h2>
            <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                <div class="stat-card">
                    <div class="stat-value"><?= htmlspecialchars($durationStats['total_completed'] ?? 0) ?></div>
                    <div class="stat-label">Completed Tasks</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value"><?= formatDurationMinutes($durationStats['avg_duration_minutes']) ?></div>
                    <div class="stat-label">Average Duration</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value"><?= formatDurationMinutes($durationStats['min_duration']) ?></div>
                    <div class="stat-label">Fastest Task</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value"><?= formatDurationMinutes($durationStats['max_duration']) ?></div>
                    <div class="stat-label">Slowest Task</div>
                </div>
            </div>
            <?php if (!empty($agentDurationStats)): ?>
            <div style="margin-top: 20px;">
                <h3 style="font-size: 1rem; color: #888; margin-bottom: 10px;">By Agent</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;">
                    <?php foreach ($agentDurationStats as $agentStat): ?>
                    <div style="background: rgba(255, 255, 255, 0.05); padding: 12px; border-radius: 8px;">
                        <div style="font-weight: 600; color: #00d9ff;"><?= htmlspecialchars($agentStat['agent_name']) ?></div>
                        <div style="font-size: 0.85rem; color: #888; margin-top: 4px;">
                            <?= htmlspecialchars($agentStat['tasks_completed']) ?> tasks completed • 
                            avg <?= formatDurationMinutes($agentStat['avg_duration_minutes']) ?>
                        </div>
                    </div>
                    <?php endforeach; ?>
                </div>
            </div>
            <?php endif; ?>
        </div>
        <?php endif; ?>

        <!-- Kanban Board Section -->
        <div class="section">
            <h2>📋 Task Kanban Board (<?= count($tasks) ?> tasks)</h2>
            <div class="kanban-board" id="kanbanBoard">
                <?php foreach ($kanbanColumns as $status => $column): ?>
                <div class="kanban-column <?= $status ?>" data-status="<?= $status ?>">
                    <div class="kanban-column-header">
                        <span class="kanban-column-title"><?= $column['label'] ?></span>
                        <span class="kanban-column-count"><?= count($column['tasks']) ?></span>
                    </div>
                    <div class="kanban-cards" id="column-<?= $status ?>">
                        <?php foreach ($column['tasks'] as $task): 
                            $priorityColor = priorityColor($task['priority'] ?? 'normal');
                            $isOverdue = isset($task['due_date']) && $task['due_date'] && strtotime($task['due_date']) < strtotime('today');
                            $isDueSoon = isset($task['due_date']) && $task['due_date'] && !$isOverdue && strtotime($task['due_date']) <= strtotime('+2 days');
                            $dueClass = $isOverdue ? 'overdue' : ($isDueSoon ? 'soon' : '');
                            $assigneeInitials = '';
                            if (!empty($task['assignee_name'])) {
                                $names = explode(' ', $task['assignee_name']);
                                foreach ($names as $n) {
                                    $assigneeInitials .= strtoupper(substr($n, 0, 1));
                                }
                                $assigneeInitials = substr($assigneeInitials, 0, 2);
                            }
                        ?>
                        <?php $isBlocked = !empty($task['_blocked']); ?>
                        <?php $isActiveTask = !empty($activeTaskIds[$task['id']]); ?>
                        <div class="kanban-card<?= $isBlocked ? ' blocked' : '' ?><?= $isActiveTask ? ' working' : '' ?>">
                            <?php if ($isBlocked): ?>
                                <div class="blocked-flag">BLOCKED</div>
                            <?php endif; ?>
                            <?php if ($isActiveTask): ?>
                                <div class="work-indicator" title="Active agent: <?= htmlspecialchars($activeTaskIds[$task['id']]) ?>"></div>
                            <?php endif; ?>
                            <div class="kanban-card-header">
                                <span class="kanban-card-title" title="<?= htmlspecialchars($task['title'] ?? 'Untitled') ?>"><?= htmlspecialchars($task['title'] ?? 'Untitled') ?></span>
                                <span class="kanban-card-id-row">
                                    <span class="kanban-card-id">#<?= $task['id'] ?></span>
                                    <button class="copy-btn" onclick="copyTaskId('<?= $task['id'] ?>', event)" title="Copy Task ID">⧉</button>
                                </span>
                            </div>
                            <?php if (!empty($task['project_id'])): 
                                $projectDisplay = $task['project_name'] ?? $task['project_id'];
                                // If project name looks like an ID (EPIC-XXX), try to get better display name
                                if (preg_match('/^EPIC-\d+$/', $projectDisplay)) {
                                    $projectDisplay = 'Nurse AI'; // Default to Nurse AI for Epic 2
                                }
                            ?>
                            <div class="kanban-card-project">📁 <?= htmlspecialchars($projectDisplay) ?></div>
                            <?php endif; ?>
                            <?php if (!empty($task['runtime'])): ?>
                            <div class="kanban-card-runtime">⚙️ <?= htmlspecialchars($task['runtime']) ?></div>
                            <?php endif; ?>
                            
                            <div class="kanban-card-footer">
                                <div class="kanban-card-meta">
                                    <div class="kanban-card-avatar" title="<?= htmlspecialchars($task['assignee_name'] ?? 'Unassigned') ?>">
                                        <?= $assigneeInitials ?: '?' ?>
                                    </div>
                                    <div class="kanban-card-priority" style="background: <?= $priorityColor ?>" title="Priority: <?= htmlspecialchars($task['priority'] ?? 'normal') ?>"></div>
                                </div>
                                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                                    <?php if (!empty($task['due_date'])): ?>
                                    <span class="kanban-card-due <?= $dueClass ?>">
                                        <?= $isOverdue ? '⚠️ ' : '📅 ' ?><?= htmlspecialchars($task['due_date']) ?>
                                    </span>
                                    <?php endif; ?>
                                    <span class="kanban-card-duration" title="<?= $task['status'] === 'done' ? 'Total time spent' : 'Elapsed time' ?>">
                                        ⏱️ <?= getDuration($task) ?>
                                    </span>
                                </div>
                            </div>

                            <?php if ($isBlocked && !empty($task['blocked_reason'])): ?>
                            <div class="blocked-reason">
                                🚫 <?= htmlspecialchars($task['blocked_reason']) ?>
                            </div>
                            <?php endif; ?>
                        </div>
                        <?php endforeach; ?>
                    </div>
                </div>
                <?php endforeach; ?>
            </div>
        </div>

        <div class="two-columns">
            <!-- Agents Section -->
            <div class="section">
                <h2>👥 Agents (<?= count($agents) ?>)</h2>
                <div class="agent-grid">
                    <?php foreach ($agents as $agent): 
                        $healthStatus = $agent['health_status'] ?? 'unknown';
                        $minutesSince = $agent['minutes_since_heartbeat'] ?? null;
                        $healthClass = healthClass($healthStatus, $minutesSince);
                        $healthEmoji = healthEmoji($healthStatus, $minutesSince);
                        $lastSeen = formatLastSeen($minutesSince);
                    ?>
                    <div class="agent-card <?= $healthClass ?>">
                        <div class="agent-header">
                            <div>
                                <div class="agent-name"><?= htmlspecialchars($agent['name'] ?? 'Unknown') ?></div>
                                <div class="agent-role"><?= htmlspecialchars($agent['role'] ?? 'N/A') ?></div>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 5px;">
                                <span class="badge <?= badgeClass($agent['status']) ?>"><?= htmlspecialchars($agent['status'] ?? 'idle') ?></span>
                                <span class="health-indicator <?= $healthClass ?>" title="Last seen: <?= $lastSeen ?>">
                                    <?= $healthEmoji ?> <?= htmlspecialchars($healthStatus === 'unknown' && $minutesSince !== null ? healthClass($healthStatus, $minutesSince) : $healthStatus) ?>
                                </span>
                            </div>
                        </div>
                        <div class="agent-stats">
                            Active Tasks: <?= htmlspecialchars($agent['active_tasks'] ?? 0) ?> | 
                            In Progress: <?= htmlspecialchars($agent['in_progress_tasks'] ?? 0) ?> |
                            Completed: <?= htmlspecialchars($agent['total_tasks_completed'] ?? 0) ?>
                        </div>
                        <div class="agent-stats" style="margin-top: 8px; color: #666;">
                            💓 Last seen: <?= $lastSeen ?>
                        </div>
                    </div>
                    <?php endforeach; ?>
                </div>
            </div>

            <!-- Projects Section -->
            <div class="section">
                <h2>📊 Projects (<?= count($projects) ?>)</h2>
                <?php foreach ($projects as $project): ?>
                <div class="project-card">
                    <div class="project-header">
                        <strong><?= htmlspecialchars($project['name'] ?? 'Unnamed') ?></strong>
                        <span class="badge <?= badgeClass($project['status']) ?>"><?= htmlspecialchars($project['status'] ?? 'planning') ?></span>
                    </div>
                    <div class="project-stats">
                        Tasks: <?= htmlspecialchars($project['total_tasks'] ?? 0) ?> total | 
                        <?= htmlspecialchars($project['completed_tasks'] ?? 0) ?> done | 
                        <?= htmlspecialchars($project['in_progress_tasks'] ?? 0) ?> in progress | 
                        <?= htmlspecialchars($project['blocked_tasks'] ?? 0) ?> blocked
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: <?= htmlspecialchars($project['progress_pct'] ?? 0) ?>%"></div>
                    </div>
                    <div class="progress-text"><?= htmlspecialchars($project['progress_pct'] ?? 0) ?>% complete</div>
                </div>
                <?php endforeach; ?>
            </div>
        </div>

        <!-- Activity Section -->
        <div class="section">
            <h2>📝 Recent Activity (<?= count($activities) ?> events)</h2>
            <?php foreach ($activities as $activity): ?>
            <div class="activity-item">
                <div style="display: flex; justify-content: space-between;">
                    <strong><?= strtoupper(htmlspecialchars($activity['action'] ?? 'unknown')) ?></strong>
                    <span class="activity-time"><?= htmlspecialchars($activity['timestamp'] ?? '-') ?></span>
                </div>
                <div style="margin-top: 5px;">
                    Task: <?= htmlspecialchars($activity['task_title'] ?? $activity['task_id'] ?? 'Unknown') ?><br>
                    Agent: <?= htmlspecialchars($activity['agent_name'] ?? 'System') ?>
                    <?php if ($activity['old_status'] && $activity['new_status']): ?>
                        | <?= htmlspecialchars($activity['old_status']) ?> → <?= htmlspecialchars($activity['new_status']) ?>
                    <?php endif; ?>
                    <?php if ($activity['old_progress'] !== null && $activity['new_progress'] !== null): ?>
                        | <?= htmlspecialchars($activity['old_progress']) ?>% → <?= htmlspecialchars($activity['new_progress']) ?>
                    <?php endif; ?>
                    <?php if ($activity['notes']): ?>
                        <br><em><?= htmlspecialchars($activity['notes']) ?></em>
                    <?php endif; ?>
                </div>
            </div>
            <?php endforeach; ?>
        </div>

        <?php endif; // end if not error ?>
    </div>

    <!-- Task Detail Modal (Read Only) -->
    <div class="modal-overlay" id="taskModal" onclick="closeModal(event)">
        <div class="modal-content modal-task-details" onclick="event.stopPropagation()">
            <h3 class="modal-title" id="modalTitle">Task Details</h3>
            <div id="modalBody" style="color: #eaeaea; line-height: 1.6;">
                <!-- Content loaded via JavaScript -->
            </div>
            <div style="margin-top: 20px; text-align: right;">
                <button onclick="closeModal()" style="padding: 8px 16px; background: #4a5568; color: white; border: none; border-radius: 6px; cursor: pointer;">Close</button>
            </div>
        </div>
    </div>

    <script>
        // Task data for modal
        const taskData = <?= json_encode($tasks) ?>;
        
        // Render markdown checklist to HTML
        function escapeHtml(text) {
            if (!text) return '';
            return text.replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function renderChecklist(text) {
            if (!text) return '';
            const lines = text.replace(/\\r\\n/g, '\\n').replace(/\\n/g, '\n').split('\n');
            const items = [];
            lines.forEach(raw => {
                const line = raw.trim();
                if (!line) return;
                let m = line.match(/^[-*]\\s+\\[(x| )\\]\\s+(.*)$/i);
                if (m) {
                    items.push({ checked: m[1].toLowerCase() === 'x', text: escapeHtml(m[2]) });
                    return;
                }
                m = line.match(/^[-*]\\s+(.*)$/);
                if (m) {
                    items.push({ checked: false, text: escapeHtml(m[1]), plain: true });
                    return;
                }
            });

            if (items.length === 0) {
                return `<div style="color:#a0aec0; white-space: pre-wrap;">${escapeHtml(text).replace(/\\n/g, '\n')}</div>`;
            }

            const total = items.length;
            const checked = items.filter(i => i.checked).length;
            const summary = `<div class="task-checklist-summary">Checked ${checked} / ${total}</div>`;
            const html = items.map(i => {
                const box = i.plain ? '•' : (i.checked ? '☑' : '☐');
                const cls = i.checked ? 'checked' : '';
                return `<li class="${cls}" style="margin: 8px 0; line-height: 1.5;">${box} ${i.text}</li>`;
            }).join('');
            return summary + `<ul style="list-style: none; padding-left: 0; margin: 0;">${html}</ul>`;
        }
        
        // Open modal with task details
        function openTaskModal(taskId) {
            const task = taskData.find(t => t.id === taskId);
            if (!task) return;
            
            const modal = document.getElementById('taskModal');
            const title = document.getElementById('modalTitle');
            const body = document.getElementById('modalBody');
            
            const taskTitle = escapeHtml(task.title || '');
            const taskIdLabel = escapeHtml(`#${task.id}`);
            title.innerHTML = `
                <div class="modal-task-title">${taskTitle}</div>
                <div class="modal-task-id-row">
                    <span class="modal-task-id">${taskIdLabel}</span>
                    <button class="copy-btn" onclick="copyTaskId('${task.id}', event)" title="Copy Task ID">⧉</button>
                </div>
            `;
            
            // Format date helper (Bangkok +7 timezone)
            const formatDate = (dateStr) => {
                if (!dateStr) return null;
                const date = new Date(dateStr);
                return date.toLocaleString('th-TH', {
                    timeZone: 'Asia/Bangkok',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }) + ' (GMT+7)';
            };
            
            // Build modal content
            let content = `
                <p><strong>Status:</strong> <span style="text-transform: uppercase; color: ${getStatusColor(task.status)}">${task.status}</span></p>
                <p><strong>Priority:</strong> ${task.priority || 'normal'}</p>
                <p><strong>Assignee:</strong> ${task.assignee_name || 'Unassigned'}</p>
                <p><strong>Project:</strong> ${task.project_name || 'N/A'}</p>
                ${task.working_dir ? `<p><strong>📁 Working Dir:</strong> <code style="background: #2d3748; padding: 2px 6px; border-radius: 4px; font-size: 0.9em;">${task.working_dir}</code></p>` : '<p><strong>📁 Working Dir:</strong> <span style="color: #f56565;">⚠️ Not set!</span></p>'}
                ${task.runtime ? `<p><strong>⚙️ Runtime:</strong> <span>${escapeHtml(task.runtime)}</span></p>` : ''}
                ${task.runtime_at ? `<p><strong>⏱ Runtime At:</strong> ${formatDate(task.runtime_at)}</p>` : ''}
                ${(task.status === 'blocked' && task.blocked_reason) ? `<p><strong>🚫 Blocked Reason:</strong> <span style="color: #f56565; white-space: pre-wrap;">${escapeHtml(task.blocked_reason).replace(/\\n/g, '\n')}</span></p>` : ''}
                ${task.review_feedback ? `<p><strong>🧪 Review Feedback:</strong> <span style="color: #fed7d7; white-space: pre-wrap;">${escapeHtml(task.review_feedback).replace(/\\n/g, '\n')}</span></p>` : ''}
                ${task.review_feedback_at ? `<p><strong>🧪 Feedback Time:</strong> ${formatDate(task.review_feedback_at)}</p>` : ''}
                <div class="task-meta-grid" style="margin-top: 10px;">
                    <div class="task-meta-item"><strong>📅 Created</strong><br>${task.created_at ? formatDate(task.created_at) : '-'}</div>
                    <div class="task-meta-item"><strong>🚀 Started</strong><br>${task.started_at ? formatDate(task.started_at) : '-'}</div>
                    <div class="task-meta-item"><strong>✅ Completed</strong><br>${task.completed_at ? formatDate(task.completed_at) : '-'}</div>
                    <div class="task-meta-item"><strong>⏰ Due</strong><br>${task.due_date || '-'}</div>
                    <div class="task-meta-item"><strong>🧭 Backlog At</strong><br>${task.backlog_at ? formatDate(task.backlog_at) : '-'}</div>
                    <div class="task-meta-item"><strong>📝 Todo At</strong><br>${task.todo_at ? formatDate(task.todo_at) : '-'}</div>
                    <div class="task-meta-item"><strong>🔧 In Progress At</strong><br>${task.in_progress_at ? formatDate(task.in_progress_at) : '-'}</div>
                    <div class="task-meta-item"><strong>👀 Review At</strong><br>${task.review_at ? formatDate(task.review_at) : '-'}</div>
                    <div class="task-meta-item"><strong>🔍 Reviewing At</strong><br>${task.reviewing_at ? formatDate(task.reviewing_at) : '-'}</div>
                    <div class="task-meta-item"><strong>🏁 Done At</strong><br>${task.done_at ? formatDate(task.done_at) : '-'}</div>
                    <div class="task-meta-item"><strong>🚫 Blocked At</strong><br>${task.blocked_at ? formatDate(task.blocked_at) : '-'}</div>
                    <div class="task-meta-item"><strong>📈 Progress</strong><br>${task.progress ?? 0}%</div>
                    <div class="task-meta-item"><strong>🔁 Fix Loops</strong><br>${task.fix_loop_count ?? 0}</div>
                </div>
            `;
            
            // Add Expected Outcome section
            if (task.expected_outcome) {
                // Convert literal \n to actual newlines
                const outcome = escapeHtml(task.expected_outcome).replace(/\\n/g, '\n');
                content += `
                    <hr class="task-section-divider">
                    <div class="task-goal">
                        <div class="task-goal-title">🎯 Expected Outcome</div>
                        <div class="task-goal-content" style="background: rgba(72, 187, 120, 0.1); border-left: 3px solid #48bb78; padding: 12px; border-radius: 4px; margin-top: 8px; line-height: 1.6; white-space: pre-wrap;">${outcome}</div>
                    </div>
                `;
            }
            
            // Add Prerequisites section
            if (task.prerequisites) {
                content += `
                    <div class="task-checklist">
                        <div class="task-checklist-title">✅ Prerequisites (Before Starting)</div>
                        <div class="task-checklist-content">${renderChecklist(task.prerequisites)}</div>
                    </div>
                `;
            }
            
            // Add Acceptance Criteria section
            if (task.acceptance_criteria) {
                content += `
                    <div class="task-checklist">
                        <div class="task-checklist-title">📌 Acceptance Criteria (Definition of Done)</div>
                        <div class="task-checklist-content">${renderChecklist(task.acceptance_criteria)}</div>
                    </div>
                `;
            }
            
            // Add Description section
            if (task.description) {
                // Convert literal \n to actual newlines for proper display
                const desc = escapeHtml(task.description).replace(/\\n/g, '\n');
                content += `
                    <hr class="task-section-divider">
                    <p><strong>📝 Description:</strong></p>
                    <p style="margin-left: 10px; color: #a0aec0; white-space: pre-wrap;">${desc}</p>
                `;
            }
            
            body.innerHTML = content;
            modal.classList.add('active');
        }
        
        function getStatusColor(status) {
            const colors = {
                'backlog': '#a0aec0',
                'todo': '#718096',
                'in_progress': '#4299e1',
                'review': '#ed8936',
                'reviewing': '#d69e2e',
                'done': '#48bb78',
                'blocked': '#f56565'
            };
            return colors[status] || '#718096';
        }
        
        function closeModal(e) {
            if (e && e.target !== e.currentTarget) return;
            document.getElementById('taskModal').classList.remove('active');
        }

        function copyTaskId(taskId, e) {
            if (e) e.stopPropagation();
            const btn = e ? e.currentTarget : null;
            const original = btn ? btn.textContent : null;
            const done = () => {
                if (btn) {
                    btn.textContent = 'Copied';
                    setTimeout(() => { btn.textContent = original || 'Copy'; }, 1000);
                }
            };
            const fallback = () => {
                const ta = document.createElement('textarea');
                ta.value = taskId;
                document.body.appendChild(ta);
                ta.select();
                try { document.execCommand('copy'); } catch (_) {}
                document.body.removeChild(ta);
                done();
            };
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(taskId).then(done).catch(fallback);
            } else {
                fallback();
            }
        }
        
        // Add click handlers to cards
        document.querySelectorAll('.kanban-card').forEach(card => {
            card.addEventListener('click', function() {
                const taskId = this.querySelector('.kanban-card-id').textContent.replace('#', '');
                openTaskModal(taskId);
            });
            card.style.cursor = 'pointer';
        });
        
        // Keyboard shortcut - ESC to close modal
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeModal();
            }
        });
        
        console.log('AI Team Dashboard - Read Only Mode with Task Details');
    </script>
</body>
</html>
