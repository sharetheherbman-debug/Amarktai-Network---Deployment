#!/usr/bin/env python3
"""
Route Collision Checker
Detects duplicate routes in FastAPI application to prevent startup failures

Usage:
    python scripts/check_routes.py

Exit codes:
    0 - No duplicates found
    1 - Duplicates found (prints details)
"""

import sys
import os
from collections import defaultdict
from typing import Dict, List, Tuple

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def normalize_path(path: str) -> str:
    """Normalize path by removing trailing slashes and ensuring it starts with /"""
    path = path.rstrip('/')
    if not path.startswith('/'):
        path = '/' + path
    return path

def extract_routes(app) -> Dict[Tuple[str, str], List[str]]:
    """
    Extract all routes from FastAPI app
    
    Returns:
        Dict mapping (method, path) -> [endpoint names]
    """
    routes_map = defaultdict(list)
    
    for route in app.routes:
        # Skip non-route objects (like mounts)
        if not hasattr(route, 'methods'):
            continue
            
        # Get methods (filter out HEAD and OPTIONS as they're auto-generated)
        methods = route.methods or set()
        methods = {m for m in methods if m not in ('HEAD', 'OPTIONS')}
        
        if not methods:
            continue
            
        # Get path
        path = normalize_path(route.path)
        
        # Get endpoint name
        endpoint_name = "unknown"
        if hasattr(route, 'endpoint'):
            endpoint = route.endpoint
            if hasattr(endpoint, '__module__') and hasattr(endpoint, '__name__'):
                endpoint_name = f"{endpoint.__module__}:{endpoint.__name__}"
            elif hasattr(endpoint, '__name__'):
                endpoint_name = endpoint.__name__
        
        # Record each method+path combination
        for method in methods:
            route_key = (method, path)
            routes_map[route_key].append(endpoint_name)
    
    return routes_map

def find_duplicates(routes_map: Dict[Tuple[str, str], List[str]]) -> Dict[Tuple[str, str], List[str]]:
    """Find routes that have multiple handlers"""
    return {
        route_key: endpoints 
        for route_key, endpoints in routes_map.items() 
        if len(endpoints) > 1
    }

def print_duplicates(duplicates: Dict[Tuple[str, str], List[str]]) -> None:
    """Print duplicate routes in a readable format"""
    print("\n" + "="*80)
    print("ROUTE COLLISION DETECTED")
    print("="*80)
    print(f"\nFound {len(duplicates)} duplicate route(s):\n")
    
    for (method, path), endpoints in sorted(duplicates.items()):
        print(f"❌ {method:6s} {path}")
        print(f"   Defined {len(endpoints)} times:")
        for endpoint in endpoints:
            print(f"      - {endpoint}")
        print()
    
    print("="*80)
    print("⚠️  Server cannot start with route collisions!")
    print("   Fix by keeping only one handler per route (method + path).")
    print("="*80 + "\n")

def print_success(total_routes: int) -> None:
    """Print success message"""
    print("\n" + "="*80)
    print("✅ NO ROUTE COLLISIONS DETECTED")
    print("="*80)
    print(f"\nChecked {total_routes} unique routes")
    print("All routes have exactly one handler each")
    print("Server should boot successfully\n")
    print("="*80 + "\n")

def main():
    """Main entry point"""
    print("Loading FastAPI application...")
    
    try:
        # Import server module (this builds the app)
        import server
        app = server.app
        
        print(f"✓ Loaded application with {len(app.routes)} total routes")
        
        # Extract routes
        routes_map = extract_routes(app)
        print(f"✓ Extracted {len(routes_map)} unique method+path combinations")
        
        # Find duplicates
        duplicates = find_duplicates(routes_map)
        
        if duplicates:
            print_duplicates(duplicates)
            return 1
        else:
            print_success(len(routes_map))
            return 0
            
    except Exception as e:
        print(f"\n❌ ERROR: Failed to load application: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
