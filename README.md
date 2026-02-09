# Backend - Mundial de Porras F1

## Overview

This is a FastAPI-based backend application for a Formula 1 predictions and betting game. It provides REST APIs for user management, race predictions, bingo games, season management, and scoring mechanics.

## Technology Stack

- **FastAPI**: Web framework for building APIs
- **SQLAlchemy**: ORM for database interactions
- **SQLite**: Database (dev environment)
- **PostgreSQL**: Supported for production
- **JWT Authentication**: Token-based user authentication
- **Bcrypt**: Password hashing

## Project Structure

### Core Directories

- **app/api/**: Route handlers for all endpoints
- **app/db/**: Database configuration and models
- **app/core/**: Security and dependency injection utilities
- **app/schemas/**: Pydantic models for request/response validation
- **app/services/**: Business logic and calculations
- **app/scripts/**: Utility scripts (e.g., admin creation)
- **app/static/**: Static files (avatars, etc.)

## Key Components

### API Routes (app/api/)

- **auth.py**: User registration, login, and profile management
- **predictions.py**: Race predictions submission and management
- **race_results.py**: Race results and position tracking
- **grand_prix.py**: Grand Prix event management
- **bingo.py**: Bingo game mechanics
- **teams.py**: Team management and team members
- **achievements.py**: User achievements and badges
- **stats.py**: User statistics and rankings
- **seasons.py**: Season configuration
- **admin.py**: Administrative operations
- **avatars.py**: Avatar upload and management

### Database Models (app/db/models/)

The system uses SQLAlchemy ORM with the following main entities:

- **User**: Player accounts with role-based access
- **Team**: Team groups with members
- **TeamMember**: Association between users and teams
- **Season**: F1 season configuration
- **GrandPrix**: Individual races within a season
- **Prediction**: User predictions for races
- **PredictionPosition**: Predicted finishing positions
- **RaceResult**: Actual race outcomes
- **RacePosition**: Actual finishing positions
- **BingoTile**: Bingo card tiles
- **BingoSelection**: User bingo selections
- **Achievement**: User achievements and awards
- **Driver**: F1 drivers
- **Constructor**: F1 teams/constructors
- **Avatar**: User profile avatars

### Services (app/services/)

- **achievements_service.py**: Logic for awarding achievements to users
- **scoring.py**: Calculation of points and rankings based on predictions vs results

### Authentication & Authorization

Uses OAuth2 with JWT tokens:

- **deps.py**: Dependency injection for authentication
  - `get_current_user()`: Validates JWT token and returns authenticated user
  - `require_admin()`: Ensures user has admin role
  
- **security.py**: Password hashing and token generation
  - Bcrypt for password hashing
  - HS256 JWT algorithm
  - Configurable token expiration

## Getting Started

### Prerequisites

Python 3.13+ with Poetry package manager

### Installation

1. Install dependencies:
```bash
cd app
poetry install
```

2. Set up environment variables in `.env`:
```
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./dev.db  # or PostgreSQL connection string
```

3. Run the application:
```bash
poetry run uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, access interactive documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database

### Setup

Tables are automatically created on application startup via SQLAlchemy:
```python
Base.metadata.create_all(bind=engine)
```

### Migrations

Use Alembic for database migrations (included in dependencies):
```bash
alembic upgrade head
```

## Key Features

### Predictions System
Users submit predictions for race outcomes before races start. Points are awarded based on accuracy.

### Bingo Game
Users select tiles from a bingo card with various F1 outcomes. Awards are given when rows/columns/diagonals are completed.

### Scoring & Rankings
Automated calculation of player points based on:
- Prediction accuracy
- Bingo completions
- Achievement unlocks
- Season-long standings

### Team System
Users can create or join teams for group-based competition.

### Avatar System
Users can upload custom avatars stored in `app/static/avatars/`.

## Static Files

The application serves static files from the `app/static` directory:
```
http://localhost:8000/static/avatars/[filename]
```

## Admin Operations

Admin users can:
- Create/update seasons and races
- Input race results
- Manage users
- Award achievements

Use `app/scripts/create_admin.py` to create admin accounts.

## Development

### Seed Data

Several seed scripts are available in the root directory:
- `seed_data.py`: Initial data setup
- `seed_data_bingo.py`: Bingo tiles
- `seed_data_achievements.py`: Achievement definitions

Run with:
```bash
poetry run python ../seed_data.py
```

### Code Organization

- Request/response schemas are in `schemas/`
- Database access happens in route handlers or services
- Business logic is isolated in `services/`
- Authentication checks are in `deps.py`

## Error Handling

The API returns standard HTTP status codes:
- 200: Success
- 400: Bad request/validation error
- 401: Unauthorized/invalid token
- 403: Forbidden/insufficient permissions
- 404: Resource not found
- 500: Server error