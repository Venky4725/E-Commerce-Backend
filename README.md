# E-Commerce Backend

Backend API for an e-commerce platform built with FastAPI.

## Features

- User authentication and authorization
- Product management
- Shopping cart functionality
- Order processing
- Real-time updates with WebSockets
- Background task processing with Celery
- Caching with Redis
- Database migrations with Alembic

## Project Structure

```
app/
├── main.py              # Main application entry point
├── core/                # Core configuration and database setup
│   ├── config.py        # Application configuration
│   ├── database.py      # Database connection
│   └── security.py      # Security utilities
├── models/              # Database models
│   ├── user.py
│   ├── product.py
│   ├── cart.py
│   └── order.py
├── schemas/             # Pydantic schemas
│   ├── user_schema.py
│   ├── product_schema.py
│   ├── cart_schema.py
│   └── order_schema.py
├── crud/                # Database CRUD operations
│   ├── user_crud.py
│   ├── product_crud.py
│   ├── cart_crud.py
│   └── order_crud.py
├── api/                 # API endpoints
│   ├── deps.py          # Dependencies
│   └── routes/          # Route handlers
│       ├── auth.py
│       ├── products.py
│       ├── cart.py
│       ├── orders.py
│       └── websocket.py
├── services/            # Business logic services
│   ├── cache_service.py
│   ├── order_service.py
│   └── websocket_manager.py
├── tasks/               # Background tasks
│   ├── celery_worker.py
│   └── email_tasks.py
└── utils/               # Utility functions
    └── pagination.py
```

## Setup

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables in `.env` file
6. Run database migrations: `alembic upgrade head`
7. Start the server: `uvicorn app.main:app --reload`

## Running Tests

```bash
pytest tests/
```

## License

MIT