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
from typing import Dict
from dotenv import load_dotenv
from rscrew.crew import Rscrew
from rscrew.output_capture import capture_output
from rscrew.plan_manager import PlanManager, InteractivePlanSession

# Load environment variables from .env file
def load_environment():
    """Load environment variables from .env files in multiple locations"""
    # Try multiple .env file locations
    env_paths = [
        '.env',  # Current directory
        'rscrew/.env',  # rscrew subdirectory
        os.path.join(os.path.dirname(__file__), '../../.env'),  # Relative to this file
        os.path.expanduser('~/.rscrew/.env'),  # User home directory
    ]
    
    loaded = False
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            if os.getenv('RSCREW_DEBUG', 'false').lower() == 'true':
                print(f"[DEBUG] Loaded .env from: {env_path}")
            loaded = True
            break
    
    if not loaded and os.getenv('RSCREW_DEBUG', 'false').lower() == 'true':
        print("[DEBUG] No .env file found in standard locations")

# Load environment variables at module import
load_environment()


def detect_implementation_intent(user_request: str) -> Dict[str, Any]:
    """
    Detect if user request requires implementation vs advisory response.
    Used by dynamic agents to determine mode switching.
    """
    from rscrew.dynamic_agent import ContextDecisionEngine
    
    decision_engine = ContextDecisionEngine()
    analysis = decision_engine.analyze_request(user_request, {})
    
    return {
        'requires_implementation': analysis['mode'] in ['IMPLEMENTATION', 'HYBRID'],
        'implementation_confidence': analysis['confidence'],
        'implementation_mode': analysis['mode'],
        'risk_level': analysis['estimated_risk'],
        'specific_target': analysis['specific_target'],
        'requires_confirmation': analysis['requires_confirmation']
    }


def classify_request_intent(user_request: str, execution_context: str, force_classification: str = None) -> Dict[str, str]:
    """
    Classify user intent to determine appropriate workflow routing.
    Enhanced with dynamic implementation detection for advisory/implementation mode switching.
    
    Args:
        user_request (str): The user's original request
        execution_context (str): Context about where the command was executed
        force_classification (str): Optional forced classification ('info' or 'build')
        
    Returns:
        Dict[str, str]: Intent classification with confidence, routing, and implementation flags
    """
    request_lower = user_request.lower().strip()
    
    # Handle forced classification first
    if force_classification:
        if force_classification.lower() == 'info':
            return {
                "intent": "INFORMATION",
                "confidence": "Forced 1.00",
                "workflow": "Quick Response",
                "reasoning": "Classification forced to INFORMATION via -setClass flag"
            }
        elif force_classification.lower() == 'build':
            return {
                "intent": "IMPLEMENTATION", 
                "confidence": "Forced 1.00",
                "workflow": "Full Development",
                "reasoning": "Classification forced to IMPLEMENTATION via -setClass flag"
            }
    
    # Check for nonsense input (empty, random characters, no meaningful content)
    if not request_lower or len(request_lower.strip()) < 3:
        return {
            "intent": "NONSENSE",
            "confidence": "High 0.95",
            "workflow": "No Action",
            "reasoning": "Input too short or empty"
        }
    
    # Check for random characters/numbers (nonsense detection)
    import re
    # If mostly non-alphabetic characters or random patterns
    alpha_ratio = len(re.findall(r'[a-zA-Z]', request_lower)) / len(request_lower)
    if alpha_ratio < 0.3:  # Less than 30% alphabetic characters
        return {
            "intent": "NONSENSE",
            "confidence": "High 0.90",
            "workflow": "No Action", 
            "reasoning": "Input appears to be random characters or numbers"
        }
    
    # EMPHASIZE: If prompt is ALL questions, classify as INFORMATION
    # If prompt is ALL action statements, classify as IMPLEMENTATION
    # Split into sentences and also handle compound sentences with 'and'
    import re
    sentences = re.split(r'[.!?]+', request_lower)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Further split compound sentences connected by 'and' to handle mixed intents
    expanded_parts = []
    for sentence in sentences:
        # Split on 'and' but preserve context
        parts = re.split(r'\s+and\s+', sentence)
        if len(parts) > 1:
            # Check if this creates meaningful separate parts
            for part in parts:
                part = part.strip()
                if len(part) > 3:  # Ignore very short parts
                    expanded_parts.append(part)
        else:
            expanded_parts.append(sentence)
    
    if expanded_parts:
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can you', 'could you', 'would you', 'do you', 'is there', 'are there']
        action_words = ['build', 'create', 'develop', 'implement', 'code', 'write', 'program', 'make', 'construct', 'design']
        
        all_questions = True
        all_actions = True
        question_count = 0
        action_count = 0
        vague_count = 0
        
        for part in expanded_parts:
            part = part.strip()
            if len(part) > 0:
                # Check if part is a question
                is_question = (
                    any(part.startswith(qw) for qw in question_words) or
                    part.endswith('?') or
                    '?' in part or
                    any(qw in part for qw in ['what', 'how', 'why', 'when', 'where', 'who', 'which'])
                )
                
                # Check if part is an action/command (exclude vague suggestions)
                # First check for vague/hypothetical language that should NOT be treated as actions
                vague_indicators = ['maybe', 'might', 'could', 'perhaps', 'possibly', 'what if', 'how about']
                is_vague = any(indicator in part for indicator in vague_indicators)
                
                if is_vague:
                    is_action = False  # Vague suggestions are not concrete actions
                else:
                    is_action = (
                        any(part.startswith(aw) for aw in action_words) or
                        any(keyword in part for keyword in ['build me', 'create a', 'develop a', 'implement a', 'write a', 'make a', 'code a', 'create one', 'build one', 'make one', 'please build', 'please create', 'please make']) or
                        any(aw in part for aw in action_words if not is_vague)  # Only if not vague
                    )
                
                if is_question:
                    question_count += 1
                    all_actions = False
                elif is_action:
                    action_count += 1
                    all_questions = False
                elif is_vague:
                    vague_count += 1
                    all_questions = False
                    all_actions = False
                else:
                    # Neither question, action, nor vague - neutral content
                    all_questions = False
                    all_actions = False
        
        # If there are ANY action items in the prompt → check confidence thresholds
        if action_count > 0:
            # Calculate confidence based on action count and clarity
            base_confidence = 0.65 if action_count == 1 else (0.8 if action_count == 2 else 0.9)
            
            # Reduce confidence for mixed content (questions + actions)
            if question_count > 0 and action_count > 0:
                # More significant reduction for mixed content
                if question_count >= action_count * 2:  # Many more questions than actions
                    action_confidence = base_confidence * 0.3  # Very low confidence
                else:
                    action_confidence = base_confidence * 0.7  # Moderate reduction
            else:
                action_confidence = base_confidence
            
            # Apply confidence thresholds per prompt 17 requirements
            if action_confidence < 0.20:
                return {
                    "intent": "NONSENSE",
                    "confidence": f"Low {action_confidence:.2f}",
                    "workflow": "No Action",
                    "reasoning": f"Action confidence {action_confidence:.2f} below 0.20 threshold, classified as nonsense"
                }
            elif action_confidence < 0.60:
                return {
                    "intent": "INFORMATION",
                    "confidence": f"Medium {action_confidence:.2f}",
                    "workflow": "Quick Response",
                    "reasoning": f"Action confidence {action_confidence:.2f} below 0.60 threshold, defaulting to INFORMATION"
                }
            else:
                return {
                    "intent": "IMPLEMENTATION",
                    "confidence": f"High {action_confidence:.2f}" if action_confidence >= 0.75 else f"Medium {action_confidence:.2f}",
                    "workflow": "Full Development",
                    "reasoning": "Contains action statements with sufficient confidence - classified as implementation request"
                }
        
        # Classify as INFORMATION if we have questions and no concrete actions
        if question_count > 0 and action_count == 0:
            return {
                "intent": "INFORMATION",
                "confidence": "High 0.85",
                "workflow": "Quick Response",
                "reasoning": "All sentences are questions - classified as information request"
            }
        
        # Handle vague-only content (no concrete actions or questions)
        if action_count == 0 and question_count == 0 and vague_count > 0:
            return {
                "intent": "INFORMATION",
                "confidence": "Low 0.30",
                "workflow": "Quick Response",
                "reasoning": "Contains only vague suggestions without concrete actions or questions - classified as information request"
            }
    
    # Information request indicators (including analysis, reports, general info gathering)
    info_keywords = [
        'what is', 'how does', 'explain', 'what are the differences', 'compare',
        'why should i', 'pros and cons', 'advantages', 'disadvantages', 'benefits',
        'what are', 'how do', 'tell me about', 'describe', 'definition of',
        'analyze', 'analysis', 'summary', 'summarize', 'overview', 'review', 'examine',
        'generate report', 'create report', 'report on', 'information about',
        'research', 'investigate', 'study', 'explore', 'understand'
    ]
    
    # Planning request indicators  
    planning_keywords = [
        'what\'s the best approach', 'how should i', 'what would you recommend',
        'what technologies should', 'help me plan', 'what strategy', 'best practices',
        'how to structure', 'what framework', 'which tool', 'advice for'
    ]
    
    # Implementation request indicators (ONLY for actual building/coding actions)
    # EXCLUDE report generation, analysis, and information gathering
    implementation_keywords = [
        'build', 'create', 'develop', 'implement', 'code', 'write', 'program',
        'make', 'construct', 'design and build', 'build me', 'create a program', 
        'write code for', 'develop an application', 'code a', 'program a', 
        'build an app', 'create software', 'develop software', 'write a script', 
        'build a system', 'create a tool', 'develop a tool'
    ]
    
    # Count matches
    info_matches = sum(1 for keyword in info_keywords if keyword in request_lower)
    planning_matches = sum(1 for keyword in planning_keywords if keyword in request_lower)
    implementation_matches = sum(1 for keyword in implementation_keywords if keyword in request_lower)
    
    # Calculate confidence scores (0.0 to 1.0)
    total_matches = info_matches + planning_matches + implementation_matches
    max_matches = max(info_matches, planning_matches, implementation_matches)
    
    # Base confidence calculation
    if max_matches == 0:
        confidence_score = 0.15  # Very low confidence for unclear requests
    elif max_matches == 1:
        confidence_score = 0.65  # Medium confidence for single match
    elif max_matches == 2:
        confidence_score = 0.8   # High confidence for double match
    else:
        confidence_score = 0.9   # Very high confidence for multiple matches
    
    # Adjust confidence based on competing signals
    if total_matches > max_matches:  # Mixed signals reduce confidence
        confidence_score *= 0.85
    
    # Check for nonsense classification threshold (updated to 0.20 per prompt 17)
    info_confidence = confidence_score if info_matches == max_matches else confidence_score * 0.5
    build_confidence = confidence_score if implementation_matches == max_matches else confidence_score * 0.5
    
    if info_confidence < 0.20 and build_confidence < 0.20:
        return {
            "intent": "NONSENSE",
            "confidence": f"Low {max(info_confidence, build_confidence):.2f}",
            "workflow": "No Action",
            "reasoning": "Both info and build confidence below 0.20 threshold"
        }
    
    # Determine intent with updated logic per prompt 17
    if info_matches > planning_matches and info_matches > implementation_matches:
        intent = "INFORMATION"
        confidence = f"High {confidence_score:.2f}" if confidence_score >= 0.75 else f"Medium {confidence_score:.2f}"
        workflow = "Quick Response"
        reasoning = f"Request contains {info_matches} information-seeking keywords"
    elif planning_matches > implementation_matches:
        intent = "PLANNING"
        confidence = f"High {confidence_score:.2f}" if confidence_score >= 0.75 else f"Medium {confidence_score:.2f}"
        workflow = "Strategic Planning"
        reasoning = f"Request contains {planning_matches} planning/strategy keywords"
    elif implementation_matches > 0:
        # Apply new logic: implementation confidence below 0.6 → INFORMATION, below 0.2 → NONSENSE
        if build_confidence < 0.20:
            intent = "NONSENSE"
            confidence = f"Low {build_confidence:.2f}"
            workflow = "No Action"
            reasoning = f"Implementation confidence {build_confidence:.2f} below 0.20 threshold, classified as nonsense"
        elif build_confidence < 0.60:
            intent = "INFORMATION"
            confidence = f"Medium {build_confidence:.2f}"
            workflow = "Quick Response"
            reasoning = f"Implementation confidence {build_confidence:.2f} below 0.60 threshold, defaulting to INFORMATION"
        else:
            intent = "IMPLEMENTATION"
            confidence = f"High {confidence_score:.2f}" if confidence_score >= 0.75 else f"Medium {confidence_score:.2f}"
            workflow = "Full Development"
            reasoning = f"Request contains {implementation_matches} implementation keywords with sufficient confidence"
    else:
        # Default to information for unclear requests
        intent = "INFORMATION"
        confidence = f"Low {confidence_score:.2f}"
        workflow = "Quick Response"
        reasoning = "No clear intent indicators found, defaulting to information request"
    
    # Add implementation detection for dynamic agent mode switching
    implementation_analysis = detect_implementation_intent(user_request)
    
    return {
        "intent": intent,
        "confidence": confidence,
        "workflow": workflow,
        "reasoning": reasoning,
        # Dynamic implementation detection
        "requires_implementation": implementation_analysis['requires_implementation'],
        "implementation_mode": implementation_analysis['implementation_mode'],
        "implementation_confidence": implementation_analysis['implementation_confidence'],
        "risk_level": implementation_analysis['risk_level'],
        "specific_target": implementation_analysis['specific_target'],
        "requires_confirmation": implementation_analysis['requires_confirmation']
    }


import subprocess
import tempfile
import shutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.spinner import Spinner
from rich.live import Live
from rich.text import Text
import select
import fcntl

# Initialize rich console
console = Console()

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
        
        # Classify intent to determine appropriate workflow
        debug_print("Classifying user intent...")
        intent_result = classify_request_intent(user_prompt, execution_context)
        debug_print(f"Intent classification: {intent_result['intent']} (confidence: {intent_result['confidence']})")
        debug_print(f"Reasoning: {intent_result['reasoning']}")
        
        # Enhanced: Check for implementation requirements
        debug_print(f"Implementation analysis:")
        debug_print(f"  - Requires implementation: {intent_result.get('requires_implementation', False)}")
        debug_print(f"  - Implementation mode: {intent_result.get('implementation_mode', 'ADVISORY')}")
        debug_print(f"  - Risk level: {intent_result.get('risk_level', 'LOW')}")
        debug_print(f"  - Specific target: {intent_result.get('specific_target', False)}")
        
        # Store implementation context for agents
        inputs['implementation_context'] = {
            'requires_implementation': intent_result.get('requires_implementation', False),
            'implementation_mode': intent_result.get('implementation_mode', 'ADVISORY'),
            'risk_level': intent_result.get('risk_level', 'LOW'),
            'specific_target': intent_result.get('specific_target', False),
            'requires_confirmation': intent_result.get('requires_confirmation', False)
        }
        
        # Route to appropriate workflow based on intent
        if intent_result["intent"] == "INFORMATION":
            # Determine if enhanced workflow is needed based on domain complexity
            if hasattr(crew_instance, 'detect_domain_expertise_needed'):
                relevant_domains = crew_instance.detect_domain_expertise_needed(user_prompt)
                
                if relevant_domains and hasattr(crew_instance, 'run_enhanced_information_workflow'):
                    debug_print(f"Routing to enhanced information workflow for domains: {relevant_domains}")
                    result = crew_instance.run_enhanced_information_workflow(inputs)
                    debug_print("Enhanced information workflow completed")
                elif hasattr(crew_instance, 'run_information_workflow'):
                    debug_print("Routing to simple information workflow...")
                    result = crew_instance.run_information_workflow(inputs)
                    debug_print("Simple information workflow completed")
                else:
                    debug_print("Information workflows not implemented, falling back to interactive dialogue...")
                    result = crew_instance.run_with_interactive_dialogue(inputs)
                    debug_print("Interactive workflow completed")
            else:
                # Fallback to simple information workflow if domain detection not available
                debug_print("Domain detection not available, routing to simple information workflow...")
                if hasattr(crew_instance, 'run_information_workflow'):
                    result = crew_instance.run_information_workflow(inputs)
                    debug_print("Simple information workflow completed")
                else:
                    debug_print("Information workflow not implemented, falling back to interactive dialogue...")
                    result = crew_instance.run_with_interactive_dialogue(inputs)
                    debug_print("Interactive workflow completed")
        else:
            debug_print("Routing to full interactive dialogue workflow...")
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

def run_test_with_progress(cmd, test_name, timeout=600, verbose=False, debug=False):
    """Run a test command with real-time progress indication and optional verbose/debug output"""
    start_time = time.time()
    
    # Debug mode: show command details
    if debug:
        console.print(f"[dim][DEBUG] Command: {' '.join(cmd)}[/dim]")
        console.print(f"[dim][DEBUG] Working directory: {os.getcwd()}[/dim]")
        console.print(f"[dim][DEBUG] Timeout: {timeout}s[/dim]")
    
    # Verbose mode: show test start
    if verbose:
        console.print(f"[bold blue]Starting {test_name} test...[/bold blue]")
    
    # Set up environment for debug mode and test mode
    env = os.environ.copy()
    env['RSCREW_TEST_MODE'] = 'true'  # Enable test mode for automated responses
    if debug:
        env['RSCREW_DEBUG'] = 'true'
        console.print(f"[dim][DEBUG] Environment: RSCREW_DEBUG=true[/dim]")
    
    # Prepare for real-time output capture
    output_lines = []
    error_lines = []
    
    try:
        # Start the subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        
        if debug:
            console.print(f"[dim][DEBUG] Process PID: {process.pid}[/dim]")
        
        # Create spinner for progress indication
        spinner_text = f"Running {test_name} test..."
        
        def update_spinner_text(elapsed):
            return f"Running {test_name} test... ({elapsed:.0f}s elapsed)"
        
        # Real-time output processing
        with Live(console=console, refresh_per_second=4) as live:
            spinner = Spinner("dots", text=spinner_text)
            live.update(spinner)
            
            # Make stdout and stderr non-blocking
            import fcntl
            fd_stdout = process.stdout.fileno()
            fd_stderr = process.stderr.fileno()
            fl_stdout = fcntl.fcntl(fd_stdout, fcntl.F_GETFL)
            fl_stderr = fcntl.fcntl(fd_stderr, fcntl.F_GETFL)
            fcntl.fcntl(fd_stdout, fcntl.F_SETFL, fl_stdout | os.O_NONBLOCK)
            fcntl.fcntl(fd_stderr, fcntl.F_SETFL, fl_stderr | os.O_NONBLOCK)
            
            while process.poll() is None:
                elapsed = time.time() - start_time
                
                # Check for timeout
                if elapsed > timeout:
                    process.terminate()
                    process.wait(timeout=5)
                    return TestResult(test_name, False, elapsed, "", f"Test timed out after {timeout} seconds")
                
                # Update spinner with elapsed time
                spinner.text = update_spinner_text(elapsed)
                live.update(spinner)
                
                # Read available output
                try:
                    stdout_data = process.stdout.read()
                    if stdout_data:
                        lines = stdout_data.split('\n')
                        for line in lines:
                            if line.strip():
                                output_lines.append(line)
                                if verbose:
                                    console.print(f"[dim]  {line}[/dim]")
                                elif debug:
                                    console.print(f"[dim][OUT] {line}[/dim]")
                except:
                    pass
                
                try:
                    stderr_data = process.stderr.read()
                    if stderr_data:
                        lines = stderr_data.split('\n')
                        for line in lines:
                            if line.strip():
                                error_lines.append(line)
                                if verbose:
                                    console.print(f"[dim red]  {line}[/dim red]")
                                elif debug:
                                    console.print(f"[dim red][ERR] {line}[/dim red]")
                except:
                    pass
                
                time.sleep(0.1)
            
            # Final read of any remaining output
            try:
                remaining_stdout = process.stdout.read()
                if remaining_stdout:
                    for line in remaining_stdout.split('\n'):
                        if line.strip():
                            output_lines.append(line)
                            if verbose or debug:
                                prefix = "[OUT]" if debug else ""
                                console.print(f"[dim]{prefix} {line}[/dim]")
            except:
                pass
            
            try:
                remaining_stderr = process.stderr.read()
                if remaining_stderr:
                    for line in remaining_stderr.split('\n'):
                        if line.strip():
                            error_lines.append(line)
                            if verbose or debug:
                                prefix = "[ERR]" if debug else ""
                                console.print(f"[dim red]{prefix} {line}[/dim red]")
            except:
                pass
        
        # Calculate final duration
        duration = time.time() - start_time
        
        # Combine output
        full_output = '\n'.join(output_lines + error_lines)
        
        if debug:
            console.print(f"[dim][DEBUG] Process completed with exit code: {process.returncode}[/dim]")
            console.print(f"[dim][DEBUG] Output length: {len(full_output)} characters[/dim]")
            console.print(f"[dim][DEBUG] Duration: {duration:.1f}s[/dim]")
        
        # Validate output
        passed, validation_msg = validate_test_output(test_name, full_output, duration)
        
        if debug:
            console.print(f"[dim][DEBUG] Validation result: {passed} - {validation_msg}[/dim]")
        
        if not passed:
            return TestResult(test_name, False, duration, full_output, validation_msg)
        
        # Check exit code
        if process.returncode != 0:
            return TestResult(test_name, False, duration, full_output, f"Non-zero exit code: {process.returncode}")
        
        return TestResult(test_name, True, duration, full_output)
        
    except Exception as e:
        duration = time.time() - start_time
        if debug:
            console.print(f"[dim red][DEBUG] Exception: {str(e)}[/dim red]")
        return TestResult(test_name, False, duration, "", f"Test execution error: {str(e)}")

def run_single_test(test_name, timeout=600, verbose=False, debug=False):
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
            # Basic test should run in project directory, not empty temp directory
            os.chdir(original_cwd)  # Go back to project directory
            prompt = (assets_dir / "basic_prompt.txt").read_text().strip()
            cmd = ["rc", prompt]
        
        elif test_name == "simple":
            prompt = (assets_dir / "simple_prompt.txt").read_text().strip()
            cmd = ["rc", prompt]
        
        elif test_name == "quick":
            prompt = (assets_dir / "quick_prompt.txt").read_text().strip()
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
        
        # Run the test command with progress indication
        if verbose or debug:
            # Use enhanced progress system
            return run_test_with_progress(cmd, test_name, timeout, verbose, debug)
        else:
            # Use simple progress with spinner
            try:
                # Set up environment for test mode
                env = os.environ.copy()
                env['RSCREW_TEST_MODE'] = 'true'  # Enable test mode for automated responses
                
                with console.status(f"Running {test_name} test...", spinner="dots"):
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        cwd=test_dir,
                        env=env
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

def run_test_command(test_type=None, details=False, clean=False, verbose=False, debug=False):
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
    available_tests = ["quick", "simple", "basic", "plan", "build", "update", "file"]
    
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
                executor.submit(run_single_test, test, 600, verbose, debug): test 
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
            if not (verbose or debug):
                print(f"Running {test} test...")
            result = run_single_test(test, 600, verbose, debug)
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

def run_classification(prompt_text, file_path, set_class=None):
    """
    Classify prompt intent and show workflow routing without execution.
    Updated to support -setClass flag per prompt 15 requirements.
    """
    try:
        # Get prompt text
        if file_path:
            if not os.path.exists(file_path):
                print(f"❌ Error: File not found: {file_path}")
                return
            with open(file_path, 'r', encoding='utf-8') as f:
                prompt_text = f.read().strip()
        
        if not prompt_text:
            print("❌ Error: No prompt text provided")
            return
        
        # Classify the request with optional forced classification
        execution_context = f"Classification mode in {os.getcwd()}"
        classification = classify_request_intent(prompt_text, execution_context, set_class)
        
        intent = classification["intent"]
        confidence = classification["confidence"]
        reasoning = classification["reasoning"]
        
        # Determine workflow
        if intent == "INFORMATION":
            workflow = "Information Workflow (Fast)"
            description = "Single research analyst, direct response, no interactive dialogue"
        elif intent == "PLANNING":
            workflow = "Strategic Planning Workflow"
            description = "Planning crew for strategic advice and recommendations"
        elif intent == "IMPLEMENTATION":
            workflow = "Interactive Dialogue Workflow (Full)"
            description = "Full crew with operator dialogue and complex task handling"
        elif intent == "NONSENSE":
            workflow = "No Action"
            description = "Input appears to be nonsense or invalid - no workflow executed"
        else:
            workflow = "Interactive Dialogue Workflow (Full)"
            description = "Full crew with operator dialogue and complex task handling"
        
        # Display results
        print("🔍 Intent Classification Results")
        print("=" * 40)
        print(f"Prompt: {prompt_text[:100]}{'...' if len(prompt_text) > 100 else ''}")
        print(f"Intent: {intent}")
        print(f"Confidence: {confidence}")
        print(f"Reasoning: {reasoning}")
        print(f"Workflow: {workflow}")
        print(f"Description: {description}")
        if set_class:
            print(f"Override: Classification forced via -setClass {set_class}")
        print("=" * 40)
        
    except Exception as e:
        print(f"❌ Error during classification: {str(e)}")

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
  rc -test                                     Run quick test (default - math question)
  rc -test quick                              Run ultra-fast simple test (math question)
  rc -test simple                             Run medium complexity test (Python explanation)
  rc -test basic                              Run complex test (directory analysis)
  rc -test plan                               Test plan generation functionality
  rc -test build                              Test build implementation functionality
  rc -test update                             Test update functionality
  rc -test file                               Test file input functionality
  rc -test all                                Run all tests in parallel
  rc -test --clean                            Clean up test generated files
  rc -check                                   System health check

Classification System:
  rc -class "What is 2 + 2?"                 Classify prompt intent and show workflow routing
  rc -class -f /path/to/prompt.txt            Classify prompt from file
  rc -class "Build me an app" -setClass info  Force classification to info (override)
  rc -class "What is Python?" -setClass build Force classification to build (override)

Planning System:
  rc -plan "Build a web app" [-name my_app]   Generate implementation plan
  rc -build /path/to/plan.md                  Implement from plan
  rc -update /path/to/plan.md                 Interactive plan updates

Primary Mode (Default):
  rc "Your prompt here"                       Direct crew execution
  rc -f /path/to/prompt.txt                   Read prompt from file

Examples:
  rc -test quick                              # Ultra-fast test (math question)
  rc -test simple -v                          # Medium test with verbose output
  rc -test basic                              # Complex test (directory analysis)
  rc -test all                                # Run comprehensive test suite
  rc -test quick -v -d                        # Quick test with full debug output
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
        const='quick',
        help='Run test commands: quick, simple, basic, plan, build, update, file, all'
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
        '-v', '--verbose',
        action='store_true',
        help='Show detailed progress during test execution'
    )
    
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug mode for test execution'
    )
    
    parser.add_argument(
        '-check',
        action='store_true', 
        help='System health check'
    )
    
    parser.add_argument(
        '-class',
        nargs='?',
        const='',
        help='Classify prompt intent and show workflow routing (no execution)'
    )
    
    parser.add_argument(
        '-setClass',
        choices=['info', 'build'],
        help='Force classification to specific type (info or build) - use with -class'
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
        run_test_command(test_type=args.test, details=args.details, clean=args.clean, 
                        verbose=args.verbose, debug=args.debug)
    elif args.check:
        run_quick_check()
    # Classification system
    elif getattr(args, 'class') is not None:
        run_classification(getattr(args, 'class'), args.file, args.setClass)
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
        print("  rc -test -v                              # Test with verbose progress")
        print("  rc -test -d                              # Test with debug output")
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