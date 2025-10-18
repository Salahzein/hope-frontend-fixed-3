"""
AI Configuration Settings
Toggle between rule-based AI and OpenAI integration
"""

# AI Service Configuration
USE_OPENAI = False   # DISABLED: Use rule-based filtering for speed and accuracy
USE_IMPROVED_AI_SCORING = True  # Using improved AI scoring (the working one)

# AI Threshold Configuration  
AI_RELEVANCE_THRESHOLD = 5  # Very low threshold to get results for testing

def get_ai_config():
    """Get current AI configuration"""
    return {
        "use_openai": USE_OPENAI,
        "use_improved_scoring": USE_IMPROVED_AI_SCORING,
        "threshold": AI_RELEVANCE_THRESHOLD
    }

def set_ai_config(use_openai: bool = None, use_improved: bool = None, threshold: int = None):
    """Update AI configuration (for testing purposes)"""
    global USE_OPENAI, USE_IMPROVED_AI_SCORING, AI_RELEVANCE_THRESHOLD
    
    if use_openai is not None:
        USE_OPENAI = use_openai
    if use_improved is not None:
        USE_IMPROVED_AI_SCORING = use_improved
    if threshold is not None:
        AI_RELEVANCE_THRESHOLD = threshold
    
    return get_ai_config()
