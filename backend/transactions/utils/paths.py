"""
Utility functions for working with file paths.
"""
import os
from pathlib import Path
from django.conf import settings

def get_app_directory():
    """
    Returns the absolute path to the transactions app directory.
    
    Returns:
        str: The path to the transactions app directory
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_cache_directory():
    """
    Returns the path to the cache directory, creating it if it doesn't exist.
    
    Returns:
        str: The path to the cache directory
    """
    cache_dir = os.path.join(get_app_directory(), 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def get_cache_file_path(filename):
    """
    Returns the path to a file in the cache directory.
    
    Args:
        filename (str): The name of the file
        
    Returns:
        str: The full path to the file in the cache directory
    """
    return os.path.join(get_cache_directory(), filename)

def get_project_root():
    """
    Returns the path to the project root directory.
    
    Returns:
        str: The path to the project root directory
    """
    return str(settings.BASE_DIR) 