# Finance Visualizer Backend

A Django-based backend API for analyzing and visualizing financial transaction data.

## Features

- Import transactions from Tripletex API
- Categorize transactions automatically or manually
- Identify internal transfers between accounts
- Generate financial summaries and reports
- RESTful API for frontend integration
- Comprehensive documentation using Swagger

## Project Structure

The backend follows a modular structure with clear separation of concerns:

```
backend/
├── finance_visualizer/          # Main Django project
├── transactions/                # Transactions app
│   ├── api/                     # API endpoints
│   │   ├── serializers.py       # Data serialization
│   │   └── views.py             # API views
│   ├── constants/               # Application constants
│   ├── management/              # Management commands
│   │   └── commands/            # CLI commands
│   ├── migrations/              # Database migrations
│   ├── models.py                # Data models
│   ├── services/                # Business logic
│   │   ├── category_service.py  # Category operations
│   │   └── transaction_service.py # Transaction operations
│   ├── utils/                   # Utility functions
│   │   ├── paths.py             # Path helpers
│   │   └── tripletex.py         # Tripletex API utilities
│   ├── admin.py                 # Admin interface
│   └── urls.py                  # URL routing
├── manage.py                    # Django management script
└── requirements.txt             # Dependencies
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-username/finance-visualizer.git
   cd finance-visualizer/backend
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your configuration (use `.env.example` as a template):
   ```
   cp .env.example .env
   # Edit .env with your settings
   ```

5. Apply migrations:
   ```
   python manage.py migrate
   ```

6. Initialize default categories:
   ```
   python manage.py init_categories
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/swagger/
- ReDoc: http://localhost:8000/redoc/

## Management Commands

The application includes several management commands for common tasks:

- **Import transactions from Tripletex**:
  ```
  python manage.py import_transactions
  ```

- **Update internal transfers**:
  ```
  python manage.py update_transfers
  ```

- **Initialize default categories**:
  ```
  python manage.py init_categories
  ```

- **Populate bank accounts from transaction data**:
  ```
  python manage.py populate_bank_accounts --update-transactions
  ```

## Architecture

The backend is built with a service-oriented architecture:

1. **Models**: Define the data structure
2. **Services**: Implement business logic
3. **API views**: Handle HTTP requests and responses
4. **Serializers**: Transform data between models and JSON
5. **Utils**: Provide helper functions
6. **Management commands**: Enable CLI operations

This architecture ensures:

- Clear separation of concerns
- Reusable business logic
- Maintainable codebase
- Testable components

## Dependencies

- Django 4.2.3
- Django REST Framework 3.14.0
- Django CORS Headers 4.2.0
- Other dependencies listed in `requirements.txt`

## License

[MIT License](LICENSE) 