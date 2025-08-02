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
    """Run the crew with a custom prompt."""
    execution_context = get_execution_context()
    
    # Combine user prompt with execution context
    full_prompt = f"{execution_context}\n\nUSER REQUEST:\n{user_prompt}"
    
    inputs = {
        'topic': user_prompt,
        'current_year': str(datetime.now().year),
        'execution_context': execution_context,
        'full_prompt': full_prompt
    }
    
    try:
        print("🚀 Starting RSCrew with custom prompt...")
        print(f"📍 Working from: {os.getcwd()}")
        print(f"💭 Prompt: {user_prompt}")
        print("-" * 50)
        
        result = Rscrew().crew().kickoff(inputs=inputs)
        
        print("-" * 50)
        print("✅ RSCrew completed!")
        return result
        
    except Exception as e:
        print(f"❌ Error occurred while running the crew: {e}")
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