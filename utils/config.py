import os

class Config:
    # Model Configuration
    DEFAULT_MODEL = "llama2:3.2"
    AVAILABLE_MODELS = ["llama2:3.2", "mistral:latest", "codellama:13b"]
    
    # Online Models Configuration
    ONLINE_MODELS = {
        "openai": ["gpt-3.5-turbo", "gpt-4"],
        "claude": ["claude-2.1", "claude-instant"],
        "groq": ["llama2-70b", "mixtral-8x7b"]
    }
    
    # API Keys
    MATHPIX_API_KEY = os.environ.get('MATHPIX_API_KEY')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
