#!/usr/bin/env python3
"""
Phase 5.1 LangGraph Integration Demonstration
Shows the complete functionality of Tinker's LangGraph integration
"""

import os
import tempfile
from src.tinker.checkpoint_manager import TinkerCheckpointManager
from src.tinker.langgraph_workflow import TinkerWorkflow

def demo_phase_5_1():
    """Comprehensive demonstration of Phase 5.1 features"""
    
    print("=" * 60)
    print("🚀 TINKER PHASE 5.1 - LANGGRAPH INTEGRATION DEMO")
    print("=" * 60)
    
    # Use a temporary database for the demo
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'demo.db')
        
        print(f"\n📁 Using database: {db_path}")
        
        # 1. Initialize LangGraph components
        print("\n1️⃣ INITIALIZING LANGGRAPH COMPONENTS")
        print("-" * 40)
        checkpoint_manager = TinkerCheckpointManager(db_path)
        workflow = TinkerWorkflow(checkpoint_manager)
        print("✅ Checkpoint manager and workflow initialized")
        
        # 2. Execute multiple tasks with different threads
        print("\n2️⃣ EXECUTING TASKS WITH PERSISTENCE")
        print("-" * 40)
        
        # Task 1: File operations
        print("🔹 Task 1: File operations")
        result1 = workflow.execute_task(
            "Create a hello.txt file and write 'Hello LangGraph!' to it",
            "demo-thread-1"
        )
        print(f"   Status: {result1['execution_status']}")
        print(f"   Thread: {result1['thread_id']}")
        print(f"   Conversation length: {len(result1['conversation_history'])}")
        
        # Task 2: System information (same thread)
        print("\n🔹 Task 2: System info (continuing thread 1)")
        result2 = workflow.execute_task(
            "Check system disk usage and memory",
            "demo-thread-1"  # Same thread - should build on conversation
        )
        print(f"   Status: {result2['execution_status']}")
        print(f"   Conversation length: {len(result2['conversation_history'])}")
        print(f"   Tool results: {len(result2['tool_results'])}")
        
        # Task 3: New thread
        print("\n🔹 Task 3: Network info (new thread)")
        result3 = workflow.execute_task(
            "Display network interface information",
            "demo-thread-2"  # New thread
        )
        print(f"   Status: {result3['execution_status']}")
        print(f"   Thread: {result3['thread_id']}")
        
        # 3. Demonstrate session management
        print("\n3️⃣ SESSION MANAGEMENT")
        print("-" * 40)
        sessions = workflow.list_sessions()
        print(f"📊 Total sessions: {len(sessions)}")
        for i, session in enumerate(sessions, 1):
            print(f"   {i}. Thread: {session['thread_id']}")
            print(f"      Task: {session['task_summary']}")
            print(f"      Created: {session['created_at']}")
            print(f"      Last accessed: {session['last_accessed']}")
        
        # 4. Demonstrate checkpoint listing
        print("\n4️⃣ CHECKPOINT MANAGEMENT")
        print("-" * 40)
        for session in sessions:
            thread_id = session['thread_id']
            checkpoints = workflow.get_checkpoints(thread_id)
            print(f"📍 Thread {thread_id}: {len(checkpoints)} checkpoints")
            for cp in checkpoints[:3]:  # Show first 3
                print(f"   - {cp['checkpoint_id'][:8]}... ({cp['execution_status']})")
        
        # 5. Show conversation history for first thread
        print("\n5️⃣ CONVERSATION HISTORY EXAMPLE")
        print("-" * 40)
        if result2['conversation_history']:
            print(f"📝 Thread {result2['thread_id']} conversation:")
            for i, msg in enumerate(result2['conversation_history'][:4], 1):
                msg_type = type(msg).__name__
                content = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
                print(f"   {i}. {msg_type}: {content}")
        
        # 6. Demonstrate persistence across manager instances
        print("\n6️⃣ PERSISTENCE VERIFICATION")
        print("-" * 40)
        print("🔄 Creating new manager instance with same database...")
        
        # Create new instances - should load existing data
        checkpoint_manager2 = TinkerCheckpointManager(db_path)
        workflow2 = TinkerWorkflow(checkpoint_manager2)
        
        sessions2 = workflow2.list_sessions()
        print(f"✅ Loaded {len(sessions2)} sessions from persistent storage")
        
        # Add one more task to existing thread
        result4 = workflow2.execute_task(
            "List running processes",
            "demo-thread-1"  # Continue existing thread
        )
        print(f"✅ Continued existing thread with {len(result4['conversation_history'])} messages")
        
        print("\n" + "=" * 60)
        print("🎉 PHASE 5.1 DEMONSTRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        print("\n📋 FEATURES DEMONSTRATED:")
        print("✅ LangGraph workflow execution")
        print("✅ SQLite-based persistence")
        print("✅ Session management across threads")
        print("✅ Checkpoint tracking and metadata")
        print("✅ Conversation history accumulation")
        print("✅ Tool result tracking")
        print("✅ Cross-instance persistence")
        print("✅ Thread continuation and resumption")
        
        print("\n🔧 TECHNICAL STACK:")
        print("• LangGraph StateGraph for workflow orchestration")
        print("• SQLite with SqliteSaver for checkpoint persistence")
        print("• Custom state management with TinkerState")
        print("• Node-based execution wrapping existing tools")
        print("• Thread-safe session and checkpoint tracking")

if __name__ == "__main__":
    demo_phase_5_1()
