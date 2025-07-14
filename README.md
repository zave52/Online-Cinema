# Online Cinema API

## Description

The Online Cinema API is a comprehensive platform for managing and streaming movies. It provides a robust backend for an
online cinema application, including user management, movie cataloging, a shopping cart, order processing, and payments.

## Features

* **User Management**: Secure user registration, authentication, and profile management.
* **Movie Catalog**: Browse, search, and filter movies. View detailed information about each movie, including genres,
  directors, ratings and other.
* **Shopping Cart**: Add and remove movies from a shopping cart.
* **Orders**: Create and manage movie purchase orders.
* **Payments**: Integrated with Stripe for secure payment processing.
* **Email Notifications**: Automated email notifications for events like registration, password reset, and order
  confirmation.
* **Asynchronous Tasks**: Utilizes Celery for handling background tasks like sending email notifications.
* **API Documentation**: Interactive API documentation available through Swagger UI and ReDoc.

## Tech Stack

* **Backend**: Python (>=3.13), FastAPI
* **Database**: PostgreSQL
* **Message Broker**: Redis
* **Asynchronous Tasks**: Celery
* **Payments**: Stripe
* **Email Testing**: MailHog
* **Object Storage**: MinIO
* **Containerization**: Docker, Docker Compose
* **Testing**: Pytest
* **Linting**: flake8, mypy

## Project Structure

```
/
├── .github/                # GitHub Actions workflows
├── configs/                # Nginx configuration
├── docker/                 # Dockerfiles for various services
├── scripts/                # Shell scripts for running the application
├── src/                    # Source code
│   ├── config/             # Application configuration
│   ├── database/           # Database models, migrations, and session management
│   ├── exceptions/         # Custom exception handlers
│   ├── notifications/      # Email notification services
│   ├── payments/           # Payment processing logic
│   ├── routers/            # API endpoints
│   ├── schemas/            # Pydantic schemas for data validation
│   ├── security/           # Authentication and authorization
│   ├── storages/           # File storage services
│   ├── tasks/              # Celery tasks
│   ├── tests/              # Tests
│   ├── validation/         # Custom validation logic
│   └── main.py             # Main application file
├── .env.sample             # Example environment variables
├── .flake8                 # Flake8 configuration
├── alembic.ini             # Alembic configuration
├── docker-compose-dev.yml  # Docker Compose for development
├── docker-compose-prod.yml # Docker Compose for production
├── docker-compose-tests.yml# Docker Compose for testing
├── Dockerfile              # Main Dockerfile for the application
├── mypy.ini                # MyPy configuration
├── poetry.lock             # Poetry lock file
├── pyproject.toml          # Project metadata and dependencies
├── pytest.ini              # Pytest configuration
└── README.md               # This file
```

## Installation and Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/Online-Cinema.git
   cd Online-Cinema
   ```

2. **Install Poetry**:
   If you don't have Poetry installed, you can install it by following the official instructions on
   the [Poetry website](https://python-poetry.org/docs/#installation).

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Create a `.env` file**:
   Create a `.env` file in the root directory by copying the `.env.sample` file and filling in the required environment
   variables.

   ```bash
   cp .env.sample .env
   ```

## Initial Setup

Before you can register users, you need to populate the `user_groups` table with the available user groups. After
running the application for the first time, the database migrations will create the necessary tables. You will then need
to manually add the following user groups to the `user_groups` table:

* `USER`
* `MODERATOR`
* `ADMIN`

You can do this by connecting to the PostgreSQL database (e.g., using `psql` or a GUI tool like pgAdmin) and running the
following SQL commands:

```sql
INSERT INTO user_groups (name)
VALUES ('USER');
INSERT INTO user_groups (name)
VALUES ('MODERATOR');
INSERT INTO user_groups (name)
VALUES ('ADMIN');
```

This step is essential for the user registration process to work correctly.

## How to Run

### Development

To run the application in a development environment, use the following command:

```bash
docker-compose -f docker-compose-dev.yml up --build
```

The API will be available at `http://localhost:8000`.

### Production

To run the application in a production environment, use the following command:

```bash
docker-compose -f docker-compose-prod.yml up --build
```

## Services and Ports

When running the application in a development environment, the following services will be available at the specified
ports:

| Service      | Port      | Description                                          |
| ------------ | --------- | ---------------------------------------------------- |
| `app`        | `8000`    | The main FastAPI application                         |
| `db`         | `5432`    | The PostgreSQL database                              |
| `pgadmin`    | `3333`    | pgAdmin, a web-based administration tool for PostgreSQL |
| `flower`     | `5555`    | A web-based tool for monitoring Celery jobs          |
| `mailhog`    | `8025`    | A web-based tool for testing email sending           |
| `minio`      | `9001`    | The MinIO web console                                |

## How to Test

Before running the tests, you need to create a `.env` file in the `docker/tests` directory by copying the
`docker/tests/.env.sample` file and filling in the required environment variables.

```bash
cp docker/tests/.env.sample docker/tests/.env
```

To run all tests, use the following command:

```bash
docker-compose -f docker-compose-tests.yml up --build
```

This will run all tests, including unit, integration, and end-to-end tests.

### Running Specific Tests

You can run specific types of tests using pytest markers. The available markers are:

* `unit`
* `integration`
* `api`
* `e2e`
* `validation`

To run only a specific group of tests (e.g., `unit` tests), modify the `command` in `docker-compose-tests.yml` to
include the `-m` flag. For example:

```bash
pytest -m unit
```

## API Documentation

Once the application is running, you can access the interactive API documentation at the following URLs:

* **Swagger UI**: `http://localhost:8000/docs`
* **ReDoc**: `http://localhost:8000/redoc`

You will need to be logged in to access the documentation.
