import os
import logging
import time
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.llm import LLM
from typing import List, Dict, Any
from rscrew.tools.custom_tool import (
    ReadFile, WriteFile, ListDirectory, FindFiles, GetFileInfo
)
from rscrew.tools.programming_tools import (
    OperatorIntentTools, ProjectManagementTools, TechnicalResearchTools, ArchitectureTools,
    DevelopmentTools, QualityAssuranceTools, DocumentationTools
)
from rscrew.interactive_dialogue import conduct_operator_dialogue
from rscrew.tenacity_llm_handler import apply_tenacity_error_handling_to_agents, check_tenacity_installation
from rscrew.model_manager import create_llm_with_smart_routing, get_model_manager

# Load environment variables from .env file
def load_environment():
    """Load environment variables from .env files in multiple locations"""
    env_paths = [
        '.env',  # Current directory
        'rscrew/.env',  # rscrew subdirectory  
        os.path.join(os.path.dirname(__file__), '../../.env'),  # Relative to this file
        os.path.expanduser('~/.rscrew/.env'),  # User home directory
    ]
    
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            if os.getenv('RSCREW_DEBUG', 'false').lower() == 'true':
                print(f"[DEBUG] Loaded .env from: {env_path}")
            return True
    return False

# Load environment variables at module import
load_environment()

# Version information for deployment tracking
RSCREW_VERSION = "v3.1-tenacity-hybrid"
RSCREW_FEATURES = ["tenacity-retry-logic", "context-aware-fallbacks", "debug-monitoring", "programming-assistant-crew"]
RSCREW_COMMIT = "programming-assistant"  # Full programming assistant crew implementation

# Debug toggle - only enabled when explicitly set to 'true'
DEBUG_MODE = os.getenv('RSCREW_DEBUG', 'false').lower() == 'true'

# Rate limiting variables
_last_call_time = 0.0
_min_call_interval = float(os.getenv('RSCREW_LLM_MIN_INTERVAL', '0.5'))

def debug_print(message):
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

def apply_rate_limiting():
    """Apply rate limiting to prevent API overload"""
    global _last_call_time
    current_time = time.time()
    time_since_last_call = current_time - _last_call_time
    
    if time_since_last_call < _min_call_interval:
        sleep_time = _min_call_interval - time_since_last_call
        if DEBUG_MODE:
            debug_print(f"Rate limiting: sleeping for {sleep_time:.3f}s")
        time.sleep(sleep_time)
    
    _last_call_time = time.time()

# Legacy LLM creation functions removed - now handled by centralized model manager

def apply_llm_monitoring_and_rate_limiting(llm, agent_name: str, provider: str):
    """Apply monitoring and rate limiting to an LLM instance"""
    
    try:
        # Fix LLM call method - ensure proper method binding and error handling
        if llm and hasattr(llm, 'call'):
            original_call = llm.call
            
            def fixed_call(*args, **kwargs):
                if DEBUG_MODE:
                    debug_print(f"=== {provider} LLM Call Intercepted ({agent_name} - {RSCREW_VERSION}) ===")
                    debug_print(f"Provider: {provider}")
                    debug_print(f"Features Active: {', '.join(RSCREW_FEATURES)}")
                    debug_print(f"Args count: {len(args)}")
                    debug_print(f"Kwargs keys: {list(kwargs.keys()) if kwargs else 'None'}")
                    if args:
                        debug_print(f"Prompt length: {len(str(args[0])) if args[0] else 0}")
                        debug_print(f"Prompt type: {type(args[0])}")
                        if isinstance(args[0], list):
                            debug_print(f"Prompt is list with {len(args[0])} items")
                            for i, item in enumerate(args[0][:3]):  # Show first 3 items
                                debug_print(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
                        else:
                            debug_print(f"Prompt preview: {str(args[0])[:200]}..." if args[0] and len(str(args[0])) > 200 else str(args[0]))
                
                try:
                    # Ensure we have valid arguments
                    if not args or args[0] is None:
                        if DEBUG_MODE:
                            debug_print(f"WARNING: Empty or None prompt detected ({agent_name})")
                        return ""
                    
                    # Apply rate limiting
                    apply_rate_limiting()
                    
                    result = original_call(*args, **kwargs)
                    
                    # Ensure we return a valid result (convert None to empty string)
                    if result is None:
                        if DEBUG_MODE:
                            debug_print(f"WARNING: LLM returned None, converting to empty string ({agent_name})")
                        result = ""
                    
                    if DEBUG_MODE:
                        debug_print(f"LLM call result type: {type(result)}")
                        debug_print(f"LLM call result length: {len(str(result)) if result else 0}")
                        debug_print(f"LLM call result preview: {str(result)[:200]}..." if result and len(str(result)) > 200 else str(result))
                        debug_print(f"=== End LLM Call ({agent_name}) ===")
                    return result
                except Exception as e:
                    if DEBUG_MODE:
                        debug_print(f"LLM call failed ({agent_name}): {e}")
                        debug_print(f"Exception type: {type(e)}")
                        debug_print(f"=== End LLM Call ({agent_name} - Failed) ===")
                    raise
            
            llm.call = fixed_call
            
    except Exception as e:
        debug_print(f"ERROR creating LLM for {agent_name}: {e}")
        llm = None
    
    return llm

# Set up logging for CrewAI internals (but suppress verbose LiteLLM logs)
if DEBUG_MODE:
    logging.basicConfig(level=logging.INFO)  # Changed from DEBUG to INFO
    # Suppress verbose LiteLLM logging
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    debug_print("Debug mode enabled")
    debug_print(f"=== RSCrew Version Info ===")
    debug_print(f"Version: {RSCREW_VERSION}")
    debug_print(f"Features: {', '.join(RSCREW_FEATURES)}")
    debug_print(f"Commit: {RSCREW_COMMIT}")
    debug_print("=============================")

# Debug: Check environment variables
debug_print("=== Environment Check ===")
debug_print(f"ANTHROPIC_API_KEY exists: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
debug_print(f"ANTHROPIC_API_KEY length: {len(os.getenv('ANTHROPIC_API_KEY', ''))}")
debug_print("==========================")
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class Rscrew():
    """Rscrew crew"""
    
    agents: List[BaseAgent]
    tasks: List[Task]
    
    def __init__(self):
        debug_print("=== Initializing Rscrew Class ===")
        try:
            super().__init__()
            debug_print("Rscrew class initialized successfully")
        except Exception as e:
            debug_print(f"Error initializing Rscrew class: {e}")
            raise
        debug_print("===================================")

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def operator_intent_interpreter(self) -> Agent:
        debug_print("=== Creating Operator Intent Interpreter Agent ===")
        
        llm = create_llm_with_smart_routing("operator_intent_interpreter")
        
        agent = Agent(
            config=self.agents_config['operator_intent_interpreter'], # type: ignore[index]
            tools=[
                OperatorIntentTools.analyze_request_for_context_gaps,
                OperatorIntentTools.generate_contextual_question,
                OperatorIntentTools.synthesize_operator_context
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Operator Intent Interpreter created with role: {getattr(agent, 'role', 'Unknown').strip()}")
        debug_print(f"Tools: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in agent.tools]}")
        debug_print("=====================================================")
        return agent

    @agent
    def project_orchestrator(self) -> Agent:
        debug_print("=== Creating Project Orchestrator Agent ===")
        llm = create_llm_with_smart_routing("project_orchestrator")
        
        agent = Agent(
            config=self.agents_config['project_orchestrator'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                ProjectManagementTools.classify_user_intent,
                ProjectManagementTools.analyze_project_scope,
                ProjectManagementTools.create_task_breakdown
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Project Orchestrator created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("===========================================")
        return agent

    @agent
    def research_analyst(self) -> Agent:
        debug_print("=== Creating Research Analyst Agent ===")
        llm = create_llm_with_smart_routing("research_analyst")
        
        agent = Agent(
            config=self.agents_config['research_analyst'], # type: ignore[index]
            tools=[
                ReadFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                TechnicalResearchTools.analyze_codebase_structure,
                TechnicalResearchTools.research_technology_stack
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Research Analyst created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("========================================")
        return agent

    @agent
    def solution_architect(self) -> Agent:
        debug_print("=== Creating Solution Architect Agent ===")
        llm = create_llm_with_smart_routing("solution_architect")
        
        agent = Agent(
            config=self.agents_config['solution_architect'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                ArchitectureTools.design_system_architecture,
                ArchitectureTools.create_api_specification
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Solution Architect created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("==========================================")
        return agent

    @agent
    def code_implementer(self) -> Agent:
        debug_print("=== Creating Code Implementer Agent ===")
        llm = create_llm_with_smart_routing("code_implementer")
        
        agent = Agent(
            config=self.agents_config['code_implementer'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                DevelopmentTools.generate_project_structure,
                DevelopmentTools.create_code_template
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Code Implementer created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("========================================")
        return agent

    @agent
    def quality_assurance(self) -> Agent:
        debug_print("=== Creating Quality Assurance Agent ===")
        llm = create_llm_with_smart_routing("quality_assurance")
        
        agent = Agent(
            config=self.agents_config['quality_assurance'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                QualityAssuranceTools.create_test_plan,
                QualityAssuranceTools.perform_code_review
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Quality Assurance created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("=========================================")
        return agent

    @agent
    def technical_writer(self) -> Agent:
        debug_print("=== Creating Technical Writer Agent ===")
        llm = create_llm_with_smart_routing("technical_writer")
        
        agent = Agent(
            config=self.agents_config['technical_writer'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                DocumentationTools.generate_api_documentation,
                DocumentationTools.create_user_guide
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Technical Writer created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("========================================")
        return agent

    # Specialized Planning Agents for Flag-Based System
    @agent
    def security_architecture_specialist(self) -> Agent:
        debug_print("=== Creating Security Architecture Specialist Agent ===")
        llm = create_llm_with_smart_routing("security_architecture_specialist")
        
        agent = Agent(
            config=self.agents_config['security_architecture_specialist'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                ArchitectureTools.design_system_architecture,
                ArchitectureTools.create_api_specification
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Security Architecture Specialist created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("========================================================")
        return agent

    @agent
    def database_architecture_specialist(self) -> Agent:
        debug_print("=== Creating Database Architecture Specialist Agent ===")
        llm = create_llm_with_smart_routing("database_architecture_specialist")
        
        agent = Agent(
            config=self.agents_config['database_architecture_specialist'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                ArchitectureTools.design_system_architecture,
                TechnicalResearchTools.research_technology_stack
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Database Architecture Specialist created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("========================================================")
        return agent

    @agent
    def frontend_architecture_specialist(self) -> Agent:
        debug_print("=== Creating Frontend Architecture Specialist Agent ===")
        llm = create_llm_with_smart_routing("frontend_architecture_specialist")
        
        agent = Agent(
            config=self.agents_config['frontend_architecture_specialist'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                ArchitectureTools.design_system_architecture,
                DevelopmentTools.create_code_template
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Frontend Architecture Specialist created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("=======================================================")
        return agent

    @agent
    def infrastructure_specialist(self) -> Agent:
        debug_print("=== Creating Infrastructure Specialist Agent ===")
        llm = create_llm_with_smart_routing("infrastructure_specialist")
        
        agent = Agent(
            config=self.agents_config['infrastructure_specialist'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                ArchitectureTools.design_system_architecture,
                DevelopmentTools.generate_project_structure
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Infrastructure Specialist created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("=================================================")
        return agent

    @agent
    def feature_analyst(self) -> Agent:
        debug_print("=== Creating Feature Analyst Agent ===")
        llm = create_llm_with_smart_routing("feature_analyst")
        
        agent = Agent(
            config=self.agents_config['feature_analyst'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                ProjectManagementTools.analyze_project_scope,
                TechnicalResearchTools.research_technology_stack
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Feature Analyst created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("=======================================")
        return agent

    @agent
    def plan_update_coordinator(self) -> Agent:
        debug_print("=== Creating Plan Update Coordinator Agent ===")
        llm = create_llm_with_smart_routing("plan_update_coordinator")
        
        agent = Agent(
            config=self.agents_config['plan_update_coordinator'], # type: ignore[index]
            tools=[
                ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo(),
                ProjectManagementTools.analyze_project_scope,
                ArchitectureTools.design_system_architecture
            ],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Plan Update Coordinator created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print("===============================================")
        return agent

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
# NOTE: operator_intent_dialogue_task is now handled by interactive_dialogue.py 
# before the CrewAI workflow starts. This ensures proper CLI interaction.

    @task
    def intent_classification_task(self) -> Task:
        debug_print("=== Creating Intent Classification Task ===")
        task = Task(
            config=self.tasks_config['intent_classification_task'], # type: ignore[index]
            agent=self.project_orchestrator()
        )
        debug_print(f"Intent Classification task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("===========================================")
        return task

    @task
    def research_task(self) -> Task:
        debug_print("=== Creating Research Task (Information Mode) ===")
        task = Task(
            config=self.tasks_config['research_task'], # type: ignore[index]
            agent=self.research_analyst()
        )
        debug_print(f"Research task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("=================================================")
        return task

    @task
    def information_response_task(self) -> Task:
        debug_print("=== Creating Information Response Task ===")
        task = Task(
            config=self.tasks_config['information_response_task'], # type: ignore[index]
            agent=self.technical_writer(),
            output_file='information_response.md'
        )
        debug_print(f"Information Response task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("==========================================")
        return task

    @task
    def project_analysis_task(self) -> Task:
        debug_print("=== Creating Project Analysis Task ===")
        task = Task(
            config=self.tasks_config['project_analysis_task'], # type: ignore[index]
            agent=self.project_orchestrator()
        )
        debug_print(f"Project Analysis task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("=======================================")
        return task

    @task
    def technical_research_task(self) -> Task:
        debug_print("=== Creating Technical Research Task ===")
        task = Task(
            config=self.tasks_config['technical_research_task'], # type: ignore[index]
            agent=self.research_analyst()
        )
        debug_print(f"Technical Research task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("========================================")
        return task

    @task
    def solution_design_task(self) -> Task:
        debug_print("=== Creating Solution Design Task ===")
        task = Task(
            config=self.tasks_config['solution_design_task'], # type: ignore[index]
            agent=self.solution_architect()
        )
        debug_print(f"Solution Design task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("======================================")
        return task

    @task
    def implementation_task(self) -> Task:
        debug_print("=== Creating Implementation Task ===")
        task = Task(
            config=self.tasks_config['implementation_task'], # type: ignore[index]
            agent=self.code_implementer()
        )
        debug_print(f"Implementation task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("====================================")
        return task

    @task
    def quality_assurance_task(self) -> Task:
        debug_print("=== Creating Quality Assurance Task ===")
        task = Task(
            config=self.tasks_config['quality_assurance_task'], # type: ignore[index]
            agent=self.quality_assurance()
        )
        debug_print(f"Quality Assurance task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("========================================")
        return task

    @task
    def documentation_task(self) -> Task:
        debug_print("=== Creating Documentation Task ===")
        task = Task(
            config=self.tasks_config['documentation_task'], # type: ignore[index]
            agent=self.technical_writer(),
            output_file='programming_assistant_report.md'
        )
        debug_print(f"Documentation task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("====================================")
        return task

    # Flag-Based Planning System Tasks
    @task
    def plan_generation_task(self) -> Task:
        debug_print("=== Creating Plan Generation Task ===")
        task = Task(
            config=self.tasks_config['plan_generation_task'], # type: ignore[index]
            agent=self.solution_architect()
        )
        debug_print(f"Plan Generation task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("======================================")
        return task

    @task
    def plan_based_implementation_task(self) -> Task:
        debug_print("=== Creating Plan-Based Implementation Task ===")
        task = Task(
            config=self.tasks_config['plan_based_implementation_task'], # type: ignore[index]
            agent=self.code_implementer()
        )
        debug_print(f"Plan-Based Implementation task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("===============================================")
        return task

    @task
    def plan_assessment_task(self) -> Task:
        debug_print("=== Creating Plan Assessment Task ===")
        task = Task(
            config=self.tasks_config['plan_assessment_task'], # type: ignore[index]
            agent=self.plan_update_coordinator()
        )
        debug_print(f"Plan Assessment task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("=====================================")
        return task

    @task
    def plan_update_task(self) -> Task:
        debug_print("=== Creating Plan Update Task ===")
        task = Task(
            config=self.tasks_config['plan_update_task'], # type: ignore[index]
            agent=self.plan_update_coordinator()
        )
        debug_print(f"Plan Update task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("==================================")
        return task

    def run_with_interactive_dialogue(self, inputs: Dict[str, Any]) -> str:
        """
        Run the crew with interactive operator dialogue for enhanced context
        
        Args:
            inputs: Standard crew inputs including 'topic' and 'execution_context'
            
        Returns:
            Final crew output with operator context integration
        """
        # Extract original inputs
        user_request = inputs.get('topic', '')
        execution_context = inputs.get('execution_context', '')
        
        # Conduct interactive dialogue to gather operator context
        debug_print("=== Starting Interactive Operator Dialogue ===")
        operator_context = conduct_operator_dialogue(user_request, execution_context)
        debug_print("=== Operator Dialogue Complete ===")
        
        # Enhance inputs with operator context
        enhanced_inputs = {
            **inputs,  # Keep original inputs (topic, current_year, execution_context)
            'topic': operator_context['enhanced_request'],  # Use enhanced request
            'operator_context': operator_context['operator_context'],
            'technical_background': operator_context['technical_background'],
            'project_context': operator_context['project_context'],
            'complexity_preference': operator_context['complexity_preference'],
            'qa_dialogue': operator_context['qa_dialogue'],
            'unstated_needs': operator_context['unstated_needs'],
            # Default values for plan-based template variables (not used in default mode)
            'implementation_plan': 'No specific implementation plan provided. Proceed with analysis and solution development based on the request.',
            'current_plan': 'No existing plan available. This is a new request.',
            'user_request': operator_context['enhanced_request'],  # Same as topic for consistency
            'change_type': 'new_request',  # Default change type for new requests
            'assessment_results': 'No prior assessment available. Proceed with fresh analysis.'
        }
        
        debug_print(f"Enhanced inputs: {list(enhanced_inputs.keys())}")
        
        # Run the crew with enhanced context
        crew_instance = self.crew()
        return crew_instance.kickoff(inputs=enhanced_inputs)

    def detect_domain_expertise_needed(self, request: str) -> List[str]:
        """
        Detect which specialist domains are relevant to the request.
        
        Args:
            request: User's request text
            
        Returns:
            List of relevant domain names
        """
        domains = []
        request_lower = request.lower()
        
        domain_keywords = {
            'infrastructure': [
                'aws', 'cloud', 'docker', 'kubernetes', 'deploy', 'deployment', 'ci/cd', 'devops', 
                'infrastructure', 'server', 'hosting', 'load balancer', 'scaling', 'containerization',
                'terraform', 'ansible', 'jenkins', 'gitlab', 'github actions', 'azure', 'gcp'
            ],
            'database': [
                'database', 'sql', 'mysql', 'postgresql', 'mongodb', 'schema', 'query', 'db',
                'redis', 'elasticsearch', 'cassandra', 'dynamodb', 'migration', 'backup',
                'db performance', 'database performance', 'indexing', 'normalization', 'orm', 'transaction'
            ],
            'security': [
                'security', 'secure', 'auth', 'authentication', 'authorization', 'oauth', 'jwt', 'encryption', 
                'ssl', 'tls', 'vulnerability', 'penetration', 'firewall', 'vpn', 'certificate',
                'password', 'token', 'session', 'csrf', 'xss', 'injection', 'compliance'
            ],
            'frontend': [
                'frontend', 'ui', 'ux', 'react', 'vue', 'angular', 'css', 'html', 'javascript',
                'typescript', 'responsive', 'mobile', 'browser', 'dom', 'component', 'state',
                'routing', 'webpack', 'vite', 'sass', 'tailwind', 'bootstrap'
            ],
            'feature': [
                'feature', 'functionality', 'business', 'requirement', 'user story', 'workflow',
                'process', 'logic', 'rules', 'validation', 'integration', 'api', 'endpoint'
            ]
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in request_lower for keyword in keywords):
                domains.append(domain)
                debug_print(f"Detected domain '{domain}' for request")
        
        debug_print(f"Total domains detected: {domains}")
        return domains

    def run_enhanced_information_workflow(self, inputs: Dict[str, Any]) -> str:
        """
        Run enhanced information workflow with domain-specific specialist advisory.
        
        Args:
            inputs: Standard crew inputs including 'topic' and 'execution_context'
            
        Returns:
            Expert advisory response from relevant specialists
        """
        debug_print("=== Starting Enhanced Information Workflow ===")
        
        request = inputs.get('topic', '')
        relevant_domains = self.detect_domain_expertise_needed(request)
        
        # Always include research analyst for general research coordination
        agents = [self.research_analyst()]
        
        # Add relevant specialists as advisors
        if 'infrastructure' in relevant_domains:
            agents.append(self.infrastructure_specialist())
            debug_print("Added Infrastructure Specialist")
        if 'database' in relevant_domains:
            agents.append(self.database_architecture_specialist())
            debug_print("Added Database Architecture Specialist")
        if 'security' in relevant_domains:
            agents.append(self.security_architecture_specialist())
            debug_print("Added Security Architecture Specialist")
        if 'frontend' in relevant_domains:
            agents.append(self.frontend_architecture_specialist())
            debug_print("Added Frontend Architecture Specialist")
        if 'feature' in relevant_domains:
            agents.append(self.feature_analyst())
            debug_print("Added Feature Analyst")
        
        # Always include technical writer for final response coordination
        agents.append(self.technical_writer())
        
        # Apply error handling to all agents
        robust_agents = apply_tenacity_error_handling_to_agents(agents)
        
        # Create advisory tasks based on detected domains
        tasks = self.create_advisory_tasks(relevant_domains, inputs)
        
        # Execute enhanced information workflow
        enhanced_crew = Crew(
            agents=robust_agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )
        
        debug_print(f"Enhanced information workflow crew created with {len(robust_agents)} agents")
        result = enhanced_crew.kickoff(inputs=inputs)
        debug_print("=== Enhanced Information Workflow Complete ===")
        
        return result

    def create_advisory_tasks(self, domains: List[str], inputs: Dict[str, Any]) -> List[Task]:
        """
        Create advisory tasks based on detected domains.
        
        Args:
            domains: List of detected domain names
            inputs: Standard crew inputs
            
        Returns:
            List of tasks for the advisory workflow
        """
        from crewai import Task
        tasks = []
        
        # Always start with research coordination
        research_task = Task(
            description=f"""
            As the Technical Research Specialist, coordinate the advisory response:
            
            User Request: {inputs.get('topic', '')}
            Context: {inputs.get('execution_context', '')}
            Detected Domains: {', '.join(domains) if domains else 'General'}
            
            Provide initial research and coordinate with domain specialists to ensure:
            1. Comprehensive coverage of the user's question
            2. Integration of specialist insights
            3. Clear, actionable information
            4. Identification of any gaps that need specialist input
            
            Focus on research coordination and general technical context.
            """,
            expected_output="Research coordination and general technical context for specialist advisory",
            agent=self.research_analyst()
        )
        tasks.append(research_task)
        
        # Add domain-specific advisory tasks
        if 'infrastructure' in domains:
            infra_task = Task(
                description=f"""
                As the Infrastructure Specialist, provide expert advisory on infrastructure aspects:
                
                User Request: {inputs.get('topic', '')}
                Context: {inputs.get('execution_context', '')}
                Research Context: Use the research analyst's coordination
                
                Focus on infrastructure, DevOps, cloud, and deployment considerations:
                1. Best practices for the specific infrastructure challenge
                2. Recommended tools and technologies
                3. Architecture considerations and scalability
                4. Security and reliability implications
                5. Implementation guidance and common pitfalls
                6. Cost and performance considerations
                
                Provide expert-level infrastructure advice without full implementation details.
                """,
                expected_output="Expert infrastructure advisory with best practices and recommendations",
                agent=self.infrastructure_specialist()
            )
            tasks.append(infra_task)
        
        if 'database' in domains:
            db_task = Task(
                description=f"""
                As the Database Architecture Specialist, provide expert advisory on database aspects:
                
                User Request: {inputs.get('topic', '')}
                Context: {inputs.get('execution_context', '')}
                Research Context: Use the research analyst's coordination
                
                Focus on database design, optimization, and best practices:
                1. Database technology recommendations and trade-offs
                2. Schema design considerations and normalization
                3. Performance optimization strategies
                4. Scaling approaches and migration strategies
                5. Security, backup, and recovery considerations
                6. Query optimization and indexing guidance
                
                Provide expert-level database advice without full implementation details.
                """,
                expected_output="Expert database advisory with technology recommendations and best practices",
                agent=self.database_architecture_specialist()
            )
            tasks.append(db_task)
        
        if 'security' in domains:
            security_task = Task(
                description=f"""
                As the Security Architecture Specialist, provide expert advisory on security aspects:
                
                User Request: {inputs.get('topic', '')}
                Context: {inputs.get('execution_context', '')}
                Research Context: Use the research analyst's coordination
                
                Focus on security design, authentication, and best practices:
                1. Security architecture recommendations
                2. Authentication and authorization strategies
                3. Encryption and data protection approaches
                4. Vulnerability assessment and mitigation
                5. Compliance and regulatory considerations
                6. Security monitoring and incident response
                
                Provide expert-level security advice without full implementation details.
                """,
                expected_output="Expert security advisory with architecture recommendations and best practices",
                agent=self.security_architecture_specialist()
            )
            tasks.append(security_task)
        
        if 'frontend' in domains:
            frontend_task = Task(
                description=f"""
                As the Frontend Architecture Specialist, provide expert advisory on frontend aspects:
                
                User Request: {inputs.get('topic', '')}
                Context: {inputs.get('execution_context', '')}
                Research Context: Use the research analyst's coordination
                
                Focus on frontend design, user experience, and best practices:
                1. Frontend technology recommendations and frameworks
                2. User interface design patterns and best practices
                3. Performance optimization and responsive design
                4. Accessibility and cross-browser compatibility
                5. State management and component architecture
                6. Build tools and development workflow
                
                Provide expert-level frontend advice without full implementation details.
                """,
                expected_output="Expert frontend advisory with technology recommendations and best practices",
                agent=self.frontend_architecture_specialist()
            )
            tasks.append(frontend_task)
        
        if 'feature' in domains:
            feature_task = Task(
                description=f"""
                As the Feature Analyst, provide expert advisory on feature and business logic aspects:
                
                User Request: {inputs.get('topic', '')}
                Context: {inputs.get('execution_context', '')}
                Research Context: Use the research analyst's coordination
                
                Focus on feature design, business logic, and requirements:
                1. Feature architecture and design patterns
                2. Business logic implementation strategies
                3. User workflow and experience considerations
                4. Integration requirements and API design
                5. Validation and error handling approaches
                6. Testing and quality assurance strategies
                
                Provide expert-level feature analysis without full implementation details.
                """,
                expected_output="Expert feature advisory with design patterns and implementation strategies",
                agent=self.feature_analyst()
            )
            tasks.append(feature_task)
        
        # Always end with technical writing coordination
        final_task = Task(
            description=f"""
            As the Technical Documentation Specialist, create a comprehensive advisory response:
            
            User Request: {inputs.get('topic', '')}
            Specialist Insights: Integrate all specialist advisory inputs
            Research Context: Use the research analyst's coordination
            
            Create a unified response that:
            1. Directly addresses the user's question with expert insights
            2. Integrates recommendations from all relevant specialists
            3. Organizes information in a logical, easy-to-follow structure
            4. Provides actionable next steps and best practices
            5. Highlights any important considerations or trade-offs
            6. Uses clear formatting for readability
            
            This is an expert advisory response, not implementation documentation.
            """,
            expected_output="Comprehensive expert advisory response integrating all specialist insights",
            agent=self.technical_writer()
        )
        tasks.append(final_task)
        
        debug_print(f"Created {len(tasks)} advisory tasks for domains: {domains}")
        return tasks

    def run_information_workflow(self, inputs: Dict[str, Any]) -> str:
        """
        Run a simplified workflow for information requests without interactive dialogue.
        Designed for quick, direct responses to simple questions.
        
        Args:
            inputs: Standard crew inputs including 'topic' and 'execution_context'
            
        Returns:
            Direct response from research analyst
        """
        debug_print("=== Starting Simple Information Workflow ===")
        
        # Create a minimal crew with just the research analyst for quick responses
        research_agent = self.research_analyst()
        
        # Apply error handling
        robust_agents = apply_tenacity_error_handling_to_agents([research_agent])
        
        # Create a simple information task
        from crewai import Task
        
        info_task = Task(
            description=f"""
            Provide a clear, direct answer to this question: {inputs.get('topic', '')}
            
            Context: {inputs.get('execution_context', '')}
            
            Requirements:
            - Give a concise, accurate answer
            - No need for extensive research or planning
            - Focus on being helpful and informative
            - Keep response under 200 words unless more detail is specifically needed
            """,
            expected_output="A clear, direct answer to the user's question",
            agent=robust_agents[0]
        )
        
        # Create minimal crew for information requests
        info_crew = Crew(
            agents=robust_agents,
            tasks=[info_task],
            process=Process.sequential,
            verbose=True
        )
        
        debug_print("Information workflow crew created, executing...")
        result = info_crew.kickoff(inputs=inputs)
        debug_print("=== Information Workflow Complete ===")
        
        return result

    @crew
    def crew(self) -> Crew:
        """Creates the Rscrew crew"""
        debug_print("=== Creating Crew ===")
        debug_print(f"Available agents: {len(self.agents)}")
        debug_print(f"Available tasks: {len(self.tasks)}")
        
        for i, agent in enumerate(self.agents):
            debug_print(f"Agent {i}: {getattr(agent, 'role', 'unknown')} with LLM: {getattr(agent, 'llm', 'None')}")
        
        # Apply Tenacity-based LLM error handling to all agents
        debug_print("Applying Tenacity-based LLM error handling to agents...")
        tenacity_available = check_tenacity_installation()
        debug_print(f"Tenacity available: {tenacity_available}")
        
        robust_agents = apply_tenacity_error_handling_to_agents(self.agents)
        
        crew = Crew(
            agents=robust_agents, # Agents with error handling applied
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
        
        debug_print("Crew created successfully with Tenacity-based LLM error handling")
        debug_print("====================")
        return crew

    # Flag-Based Planning System Crews (without @crew decorator)
    def planning_crew(self) -> Crew:
        """Creates a crew for plan generation (rc -plan)"""
        debug_print("=== Creating Planning Crew ===")
        
        planning_agents = [
            self.project_orchestrator(),
            self.research_analyst(),
            self.solution_architect()
        ]
        
        planning_tasks = [
            self.plan_generation_task()
        ]
        
        # Apply Tenacity-based LLM error handling to planning agents
        robust_agents = apply_tenacity_error_handling_to_agents(planning_agents)
        
        crew = Crew(
            agents=robust_agents,
            tasks=planning_tasks,
            process=Process.sequential,
            verbose=True
        )
        
        debug_print("Planning Crew created successfully")
        debug_print("=================================")
        return crew

    def implementation_crew(self) -> Crew:
        """Creates a crew for plan-based implementation (rc -build)"""
        debug_print("=== Creating Implementation Crew ===")
        
        implementation_agents = [
            self.code_implementer(),
            self.quality_assurance(),
            self.technical_writer()
        ]
        
        implementation_tasks = [
            self.plan_based_implementation_task(),
            self.quality_assurance_task(),
            self.documentation_task()
        ]
        
        # Apply Tenacity-based LLM error handling to implementation agents
        robust_agents = apply_tenacity_error_handling_to_agents(implementation_agents)
        
        crew = Crew(
            agents=robust_agents,
            tasks=implementation_tasks,
            process=Process.sequential,
            verbose=True
        )
        
        debug_print("Implementation Crew created successfully")
        debug_print("=======================================")
        return crew

    def route_update_request(self, user_request: str) -> Agent:
        """Route update request to appropriate specialist agent"""
        debug_print(f"=== Routing Update Request: {user_request[:50]}... ===")
        
        # Simple keyword-based routing for now
        request_lower = user_request.lower()
        
        if any(keyword in request_lower for keyword in ['auth', 'login', 'security', 'oauth', 'permission', 'access']):
            debug_print("Routing to Security Architecture Specialist")
            return self.security_architecture_specialist()
        elif any(keyword in request_lower for keyword in ['database', 'db', 'sql', 'postgres', 'mysql', 'mongo', 'data']):
            debug_print("Routing to Database Architecture Specialist")
            return self.database_architecture_specialist()
        elif any(keyword in request_lower for keyword in ['frontend', 'ui', 'react', 'vue', 'angular', 'css', 'html', 'javascript']):
            debug_print("Routing to Frontend Architecture Specialist")
            return self.frontend_architecture_specialist()
        elif any(keyword in request_lower for keyword in ['deploy', 'docker', 'kubernetes', 'aws', 'cloud', 'infrastructure', 'ci/cd']):
            debug_print("Routing to Infrastructure Specialist")
            return self.infrastructure_specialist()
        elif any(keyword in request_lower for keyword in ['feature', 'functionality', 'business', 'requirement', 'user story']):
            debug_print("Routing to Feature Analyst")
            return self.feature_analyst()
        else:
            debug_print("Routing to Plan Update Coordinator (general)")
            return self.plan_update_coordinator()

    def assess_and_preview_change(self, current_plan: str, user_request: str, agent: Agent) -> dict:
        """Assess feasibility and generate preview of changes"""
        debug_print(f"=== Assessing Change with {getattr(agent, 'role', 'Unknown')} ===")
        
        # Determine change type based on agent
        agent_role = getattr(agent, 'role', '').lower()
        if 'security' in agent_role:
            change_type = 'SECURITY'
        elif 'database' in agent_role:
            change_type = 'DATABASE'
        elif 'frontend' in agent_role:
            change_type = 'FRONTEND'
        elif 'infrastructure' in agent_role:
            change_type = 'INFRASTRUCTURE'
        elif 'feature' in agent_role:
            change_type = 'FEATURE'
        else:
            change_type = 'GENERAL'
        
        assessment_task = Task(
            config=self.tasks_config['plan_assessment_task'], # type: ignore[index]
            agent=agent
        )
        
        inputs = {
            'current_plan': current_plan,
            'user_request': user_request,
            'change_type': change_type
        }
        
        try:
            result = assessment_task.execute(context=inputs)
            return self.parse_assessment_result(result.raw if hasattr(result, 'raw') else str(result))
        except Exception as e:
            debug_print(f"Error in assessment: {e}")
            return {
                'assessment': f"Error assessing change: {e}",
                'impact': "Unknown",
                'considerations': "Assessment failed",
                'risks': "Unknown risks",
                'recommendations': "Please try again",
                'implementation_approach': "Manual review needed"
            }

    def parse_assessment_result(self, result_text: str) -> dict:
        """Parse assessment result into structured format"""
        debug_print("=== Parsing Assessment Result ===")
        
        # Simple parsing - look for section headers
        sections = {
            'assessment': '',
            'impact': '',
            'considerations': '',
            'risks': '',
            'recommendations': '',
            'implementation_approach': ''
        }
        
        lines = result_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('ASSESSMENT:'):
                current_section = 'assessment'
                sections[current_section] = line.replace('ASSESSMENT:', '').strip()
            elif line.startswith('IMPACT:'):
                current_section = 'impact'
                sections[current_section] = line.replace('IMPACT:', '').strip()
            elif line.startswith('CONSIDERATIONS:'):
                current_section = 'considerations'
                sections[current_section] = line.replace('CONSIDERATIONS:', '').strip()
            elif line.startswith('RISKS:'):
                current_section = 'risks'
                sections[current_section] = line.replace('RISKS:', '').strip()
            elif line.startswith('RECOMMENDATIONS:'):
                current_section = 'recommendations'
                sections[current_section] = line.replace('RECOMMENDATIONS:', '').strip()
            elif line.startswith('IMPLEMENTATION_APPROACH:'):
                current_section = 'implementation_approach'
                sections[current_section] = line.replace('IMPLEMENTATION_APPROACH:', '').strip()
            elif current_section and line:
                sections[current_section] += ' ' + line
        
        debug_print("Assessment parsing complete")
        return sections
