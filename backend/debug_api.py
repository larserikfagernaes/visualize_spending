#!/usr/bin/env python3
"""
Debug script for inspecting the Django API configuration
"""
import os
import sys
import django
from django.conf import settings

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def print_dict_section(title, data):
    """Print a dictionary in a formatted section"""
    print_section(title)
    for key, value in data.items():
        print(f"{key}: {value}")

def main():
    """Main function to output debug information"""
    # Print basic settings
    print_section("Basic Settings")
    print(f"DEBUG: {settings.DEBUG}")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    # Print CORS settings
    print_section("CORS Settings")
    print(f"CORS_ALLOWED_ORIGINS: {getattr(settings, 'CORS_ALLOWED_ORIGINS', 'Not set')}")
    print(f"CORS_ALLOW_ALL_ORIGINS: {getattr(settings, 'CORS_ALLOW_ALL_ORIGINS', 'Not set')}")
    print(f"CORS_ALLOW_CREDENTIALS: {getattr(settings, 'CORS_ALLOW_CREDENTIALS', 'Not set')}")
    print(f"CORS_ALLOW_METHODS: {getattr(settings, 'CORS_ALLOW_METHODS', 'Not set')}")
    print(f"CORS_ALLOW_HEADERS: {getattr(settings, 'CORS_ALLOW_HEADERS', 'Not set')}")
    
    # Print installed apps
    print_section("Installed Apps")
    for app in settings.INSTALLED_APPS:
        print(f"- {app}")
    
    # Print middleware
    print_section("Middleware")
    for middleware in settings.MIDDLEWARE:
        print(f"- {middleware}")
    
    # Get Auth related settings
    print_section("Authentication Settings")
    print(f"REST_FRAMEWORK: {settings.REST_FRAMEWORK}")
    
    # Print URLs
    print_section("URL Patterns")
    try:
        from django.urls import get_resolver
        resolver = get_resolver()
        
        def print_patterns(patterns, prefix=''):
            for pattern in patterns:
                if hasattr(pattern, 'pattern'):
                    if hasattr(pattern, 'callback') and pattern.callback:
                        callback_name = pattern.callback.__name__
                        module_name = pattern.callback.__module__
                        print(f"{prefix}{pattern.pattern} -> {module_name}.{callback_name}")
                    
                    if hasattr(pattern, 'url_patterns'):
                        print(f"{prefix}{pattern.pattern} [")
                        print_patterns(pattern.url_patterns, prefix + '  ')
                        print(f"{prefix}]")
        
        print_patterns(resolver.url_patterns)
    except Exception as e:
        print(f"Error fetching URL patterns: {e}")
    
    # Check for specific view permissions
    print_section("View Permissions")
    try:
        from transactions.api.views import (
            TransactionViewSet,
            CategoryViewSet,
            BankStatementViewSet,
            BankAccountViewSet
        )
        
        viewsets = {
            'TransactionViewSet': TransactionViewSet,
            'CategoryViewSet': CategoryViewSet,
            'BankStatementViewSet': BankStatementViewSet,
            'BankAccountViewSet': BankAccountViewSet
        }
        
        for name, viewset in viewsets.items():
            print(f"{name} permissions: {viewset.permission_classes}")
    except Exception as e:
        print(f"Error fetching view permissions: {e}")
    
    # Create API URL test section
    print_section("API URL Tests")
    print("To test API endpoints with curl:")
    print("\nCheck CORS preflight:")
    print("curl -i -X OPTIONS \\")
    print("  -H \"Origin: http://localhost:3001\" \\")
    print("  -H \"Access-Control-Request-Method: GET\" \\")
    print("  -H \"Access-Control-Request-Headers: Authorization, Content-Type\" \\")
    print("  http://localhost:8000/api/v1/bank-accounts/")
    
    print("\nTest GET request:")
    print("curl -i -X GET \\")
    print("  -H \"Origin: http://localhost:3001\" \\")
    print("  -H \"Authorization: Basic ZGV2OmRldg==\" \\")
    print("  http://localhost:8000/api/v1/bank-accounts/")

if __name__ == "__main__":
    main() 