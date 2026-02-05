#!/usr/bin/env python3
"""
Shift Swap Request System for AI Team
======================================
Complete swap request system with approval workflow

Author: Winston (System Architect)
Created: 2026-02-03
Version: 1.0.0
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
import time

# Set timezone to Bangkok (+7)
os.environ['TZ'] = 'Asia/Bangkok'
try:
    time.tzset()
except AttributeError:
    pass

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"


class SwapStatus(str, Enum):
    """Swap request status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    COMPLETED = "completed"


class ShiftType(str, Enum):
    """Type of shift assignment"""
    REGULAR = "regular"
    ON_CALL = "on_call"
    HOLIDAY = "holiday"
    OVERTIME = "overtime"
    MAINTENANCE = "maintenance"


@dataclass
class Shift:
    """Represents a single shift assignment"""
    id: int
    agent_id: str
    shift_date: str
    start_time: str
    end_time: str
    shift_type: str
    is_recurring: bool
    recurring_pattern: Optional[str]
    project_id: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str


@dataclass
class SwapRequest:
    """Represents a shift swap request"""
    id: int
    requestor_agent_id: str
    requestor_shift_id: int
    target_agent_id: str
    target_shift_id: int
    status: str
    reason: Optional[str]
    response_notes: Optional[str]
    requested_at: str
    responded_at: Optional[str]
    completed_at: Optional[str]
    expires_at: Optional[str]
    notified: bool


@dataclass
class SwapRequestDetails:
    """Extended swap request with agent and shift details"""
    # Request info
    request_id: int
    status: str
    reason: Optional[str]
    response_notes: Optional[str]
    requested_at: str
    responded_at: Optional[str]
    expires_at: Optional[str]
    
    # Requestor info
    requestor_agent_id: str
    requestor_name: str
    requestor_role: str
    
    # Target info
    target_agent_id: str
    target_name: str
    target_role: str
    
    # Shift info
    requestor_shift_id: int
    requestor_shift_date: str
    requestor_start_time: str
    requestor_end_time: str
    target_shift_id: int
    target_shift_date: str
    target_start_time: str
    target_end_time: str


class ShiftSwapSystem:
    """
    Shift Swap Request System with approval workflow
    
    Features:
    - Create swap requests between agents
    - Approval workflow with timeout
    - Automatic notifications
    - Validation rules for swap eligibility
    - History tracking
    """
    
    DEFAULT_EXPIRY_HOURS = 48  # Requests expire after 48 hours
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize database tables for shift swap system"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Shifts table - stores agent shift assignments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                shift_date DATE NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                shift_type TEXT DEFAULT 'regular' 
                    CHECK (shift_type IN ('regular', 'on_call', 'holiday', 'overtime', 'maintenance')),
                is_recurring BOOLEAN DEFAULT FALSE,
                recurring_pattern TEXT,
                project_id TEXT,
                notes TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
            )
        ''')
        
        # Swap requests table - stores swap request workflow
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS swap_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requestor_agent_id TEXT NOT NULL,
                requestor_shift_id INTEGER NOT NULL,
                target_agent_id TEXT NOT NULL,
                target_shift_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled', 'expired', 'completed')),
                reason TEXT,
                response_notes TEXT,
                requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                responded_at DATETIME,
                completed_at DATETIME,
                expires_at DATETIME,
                notified BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (requestor_agent_id) REFERENCES agents(id) ON DELETE CASCADE,
                FOREIGN KEY (target_agent_id) REFERENCES agents(id) ON DELETE CASCADE,
                FOREIGN KEY (requestor_shift_id) REFERENCES shifts(id) ON DELETE CASCADE,
                FOREIGN KEY (target_shift_id) REFERENCES shifts(id) ON DELETE CASCADE,
                CONSTRAINT no_self_swap CHECK (requestor_agent_id != target_agent_id)
            )
        ''')
        
        # Swap request history for audit trail
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS swap_request_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                swap_request_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                actor_agent_id TEXT,
                notes TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (swap_request_id) REFERENCES swap_requests(id) ON DELETE CASCADE,
                FOREIGN KEY (actor_agent_id) REFERENCES agents(id) ON DELETE SET NULL
            )
        ''')
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shifts_agent ON shifts(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shifts_date ON shifts(shift_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shifts_active ON shifts(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_swap_req_requestor ON swap_requests(requestor_agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_swap_req_target ON swap_requests(target_agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_swap_req_status ON swap_requests(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_swap_req_expires ON swap_requests(expires_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_swap_hist_request ON swap_request_history(swap_request_id)')
        
        conn.commit()
        conn.close()
        
        # Create views
        self._create_views()
    
    def _create_views(self):
        """Create database views for swap request summaries"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # View: Swap request details with agent names
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS v_swap_request_details AS
            SELECT 
                sr.id as request_id,
                sr.status,
                sr.reason,
                sr.response_notes,
                sr.requested_at,
                sr.responded_at,
                sr.expires_at,
                sr.requestor_agent_id,
                ra.name as requestor_name,
                ra.role as requestor_role,
                sr.target_agent_id,
                ta.name as target_name,
                ta.role as target_role,
                sr.requestor_shift_id,
                s1.shift_date as requestor_shift_date,
                s1.start_time as requestor_start_time,
                s1.end_time as requestor_end_time,
                sr.target_shift_id,
                s2.shift_date as target_shift_date,
                s2.start_time as target_start_time,
                s2.end_time as target_end_time,
                CASE 
                    WHEN sr.expires_at < datetime('now') AND sr.status = 'pending' THEN 'expired'
                    WHEN sr.status = 'pending' AND sr.expires_at <= datetime('now', '+6 hours') THEN 'expiring_soon'
                    ELSE sr.status
                END as effective_status
            FROM swap_requests sr
            JOIN agents ra ON sr.requestor_agent_id = ra.id
            JOIN agents ta ON sr.target_agent_id = ta.id
            JOIN shifts s1 ON sr.requestor_shift_id = s1.id
            JOIN shifts s2 ON sr.target_shift_id = s2.id
        ''')
        
        # View: Agent shift summary
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS v_agent_shift_summary AS
            SELECT 
                a.id as agent_id,
                a.name as agent_name,
                a.role as agent_role,
                a.status as agent_status,
                COUNT(DISTINCT s.id) as total_shifts,
                COUNT(DISTINCT CASE WHEN s.shift_date >= date('now') THEN s.id END) as upcoming_shifts,
                COUNT(DISTINCT CASE 
                    WHEN sr.status = 'pending' AND sr.requestor_agent_id = a.id THEN sr.id 
                END) as outgoing_swap_requests,
                COUNT(DISTINCT CASE 
                    WHEN sr.status = 'pending' AND sr.target_agent_id = a.id THEN sr.id 
                END) as incoming_swap_requests
            FROM agents a
            LEFT JOIN shifts s ON a.id = s.agent_id AND s.is_active = TRUE
            LEFT JOIN swap_requests sr ON (a.id = sr.requestor_agent_id OR a.id = sr.target_agent_id)
            GROUP BY a.id
        ''')
        
        conn.commit()
        conn.close()
    
    # ==================== VALIDATION RULES ====================
    
    def _validate_swap_eligibility(self, requestor_agent_id: str, requestor_shift_id: int,
                                   target_agent_id: str, target_shift_id: int) -> Tuple[bool, str]:
        """
        Validate if a swap request is eligible
        
        Validation Rules:
        1. Agents cannot swap with themselves
        2. Both agents must exist and be active
        3. Both shifts must exist and be active
        4. Requestor must own the shift being offered
        5. Target agent must own the target shift
        6. Shifts must not be in the past
        7. No conflicting pending requests for the same shifts
        8. Target shift must not overlap with requestor's other shifts
        9. Requestor shift must not overlap with target's other shifts
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Rule 1: Self-swap check (enforced by DB constraint, but double-check)
        if requestor_agent_id == target_agent_id:
            return False, "Cannot swap shift with yourself"
        
        # Rule 2: Check agents exist and are active
        cursor.execute('''
            SELECT id, status FROM agents WHERE id IN (?, ?)
        ''', (requestor_agent_id, target_agent_id))
        agents = {row['id']: row['status'] for row in cursor.fetchall()}
        
        if requestor_agent_id not in agents:
            return False, f"Requestor agent '{requestor_agent_id}' not found"
        if target_agent_id not in agents:
            return False, f"Target agent '{target_agent_id}' not found"
        if agents[requestor_agent_id] == 'offline':
            return False, f"Requestor agent '{requestor_agent_id}' is offline"
        
        # Rule 3: Check shifts exist and are active
        cursor.execute('''
            SELECT id, agent_id, shift_date, start_time, end_time, is_active
            FROM shifts WHERE id IN (?, ?)
        ''', (requestor_shift_id, target_shift_id))
        shifts = {row['id']: dict(row) for row in cursor.fetchall()}
        
        if requestor_shift_id not in shifts:
            return False, f"Requestor shift {requestor_shift_id} not found"
        if target_shift_id not in shifts:
            return False, f"Target shift {target_shift_id} not found"
        if not shifts[requestor_shift_id]['is_active']:
            return False, f"Requestor shift {requestor_shift_id} is not active"
        if not shifts[target_shift_id]['is_active']:
            return False, f"Target shift {target_shift_id} is not active"
        
        # Rule 4: Requestor must own their shift
        if shifts[requestor_shift_id]['agent_id'] != requestor_agent_id:
            return False, "Requestor does not own the offered shift"
        
        # Rule 5: Target must own their shift
        if shifts[target_shift_id]['agent_id'] != target_agent_id:
            return False, "Target agent does not own the target shift"
        
        # Rule 6: Shifts must not be in the past
        requestor_shift_date = shifts[requestor_shift_id]['shift_date']
        target_shift_date = shifts[target_shift_id]['shift_date']
        today = datetime.now().strftime('%Y-%m-%d')
        
        if requestor_shift_date < today:
            return False, "Cannot swap past shifts"
        if target_shift_date < today:
            return False, "Cannot swap with a past shift"
        
        # Rule 7: Check for conflicting pending requests
        cursor.execute('''
            SELECT id FROM swap_requests 
            WHERE status = 'pending'
            AND (requestor_shift_id = ? OR target_shift_id = ?
                 OR requestor_shift_id = ? OR target_shift_id = ?)
        ''', (requestor_shift_id, requestor_shift_id, target_shift_id, target_shift_id))
        if cursor.fetchone():
            return False, "One of these shifts already has a pending swap request"
        
        # Rule 8: Check for shift conflicts after swap
        # Target's shift time should not conflict with requestor's other shifts
        target_start = f"{target_shift_date} {shifts[target_shift_id]['start_time']}"
        target_end = f"{target_shift_date} {shifts[target_shift_id]['end_time']}"
        
        cursor.execute('''
            SELECT id FROM shifts 
            WHERE agent_id = ? AND is_active = TRUE AND id != ?
            AND shift_date = ?
            AND (
                (start_time <= ? AND end_time > ?) OR  -- Overlaps with start
                (start_time < ? AND end_time >= ?) OR  -- Overlaps with end
                (start_time >= ? AND end_time <= ?)    -- Completely inside
            )
        ''', (requestor_agent_id, requestor_shift_id, target_shift_date,
              shifts[target_shift_id]['start_time'], shifts[target_shift_id]['start_time'],
              shifts[target_shift_id]['end_time'], shifts[target_shift_id]['end_time'],
              shifts[target_shift_id]['start_time'], shifts[target_shift_id]['end_time']))
        if cursor.fetchone():
            return False, "Target shift conflicts with requestor's other shifts"
        
        # Rule 9: Requestor's shift should not conflict with target's other shifts
        cursor.execute('''
            SELECT id FROM shifts 
            WHERE agent_id = ? AND is_active = TRUE AND id != ?
            AND shift_date = ?
            AND (
                (start_time <= ? AND end_time > ?) OR
                (start_time < ? AND end_time >= ?) OR
                (start_time >= ? AND end_time <= ?)
            )
        ''', (target_agent_id, target_shift_id, requestor_shift_date,
              shifts[requestor_shift_id]['start_time'], shifts[requestor_shift_id]['start_time'],
              shifts[requestor_shift_id]['end_time'], shifts[requestor_shift_id]['end_time'],
              shifts[requestor_shift_id]['start_time'], shifts[requestor_shift_id]['end_time']))
        if cursor.fetchone():
            return False, "Requestor shift conflicts with target's other shifts"
        
        conn.close()
        return True, "Validation passed"
    
    # ==================== CORE API ====================
    
    def create_shift(self, agent_id: str, shift_date: str, start_time: str, end_time: str,
                     shift_type: str = "regular", project_id: str = None,
                     is_recurring: bool = False, recurring_pattern: str = None,
                     notes: str = None) -> int:
        """
        Create a new shift assignment for an agent
        
        Args:
            agent_id: Agent ID
            shift_date: Date in YYYY-MM-DD format
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            shift_type: Type of shift (regular, on_call, holiday, overtime, maintenance)
            project_id: Optional project assignment
            is_recurring: Whether this is a recurring shift
            recurring_pattern: Pattern for recurring shifts (e.g., 'weekly', 'monthly')
            notes: Additional notes
            
        Returns:
            int: The created shift ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO shifts (agent_id, shift_date, start_time, end_time, shift_type,
                               project_id, is_recurring, recurring_pattern, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (agent_id, shift_date, start_time, end_time, shift_type,
              project_id, is_recurring, recurring_pattern, notes))
        
        shift_id = cursor.lastrowid
        
        # Log shift creation in swap_request_history for audit trail
        cursor.execute('''
            INSERT INTO swap_request_history (swap_request_id, action, notes)
            VALUES (0, 'shift_created', ?)
        ''', (f"Shift {shift_id} created for {agent_id} on {shift_date}",))
        
        conn.commit()
        conn.close()
        
        return shift_id
    
    def create_swap_request(self, requestor_agent_id: str, requestor_shift_id: int,
                           target_agent_id: str, target_shift_id: int,
                           reason: str = None, expiry_hours: int = None) -> Tuple[int, str]:
        """
        Create a new shift swap request
        
        Args:
            requestor_agent_id: Agent requesting the swap
            requestor_shift_id: Shift being offered
            target_agent_id: Agent being asked to swap
            target_shift_id: Shift being requested
            reason: Optional reason for the swap
            expiry_hours: Hours until request expires (default: 48)
            
        Returns:
            Tuple[int, str]: (request_id, message)
        """
        # Validate eligibility
        is_valid, message = self._validate_swap_eligibility(
            requestor_agent_id, requestor_shift_id,
            target_agent_id, target_shift_id
        )
        
        if not is_valid:
            return -1, message
        
        # Calculate expiry time
        expiry = expiry_hours or self.DEFAULT_EXPIRY_HOURS
        expires_at = (datetime.now() + timedelta(hours=expiry)).strftime('%Y-%m-%d %H:%M:%S')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create swap request
        cursor.execute('''
            INSERT INTO swap_requests 
            (requestor_agent_id, requestor_shift_id, target_agent_id, target_shift_id,
             reason, expires_at, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (requestor_agent_id, requestor_shift_id, target_agent_id, target_shift_id,
              reason, expires_at))
        
        request_id = cursor.lastrowid
        
        # Log history
        cursor.execute('''
            INSERT INTO swap_request_history 
            (swap_request_id, action, new_status, actor_agent_id, notes)
            VALUES (?, 'created', 'pending', ?, ?)
        ''', (request_id, requestor_agent_id, reason or "Swap request created"))
        
        conn.commit()
        conn.close()
        
        # Send notification to target agent
        self._notify_swap_request_created(request_id)
        
        return request_id, f"Swap request #{request_id} created successfully. Expires at {expires_at}"
    
    def approve_swap_request(self, request_id: int, approver_agent_id: str,
                             response_notes: str = None) -> Tuple[bool, str]:
        """
        Approve a pending swap request
        
        Args:
            request_id: The swap request ID
            approver_agent_id: Agent approving (must be target agent)
            response_notes: Optional notes with approval
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get request details
        cursor.execute('''
            SELECT * FROM swap_requests WHERE id = ?
        ''', (request_id,))
        request = cursor.fetchone()
        
        if not request:
            conn.close()
            return False, f"Swap request #{request_id} not found"
        
        # Check if already processed
        if request['status'] != 'pending':
            conn.close()
            return False, f"Swap request is already {request['status']}"
        
        # Check if approver is the target agent
        if request['target_agent_id'] != approver_agent_id:
            conn.close()
            return False, "Only the target agent can approve this request"
        
        # Check if expired
        if request['expires_at'] and request['expires_at'] < datetime.now().strftime('%Y-%m-%d %H:%M:%S'):
            cursor.execute('''
                UPDATE swap_requests SET status = 'expired' WHERE id = ?
            ''', (request_id,))
            conn.commit()
            conn.close()
            return False, "Swap request has expired"
        
        # Perform the swap - exchange agent assignments
        cursor.execute('''
            UPDATE shifts SET agent_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (request['target_agent_id'], request['requestor_shift_id']))
        
        cursor.execute('''
            UPDATE shifts SET agent_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (request['requestor_agent_id'], request['target_shift_id']))
        
        # Update request status
        cursor.execute('''
            UPDATE swap_requests 
            SET status = 'approved',
                responded_at = CURRENT_TIMESTAMP,
                completed_at = CURRENT_TIMESTAMP,
                response_notes = ?
            WHERE id = ?
        ''', (response_notes, request_id))
        
        # Log history
        cursor.execute('''
            INSERT INTO swap_request_history 
            (swap_request_id, action, old_status, new_status, actor_agent_id, notes)
            VALUES (?, 'approved', 'pending', 'approved', ?, ?)
        ''', (request_id, approver_agent_id, response_notes or "Approved"))
        
        conn.commit()
        conn.close()
        
        # Send notifications
        self._notify_swap_approved(request_id)
        
        return True, f"Swap request #{request_id} approved. Shifts have been exchanged."
    
    def reject_swap_request(self, request_id: int, rejector_agent_id: str,
                            response_notes: str = None) -> Tuple[bool, str]:
        """
        Reject a pending swap request
        
        Args:
            request_id: The swap request ID
            rejector_agent_id: Agent rejecting (must be target agent or requestor)
            response_notes: Optional reason for rejection
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get request details
        cursor.execute('''
            SELECT * FROM swap_requests WHERE id = ?
        ''', (request_id,))
        request = cursor.fetchone()
        
        if not request:
            conn.close()
            return False, f"Swap request #{request_id} not found"
        
        if request['status'] != 'pending':
            conn.close()
            return False, f"Swap request is already {request['status']}"
        
        # Only target agent or requestor can reject
        if rejector_agent_id not in [request['target_agent_id'], request['requestor_agent_id']]:
            conn.close()
            return False, "Only involved agents can reject this request"
        
        # Update request status
        cursor.execute('''
            UPDATE swap_requests 
            SET status = 'rejected',
                responded_at = CURRENT_TIMESTAMP,
                response_notes = ?
            WHERE id = ?
        ''', (response_notes, request_id))
        
        # Log history
        actor_role = "target" if rejector_agent_id == request['target_agent_id'] else "requestor"
        cursor.execute('''
            INSERT INTO swap_request_history 
            (swap_request_id, action, old_status, new_status, actor_agent_id, notes)
            VALUES (?, 'rejected', 'pending', 'rejected', ?, ?)
        ''', (request_id, rejector_agent_id, response_notes or f"Rejected by {actor_role}"))
        
        conn.commit()
        conn.close()
        
        # Send notification
        self._notify_swap_rejected(request_id)
        
        return True, f"Swap request #{request_id} rejected"
    
    def cancel_swap_request(self, request_id: int, requestor_agent_id: str) -> Tuple[bool, str]:
        """
        Cancel a pending swap request (only by requestor)
        
        Args:
            request_id: The swap request ID
            requestor_agent_id: Must match the original requestor
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get request details
        cursor.execute('''
            SELECT * FROM swap_requests WHERE id = ?
        ''', (request_id,))
        request = cursor.fetchone()
        
        if not request:
            conn.close()
            return False, f"Swap request #{request_id} not found"
        
        if request['status'] != 'pending':
            conn.close()
            return False, f"Cannot cancel - request is already {request['status']}"
        
        if request['requestor_agent_id'] != requestor_agent_id:
            conn.close()
            return False, "Only the requestor can cancel this request"
        
        # Update request status
        cursor.execute('''
            UPDATE swap_requests 
            SET status = 'cancelled',
                responded_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (request_id,))
        
        # Log history
        cursor.execute('''
            INSERT INTO swap_request_history 
            (swap_request_id, action, old_status, new_status, actor_agent_id, notes)
            VALUES (?, 'cancelled', 'pending', 'cancelled', ?, 'Cancelled by requestor')
        ''', (request_id, requestor_agent_id))
        
        conn.commit()
        conn.close()
        
        # Send notification
        self._notify_swap_cancelled(request_id)
        
        return True, f"Swap request #{request_id} cancelled"
    
    def get_swap_request(self, request_id: int) -> Optional[SwapRequestDetails]:
        """Get detailed information about a swap request"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM v_swap_request_details WHERE request_id = ?
        ''', (request_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return SwapRequestDetails(
            request_id=row['request_id'],
            status=row['status'],
            reason=row['reason'],
            response_notes=row['response_notes'],
            requested_at=row['requested_at'],
            responded_at=row['responded_at'],
            expires_at=row['expires_at'],
            requestor_agent_id=row['requestor_agent_id'],
            requestor_name=row['requestor_name'],
            requestor_role=row['requestor_role'],
            target_agent_id=row['target_agent_id'],
            target_name=row['target_name'],
            target_role=row['target_role'],
            requestor_shift_id=row['requestor_shift_id'],
            requestor_shift_date=row['requestor_shift_date'],
            requestor_start_time=row['requestor_start_time'],
            requestor_end_time=row['requestor_end_time'],
            target_shift_id=row['target_shift_id'],
            target_shift_date=row['target_shift_date'],
            target_start_time=row['target_start_time'],
            target_end_time=row['target_end_time']
        )
    
    def get_swap_requests(self, agent_id: str = None, status: str = None,
                         direction: str = None) -> List[SwapRequestDetails]:
        """
        Get swap requests with optional filters
        
        Args:
            agent_id: Filter by agent (as requestor or target)
            status: Filter by status (pending, approved, rejected, etc.)
            direction: 'outgoing', 'incoming', or None for both
            
        Returns:
            List[SwapRequestDetails]: List of matching swap requests
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM v_swap_request_details WHERE 1=1'
        params = []
        
        if agent_id:
            if direction == 'outgoing':
                query += ' AND requestor_agent_id = ?'
                params.append(agent_id)
            elif direction == 'incoming':
                query += ' AND target_agent_id = ?'
                params.append(agent_id)
            else:
                query += ' AND (requestor_agent_id = ? OR target_agent_id = ?)'
                params.extend([agent_id, agent_id])
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        query += ' ORDER BY requested_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [SwapRequestDetails(
            request_id=row['request_id'],
            status=row['status'],
            reason=row['reason'],
            response_notes=row['response_notes'],
            requested_at=row['requested_at'],
            responded_at=row['responded_at'],
            expires_at=row['expires_at'],
            requestor_agent_id=row['requestor_agent_id'],
            requestor_name=row['requestor_name'],
            requestor_role=row['requestor_role'],
            target_agent_id=row['target_agent_id'],
            target_name=row['target_name'],
            target_role=row['target_role'],
            requestor_shift_id=row['requestor_shift_id'],
            requestor_shift_date=row['requestor_shift_date'],
            requestor_start_time=row['requestor_start_time'],
            requestor_end_time=row['requestor_end_time'],
            target_shift_id=row['target_shift_id'],
            target_shift_date=row['target_shift_date'],
            target_start_time=row['target_start_time'],
            target_end_time=row['target_end_time']
        ) for row in rows]
    
    def get_agent_shifts(self, agent_id: str, from_date: str = None,
                         to_date: str = None) -> List[Dict]:
        """
        Get shifts for an agent
        
        Args:
            agent_id: The agent ID
            from_date: Start date filter (YYYY-MM-DD)
            to_date: End date filter (YYYY-MM-DD)
            
        Returns:
            List[Dict]: List of shift records
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT s.*, p.name as project_name
            FROM shifts s
            LEFT JOIN projects p ON s.project_id = p.id
            WHERE s.agent_id = ? AND s.is_active = TRUE
        '''
        params = [agent_id]
        
        if from_date:
            query += ' AND s.shift_date >= ?'
            params.append(from_date)
        if to_date:
            query += ' AND s.shift_date <= ?'
            params.append(to_date)
        
        query += ' ORDER BY s.shift_date, s.start_time'
        
        cursor.execute(query, params)
        shifts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return shifts
    
    def expire_old_requests(self) -> int:
        """
        Mark expired pending requests as expired
        
        Returns:
            int: Number of requests expired
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE swap_requests 
            SET status = 'expired'
            WHERE status = 'pending'
            AND expires_at < datetime('now')
        ''')
        
        expired_count = cursor.rowcount
        
        if expired_count > 0:
            # Log the expirations
            cursor.execute('''
                INSERT INTO swap_request_history (swap_request_id, action, old_status, new_status, notes)
                SELECT id, 'expired', 'pending', 'expired', 'Auto-expired by system'
                FROM swap_requests
                WHERE status = 'expired'
                AND expires_at < datetime('now')
            ''')
        
        conn.commit()
        conn.close()
        
        return expired_count
    
    # ==================== NOTIFICATION INTEGRATION ====================
    
    def _send_telegram_notification(self, message: str) -> bool:
        """Send notification via Telegram"""
        try:
            result = subprocess.run(
                ["openclaw", "message", "send", "--channel", "telegram",
                 "--target", TELEGRAM_CHANNEL, "--message", message],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[Notification Error] {e}")
            return False
    
    def _notify_swap_request_created(self, request_id: int):
        """Notify target agent of new swap request"""
        details = self.get_swap_request(request_id)
        if not details:
            return
        
        message = f"""🔄 **New Shift Swap Request**

From: {details.requestor_name} ({details.requestor_role})
To: {details.target_name} ({details.target_role})

**Your Shift:**
📅 {details.target_shift_date} | ⏰ {details.target_start_time} - {details.target_end_time}

**Offered Shift:**
📅 {details.requestor_shift_date} | ⏰ {details.requestor_start_time} - {details.requestor_end_time}

**Reason:** {details.reason or 'No reason provided'}
**Expires:** {details.expires_at}

Request ID: #{request_id}
"""
        self._send_telegram_notification(message)
    
    def _notify_swap_approved(self, request_id: int):
        """Notify both agents of approved swap"""
        details = self.get_swap_request(request_id)
        if not details:
            return
        
        message = f"""✅ **Shift Swap Approved**

Request #{request_id} has been approved!

{details.requestor_name} ↔️ {details.target_name}

**Shift Exchange:**
- {details.requestor_name} now has: {details.target_shift_date} {details.target_start_time}-{details.target_end_time}
- {details.target_name} now has: {details.requestor_shift_date} {details.requestor_start_time}-{details.requestor_end_time}

**Notes:** {details.response_notes or 'None'}
"""
        self._send_telegram_notification(message)
    
    def _notify_swap_rejected(self, request_id: int):
        """Notify requestor of rejected swap"""
        details = self.get_swap_request(request_id)
        if not details:
            return
        
        message = f"""❌ **Shift Swap Rejected**

Request #{request_id} was rejected.

From: {details.requestor_name}
To: {details.target_name}

**Reason:** {details.response_notes or 'No reason provided'}
"""
        self._send_telegram_notification(message)
    
    def _notify_swap_cancelled(self, request_id: int):
        """Notify target of cancelled swap request"""
        details = self.get_swap_request(request_id)
        if not details:
            return
        
        message = f"""🚫 **Shift Swap Cancelled**

Request #{request_id} was cancelled by {details.requestor_name}.

No action required.
"""
        self._send_telegram_notification(message)
    
    # ==================== REPORTING & STATS ====================
    
    def get_swap_statistics(self, agent_id: str = None) -> Dict:
        """
        Get swap request statistics
        
        Args:
            agent_id: Optional agent ID to filter stats
            
        Returns:
            Dict: Statistics about swap requests
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired
            FROM swap_requests
        '''
        params = []
        
        if agent_id:
            query += ' WHERE requestor_agent_id = ? OR target_agent_id = ?'
            params = [agent_id, agent_id]
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        total = row['total'] or 0
        approved = row['approved'] or 0
        
        stats = {
            'total_requests': total,
            'pending': row['pending'] or 0,
            'approved': approved,
            'rejected': row['rejected'] or 0,
            'cancelled': row['cancelled'] or 0,
            'expired': row['expired'] or 0,
            'approval_rate': round((approved / total * 100), 1) if total > 0 else 0
        }
        
        conn.close()
        return stats


# ==================== CLI INTERFACE ====================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Shift Swap Request System')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create shift command
    shift_create = subparsers.add_parser('shift-create', help='Create a shift')
    shift_create.add_argument('agent_id', help='Agent ID')
    shift_create.add_argument('date', help='Shift date (YYYY-MM-DD)')
    shift_create.add_argument('start_time', help='Start time (HH:MM)')
    shift_create.add_argument('end_time', help='End time (HH:MM)')
    shift_create.add_argument('--type', default='regular', choices=['regular', 'on_call', 'holiday', 'overtime', 'maintenance'])
    shift_create.add_argument('--project', help='Project ID')
    shift_create.add_argument('--notes', help='Additional notes')
    
    # Create swap request command
    swap_req = subparsers.add_parser('request', help='Create swap request')
    swap_req.add_argument('requestor', help='Requestor agent ID')
    swap_req.add_argument('requestor_shift', type=int, help='Requestor shift ID')
    swap_req.add_argument('target', help='Target agent ID')
    swap_req.add_argument('target_shift', type=int, help='Target shift ID')
    swap_req.add_argument('--reason', help='Reason for swap')
    swap_req.add_argument('--expiry', type=int, default=48, help='Expiry hours (default: 48)')
    
    # Approve command
    approve = subparsers.add_parser('approve', help='Approve swap request')
    approve.add_argument('request_id', type=int, help='Request ID')
    approve.add_argument('approver', help='Approver agent ID')
    approve.add_argument('--notes', help='Response notes')
    
    # Reject command
    reject = subparsers.add_parser('reject', help='Reject swap request')
    reject.add_argument('request_id', type=int, help='Request ID')
    reject.add_argument('rejector', help='Rejector agent ID')
    reject.add_argument('--notes', help='Response notes')
    
    # Cancel command
    cancel = subparsers.add_parser('cancel', help='Cancel swap request')
    cancel.add_argument('request_id', type=int, help='Request ID')
    cancel.add_argument('requestor', help='Requestor agent ID')
    
    # List command
    list_cmd = subparsers.add_parser('list', help='List swap requests')
    list_cmd.add_argument('--agent', help='Filter by agent ID')
    list_cmd.add_argument('--status', choices=['pending', 'approved', 'rejected', 'cancelled', 'expired'])
    list_cmd.add_argument('--direction', choices=['outgoing', 'incoming'])
    
    # View command
    view = subparsers.add_parser('view', help='View swap request details')
    view.add_argument('request_id', type=int, help='Request ID')
    
    # Stats command
    stats = subparsers.add_parser('stats', help='Show swap statistics')
    stats.add_argument('--agent', help='Filter by agent ID')
    
    # Shifts command
    shifts = subparsers.add_parser('shifts', help='List agent shifts')
    shifts.add_argument('agent_id', help='Agent ID')
    shifts.add_argument('--from', dest='from_date', help='From date (YYYY-MM-DD)')
    shifts.add_argument('--to', help='To date (YYYY-MM-DD)')
    
    # Expire command
    expire = subparsers.add_parser('expire', help='Expire old pending requests')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    system = ShiftSwapSystem()
    
    if args.command == 'shift-create':
        shift_id = system.create_shift(
            args.agent_id, args.date, args.start_time, args.end_time,
            args.type, args.project, notes=args.notes
        )
        print(f"✅ Shift created with ID: {shift_id}")
    
    elif args.command == 'request':
        req_id, msg = system.create_swap_request(
            args.requestor, args.requestor_shift,
            args.target, args.target_shift,
            args.reason, args.expiry
        )
        if req_id > 0:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
    
    elif args.command == 'approve':
        success, msg = system.approve_swap_request(args.request_id, args.approver, args.notes)
        print(f"{'✅' if success else '❌'} {msg}")
    
    elif args.command == 'reject':
        success, msg = system.reject_swap_request(args.request_id, args.rejector, args.notes)
        print(f"{'✅' if success else '❌'} {msg}")
    
    elif args.command == 'cancel':
        success, msg = system.cancel_swap_request(args.request_id, args.requestor)
        print(f"{'✅' if success else '❌'} {msg}")
    
    elif args.command == 'list':
        requests = system.get_swap_requests(args.agent, args.status, args.direction)
        if not requests:
            print("No swap requests found.")
            return
        
        print(f"\n{'ID':<6} {'Status':<10} {'Requestor':<15} {'Target':<15} {'Date':<20}")
        print("-" * 70)
        for req in requests:
            print(f"{req.request_id:<6} {req.status:<10} {req.requestor_name:<15} {req.target_name:<15} {req.requested_at[:16]}")
    
    elif args.command == 'view':
        req = system.get_swap_request(args.request_id)
        if not req:
            print(f"Request #{args.request_id} not found.")
            return
        
        print(f"\n🔄 Swap Request #{req.request_id}")
        print(f"Status: {req.status}")
        print(f"\nRequestor: {req.requestor_name} ({req.requestor_role})")
        print(f"Shift: {req.requestor_shift_date} {req.requestor_start_time}-{req.requestor_end_time}")
        print(f"\nTarget: {req.target_name} ({req.target_role})")
        print(f"Shift: {req.target_shift_date} {req.target_start_time}-{req.target_end_time}")
        print(f"\nReason: {req.reason or 'N/A'}")
        print(f"Response: {req.response_notes or 'N/A'}")
        print(f"\nRequested: {req.requested_at}")
        print(f"Expires: {req.expires_at or 'N/A'}")
        if req.responded_at:
            print(f"Responded: {req.responded_at}")
    
    elif args.command == 'stats':
        stats = system.get_swap_statistics(args.agent)
        print("\n📊 Swap Request Statistics")
        print("-" * 30)
        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
    
    elif args.command == 'shifts':
        shifts = system.get_agent_shifts(args.agent_id, args.from_date, args.to)
        if not shifts:
            print(f"No shifts found for {args.agent_id}")
            return
        
        print(f"\n🗓️  Shifts for {args.agent_id}")
        print(f"{'ID':<6} {'Date':<12} {'Time':<15} {'Type':<12} {'Project':<20}")
        print("-" * 70)
        for shift in shifts:
            time_str = f"{shift['start_time']} - {shift['end_time']}"
            project_name = shift.get('project_name') or 'N/A'
            print(f"{shift['id']:<6} {shift['shift_date']:<12} {time_str:<15} {shift['shift_type']:<12} {project_name:<20}")
    
    elif args.command == 'expire':
        count = system.expire_old_requests()
        print(f"✅ Expired {count} old pending requests")


if __name__ == '__main__':
    main()
