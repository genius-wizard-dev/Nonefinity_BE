# Nonefinity Agent Backend

<div align="center">
  <img src="../img/logo.jpg" alt="Nonefinity Logo" width="200" height="200" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
</div>

<div align="center">
  <h3>🤖 Modern Backend Application for Nonefinity Agent</h3>
  <p><em>A powerful backend system built with FastAPI, featuring comprehensive logging, monitoring, and configuration management.</em></p>
</div>

---

## 🚀 Features Implemented

### ✅ Core Framework
- **FastAPI Application**: Modern async web framework with automatic OpenAPI documentation
- **Structured Project Layout**: Clean separation of concerns with organized modules
- **Python 3.12+**: Latest Python features and type hints
- **UV Package Manager**: Fast, modern Python package and project management

### ✅ Configuration Management
- **Environment-based Settings**: Comprehensive configuration using Pydantic Settings
- **Multi-service Configuration**: Separate settings classes for different services
- **Type-safe Configuration**: Full type checking with Pydantic models
- **Environment Variable Support**: Automatic loading from `.env` files

### ✅ Advanced Logging System
- **Structured Logging**: JSON formatting for production environments
- **Colored Console Output**: Enhanced development experience with colored logs
- **Multiple Formatters**: JSON for production, colored text for development
- **File Logging**: Configurable file output with automatic directory creation
- **Context Logging**: Support for adding structured context to log messages
- **Logger Configuration**: Fine-tuned logging levels for different libraries

### ✅ Monitoring & Error Tracking
- **Sentry Integration**: Complete error tracking and performance monitoring
- **Multiple Integrations**: FastAPI, Redis, MongoDB, and logging integrations
- **Data Privacy**: Automatic filtering of sensitive information (headers, cookies)
- **Health Check Filtering**: Excludes health checks from transaction tracking
- **Configurable Sampling**: Adjustable trace and error sampling rates

### ✅ Application Lifecycle Management
- **Lifespan Events**: Proper application startup and shutdown handling
- **Graceful Initialization**: Ordered service initialization during startup
- **Resource Cleanup**: Proper cleanup during application shutdown
- **Health Monitoring**: Built-in health check endpoints

## 📁 Project Structure

```
Nonefinity_Backend/
├── app/
│   ├── api/                 # API routes and endpoints
│   ├── configs/            # Configuration management
│   │   └── settings.py     # Environment-based settings
│   ├── consts/            # Application constants
│   ├── crud/              # Database operations (Create, Read, Update, Delete)
│   ├── databases/         # Database connection and setup
│   ├── dependencies/      # FastAPI dependencies
│   ├── middlewares/       # Custom middleware
│   │   └── sentry.py      # Sentry monitoring setup
│   ├── models/           # Database models
│   ├── schemas/          # Pydantic schemas for API
│   ├── services/         # Business logic services
│   ├── utils/            # Utility functions
│   │   └── logging.py    # Advanced logging system
│   └── main.py           # Application entry point
├── pyproject.toml        # Project dependencies and metadata
├── uv.lock              # Locked dependencies
└── README.md            # This file
```

## 🛠 Technology Stack

### Core Framework
- **FastAPI**: Modern web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **Pydantic**: Data validation and settings management

### Database & Storage
- **MongoDB**: Document database with Motor async driver
- **Redis**: In-memory data structure store for caching
- **Beanie**: Async MongoDB ODM based on Pydantic

### Authentication & Security
- **Authlib**: OAuth and JWT authentication library
- **Passlib**: Password hashing with bcrypt
- **Email Validator**: Email validation utilities

### Monitoring & Logging
- **Sentry**: Error tracking and performance monitoring
- **Custom Logging**: Structured logging with JSON and colored formatters

### Vector Database
- **Qdrant**: Vector database for AI/ML applications

### Development Tools
- **HTTPX**: Modern HTTP client for async requests
- **UV**: Fast Python package and project manager

## ⚙️ Configuration

The application uses environment-based configuration with the following settings groups:

### Application Settings (`APP_*`)
- `APP_NAME`: Application name (default: "Nonefinity Agent")
- `APP_ENV`: Environment (dev/prod, default: "dev")
- `APP_HOST`: Host address (default: "0.0.0.0")
- `APP_PORT`: Port number (default: 8000)
- `APP_DEBUG`: Debug mode (default: True)

### MongoDB Settings (`MONGO_*`)
- `MONGO_HOST`: MongoDB host
- `MONGO_PORT`: MongoDB port (default: 27017)
- `MONGO_DB`: Database name
- `MONGO_USER`: Username (optional)
- `MONGO_PWD`: Password (optional)

### Redis Settings (`REDIS_*`)
- `REDIS_URL`: Redis connection URL
- `REDIS_PWD`: Redis password (optional)

### Sentry Monitoring (`SENTRY_*`)
- `SENTRY_DSN`: Sentry Data Source Name
- `SENTRY_TRACES_SAMPLE_RATE`: Trace sampling rate (default: 0.2)
- `SENTRY_PROFILES_SAMPLE_RATE`: Profile sampling rate (default: 0.0)
- `SENTRY_SEND_DEFAULT_PII`: Send personal information (default: False)

### Authentication (`AUTH_*`)
- `AUTH_JWT_ISS`: JWT issuer (default: "http://127.0.0.1:8000")
- `AUTH_JWT_AUD`: JWT audience
- `AUTH_JWT_ALG`: JWT algorithm (default: "HS256")
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiry (default: 15)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiry (default: 14)

### Vector Database (`QDRANT_*`)
- `QDRANT_URL`: Qdrant connection URL

### Other Settings
- `RELEASE`: Application release version (optional)

## 🚦 Getting Started

### Prerequisites
- Python 3.12 or higher
- UV package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Nonefinity_Backend
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Create environment file**
   ```bash
   cp .env.sample .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The application will be available at `http://localhost:8000`

### API Documentation
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📋 Available Endpoints

### Health & Status
- `GET /`: Welcome message with application information
- `GET /health`: Health check endpoint

## 🔧 Development Features

### Logging System
The application includes a sophisticated logging system with:

- **Development Mode**: Colored console output for easy debugging
- **Production Mode**: JSON structured logs for log aggregation
- **File Logging**: Optional file output for persistent logging
- **Context Support**: Add structured data to log messages
- **Library Integration**: Configured logging for FastAPI, MongoDB, Redis, etc.

### Error Monitoring
Sentry integration provides:

- **Error Tracking**: Automatic error capture and reporting
- **Performance Monitoring**: Request tracing and performance insights
- **Data Privacy**: Automatic filtering of sensitive information
- **Custom Sampling**: Configurable error and trace sampling rates

### Configuration Management
Environment-based configuration with:

- **Type Safety**: Full Pydantic validation for all settings
- **Environment Separation**: Different configs for dev/prod environments
- **Service Isolation**: Separate settings for each external service
- **Auto-loading**: Automatic environment variable loading

## 🏗 Architecture Decisions

### Why FastAPI?
- Modern async/await support
- Automatic API documentation
- Built-in data validation
- High performance
- Great developer experience

### Why Pydantic Settings?
- Type-safe configuration
- Automatic environment variable parsing
- Built-in validation
- Easy testing with different configs

### Why Structured Logging?
- Better log aggregation and searching
- Consistent log format across services
- Enhanced debugging capabilities
- Production-ready monitoring

### Why Sentry?
- Comprehensive error tracking
- Performance monitoring
- Real-time alerting
- Integration with popular services

## 🔄 Future Implementation Areas

The project structure is prepared for:

- **API Routes** (`app/api/`): REST API endpoints
- **Database Models** (`app/models/`): Data models and schemas
- **CRUD Operations** (`app/crud/`): Database interaction layer
- **Business Services** (`app/services/`): Business logic implementation
- **Dependencies** (`app/dependencies/`): FastAPI dependency injection
- **Database Setup** (`app/databases/`): Database connection and initialization

## 🤝 Contributing

This project follows modern Python development practices:
- Type hints throughout the codebase
- Structured logging for debugging
- Environment-based configuration
- Comprehensive error handling
- Clean architecture separation

## 📝 Notes

- All text and comments are in English as per project requirements
- The application is designed for both development and production environments
- Comprehensive monitoring and logging are built-in from the start
- The project structure supports scalable development with clear separation of concerns