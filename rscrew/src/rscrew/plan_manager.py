#!/usr/bin/env python
"""
Plan Manager - Utilities for managing implementation plans
Handles plan file operations, parsing, and interactive updates
"""

import os
import re
import difflib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from rscrew.crew import Rscrew

class PlanManager:
    """Manages implementation plan files and operations"""
    
    def __init__(self, plans_dir: str = None):
        if plans_dir is None:
            # Find project root and use plans directory there
            plans_dir = self._find_project_plans_dir()
        self.plans_dir = Path(plans_dir)
        self.plans_dir.mkdir(exist_ok=True)
        self.crew_instance = None
    
    def _find_project_plans_dir(self) -> str:
        """Find the project root and return the plans directory path"""
        # Start from the module's location to find the project root
        module_dir = Path(__file__).parent  # This is src/rscrew/
        
        # Go up to find the rscrew root directory
        rscrew_root = module_dir.parent.parent  # This should be the rscrew/ directory
        
        # Verify this is the correct rscrew directory
        if (rscrew_root / "src" / "rscrew").exists():
            plans_dir = rscrew_root / "plans"
            if os.getenv('RSCREW_DEBUG', 'false').lower() == 'true':
                print(f"[DEBUG] Found rscrew root at: {rscrew_root}")
                print(f"[DEBUG] Plans directory will be: {plans_dir}")
            return str(plans_dir)
        
        # Fallback: look for project structure from current working directory
        current_dir = Path.cwd()
        
        # Check if we're already in a project with rscrew structure
        if (current_dir / "rscrew" / "src").exists():
            return str(current_dir / "rscrew" / "plans")
        
        # Check if we're inside the rscrew directory
        if current_dir.name == "rscrew" and (current_dir / "src").exists():
            return str(current_dir / "plans")
        
        # Check if we're deeper in the rscrew structure
        for parent in current_dir.parents:
            if parent.name == "rscrew" and (parent / "src").exists():
                return str(parent / "plans")
            # Check if parent has rscrew subdirectory
            if (parent / "rscrew" / "src").exists():
                return str(parent / "rscrew" / "plans")
        
        # Fallback to current directory if no project structure found
        return "./plans"
    
    def get_crew_instance(self) -> Rscrew:
        """Get or create crew instance"""
        if self.crew_instance is None:
            self.crew_instance = Rscrew()
        return self.crew_instance
    
    def generate_plan_name(self, custom_name: Optional[str] = None) -> str:
        """Generate plan filename with optional custom name"""
        if custom_name:
            # Ensure .md extension
            if not custom_name.endswith('.md'):
                custom_name += '.md'
            return custom_name
        else:
            # Auto-generate with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f'plan_{timestamp}.md'
    
    def get_plan_path(self, plan_name: str) -> Path:
        """Get full path for plan file"""
        return self.plans_dir / plan_name
    
    def load_plan(self, plan_path: Path) -> str:
        """Load plan content from file"""
        if not plan_path.exists():
            raise FileNotFoundError(f"Plan file not found: {plan_path}")
        
        try:
            with open(plan_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Error reading plan file: {e}")
    
    def save_plan(self, content: str, plan_path: Path) -> None:
        """Save plan content to file"""
        try:
            with open(plan_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            raise Exception(f"Error saving plan file: {e}")
    
    def validate_plan(self, content: str) -> Tuple[bool, List[str]]:
        """Validate plan has required sections"""
        required_sections = [
            "# Implementation Plan:",
            "## Executive Summary",
            "## Technical Architecture",
            "## Implementation Roadmap",
            "## Resource Requirements",
            "## Risk Assessment",
            "## Success Criteria"
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in content:
                missing_sections.append(section)
        
        is_valid = len(missing_sections) == 0
        return is_valid, missing_sections
    
    def parse_plan_sections(self, content: str) -> Dict[str, str]:
        """Parse plan content into sections"""
        sections = {}
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            # Check if this is a section header
            if line.startswith('## '):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = line.replace('## ', '').strip()
                current_content = [line]
            elif current_section:
                current_content.append(line)
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def extract_plan_title(self, content: str) -> str:
        """Extract plan title from content"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# Implementation Plan:'):
                return line.replace('# Implementation Plan:', '').strip()
        return "Unknown Plan"
    
    def show_change_preview(self, original_sections: Dict[str, str], updated_sections: Dict[str, str]) -> None:
        """Display diff preview of changes"""
        print("\n📝 Preview of changes:")
        
        for section_name in updated_sections:
            if section_name in original_sections:
                original_lines = original_sections[section_name].splitlines()
                updated_lines = updated_sections[section_name].splitlines()
                
                # Generate diff
                diff = list(difflib.unified_diff(
                    original_lines, 
                    updated_lines,
                    fromfile=f"Current {section_name}",
                    tofile=f"Updated {section_name}",
                    lineterm=""
                ))
                
                if diff:
                    print(f"\n🔄 Changes to {section_name}:")
                    for line in diff[2:]:  # Skip the file headers
                        if line.startswith('+') and not line.startswith('+++'):
                            print(f"🟢 {line}")
                        elif line.startswith('-') and not line.startswith('---'):
                            print(f"🔴 {line}")
                        elif line.startswith('@@'):
                            print(f"📍 {line}")
            else:
                print(f"\n✨ New section: {section_name}")
                print(f"🟢 {updated_sections[section_name][:200]}...")
    
    def apply_changes(self, current_plan: str, updated_sections: Dict[str, str]) -> str:
        """Apply changes to plan content"""
        current_sections = self.parse_plan_sections(current_plan)
        
        # Update sections
        for section_name, new_content in updated_sections.items():
            current_sections[section_name] = new_content
        
        # Reconstruct plan
        lines = []
        plan_lines = current_plan.split('\n')
        
        # Keep title and any content before first section
        in_section = False
        for line in plan_lines:
            if line.startswith('## '):
                in_section = True
                section_name = line.replace('## ', '').strip()
                if section_name in current_sections:
                    lines.append(current_sections[section_name])
                else:
                    lines.append(line)
            elif not in_section:
                lines.append(line)
        
        return '\n'.join(lines)
    
    def display_plan_summary(self, content: str) -> None:
        """Display a summary of the plan"""
        title = self.extract_plan_title(content)
        sections = self.parse_plan_sections(content)
        
        print(f"\n📋 Plan Summary: {title}")
        print("=" * 50)
        
        for section_name in sections:
            section_content = sections[section_name]
            # Show first few lines of each section
            lines = section_content.split('\n')[1:4]  # Skip the header line
            preview = ' '.join(line.strip() for line in lines if line.strip())
            if len(preview) > 100:
                preview = preview[:100] + "..."
            print(f"• {section_name}: {preview}")
    
    def show_help(self) -> None:
        """Display help for interactive session"""
        print("""
Available commands:
  • Just type what you want to change (e.g., "add user authentication")
  • 'show' or 'summary' - Display current plan
  • 'changes' - Show what's been modified this session  
  • 'revert' - Undo last change
  • 'done' or 'exit' - Save changes and exit
  • 'cancel' - Exit without saving
  • 'help' - Show this help

Examples:
  > Add user authentication with OAuth
  > Change the database from SQLite to PostgreSQL
  > Add mobile app support
  > Remove the admin dashboard feature
        """)

class InteractivePlanSession:
    """Manages an interactive plan update session"""
    
    def __init__(self, plan_path: Path, plan_manager: PlanManager):
        self.plan_path = plan_path
        self.plan_manager = plan_manager
        self.original_plan = plan_manager.load_plan(plan_path)
        self.current_plan = self.original_plan
        self.change_history = []
        self.crew_instance = plan_manager.get_crew_instance()
    
    def add_change(self, user_request: str, updated_plan: str) -> None:
        """Add a change to the history"""
        self.change_history.append({
            'request': user_request,
            'timestamp': datetime.now(),
            'previous_plan': self.current_plan,
            'updated_plan': updated_plan
        })
        self.current_plan = updated_plan
    
    def show_changes(self) -> None:
        """Display summary of all changes made this session"""
        if not self.change_history:
            print("No changes made this session.")
            return
        
        print(f"\nChanges made this session ({len(self.change_history)}):")
        for i, change in enumerate(self.change_history, 1):
            timestamp = change['timestamp'].strftime('%H:%M:%S')
            print(f"{i}. [{timestamp}] {change['request']}")
    
    def revert_last_change(self) -> bool:
        """Undo the most recent change"""
        if self.change_history:
            last_change = self.change_history.pop()
            self.current_plan = last_change['previous_plan']
            print(f"✅ Reverted: {last_change['request']}")
            return True
        else:
            print("❌ No changes to revert.")
            return False
    
    def process_update_request(self, user_request: str) -> bool:
        """Process a plan update request"""
        try:
            print("🤔 Analyzing request...")
            
            # Route to appropriate agent
            agent = self.crew_instance.route_update_request(user_request)
            agent_role = getattr(agent, 'role', 'Unknown')
            print(f"🎯 Agent: {agent_role}")
            
            # Assess and preview changes
            print("📊 Assessing feasibility and impact...")
            assessment = self.crew_instance.assess_and_preview_change(
                self.current_plan, user_request, agent
            )
            
            print(f"\n💡 Assessment: {assessment['assessment']}")
            if assessment['considerations']:
                print(f"🔍 Considerations: {assessment['considerations']}")
            if assessment['risks']:
                print(f"⚠️  Risks: {assessment['risks']}")
            
            # For now, we'll simulate the preview and update
            # In a full implementation, this would use the plan_update_task
            print("\n📝 Preview of changes:")
            print("(Simulated preview - full implementation would show actual diff)")
            
            # Confirm changes
            confirm = input("\nApply these changes? (y/n): ").strip().lower()
            
            if confirm == 'y':
                # For now, we'll just add a comment to the plan
                # In full implementation, this would use the crew to update the plan
                updated_plan = self.current_plan + f"\n\n<!-- Change applied: {user_request} -->"
                self.add_change(user_request, updated_plan)
                print("✅ Plan updated.")
                return True
            else:
                print("❌ Changes discarded.")
                return False
                
        except Exception as e:
            print(f"❌ Error processing request: {e}")
            return False
    
    def run(self) -> None:
        """Run the interactive session"""
        plan_title = self.plan_manager.extract_plan_title(self.current_plan)
        
        print(f"\n=== INTERACTIVE PLAN UPDATE SESSION ===")
        print(f"Current plan: {plan_title}")
        print("What would you like to change? (Type 'help' for commands)\n")
        
        while True:
            try:
                user_input = input("> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['done', 'exit']:
                    self.plan_manager.save_plan(self.current_plan, self.plan_path)
                    print(f"💾 Saving final plan to {self.plan_path}")
                    print(f"📊 Session summary: {len(self.change_history)} changes applied")
                    print("✨ Session complete.")
                    break
                    
                elif user_input.lower() == 'cancel':
                    print("❌ Session cancelled. No changes saved.")
                    break
                    
                elif user_input.lower() in ['show', 'summary']:
                    self.plan_manager.display_plan_summary(self.current_plan)
                    
                elif user_input.lower() == 'changes':
                    self.show_changes()
                    
                elif user_input.lower() == 'revert':
                    self.revert_last_change()
                    
                elif user_input.lower() == 'help':
                    self.plan_manager.show_help()
                    
                else:
                    # Process update request
                    self.process_update_request(user_input)
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Session interrupted. Type 'done' to save or 'cancel' to exit without saving.")
            except EOFError:
                print("\n\n❌ Session ended. No changes saved.")
                break