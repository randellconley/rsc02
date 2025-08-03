#!/usr/bin/env python3
"""
Debug script to test LLM error handling behavior
"""

import os
import sys
sys.path.insert(0, 'src')

from crewai import LLM
from rscrew.tenacity_llm_handler import create_tenacity_robust_llm

def test_basic_llm():
    """Test basic LLM functionality"""
    print("=== Testing Basic LLM ===")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    llm = LLM(model='claude-3-5-sonnet-20241022', api_key=api_key)
    
    try:
        response = llm.call("Say 'Hello World' and nothing else.")
        print(f"Basic LLM Response: {response}")
        print(f"Response type: {type(response)}")
        print(f"Response length: {len(str(response))}")
        return True
    except Exception as e:
        print(f"Basic LLM Error: {e}")
        return False

def test_wrapped_llm():
    """Test wrapped LLM functionality"""
    print("\n=== Testing Wrapped LLM ===")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    llm = LLM(model='claude-3-5-sonnet-20241022', api_key=api_key)
    
    # Wrap with error handling
    wrapped_llm = create_tenacity_robust_llm(llm, fallback_enabled=True)
    
    try:
        response = wrapped_llm.call("Say 'Hello World' and nothing else.")
        print(f"Wrapped LLM Response: {response}")
        print(f"Response type: {type(response)}")
        print(f"Response length: {len(str(response))}")
        return True
    except Exception as e:
        print(f"Wrapped LLM Error: {e}")
        return False

def test_multiple_concurrent_calls():
    """Test multiple concurrent LLM calls to simulate crew behavior"""
    print("\n=== Testing Multiple Concurrent Calls ===")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    results = []
    for i in range(5):
        print(f"Call {i+1}:")
        llm = LLM(model='claude-3-5-sonnet-20241022', api_key=api_key)
        wrapped_llm = create_tenacity_robust_llm(llm, fallback_enabled=True)
        
        try:
            response = wrapped_llm.call(f"Say 'Response {i+1}' and nothing else.")
            print(f"  Response: {response}")
            print(f"  Length: {len(str(response))}")
            results.append(True)
        except Exception as e:
            print(f"  Error: {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\nSuccess rate: {success_rate:.1f}% ({sum(results)}/{len(results)})")
    return success_rate >= 80  # 80% success rate is acceptable

def test_wrapped_llm_no_fallback():
    """Test wrapped LLM functionality without fallback"""
    print("\n=== Testing Wrapped LLM (No Fallback) ===")
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    llm = LLM(model='claude-3-5-sonnet-20241022', api_key=api_key)
    
    # Wrap with error handling but no fallback
    wrapped_llm = create_tenacity_robust_llm(llm, fallback_enabled=False)
    
    try:
        response = wrapped_llm.call("Say 'Hello World' and nothing else.")
        print(f"Wrapped LLM (No Fallback) Response: {response}")
        print(f"Response type: {type(response)}")
        print(f"Response length: {len(str(response))}")
        return True
    except Exception as e:
        print(f"Wrapped LLM (No Fallback) Error: {e}")
        return False

if __name__ == "__main__":
    # Set debug mode
    os.environ['RSCREW_DEBUG'] = 'true'
    
    print("Debug LLM Test")
    print("=" * 50)
    
    basic_ok = test_basic_llm()
    wrapped_ok = test_wrapped_llm()
    multiple_ok = test_multiple_concurrent_calls()
    wrapped_no_fallback_ok = test_wrapped_llm_no_fallback()
    
    print("\n" + "=" * 50)
    print("RESULTS:")
    print(f"Basic LLM: {'✅ PASS' if basic_ok else '❌ FAIL'}")
    print(f"Wrapped LLM: {'✅ PASS' if wrapped_ok else '❌ FAIL'}")
    print(f"Multiple Calls: {'✅ PASS' if multiple_ok else '❌ FAIL'}")
    print(f"Wrapped LLM (No Fallback): {'✅ PASS' if wrapped_no_fallback_ok else '❌ FAIL'}")
    
    if basic_ok and not wrapped_ok:
        print("\n🔍 DIAGNOSIS: Error handling wrapper is causing issues!")
    elif basic_ok and wrapped_ok and not multiple_ok:
        print("\n🔍 DIAGNOSIS: Rate limiting or concurrent call issues detected!")
    elif basic_ok and wrapped_ok and str(wrapped_ok).startswith("# Unable to generate"):
        print("\n🔍 DIAGNOSIS: Wrapper is incorrectly triggering fallback responses!")