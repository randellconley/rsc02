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

def run():
    """
    Main entry point for the RC command.
    Handles flag-based planning system and legacy prompt mode.
    """
    parser = argparse.ArgumentParser(
        description='RC - RSCrew Command Runner. Flag-based planning system.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Flag-Based Planning System:
  rc -plan "Build a web app" [-name my_app]     Generate implementation plan
  rc -build /path/to/plan.md                   Implement from plan
  rc -update /path/to/plan.md                  Interactive plan updates

Legacy Mode:
  rc Please analyze this project                Traditional crew execution
  rc -f /path/to/prompt.txt                    Read prompt from file

Examples:
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
    
    # Legacy arguments
    parser.add_argument(
        '-f', '--file',
        help='Read prompt from a file (legacy mode)'
    )
    
    parser.add_argument(
        'prompt',
        nargs='*',
        help='The prompt/request for the CrewAI agents (legacy mode)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Flag-based planning system
    if args.plan:
        run_plan_generation(args.plan, args.name)
    elif args.build:
        run_plan_implementation(args.build)
    elif args.update:
        run_plan_update(args.update)
    # Legacy mode
    elif args.file:
        user_prompt = read_prompt_file(args.file)
        run_crew_with_prompt(user_prompt)
    elif args.prompt:
        user_prompt = ' '.join(args.prompt)
        run_crew_with_prompt(user_prompt)
    else:
        # No arguments provided
        print("❌ Error: No command provided. Use either:")
        print("\nFlag-based planning:")
        print("  rc -plan \"Your request here\" [-name plan_name]")
        print("  rc -build /path/to/plan.md")
        print("  rc -update /path/to/plan.md")
        print("\nLegacy mode:")
        print("  rc Your prompt here")
        print("  rc -f /path/to/prompt.txt")
        print("\nUse 'rc --help' for more information.")
        sys.exit(1)

if __name__ == "__main__":
    run()