#!/usr/bin/env python3
"""Test script for Symphony multi-agent task execution.

This script tests the high-level API shown in the README.
"""

import sys
import os
sys.path.insert(0, '/workspace/code')

def test_basic_import():
    """Test basic imports work correctly."""
    print("[TEST] Testing basic imports...")
    
    try:
        # Test core imports
        from agents.agent import Agent
        from protocol.task_contract import Task
        from core.capability import CapabilityManager
        print("✅ Core module imports successful")
        
        # Test Task class new API
        task = Task(
            description="Test task",
            requirements=["testing", "validation"],
            context={"domain": "test", "complexity": "low"}
        )
        print(f"✅ Task creation successful: {task}")
        
        # Test Agent class new API
        agent = Agent(
            node_id="test_agent",
            capabilities=["testing", "debugging", "validation"]
        )
        print(f"✅ Agent creation successful: {agent.agent_id}")
        
        return True
    except Exception as e:
        print(f"❌ Basic import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_symphony_integration():
    """Test Symphony orchestrator integration."""
    print("\n[TEST] Testing Symphony integration...")
    
    try:
        from symphony import execute_task, register_agent, get_registered_agents
        from agents.agent import Agent
        from protocol.task_contract import Task
        
        # Create agents
        math_agent = Agent(
            node_id="math_specialist",
            capabilities=["mathematical-reasoning", "calculus", "statistics"]
        )
        
        code_agent = Agent(
            node_id="code_specialist", 
            capabilities=["code-generation", "debugging", "optimization"]
        )
        
        research_agent = Agent(
            node_id="research_specialist",
            capabilities=["web-search", "data-analysis", "summarization"]
        )
        
        print(f"✅ Created {len(get_registered_agents())} agents")
        
        # Create complex task
        complex_task = Task(
            description="Build a machine learning model to predict stock prices using financial data",
            requirements=["data-collection", "mathematical-modeling", "code-implementation"],
            context={"domain": "finance", "complexity": "high"}
        )
        
        print(f"✅ Task created: {complex_task}")
        
        # Execute task
        print("\n[EXECUTION] Starting multi-agent task execution...")
        result = execute_task(complex_task)
        
        print("\n[RESULT] Task execution completed!")
        print("=" * 60)
        print(result)
        print("=" * 60)
        
        return True
    except Exception as e:
        print(f"❌ Symphony integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_readme_example():
    """Test the exact example from README."""
    print("\n[TEST] Testing README example...")
    
    try:
        # This is the exact code from README
        from agents.agent import Agent
        from protocol.task_contract import Task
        from core.capability import CapabilityManager
        from symphony import execute_task
        
        # Initialize multiple specialized agents
        math_agent = Agent(
            node_id="math_specialist",
            capabilities=["mathematical-reasoning", "calculus", "statistics"]
        )
        
        code_agent = Agent(
            node_id="code_specialist", 
            capabilities=["code-generation", "debugging", "optimization"]
        )
        
        research_agent = Agent(
            node_id="research_specialist",
            capabilities=["web-search", "data-analysis", "summarization"]
        )
        
        # Create a complex task requiring multiple specialties
        complex_task = Task(
            description="Build a machine learning model to predict stock prices using financial data",
            requirements=["data-collection", "mathematical-modeling", "code-implementation"],
            context={"domain": "finance", "complexity": "high"}
        )
        
        # The framework automatically:
        # 1. Decomposes the task into specialized sub-tasks
        # 2. Broadcasts beacons to find suitable agents
        # 3. Routes sub-tasks to best-matching specialists
        # 4. Aggregates results through CoT voting
        
        result = execute_task(complex_task)
        
        print("\n✅ README example executed successfully!")
        print(f"Result length: {len(result)} characters")
        
        return True
    except Exception as e:
        print(f"❌ README example test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests."""
    print("🎼 Symphony Multi-Agent Task Execution Test Suite")
    print("=" * 60)
    
    tests = [
        test_basic_import,
        test_symphony_integration,
        test_readme_example
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Symphony multi-agent task execution is working!")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
