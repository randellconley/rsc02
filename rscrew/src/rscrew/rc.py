#!/usr/bin/env python
"""
RC - RSCrew Command Runner
A global command interface for running the RSCrew multi-agent system from anywhere.
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from rscrew.crew import Rscrew

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

def run_crew_with_prompt(user_prompt):
    """Run the crew with a custom prompt using interactive dialogue."""
    # Check if debug mode is enabled
    debug_mode = os.getenv('RSCREW_DEBUG', 'true').lower() == 'true'
    
    def debug_print(message):
        if debug_mode:
            print(f"[DEBUG] {message}")
    
    execution_context = get_execution_context()
    
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
    
    try:
        print("🚀 Starting RSCrew with Interactive Operator Dialogue...")
        print(f"📍 Working from: {os.getcwd()}")
        print(f"💭 Request: {user_prompt}")
        
        debug_print("Creating Rscrew instance...")
        crew_instance = Rscrew()
        debug_print("Rscrew instance created")
        
        debug_print("Starting interactive dialogue workflow...")
        result = crew_instance.run_with_interactive_dialogue(inputs)
        debug_print("Interactive workflow completed")
        
        print("\n" + "="*60)
        print("✅ RSCrew completed successfully!")
        print("="*60)
        return result
        
    except Exception as e:
        debug_print(f"Exception type: {type(e).__name__}")
        debug_print(f"Exception args: {e.args}")
        print(f"❌ Error occurred while running the crew: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def run():
    """
    Main entry point for the RC command.
    Handles command line arguments and executes the crew with custom prompts.
    """
    parser = argparse.ArgumentParser(
        description='RC - RSCrew Command Runner. Run CrewAI analysis from anywhere.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rc Please analyze this project and suggest improvements
  rc -f /path/to/prompt.txt
  rc Review the code in ./src/ and identify potential bugs
        """
    )
    
    parser.add_argument(
        '-f', '--file',
        help='Read prompt from a file instead of command line arguments'
    )
    
    parser.add_argument(
        'prompt',
        nargs='*',
        help='The prompt/request for the CrewAI agents (ignored if -f is used)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Determine the prompt source
    if args.file:
        # Read prompt from file
        user_prompt = read_prompt_file(args.file)
    elif args.prompt:
        # Use command line arguments as prompt
        user_prompt = ' '.join(args.prompt)
    else:
        # No prompt provided
        print("❌ Error: No prompt provided. Use either:")
        print("  rc Your prompt here")
        print("  rc -f /path/to/prompt.txt")
        print("\nUse 'rc --help' for more information.")
        sys.exit(1)
    
    # Validate prompt
    if not user_prompt.strip():
        print("❌ Error: Empty prompt provided.")
        sys.exit(1)
    
    # Run the crew with the custom prompt
    run_crew_with_prompt(user_prompt)

if __name__ == "__main__":
    run()