"""
Environment utility functions for consistent configuration parsing.
"""
import os


def env_bool(name: str, default: bool = False) -> bool:
    """
    Parse environment variable as boolean.
    
    Returns True for: '1', 'true', 'yes', 'y', 'on' (case-insensitive)
    Returns default when variable is not set or empty.
    
    Args:
        name: Environment variable name
        default: Default value if variable is not set
        
    Returns:
        Boolean value
        
    Examples:
        >>> os.environ['TEST_VAR'] = 'true'
        >>> env_bool('TEST_VAR')
        True
        >>> env_bool('NONEXISTENT', default=False)
        False
    """
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip().lower()
    return value in {'1', 'true', 'yes', 'y', 'on'}
