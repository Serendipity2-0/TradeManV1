# PostgreSQL Setup and Migration Guide

This guide will walk you through setting up PostgreSQL for your project and managing database migrations using Alembic.

## Table of Contents

- [PostgreSQL Setup and Migration Guide](#postgresql-setup-and-migration-guide)
  - [Table of Contents](#table-of-contents)
  - [PostgreSQL Installation](#postgresql-installation)
  - [Database Setup](#database-setup)
  - [Project Configuration](#project-configuration)
  - [Alembic Setup](#alembic-setup)
  - [Creating and Running Migrations](#creating-and-running-migrations)
  - [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)

## PostgreSQL Installation

1. Download and install PostgreSQL from the [official website](https://www.postgresql.org/download/).
2. During installation, note down the superuser (postgres) password you set.

## Database Setup

1. Open pgAdmin or your preferred PostgreSQL client.
2. Create a new database for your project:
   ```sql
   CREATE DATABASE your_database_name;
   ```
3. Create a new user and grant privileges:
   ```sql
   CREATE USER your_username WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE your_database_name TO your_username;
   ```

## Project Configuration

1. Install the required Python packages:
   ```bash
   pip install sqlalchemy alembic psycopg2-binary
   ```

2. Update your project's database configuration (e.g., in a `config.py` file):
   ```python
   DATABASE_URL = "postgresql://your_username:your_password@localhost/your_database_name"
   ```

## Alembic Setup

1. Initialize Alembic in your project:
   ```bash
   alembic init alembic
   ```

2. Edit `alembic.ini` in your project root:
   ```ini
   sqlalchemy.url = postgresql://your_username:your_password@localhost/your_database_name
   ```

3. Update `alembic/env.py`:
   ```python
   from db.models import Base
   from db import models
   
   # Find target_metadata = None and replace with:
   target_metadata = Base.metadata
   ```

## Creating and Running Migrations

1. After making changes to your models, create a new migration:
   ```bash
   alembic revision --autogenerate -m "Description of changes"
   ```

2. Review the generated migration script in `alembic/versions/`.

3. Apply the migration:
   ```bash
   alembic upgrade head
   ```

4. To revert a migration:
   ```bash
   alembic downgrade -1
   ```

## Common Issues and Troubleshooting

- **Connection refused**: Ensure PostgreSQL is running and the connection details are correct.
- **Permission denied**: Check that your user has the necessary privileges on the database.
- **Module not found errors**: Ensure all required packages are installed and your Python environment is activated.
- **Alembic not detecting changes**: Make sure your models are imported in `env.py` and `Base.metadata` is correctly set.

For more detailed information, refer to the [Alembic documentation](https://alembic.sqlalchemy.org/en/latest/) and [SQLAlchemy documentation](https://docs.sqlalchemy.org/en/14/).
