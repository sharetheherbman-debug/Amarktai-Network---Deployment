"""
Build Info Router - Provides build version and deployment information
"""

from fastapi import APIRouter
from datetime import datetime
import os
import subprocess
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["Build"])


def get_git_sha() -> str:
    """Get current git commit SHA"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Failed to get git SHA: {e}")
    
    return "unknown"


def get_git_branch() -> str:
    """Get current git branch"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Failed to get git branch: {e}")
    
    return "unknown"


# Get build info at startup
BUILD_SHA = os.environ.get("BUILD_SHA") or get_git_sha()
BUILD_TIME = os.environ.get("BUILD_TIME") or datetime.utcnow().isoformat()
BUILD_BRANCH = os.environ.get("BUILD_BRANCH") or get_git_branch()


@router.get("/build")
async def get_build_info():
    """Get build information
    
    Returns:
        Build SHA, time, branch, and expected frontend SHA
    """
    return {
        "success": True,
        "backend": {
            "sha": BUILD_SHA,
            "branch": BUILD_BRANCH,
            "build_time": BUILD_TIME,
            "python_version": os.sys.version.split()[0]
        },
        "frontend": {
            "expected_sha": BUILD_SHA,  # Frontend should match backend
            "note": "Frontend build SHA should be displayed in UI footer"
        },
        "deployment": {
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "host": os.environ.get("HOSTNAME", "unknown")
        }
    }
