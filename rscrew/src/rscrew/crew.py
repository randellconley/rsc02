import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.llm import LLM
from typing import List
from rscrew.tools.custom_tool import (
    ReadFile, WriteFile, ListDirectory, FindFiles, GetFileInfo
)

# Debug: Check environment variables
print("=== DEBUG: Environment Check ===")
print(f"ANTHROPIC_API_KEY exists: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
print(f"ANTHROPIC_API_KEY length: {len(os.getenv('ANTHROPIC_API_KEY', ''))}")
print("=================================")
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class Rscrew():
    """Rscrew crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def researcher(self) -> Agent:
        print("=== DEBUG: Creating Researcher Agent ===")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        print(f"API Key available: {bool(api_key)}")
        print(f"API Key length: {len(api_key) if api_key else 0}")
        
        try:
            llm = LLM(model="claude-3-5-sonnet-20241022", api_key=api_key)
            print(f"LLM created successfully: {llm.model}")
        except Exception as e:
            print(f"ERROR creating LLM: {e}")
            llm = None
        
        print(f"Researcher LLM: {llm.model if llm else 'None'}")
        print("======================================")
        
        return Agent(
            config=self.agents_config['researcher'], # type: ignore[index]
            tools=[ReadFile(), ListDirectory(), FindFiles(), GetFileInfo()],
            verbose=True,
            llm=llm
        )

    @agent
    def reporting_analyst(self) -> Agent:
        print("=== DEBUG: Creating Reporting Analyst Agent ===")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        print(f"API Key available: {bool(api_key)}")
        print(f"API Key length: {len(api_key) if api_key else 0}")
        
        try:
            llm = LLM(model="claude-3-5-sonnet-20241022", api_key=api_key)
            print(f"LLM created successfully: {llm.model}")
        except Exception as e:
            print(f"ERROR creating LLM: {e}")
            llm = None
        
        print(f"Reporting Analyst LLM: {llm.model if llm else 'None'}")
        print("==========================================")
        
        return Agent(
            config=self.agents_config['reporting_analyst'], # type: ignore[index]
            tools=[ReadFile(), WriteFile(), ListDirectory(), FindFiles(), GetFileInfo()],
            verbose=True,
            llm=llm
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'], # type: ignore[index]
            agent=self.researcher()
        )

    @task
    def reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config['reporting_task'], # type: ignore[index]
            agent=self.reporting_analyst(),
            output_file='report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Rscrew crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
