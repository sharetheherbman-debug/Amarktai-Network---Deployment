"""
Dashboard Endpoints Router
Provides real-time math and analytics for dashboard frontend
All data sourced from MongoDB - single source of truth
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal
import logging
from decimal import Decimal

from auth import get_current_user
import database as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Dashboard"])

# NOTE: Removed duplicate endpoints to fix route collisions
# - GET /countdown/status (canonical: routes/ledger_endpoints.py)
# - GET /portfolio/summary (canonical: routes/ledger_endpoints.py)
# Ledger is the source of truth for portfolio data and equity calculations
