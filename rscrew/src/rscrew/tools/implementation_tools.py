#!/usr/bin/env python3
"""
Implementation Tools Framework
Provides agents with implementation capabilities while maintaining safety controls.
"""

import os
import subprocess
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type


class SafetyController:
    """Controls safety and permissions for implementation operations"""
    
    def __init__(self):
        self.aws_account_boundary = True
        self.max_weekly_cost = 5.00
        self.external_read_allowed = True
        
    def assess_risk(self, operation: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Assess risk level of an operation"""
        risks = []
        
        # Cost assessment
        estimated_cost = self.estimate_cost(operation)
        if estimated_cost > self.max_weekly_cost:
            risks.append(f"COST_EXCEEDED: ${estimated_cost:.2f} > ${self.max_weekly_cost}")
            
        # External boundary check
        if self.is_external_write(operation):
            risks.append("EXTERNAL_WRITE_BLOCKED: Cannot modify resources outside AWS account")
            
        # Determine risk level
        if len(risks) == 0:
            return "LOW", risks
        elif any("COST_EXCEEDED" in r or "EXTERNAL_WRITE" in r for r in risks):
            return "HIGH", risks
        else:
            return "MEDIUM", risks
            
    def estimate_cost(self, operation: Dict[str, Any]) -> float:
        """Estimate weekly cost impact of operation"""
        base_cost = 0.01  # Base operation cost
        
        # API call costs
        if operation.get('api_calls', 0) > 0:
            base_cost += operation['api_calls'] * 0.002
            
        # Compute time costs
        if operation.get('compute_minutes', 0) > 0:
            base_cost += operation['compute_minutes'] * 0.01
            
        return base_cost
        
    def is_external_write(self, operation: Dict[str, Any]) -> bool:
        """Check if operation writes outside AWS account"""
        if not operation.get('target_external', False):
            return False
            
        write_operations = ['write', 'create', 'delete', 'modify', 'deploy', 'purchase']
        return operation.get('operation_type') in write_operations
        
    def approve_operation(self, operation: Dict[str, Any]) -> Tuple[bool, str]:
        """Approve or reject an operation"""
        risk_level, risks = self.assess_risk(operation)
        
        if risk_level == "LOW":
            return True, "Operation approved"
        elif risk_level == "HIGH":
            return False, f"Operation blocked: {'; '.join(risks)}"
        else:
            return False, f"Operation requires confirmation: {'; '.join(risks)}"


class GitRollbackManager:
    """Manages git-based rollback strategy"""
    
    def __init__(self, repo_path: str = None):
        self.repo_path = repo_path or os.getcwd()
        self.base_branch = "main"
        self.agent_branch_prefix = "agent-implementation"
        
    def create_implementation_branch(self, agent_name: str, task_description: str) -> str:
        """Create a new branch for implementation"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        task_slug = task_description.lower().replace(" ", "-")[:30]
        branch_name = f"{self.agent_branch_prefix}/{agent_name}/{timestamp}_{task_slug}"
        
        try:
            # Ensure we're on main branch
            subprocess.run(["git", "checkout", self.base_branch], 
                         cwd=self.repo_path, check=True, capture_output=True)
            
            # Create and switch to new branch
            subprocess.run(["git", "checkout", "-b", branch_name], 
                         cwd=self.repo_path, check=True, capture_output=True)
            
            return branch_name
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create branch {branch_name}: {e}")
            
    def commit_change(self, message: str) -> bool:
        """Commit current changes"""
        try:
            subprocess.run(["git", "add", "-A"], cwd=self.repo_path, check=True)
            subprocess.run(["git", "commit", "-m", message], 
                         cwd=self.repo_path, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
            
    def generate_merge_instructions(self, branch_name: str, test_results: Dict) -> str:
        """Generate instructions for user to merge changes"""
        if test_results.get('passed', False):
            return f"""
✅ Implementation completed successfully on branch: {branch_name}

Changes made:
{self._format_changes(test_results.get('changes', []))}

Test Results:
{self._format_test_results(test_results)}

To merge these changes:
1. Review the changes: git diff {self.base_branch}..{branch_name}
2. Merge when ready: git checkout {self.base_branch} && git merge {branch_name}
3. Delete branch: git branch -d {branch_name}

Or create PR for review: git push origin {branch_name}
"""
        else:
            return f"""
❌ Implementation failed on branch: {branch_name}

Test Results:
{self._format_test_results(test_results)}

To investigate:
1. Check the changes: git diff {self.base_branch}..{branch_name}
2. Review logs and fix issues
3. Delete failed branch: git checkout {self.base_branch} && git branch -D {branch_name}
"""
            
    def _format_changes(self, changes: List[str]) -> str:
        return "\n".join(f"  - {change}" for change in changes)
        
    def _format_test_results(self, test_results: Dict) -> str:
        results = []
        for test_name, result in test_results.get('tests', {}).items():
            status = "✅" if result.get('passed') else "❌"
            results.append(f"  {status} {test_name}: {result.get('message', 'No details')}")
        return "\n".join(results)


class WriteFileInput(BaseModel):
    """Input schema for WriteFile tool."""
    file_path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="Content to write to the file")
    create_dirs: bool = Field(default=True, description="Create directories if they don't exist")

class WriteFileTool(BaseTool):
    """Tool for writing/creating files with safety controls"""
    
    name: str = "write_file"
    description: str = "Write content to a file with safety controls and git tracking"
    args_schema: Type[BaseModel] = WriteFileInput
    
    def _run(self, file_path: str, content: str, create_dirs: bool = True) -> str:
        """Write content to file with safety checks"""
        safety_controller = SafetyController()
        
        operation = {
            'operation_type': 'write',
            'target_external': not file_path.startswith('/home/ubuntu/environment/workbench'),
            'api_calls': 0,
            'compute_minutes': 0.1
        }
        
        # Safety check
        approved, message = safety_controller.approve_operation(operation)
        if not approved:
            return f"❌ Operation blocked: {message}"
            
        try:
            file_path = Path(file_path)
            
            # Create directories if needed
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return f"✅ File written successfully: {file_path}"
            
        except Exception as e:
            return f"❌ Failed to write file: {e}"


class ExecuteCommandInput(BaseModel):
    """Input schema for ExecuteCommand tool."""
    command: str = Field(..., description="System command to execute")
    working_dir: str = Field(default=None, description="Working directory for command execution")

class ExecuteCommandTool(BaseTool):
    """Tool for executing system commands with safety controls"""
    
    name: str = "execute_command"
    description: str = "Execute system commands with safety controls and logging"
    args_schema: Type[BaseModel] = ExecuteCommandInput
    
    def _run(self, command: str, working_dir: str = None) -> str:
        """Execute command with safety checks"""
        safety_controller = SafetyController()
        allowed_commands = [
            'ls', 'cat', 'grep', 'find', 'curl', 'wget',  # Read operations
            'mkdir', 'cp', 'mv', 'chmod', 'chown',        # File operations
            'systemctl', 'service', 'apache2ctl',         # Service operations
            'git', 'npm', 'pip', 'python', 'node',        # Development tools
            'a2ensite', 'a2dissite', 'a2enmod'            # Apache tools
        ]
        
        # Parse command
        cmd_parts = command.split()
        if not cmd_parts:
            return "❌ Empty command"
            
        base_command = cmd_parts[0]
        
        # Safety checks
        if base_command not in allowed_commands:
            return f"❌ Command not allowed: {base_command}"
            
        operation = {
            'operation_type': 'execute',
            'target_external': False,  # System commands are internal
            'api_calls': 0,
            'compute_minutes': 0.5
        }
        
        approved, message = safety_controller.approve_operation(operation)
        if not approved:
            return f"❌ Operation blocked: {message}"
            
        try:
            # Execute command
            result = subprocess.run(
                cmd_parts,
                cwd=working_dir or os.getcwd(),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"✅ Command executed successfully:\n{result.stdout}"
            else:
                return f"❌ Command failed (exit code {result.returncode}):\n{result.stderr}"
                
        except subprocess.TimeoutExpired:
            return "❌ Command timed out after 30 seconds"
        except Exception as e:
            return f"❌ Failed to execute command: {e}"


class ConfigureServiceInput(BaseModel):
    """Input schema for ConfigureService tool."""
    service_type: str = Field(..., description="Type of service to configure (e.g., 'apache_virtual_host')")
    config_data: Dict[str, Any] = Field(..., description="Configuration data for the service")

class ConfigureServiceTool(BaseTool):
    """Tool for configuring system services (Apache, Nginx, etc.)"""
    
    name: str = "configure_service"
    description: str = "Configure system services with templates and safety controls"
    args_schema: Type[BaseModel] = ConfigureServiceInput
    
    def _run(self, service_type: str, config_data: Dict[str, Any]) -> str:
        """Configure a service with provided data"""
        safety_controller = SafetyController()
        
        operation = {
            'operation_type': 'configure',
            'target_external': False,
            'api_calls': 0,
            'compute_minutes': 1.0
        }
        
        approved, message = safety_controller.approve_operation(operation)
        if not approved:
            return f"❌ Operation blocked: {message}"
            
        if service_type == "apache_virtual_host":
            return self._configure_apache_vhost(config_data)
        elif service_type == "nginx_server_block":
            return self._configure_nginx_server(config_data)
        else:
            return f"❌ Unsupported service type: {service_type}"
            
    def _configure_apache_vhost(self, config: Dict[str, Any]) -> str:
        """Configure Apache virtual host"""
        try:
            server_name = config.get('server_name')
            document_root = config.get('document_root')
            
            if not server_name or not document_root:
                return "❌ Missing required config: server_name and document_root"
                
            # Generate virtual host configuration
            vhost_config = f"""<VirtualHost *:80>
    ServerName {server_name}
    DocumentRoot {document_root}
    
    <Directory {document_root}>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>
    
    ErrorLog ${{APACHE_LOG_DIR}}/{server_name}-error.log
    CustomLog ${{APACHE_LOG_DIR}}/{server_name}-access.log combined
</VirtualHost>
"""
            
            # Write configuration file
            config_file = f"/etc/apache2/sites-available/{server_name}.conf"
            write_tool = WriteFileTool()
            write_result = write_tool._run(config_file, vhost_config)
            
            if "✅" not in write_result:
                return write_result
                
            # Enable site
            exec_tool = ExecuteCommandTool()
            enable_result = exec_tool._run(f"a2ensite {server_name}.conf")
            
            if "✅" not in enable_result:
                return enable_result
                
            # Test configuration
            test_result = exec_tool._run("apache2ctl configtest")
            
            if "✅" not in test_result:
                return f"❌ Apache configuration test failed:\n{test_result}"
                
            # Reload Apache
            reload_result = exec_tool._run("systemctl reload apache2")
            
            return f"✅ Apache virtual host configured successfully for {server_name}"
            
        except Exception as e:
            return f"❌ Failed to configure Apache virtual host: {e}"


class ExternalReadInput(BaseModel):
    """Input schema for ExternalRead tool."""
    url: str = Field(..., description="URL to read from")
    method: str = Field(default="GET", description="HTTP method to use")
    headers: Dict = Field(default=None, description="HTTP headers to include")

class ExternalReadTool(BaseTool):
    """Tool for reading external resources (APIs, websites, documentation)"""
    
    name: str = "external_read"
    description: str = "Read external resources like APIs, documentation, and websites"
    args_schema: Type[BaseModel] = ExternalReadInput
    
    def _run(self, url: str, method: str = "GET", headers: Dict = None) -> str:
        """Read from external URL"""
        operation = {
            'operation_type': 'read',
            'target_external': True,
            'api_calls': 1,
            'compute_minutes': 0.1
        }
        
        # External reads are allowed
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers or {},
                timeout=10
            )
            
            if response.status_code == 200:
                return f"✅ External read successful:\n{response.text[:2000]}..."
            else:
                return f"❌ External read failed: HTTP {response.status_code}"
                
        except Exception as e:
            return f"❌ Failed to read external resource: {e}"


# Export all tools
IMPLEMENTATION_TOOLS = [
    WriteFileTool(),
    ExecuteCommandTool(),
    ConfigureServiceTool(),
    ExternalReadTool()
]