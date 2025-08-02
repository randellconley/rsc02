"""
Interactive Operator Intent Dialogue System

Conducts CLI-friendly Q&A before launching the main CrewAI workflow
to gather comprehensive operator context and intentions.
"""

import sys
from typing import Dict, List, Tuple, Optional


class OperatorDialogue:
    """Handles interactive dialogue with the operator to understand context and intent"""
    
    def __init__(self):
        self.qa_history: List[Tuple[str, str]] = []
        self.operator_context: Dict[str, str] = {}
    
    def analyze_request_gaps(self, user_request: str, execution_context: str) -> List[str]:
        """Analyze user request to identify key context gaps that need clarification"""
        request_lower = user_request.lower()
        questions = []
        
        # Technical context gaps
        if any(tech in request_lower for tech in ['api', 'web', 'app', 'system', 'database', 'server']):
            if not any(lang in request_lower for lang in ['python', 'javascript', 'java', 'go', 'rust', 'php', 'ruby']):
                questions.append("What's your preferred programming language or current tech stack?")
        
        # Purpose gaps
        if not any(purpose in request_lower for purpose in ['learn', 'production', 'work', 'personal', 'experiment']):
            questions.append("Is this for learning, a personal project, or production use?")
        
        # Experience/complexity gaps
        if any(word in request_lower for word in ['create', 'build', 'implement', 'develop']):
            if not any(level in request_lower for level in ['simple', 'basic', 'advanced', 'production', 'enterprise']):
                questions.append("Are you looking for a simple learning example or a production-ready solution?")
        
        # Scope gaps
        if any(word in request_lower for word in ['system', 'platform', 'application']):
            if not any(scope in request_lower for scope in ['prototype', 'mvp', 'full', 'complete', 'basic']):
                questions.append("Do you want something robust from the start, or prefer to start simple and expand?")
        
        # Specific requirements
        if any(word in request_lower for word in ['user', 'auth', 'login', 'management']):
            questions.append("Do you need authentication, user roles, or just basic CRUD operations?")
        elif any(word in request_lower for word in ['api', 'database', 'data']):
            questions.append("Any specific requirements for data storage, authentication, or integrations?")
        
        # Integration context
        if len(questions) < 5:  # Only ask if we haven't hit the limit
            questions.append("Are you starting from scratch or integrating with existing systems?")
        
        # Limit to 5 questions max
        return questions[:5]
    
    def ask_question(self, question: str, question_num: int, total_questions: int) -> str:
        """Ask a single question and get user response"""
        print(f"\n**Question {question_num}/{total_questions}**: {question}")
        print("Your answer: ", end="", flush=True)
        
        try:
            response = input().strip()
            if not response:
                response = "No specific preference"
            return response
        except (KeyboardInterrupt, EOFError):
            print("\n\nDialogue interrupted. Using available context...")
            return "Interrupted"
    
    def conduct_dialogue(self, user_request: str, execution_context: str) -> Dict[str, str]:
        """Conduct the full interactive dialogue"""
        print("\n" + "="*60)
        print("🤖 OPERATOR INTENT INTERPRETER")
        print("="*60)
        print(f"Request: {user_request}")
        print("\nI'd like to understand your context better to provide the most relevant solution.")
        print("This will take 3-5 quick questions:")
        
        # Generate questions based on request analysis
        questions = self.analyze_request_gaps(user_request, execution_context)
        total_questions = len(questions)
        
        # Conduct Q&A
        for i, question in enumerate(questions, 1):
            answer = self.ask_question(question, i, total_questions)
            self.qa_history.append((question, answer))
            
            if answer == "Interrupted":
                break
        
        # Synthesize context
        context = self.synthesize_context(user_request, execution_context)
        
        print("\n" + "="*60)
        print("📋 CONTEXT SYNTHESIS COMPLETE")
        print("="*60)
        print("Proceeding with enhanced workflow...")
        print()
        
        return context
    
    def synthesize_context(self, user_request: str, execution_context: str) -> Dict[str, str]:
        """Synthesize the Q&A dialogue into comprehensive operator context"""
        if not self.qa_history:
            return {
                'original_request': user_request,
                'execution_context': execution_context,
                'operator_context': 'No additional context gathered',
                'enhanced_request': user_request
            }
        
        # Analyze responses
        all_answers = " ".join([answer.lower() for _, answer in self.qa_history])
        
        # Technical background
        tech_background = "Unknown"
        tech_langs = ['python', 'javascript', 'java', 'go', 'rust', 'php', 'ruby', 'node', 'react', 'flask', 'django']
        mentioned_tech = [tech for tech in tech_langs if tech in all_answers]
        if mentioned_tech:
            tech_background = f"Experienced with {', '.join(mentioned_tech)}"
        
        # Project context
        project_context = "General request"
        if "learning" in all_answers or "learn" in all_answers:
            project_context = "Learning/Educational"
        elif "production" in all_answers:
            project_context = "Production/Professional"
        elif "personal" in all_answers:
            project_context = "Personal Project"
        elif "work" in all_answers:
            project_context = "Work/Professional"
        
        # Complexity preference
        complexity_pref = "Moderate"
        if any(word in all_answers for word in ['simple', 'basic', 'minimal', 'easy']):
            complexity_pref = "Simple/Minimal"
        elif any(word in all_answers for word in ['robust', 'production', 'comprehensive', 'solid']):
            complexity_pref = "Robust/Comprehensive"
        elif any(word in all_answers for word in ['enterprise', 'scalable', 'advanced']):
            complexity_pref = "Advanced/Enterprise"
        
        # Build context summary
        qa_summary = "\n".join([f"Q: {q}\nA: {a}" for q, a in self.qa_history])
        
        # Identify unstated needs
        unstated_needs = []
        if any(word in user_request.lower() for word in ['user', 'auth', 'login']):
            if "auth" not in all_answers and "authentication" not in all_answers:
                unstated_needs.append("Likely needs authentication system")
        if any(word in user_request.lower() for word in ['api', 'data']):
            if "database" not in all_answers and "storage" not in all_answers:
                unstated_needs.append("Probably needs data persistence")
        if "production" in all_answers and "test" not in all_answers:
            unstated_needs.append("Should include testing strategy")
        
        # Create enhanced request
        enhanced_request = f"{user_request}\n\nOPERATOR CONTEXT: {project_context} with {complexity_pref.lower()} approach"
        if tech_background != "Unknown":
            enhanced_request += f", using {tech_background.lower()}"
        if unstated_needs:
            enhanced_request += f". Consider: {'; '.join(unstated_needs)}"
        
        context = {
            'original_request': user_request,
            'execution_context': execution_context,
            'technical_background': tech_background,
            'project_context': project_context,
            'complexity_preference': complexity_pref,
            'qa_dialogue': qa_summary,
            'unstated_needs': '; '.join(unstated_needs) if unstated_needs else 'None identified',
            'enhanced_request': enhanced_request,
            'operator_context': f"Operator Profile: {tech_background} developer working on {project_context.lower()} with {complexity_pref.lower()} requirements. {len(unstated_needs)} unstated needs identified."
        }
        
        # Display synthesis
        print(f"\n📊 OPERATOR PROFILE:")
        print(f"   Technical Background: {tech_background}")
        print(f"   Project Context: {project_context}")
        print(f"   Complexity Preference: {complexity_pref}")
        if unstated_needs:
            print(f"   Unstated Needs: {'; '.join(unstated_needs)}")
        
        return context


def conduct_operator_dialogue(user_request: str, execution_context: str = "") -> Dict[str, str]:
    """
    Main function to conduct operator dialogue and return context
    
    Args:
        user_request: The user's original request
        execution_context: Context about where the command was executed
        
    Returns:
        Dict containing comprehensive operator context
    """
    dialogue = OperatorDialogue()
    return dialogue.conduct_dialogue(user_request, execution_context)


if __name__ == "__main__":
    # Test the dialogue system
    if len(sys.argv) > 1:
        request = " ".join(sys.argv[1:])
    else:
        request = "Create a REST API for user management"
    
    context = conduct_operator_dialogue(request, "CLI test")
    print("\nFinal Context:")
    for key, value in context.items():
        print(f"{key}: {value}")