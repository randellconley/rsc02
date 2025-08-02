#!/usr/bin/env python
"""
RC - RSCrew Command Runner
A simple command interface for running the RSCrew multi-agent system.
"""

from rscrew.main import run as main_run

def run():
    """
    Run the RSCrew research crew.
    This is the main entry point for the 'rc' command.
    """
    print("🚀 Starting RSCrew...")
    main_run()
    print("✅ RSCrew completed!")

if __name__ == "__main__":
    run()