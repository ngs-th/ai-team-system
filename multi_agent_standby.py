#!/usr/bin/env python3
"""
AI Team - Multi-Agent Stand By System
Spawn all agents with keep-alive mode for continuous communication
"""

import subprocess
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "team.db"
TELEGRAM_CHANNEL = "1268858185"

AGENTS = {
    'pm': {
        'name': 'John',
        'role': 'Product Manager',
        'icon': '📋',
        'model': 'anthropic/claude-opus-4-5',
        'file': 'agents/pm.md'
    },
    'analyst': {
        'name': 'Mary',
        'role': 'Business Analyst',
        'icon': '📊',
        'model': 'anthropic/claude-sonnet-4-5',
        'file': 'agents/analyst.md'
    },
    'architect': {
        'name': 'Winston',
        'role': 'System Architect',
        'icon': '🏗️',
        'model': 'anthropic/claude-opus-4-5',
        'file': 'agents/architect.md'
    },
    'dev': {
        'name': 'Amelia',
        'role': 'Developer',
        'icon': '💻',
        'model': 'kimi-code/kimi-for-coding',
        'file': 'agents/dev.md'
    },
    'ux-designer': {
        'name': 'Sally',
        'role': 'UX Designer',
        'icon': '🎨',
        'model': 'anthropic/claude-sonnet-4-5',
        'file': 'agents/ux-designer.md'
    },
    'scrum-master': {
        'name': 'Bob',
        'role': 'Scrum Master',
        'icon': '🏃',
        'model': 'anthropic/claude-sonnet-4-5',
        'file': 'agents/scrum-master.md'
    },
    'qa': {
        'name': 'Quinn',
        'role': 'QA Engineer',
        'icon': '🧪',
        'model': 'anthropic/claude-sonnet-4-5',
        'file': 'agents/qa-engineer.md'
    },
    'tech-writer': {
        'name': 'Tom',
        'role': 'Technical Writer',
        'icon': '📝',
        'model': 'anthropic/claude-sonnet-4-5',
        'file': 'agents/tech-writer.md'
    },
    'solo-dev': {
        'name': 'Barry',
        'role': 'Solo Developer',
        'icon': '🚀',
        'model': 'kimi-code/kimi-for-coding',
        'file': 'agents/solo-dev.md'
    }
}

def read_agent_config(agent_type):
    """Read agent configuration from markdown file"""
    config_path = Path(__file__).parent / AGENTS[agent_type]['file']
    if config_path.exists():
        return config_path.read_text()
    return f"# {AGENTS[agent_type]['name']} - {AGENTS[agent_type]['role']}"

def build_standby_message(agent_type):
    """Build stand-by mode message for agent"""
    agent = AGENTS[agent_type]
    agent_config = read_agent_config(agent_type)
    
    return f"""{agent_config}

---

## 🤖 STAND BY MODE ACTIVATED

You are now in **STAND BY MODE**. This means:

### Your Status
- **Name:** {agent['name']} ({agent['icon']})
- **Role:** {agent['role']}
- **Mode:** Active & Listening
- **Session:** Keep-alive (will not auto-close)

### What You Can Do
1. **Wait for instructions** - I will send you tasks via this channel
2. **Communicate with other agents** - Use the database to coordinate
3. **Report progress** - Send updates back to me
4. **Ask questions** - If unclear, ask immediately

### Communication Rules
- When you receive a message, respond promptly
- Use your expertise to contribute
- Reference other agents when collaboration is needed
- Update task status in team.db after each action

### Current Task
**WAITING FOR ASSIGNMENT**

You are now on standby. I will send you a task shortly. When received:
1. Acknowledge receipt
2. Ask clarifying questions if needed
3. Execute using your expertise
4. Report progress regularly

### Tools Available
- `write` - Create files
- `read` - Read files
- `edit` - Modify files
- `exec` - Run commands
- `team_db.py` - Update task status
- `memory_search` - Recall previous work

**You are live and ready. Awaiting instructions...**
"""

def spawn_agent_standby(agent_type):
    """Spawn agent in stand-by mode with keep-alive using sessions_spawn"""
    if agent_type not in AGENTS:
        print(f"❌ Unknown agent type: {agent_type}")
        return None
    
    agent = AGENTS[agent_type]
    task_message = build_standby_message(agent_type)
    label = f"standby-{agent_type}-{int(time.time())}"
    
    print(f"🚀 Spawning {agent['icon']} {agent['name']} ({agent['role']})...")
    print(f"   Label: {label}")
    
    # Return the spawn configuration for the caller to use sessions_spawn
    return {
        'agent_type': agent_type,
        'name': agent['name'],
        'role': agent['role'],
        'icon': agent['icon'],
        'model': agent['model'],
        'label': label,
        'task': task_message,
        'status': 'ready_to_spawn'
    }

def spawn_all_agents():
    """Spawn all agents in stand-by mode"""
    print("=" * 70)
    print("🤖 AI TEAM - MULTI-AGENT STAND BY SYSTEM")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Agents: {len(AGENTS)}")
    print("=" * 70)
    print()
    
    results = []
    
    for agent_type in AGENTS:
        result = spawn_agent_standby(agent_type)
        if result:
            results.append(result)
        time.sleep(2)  # Small delay between spawns
    
    print()
    print("=" * 70)
    print("📊 SPAWN SUMMARY")
    print("=" * 70)
    print(f"Total Spawned: {len(results)}/{len(AGENTS)}")
    print()
    
    for r in results:
        icon = AGENTS[r['agent_type']]['icon']
        print(f"  {icon} {r['name']}: {r['status'].upper()}")
    
    print()
    print("✅ All agents are now in STAND BY MODE")
    print("   They are ready to receive instructions and collaborate!")
    print()
    
    return results

def test_agent_communication():
    """Test communication between agents"""
    print("=" * 70)
    print("🧪 TESTING AGENT COMMUNICATION")
    print("=" * 70)
    print()
    
    # Create a test task that requires collaboration
    test_scenario = """
## 🎭 COLLABORATION TEST SCENARIO

**Project:** Nurse AI System - New Feature

### The Challenge
Design and implement a "Shift Swap Marketplace" where nurses can:
1. Post shifts they want to swap
2. Browse available shifts from colleagues
3. Request swaps with automatic fairness scoring
4. Get head nurse approval

### Your Roles in This Test:

**PM (John):** Define requirements and success criteria
**Architect (Winston):** Design the technical solution
**UX Designer (Sally):** Create user flow and interface
**Dev (Amelia):** Implement the core functionality
**QA (Quinn):** Define test scenarios

### Instructions
1. Each agent responds with their perspective/approach
2. Reference other agents' suggestions
3. Build on each other's ideas
4. Ask clarifying questions

### Starting Question
"What are the key features and technical considerations for the Shift Swap Marketplace?"

---
**Begin your collaboration!**
"""
    
    print(test_scenario)
    print()
    print("📝 This scenario will test:")
    print("  ✓ Multi-agent communication")
    print("  ✓ Role-specific expertise")
    print("  ✓ Collaborative problem-solving")
    print("  ✓ Cross-referencing between agents")
    print()
    
    return test_scenario

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='AI Team Multi-Agent Stand By System')
    parser.add_argument('--spawn-all', action='store_true', help='Spawn all agents in stand-by mode')
    parser.add_argument('--spawn', help='Spawn specific agent (pm, analyst, architect, dev, etc.)')
    parser.add_argument('--test', action='store_true', help='Run collaboration test scenario')
    parser.add_argument('--list', action='store_true', help='List available agents')
    args = parser.parse_args()
    
    if args.list:
        print("Available Agents:")
        for agent_type, info in AGENTS.items():
            print(f"  {info['icon']} {agent_type:12} - {info['name']} ({info['role']})")
    elif args.spawn:
        spawn_agent_standby(args.spawn)
    elif args.spawn_all:
        results = spawn_all_agents()
        if results:
            print("\n💡 Next steps:")
            print("  1. Wait for agents to fully initialize")
            print("  2. Run: python3 multi_agent_standby.py --test")
            print("  3. Or send tasks via: openclaw sessions_send --sessionKey <key>")
    elif args.test:
        test_agent_communication()
    else:
        parser.print_help()
