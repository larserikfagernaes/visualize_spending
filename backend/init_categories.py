import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_visualizer.settings')
django.setup()

from transactions.models import Category

# Define categories
categories = [
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

def init_categories():
    for category_data in categories:
        Category.objects.get_or_create(
            name=category_data['name'],
            defaults={'description': category_data['description']}
        )
    print(f"Initialized {len(categories)} categories")

if __name__ == '__main__':
    init_categories() 