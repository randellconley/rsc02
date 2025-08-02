import os
import logging
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.llm import LLM
from typing import List
from rscrew.tools.custom_tool import (
    ReadFile, WriteFile, ListDirectory, FindFiles, GetFileInfo
)

# Debug toggle - set to False to disable debug output
DEBUG_MODE = os.getenv('RSCREW_DEBUG', 'true').lower() == 'true'

def debug_print(message):
    if DEBUG_MODE:
        print(f"[DEBUG] {message}")

# Set up logging for CrewAI internals (but suppress verbose LiteLLM logs)
if DEBUG_MODE:
    logging.basicConfig(level=logging.INFO)  # Changed from DEBUG to INFO
    # Suppress verbose LiteLLM logging
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    debug_print("Debug mode enabled")

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
    def researcher(self) -> Agent:
        debug_print("=== Creating Researcher Agent ===")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        try:
            llm = LLM(model="claude-3-5-sonnet-20241022", api_key=api_key)
            debug_print(f"LLM created: {llm.model}")
            
            # Add debugging wrapper to intercept CrewAI's LLM calls
            if DEBUG_MODE:
                original_call = llm.call
                def debug_call(*args, **kwargs):
                    debug_print(f"=== CrewAI LLM Call Intercepted ===")
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
                        result = original_call(*args, **kwargs)
                        debug_print(f"LLM call result type: {type(result)}")
                        debug_print(f"LLM call result length: {len(str(result)) if result else 0}")
                        debug_print(f"LLM call result preview: {str(result)[:200]}..." if result and len(str(result)) > 200 else str(result))
                        debug_print("=== End LLM Call ===")
                        return result
                    except Exception as e:
                        debug_print(f"LLM call failed: {e}")
                        debug_print(f"Exception type: {type(e)}")
                        debug_print("=== End LLM Call (Failed) ===")
                        raise
                
                llm.call = debug_call
                
        except Exception as e:
            debug_print(f"ERROR creating LLM: {e}")
            llm = None
        
        # Test LLM directly
        if llm and DEBUG_MODE:
            try:
                debug_print("Testing LLM with simple call...")
                test_response = llm.call("Say 'test successful'")
                debug_print(f"Simple test response: {test_response}")
                debug_print(f"Response type: {type(test_response)}")
                debug_print(f"Response length: {len(str(test_response)) if test_response else 0}")
                
                # Test with a more complex prompt similar to what CrewAI might send
                debug_print("Testing LLM with complex prompt...")
                complex_prompt = """You are a Senior Data Researcher. Your goal is to uncover cutting-edge developments in hello.
                
Please respond with a brief analysis of the topic 'hello'."""
                complex_response = llm.call(complex_prompt)
                debug_print(f"Complex test response: {complex_response}")
                debug_print(f"Complex response type: {type(complex_response)}")
                debug_print(f"Complex response length: {len(str(complex_response)) if complex_response else 0}")
                
            except Exception as e:
                debug_print(f"LLM test failed: {e}")
                debug_print(f"Exception type: {type(e)}")
                debug_print(f"Exception args: {e.args}")
        
        debug_print("===================================")
        
        agent = Agent(
            config=self.agents_config['researcher'], # type: ignore[index]
            tools=[ReadFile(), ListDirectory(), FindFiles(), GetFileInfo()],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Agent created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print(f"Agent LLM model: {getattr(agent.llm, 'model', 'Unknown') if hasattr(agent, 'llm') and agent.llm else 'No LLM'}")
        debug_print(f"Agent LLM type: {type(agent.llm) if hasattr(agent, 'llm') and agent.llm else 'No LLM'}")
        return agent

    @agent
    def reporting_analyst(self) -> Agent:
        debug_print("=== Creating Reporting Analyst Agent ===")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        try:
            llm = LLM(model="claude-3-5-sonnet-20241022", api_key=api_key)
            debug_print(f"LLM created: {llm.model}")
        except Exception as e:
            debug_print(f"ERROR creating LLM: {e}")
            llm = None
        
        debug_print("========================================")
        
        agent = Agent(
            config=self.agents_config['reporting_analyst'], # type: ignore[index]
            tools=[ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo()],
            verbose=True,
            llm=llm
        )
        
        debug_print(f"Agent created with LLM: {getattr(agent, 'llm', 'None')}")
        debug_print(f"Agent LLM model: {getattr(agent.llm, 'model', 'Unknown') if hasattr(agent, 'llm') and agent.llm else 'No LLM'}")
        debug_print(f"Agent LLM type: {type(agent.llm) if hasattr(agent, 'llm') and agent.llm else 'No LLM'}")
        return agent

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def research_task(self) -> Task:
        debug_print("=== Creating Research Task ===")
        task = Task(
            config=self.tasks_config['research_task'], # type: ignore[index]
            agent=self.researcher()
        )
        debug_print(f"Research task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("==============================")
        return task

    @task
    def reporting_task(self) -> Task:
        debug_print("=== Creating Reporting Task ===")
        task = Task(
            config=self.tasks_config['reporting_task'], # type: ignore[index]
            agent=self.reporting_analyst(),
            output_file='report.md'
        )
        debug_print(f"Reporting task created with agent: {getattr(task.agent, 'role', 'Unknown').strip()}")
        debug_print("===============================")
        return task

    @crew
    def crew(self) -> Crew:
        """Creates the Rscrew crew"""
        debug_print("=== Creating Crew ===")
        debug_print(f"Available agents: {len(self.agents)}")
        debug_print(f"Available tasks: {len(self.tasks)}")
        
        for i, agent in enumerate(self.agents):
            debug_print(f"Agent {i}: {getattr(agent, 'role', 'unknown')} with LLM: {getattr(agent, 'llm', 'None')}")
        
        crew = Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
        
        debug_print("Crew created successfully")
        debug_print("====================")
        return crew
