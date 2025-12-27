"""
AI Command Router - Entry Point

Production-grade router with fuzzy matching, synonyms, and tool registry.
This module provides backward compatibility while using the enhanced router.

For documentation, see: /COMMANDS.md
"""

# Import enhanced router as default
from services.ai_command_router_enhanced import (
    get_enhanced_ai_command_router,
    EnhancedAICommandRouter,
    CommandOutputSchema,
    ConfirmationLevel,
    ToolRegistry
)

# Import legacy router for compatibility
from services.ai_command_router_legacy import AICommandRouter as LegacyAICommandRouter

import logging

logger = logging.getLogger(__name__)


def get_ai_command_router(db):
    """
    Factory function to get command router
    
    Returns the enhanced router with production features:
    - Fuzzy bot name matching (rapidfuzz)
    - Synonym support for natural language
    - Multi-command parsing ("pause alpha and beta")
    - Structured command output schema
    - Risk-based confirmation system
    - Tool registry for AI feature access
    - Health/bodyguard integration
    - Full dashboard parity
    
    See /COMMANDS.md for complete documentation.
    """
    return get_enhanced_ai_command_router(db)


# Alias for backward compatibility
AICommandRouter = EnhancedAICommandRouter


__all__ = [
    'get_ai_command_router',
    'AICommandRouter',
    'EnhancedAICommandRouter',
    'LegacyAICommandRouter',
    'CommandOutputSchema',
    'ConfirmationLevel',
    'ToolRegistry'
]
