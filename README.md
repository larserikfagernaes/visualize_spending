# Finance Visualizer

A full-stack application for visualizing and categorizing bank transactions. Built with React and Django.

## Features

- Import transactions from JSON files
- Categorize transactions
- View transaction summary statistics
- Visualize spending patterns with charts
- Filter and search transactions

## Project Structure

- `backend/`: Django REST API
- `frontend/`: React application

## Setup and Installation

### Backend (Django)

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Activate the virtual environment:
   ```
   source venv/bin/activate
   ```

3. Run migrations:
   ```
   python3 manage.py makemigrations
   python3 manage.py migrate
   ```

4. Create a superuser (optional):
   ```
   python3 manage.py createsuperuser
   ```

5. Start the development server:
   ```
   python3 manage.py runserver
   ```

The API will be available at http://localhost:8000/api/

### Frontend (React)

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Start the development server:
   ```
   npm start
   ```

The application will be available at http://localhost:3000/

## Usage

1. Start both the backend and frontend servers
2. Click the "Import" button to import transactions from the JSON files
3. Use the "Transactions" tab to view and categorize transactions
4. Use the "Categories" tab to manage categories
5. View summary statistics and charts in the "Summary" tab

## API Endpoints

- `GET /api/transactions/`: List all transactions
- `POST /api/import/`: Import transactions from JSON files
- `POST /api/categorize/{transaction_id}/`: Categorize a transaction
- `GET /api/transactions/summary/`: Get transaction summary statistics
- `GET /api/categories/`: List all categories
- `POST /api/categories/`: Create a new category 