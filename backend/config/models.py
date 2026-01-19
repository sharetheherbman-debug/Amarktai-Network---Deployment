"""
AI Model Configuration - Single Source of Truth
Defines OpenAI model preferences and fallback chain
All AI features MUST reference this module for model selection
"""

from typing import List, Optional, Dict

# OpenAI model fallback chain (in order of preference)
# Try models in sequence until one works
OPENAI_MODEL_FALLBACK_CHAIN: List[str] = [
    'gpt-4o',           # Latest GPT-4 optimized
    'gpt-4-turbo',      # GPT-4 Turbo
    'gpt-4',            # Standard GPT-4
    'gpt-3.5-turbo',    # GPT-3.5 Turbo (most compatible)
]

# Default model to try first
DEFAULT_OPENAI_MODEL = OPENAI_MODEL_FALLBACK_CHAIN[0]

# Model capabilities and metadata
MODEL_METADATA: Dict[str, Dict] = {
    'gpt-4o': {
        'name': 'GPT-4o',
        'max_tokens': 128000,
        'supports_function_calling': True,
        'description': 'Latest GPT-4 optimized model'
    },
    'gpt-4-turbo': {
        'name': 'GPT-4 Turbo',
        'max_tokens': 128000,
        'supports_function_calling': True,
        'description': 'GPT-4 Turbo with extended context'
    },
    'gpt-4': {
        'name': 'GPT-4',
        'max_tokens': 8192,
        'supports_function_calling': True,
        'description': 'Standard GPT-4 model'
    },
    'gpt-3.5-turbo': {
        'name': 'GPT-3.5 Turbo',
        'max_tokens': 16385,
        'supports_function_calling': True,
        'description': 'Fast and efficient GPT-3.5'
    }
}


def get_model_fallback_chain() -> List[str]:
    """Get the full model fallback chain
    
    Returns:
        List of model names in fallback order
    """
    return OPENAI_MODEL_FALLBACK_CHAIN.copy()


def get_default_model() -> str:
    """Get the default model to try first
    
    Returns:
        Default model name
    """
    return DEFAULT_OPENAI_MODEL


def get_model_metadata(model_name: str) -> Optional[Dict]:
    """Get metadata for a specific model
    
    Args:
        model_name: Model identifier
        
    Returns:
        Model metadata dict or None if not found
    """
    return MODEL_METADATA.get(model_name)


def get_next_fallback_model(current_model: str) -> Optional[str]:
    """Get the next model in the fallback chain
    
    Args:
        current_model: Current model that failed
        
    Returns:
        Next model to try, or None if no more fallbacks
    """
    try:
        current_index = OPENAI_MODEL_FALLBACK_CHAIN.index(current_model)
        if current_index < len(OPENAI_MODEL_FALLBACK_CHAIN) - 1:
            return OPENAI_MODEL_FALLBACK_CHAIN[current_index + 1]
    except ValueError:
        # Current model not in chain, return first model
        return DEFAULT_OPENAI_MODEL
    
    return None


def is_valid_model(model_name: str) -> bool:
    """Check if model is in the supported list
    
    Args:
        model_name: Model identifier to check
        
    Returns:
        True if model is supported, False otherwise
    """
    return model_name in MODEL_METADATA
