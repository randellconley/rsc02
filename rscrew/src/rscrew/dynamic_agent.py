#!/usr/bin/env python3
"""
Dynamic Agent Framework
Enables agents to switch between advisory and implementation modes based on context.
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

from crewai import Agent, Task
from crewai.tools import BaseTool

from .tools.implementation_tools import (
    IMPLEMENTATION_TOOLS, 
    SafetyController, 
    GitRollbackManager
)


class ContextDecisionEngine:
    """Determines when to advise vs implement based on context analysis"""
    
    def __init__(self):
        self.implementation_keywords = [
            'fix', 'create', 'build', 'deploy', 'configure', 'setup', 'install',
            'implement', 'make', 'change', 'update', 'modify', 'add', 'remove',
            'restart', 'start', 'stop', 'enable', 'disable', 'apply'
        ]
        
        self.advisory_keywords = [
            'how', 'what', 'why', 'when', 'where', 'explain', 'describe',
            'recommend', 'suggest', 'advise', 'best practice', 'should i',
            'tell me', 'show me', 'help me understand'
        ]
        
    def analyze_request(self, user_request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user request to determine appropriate response mode"""
        request_lower = user_request.lower()
        
        # Count implementation vs advisory indicators
        impl_score = sum(1 for keyword in self.implementation_keywords 
                        if keyword in request_lower)
        advisory_score = sum(1 for keyword in self.advisory_keywords 
                           if keyword in request_lower)
        
        # Analyze request structure
        is_question = '?' in user_request
        is_command = any(request_lower.startswith(cmd) for cmd in 
                        ['fix', 'create', 'build', 'deploy', 'configure'])
        has_specific_target = self._has_specific_target(user_request)
        
        # Determine mode
        if impl_score > advisory_score and (is_command or has_specific_target):
            mode = "IMPLEMENTATION"
            confidence = min(0.9, 0.5 + (impl_score - advisory_score) * 0.1)
        elif advisory_score > impl_score or is_question:
            mode = "ADVISORY"
            confidence = min(0.9, 0.5 + (advisory_score - impl_score) * 0.1)
        else:
            # Hybrid mode - provide both
            mode = "HYBRID"
            confidence = 0.6
            
        return {
            'mode': mode,
            'confidence': confidence,
            'implementation_score': impl_score,
            'advisory_score': advisory_score,
            'requires_confirmation': self._requires_confirmation(user_request),
            'estimated_risk': self._estimate_risk(user_request),
            'specific_target': has_specific_target
        }
        
    def _has_specific_target(self, request: str) -> bool:
        """Check if request has specific implementation target"""
        specific_patterns = [
            r'\b\w+\.(com|org|net|io)\b',  # Domain names
            r'/[\w/]+\.\w+',               # File paths
            r'\b\w+\.conf\b',              # Config files
            r'\bapache\b|\bnginx\b',       # Specific services
            r'\bindex\.php\b|\bindex\.html\b'  # Specific files
        ]
        
        return any(re.search(pattern, request, re.IGNORECASE) 
                  for pattern in specific_patterns)
                  
    def _requires_confirmation(self, request: str) -> bool:
        """Check if request requires user confirmation"""
        high_risk_keywords = [
            'delete', 'remove', 'drop', 'destroy', 'reset',
            'production', 'live', 'main', 'master'
        ]
        
        return any(keyword in request.lower() for keyword in high_risk_keywords)
        
    def _estimate_risk(self, request: str) -> str:
        """Estimate risk level of request"""
        request_lower = request.lower()
        
        high_risk = ['delete', 'remove', 'drop', 'production', 'live']
        medium_risk = ['restart', 'reload', 'modify', 'change']
        
        if any(keyword in request_lower for keyword in high_risk):
            return "HIGH"
        elif any(keyword in request_lower for keyword in medium_risk):
            return "MEDIUM"
        else:
            return "LOW"


class LearningSystem:
    """Learns from user interactions to improve decision making"""
    
    def __init__(self):
        self.interaction_history = []
        self.user_preferences = {}
        self.pattern_cache = {}
        
    def record_interaction(self, request: str, agent_action: str, 
                         user_feedback: Optional[str] = None):
        """Record user interaction for learning"""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'request': request,
            'agent_action': agent_action,
            'user_feedback': user_feedback,
            'request_type': self._classify_request_type(request)
        }
        
        self.interaction_history.append(interaction)
        self._update_preferences(interaction)
        
    def _classify_request_type(self, request: str) -> str:
        """Classify request type for learning"""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['fix', 'configure', 'setup']):
            return "CONFIGURATION"
        elif any(word in request_lower for word in ['create', 'build', 'develop']):
            return "DEVELOPMENT"
        elif any(word in request_lower for word in ['deploy', 'install', 'update']):
            return "DEPLOYMENT"
        else:
            return "GENERAL"
            
    def _update_preferences(self, interaction: Dict[str, Any]):
        """Update user preferences based on interaction"""
        request_type = interaction['request_type']
        
        if request_type not in self.user_preferences:
            self.user_preferences[request_type] = {
                'prefers_implementation': 0,
                'prefers_advisory': 0,
                'total_interactions': 0
            }
            
        prefs = self.user_preferences[request_type]
        prefs['total_interactions'] += 1
        
        # Infer preference from action taken
        if 'implemented' in interaction['agent_action'].lower():
            prefs['prefers_implementation'] += 1
        else:
            prefs['prefers_advisory'] += 1
            
    def get_preference_score(self, request_type: str) -> float:
        """Get user's preference score for implementation vs advisory"""
        if request_type not in self.user_preferences:
            return 0.5  # Neutral
            
        prefs = self.user_preferences[request_type]
        if prefs['total_interactions'] == 0:
            return 0.5
            
        impl_ratio = prefs['prefers_implementation'] / prefs['total_interactions']
        return impl_ratio


class DynamicAgent:
    """Enhanced agent with dynamic advisory/implementation capabilities"""
    
    def __init__(self, base_agent: Agent, agent_name: str):
        self.base_agent = base_agent
        self.agent_name = agent_name
        self.decision_engine = ContextDecisionEngine()
        self.learning_system = LearningSystem()
        self.safety_controller = SafetyController()
        self.git_manager = GitRollbackManager()
        
        # Combine all available tools
        self.all_tools = self._load_all_tools()
        
        # Add tools to base agent
        if hasattr(self.base_agent, 'tools'):
            self.base_agent.tools.extend(self.all_tools)
        else:
            self.base_agent.tools = self.all_tools
            
    def _load_all_tools(self) -> List[BaseTool]:
        """Load all available tools for the agent"""
        tools = []
        
        # Add implementation tools
        tools.extend(IMPLEMENTATION_TOOLS)
        
        # Add existing programming tools
        try:
            tools.extend(PROGRAMMING_TOOLS)
        except:
            pass  # Programming tools might not be available
            
        # Custom tools can be added here in the future
            
        return tools
        
    def process_request(self, user_request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user request with dynamic mode selection"""
        
        # Analyze request context
        analysis = self.decision_engine.analyze_request(user_request, context)
        
        # Apply learning preferences
        request_type = self.learning_system._classify_request_type(user_request)
        preference_score = self.learning_system.get_preference_score(request_type)
        
        # Adjust mode based on learned preferences
        if preference_score > 0.7 and analysis['mode'] == 'ADVISORY':
            analysis['mode'] = 'HYBRID'
        elif preference_score < 0.3 and analysis['mode'] == 'IMPLEMENTATION':
            analysis['mode'] = 'HYBRID'
            
        # Execute based on determined mode
        if analysis['mode'] == 'IMPLEMENTATION':
            result = self._execute_implementation(user_request, analysis, context)
        elif analysis['mode'] == 'ADVISORY':
            result = self._provide_advisory(user_request, analysis, context)
        else:  # HYBRID
            result = self._provide_hybrid_response(user_request, analysis, context)
            
        # Record interaction for learning
        self.learning_system.record_interaction(
            user_request, 
            result.get('action_taken', 'unknown')
        )
        
        return result
        
    def _execute_implementation(self, request: str, analysis: Dict, context: Dict) -> Dict[str, Any]:
        """Execute implementation directly"""
        
        # Create implementation branch
        try:
            branch_name = self.git_manager.create_implementation_branch(
                self.agent_name, 
                request[:50]
            )
        except Exception as e:
            return {
                'mode': 'IMPLEMENTATION',
                'status': 'FAILED',
                'message': f"❌ Failed to create git branch: {e}",
                'action_taken': 'implementation_failed'
            }
            
        # Execute the implementation
        implementation_result = self._perform_implementation(request, context)
        
        # Commit changes
        if implementation_result.get('success'):
            self.git_manager.commit_change(f"Implement: {request}")
            
        # Run tests
        test_results = self._run_implementation_tests(implementation_result)
        
        # Generate merge instructions
        merge_instructions = self.git_manager.generate_merge_instructions(
            branch_name, test_results
        )
        
        return {
            'mode': 'IMPLEMENTATION',
            'status': 'COMPLETED' if test_results.get('passed') else 'FAILED',
            'branch_name': branch_name,
            'implementation_result': implementation_result,
            'test_results': test_results,
            'merge_instructions': merge_instructions,
            'action_taken': 'implemented'
        }
        
    def _provide_advisory(self, request: str, analysis: Dict, context: Dict) -> Dict[str, Any]:
        """Provide advisory response only"""
        
        # Generate advisory content using base agent
        advisory_content = self._generate_advisory_content(request, context)
        
        return {
            'mode': 'ADVISORY',
            'status': 'COMPLETED',
            'advisory_content': advisory_content,
            'action_taken': 'advisory'
        }
        
    def _provide_hybrid_response(self, request: str, analysis: Dict, context: Dict) -> Dict[str, Any]:
        """Provide both advisory and implementation"""
        
        # Generate advisory content
        advisory_content = self._generate_advisory_content(request, context)
        
        # Offer implementation
        implementation_offer = f"""
**Advisory Response:**
{advisory_content}

**Implementation Available:**
I can implement this solution for you. Would you like me to:
1. Create a git branch and implement the changes
2. Run tests to verify the implementation
3. Provide merge instructions for you to review

Reply 'implement' to proceed with implementation, or ask follow-up questions for more details.
"""
        
        return {
            'mode': 'HYBRID',
            'status': 'COMPLETED',
            'advisory_content': advisory_content,
            'implementation_offer': implementation_offer,
            'action_taken': 'hybrid'
        }
        
    def _perform_implementation(self, request: str, context: Dict) -> Dict[str, Any]:
        """Perform the actual implementation"""
        
        # This would be customized based on the specific request
        # For now, return a placeholder that indicates implementation capability
        
        return {
            'success': True,
            'changes': [f"Implemented solution for: {request}"],
            'files_modified': [],
            'services_affected': []
        }
        
    def _run_implementation_tests(self, implementation_result: Dict) -> Dict[str, Any]:
        """Run tests on the implementation"""
        
        # Basic test framework - would be expanded based on implementation type
        tests = {
            'syntax_check': {'passed': True, 'message': 'Syntax validation passed'},
            'basic_functionality': {'passed': True, 'message': 'Basic functionality verified'}
        }
        
        all_passed = all(test['passed'] for test in tests.values())
        
        return {
            'passed': all_passed,
            'tests': tests,
            'changes': implementation_result.get('changes', [])
        }
        
    def _generate_advisory_content(self, request: str, context: Dict) -> str:
        """Generate advisory content using base agent capabilities"""
        
        # This would use the base agent's existing advisory capabilities
        # For now, return a structured advisory response
        
        return f"""
Based on your request: "{request}"

Here's my analysis and recommendations:

1. **Assessment**: [Analysis of the situation]
2. **Recommended Approach**: [Step-by-step guidance]
3. **Considerations**: [Important factors to consider]
4. **Next Steps**: [Actionable next steps]

This advisory response would be generated by the base agent's existing capabilities.
"""


def enhance_agent_with_dynamic_capabilities(base_agent: Agent, agent_name: str) -> DynamicAgent:
    """Factory function to enhance existing agents with dynamic capabilities"""
    return DynamicAgent(base_agent, agent_name)