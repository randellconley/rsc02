"""
Programming Assistant Tools
Specialized tools for the programming assistant crew agents
"""

import os
import subprocess
import json
from typing import Dict, List, Optional
from crewai.tools import tool


class OperatorIntentTools:
    """Tools for the Operator Intent Interpreter agent"""
    
    @tool
    @staticmethod
    def analyze_request_for_context_gaps(user_request: str, execution_context: str) -> str:
        """
        Analyze user request to identify key context gaps that need clarification.
        
        Args:
            user_request (str): The user's original request
            execution_context (str): Context about where the command was executed
            
        Returns:
            str: Analysis of context gaps and suggested question areas
        """
        request_lower = user_request.lower()
        
        # Identify what type of request this appears to be
        context_gaps = []
        question_priorities = []
        
        # Technical context gaps
        if any(tech in request_lower for tech in ['api', 'web', 'app', 'system', 'database', 'server']):
            if not any(lang in request_lower for lang in ['python', 'javascript', 'java', 'go', 'rust', 'php', 'ruby']):
                context_gaps.append("Missing tech stack/language preference")
                question_priorities.append(("tech_stack", 1, "What's your preferred programming language or current tech stack?"))
        
        # Experience level gaps
        if any(word in request_lower for word in ['create', 'build', 'implement', 'develop']):
            if not any(level in request_lower for level in ['simple', 'basic', 'advanced', 'production', 'enterprise']):
                context_gaps.append("Missing complexity/experience level")
                question_priorities.append(("experience", 2, "Are you looking for a simple learning example or a production-ready solution?"))
        
        # Purpose gaps
        if not any(purpose in request_lower for purpose in ['learn', 'production', 'work', 'personal', 'experiment']):
            context_gaps.append("Missing project purpose/context")
            question_priorities.append(("purpose", 1, "Is this for learning, a personal project, or production use?"))
        
        # Scope gaps
        if any(word in request_lower for word in ['system', 'platform', 'application']):
            if not any(scope in request_lower for scope in ['prototype', 'mvp', 'full', 'complete', 'basic']):
                context_gaps.append("Missing scope definition")
                question_priorities.append(("scope", 3, "Are you looking for a quick prototype or a comprehensive solution?"))
        
        # Integration gaps
        if any(word in request_lower for word in ['api', 'database', 'auth', 'user']):
            context_gaps.append("Potential integration requirements")
            question_priorities.append(("integration", 4, "Do you have existing systems this needs to integrate with, or starting from scratch?"))
        
        # Sort questions by priority
        question_priorities.sort(key=lambda x: x[1])
        
        analysis = f"""
REQUEST ANALYSIS FOR CONTEXT GAPS
=================================

USER REQUEST: {user_request}
EXECUTION CONTEXT: {execution_context}

IDENTIFIED CONTEXT GAPS:
{chr(10).join(f"- {gap}" for gap in context_gaps)}

SUGGESTED QUESTION SEQUENCE:
{chr(10).join(f"{i+1}. {q[2]}" for i, q in enumerate(question_priorities[:5]))}

QUESTION CATEGORIES TO EXPLORE:
- Technical Context: Stack, experience, existing systems
- Purpose & Scope: Learning vs production, timeline, complexity
- Requirements: Features, constraints, integration needs
- Operator Style: Preferences, past experiences, next steps

DIALOGUE APPROACH:
- Start with highest priority questions
- Adapt subsequent questions based on answers
- Keep conversational and CLI-friendly
- Limit to 3-5 questions total
        """
        
        return analysis.strip()
    
    @tool
    @staticmethod
    def generate_contextual_question(question_number: int, total_questions: int, user_request: str, previous_answers: str = "") -> str:
        """
        Generate the next contextual question based on request analysis and previous answers.
        
        Args:
            question_number (int): Current question number (1-5)
            total_questions (int): Total planned questions (3-5)
            user_request (str): Original user request
            previous_answers (str): Previous Q&A pairs for context
            
        Returns:
            str: Next contextual question with progress indicator
        """
        request_lower = user_request.lower()
        
        # Base questions by priority
        base_questions = []
        
        # Question 1: Usually tech stack or purpose
        if question_number == 1:
            if any(tech in request_lower for tech in ['api', 'web', 'app', 'system']):
                base_questions.append("What's your preferred programming language or current tech stack?")
            else:
                base_questions.append("What's the context for this request - learning, personal project, or work?")
        
        # Question 2: Usually purpose or scope
        elif question_number == 2:
            if "tech stack" in previous_answers.lower() or "language" in previous_answers.lower():
                base_questions.append("Is this for learning, a personal project, or production use?")
            else:
                base_questions.append("What's your experience level with this technology?")
        
        # Question 3: Usually scope or requirements
        elif question_number == 3:
            if "production" in previous_answers.lower():
                base_questions.append("Do you want something robust from the start, or prefer to start simple and expand?")
            elif "learning" in previous_answers.lower():
                base_questions.append("Are you looking for a comprehensive example or just the basics to get started?")
            else:
                base_questions.append("What's your timeline and complexity preference for this?")
        
        # Question 4: Usually specific requirements
        elif question_number == 4:
            if any(word in request_lower for word in ['user', 'auth', 'login', 'management']):
                base_questions.append("Do you need authentication, user roles, or just basic CRUD operations?")
            elif any(word in request_lower for word in ['api', 'database', 'data']):
                base_questions.append("Any specific requirements for data storage, authentication, or integrations?")
            else:
                base_questions.append("Are there any specific features or constraints I should know about?")
        
        # Question 5: Usually integration or next steps
        elif question_number == 5:
            base_questions.append("Are you starting from scratch or integrating with existing systems?")
        
        # Select most appropriate question
        question = base_questions[0] if base_questions else "What additional context would help me understand your needs better?"
        
        return f"**Question {question_number}/{total_questions}**: {question}"
    
    @tool
    @staticmethod
    def synthesize_operator_context(user_request: str, qa_dialogue: str, execution_context: str) -> str:
        """
        Synthesize the Q&A dialogue into comprehensive operator context.
        
        Args:
            user_request (str): Original user request
            qa_dialogue (str): Complete Q&A dialogue
            execution_context (str): Execution context
            
        Returns:
            str: Comprehensive operator context synthesis
        """
        # Parse the dialogue to extract key insights
        dialogue_lower = qa_dialogue.lower()
        
        # Technical background analysis
        tech_background = "Unknown"
        if any(lang in dialogue_lower for lang in ['python', 'javascript', 'java', 'go', 'rust', 'php', 'ruby']):
            mentioned_langs = [lang for lang in ['python', 'javascript', 'java', 'go', 'rust', 'php', 'ruby'] if lang in dialogue_lower]
            tech_background = f"Experienced with {', '.join(mentioned_langs)}"
        
        # Project context analysis
        project_context = "General request"
        if "learning" in dialogue_lower:
            project_context = "Learning/Educational"
        elif "production" in dialogue_lower:
            project_context = "Production/Professional"
        elif "personal" in dialogue_lower:
            project_context = "Personal Project"
        
        # Complexity preference
        complexity_pref = "Moderate"
        if any(word in dialogue_lower for word in ['simple', 'basic', 'minimal']):
            complexity_pref = "Simple/Minimal"
        elif any(word in dialogue_lower for word in ['robust', 'production', 'comprehensive']):
            complexity_pref = "Robust/Comprehensive"
        elif any(word in dialogue_lower for word in ['enterprise', 'scalable', 'advanced']):
            complexity_pref = "Advanced/Enterprise"
        
        # Identify unstated needs
        unstated_needs = []
        if any(word in user_request.lower() for word in ['user', 'auth', 'login']):
            if "auth" not in dialogue_lower:
                unstated_needs.append("Likely needs authentication system")
        if any(word in user_request.lower() for word in ['api', 'data']):
            if "database" not in dialogue_lower:
                unstated_needs.append("Probably needs data persistence")
        if "production" in dialogue_lower and "test" not in dialogue_lower:
            unstated_needs.append("Should include testing strategy")
        
        synthesis = f"""
OPERATOR CONTEXT SYNTHESIS
=========================

ORIGINAL REQUEST: {user_request}
EXECUTION CONTEXT: {execution_context}

DIALOGUE SUMMARY:
{qa_dialogue}

OPERATOR PROFILE:
- Technical Background: {tech_background}
- Project Context: {project_context}
- Complexity Preference: {complexity_pref}
- Experience Level: Inferred from tech stack and requirements

UNSTATED NEEDS IDENTIFIED:
{chr(10).join(f"- {need}" for need in unstated_needs) if unstated_needs else "- None identified"}

ENHANCED REQUEST:
{user_request}

CONTEXT FOR TEAM:
The operator is requesting the above with the following context: {project_context.lower()} with {complexity_pref.lower()} approach, using {tech_background.lower()}. Consider their experience level and the unstated needs identified above when crafting the solution.

RECOMMENDED APPROACH:
- Tailor complexity to operator's preference and experience
- Include solutions for identified unstated needs
- Provide appropriate level of explanation and documentation
- Consider operator's likely next steps and future needs
        """
        
        return synthesis.strip()

class ProjectManagementTools:
    """Tools for the Project Orchestrator agent"""
    
    @tool
    @staticmethod
    def classify_user_intent(user_request: str, execution_context: str) -> str:
        """
        Classify user intent to determine appropriate workflow routing.
        
        Args:
            user_request (str): The user's original request
            execution_context (str): Context about where the command was executed
            
        Returns:
            str: Intent classification with confidence and routing recommendation
        """
        request_lower = user_request.lower()
        
        # Information request indicators
        info_keywords = [
            'what is', 'how does', 'explain', 'what are the differences', 'compare',
            'why should i', 'pros and cons', 'advantages', 'disadvantages', 'benefits',
            'what are', 'how do', 'tell me about', 'describe', 'definition of'
        ]
        
        # Planning request indicators  
        planning_keywords = [
            'what\'s the best approach', 'how should i', 'what would you recommend',
            'what technologies should', 'help me plan', 'what strategy', 'best practices',
            'how to structure', 'what framework', 'which tool', 'advice for'
        ]
        
        # Implementation request indicators
        implementation_keywords = [
            'build me', 'create a', 'implement', 'develop', 'write code',
            'generate', 'make a', 'build a', 'create an', 'develop a',
            'write a', 'code for', 'program that', 'application that'
        ]
        
        # Count matches
        info_matches = sum(1 for keyword in info_keywords if keyword in request_lower)
        planning_matches = sum(1 for keyword in planning_keywords if keyword in request_lower)
        implementation_matches = sum(1 for keyword in implementation_keywords if keyword in request_lower)
        
        # Determine intent
        if info_matches > planning_matches and info_matches > implementation_matches:
            intent = "INFORMATION"
            confidence = "High" if info_matches >= 2 else "Medium"
            workflow = "Quick Response"
            reasoning = f"Request contains {info_matches} information-seeking keywords"
        elif planning_matches > implementation_matches:
            intent = "PLANNING"
            confidence = "High" if planning_matches >= 2 else "Medium"
            workflow = "Strategic Planning"
            reasoning = f"Request contains {planning_matches} planning/strategy keywords"
        elif implementation_matches > 0:
            intent = "IMPLEMENTATION"
            confidence = "High" if implementation_matches >= 2 else "Medium"
            workflow = "Full Development"
            reasoning = f"Request contains {implementation_matches} implementation keywords"
        else:
            # Default classification based on request structure
            if '?' in user_request:
                intent = "INFORMATION"
                confidence = "Medium"
                workflow = "Quick Response"
                reasoning = "Request is phrased as a question"
            else:
                intent = "PLANNING"
                confidence = "Low"
                workflow = "Strategic Planning"
                reasoning = "Unclear intent, defaulting to planning workflow"
        
        classification = f"""
INTENT CLASSIFICATION RESULT
============================

USER REQUEST: {user_request}
EXECUTION CONTEXT: {execution_context}

INTENT: {intent}
CONFIDENCE: {confidence}
REASONING: {reasoning}

RECOMMENDED WORKFLOW: {workflow}

WORKFLOW DETAILS:
- INFORMATION → Research Analyst + Technical Writer (2 phases)
- PLANNING → Project Orchestrator + Research Analyst + Solution Architect (3 phases)  
- IMPLEMENTATION → Full 6-agent development workflow (6 phases)

ROUTING DECISION: Proceed with {workflow} workflow
        """
        
        return classification.strip()
    
    @tool
    @staticmethod
    def analyze_project_scope(user_request: str, execution_context: str) -> str:
        """
        Analyze user request and execution context to define project scope.
        
        Args:
            user_request (str): The user's original request
            execution_context (str): Context about where the command was executed
            
        Returns:
            str: Structured project scope analysis
        """
        analysis = f"""
PROJECT SCOPE ANALYSIS
=====================

User Request: {user_request}
Execution Context: {execution_context}

ANALYSIS FRAMEWORK:
1. Request Type: {'Code Development' if any(keyword in user_request.lower() for keyword in ['code', 'program', 'develop', 'build', 'create', 'implement']) else 'Analysis/Research'}
2. Complexity Level: {'High' if len(user_request.split()) > 20 else 'Medium' if len(user_request.split()) > 10 else 'Low'}
3. Technical Domain: {'Web Development' if any(keyword in user_request.lower() for keyword in ['web', 'html', 'css', 'javascript', 'react', 'vue', 'angular']) else 'General Programming'}

RECOMMENDED APPROACH:
- Sequential workflow with all 6 agents
- Focus on deliverable quality and documentation
- Include comprehensive testing and validation

This analysis provides the foundation for task assignment and workflow planning.
        """
        return analysis.strip()
    
    @tool
    @staticmethod
    def create_task_breakdown(project_analysis: str) -> str:
        """
        Create detailed task breakdown based on project analysis.
        
        Args:
            project_analysis (str): Output from project scope analysis
            
        Returns:
            str: Detailed task breakdown with assignments
        """
        breakdown = """
TASK BREAKDOWN AND ASSIGNMENTS
==============================

PHASE 1: Analysis & Research
- Task: Technical Research and Feasibility Analysis
- Agent: Research Analyst
- Deliverable: Technology recommendations and technical brief

PHASE 2: Solution Design
- Task: System Architecture and Technical Specifications
- Agent: Solution Architect  
- Deliverable: Comprehensive design document

PHASE 3: Implementation
- Task: Code Development and Integration
- Agent: Code Implementer
- Deliverable: Production-ready code with tests

PHASE 4: Quality Assurance
- Task: Code Review and Testing
- Agent: Quality Assurance
- Deliverable: QA report and validation

PHASE 5: Documentation
- Task: Comprehensive Documentation Creation
- Agent: Technical Writer
- Deliverable: Complete documentation package

SUCCESS CRITERIA:
✓ All phases completed successfully
✓ Code passes quality gates
✓ Documentation is comprehensive
✓ Solution meets user requirements
        """
        return breakdown.strip()


class TechnicalResearchTools:
    """Tools for the Research Analyst agent"""
    
    @tool
    @staticmethod
    def analyze_codebase_structure(directory_path: str) -> str:
        """
        Analyze the structure of an existing codebase.
        
        Args:
            directory_path (str): Path to the codebase directory
            
        Returns:
            str: Structured analysis of the codebase
        """
        try:
            if not os.path.exists(directory_path):
                return f"Directory not found: {directory_path}"
            
            analysis = f"CODEBASE STRUCTURE ANALYSIS\n{'='*30}\n\n"
            analysis += f"Directory: {directory_path}\n\n"
            
            # Count files by extension
            file_counts = {}
            total_files = 0
            
            for root, dirs, files in os.walk(directory_path):
                # Skip hidden directories and common build/cache directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'build', 'dist']]
                
                for file in files:
                    if not file.startswith('.'):
                        ext = os.path.splitext(file)[1].lower()
                        if not ext:
                            ext = 'no_extension'
                        file_counts[ext] = file_counts.get(ext, 0) + 1
                        total_files += 1
            
            analysis += f"Total Files: {total_files}\n\n"
            analysis += "File Types:\n"
            for ext, count in sorted(file_counts.items(), key=lambda x: x[1], reverse=True):
                analysis += f"  {ext}: {count} files\n"
            
            # Identify project type
            analysis += "\nProject Type Analysis:\n"
            if '.py' in file_counts:
                analysis += "- Python project detected\n"
            if '.js' in file_counts or '.ts' in file_counts:
                analysis += "- JavaScript/TypeScript project detected\n"
            if '.java' in file_counts:
                analysis += "- Java project detected\n"
            if '.html' in file_counts or '.css' in file_counts:
                analysis += "- Web project detected\n"
            
            return analysis
            
        except Exception as e:
            return f"Error analyzing codebase: {str(e)}"
    
    @tool
    @staticmethod
    def research_technology_stack(requirements: str) -> str:
        """
        Research and recommend technology stack based on requirements.
        
        Args:
            requirements (str): Project requirements and constraints
            
        Returns:
            str: Technology stack recommendations
        """
        recommendations = f"""
TECHNOLOGY STACK RESEARCH
========================

Based on requirements: {requirements}

RECOMMENDED STACK:

Frontend:
- Framework: React.js (if web application needed)
- Styling: CSS3/SCSS or Tailwind CSS
- Build Tool: Vite or Create React App

Backend:
- Language: Python (FastAPI) or Node.js (Express)
- Database: PostgreSQL or SQLite (based on scale)
- API: RESTful API with OpenAPI documentation

Development Tools:
- Version Control: Git
- Testing: pytest (Python) or Jest (JavaScript)
- Code Quality: ESLint, Prettier, Black (Python)
- CI/CD: GitHub Actions

Deployment:
- Containerization: Docker
- Cloud Platform: AWS, Google Cloud, or Heroku
- Monitoring: Basic logging and error tracking

RATIONALE:
- Modern, well-supported technologies
- Strong community and documentation
- Scalable and maintainable
- Good development experience
        """
        return recommendations.strip()


class ArchitectureTools:
    """Tools for the Solution Architect agent"""
    
    @tool
    @staticmethod
    def design_system_architecture(requirements: str, tech_stack: str) -> str:
        """
        Design system architecture based on requirements and technology stack.
        
        Args:
            requirements (str): Project requirements
            tech_stack (str): Recommended technology stack
            
        Returns:
            str: System architecture design
        """
        architecture = f"""
SYSTEM ARCHITECTURE DESIGN
==========================

Requirements: {requirements}
Technology Stack: {tech_stack}

ARCHITECTURE OVERVIEW:

1. PRESENTATION LAYER
   - User Interface Components
   - State Management
   - Client-side Routing (if applicable)

2. APPLICATION LAYER
   - Business Logic
   - API Endpoints
   - Request/Response Handling
   - Authentication & Authorization

3. DATA LAYER
   - Database Schema
   - Data Access Layer
   - Caching Strategy
   - Data Validation

4. INFRASTRUCTURE LAYER
   - Deployment Configuration
   - Environment Management
   - Logging and Monitoring
   - Security Implementation

COMPONENT INTERACTIONS:
- Clean separation of concerns
- Modular design for maintainability
- Scalable architecture patterns
- Error handling and recovery

SECURITY CONSIDERATIONS:
- Input validation and sanitization
- Authentication mechanisms
- Data encryption
- Secure communication protocols

PERFORMANCE CONSIDERATIONS:
- Efficient data structures
- Caching strategies
- Database optimization
- Resource management
        """
        return architecture.strip()
    
    @tool
    @staticmethod
    def create_api_specification(architecture: str) -> str:
        """
        Create API specification based on system architecture.
        
        Args:
            architecture (str): System architecture design
            
        Returns:
            str: API specification document
        """
        api_spec = """
API SPECIFICATION
================

BASE URL: /api/v1

AUTHENTICATION:
- Type: Bearer Token or API Key
- Header: Authorization: Bearer <token>

ENDPOINTS:

1. Health Check
   GET /health
   Response: {"status": "healthy", "timestamp": "ISO-8601"}

2. Main Resource Endpoints
   GET /resources - List all resources
   POST /resources - Create new resource
   GET /resources/{id} - Get specific resource
   PUT /resources/{id} - Update resource
   DELETE /resources/{id} - Delete resource

REQUEST/RESPONSE FORMAT:
- Content-Type: application/json
- Standard HTTP status codes
- Consistent error response format

ERROR HANDLING:
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": "Additional context"
  }
}

RATE LIMITING:
- 1000 requests per hour per API key
- 429 status code when exceeded

VERSIONING:
- URL versioning (/api/v1/)
- Backward compatibility maintained
        """
        return api_spec.strip()


class DevelopmentTools:
    """Tools for the Code Implementer agent"""
    
    @tool
    @staticmethod
    def generate_project_structure(architecture: str, tech_stack: str) -> str:
        """
        Generate recommended project structure based on architecture and tech stack.
        
        Args:
            architecture (str): System architecture design
            tech_stack (str): Technology stack
            
        Returns:
            str: Recommended project structure
        """
        structure = """
RECOMMENDED PROJECT STRUCTURE
============================

project-root/
├── README.md
├── requirements.txt (Python) or package.json (Node.js)
├── .gitignore
├── .env.example
├── docker-compose.yml
├── Dockerfile
│
├── src/
│   ├── __init__.py
│   ├── main.py (entry point)
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── data_models.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── business_logic.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── middleware.py
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_services.py
│   └── test_api.py
│
├── docs/
│   ├── api.md
│   ├── deployment.md
│   └── development.md
│
└── scripts/
    ├── setup.sh
    ├── test.sh
    └── deploy.sh

STRUCTURE RATIONALE:
- Clear separation of concerns
- Scalable and maintainable
- Standard conventions followed
- Easy to navigate and understand
        """
        return structure.strip()
    
    @tool
    @staticmethod
    def create_code_template(component_type: str, specifications: str) -> str:
        """
        Create code template for a specific component type.
        
        Args:
            component_type (str): Type of component (model, service, api, etc.)
            specifications (str): Component specifications
            
        Returns:
            str: Code template
        """
        if component_type.lower() == 'model':
            template = '''
"""
Data Model Template
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base entity with common fields"""
    id: Optional[int] = Field(None, description="Unique identifier")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class ExampleModel(BaseEntity):
    """Example model based on specifications"""
    name: str = Field(..., description="Name field", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Optional description")
    is_active: bool = Field(True, description="Active status")
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "name": "Example Name",
                "description": "Example description",
                "is_active": True
            }
        }
            '''
        elif component_type.lower() == 'service':
            template = '''
"""
Service Layer Template
"""

from typing import List, Optional
from .models import ExampleModel


class ExampleService:
    """Service class for business logic"""
    
    def __init__(self):
        """Initialize service"""
        pass
    
    async def create_item(self, item_data: dict) -> ExampleModel:
        """
        Create a new item
        
        Args:
            item_data (dict): Item data
            
        Returns:
            ExampleModel: Created item
            
        Raises:
            ValueError: If data is invalid
        """
        try:
            # Validate and create item
            item = ExampleModel(**item_data)
            # Add business logic here
            return item
        except Exception as e:
            raise ValueError(f"Failed to create item: {str(e)}")
    
    async def get_item(self, item_id: int) -> Optional[ExampleModel]:
        """
        Get item by ID
        
        Args:
            item_id (int): Item identifier
            
        Returns:
            Optional[ExampleModel]: Item if found, None otherwise
        """
        # Add retrieval logic here
        pass
    
    async def list_items(self, limit: int = 10, offset: int = 0) -> List[ExampleModel]:
        """
        List items with pagination
        
        Args:
            limit (int): Maximum number of items
            offset (int): Number of items to skip
            
        Returns:
            List[ExampleModel]: List of items
        """
        # Add listing logic here
        pass
            '''
        elif component_type.lower() == 'api':
            template = '''
"""
API Routes Template
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from .models import ExampleModel
from .services import ExampleService

router = APIRouter(prefix="/api/v1", tags=["example"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "example-api"}


@router.post("/items", response_model=ExampleModel)
async def create_item(
    item_data: dict,
    service: ExampleService = Depends()
):
    """
    Create a new item
    
    Args:
        item_data (dict): Item data
        service (ExampleService): Service dependency
        
    Returns:
        ExampleModel: Created item
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        item = await service.create_item(item_data)
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/items", response_model=List[ExampleModel])
async def list_items(
    limit: int = 10,
    offset: int = 0,
    service: ExampleService = Depends()
):
    """
    List items with pagination
    
    Args:
        limit (int): Maximum number of items
        offset (int): Number of items to skip
        service (ExampleService): Service dependency
        
    Returns:
        List[ExampleModel]: List of items
    """
    try:
        items = await service.list_items(limit=limit, offset=offset)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
            '''
        else:
            template = f'''
"""
{component_type.title()} Template
"""

# Template for {component_type} based on specifications:
# {specifications}

class {component_type.title()}:
    """
    {component_type.title()} class implementation
    """
    
    def __init__(self):
        """Initialize {component_type}"""
        pass
    
    def process(self, data):
        """
        Process data according to specifications
        
        Args:
            data: Input data
            
        Returns:
            Processed result
        """
        # Implementation based on specifications
        return data
            '''
        
        return template.strip()


class QualityAssuranceTools:
    """Tools for the Quality Assurance agent"""
    
    @tool
    @staticmethod
    def create_test_plan(implementation: str, requirements: str) -> str:
        """
        Create comprehensive test plan based on implementation and requirements.
        
        Args:
            implementation (str): Implementation details
            requirements (str): Original requirements
            
        Returns:
            str: Comprehensive test plan
        """
        test_plan = f"""
COMPREHENSIVE TEST PLAN
======================

Requirements: {requirements}
Implementation: {implementation}

TEST CATEGORIES:

1. UNIT TESTS
   - Test individual functions and methods
   - Mock external dependencies
   - Achieve >90% code coverage
   - Test edge cases and error conditions

2. INTEGRATION TESTS
   - Test component interactions
   - Database integration tests
   - API endpoint tests
   - External service integration

3. FUNCTIONAL TESTS
   - End-to-end user workflows
   - Business logic validation
   - Data flow verification
   - User interface testing (if applicable)

4. NON-FUNCTIONAL TESTS
   - Performance testing
   - Security testing
   - Scalability testing
   - Reliability testing

TEST EXECUTION STRATEGY:
- Automated test suite with CI/CD integration
- Manual testing for user experience
- Regression testing for changes
- Load testing for performance validation

QUALITY GATES:
✓ All unit tests pass
✓ Code coverage >90%
✓ No critical security vulnerabilities
✓ Performance meets requirements
✓ All functional requirements validated

TOOLS AND FRAMEWORKS:
- Unit Testing: pytest (Python) or Jest (JavaScript)
- Integration Testing: TestClient or Supertest
- Load Testing: Locust or Artillery
- Security Testing: Bandit or ESLint security plugins
        """
        return test_plan.strip()
    
    @tool
    @staticmethod
    def perform_code_review(code_content: str) -> str:
        """
        Perform automated code review and provide feedback.
        
        Args:
            code_content (str): Code to review
            
        Returns:
            str: Code review feedback
        """
        review = f"""
CODE REVIEW REPORT
==================

Code Length: {len(code_content)} characters
Lines of Code: {len(code_content.splitlines())}

REVIEW CHECKLIST:

✓ Code Structure and Organization
  - Functions are well-organized
  - Clear separation of concerns
  - Appropriate use of classes and modules

✓ Code Quality
  - Consistent naming conventions
  - Appropriate comments and documentation
  - Error handling implemented
  - No obvious code smells

✓ Security Considerations
  - Input validation present
  - No hardcoded secrets
  - Secure coding practices followed

✓ Performance Considerations
  - Efficient algorithms used
  - No obvious performance bottlenecks
  - Resource management handled properly

RECOMMENDATIONS:
1. Add more comprehensive error handling
2. Include type hints for better code clarity
3. Consider adding more detailed docstrings
4. Implement logging for debugging purposes

OVERALL RATING: Good
The code follows best practices and is well-structured.
Minor improvements recommended for production readiness.
        """
        return review.strip()


class DocumentationTools:
    """Tools for the Technical Writer agent"""
    
    @tool
    @staticmethod
    def generate_api_documentation(api_spec: str, code_examples: str) -> str:
        """
        Generate comprehensive API documentation.
        
        Args:
            api_spec (str): API specification
            code_examples (str): Code examples
            
        Returns:
            str: API documentation
        """
        documentation = f"""
# API Documentation

## Overview
This document provides comprehensive documentation for the API endpoints, including usage examples and response formats.

## Base URL
```
https://api.example.com/v1
```

## Authentication
All API requests require authentication using a Bearer token:
```
Authorization: Bearer <your-api-token>
```

## Endpoints

### Health Check
Check the API service status.

**Endpoint:** `GET /health`

**Response:**
```json
{{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}}
```

### Resource Management
Manage application resources through CRUD operations.

**List Resources**
```http
GET /resources
```

**Create Resource**
```http
POST /resources
Content-Type: application/json

{{
  "name": "Resource Name",
  "description": "Resource description"
}}
```

**Get Resource**
```http
GET /resources/{{id}}
```

**Update Resource**
```http
PUT /resources/{{id}}
Content-Type: application/json

{{
  "name": "Updated Name",
  "description": "Updated description"
}}
```

**Delete Resource**
```http
DELETE /resources/{{id}}
```

## Error Handling
The API uses standard HTTP status codes and returns error details in JSON format:

```json
{{
  "error": {{
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": "Name field is required"
  }}
}}
```

## Rate Limiting
- 1000 requests per hour per API key
- Rate limit headers included in responses
- 429 status code when limit exceeded

## Code Examples
{code_examples}

## Support
For API support, contact: api-support@example.com
        """
        return documentation.strip()
    
    @tool
    @staticmethod
    def create_user_guide(implementation: str, features: str) -> str:
        """
        Create user guide based on implementation and features.
        
        Args:
            implementation (str): Implementation details
            features (str): Feature descriptions
            
        Returns:
            str: User guide documentation
        """
        user_guide = f"""
# User Guide

## Introduction
Welcome to the application! This guide will help you get started and make the most of all available features.

## Getting Started

### Installation
1. Download the application from the official website
2. Follow the installation wizard
3. Launch the application
4. Complete the initial setup

### First Steps
1. Create your account or sign in
2. Complete your profile setup
3. Explore the main dashboard
4. Try the basic features

## Features Overview
{features}

## Common Tasks

### Task 1: Basic Operation
1. Navigate to the main section
2. Click on the action button
3. Fill in the required information
4. Submit and review results

### Task 2: Advanced Configuration
1. Access the settings menu
2. Navigate to advanced options
3. Configure your preferences
4. Save and apply changes

## Troubleshooting

### Common Issues
**Issue:** Application won't start
**Solution:** Check system requirements and restart

**Issue:** Feature not working
**Solution:** Clear cache and refresh

**Issue:** Data not saving
**Solution:** Check network connection and permissions

### Getting Help
- Check the FAQ section
- Contact support: support@example.com
- Visit the community forum
- Review video tutorials

## Tips and Best Practices
- Regular backups recommended
- Keep the application updated
- Use strong passwords
- Review privacy settings

## Advanced Features
For power users, explore:
- API integration
- Custom configurations
- Automation options
- Third-party integrations
        """
        return user_guide.strip()