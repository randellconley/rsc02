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
from rscrew.llm_error_handler import apply_error_handling_to_agents, get_llm_config

# Version information for deployment tracking
RSCREW_VERSION = "v3.0-programming-assistant"
RSCREW_FEATURES = ["null-response-handling", "debug-monitoring", "programming-assistant-crew"]
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
            **inputs,  # Keep original inputs
            'topic': operator_context['enhanced_request'],  # Use enhanced request
            'operator_context': operator_context['operator_context'],
            'technical_background': operator_context['technical_background'],
            'project_context': operator_context['project_context'],
            'complexity_preference': operator_context['complexity_preference'],
            'qa_dialogue': operator_context['qa_dialogue'],
            'unstated_needs': operator_context['unstated_needs']
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
        
        # Apply LLM error handling to all agents
        debug_print("Applying LLM error handling to agents...")
        llm_config = get_llm_config()
        debug_print(f"LLM config: max_retries={llm_config['max_retries']}, fallback_enabled={llm_config['fallback_enabled']}")
        
        robust_agents = apply_error_handling_to_agents(self.agents)
        
        crew = Crew(
            agents=robust_agents, # Agents with error handling applied
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
        
        debug_print("Crew created successfully with LLM error handling")
        debug_print("====================")
        return crew
