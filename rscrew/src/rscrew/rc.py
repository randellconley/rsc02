#!/usr/bin/env python
"""
RC - RSCrew Command Runner
A global command interface for running the RSCrew multi-agent system from anywhere.
Supports flag-based planning system: -plan, -build, -update
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from rscrew.crew import Rscrew
from rscrew.output_capture import capture_output
from rscrew.plan_manager import PlanManager, InteractivePlanSession
import subprocess
import tempfile
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def read_prompt_file(file_path):
    """Read prompt from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"❌ Error: Prompt file '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading prompt file: {e}")
        sys.exit(1)

def get_execution_context():
    """Get context about where the RC command is being executed."""
    current_dir = os.getcwd()
    dir_name = os.path.basename(current_dir)
    
    # Get list of files and directories in current location
    try:
        items = os.listdir(current_dir)
        files = [f for f in items if os.path.isfile(os.path.join(current_dir, f))]
        dirs = [d for d in items if os.path.isdir(os.path.join(current_dir, d))]
    except PermissionError:
        files, dirs = [], []
    
    context = f"""
EXECUTION CONTEXT:
- Current working directory: {current_dir}
- Directory name: {dir_name}
- Files in directory: {', '.join(files[:10])}{'...' if len(files) > 10 else ''}
- Subdirectories: {', '.join(dirs[:10])}{'...' if len(dirs) > 10 else ''}
- Total files: {len(files)}, Total directories: {len(dirs)}
"""
    return context

class OutputLogger:
    """Custom logger to capture all output during RC execution"""
    
    def __init__(self):
        self.output_buffer = []
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def write(self, text):
        # Write to original stdout/stderr for real-time display
        self.original_stdout.write(text)
        self.original_stdout.flush()
        # Also capture for later saving
        self.output_buffer.append(text)
    
    def flush(self):
        self.original_stdout.flush()
    
    def get_captured_output(self):
        return ''.join(self.output_buffer)

def run_crew_with_prompt(user_prompt):
    """Run the crew with a custom prompt using interactive dialogue."""
    # Check if debug mode is enabled
    debug_mode = os.getenv('RSCREW_DEBUG', 'true').lower() == 'true'
    
    def debug_print(message):
        if debug_mode:
            print(f"[DEBUG] {message}")
    
    execution_context = get_execution_context()
    working_dir = os.getcwd()
    
    # Prepare initial inputs
    inputs = {
        'topic': user_prompt,
        'current_year': str(datetime.now().year),
        'execution_context': execution_context
    }
    
    debug_print(f"=== RC Initial Inputs Debug ===")
    debug_print(f"Inputs keys: {list(inputs.keys())}")
    debug_print(f"Topic: {inputs['topic']}")
    debug_print(f"Current year: {inputs['current_year']}")
    debug_print(f"Execution context length: {len(inputs['execution_context'])}")
    debug_print("===============================")
    
    # Set up output capture
    output_logger = OutputLogger()
    
    try:
        print("🚀 Starting RSCrew with Interactive Operator Dialogue...")
        print(f"📍 Working from: {working_dir}")
        print(f"💭 Request: {user_prompt}")
        print("=" * 60)
        
        # Start capturing output (but allow interactive input)
        sys.stdout = output_logger
        
        debug_print("Creating Rscrew instance...")
        crew_instance = Rscrew()
        debug_print("Rscrew instance created")
        
        debug_print("Starting interactive dialogue workflow...")
        result = crew_instance.run_with_interactive_dialogue(inputs)
        debug_print("Interactive workflow completed")
        
        # Restore original stdout
        sys.stdout = output_logger.original_stdout
        
        print("\n" + "="*60)
        print("✅ RSCrew completed successfully!")
        print("="*60)
        
        # Get captured output
        captured_output = output_logger.get_captured_output()
        
        # Save output to file
        command_summary = f"rc {user_prompt[:50]}{'...' if len(user_prompt) > 50 else ''}"
        try:
            capture_output(
                prompt=user_prompt,
                output=captured_output,
                working_dir=working_dir,
                command=command_summary
            )
        except Exception as capture_error:
            print(f"[OUTPUT] Warning: Could not save output - {capture_error}")
        
        return result
        
    except Exception as e:
        # Restore original stdout in case of error
        sys.stdout = output_logger.original_stdout
        
        debug_print(f"Exception type: {type(e).__name__}")
        debug_print(f"Exception args: {e.args}")
        
        # Get any captured output before the error
        captured_output = output_logger.get_captured_output()
        error_output = captured_output + f"\n--- ERROR ---\n{str(e)}"
        
        print(f"❌ Error occurred while running the crew: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()
            error_output += f"\n--- TRACEBACK ---\n{traceback.format_exc()}"
        
        # Save error output to file
        command_summary = f"rc {user_prompt[:50]}{'...' if len(user_prompt) > 50 else ''} [ERROR]"
        try:
            capture_output(
                prompt=user_prompt,
                output=error_output,
                working_dir=working_dir,
                command=command_summary
            )
        except Exception as capture_error:
            print(f"[OUTPUT] Warning: Could not save error output - {capture_error}")
        
        sys.exit(1)

def run_plan_generation(prompt: str, plan_name: str = None) -> str:
    """Generate an implementation plan"""
    print("🚀 Starting Plan Generation...")
    print(f"💭 Request: {prompt}")
    print("=" * 60)
    
    # Initialize plan manager
    plan_manager = PlanManager()
    
    # Generate plan filename
    plan_filename = plan_manager.generate_plan_name(plan_name)
    plan_path = plan_manager.get_plan_path(plan_filename)
    
    # Prepare inputs for planning crew
    inputs = {
        'topic': prompt,
        'current_year': str(datetime.now().year),
        'execution_context': get_execution_context()
    }
    
    try:
        # Create crew instance and run planning crew
        crew_instance = Rscrew()
        planning_crew = crew_instance.planning_crew()
        result = planning_crew.kickoff(inputs=inputs)
        
        # Extract plan content from result
        plan_content = result.raw if hasattr(result, 'raw') else str(result)
        
        # Save plan to file
        plan_manager.save_plan(plan_content, plan_path)
        
        print("\n" + "="*60)
        print("✅ Plan generation completed successfully!")
        print(f"📄 Plan saved to: {plan_path}")
        print("="*60)
        
        return str(plan_path)
        
    except Exception as e:
        print(f"❌ Error generating plan: {e}")
        sys.exit(1)

def run_plan_implementation(plan_path: str) -> None:
    """Implement from an existing plan"""
    print("🚀 Starting Plan Implementation...")
    print(f"📄 Plan file: {plan_path}")
    print("=" * 60)
    
    # Initialize plan manager
    plan_manager = PlanManager()
    plan_file_path = Path(plan_path)
    
    # Validate plan file exists
    if not plan_file_path.exists():
        print(f"❌ Error: Plan file not found: {plan_path}")
        sys.exit(1)
    
    try:
        # Load and validate plan
        plan_content = plan_manager.load_plan(plan_file_path)
        is_valid, missing_sections = plan_manager.validate_plan(plan_content)
        
        if not is_valid:
            print("❌ Error: Plan file is missing required sections:")
            for section in missing_sections:
                print(f"  - {section}")
            sys.exit(1)
        
        # Prepare inputs for implementation crew
        inputs = {
            'topic': plan_manager.extract_plan_title(plan_content),
            'implementation_plan': plan_content,
            'current_year': str(datetime.now().year)
        }
        
        # Create crew instance and run implementation crew
        crew_instance = Rscrew()
        implementation_crew = crew_instance.implementation_crew()
        result = implementation_crew.kickoff(inputs=inputs)
        
        print("\n" + "="*60)
        print("✅ Implementation completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error implementing plan: {e}")
        sys.exit(1)

def run_plan_update(plan_path: str) -> None:
    """Start interactive plan update session"""
    print("🚀 Starting Interactive Plan Update...")
    print(f"📄 Plan file: {plan_path}")
    print("=" * 60)
    
    # Initialize plan manager
    plan_manager = PlanManager()
    plan_file_path = Path(plan_path)
    
    # Validate plan file exists
    if not plan_file_path.exists():
        print(f"❌ Error: Plan file not found: {plan_path}")
        sys.exit(1)
    
    try:
        # Validate plan
        plan_content = plan_manager.load_plan(plan_file_path)
        is_valid, missing_sections = plan_manager.validate_plan(plan_content)
        
        if not is_valid:
            print("⚠️  Warning: Plan file is missing some sections:")
            for section in missing_sections:
                print(f"  - {section}")
            print("Continuing with interactive update...\n")
        
        # Start interactive session
        session = InteractivePlanSession(plan_file_path, plan_manager)
        session.run()
        
    except Exception as e:
        print(f"❌ Error updating plan: {e}")
        sys.exit(1)

def run_system_test():
    """Run comprehensive system health check and connectivity tests."""
    print("🚀 RSCrew System Health Check")
    print("=" * 40)
    
    # Test 1: Dependencies
    try:
        import crewai, litellm, yaml, os
        print("✅ Dependencies: All required packages installed")
    except ImportError as e:
        print(f"❌ Dependencies: Missing {e}")
        return False
    
    # Test 2: Configuration
    try:
        from rscrew.model_manager import get_model_manager
        manager = get_model_manager()
        config = manager.config
        print(f"✅ Configuration: {len(config['providers'])} providers configured")
    except Exception as e:
        print(f"❌ Configuration: {e}")
        return False
    
    # Test 3: Model Manager
    try:
        from rscrew.model_manager import get_model_manager
        manager = get_model_manager()
        stats = manager.get_provider_stats()
        print(f"✅ Model Manager: {len(stats['available_providers'])}/4 providers available")
    except Exception as e:
        print(f"❌ Model Manager: {e}")
        return False
    
    # Test 4: Provider Connectivity (using model_manager_cli.py)
    try:
        print("\n🔗 Testing Provider Connectivity:")
        result = subprocess.run([
            sys.executable, 'model_manager_cli.py', 'status'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
        
        if result.returncode == 0:
            # Extract operational providers from output
            operational_count = result.stdout.count("✅ Operational")
            print(f"✅ Provider Connectivity: {operational_count}/4 providers operational")
        else:
            print("❌ Provider Connectivity: Failed to test providers")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Provider Connectivity: {e}")
        return False
    
    # Test 5: Crew Creation
    try:
        from rscrew.crew import Rscrew
        crew_instance = Rscrew()
        crew = crew_instance.crew()
        print(f"✅ Crew Creation: {len(crew.agents)} agents created successfully")
    except Exception as e:
        print(f"❌ Crew Creation: {e}")
        return False
    
    print("\n🎉 All tests passed! System is operational.")
    return True

def run_quick_check():
    """Run quick system status check."""
    print("⚡ Quick System Check")
    print("=" * 20)
    
    # Check API keys
    api_keys = {
        'CLAUDE': os.getenv('ANTHROPIC_API_KEY'),
        'GEMINI': os.getenv('GEMINI_API_KEY'), 
        'OPENAI': os.getenv('OPENAI_API_KEY'),
        'DEEPSEEK': os.getenv('DEEPSEEK_API_KEY')
    }
    
    print("API Keys:")
    for provider, key in api_keys.items():
        status = "✅" if key else "❌"
        print(f"  {provider}: {status}")
    
    # Quick model manager test
    try:
        from rscrew.model_manager import get_model_manager
        manager = get_model_manager()
        stats = manager.get_provider_stats()
        available = len(stats['available_providers'])
        print(f"\nProviders: {available}/4 available")
        
        if available == 4:
            print("✅ System ready")
        else:
            print("⚠️  Some providers unavailable")
    except Exception as e:
        print(f"❌ Model manager error: {e}")

# Test Infrastructure Functions

class TestResult:
    def __init__(self, name, passed, duration, output="", error=""):
        self.name = name
        self.passed = passed
        self.duration = duration
        self.output = output
        self.error = error

def get_test_assets_dir():
    """Get the path to test assets directory"""
    current_file = Path(__file__).parent
    project_root = current_file.parent.parent
    return project_root / "tests" / "assets"

def create_test_workspace(test_name):
    """Create isolated test workspace"""
    timestamp = int(time.time())
    test_dir = Path(tempfile.gettempdir()) / f"rc_test_{test_name}_{timestamp}"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir

def validate_test_output(test_name, output, duration):
    """Fuzzy validation logic for test outputs"""
    output_lower = output.lower()
    
    # Common failure patterns
    failure_patterns = [
        "fatal", "crashed", "failed", "error:", "exception:",
        "traceback", "authentication failed", "permission denied"
    ]
    
    # Check for immediate failures
    if duration < 5:
        return False, "Test completed too quickly (likely immediate failure)"
    
    # Check for timeout (should be handled by caller)
    if duration > 600:  # 10 minutes
        return False, "Test exceeded timeout"
    
    # Check for failure patterns
    for pattern in failure_patterns:
        if pattern in output_lower:
            return False, f"Found failure pattern: {pattern}"
    
    # Test-specific validations
    if test_name == "basic":
        if len(output) < 100:
            return False, "Output too short for basic prompt test"
        if "agent" not in output_lower:
            return False, "No agent activity detected"
    
    elif test_name == "plan":
        if "plan" not in output_lower and ".md" not in output_lower:
            return False, "No plan generation detected"
    
    elif test_name == "build":
        if "build" not in output_lower and "implement" not in output_lower:
            return False, "No build activity detected"
    
    elif test_name == "file":
        if len(output) < 50:
            return False, "Output too short for file input test"
    
    return True, "Test passed validation"

def run_single_test(test_name, timeout=600):
    """Run a single test with timeout and validation"""
    start_time = time.time()
    test_dir = create_test_workspace(test_name)
    assets_dir = get_test_assets_dir()
    
    try:
        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(test_dir)
        
        # Prepare test command based on test type
        if test_name == "basic":
            prompt = (assets_dir / "basic_prompt.txt").read_text().strip()
            cmd = ["rc", prompt]
        
        elif test_name == "plan":
            prompt = (assets_dir / "plan_prompt.txt").read_text().strip()
            cmd = ["rc", "-plan", prompt, "-name", "test_calc"]
        
        elif test_name == "build":
            plan_file = assets_dir / "test_plan.md"
            cmd = ["rc", "-build", str(plan_file)]
        
        elif test_name == "update":
            plan_file = assets_dir / "test_plan.md"
            cmd = ["rc", "-update", str(plan_file)]
        
        elif test_name == "file":
            prompt_file = assets_dir / "file_prompt.txt"
            cmd = ["rc", "-f", str(prompt_file)]
        
        else:
            return TestResult(test_name, False, 0, "", f"Unknown test type: {test_name}")
        
        # Run the test command
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=test_dir
            )
            
            duration = time.time() - start_time
            output = result.stdout + result.stderr
            
            # Validate output
            passed, validation_msg = validate_test_output(test_name, output, duration)
            
            if not passed:
                return TestResult(test_name, False, duration, output, validation_msg)
            
            # Check exit code
            if result.returncode != 0:
                return TestResult(test_name, False, duration, output, f"Non-zero exit code: {result.returncode}")
            
            return TestResult(test_name, True, duration, output)
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(test_name, False, duration, "", f"Test timed out after {timeout} seconds")
        
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(test_name, False, duration, "", f"Test execution error: {e}")
    
    finally:
        # Cleanup
        os.chdir(original_cwd)
        try:
            shutil.rmtree(test_dir)
        except:
            pass  # Best effort cleanup

def run_test_command(test_type=None, details=False, clean=False):
    """Run RC test commands"""
    
    if clean:
        # Clean up test artifacts
        project_root = Path(__file__).parent.parent.parent
        test_dirs = [
            project_root / "tests" / "runs",
            project_root / "tests" / "results"
        ]
        
        cleaned = 0
        for test_dir in test_dirs:
            if test_dir.exists():
                try:
                    shutil.rmtree(test_dir)
                    test_dir.mkdir(parents=True, exist_ok=True)
                    cleaned += 1
                except Exception as e:
                    print(f"⚠️  Could not clean {test_dir}: {e}")
        
        print(f"🧹 Cleaned {cleaned} test directories")
        return
    
    # Define available tests
    available_tests = ["basic", "plan", "build", "update", "file"]
    
    if test_type and test_type not in available_tests + ["all"]:
        print(f"❌ Unknown test type: {test_type}")
        print(f"Available tests: {', '.join(available_tests + ['all'])}")
        return
    
    # Determine which tests to run
    if test_type == "all" or test_type is None:
        tests_to_run = available_tests
        parallel = True
    else:
        tests_to_run = [test_type]
        parallel = False
    
    print("🧪 RC Test Suite")
    print("=" * 40)
    
    if parallel and len(tests_to_run) > 1:
        # Run tests in parallel
        print(f"Running {len(tests_to_run)} tests in parallel...")
        print()
        
        with ThreadPoolExecutor(max_workers=len(tests_to_run)) as executor:
            # Submit all tests
            future_to_test = {
                executor.submit(run_single_test, test): test 
                for test in tests_to_run
            }
            
            results = []
            for future in as_completed(future_to_test):
                test_name = future_to_test[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Show progress
                    status = "✅ PASSED" if result.passed else "❌ FAILED"
                    duration_str = f"{result.duration:.1f}s"
                    print(f"{status} {result.name.title()} Test ({duration_str})")
                    
                    if not result.passed:
                        print(f"   Error: {result.error}")
                    
                except Exception as e:
                    results.append(TestResult(test_name, False, 0, "", str(e)))
                    print(f"❌ FAILED {test_name.title()} Test (error)")
                    print(f"   Error: {e}")
    
    else:
        # Run tests sequentially
        results = []
        for test in tests_to_run:
            print(f"Running {test} test...")
            result = run_single_test(test)
            results.append(result)
            
            status = "✅ PASSED" if result.passed else "❌ FAILED"
            duration_str = f"{result.duration:.1f}s"
            print(f"{status} {result.name.title()} Test ({duration_str})")
            
            if not result.passed:
                print(f"   Error: {result.error}")
            
            if details and result.output:
                print(f"\n--- {test.title()} Test Output ---")
                print(result.output[:1000] + ("..." if len(result.output) > 1000 else ""))
                print("--- End Output ---\n")
    
    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    print()
    print("=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")
        print("Use 'rc -test <name> --details' for expanded output")

def run():
    """
    Main entry point for the RC command.
    Handles flag-based planning system and direct prompt mode.
    """
    parser = argparse.ArgumentParser(
        description='RC - RSCrew Command Runner. Direct prompts and planning system.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Testing Commands:
  rc -test                                     Run basic direct prompt test
  rc -test plan                               Test plan generation functionality
  rc -test build                              Test build implementation functionality
  rc -test update                             Test update functionality
  rc -test file                               Test file input functionality
  rc -test all                                Run all tests in parallel
  rc -test --clean                            Clean up test generated files
  rc -check                                   System health check

Planning System:
  rc -plan "Build a web app" [-name my_app]   Generate implementation plan
  rc -build /path/to/plan.md                  Implement from plan
  rc -update /path/to/plan.md                 Interactive plan updates

Primary Mode (Default):
  rc "Your prompt here"                       Direct crew execution
  rc -f /path/to/prompt.txt                   Read prompt from file

Examples:
  rc -test                                    # Test basic functionality
  rc -test all                                # Run comprehensive test suite
  rc -plan "Create a REST API for user management"
  rc -plan "Build a task tracker" -name task_manager
  rc -build ./plans/task_manager.md
  rc -update ./plans/task_manager.md
        """
    )
    
    # Flag-based planning arguments
    parser.add_argument(
        '-plan',
        help='Generate implementation plan from prompt'
    )
    
    parser.add_argument(
        '-name',
        help='Custom name for plan file (optional, auto-adds .md extension)'
    )
    
    parser.add_argument(
        '-build',
        help='Implement from existing plan file'
    )
    
    parser.add_argument(
        '-update',
        help='Start interactive plan update session'
    )
    
    # Testing arguments
    parser.add_argument(
        '-test',
        nargs='?',
        const='basic',
        help='Run test commands: basic, plan, build, update, file, all'
    )
    
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean up test generated files (use with -test)'
    )
    
    parser.add_argument(
        '--details',
        action='store_true',
        help='Show detailed test output (use with -test)'
    )
    
    parser.add_argument(
        '-check',
        action='store_true', 
        help='System health check'
    )
    
    # Primary mode arguments
    parser.add_argument(
        '-f', '--file',
        help='Read prompt from a file'
    )
    
    parser.add_argument(
        'prompt',
        nargs='*',
        help='The prompt/request for the CrewAI agents (primary mode)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Testing system
    if args.test is not None:
        run_test_command(test_type=args.test, details=args.details, clean=args.clean)
    elif args.check:
        run_quick_check()
    # Planning system
    elif args.plan:
        run_plan_generation(args.plan, args.name)
    elif args.build:
        run_plan_implementation(args.build)
    elif args.update:
        run_plan_update(args.update)
    # Primary mode
    elif args.file:
        user_prompt = read_prompt_file(args.file)
        run_crew_with_prompt(user_prompt)
    elif args.prompt:
        user_prompt = ' '.join(args.prompt)
        run_crew_with_prompt(user_prompt)
    else:
        # No arguments provided
        print("❌ Error: No command provided. Use either:")
        print("\nTesting:")
        print("  rc -test                                 # Basic functionality test")
        print("  rc -test all                             # Run all tests")
        print("  rc -check                                # System health check")
        print("\nPlanning system:")
        print("  rc -plan \"Your request here\" [-name plan_name]")
        print("  rc -build /path/to/plan.md")
        print("  rc -update /path/to/plan.md")
        print("\nPrimary mode:")
        print("  rc \"Your prompt here\"")
        print("  rc -f /path/to/prompt.txt")
        print("\nUse 'rc --help' for more information.")
        sys.exit(1)

if __name__ == "__main__":
    run()