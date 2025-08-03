"""
Interactive Operator Intent Dialogue System - Hybrid Approach

Conducts CLI-friendly Q&A before launching the main CrewAI workflow
using cached domain patterns for known domains and dynamic generation for novel requests.
"""

import sys
import re
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DomainMatch:
    domain: str
    confidence: float
    keywords_found: List[str]


class OperatorDialogue:
    """Handles interactive dialogue with hybrid cached/dynamic questioning"""
    
    def __init__(self):
        self.qa_history: List[Tuple[str, str]] = []
        self.operator_context: Dict[str, str] = {}
        self.domain_patterns = self._initialize_domain_patterns()
        self.domain_questions = self._initialize_domain_questions()
        self._cached_questions: Optional[List[str]] = None
    
    def _initialize_domain_patterns(self) -> Dict:
        """Initialize domain detection patterns (cache)"""
        return {
            'web_development': {
                'keywords': ['api', 'rest', 'web', 'frontend', 'backend', 'server', 'endpoint', 'http', 'json', 'flask', 'django', 'express', 'fastapi'],
                'concepts': ['authentication', 'routing', 'middleware', 'cors', 'crud'],
                'weight': 1.0
            },
            'machine_learning': {
                'keywords': ['ml', 'model', 'prediction', 'classification', 'regression', 'neural', 'ai', 'training', 'classifier', 'algorithm'],
                'concepts': ['dataset', 'features', 'accuracy', 'supervised', 'unsupervised'],
                'weight': 1.0
            },
            'database': {
                'keywords': ['database', 'schema', 'sql', 'nosql', 'query', 'table', 'data', 'storage', 'postgresql', 'mysql', 'mongodb'],
                'concepts': ['relationships', 'indexing', 'normalization', 'transactions'],
                'weight': 1.0
            },
            'mobile_development': {
                'keywords': ['mobile', 'app', 'ios', 'android', 'react native', 'flutter', 'native'],
                'concepts': ['cross-platform', 'app store', 'responsive', 'touch'],
                'weight': 1.0
            },
            'devops': {
                'keywords': ['deploy', 'ci/cd', 'docker', 'kubernetes', 'pipeline', 'automation'],
                'concepts': ['monitoring', 'scaling', 'infrastructure', 'containerization'],
                'weight': 1.0
            },
            'data_analysis': {
                'keywords': ['analysis', 'visualization', 'dashboard', 'report', 'analytics', 'insights'],
                'concepts': ['charts', 'metrics', 'kpi', 'business intelligence'],
                'weight': 1.0
            }
        }
    
    def _initialize_domain_questions(self) -> Dict:
        """Initialize domain-specific question banks (cache)"""
        return {
            'web_development': {
                'technology_stack': [
                    "What's your preferred backend framework? (Flask, Django, Express, FastAPI, etc.)",
                    "Frontend requirements? (React, Vue, vanilla JS, or API-only?)",
                    "Database preference? (PostgreSQL, MySQL, MongoDB, etc.)"
                ],
                'architecture': [
                    "Authentication method? (JWT, OAuth, sessions, or none needed?)",
                    "Expected scale? (personal project, small team, or high traffic?)",
                    "Deployment preference? (cloud, local, or containerized?)"
                ],
                'requirements': [
                    "Any specific integrations needed? (payment, email, third-party APIs)",
                    "Real-time features required? (WebSockets, live updates)"
                ]
            },
            'machine_learning': {
                'problem_type': [
                    "What type of ML problem? (classification, regression, clustering, NLP, computer vision)",
                    "Supervised or unsupervised learning?",
                    "Real-time predictions or batch processing?"
                ],
                'data': [
                    "Do you have a dataset ready, or need help finding/creating one?",
                    "Data size and format? (CSV, JSON, images, text files)",
                    "Any data privacy or compliance requirements?"
                ],
                'deployment': [
                    "Model deployment target? (local testing, cloud API, edge device)",
                    "Performance requirements? (speed vs accuracy trade-offs)"
                ]
            },
            'database': {
                'design': [
                    "Primary use case? (transactional, analytical, real-time, or mixed)",
                    "Expected data volume and growth? (MB, GB, TB scale)",
                    "Query patterns? (simple lookups, complex joins, aggregations)"
                ],
                'technology': [
                    "SQL or NoSQL preference? (or unsure)",
                    "Consistency vs performance priorities?",
                    "Integration with existing systems?"
                ]
            },
            'mobile_development': {
                'platform': [
                    "Target platforms? (iOS only, Android only, or both)",
                    "Native performance needs or web-based acceptable?",
                    "App store distribution or internal/enterprise use?"
                ],
                'features': [
                    "Key features needed? (offline support, push notifications, camera, etc.)",
                    "Backend integration requirements? (APIs, databases, cloud services)"
                ]
            },
            'devops': {
                'infrastructure': [
                    "Current deployment process? (manual, basic scripts, or automated)",
                    "Target platforms? (AWS, Azure, GCP, on-premise, or hybrid)",
                    "Team size and release frequency?"
                ],
                'requirements': [
                    "Primary goals? (faster deployments, reliability, cost optimization)",
                    "Compliance or security requirements? (SOC2, HIPAA, etc.)"
                ]
            },
            'data_analysis': {
                'scope': [
                    "Data source? (databases, files, APIs, or need to collect)",
                    "Analysis type? (descriptive, predictive, or prescriptive)",
                    "Audience? (technical team, executives, or external clients)"
                ],
                'output': [
                    "Preferred output format? (interactive dashboard, static reports, or automated alerts)",
                    "Update frequency? (real-time, daily, weekly, or on-demand)"
                ]
            }
        }
    
    def detect_domains(self, request: str) -> List[DomainMatch]:
        """Detect domains with confidence scoring"""
        request_lower = request.lower()
        domain_matches = []
        
        for domain, pattern in self.domain_patterns.items():
            score = 0.0
            keywords_found = []
            
            # Check keywords
            for keyword in pattern['keywords']:
                if keyword in request_lower:
                    score += 2.0  # Increased weight for keywords
                    keywords_found.append(keyword)
            
            # Check concepts (weighted higher)
            for concept in pattern['concepts']:
                if concept in request_lower:
                    score += 3.0  # Increased weight for concepts
                    keywords_found.append(concept)
            
            # Calculate confidence based on matches found, not total possible
            if keywords_found:
                # Base confidence on number of matches found
                base_confidence = min(score / 10.0, 1.0)  # Scale to 0-1
                # Boost confidence for multiple matches
                match_bonus = min(len(keywords_found) * 0.1, 0.3)
                confidence = min(base_confidence + match_bonus, 1.0)
                
                domain_matches.append(DomainMatch(domain, confidence, keywords_found))
        
        # Sort by confidence
        return sorted(domain_matches, key=lambda x: x.confidence, reverse=True)
    
    def select_questioning_strategy(self, request: str) -> Tuple[str, Optional[str]]:
        """Decide between cached or dynamic approach"""
        domain_matches = self.detect_domains(request)
        confidence_threshold = 0.15  # Lower threshold for better cache utilization
        
        if domain_matches and domain_matches[0].confidence >= confidence_threshold:
            return "CACHED", domain_matches[0].domain
        else:
            return "DYNAMIC", None
    
    def get_cached_questions(self, domain: str, request: str) -> List[str]:
        """Get prioritized questions for a known domain"""
        if domain not in self.domain_questions:
            return []
        
        domain_bank = self.domain_questions[domain]
        questions = []
        
        # Prioritize question categories based on request analysis
        for category, category_questions in domain_bank.items():
            # Add most relevant questions from each category
            questions.extend(category_questions[:2])  # Max 2 per category
        
        # Filter out questions already answered by request context
        filtered_questions = self.filter_redundant_questions(questions, request)
        
        return filtered_questions[:5]  # Max 5 questions
    
    def filter_redundant_questions(self, questions: List[str], request: str) -> List[str]:
        """Remove questions already answered by the request context"""
        request_lower = request.lower()
        filtered = []
        
        for question in questions:
            # Skip if request already contains relevant information
            if "framework" in question.lower() and any(fw in request_lower for fw in ['flask', 'django', 'express', 'react']):
                continue
            if "platform" in question.lower() and any(pl in request_lower for pl in ['ios', 'android', 'web']):
                continue
            if "database" in question.lower() and any(db in request_lower for db in ['postgres', 'mysql', 'mongo']):
                continue
            
            filtered.append(question)
        
        return filtered
    
    def generate_dynamic_question(self, request: str, question_number: int, max_questions: int) -> Optional[str]:
        """Generate questions dynamically for unknown domains"""
        context = self.extract_context_from_history()
        
        if question_number == 1:
            return self.identify_core_challenge_question(request)
        elif question_number == 2:
            return self.generate_technology_question(request, context)
        elif question_number == 3:
            return self.generate_scope_question(request, context)
        elif question_number == 4:
            return self.generate_requirements_question(request, context)
        elif question_number == 5:
            return self.generate_context_question(request, context)
        
        return None
    
    def identify_core_challenge_question(self, request: str) -> str:
        """Generate first question to understand the core challenge"""
        if any(word in request.lower() for word in ['create', 'build', 'develop', 'implement']):
            return "What's the main challenge or goal you're trying to solve with this?"
        elif any(word in request.lower() for word in ['analyze', 'understand', 'explain']):
            return "What specific aspect would be most helpful to focus on?"
        elif any(word in request.lower() for word in ['fix', 'debug', 'troubleshoot']):
            return "What symptoms or issues are you experiencing?"
        else:
            return "What's your primary objective with this request?"
    
    def generate_technology_question(self, request: str, context: Dict) -> str:
        """Generate technology-focused question based on context"""
        if 'technology' not in context:
            return "What technologies or tools are you currently using or prefer to use?"
        else:
            return "Any specific technical constraints or requirements to consider?"
    
    def generate_scope_question(self, request: str, context: Dict) -> str:
        """Generate scope/complexity question"""
        if 'scope' not in context:
            return "Is this for learning/experimentation or production use?"
        else:
            return "What level of complexity or robustness do you need?"
    
    def generate_requirements_question(self, request: str, context: Dict) -> str:
        """Generate requirements-focused question"""
        return "Any specific requirements, constraints, or integrations needed?"
    
    def generate_context_question(self, request: str, context: Dict) -> str:
        """Generate contextual question"""
        return "Are you starting from scratch or working with existing systems?"
    
    def extract_context_from_history(self) -> Dict[str, str]:
        """Extract context from previous Q&A"""
        context = {}
        for question, answer in self.qa_history:
            if any(word in question.lower() for word in ['technology', 'framework', 'language']):
                context['technology'] = answer
            elif any(word in question.lower() for word in ['scope', 'complexity', 'production']):
                context['scope'] = answer
            elif any(word in question.lower() for word in ['challenge', 'goal', 'objective']):
                context['objective'] = answer
        return context
    
    def generate_next_question(self, user_request: str, execution_context: str, question_num: int, max_questions: int) -> Optional[str]:
        """Generate next question using hybrid approach"""
        strategy, domain = self.select_questioning_strategy(user_request)
        
        if strategy == "CACHED" and domain:
            # Use cached questions for known domains
            if not self._cached_questions:
                self._cached_questions = self.get_cached_questions(domain, user_request)
                print(f"🎯 Detected domain: {domain.replace('_', ' ').title()} (using optimized questions)")
            
            if question_num <= len(self._cached_questions):
                return self._cached_questions[question_num - 1]
            else:
                return None  # No more cached questions
        else:
            # Use dynamic generation for unknown domains
            if question_num == 1:
                print("🔍 Novel request detected (using adaptive questioning)")
            return self.generate_dynamic_question(user_request, question_num, max_questions)
    
    def has_sufficient_context(self) -> bool:
        """Check if we have enough context to proceed"""
        if len(self.qa_history) < 2:
            return False
        
        # Check if we have key context areas covered
        context = self.extract_context_from_history()
        essential_areas = ['technology', 'scope', 'objective']
        covered_areas = sum(1 for area in essential_areas if area in context)
        
        return covered_areas >= 2 or len(self.qa_history) >= 4
    
    def _get_test_mode_answer(self, question: str, question_num: int) -> str:
        """Generate appropriate default answers for test mode"""
        question_lower = question.lower()
        
        # Provide context-aware default answers based on question content
        if 'aspect' in question_lower or 'focus' in question_lower:
            return "Overall structure and organization"
        elif 'technical' in question_lower or 'experience' in question_lower:
            return "Intermediate - familiar with common tools and practices"
        elif 'project' in question_lower or 'context' in question_lower:
            return "Development project requiring analysis and documentation"
        elif 'complexity' in question_lower or 'approach' in question_lower:
            return "Balanced approach with clear explanations"
        elif 'timeline' in question_lower or 'urgency' in question_lower:
            return "Standard timeline, quality over speed"
        else:
            # Generic fallback answers
            fallback_answers = [
                "Standard approach",
                "No specific preference", 
                "Balanced solution",
                "Default configuration",
                "Standard requirements"
            ]
            return fallback_answers[(question_num - 1) % len(fallback_answers)]
    
    def ask_question(self, question: str, question_num: int, total_questions: int) -> str:
        """Ask a single question and get user response"""
        print(f"\n**Question {question_num}/{total_questions}**: {question}")
        
        # Check if we're in test mode
        if os.getenv('RSCREW_TEST_MODE') == 'true':
            # Provide sensible default answers for testing
            default_answer = self._get_test_mode_answer(question, question_num)
            print(f"Your answer: {default_answer} [TEST MODE - AUTO RESPONSE]")
            return default_answer
        
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
        """Conduct the full interactive dialogue with adaptive questioning"""
        print("\n" + "="*60)
        print("🤖 OPERATOR INTENT INTERPRETER")
        print("="*60)
        print(f"Request: {user_request}")
        print("\nI'd like to understand your context better to provide the most relevant solution.")
        print("This will take 3-5 quick questions:")
        
        # Adaptive questioning - generate each question based on previous answers
        max_questions = 5
        for question_num in range(1, max_questions + 1):
            # Generate next question based on request and previous answers
            question = self.generate_next_question(user_request, execution_context, question_num, max_questions)
            
            if not question:  # No more relevant questions
                break
                
            answer = self.ask_question(question, question_num, max_questions)
            self.qa_history.append((question, answer))
            
            if answer == "Interrupted":
                break
            
            # Check if we have enough context to stop early
            if self.has_sufficient_context():
                print(f"\n✅ Sufficient context gathered after {question_num} questions.")
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
        project_context = "Unknown"
        if any(word in all_answers for word in ['production', 'work', 'company', 'business']):
            project_context = "Production/Professional"
        elif any(word in all_answers for word in ['learn', 'study', 'practice', 'tutorial']):
            project_context = "Learning/Educational"
        elif any(word in all_answers for word in ['personal', 'hobby', 'side']):
            project_context = "Personal/Hobby"
        
        # Complexity preference
        complexity_preference = "Unknown"
        if any(word in all_answers for word in ['simple', 'basic', 'minimal', 'quick']):
            complexity_preference = "Simple/Minimal"
        elif any(word in all_answers for word in ['robust', 'production', 'enterprise', 'scalable']):
            complexity_preference = "Robust/Production"
        
        # Generate unstated needs
        unstated_needs = []
        if 'api' in user_request.lower() or 'web' in user_request.lower():
            unstated_needs.append("Probably needs data persistence")
            if 'production' in project_context.lower():
                unstated_needs.append("Should include testing strategy")
        
        unstated_needs_text = "; ".join(unstated_needs) if unstated_needs else "None identified"
        
        # Create dialogue summary
        qa_dialogue = "\n".join([f"Q: {q}\nA: {a}" for q, a in self.qa_history])
        
        # Display operator profile
        print(f"\n📊 OPERATOR PROFILE:")
        print(f"   Technical Background: {tech_background}")
        print(f"   Project Context: {project_context}")
        print(f"   Complexity Preference: {complexity_preference}")
        if unstated_needs:
            print(f"   Unstated Needs: {unstated_needs_text}")
        
        # Enhanced request
        enhanced_request = user_request
        
        # Operator context summary
        operator_context = f"Operator Profile: {tech_background} developer working on {project_context.lower()} with {complexity_preference.lower()} requirements. {len(unstated_needs)} unstated needs identified."
        
        return {
            'original_request': user_request,
            'execution_context': execution_context,
            'technical_background': tech_background,
            'project_context': project_context,
            'complexity_preference': complexity_preference,
            'qa_dialogue': qa_dialogue,
            'unstated_needs': unstated_needs_text,
            'enhanced_request': enhanced_request,
            'operator_context': operator_context
        }


def conduct_operator_dialogue(user_request: str, execution_context: str) -> Dict[str, str]:
    """Main entry point for conducting operator dialogue"""
    dialogue = OperatorDialogue()
    return dialogue.conduct_dialogue(user_request, execution_context)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        request = " ".join(sys.argv[1:])
        context = conduct_operator_dialogue(request, "CLI test environment")
        print("\n" + "="*60)
        print("FINAL CONTEXT:")
        for key, value in context.items():
            print(f"{key}: {value}")
    else:
        print("Usage: python interactive_dialogue.py 'Your request here'")