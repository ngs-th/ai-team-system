<?php
/**
 * AI Team - Productivity & Fairness Reports
 * ==========================================
 * Story 6: Productivity & Fairness Reports
 * 
 * Features:
 * - Date range selector
 * - Productivity metrics by agent
 * - Fairness/workload distribution
 * - Export to CSV
 * 
 * @author Barry (Solo Developer)
 * @version 1.0.0
 */

date_default_timezone_set('Asia/Bangkok');

require_once __DIR__ . '/database.php';

// Get date range from query params or default to last 30 days
$endDate = $_GET['end_date'] ?? date('Y-m-d');
$startDate = $_GET['start_date'] ?? date('Y-m-d', strtotime('-30 days'));
$reportType = $_GET['report'] ?? 'productivity';

// Database connection
$db = getDatabaseConnection();

// ============ DATA FETCHING FUNCTIONS ============

function getProductivityReport($db, $startDate, $endDate) {
    $stmt = $db->prepare("
        SELECT 
            a.id,
            a.name,
            a.role,
            a.total_tasks_completed,
            a.total_tasks_assigned,
            COUNT(DISTINCT CASE WHEN t.status = 'done' 
                AND date(t.completed_at) BETWEEN :start AND :end THEN t.id END) as tasks_completed_period,
            COUNT(DISTINCT CASE WHEN t.status IN ('in_progress', 'review') THEN t.id END) as tasks_active,
            ROUND(AVG(CASE WHEN t.status = 'done' AND t.actual_duration_minutes > 0 
                THEN t.actual_duration_minutes END), 1) as avg_duration_minutes
        FROM agents a
        LEFT JOIN tasks t ON a.id = t.assignee_id
        WHERE a.status != 'offline'
        GROUP BY a.id
        ORDER BY tasks_completed_period DESC, a.name
    ");
    $stmt->execute([':start' => $startDate, ':end' => $endDate]);
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

function getFairnessReport($db, $startDate, $endDate) {
    $stmt = $db->prepare("
        SELECT 
            a.id,
            a.name,
            COUNT(DISTINCT CASE WHEN t.status = 'done' 
                AND date(t.completed_at) BETWEEN :start AND :end THEN t.id END) as completed,
            COUNT(DISTINCT CASE WHEN t.status = 'done' 
                AND t.priority = 'high'
                AND date(t.completed_at) BETWEEN :start AND :end THEN t.id END) as high_priority,
            COUNT(DISTINCT CASE WHEN t.status IN ('todo', 'in_progress', 'review') THEN t.id END) as pending,
            SUM(CASE WHEN t.status = 'done' AND t.actual_duration_minutes > 0 
                THEN t.actual_duration_minutes ELSE 0 END) as total_minutes
        FROM agents a
        LEFT JOIN tasks t ON a.id = t.assignee_id
        WHERE a.status != 'offline'
        GROUP BY a.id
        ORDER BY completed DESC
    ");
    $stmt->execute([':start' => $startDate, ':end' => $endDate]);
    $workloads = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    // Calculate fairness metrics
    $completed = array_column($workloads, 'completed');
    $avg = count($completed) > 0 ? array_sum($completed) / count($completed) : 0;
    $variance = 0;
    if (count($completed) > 1) {
        $variance = array_sum(array_map(fn($x) => pow($x - $avg, 2), $completed)) / count($completed);
    }
    $stdDev = sqrt($variance);
    $cv = $avg > 0 ? ($stdDev / $avg * 100) : 0;
    $fairnessScore = max(0, 100 - $cv);
    
    return [
        'fairness_score' => round($fairnessScore, 1),
        'avg_tasks' => round($avg, 1),
        'std_dev' => round($stdDev, 2),
        'min_tasks' => count($completed) > 0 ? min($completed) : 0,
        'max_tasks' => count($completed) > 0 ? max($completed) : 0,
        'workloads' => $workloads
    ];
}

function getDurationStats($db) {
    $stmt = $db->query("
        SELECT 
            COUNT(*) as total_completed,
            ROUND(AVG(actual_duration_minutes), 1) as avg_duration,
            MIN(actual_duration_minutes) as min_duration,
            MAX(actual_duration_minutes) as max_duration
        FROM tasks 
        WHERE status = 'done' AND actual_duration_minutes IS NOT NULL
    ");
    return $stmt->fetch(PDO::FETCH_ASSOC);
}

function formatDuration($minutes) {
    if (!$minutes || $minutes <= 0) return '-';
    $hours = floor($minutes / 60);
    $mins = $minutes % 60;
    if ($hours > 0) return "{$hours}h {$mins}m";
    return "{$mins}m";
}

// Fetch data
$productivityData = getProductivityReport($db, $startDate, $endDate);
$fairnessData = getFairnessReport($db, $startDate, $endDate);
$durationStats = getDurationStats($db);

// Calculate totals
$totalCompleted = array_sum(array_column($productivityData, 'tasks_completed_period'));
$totalActive = array_sum(array_column($productivityData, 'tasks_active'));

// Export CSV if requested
if (isset($_GET['export']) && $_GET['export'] === 'csv') {
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="ai-team-report-' . date('Y-m-d') . '.csv"');
    
    $output = fopen('php://output', 'w');
    fputcsv($output, ['AI Team Report', $startDate . ' to ' . $endDate]);
    fputcsv($output, []);
    
    if ($reportType === 'productivity') {
        fputcsv($output, ['Agent ID', 'Name', 'Role', 'Completed (Period)', 'Lifetime Completed', 
                         'Lifetime Assigned', 'Active Tasks', 'Avg Duration', 'Completion Rate %']);
        foreach ($productivityData as $agent) {
            $rate = $agent['total_tasks_assigned'] > 0 
                ? round($agent['total_tasks_completed'] / $agent['total_tasks_assigned'] * 100, 1) 
                : 0;
            fputcsv($output, [
                $agent['id'], $agent['name'], $agent['role'],
                $agent['tasks_completed_period'], $agent['total_tasks_completed'],
                $agent['total_tasks_assigned'], $agent['tasks_active'],
                formatDuration($agent['avg_duration_minutes']), $rate
            ]);
        }
    } else {
        fputcsv($output, ['Fairness Score', $fairnessData['fairness_score']]);
        fputcsv($output, ['Avg Tasks/Agent', $fairnessData['avg_tasks']]);
        fputcsv($output, ['Std Deviation', $fairnessData['std_dev']]);
        fputcsv($output, []);
        fputcsv($output, ['Agent', 'Completed', 'High Priority', 'Pending', 'Total Minutes']);
        foreach ($fairnessData['workloads'] as $wl) {
            fputcsv($output, [$wl['name'], $wl['completed'], $wl['high_priority'], 
                            $wl['pending'], $wl['total_minutes']]);
        }
    }
    fclose($output);
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Team Reports - Productivity & Fairness</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eaeaea;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            text-align: center;
            color: #00d9ff;
            margin-bottom: 10px;
            font-size: 2rem;
            text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
        }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; }
        
        /* Filters */
        .filters {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
        }
        .filter-group { display: flex; flex-direction: column; gap: 5px; }
        .filter-group label { font-size: 0.85rem; color: #888; }
        .filter-group input, .filter-group select {
            padding: 10px 15px;
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(0, 0, 0, 0.3);
            color: #eaeaea;
            font-size: 0.95rem;
        }
        .btn {
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.2s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #00d9ff, #0099cc);
            color: #000;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0, 217, 255, 0.3); }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #eaeaea;
            text-decoration: none;
        }
        .btn-secondary:hover { background: rgba(255, 255, 255, 0.2); }
        
        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #00d9ff;
        }
        .stat-label { color: #888; font-size: 0.9rem; margin-top: 5px; }
        
        /* Sections */
        .section {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .section h2 {
            color: #00d9ff;
            margin-bottom: 20px;
            font-size: 1.3rem;
            border-bottom: 1px solid rgba(0, 217, 255, 0.3);
            padding-bottom: 10px;
        }
        
        /* Fairness Score */
        .fairness-score {
            text-align: center;
            padding: 30px;
        }
        .score-value {
            font-size: 4rem;
            font-weight: bold;
        }
        .score-good { color: #48bb78; }
        .score-fair { color: #ed8936; }
        .score-poor { color: #f56565; }
        .score-label { color: #888; margin-top: 10px; }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        th {
            color: #888;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.8rem;
            letter-spacing: 0.5px;
        }
        tr:hover { background: rgba(255, 255, 255, 0.03); }
        
        /* Badges */
        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-role-dev { background: #4299e1; color: #fff; }
        .badge-role-qa { background: #9f7aea; color: #fff; }
        .badge-role-pm { background: #ed8936; color: #fff; }
        .badge-role-architect { background: #48bb78; color: #fff; }
        .badge-role-default { background: #718096; color: #fff; }
        
        /* Progress bar */
        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d9ff, #0099cc);
            border-radius: 4px;
            transition: width 0.3s;
        }
        
        /* Navigation */
        .nav-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .nav-tab {
            padding: 12px 24px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.05);
            color: #888;
            text-decoration: none;
            transition: all 0.2s;
        }
        .nav-tab.active {
            background: rgba(0, 217, 255, 0.2);
            color: #00d9ff;
            border: 1px solid rgba(0, 217, 255, 0.3);
        }
        .nav-tab:hover { background: rgba(255, 255, 255, 0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 AI Team Reports</h1>
        <p class="subtitle">Productivity & Fairness Analytics</p>
        
        <!-- Navigation -->
        <div class="nav-tabs">
            <a href="?report=productivity&start_date=<?= $startDate ?>&end_date=<?= $endDate ?>" 
               class="nav-tab <?= $reportType === 'productivity' ? 'active' : '' ?>">📈 Productivity</a>
            <a href="?report=fairness&start_date=<?= $startDate ?>&end_date=<?= $endDate ?>" 
               class="nav-tab <?= $reportType === 'fairness' ? 'active' : '' ?>">⚖️ Fairness</a>
        </div>
        
        <!-- Filters -->
        <form class="filters" method="GET">
            <input type="hidden" name="report" value="<?= $reportType ?>">
            <div class="filter-group">
                <label>Start Date</label>
                <input type="date" name="start_date" value="<?= $startDate ?>">
            </div>
            <div class="filter-group">
                <label>End Date</label>
                <input type="date" name="end_date" value="<?= $endDate ?>">
            </div>
            <button type="submit" class="btn btn-primary">Update Report</button>
            <a href="?report=<?= $reportType ?>&start_date=<?= $startDate ?>&end_date=<?= $endDate ?>&export=csv" 
               class="btn btn-secondary">📥 Export CSV</a>
        </form>
        
        <!-- Stats Overview -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value"><?= $totalCompleted ?></div>
                <div class="stat-label">Tasks Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value"><?= $totalActive ?></div>
                <div class="stat-label">Active Tasks</div>
            </div>
            <div class="stat-card">
                <div class="stat-value"><?= formatDuration($durationStats['avg_duration']) ?></div>
                <div class="stat-label">Avg Duration</div>
            </div>
            <div class="stat-card">
                <div class="stat-value"><?= count($productivityData) ?></div>
                <div class="stat-label">Active Agents</div>
            </div>
        </div>
        
        <?php if ($reportType === 'productivity'): ?>
        <!-- Productivity Report -->
        <div class="section">
            <h2>📈 Productivity by Agent</h2>
            <table>
                <thead>
                    <tr>
                        <th>Agent</th>
                        <th>Role</th>
                        <th>Completed (Period)</th>
                        <th>Lifetime</th>
                        <th>Active</th>
                        <th>Avg Duration</th>
                        <th>Completion Rate</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($productivityData as $agent): 
                        $rate = $agent['total_tasks_assigned'] > 0 
                            ? round($agent['total_tasks_completed'] / $agent['total_tasks_assigned'] * 100, 1) 
                            : 0;
                        $roleClass = 'badge-role-' . ($agent['role'] ?? 'default');
                    ?>
                    <tr>
                        <td><strong><?= htmlspecialchars($agent['name']) ?></strong></td>
                        <td><span class="badge <?= $roleClass ?>"><?= htmlspecialchars($agent['role']) ?></span></td>
                        <td><?= $agent['tasks_completed_period'] ?></td>
                        <td><?= $agent['total_tasks_completed'] ?> / <?= $agent['total_tasks_assigned'] ?></td>
                        <td><?= $agent['tasks_active'] ?></td>
                        <td><?= formatDuration($agent['avg_duration_minutes']) ?></td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div class="progress-bar" style="width: 100px;">
                                    <div class="progress-fill" style="width: <?= min($rate, 100) ?>%"></div>
                                </div>
                                <span><?= $rate ?>%</span>
                            </div>
                        </td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        
        <?php else: ?>
        <!-- Fairness Report -->
        <div class="section">
            <h2>⚖️ Workload Fairness</h2>
            <div class="fairness-score">
                <?php 
                    $scoreClass = $fairnessData['fairness_score'] >= 80 ? 'score-good' : 
                                 ($fairnessData['fairness_score'] >= 60 ? 'score-fair' : 'score-poor');
                    $scoreEmoji = $fairnessData['fairness_score'] >= 80 ? '🟢' : 
                                 ($fairnessData['fairness_score'] >= 60 ? '🟡' : '🔴');
                ?>
                <div class="score-value <?= $scoreClass ?>"><?= $scoreEmoji ?> <?= $fairnessData['fairness_score'] ?></div>
                <div class="score-label">Fairness Score (higher is fairer)</div>
            </div>
            
            <div class="stats-grid" style="margin-top: 30px;">
                <div class="stat-card">
                    <div class="stat-value"><?= $fairnessData['avg_tasks'] ?></div>
                    <div class="stat-label">Avg Tasks/Agent</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value"><?= $fairnessData['std_dev'] ?></div>
                    <div class="stat-label">Std Deviation</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value"><?= $fairnessData['min_tasks'] ?> - <?= $fairnessData['max_tasks'] ?></div>
                    <div class="stat-label">Task Range</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>👤 Workload Distribution</h2>
            <table>
                <thead>
                    <tr>
                        <th>Agent</th>
                        <th>Completed</th>
                        <th>High Priority</th>
                        <th>Pending</th>
                        <th>Total Time</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($fairnessData['workloads'] as $wl): ?>
                    <tr>
                        <td><strong><?= htmlspecialchars($wl['name']) ?></strong></td>
                        <td><?= $wl['completed'] ?></td>
                        <td><?= $wl['high_priority'] ?></td>
                        <td><?= $wl['pending'] ?></td>
                        <td><?= formatDuration($wl['total_minutes']) ?></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        <?php endif; ?>
        
        <div style="text-align: center; margin-top: 30px;">
            <a href="dashboard.php" style="color: #00d9ff; text-decoration: none;">← Back to Dashboard</a>
        </div>
    </div>
</body>
</html>
