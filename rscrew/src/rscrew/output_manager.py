#!/usr/bin/env python
"""
Output Manager for RSCrew Console Outputs

Utility script for managing saved console outputs from RC command executions.
"""

import os
import glob
import argparse
from pathlib import Path
from datetime import datetime
from rscrew.output_capture import OutputCapture

def list_outputs(limit=10, pattern="*"):
    """List recent output files"""
    capture = OutputCapture()
    output_dir = capture.output_dir
    
    if pattern == "*":
        search_pattern = str(output_dir / "*_inquiry-*_*.txt")
    else:
        search_pattern = str(output_dir / f"*{pattern}*.txt")
    
    files = glob.glob(search_pattern)
    
    if not files:
        print("No output files found.")
        return
    
    # Sort by modification time (newest first)
    files_with_time = [(f, os.path.getmtime(f)) for f in files]
    files_with_time.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Recent output files (showing {min(limit, len(files_with_time))}):")
    print("=" * 60)
    
    for i, (filepath, mtime) in enumerate(files_with_time[:limit], 1):
        filename = os.path.basename(filepath)
        file_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        file_size = os.path.getsize(filepath)
        
        print(f"{i:2d}. {filename}")
        print(f"    Modified: {file_time} | Size: {file_size:,} bytes")
        
        # Show first line of prompt from file
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("Initial Prompt:"):
                        prompt = line.replace("Initial Prompt:", "").strip()
                        print(f"    Prompt: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
                        break
        except:
            pass
        print()

def view_output(filename_or_number):
    """View a specific output file"""
    capture = OutputCapture()
    output_dir = capture.output_dir
    
    # If it's a number, get the nth most recent file
    if filename_or_number.isdigit():
        files = glob.glob(str(output_dir / "*_inquiry-*_*.txt"))
        if not files:
            print("No output files found.")
            return
        
        files_with_time = [(f, os.path.getmtime(f)) for f in files]
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        
        file_index = int(filename_or_number) - 1
        if file_index >= len(files_with_time):
            print(f"File number {filename_or_number} not found. Only {len(files_with_time)} files available.")
            return
        
        filepath = files_with_time[file_index][0]
    else:
        # Direct filename
        if not filename_or_number.endswith('.txt'):
            filename_or_number += '.txt'
        filepath = output_dir / filename_or_number
        
        if not filepath.exists():
            print(f"File not found: {filepath}")
            return
    
    # Display the file
    print(f"Viewing: {os.path.basename(filepath)}")
    print("=" * 60)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
    except Exception as e:
        print(f"Error reading file: {e}")

def cleanup_old_files(keep_count=200):
    """Clean up old output files, keeping only the most recent ones"""
    capture = OutputCapture()
    capture.max_files = keep_count
    
    files = glob.glob(str(capture.output_dir / "*_inquiry-*_*.txt"))
    original_count = len(files)
    
    capture.cleanup_old_files()
    
    files_after = glob.glob(str(capture.output_dir / "*_inquiry-*_*.txt"))
    final_count = len(files_after)
    
    removed_count = original_count - final_count
    
    print(f"Cleanup completed:")
    print(f"  Original files: {original_count}")
    print(f"  Files removed: {removed_count}")
    print(f"  Files remaining: {final_count}")

def search_outputs(search_term):
    """Search for outputs containing specific terms"""
    capture = OutputCapture()
    output_dir = capture.output_dir
    
    files = glob.glob(str(output_dir / "*_inquiry-*_*.txt"))
    matches = []
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                if search_term.lower() in content:
                    matches.append(filepath)
        except:
            continue
    
    if not matches:
        print(f"No files found containing '{search_term}'")
        return
    
    print(f"Found {len(matches)} files containing '{search_term}':")
    print("=" * 60)
    
    for i, filepath in enumerate(matches, 1):
        filename = os.path.basename(filepath)
        mtime = os.path.getmtime(filepath)
        file_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"{i}. {filename}")
        print(f"   Modified: {file_time}")
        print()

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description='RSCrew Output Manager - Manage saved console outputs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m rscrew.output_manager list                    # List recent files
  python -m rscrew.output_manager list -n 20              # List 20 most recent
  python -m rscrew.output_manager view 1                  # View most recent file
  python -m rscrew.output_manager view filename.txt       # View specific file
  python -m rscrew.output_manager search "apache"         # Search for term
  python -m rscrew.output_manager cleanup                 # Clean old files
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List output files')
    list_parser.add_argument('-n', '--number', type=int, default=10, help='Number of files to show')
    list_parser.add_argument('-p', '--pattern', default='*', help='Filter pattern')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View output file')
    view_parser.add_argument('file', help='File number (1-N) or filename')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search output files')
    search_parser.add_argument('term', help='Search term')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old files')
    cleanup_parser.add_argument('-k', '--keep', type=int, default=200, help='Number of files to keep')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'list':
        list_outputs(args.number, args.pattern)
    elif args.command == 'view':
        view_output(args.file)
    elif args.command == 'search':
        search_outputs(args.term)
    elif args.command == 'cleanup':
        cleanup_old_files(args.keep)

if __name__ == "__main__":
    main()