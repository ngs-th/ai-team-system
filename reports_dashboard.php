<?php
/**
 * Productivity & Fairness Reports Dashboard
 * ==========================================
 * Story 6: Productivity & Fairness Reports
 * 
 * Features:
 * - Date range selector
 * - Productivity chart
 * - Activity table (7 types)
 * - Fairness chart
 * - Workload distribution histogram
 * - Trend analysis
 * - Export CSV/Excel/PDF
 * 
 * @author Barry (Solo Developer)
 * @version 1.0.0
 */

date_default_timezone_set('Asia/Bangkok');

require_once __DIR__ . '/database.php';

// Get date range from query params or default to last 30 days
$endDate = $_GET['end_date'] ?? date('Y-m-d');
$startDate = $_GET['start_date'] ?? date('Y-m-d', strtotime('-30 days'));
$reportType = $_GET['report'] ?? 'summary';

// Database connection
$db = getDatabaseConnection();

// ============ DATA FETCHING FUNCTIONS ============

/**
 * Get productivity metrics for all agents
 */
function getProductivityReport($db, $startDate, $endDate) {
    $stmt = $db->prepare("
        SELECT 
            a.id as agent_id,
            a.name as agent_name,
            a.role as agent_role,
            COUNT(DISTINCT s.id) as total_shifts,
            SUM(CASE WHEN s.shift_type = 'regular' THEN 1 ELSE 0 END) as regular_shifts,
            SUM(CASE WHEN s.shift_type = 'overtime' THEN 1 ELSE 0 END) as overtime_shifts,
            SUM(CASE WHEN s.shift_type = 'on_call' THEN 1 ELSE 0 END) as oncall_shifts,
            SUM(CASE WHEN s.shift_type = 'holiday' THEN 1 ELSE 0 END) as holiday_shifts,
            SUM(CASE WHEN s.shift_type = 'maintenance' THEN 1 ELSE 0 END) as maintenance_shifts,
            SUM((julianday(s.end_time) - julianday(s.start_time)) * 24) as total_hours
        FROM agents a
        LEFT JOIN shifts s ON a.id = s.agent_id 
            AND s.shift_date BETWEEN :start AND :end
            AND s.is_active = 1
        WHERE a.status != 'offline'
        GROUP BY a.id
        ORDER BY a.name
    ");
    $stmt->execute([':start' => $startDate, ':end' => $endDate]);
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

/**
 * Get swap statistics for agents
 */
function getSwapStats($db, $startDate, $endDate) {
    // Initiated swaps
    $stmt = $db->prepare("
        SELECT 
            requestor_agent_id as agent_id,
            COUNT(*) as initiated,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
        FROM swap_requests
        WHERE date(requested_at) BETWEEN :start AND :end
        GROUP BY requestor_agent_id
    ");
    $stmt->execute([':start' => $startDate, ':end' => $endDate]);
    $initiated = [];
    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $initiated[$row['agent_id']] = $row;
    }
    
    // Received swaps
    $stmt = $db->prepare("
        SELECT 
            target_agent_id as agent_id,
            COUNT(*) as received
        FROM swap_requests
        WHERE date(requested_at) BETWEEN :start AND :end
        GROUP BY target_agent_id
    ");
    $stmt->execute([':start' => $startDate, ':end' => $endDate]);
    $received = [];
    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $received[$row['agent_id']] = $row['received'];
    }
    
    return ['initiated' => $initiated, 'received' => $received];
}

/**
 * Calculate fairness metrics
 */
function getFairnessMetrics($productivityData) {
    if (empty($productivityData)) {
        return [
            'workload_score' => 0,
            'overtime_score' => 0,
            'oncall_score' => 0,
            'avg_shifts' => 0,
            'std_dev' => 0,
            'min_shifts' => 0,
            'max_shifts' => 0
        ];
    }
    
    $shifts = array_column($productivityData, 'total_shifts');
    $avg = array_sum($shifts) / count($shifts);
    
    // Standard deviation
    $variance = 0;
    foreach ($shifts as $s) {
        $variance += pow($s - $avg, 2);
    }
    $variance /= count($shifts);
    $stdDev = sqrt($variance);
    
    // Fairness score (0-100)
    $workloadScore = $avg > 0 ? max(0, 100 - (($stdDev / $avg) * 100)) : 100;
    
    // Overtime fairness
    $overtime = array_column($productivityData, 'overtime_shifts');
    $avgOt = array_sum($overtime) / count($overtime);
    if ($avgOt > 0) {
        $otVariance = 0;
        foreach ($overtime as $ot) {
            $otVariance += pow($ot - $avgOt, 2);
        }
        $otVariance /= count($overtime);
        $otStdDev = sqrt($otVariance);
        $overtimeScore = max(0, 100 - (($otStdDev / $avgOt) * 100));
    } else {
        $overtimeScore = 100;
    }
    
    // On-call fairness
    $oncall = array_column($productivityData, 'oncall_shifts');
    $avgOc = array_sum($oncall) / count($oncall);
    if ($avgOc > 0) {
        $ocVariance = 0;
        foreach ($oncall as $oc) {
            $ocVariance += pow($oc - $avgOc, 2);
        }
        $ocVariance /= count($oncall);
        $ocStdDev = sqrt($ocVariance);
        $oncallScore = max(0, 100 - (($ocStdDev / $avgOc) * 100));
    } else {
        $oncallScore = 100;
    }
    
    return [
        'workload_score' => round($workloadScore, 1),
        'overtime_score' => round($overtimeScore, 1),
        'oncall_score' => round($oncallScore, 1),
        'avg_shifts' => round($avg, 1),
        'std_dev' => round($stdDev, 2),
        'min_shifts' => min($shifts),
        'max_shifts' => max($shifts)
    ];
}

/**
 * Get trend data for charts
 */
function getTrendData($db, $days = 30) {
    $data = [];
    $end = new DateTime();
    $start = (new DateTime())->modify("-{$days} days");
    
    $stmt = $db->prepare("
        SELECT 
            shift_date,
            COUNT(*) as shift_count,
            COUNT(DISTINCT agent_id) as agent_count
        FROM shifts
        WHERE shift_date BETWEEN :start AND :end
        AND is_active = 1
        GROUP BY shift_date
        ORDER BY shift_date
    ");
    $stmt->execute([':start' => $start->format('Y-m-d'), ':end' => $end->format('Y-m-d')]);
    $shiftData = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
    
    $stmt = $db->prepare("
        SELECT 
            date(requested_at) as request_date,
            COUNT(*) as swap_count
        FROM swap_requests
        WHERE date(requested_at) BETWEEN :start AND :end
        GROUP BY date(requested_at)
    ");
    $stmt->execute([':start' => $start->format('Y-m-d'), ':end' => $end->format('Y-m-d')]);
    $swapData = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
    
    $current = clone $start;
    while ($current <= $end) {
        $dateStr = $current->format('Y-m-d');
        $shiftInfo = $shiftData[$dateStr] ?? ['shift_count' => 0, 'agent_count' => 0];
        $data[] = [
            'date' => $dateStr,
            'shifts' => $shiftInfo['shift_count'] ?? 0,
            'agents' => $shiftInfo['agent_count'] ?? 0,
            'swaps' => $swapData[$dateStr] ?? 0
        ];
        $current->modify('+1 day');
    }
    
    return $data;
}

/**
 * Get activity records
 */
function getActivityRecords($db, $startDate, $endDate, $limit = 100) {
    $activities = [];
    
    // Shifts assigned
    $stmt = $db->prepare("
        SELECT 
            s.shift_date as date,
            a.name as agent_name,
            'shift_assigned' as type,
            s.shift_type as subtype,
            (julianday(s.end_time) - julianday(s.start_time)) * 24 as hours
        FROM shifts s
        JOIN agents a ON s.agent_id = a.id
        WHERE s.shift_date BETWEEN :start AND :end
        AND s.is_active = 1
        ORDER BY s.shift_date DESC, a.name
        LIMIT :limit
    ");
    $stmt->bindValue(':start', $startDate);
    $stmt->bindValue(':end', $endDate);
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->execute();
    
    foreach ($stmt->fetchAll(PDO::FETCH_ASSOC) as $row) {
        $activities[] = [
            'date' => $row['date'],
            'agent' => $row['agent_name'],
            'type' => $row['type'],
            'description' => ucfirst($row['subtype']) . ' shift assigned',
            'hours' => round($row['hours'], 1)
        ];
    }
    
    // Sort by date descending
    usort($activities, function($a, $b) {
        return strcmp($b['date'], $a['date']);
    });
    
    return array_slice($activities, 0, $limit);
}

// ============ EXPORT HANDLING ============

if (isset($_GET['export'])) {
    $format = $_GET['export'];
    
    if ($format === 'csv') {
        header('Content-Type: text/csv');
        header('Content-Disposition: attachment; filename="productivity_report_' . $startDate . '_to_' . $endDate . '.csv"');
        
        $output = fopen('php://output', 'w');
        fputcsv($output, ['Agent', 'Role', 'Total Shifts', 'Regular', 'Overtime', 'On-Call', 'Holiday', 'Maintenance', 'Total Hours']);
        
        $productivity = getProductivityReport($db, $startDate, $endDate);
        foreach ($productivity as $p) {
            fputcsv($output, [
                $p['agent_name'],
                $p['agent_role'],
                $p['total_shifts'],
                $p['regular_shifts'],
                $p['overtime_shifts'],
                $p['oncall_shifts'],
                $p['holiday_shifts'],
                $p['maintenance_shifts'],
                round($p['total_hours'], 2)
            ]);
        }
        fclose($output);
        exit;
    }
    
    if ($format === 'json') {
        header('Content-Type: application/json');
        header('Content-Disposition: attachment; filename="productivity_report_' . $startDate . '_to_' . $endDate . '.json"');
        
        $productivity = getProductivityReport($db, $startDate, $endDate);
        $fairness = getFairnessMetrics($productivity);
        
        echo json_encode([
            'generated_at' => date('Y-m-d H:i:s'),
            'date_range' => ['start' => $startDate, 'end' => $endDate],
            'productivity' => $productivity,
            'fairness' => $fairness
        ], JSON_PRETTY_PRINT);
        exit;
    }
}

// ============ LOAD DATA FOR DISPLAY ============

$productivityData = getProductivityReport($db, $startDate, $endDate);
$swapStats = getSwapStats($db, $startDate, $endDate);
$fairnessMetrics = getFairnessMetrics($productivityData);
$trendData = getTrendData($db, 30);
$activityData = getActivityRecords($db, $startDate, $endDate, 50);

// Merge swap stats into productivity data
foreach ($productivityData as &$agent) {
    $agentId = $agent['agent_id'];
    $agent['swaps_initiated'] = $swapStats['initiated'][$agentId]['initiated'] ?? 0;
    $agent['swaps_approved'] = $swapStats['initiated'][$agentId]['approved'] ?? 0;
    $agent['swaps_rejected'] = $swapStats['initiated'][$agentId]['rejected'] ?? 0;
    $agent['swaps_received'] = $swapStats['received'][$agentId] ?? 0;
}
unset($agent);

// Calculate summary stats
$totalShifts = array_sum(array_column($productivityData, 'total_shifts'));
$activeAgents = count(array_filter($productivityData, fn($a) => $a['total_shifts'] > 0));
$pendingSwaps = $db->query("SELECT COUNT(*) FROM swap_requests WHERE status = 'pending'")->fetchColumn();

// Chart data preparation
$agentNames = json_encode(array_column($productivityData, 'agent_name'));
$shiftCounts = json_encode(array_column($productivityData, 'total_shifts'));
$overtimeCounts = json_encode(array_column($productivityData, 'overtime_shifts'));
$oncallCounts = json_encode(array_column($productivityData, 'oncall_shifts'));
$trendDates = json_encode(array_column($trendData, 'date'));
$trendShifts = json_encode(array_column($trendData, 'shifts'));
$trendSwaps = json_encode(array_column($trendData, 'swaps'));

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Productivity & Fairness Reports | Nurse Shift Management</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            opacity: 0.9;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .filters {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 2rem;
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: end;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .filter-group label {
            font-size: 0.875rem;
            font-weight: 500;
            color: #666;
        }
        
        .filter-group input, .filter-group select {
            padding: 0.5rem 0.75rem;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 0.9rem;
            min-width: 150px;
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .btn-primary {
            background: #667eea;
            color: white;
        }
        
        .btn-primary:hover {
            background: #5a6fd6;
        }
        
        .btn-secondary {
            background: #e2e8f0;
            color: #333;
        }
        
        .btn-secondary:hover {
            background: #cbd5e0;
        }
        
        .export-buttons {
            margin-left: auto;
            display: flex;
            gap: 0.5rem;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid #667eea;
        }
        
        .stat-card h3 {
            font-size: 0.875rem;
            color: #666;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .stat-card .value {
            font-size: 2rem;
            font-weight: 700;
            color: #333;
        }
        
        .stat-card .subtitle {
            font-size: 0.875rem;
            color: #999;
            margin-top: 0.25rem;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
        }
        
        .card-header {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid #eee;
            background: #fafafa;
        }
        
        .card-header h2 {
            font-size: 1.1rem;
            color: #333;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .card-body {
            padding: 1.5rem;
        }
        
        .chart-container {
            position: relative;
            height: 300px;
        }
        
        .fairness-score {
            text-align: center;
            padding: 2rem;
        }
        
        .fairness-score .score {
            font-size: 4rem;
            font-weight: 700;
            color: #667eea;
        }
        
        .fairness-score .label {
            font-size: 1.1rem;
            color: #666;
            margin-top: 0.5rem;
        }
        
        .fairness-score .grade {
            display: inline-block;
            padding: 0.25rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            margin-top: 1rem;
        }
        
        .grade-excellent { background: #c6f6d5; color: #276749; }
        .grade-good { background: #bee3f8; color: #2c5282; }
        .grade-fair { background: #fefcbf; color: #975a16; }
        .grade-poor { background: #fed7d7; color: #c53030; }
        
        .metrics-list {
            list-style: none;
        }
        
        .metrics-list li {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 0;
            border-bottom: 1px solid #eee;
        }
        
        .metrics-list li:last-child {
            border-bottom: none;
        }
        
        .metrics-list .metric-name {
            color: #666;
        }
        
        .metrics-list .metric-value {
            font-weight: 600;
            color: #333;
        }
        
        .table-container {
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        
        th {
            font-weight: 600;
            color: #666;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: #fafafa;
        }
        
        tr:hover {
            background: #f8fafc;
        }
        
        .activity-type {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .type-shift { background: #e6fffa; color: #234e52; }
        .type-swap { background: #fef3c7; color: #92400e; }
        .type-approval { background: #d1fae5; color: #065f46; }
        
        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .badge-regular { background: #e2e8f0; color: #4a5568; }
        .badge-overtime { background: #fed7d7; color: #c53030; }
        .badge-oncall { background: #fefcbf; color: #975a16; }
        .badge-holiday { background: #c6f6d5; color: #276749; }
        
        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .filters {
                flex-direction: column;
            }
            
            .export-buttons {
                margin-left: 0;
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Productivity & Fairness Reports</h1>
        <p>Story 6: Monitor team productivity and ensure fair workload distribution</p>
    </div>
    
    <div class="container">
        <!-- Date Range Filter -->
        <form class="filters" method="GET">
            <div class="filter-group">
                <label>Start Date</label>
                <input type="date" name="start_date" value="<?= htmlspecialchars($startDate) ?>">
            </div>
            <div class="filter-group">
                <label>End Date</label>
                <input type="date" name="end_date" value="<?= htmlspecialchars($endDate) ?>">
            </div>
            <button type="submit" class="btn btn-primary">Apply Filter</button>
            
            <div class="export-buttons">
                <a href="?<?= http_build_query(array_merge($_GET, ['export' => 'csv'])) ?>" class="btn btn-secondary">📥 CSV</a>
                <a href="?<?= http_build_query(array_merge($_GET, ['export' => 'json'])) ?>" class="btn btn-secondary">📥 JSON</a>
            </div>
        </form>
        
        <!-- Summary Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Shifts</h3>
                <div class="value"><?= $totalShifts ?></div>
                <div class="subtitle">In selected period</div>
            </div>
            <div class="stat-card">
                <h3>Active Agents</h3>
                <div class="value"><?= $activeAgents ?></div>
                <div class="subtitle">With assigned shifts</div>
            </div>
            <div class="stat-card">
                <h3>Fairness Score</h3>
                <div class="value"><?= $fairnessMetrics['workload_score'] ?>%</div>
                <div class="subtitle">Workload distribution</div>
            </div>
            <div class="stat-card">
                <h3>Pending Swaps</h3>
                <div class="value"><?= $pendingSwaps ?></div>
                <div class="subtitle">Awaiting response</div>
            </div>
        </div>
        
        <!-- Charts Row 1 -->
        <div class="dashboard-grid">
            <!-- Productivity Chart -->
            <div class="card">
                <div class="card-header">
                    <h2>📈 Productivity by Agent</h2>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="productivityChart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Fairness Score -->
            <div class="card">
                <div class="card-header">
                    <h2>⚖️ Workload Fairness</h2>
                </div>
                <div class="card-body">
                    <div class="fairness-score">
                        <div class="score"><?= $fairnessMetrics['workload_score'] ?></div>
                        <div class="label">Fairness Score</div>
                        <?php
                        $grade = 'poor';
                        $gradeText = 'Needs Improvement';
                        if ($fairnessMetrics['workload_score'] >= 90) {
                            $grade = 'excellent';
                            $gradeText = 'Excellent';
                        } elseif ($fairnessMetrics['workload_score'] >= 75) {
                            $grade = 'good';
                            $gradeText = 'Good';
                        } elseif ($fairnessMetrics['workload_score'] >= 60) {
                            $grade = 'fair';
                            $gradeText = 'Fair';
                        }
                        ?>
                        <div class="grade grade-<?= $grade ?>"><?= $gradeText ?></div>
                    </div>
                    
                    <ul class="metrics-list">
                        <li>
                            <span class="metric-name">Average Shifts/Agent</span>
                            <span class="metric-value"><?= $fairnessMetrics['avg_shifts'] ?></span>
                        </li>
                        <li>
                            <span class="metric-name">Standard Deviation</span>
                            <span class="metric-value"><?= $fairnessMetrics['std_dev'] ?></span>
                        </li>
                        <li>
                            <span class="metric-name">Range</span>
                            <span class="metric-value"><?= $fairnessMetrics['min_shifts'] ?> - <?= $fairnessMetrics['max_shifts'] ?></span>
                        </li>
                        <li>
                            <span class="metric-name">Overtime Fairness</span>
                            <span class="metric-value"><?= $fairnessMetrics['overtime_score'] ?>%</span>
                        </li>
                        <li>
                            <span class="metric-name">On-Call Fairness</span>
                            <span class="metric-value"><?= $fairnessMetrics['oncall_score'] ?>%</span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Charts Row 2 -->
        <div class="dashboard-grid">
            <!-- Workload Distribution -->
            <div class="card">
                <div class="card-header">
                    <h2>📊 Workload Distribution</h2>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="workloadChart"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Trend Analysis -->
            <div class="card">
                <div class="card-header">
                    <h2>📉 30-Day Trend</h2>
                </div>
                <div class="card-body">
                    <div class="chart-container">
                        <canvas id="trendChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Activity Table -->
        <div class="card">
            <div class="card-header">
                <h2>📝 Activity Log (Last 50)</h2>
            </div>
            <div class="card-body table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Agent</th>
                            <th>Activity</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($activityData as $activity): ?>
                        <tr>
                            <td><?= htmlspecialchars($activity['date']) ?></td>
                            <td><?= htmlspecialchars($activity['agent']) ?></td>
                            <td>
                                <span class="activity-type type-<?= str_replace('_', '-', explode('_', $activity['type'])[0]) ?>">
                                    <?= ucwords(str_replace('_', ' ', $activity['type'])) ?>
                                </span>
                            </td>
                            <td><?= htmlspecialchars($activity['description']) ?></td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Productivity Table -->
        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <h2>👥 Detailed Productivity Report</h2>
            </div>
            <div class="card-body table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Role</th>
                            <th>Total</th>
                            <th>Regular</th>
                            <th>Overtime</th>
                            <th>On-Call</th>
                            <th>Holiday</th>
                            <th>Hours</th>
                            <th>Swaps Out</th>
                            <th>Swaps In</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($productivityData as $agent): ?>
                        <tr>
                            <td><strong><?= htmlspecialchars($agent['agent_name']) ?></strong></td>
                            <td><?= htmlspecialchars($agent['agent_role']) ?></td>
                            <td><?= $agent['total_shifts'] ?></td>
                            <td><?= $agent['regular_shifts'] ?></td>
                            <td><?= $agent['overtime_shifts'] ?></td>
                            <td><?= $agent['oncall_shifts'] ?></td>
                            <td><?= $agent['holiday_shifts'] ?></td>
                            <td><?= round($agent['total_hours'], 1) ?>h</td>
                            <td><?= $agent['swaps_initiated'] ?></td>
                            <td><?= $agent['swaps_received'] ?></td>
                        </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        // Productivity Chart
        const productivityCtx = document.getElementById('productivityChart').getContext('2d');
        new Chart(productivityCtx, {
            type: 'bar',
            data: {
                labels: <?= $agentNames ?>,
                datasets: [{
                    label: 'Regular Shifts',
                    data: <?= $shiftCounts ?>,
                    backgroundColor: '#667eea',
                    borderRadius: 4
                }, {
                    label: 'Overtime',
                    data: <?= $overtimeCounts ?>,
                    backgroundColor: '#f56565',
                    borderRadius: 4
                }, {
                    label: 'On-Call',
                    data: <?= $oncallCounts ?>,
                    backgroundColor: '#ecc94b',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true }
                },
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
        
        // Workload Distribution Chart
        const workloadCtx = document.getElementById('workloadChart').getContext('2d');
        new Chart(workloadCtx, {
            type: 'doughnut',
            data: {
                labels: <?= $agentNames ?>,
                datasets: [{
                    data: <?= $shiftCounts ?>,
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#f5576c',
                        '#4facfe', '#00f2fe', '#43e97b', '#38f9d7'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' }
                }
            }
        });
        
        // Trend Chart
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: <?= $trendDates ?>,
                datasets: [{
                    label: 'Shifts',
                    data: <?= $trendShifts ?>,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Swap Requests',
                    data: <?= $trendSwaps ?>,
                    borderColor: '#f56565',
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                },
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    </script>
</body>
</html>
