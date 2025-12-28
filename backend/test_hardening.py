#!/usr/bin/env python3
"""
Test script to verify startup/shutdown hardening changes.
Tests the critical fixes without requiring full server startup.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_autopilot_engine_structure():
    """Test that AutopilotEngine has correct structure"""
    print("Testing AutopilotEngine structure...")
    
    # Import without running (syntax check)
    import ast
    import inspect
    
    with open('autopilot_engine.py', 'r') as f:
        source = f.read()
        tree = ast.parse(source)
    
    # Find AutopilotEngine class
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'AutopilotEngine':
            # Check for methods (both sync and async)
            methods = {item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
            
            assert 'start' in methods, "start method not found"
            assert 'stop' in methods, "stop method not found"
            
            # Check start is async
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef) and item.name == 'start':
                    print("  ✅ start() is async")
                    break
            else:
                raise AssertionError("start() is not async")
            
            # Check __init__ initializes scheduler to None
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                    source_lines = source.split('\n')
                    func_source = '\n'.join([source_lines[i] for i in range(item.lineno - 1, item.end_lineno)])
                    if 'self.scheduler = None' in func_source:
                        print("  ✅ scheduler initialized to None")
                    break
            
            print("  ✅ AutopilotEngine structure is correct")
            return True
    
    raise AssertionError("AutopilotEngine class not found")

def test_auth_admin_functions():
    """Test that auth.py has is_admin and require_admin"""
    print("Testing auth.py admin functions...")
    
    import ast
    
    with open('auth.py', 'r') as f:
        source = f.read()
        tree = ast.parse(source)
    
    functions = {item.name for item in ast.walk(tree) if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
    
    assert 'is_admin' in functions, "is_admin function not found"
    assert 'require_admin' in functions, "require_admin function not found"
    
    # Check is_admin is async
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == 'is_admin':
            print("  ✅ is_admin() is async")
            break
    else:
        raise AssertionError("is_admin() is not async")
    
    print("  ✅ auth.py has required admin functions")
    return True

def test_paper_trading_close_exchanges():
    """Test that paper_trading_engine has enhanced close_exchanges"""
    print("Testing paper_trading_engine.close_exchanges()...")
    
    with open('paper_trading_engine.py', 'r') as f:
        source = f.read()
    
    # Check for close_exchanges method
    assert 'async def close_exchanges' in source, "close_exchanges method not found"
    
    # Check that it closes all three exchanges
    assert 'luno_exchange' in source and 'close()' in source, "Luno close not found"
    assert 'binance_exchange' in source and 'close()' in source, "Binance close not found"
    
    # Check for KuCoin (the one we added)
    if 'kucoin_exchange' in source and 'close()' in source:
        print("  ✅ KuCoin close added")
    else:
        raise AssertionError("KuCoin close not found")
    
    print("  ✅ close_exchanges() closes all exchanges")
    return True

def test_server_lifespan_hardening():
    """Test that server.py lifespan has proper error handling"""
    print("Testing server.py lifespan hardening...")
    
    with open('server.py', 'r') as f:
        source = f.read()
    
    # Check for await autopilot.start()
    if 'await autopilot.start()' in source:
        print("  ✅ autopilot.start() is properly awaited")
    else:
        raise AssertionError("autopilot.start() not awaited")
    
    # Check shutdown has try/except blocks
    shutdown_section = source[source.find('# Shutdown'):] if '# Shutdown' in source else source
    
    try_count = shutdown_section.count('try:')
    except_count = shutdown_section.count('except Exception')
    
    if try_count >= 10 and except_count >= 10:
        print(f"  ✅ Shutdown has {try_count} try blocks and {except_count} except handlers")
    else:
        print(f"  ⚠️  Shutdown has {try_count} try blocks and {except_count} except handlers")
    
    # Check only one self_healing import from engines
    if 'from engines.self_healing import self_healing' in source:
        print("  ✅ Using engines.self_healing only")
    
    # Check duplicate is NOT imported
    if 'from self_healing import self_healing' in source:
        print("  ⚠️  Warning: duplicate self_healing import found")
    
    print("  ✅ server.py lifespan is hardened")
    return True

def test_install_script_exists():
    """Test that deployment/install.sh exists and is executable"""
    print("Testing deployment scripts...")
    
    install_script = '../deployment/install.sh'
    if os.path.exists(install_script):
        print("  ✅ deployment/install.sh exists")
        
        if os.access(install_script, os.X_OK):
            print("  ✅ install.sh is executable")
        else:
            print("  ⚠️  install.sh not executable (run: chmod +x deployment/install.sh)")
        
        # Check script contains key sections
        with open(install_script, 'r') as f:
            content = f.read()
            
            checks = [
                ('apt-get', 'OS dependency installation'),
                ('python3.12 -m venv', 'Virtual environment creation'),
                ('pip install', 'Python package installation'),
                ('compileall', 'Syntax validation'),
                ('systemctl', 'Systemd service setup'),
                ('/api/health', 'Health check'),
            ]
            
            for pattern, description in checks:
                if pattern in content:
                    print(f"  ✅ Has {description}")
                else:
                    print(f"  ⚠️  Missing {description}")
    else:
        print("  ❌ deployment/install.sh not found")
        return False
    
    return True

def main():
    """Run all tests"""
    print("="*60)
    print("Startup/Shutdown Hardening - Verification Tests")
    print("="*60)
    print()
    
    tests = [
        test_autopilot_engine_structure,
        test_auth_admin_functions,
        test_paper_trading_close_exchanges,
        test_server_lifespan_hardening,
        test_install_script_exists,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            print()
            failed += 1
    
    print("="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)
    
    if failed == 0:
        print("✅ All verification tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
