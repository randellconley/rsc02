import os
import logging
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

# Version information for deployment tracking
RSCREW_VERSION = "v3.1-tenacity-hybrid"
RSCREW_FEATURES = ["tenacity-retry-logic", "context-aware-fallbacks", "debug-monitoring", "programming-assistant-crew"]
RSCREW_COMMIT = "programming-assistant"  # Full programming assistant crew implementation

# Debug toggle - only enabled when explicitly set to 'true'
DEBUG_MODE = os.getenv('RSCREW_DEBUG', 'false').lower() == 'true'

def debug_print(message):
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

def create_llm_with_monitoring(agent_name: str):
    """Create an LLM instance with monitoring and error handling for the specified agent"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    try:
        llm = LLM(model="claude-3-5-sonnet-20241022", api_key=api_key)
        debug_print(f"LLM created for {agent_name}: {llm.model}")
        
        # Fix LLM call method - ensure proper method binding and error handling
        if llm and hasattr(llm, 'call'):
            original_call = llm.call
            
            def fixed_call(*args, **kwargs):
                if DEBUG_MODE:
                    debug_print(f"=== CrewAI LLM Call Intercepted ({agent_name} - {RSCREW_VERSION}) ===")
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
        
        llm = create_llm_with_monitoring("operator_intent_interpreter")
        
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
        llm = create_llm_with_monitoring("Project Orchestrator")
        
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
        llm = create_llm_with_monitoring("Research Analyst")
        
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
        llm = create_llm_with_monitoring("Solution Architect")
        
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
        llm = create_llm_with_monitoring("Code Implementer")
        
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
        llm = create_llm_with_monitoring("Quality Assurance")
        
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
        llm = create_llm_with_monitoring("Technical Writer")
        
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
        llm = create_llm_with_monitoring("Security Architecture Specialist")
        
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
        llm = create_llm_with_monitoring("Database Architecture Specialist")
        
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
        llm = create_llm_with_monitoring("Frontend Architecture Specialist")
        
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
        llm = create_llm_with_monitoring("Infrastructure Specialist")
        
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
        llm = create_llm_with_monitoring("Feature Analyst")
        
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
        llm = create_llm_with_monitoring("Plan Update Coordinator")
        
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
