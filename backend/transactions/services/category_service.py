"""
Service layer for category-related operations.
Handles business logic for categories.
"""
import logging
from django.db.models import Count
from ..models import Category, Transaction

logger = logging.getLogger('transactions')

def get_all_categories():
    """
    Get all categories ordered by name.
    
    Returns:
        QuerySet: All categories ordered by name
    """
    return Category.objects.all().order_by('name')

def get_category_by_id(category_id):
    """
    Get a category by its ID.
    
    Args:
        category_id (int): The ID of the category to get
        
    Returns:
        Category: The category object or None if not found
    """
    try:
        return Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        logger.error(f"Category with ID {category_id} not found")
        return None

def get_category_by_name(name):
    """
    Get a category by its name.
    
    Args:
        name (str): The name of the category to get
        
    Returns:
        Category: The category object or None if not found
    """
    try:
        return Category.objects.get(name=name)
    except Category.DoesNotExist:
        logger.debug(f"Category with name '{name}' not found")
        return None

def create_category(name, description=None):
    """
    Create a new category.
    
    Args:
        name (str): The name of the new category
        description (str, optional): The description of the new category
        
    Returns:
        tuple: (Category, bool) - The created or existing category, and a boolean indicating if it was created
    """
    if not name:
        logger.error("Cannot create category with empty name")
        return None, False
    
    try:
        category, created = Category.objects.get_or_create(
            name=name,
            defaults={'description': description or ''}
        )
        
        if created:
            logger.info(f"Created category '{name}'")
        else:
            logger.debug(f"Category '{name}' already exists")
        
        return category, created
    except Exception as e:
        logger.error(f"Error creating category '{name}': {str(e)}")
        return None, False

def update_category(category_id, name=None, description=None):
    """
    Update an existing category.
    
    Args:
        category_id (int): The ID of the category to update
        name (str, optional): The new name for the category
        description (str, optional): The new description for the category
        
    Returns:
        bool: True if successful, False otherwise
    """
    category = get_category_by_id(category_id)
    if not category:
        return False
    
    try:
        if name:
            category.name = name
        
        if description is not None:
            category.description = description
        
        category.save()
        logger.info(f"Updated category {category_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating category {category_id}: {str(e)}")
        return False

def delete_category(category_id):
    """
    Delete a category.
    
    Args:
        category_id (int): The ID of the category to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    category = get_category_by_id(category_id)
    if not category:
        return False
    
    try:
        # Remove category from transactions
        Transaction.objects.filter(category=category).update(category=None)
        
        # Delete category
        category.delete()
        logger.info(f"Deleted category {category_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting category {category_id}: {str(e)}")
        return False

def get_category_usage():
    """
    Get usage statistics for categories.
    
    Returns:
        dict: Dictionary with category names as keys and usage counts as values
    """
    category_counts = Transaction.objects.values('category__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    usage = {}
    for item in category_counts:
        category_name = item['category__name'] or 'Uncategorized'
        usage[category_name] = item['count']
    
    return usage

def initialize_default_categories():
    """
    Initialize default categories if they don't exist.
    
    Returns:
        int: Number of categories created
    """
    default_categories = [
        {
            'name': 'Food & Dining',
            'description': 'Restaurants, grocery stores, and food delivery'
        },
        {
            'name': 'Transportation',
            'description': 'Gas, public transport, and ride-sharing'
        },
        {
            'name': 'Shopping',
            'description': 'Retail purchases and online shopping'
        },
        {
            'name': 'Entertainment',
            'description': 'Movies, concerts, and other entertainment'
        },
        {
            'name': 'Housing',
            'description': 'Rent, mortgage, and home maintenance'
        },
        {
            'name': 'Utilities',
            'description': 'Electricity, water, internet, and phone bills'
        },
        {
            'name': 'Health & Fitness',
            'description': 'Medical expenses, gym memberships, and wellness'
        },
        {
            'name': 'Income',
            'description': 'Salary, interest, and other income'
        },
        {
            'name': 'Travel',
            'description': 'Flights, hotels, and vacation expenses'
        },
        {
            'name': 'Education',
            'description': 'Tuition, books, and courses'
        }
    ]
    
    created_count = 0
    
    for category_data in default_categories:
        _, created = create_category(
            name=category_data['name'],
            description=category_data['description']
        )
        
        if created:
            created_count += 1
    
    logger.info(f"Initialized {created_count} default categories")
    return created_count 