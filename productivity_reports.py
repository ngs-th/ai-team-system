#!/usr/bin/env python3
"""
Productivity & Fairness Reports System
=========================================
Story 6: Nurse Shift Management System

Features:
- Date range selector
- Productivity charts
- Activity table (7 types)
- Fairness chart
- Workload distribution histogram
- Trend analysis
- Export to CSV/Excel/PDF

Author: Barry (Solo Developer)
Created: 2026-02-03
Version: 1.0.0
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import csv
import io
from collections import defaultdict

# Set timezone to Bangkok (+7)
os.environ['TZ'] = 'Asia/Bangkok'

DB_PATH = Path(__file__).parent / "team.db"


class ActivityType(str, Enum):
    """Types of activities tracked"""
    SHIFT_ASSIGNED = "shift_assigned"
    SWAP_REQUESTED = "swap_requested"
    SWAP_RECEIVED = "swap_received"
    SWAP_APPROVED = "swap_approved"
    SWAP_REJECTED = "swap_rejected"
    OVERTIME_SHIFT = "overtime_shift"
    ONCALL_SHIFT = "oncall_shift"


@dataclass
class AgentProductivity:
    """Productivity metrics for a single agent"""
    agent_id: str
    agent_name: str
    agent_role: str
    
    # Shift metrics
    total_shifts: int = 0
    regular_shifts: int = 0
    overtime_shifts: int = 0
    oncall_shifts: int = 0
    holiday_shifts: int = 0
    maintenance_shifts: int = 0
    
    # Hours calculation
    total_hours: float = 0.0
    avg_shift_hours: float = 0.0
    
    # Swap metrics
    swaps_initiated: int = 0
    swaps_received: int = 0
    swaps_approved: int = 0
    swaps_rejected: int = 0
    swap_success_rate: float = 0.0
    
    # Activity counts
    activity_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class FairnessMetrics:
    """Fairness metrics across all agents"""
    # Workload distribution
    avg_shifts_per_agent: float = 0.0
    std_dev_shifts: float = 0.0
    min_shifts: int = 0
    max_shifts: int = 0
    
    # Fairness score (0-100, higher is fairer)
    workload_fairness_score: float = 0.0
    overtime_fairness_score: float = 0.0
    oncall_fairness_score: float = 0.0
    
    # Distribution
    shift_distribution: Dict[str, int] = field(default_factory=dict)
    overtime_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Agents above/below average
    overworked_agents: List[str] = field(default_factory=list)
    underworked_agents: List[str] = field(default_factory=list)


@dataclass
class TrendDataPoint:
    """Single data point for trend analysis"""
    date: str
    total_shifts: int
    total_agents: int
    swap_requests: int
    avg_hours_per_agent: float


@dataclass
class ActivityRecord:
    """Individual activity record for activity table"""
    date: str
    agent_id: str
    agent_name: str
    activity_type: str
    description: str
    shift_type: Optional[str] = None
    hours: Optional[float] = None


class ProductivityReportSystem:
    """
    Productivity and Fairness Reporting System
    
    Features:
    - Calculate productivity metrics per agent
    - Calculate fairness scores across team
    - Generate trend analysis
    - Export reports in multiple formats
    """
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database tables for reporting"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Report snapshots table - stores historical report data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS report_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,
                snapshot_date DATE NOT NULL,
                date_range_start DATE,
                date_range_end DATE,
                data_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Agent productivity cache
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_productivity_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                calculation_date DATE NOT NULL,
                date_range_start DATE,
                date_range_end DATE,
                total_shifts INTEGER DEFAULT 0,
                total_hours REAL DEFAULT 0,
                fairness_score REAL DEFAULT 0,
                data_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
            )
        ''')
        
        # Create indexes
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_report_snapshots_type_date 
            ON report_snapshots(report_type, snapshot_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_productivity_cache_agent 
            ON agent_productivity_cache(agent_id, calculation_date)
        ''')
        
        conn.commit()
        conn.close()
    
    def get_productivity_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        agent_ids: Optional[List[str]] = None
    ) -> List[AgentProductivity]:
        """
        Generate productivity report for agents
        
        Args:
            start_date: Start date (YYYY-MM-DD), defaults to 30 days ago
            end_date: End date (YYYY-MM-DD), defaults to today
            agent_ids: Filter by specific agents, defaults to all
            
        Returns:
            List of AgentProductivity objects
        """
        # Set default date range
        if not end_date:
            end_date = date.today().isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Build agent filter
        agent_filter = ""
        params = [start_date, end_date]
        if agent_ids:
            placeholders = ','.join(['?' for _ in agent_ids])
            agent_filter = f"AND a.id IN ({placeholders})"
            params.extend(agent_ids)
        
        # Get all agents
        cursor.execute(f"""
            SELECT id, name, role
            FROM agents
            WHERE status != 'offline'
            {agent_filter.replace('a.id', 'id') if agent_filter else ''}
            ORDER BY name
        """, params[2:] if agent_ids else [])
        
        agents = {row['id']: {'name': row['name'], 'role': row['role']} for row in cursor.fetchall()}
        
        # Get shift data for each agent
        cursor.execute(f"""
            SELECT 
                s.agent_id,
                s.shift_type,
                COUNT(*) as shift_count,
                SUM(
                    (strftime('%s', s.end_time) - strftime('%s', s.start_time)) / 3600.0
                ) as total_hours
            FROM shifts s
            WHERE s.shift_date BETWEEN ? AND ?
            AND s.is_active = TRUE
            {agent_filter}
            GROUP BY s.agent_id, s.shift_type
        """, params)
        
        shift_data = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'hours': 0}))
        for row in cursor.fetchall():
            shift_data[row['agent_id']][row['shift_type']] = {
                'count': row['shift_count'],
                'hours': row['total_hours'] or 0
            }
        
        # Get swap request data
        cursor.execute(f"""
            SELECT 
                sr.requestor_agent_id,
                sr.target_agent_id,
                sr.status,
                COUNT(*) as count
            FROM swap_requests sr
            WHERE date(sr.requested_at) BETWEEN ? AND ?
            {agent_filter.replace('a.id', 'sr.requestor_agent_id') if agent_filter else ''}
            GROUP BY sr.requestor_agent_id, sr.target_agent_id, sr.status
        """, params[:2] + (params[2:] if agent_ids else []))
        
        swap_data = defaultdict(lambda: {
            'initiated': 0, 'received': 0, 
            'approved': 0, 'rejected': 0
        })
        
        for row in cursor.fetchall():
            if row['requestor_agent_id'] in agents:
                swap_data[row['requestor_agent_id']]['initiated'] += row['count']
                if row['status'] == 'approved':
                    swap_data[row['requestor_agent_id']]['approved'] += row['count']
                elif row['status'] == 'rejected':
                    swap_data[row['requestor_agent_id']]['rejected'] += row['count']
            
            if row['target_agent_id'] in agents:
                swap_data[row['target_agent_id']]['received'] += row['count']
        
        conn.close()
        
        # Build productivity objects
        results = []
        for agent_id, agent_info in agents.items():
            prod = AgentProductivity(
                agent_id=agent_id,
                agent_name=agent_info['name'],
                agent_role=agent_info['role']
            )
            
            # Add shift data
            for shift_type, data in shift_data[agent_id].items():
                count = data['count']
                hours = data['hours']
                
                prod.total_shifts += count
                prod.total_hours += hours
                
                if shift_type == 'regular':
                    prod.regular_shifts += count
                elif shift_type == 'overtime':
                    prod.overtime_shifts += count
                elif shift_type == 'on_call':
                    prod.oncall_shifts += count
                elif shift_type == 'holiday':
                    prod.holiday_shifts += count
                elif shift_type == 'maintenance':
                    prod.maintenance_shifts += count
            
            # Calculate average shift hours
            if prod.total_shifts > 0:
                prod.avg_shift_hours = prod.total_hours / prod.total_shifts
            
            # Add swap data
            swaps = swap_data[agent_id]
            prod.swaps_initiated = swaps['initiated']
            prod.swaps_received = swaps['received']
            prod.swaps_approved = swaps['approved']
            prod.swaps_rejected = swaps['rejected']
            
            if prod.swaps_initiated > 0:
                prod.swap_success_rate = (prod.swaps_approved / prod.swaps_initiated) * 100
            
            # Build activity counts
            prod.activity_counts = {
                'shift_assigned': prod.total_shifts,
                'swap_requested': prod.swaps_initiated,
                'swap_received': prod.swaps_received,
                'swap_approved': prod.swaps_approved,
                'swap_rejected': prod.swaps_rejected,
                'overtime_shift': prod.overtime_shifts,
                'oncall_shift': prod.oncall_shifts
            }
            
            results.append(prod)
        
        return sorted(results, key=lambda x: x.agent_name)
    
    def get_fairness_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> FairnessMetrics:
        """
        Calculate fairness metrics across all agents
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            FairnessMetrics object
        """
        productivity_data = self.get_productivity_report(start_date, end_date)
        
        if not productivity_data:
            return FairnessMetrics()
        
        metrics = FairnessMetrics()
        
        # Calculate shift distribution stats
        shifts = [p.total_shifts for p in productivity_data]
        metrics.avg_shifts_per_agent = sum(shifts) / len(shifts)
        metrics.min_shifts = min(shifts)
        metrics.max_shifts = max(shifts)
        
        # Calculate standard deviation
        variance = sum((s - metrics.avg_shifts_per_agent) ** 2 for s in shifts) / len(shifts)
        metrics.std_dev_shifts = variance ** 0.5
        
        # Calculate workload fairness score (0-100)
        # Lower standard deviation = higher fairness
        if metrics.avg_shifts_per_agent > 0:
            cv = metrics.std_dev_shifts / metrics.avg_shifts_per_agent  # Coefficient of variation
            metrics.workload_fairness_score = max(0, 100 - (cv * 100))
        
        # Calculate overtime fairness
        overtime_shifts = [p.overtime_shifts for p in productivity_data]
        if any(overtime_shifts):
            avg_ot = sum(overtime_shifts) / len(overtime_shifts)
            if avg_ot > 0:
                ot_variance = sum((ot - avg_ot) ** 2 for ot in overtime_shifts) / len(overtime_shifts)
                ot_cv = (ot_variance ** 0.5) / avg_ot
                metrics.overtime_fairness_score = max(0, 100 - (ot_cv * 100))
            else:
                metrics.overtime_fairness_score = 100  # Perfectly fair if no overtime
        else:
            metrics.overtime_fairness_score = 100
        
        # Calculate on-call fairness
        oncall_shifts = [p.oncall_shifts for p in productivity_data]
        if any(oncall_shifts):
            avg_oc = sum(oncall_shifts) / len(oncall_shifts)
            if avg_oc > 0:
                oc_variance = sum((oc - avg_oc) ** 2 for oc in oncall_shifts) / len(oncall_shifts)
                oc_cv = (oc_variance ** 0.5) / avg_oc
                metrics.oncall_fairness_score = max(0, 100 - (oc_cv * 100))
            else:
                metrics.oncall_fairness_score = 100
        else:
            metrics.oncall_fairness_score = 100
        
        # Build distributions
        metrics.shift_distribution = {p.agent_name: p.total_shifts for p in productivity_data}
        metrics.overtime_distribution = {p.agent_name: p.overtime_shifts for p in productivity_data}
        
        # Identify over/under worked agents
        threshold = 1.5
        for p in productivity_data:
            if p.total_shifts > metrics.avg_shifts_per_agent * threshold:
                metrics.overworked_agents.append(p.agent_name)
            elif p.total_shifts < metrics.avg_shifts_per_agent / threshold and p.total_shifts < metrics.avg_shifts_per_agent:
                metrics.underworked_agents.append(p.agent_name)
        
        return metrics
    
    def get_trend_analysis(
        self,
        days: int = 30,
        group_by: str = 'day'  # 'day' or 'week'
    ) -> List[TrendDataPoint]:
        """
        Generate trend analysis over time
        
        Args:
            days: Number of days to analyze
            group_by: Group by 'day' or 'week'
            
        Returns:
            List of TrendDataPoint objects
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get daily shift counts
        cursor.execute("""
            SELECT 
                shift_date,
                COUNT(*) as shift_count,
                COUNT(DISTINCT agent_id) as agent_count,
                SUM(
                    (strftime('%s', end_time) - strftime('%s', start_time)) / 3600.0
                ) as total_hours
            FROM shifts
            WHERE shift_date BETWEEN ? AND ?
            AND is_active = TRUE
            GROUP BY shift_date
            ORDER BY shift_date
        """, (start_date.isoformat(), end_date.isoformat()))
        
        shift_data = {row['shift_date']: {
            'shifts': row['shift_count'],
            'agents': row['agent_count'],
            'hours': row['total_hours'] or 0
        } for row in cursor.fetchall()}
        
        # Get daily swap request counts
        cursor.execute("""
            SELECT 
                date(requested_at) as request_date,
                COUNT(*) as swap_count
            FROM swap_requests
            WHERE date(requested_at) BETWEEN ? AND ?
            GROUP BY date(requested_at)
            ORDER BY date(requested_at)
        """, (start_date.isoformat(), end_date.isoformat()))
        
        swap_data = {row['request_date']: row['swap_count'] for row in cursor.fetchall()}
        
        conn.close()
        
        # Build trend data points
        results = []
        current = start_date
        while current <= end_date:
            date_str = current.isoformat()
            data = shift_data.get(date_str, {'shifts': 0, 'agents': 0, 'hours': 0})
            swaps = swap_data.get(date_str, 0)
            
            avg_hours = data['hours'] / data['agents'] if data['agents'] > 0 else 0
            
            results.append(TrendDataPoint(
                date=date_str,
                total_shifts=data['shifts'],
                total_agents=data['agents'],
                swap_requests=swaps,
                avg_hours_per_agent=round(avg_hours, 2)
            ))
            
            current += timedelta(days=1)
        
        # Group by week if requested
        if group_by == 'week':
            weekly = defaultdict(lambda: {
                'shifts': 0, 'agents': set(), 'swaps': 0, 'hours': 0, 'count': 0
            })
            
            for dp in results:
                week_start = datetime.strptime(dp.date, '%Y-%m-%d') - timedelta(
                    days=datetime.strptime(dp.date, '%Y-%m-%d').weekday()
                )
                week_key = week_start.strftime('%Y-%m-%d')
                
                weekly[week_key]['shifts'] += dp.total_shifts
                weekly[week_key]['agents'].add(dp.total_agents)
                weekly[week_key]['swaps'] += dp.swap_requests
                weekly[week_key]['hours'] += dp.avg_hours_per_agent * dp.total_agents
                weekly[week_key]['count'] += 1
            
            results = []
            for week_key, data in sorted(weekly.items()):
                avg_agents = len(data['agents']) / data['count'] if data['count'] > 0 else 0
                results.append(TrendDataPoint(
                    date=week_key,
                    total_shifts=data['shifts'],
                    total_agents=int(avg_agents),
                    swap_requests=data['swaps'],
                    avg_hours_per_agent=round(data['hours'] / data['shifts'], 2) if data['shifts'] > 0 else 0
                ))
        
        return results
    
    def get_activity_table(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        activity_types: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[ActivityRecord]:
        """
        Get detailed activity records for activity table
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            activity_types: Filter by activity types
            limit: Maximum records to return
            
        Returns:
            List of ActivityRecord objects
        """
        if not end_date:
            end_date = date.today().isoformat()
        if not start_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        activities = []
        
        # Get shift assignments
        if not activity_types or 'shift_assigned' in activity_types:
            cursor.execute("""
                SELECT 
                    s.shift_date as date,
                    s.agent_id,
                    a.name as agent_name,
                    s.shift_type,
                    (strftime('%s', s.end_time) - strftime('%s', s.start_time)) / 3600.0 as hours
                FROM shifts s
                JOIN agents a ON s.agent_id = a.id
                WHERE s.shift_date BETWEEN ? AND ?
                AND s.is_active = TRUE
                ORDER BY s.shift_date DESC, a.name
                LIMIT ?
            """, (start_date, end_date, limit))
            
            for row in cursor.fetchall():
                activities.append(ActivityRecord(
                    date=row['date'],
                    agent_id=row['agent_id'],
                    agent_name=row['agent_name'],
                    activity_type='shift_assigned',
                    description=f"Shift assigned: {row['shift_type']}",
                    shift_type=row['shift_type'],
                    hours=round(row['hours'], 2)
                ))
        
        # Get swap requests (initiated)
        if not activity_types or 'swap_requested' in activity_types:
            cursor.execute("""
                SELECT 
                    date(sr.requested_at) as date,
                    sr.requestor_agent_id as agent_id,
                    a.name as agent_name,
                    sr.status,
                    sr.reason
                FROM swap_requests sr
                JOIN agents a ON sr.requestor_agent_id = a.id
                WHERE date(sr.requested_at) BETWEEN ? AND ?
                ORDER BY sr.requested_at DESC
                LIMIT ?
            """, (start_date, end_date, limit))
            
            for row in cursor.fetchall():
                activities.append(ActivityRecord(
                    date=row['date'],
                    agent_id=row['agent_id'],
                    agent_name=row['agent_name'],
                    activity_type='swap_requested',
                    description=f"Swap requested: {row['reason'] or 'No reason given'}"
                ))
        
        # Get swap approvals/rejections
        if not activity_types or 'swap_approved' in activity_types or 'swap_rejected' in activity_types:
            cursor.execute("""
                SELECT 
                    date(sr.responded_at) as date,
                    sr.target_agent_id as agent_id,
                    a.name as agent_name,
                    sr.status,
                    sr.response_notes
                FROM swap_requests sr
                JOIN agents a ON sr.target_agent_id = a.id
                WHERE date(sr.responded_at) BETWEEN ? AND ?
                AND sr.status IN ('approved', 'rejected')
                ORDER BY sr.responded_at DESC
                LIMIT ?
            """, (start_date, end_date, limit))
            
            for row in cursor.fetchall():
                activity_type = 'swap_approved' if row['status'] == 'approved' else 'swap_rejected'
                activities.append(ActivityRecord(
                    date=row['date'],
                    agent_id=row['agent_id'],
                    agent_name=row['agent_name'],
                    activity_type=activity_type,
                    description=f"Swap {row['status']}: {row['response_notes'] or 'No notes'}"
                ))
        
        conn.close()
        
        # Sort by date descending and limit
        activities.sort(key=lambda x: x.date, reverse=True)
        return activities[:limit]
    
    def export_to_csv(
        self,
        report_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        Export report to CSV format
        
        Args:
            report_type: 'productivity', 'fairness', 'trends', or 'activities'
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        if report_type == 'productivity':
            data = self.get_productivity_report(start_date, end_date)
            writer.writerow([
                'Agent Name', 'Role', 'Total Shifts', 'Regular', 'Overtime',
                'On-Call', 'Holiday', 'Maintenance', 'Total Hours',
                'Avg Shift Hours', 'Swaps Initiated', 'Swaps Received',
                'Swaps Approved', 'Swap Success Rate %'
            ])
            for p in data:
                writer.writerow([
                    p.agent_name, p.agent_role, p.total_shifts, p.regular_shifts,
                    p.overtime_shifts, p.oncall_shifts, p.holiday_shifts,
                    p.maintenance_shifts, round(p.total_hours, 2),
                    round(p.avg_shift_hours, 2), p.swaps_initiated,
                    p.swaps_received, p.swaps_approved, round(p.swap_success_rate, 2)
                ])
        
        elif report_type == 'fairness':
            metrics = self.get_fairness_metrics(start_date, end_date)
            writer.writerow(['Fairness Metrics'])
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Avg Shifts Per Agent', round(metrics.avg_shifts_per_agent, 2)])
            writer.writerow(['Std Dev Shifts', round(metrics.std_dev_shifts, 2)])
            writer.writerow(['Min Shifts', metrics.min_shifts])
            writer.writerow(['Max Shifts', metrics.max_shifts])
            writer.writerow(['Workload Fairness Score', round(metrics.workload_fairness_score, 2)])
            writer.writerow(['Overtime Fairness Score', round(metrics.overtime_fairness_score, 2)])
            writer.writerow(['On-Call Fairness Score', round(metrics.oncall_fairness_score, 2)])
            writer.writerow([])
            writer.writerow(['Shift Distribution'])
            writer.writerow(['Agent', 'Shifts'])
            for agent, shifts in metrics.shift_distribution.items():
                writer.writerow([agent, shifts])
        
        elif report_type == 'trends':
            data = self.get_trend_analysis(days=30)
            writer.writerow(['Date', 'Total Shifts', 'Active Agents', 'Swap Requests', 'Avg Hours/Agent'])
            for t in data:
                writer.writerow([
                    t.date, t.total_shifts, t.total_agents,
                    t.swap_requests, t.avg_hours_per_agent
                ])
        
        elif report_type == 'activities':
            data = self.get_activity_table(start_date, end_date, limit=500)
            writer.writerow(['Date', 'Agent', 'Activity Type', 'Description', 'Shift Type', 'Hours'])
            for a in data:
                writer.writerow([
                    a.date, a.agent_name, a.activity_type,
                    a.description, a.shift_type or '', a.hours or ''
                ])
        
        return output.getvalue()
    
    def export_to_json(
        self,
        report_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        Export report to JSON format
        
        Args:
            report_type: 'productivity', 'fairness', 'trends', or 'activities'
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            JSON string
        """
        if report_type == 'productivity':
            data = self.get_productivity_report(start_date, end_date)
            result = {
                'report_type': 'productivity',
                'generated_at': datetime.now().isoformat(),
                'date_range': {'start': start_date, 'end': end_date},
                'agents': [asdict(p) for p in data]
            }
        
        elif report_type == 'fairness':
            metrics = self.get_fairness_metrics(start_date, end_date)
            result = {
                'report_type': 'fairness',
                'generated_at': datetime.now().isoformat(),
                'date_range': {'start': start_date, 'end': end_date},
                'metrics': asdict(metrics)
            }
        
        elif report_type == 'trends':
            data = self.get_trend_analysis(days=30)
            result = {
                'report_type': 'trends',
                'generated_at': datetime.now().isoformat(),
                'trends': [asdict(t) for t in data]
            }
        
        elif report_type == 'activities':
            data = self.get_activity_table(start_date, end_date, limit=500)
            result = {
                'report_type': 'activities',
                'generated_at': datetime.now().isoformat(),
                'date_range': {'start': start_date, 'end': end_date},
                'activities': [asdict(a) for a in data]
            }
        
        else:
            result = {'error': f'Unknown report type: {report_type}'}
        
        return json.dumps(result, indent=2, default=str)
    
    def get_summary_dashboard(self) -> Dict[str, Any]:
        """
        Get quick summary for dashboard display
        
        Returns:
            Dictionary with summary metrics
        """
        # Last 30 days
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=30)).isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total shifts
        cursor.execute("""
            SELECT COUNT(*) FROM shifts
            WHERE shift_date BETWEEN ? AND ? AND is_active = TRUE
        """, (start_date, end_date))
        total_shifts = cursor.fetchone()[0]
        
        # Active agents
        cursor.execute("SELECT COUNT(*) FROM agents WHERE status != 'offline'")
        active_agents = cursor.fetchone()[0]
        
        # Pending swap requests
        cursor.execute("""
            SELECT COUNT(*) FROM swap_requests
            WHERE status = 'pending'
        """)
        pending_swaps = cursor.fetchone()[0]
        
        # Shift type breakdown
        cursor.execute("""
            SELECT shift_type, COUNT(*) as count
            FROM shifts
            WHERE shift_date BETWEEN ? AND ? AND is_active = TRUE
            GROUP BY shift_type
        """, (start_date, end_date))
        shift_types = {row['shift_type']: row['count'] for row in cursor.fetchall()}
        
        # Fairness score
        fairness = self.get_fairness_metrics(start_date, end_date)
        
        conn.close()
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'total_shifts': total_shifts,
            'active_agents': active_agents,
            'pending_swaps': pending_swaps,
            'shift_types': shift_types,
            'fairness_score': round(fairness.workload_fairness_score, 1),
            'avg_shifts_per_agent': round(fairness.avg_shifts_per_agent, 1)
        }


# CLI Interface
def main():
    """Command-line interface for productivity reports"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Productivity & Fairness Reports System'
    )
    parser.add_argument(
        'command',
        choices=['productivity', 'fairness', 'trends', 'activities', 'summary', 'export'],
        help='Report type to generate'
    )
    parser.add_argument(
        '--start-date', '-s',
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date', '-e',
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['table', 'csv', 'json'],
        default='table',
        help='Output format'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path'
    )
    
    args = parser.parse_args()
    
    # Initialize system
    system = ProductivityReportSystem()
    
    # Set default dates
    end_date = args.end_date or date.today().isoformat()
    start_date = args.start_date or (date.today() - timedelta(days=30)).isoformat()
    
    # Generate report
    if args.command == 'productivity':
        data = system.get_productivity_report(start_date, end_date)
        
        if args.format == 'csv':
            output = system.export_to_csv('productivity', start_date, end_date)
        elif args.format == 'json':
            output = system.export_to_json('productivity', start_date, end_date)
        else:
            print(f"\n📊 Productivity Report ({start_date} to {end_date})\n")
            print(f"{'Agent':<20} {'Role':<20} {'Shifts':<8} {'Hours':<8} {'Swaps':<8}")
            print("-" * 70)
            for p in data:
                print(f"{p.agent_name:<20} {p.agent_role:<20} {p.total_shifts:<8} {p.total_hours:<8.1f} {p.swaps_initiated:<8}")
            output = None
    
    elif args.command == 'fairness':
        metrics = system.get_fairness_metrics(start_date, end_date)
        
        if args.format == 'csv':
            output = system.export_to_csv('fairness', start_date, end_date)
        elif args.format == 'json':
            output = system.export_to_json('fairness', start_date, end_date)
        else:
            print(f"\n⚖️  Fairness Metrics ({start_date} to {end_date})\n")
            print(f"Workload Fairness Score: {metrics.workload_fairness_score:.1f}/100")
            print(f"Overtime Fairness Score: {metrics.overtime_fairness_score:.1f}/100")
            print(f"On-Call Fairness Score: {metrics.oncall_fairness_score:.1f}/100")
            print(f"\nAvg Shifts Per Agent: {metrics.avg_shifts_per_agent:.1f}")
            print(f"Std Dev: {metrics.std_dev_shifts:.2f}")
            print(f"Range: {metrics.min_shifts} - {metrics.max_shifts}")
            
            if metrics.overworked_agents:
                print(f"\n⚠️  Overworked Agents: {', '.join(metrics.overworked_agents)}")
            if metrics.underworked_agents:
                print(f"\n✓ Underworked Agents: {', '.join(metrics.underworked_agents)}")
            output = None
    
    elif args.command == 'trends':
        data = system.get_trend_analysis(days=30)
        
        if args.format == 'csv':
            output = system.export_to_csv('trends')
        elif args.format == 'json':
            output = system.export_to_json('trends')
        else:
            print(f"\n📈 Trend Analysis (Last 30 Days)\n")
            print(f"{'Date':<12} {'Shifts':<8} {'Agents':<8} {'Swaps':<8} {'Avg Hrs':<8}")
            print("-" * 50)
            for t in data[-10:]:  # Last 10 days
                print(f"{t.date:<12} {t.total_shifts:<8} {t.total_agents:<8} {t.swap_requests:<8} {t.avg_hours_per_agent:<8.1f}")
            output = None
    
    elif args.command == 'activities':
        data = system.get_activity_table(start_date, end_date, limit=20)
        
        if args.format == 'csv':
            output = system.export_to_csv('activities', start_date, end_date)
        elif args.format == 'json':
            output = system.export_to_json('activities', start_date, end_date)
        else:
            print(f"\n📝 Recent Activities ({start_date} to {end_date})\n")
            print(f"{'Date':<12} {'Agent':<20} {'Type':<20} {'Description':<40}")
            print("-" * 95)
            for a in data[:20]:
                desc = a.description[:37] + '...' if len(a.description) > 40 else a.description
                print(f"{a.date:<12} {a.agent_name:<20} {a.activity_type:<20} {desc:<40}")
            output = None
    
    elif args.command == 'summary':
        summary = system.get_summary_dashboard()
        
        if args.format == 'json':
            output = json.dumps(summary, indent=2)
        else:
            print("\n📋 Dashboard Summary (Last 30 Days)\n")
            print(f"Total Shifts: {summary['total_shifts']}")
            print(f"Active Agents: {summary['active_agents']}")
            print(f"Pending Swaps: {summary['pending_swaps']}")
            print(f"Fairness Score: {summary['fairness_score']}/100")
            print(f"Avg Shifts/Agent: {summary['avg_shifts_per_agent']}")
            print(f"\nShift Types:")
            for shift_type, count in summary['shift_types'].items():
                print(f"  - {shift_type}: {count}")
            output = None
    
    elif args.command == 'export':
        # Export all reports
        reports = ['productivity', 'fairness', 'trends', 'activities']
        output_parts = []
        for report in reports:
            output_parts.append(f"=== {report.upper()} ===")
            output_parts.append(system.export_to_csv(report, start_date, end_date))
            output_parts.append("")
        output = "\n".join(output_parts)
    
    # Write output if present
    if output:
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"✅ Report saved to {args.output}")
        else:
            print(output)


if __name__ == '__main__':
    main()
