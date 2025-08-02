#!/usr/bin/env python
"""
Test the hybrid dialogue system with simulated conversations
"""

import sys
sys.path.insert(0, 'src')

from rscrew.interactive_dialogue import OperatorDialogue

def test_cached_dialogue():
    """Test cached domain dialogue"""
    print("🧪 TESTING CACHED DOMAIN DIALOGUE")
    print("="*50)
    
    dialogue = OperatorDialogue()
    request = "Create a REST API for user management"
    
    # Boost web development confidence for testing
    dialogue.domain_patterns['web_development']['weight'] = 2.0
    
    strategy, domain = dialogue.select_questioning_strategy(request)
    print(f"Request: {request}")
    print(f"Strategy: {strategy}, Domain: {domain}")
    
    if strategy == "CACHED":
        questions = dialogue.get_cached_questions(domain, request)
        print(f"\nGenerated {len(questions)} cached questions:")
        
        # Simulate Q&A
        simulated_answers = [
            "Python with Flask",
            "API-only, no frontend needed", 
            "JWT authentication",
            "Personal project that might go to production",
            "Starting from scratch"
        ]
        
        for i, (question, answer) in enumerate(zip(questions, simulated_answers), 1):
            print(f"\nQuestion {i}: {question}")
            print(f"Simulated Answer: {answer}")
            dialogue.qa_history.append((question, answer))
        
        # Test context synthesis
        context = dialogue.synthesize_context(request, "Test environment")
        print(f"\n📊 SYNTHESIZED CONTEXT:")
        print(f"Technical Background: {context['technical_background']}")
        print(f"Project Context: {context['project_context']}")
        print(f"Operator Context: {context['operator_context']}")

def test_dynamic_dialogue():
    """Test dynamic domain dialogue"""
    print("\n\n🧪 TESTING DYNAMIC DOMAIN DIALOGUE")
    print("="*50)
    
    dialogue = OperatorDialogue()
    request = "Build a quantum computing algorithm for portfolio optimization"
    
    strategy, domain = dialogue.select_questioning_strategy(request)
    print(f"Request: {request}")
    print(f"Strategy: {strategy}, Domain: {domain}")
    
    if strategy == "DYNAMIC":
        print(f"\nGenerating dynamic questions:")
        
        # Simulate dynamic Q&A
        simulated_qa = [
            ("What's the main challenge or goal you're trying to solve with this?", 
             "Optimize investment portfolios using quantum advantage for complex optimization"),
            ("What technologies or tools are you currently using or prefer to use?", 
             "IBM Qiskit and Python, familiar with classical optimization"),
            ("Is this for learning/experimentation or production use?", 
             "Research project that could lead to production implementation"),
            ("Any specific requirements, constraints, or integrations needed?", 
             "Need to handle 50-100 assets, risk constraints, and real market data"),
            ("Are you starting from scratch or working with existing systems?", 
             "Have classical portfolio optimizer, want to enhance with quantum")
        ]
        
        for i, (question, answer) in enumerate(simulated_qa, 1):
            print(f"\nQuestion {i}: {question}")
            print(f"Simulated Answer: {answer}")
            dialogue.qa_history.append((question, answer))
        
        # Test context synthesis
        context = dialogue.synthesize_context(request, "Research environment")
        print(f"\n📊 SYNTHESIZED CONTEXT:")
        print(f"Technical Background: {context['technical_background']}")
        print(f"Project Context: {context['project_context']}")
        print(f"Operator Context: {context['operator_context']}")

def test_hybrid_decision_making():
    """Test the hybrid decision making process"""
    print("\n\n🧪 TESTING HYBRID DECISION MAKING")
    print("="*50)
    
    dialogue = OperatorDialogue()
    
    test_requests = [
        "Create a Flask API with PostgreSQL",  # Should be CACHED (web_development)
        "Build a machine learning classifier",  # Should be CACHED (machine_learning) 
        "Design a MongoDB schema",  # Should be CACHED (database)
        "Create a holographic data storage system",  # Should be DYNAMIC (novel)
        "Build a neural quantum blockchain",  # Should be DYNAMIC (novel combination)
    ]
    
    for request in test_requests:
        domains = dialogue.detect_domains(request)
        strategy, domain = dialogue.select_questioning_strategy(request)
        
        print(f"\nRequest: {request}")
        print(f"  Strategy: {strategy}")
        print(f"  Domain: {domain}")
        if domains:
            print(f"  Confidence: {domains[0].confidence:.2f}")
            print(f"  Keywords found: {domains[0].keywords_found}")

if __name__ == "__main__":
    test_cached_dialogue()
    test_dynamic_dialogue() 
    test_hybrid_decision_making()
    print("\n✅ All hybrid dialogue tests completed!")