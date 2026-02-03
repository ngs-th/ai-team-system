#!/usr/bin/env python3
"""
AI Team Agent Communication Hub
Enable real-time communication between standing-by agents
"""

import subprocess
import sqlite3
import time
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "team.db"
COMM_LOG = Path(__file__).parent / "logs" / "agent_communications.log"

class AgentCommunicationHub:
    """Central hub for agent-to-agent communication"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.comm_log = COMM_LOG
        self.comm_log.parent.mkdir(exist_ok=True)
        
    def get_active_sessions(self):
        """Get all active agent sessions"""
        try:
            result = subprocess.run(
                ['openclaw', 'sessions_list', '--active-minutes', '60', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            print(f"[Error] Could not get sessions: {e}")
        return []
    
    def log_communication(self, from_agent, to_agent, message, msg_type='chat'):
        """Log inter-agent communication"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'from': from_agent,
            'to': to_agent,
            'type': msg_type,
            'message': message[:500]  # Truncate long messages
        }
        
        with open(self.comm_log, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def broadcast_to_all(self, sender, message):
        """Broadcast message to all active agents"""
        sessions = self.get_active_sessions()
        sent_count = 0
        
        print(f"📢 Broadcasting from {sender} to {len(sessions)} agents...")
        
        for session in sessions:
            if 'standby' in session.get('label', ''):
                try:
                    result = subprocess.run(
                        ['openclaw', 'sessions_send',
                         '--sessionKey', session['sessionKey'],
                         '--message', f"[Broadcast from {sender}]\n\n{message}"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        sent_count += 1
                        self.log_communication(sender, session.get('label', 'unknown'), message, 'broadcast')
                except Exception as e:
                    print(f"  ⚠️  Failed to send to {session.get('label', 'unknown')}: {e}")
        
        print(f"  ✅ Sent to {sent_count}/{len(sessions)} agents")
        return sent_count
    
    def send_to_agent(self, sender, target_agent_type, message):
        """Send message to specific agent type"""
        sessions = self.get_active_sessions()
        
        for session in sessions:
            label = session.get('label', '')
            if f'standby-{target_agent_type}' in label:
                try:
                    result = subprocess.run(
                        ['openclaw', 'sessions_send',
                         '--sessionKey', session['sessionKey'],
                         '--message', f"[Message from {sender}]\n\n{message}"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        self.log_communication(sender, target_agent_type, message, 'direct')
                        print(f"✅ Message sent to {target_agent_type}")
                        return True
                except Exception as e:
                    print(f"❌ Failed to send: {e}")
        
        print(f"⚠️  Agent {target_agent_type} not found or not active")
        return False
    
    def facilitate_discussion(self, topic, participants):
        """Facilitate a multi-agent discussion on a topic"""
        print("=" * 70)
        print(f"🎭 FACILITATED DISCUSSION: {topic}")
        print("=" * 70)
        print()
        
        # Send opening message to all participants
        opening = f"""
## 🎭 Group Discussion Started

**Topic:** {topic}

**Participants:** {', '.join(participants)}

**Instructions:**
1. Share your perspective as your role
2. Respond to other agents' points
3. Build consensus collaboratively
4. The facilitator (me) will guide the flow

**Opening Question:**
What are your initial thoughts on this topic from your role's perspective?

Please respond with:
- Your role's key concerns/considerations
- Questions for other agents
- Suggestions based on your expertise

Let's begin!
"""
        
        for participant in participants:
            self.send_to_agent('Facilitator', participant, opening)
            time.sleep(1)  # Stagger sends
        
        print(f"✅ Discussion opened with {len(participants)} participants")
        print("   Waiting for responses...")
        
    def show_active_agents(self):
        """Display all active standby agents"""
        sessions = self.get_active_sessions()
        standby_agents = [s for s in sessions if 'standby' in s.get('label', '')]
        
        print("=" * 70)
        print("🤖 ACTIVE STAND BY AGENTS")
        print("=" * 70)
        
        if not standby_agents:
            print("\n  No active standby agents found.")
            print("  Run: python3 multi_agent_standby.py --spawn-all")
        else:
            print(f"\n  Total: {len(standby_agents)} agents\n")
            for agent in standby_agents:
                label = agent.get('label', 'unknown')
                session_key = agent.get('sessionKey', 'N/A')[:20] + '...'
                print(f"  • {label}")
                print(f"    Session: {session_key}")
        
        print()
        return standby_agents

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Agent Communication Hub')
    parser.add_argument('--status', action='store_true', help='Show active agents')
    parser.add_argument('--broadcast', help='Broadcast message to all agents')
    parser.add_argument('--send', help='Send to specific agent (format: agent_type:message)')
    parser.add_argument('--discuss', help='Start facilitated discussion')
    parser.add_argument('--participants', default='pm,architect,dev,qa', help='Comma-separated participant list')
    
    args = parser.parse_args()
    hub = AgentCommunicationHub()
    
    if args.status:
        hub.show_active_agents()
    elif args.broadcast:
        hub.broadcast_to_all('Operator', args.broadcast)
    elif args.send:
        if ':' not in args.send:
            print("Error: Use format 'agent_type:message'")
            return
        agent_type, message = args.send.split(':', 1)
        hub.send_to_agent('Operator', agent_type.strip(), message.strip())
    elif args.discuss:
        participants = [p.strip() for p in args.participants.split(',')]
        hub.facilitate_discussion(args.discuss, participants)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
