# Nonefinity Agent Backend

<div align="center">
  <img src="../img/logo.jpg" alt="Nonefinity Logo" width="200" height="200" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
</div>

<div align="center">
  <h3>🤖 Modern Backend Application for Nonefinity Agent</h3>
  <p><em>A powerful backend system built with FastAPI, featuring comprehensive logging, monitoring, AI credential management, and advanced security.</em></p>
</div>

---

## 🚀 Features Implemented

### Core Framework

- **FastAPI Application**: Modern async web framework with automatic OpenAPI documentation
- **Structured Project Layout**: Clean separation of concerns with organized modules
- **Python 3.12+**: Latest Python features and type hints
- **UV Package Manager**: Fast, modern Python package and project management

### AI Credential Management System

- **🔐 Secure Credential Storage**: Encrypted API key storage using Fernet encryption
- **🏢 Multiple Provider Support**: OpenAI, OpenRouter, and extensible provider system
- **🔑 CRUD Operations**: Complete credential management (Create, Read, Update, Delete)
- **🛡️ Advanced Security**: PBKDF2 key derivation with configurable iterations
- **Credential Testing**: Built-in API key validation and health checks
- **📝 Provider Configuration**: YAML-based provider definitions with auto-loading

### Database & Storage

- **MongoDB Integration**: Document database with Beanie ODM for async operations
- **DuckDB Support**: In-memory analytics database for data processing
- **Redis Integration**: Caching and session management
- **File Management**: Upload, processing, and storage with MinIO integration
- **Dataset Management**: Structured data handling and schema validation

### Configuration Management

- **Environment-based Settings**: Comprehensive configuration using Pydantic Settings
- **Multi-service Configuration**: Separate settings classes for different services
- **Type-safe Configuration**: Full type checking with Pydantic models
- **Environment Variable Support**: Automatic loading from `.env` files
- **Security Validation**: Automatic validation of encryption settings

### Advanced Logging System

- **Structured Logging**: JSON formatting for production environments
- **Colored Console Output**: Enhanced development experience with colored logs
- **Multiple Formatters**: JSON for production, colored text for development
- **File Logging**: Configurable file output with automatic directory creation
- **Context Logging**: Support for adding structured context to log messages
- **Logger Configuration**: Fine-tuned logging levels for different libraries

### Monitoring & Error Tracking

- **Sentry Integration**: Complete error tracking and performance monitoring
- **Multiple Integrations**: FastAPI, Redis, MongoDB, and logging integrations
- **Data Privacy**: Automatic filtering of sensitive information (headers, cookies)
- **Health Check Filtering**: Excludes health checks from transaction tracking
- **Configurable Sampling**: Adjustable trace and error sampling rates

### Authentication & Security

- **Clerk Authentication**: Secure user authentication with JWT tokens
- **User Management**: Complete user lifecycle management
- **Permission System**: Role-based access control
- **API Key Encryption**: Military-grade encryption for sensitive credentials
- **Security Headers**: Automatic security header management

### Application Lifecycle Management

- **Lifespan Events**: Proper application startup and shutdown handling
- **Graceful Initialization**: Ordered service initialization during startup
- **Resource Cleanup**: Proper cleanup during application shutdown
- **Health Monitoring**: Built-in health check endpoints

## 📁 Project Structure

```
Nonefinity_Backend/
├── app/
│   ├── api/                    # API routes and endpoints
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── credential.py      # Credential management API
│   │   ├── provider.py        # AI provider management API
│   │   ├── dataset.py         # Dataset management API
│   │   ├── file.py           # File management API
│   │   ├── duckdb.py         # DuckDB operations API
│   │   └── webhooks.py       # Webhook handlers
│   ├── configs/               # Configuration management
│   │   ├── settings.py       # Environment-based settings
│   │   ├── providers.yaml    # AI provider definitions
│   │   └── setup.py          # Application setup and lifecycle
│   ├── consts/               # Application constants
│   │   └── user_event_type.py
│   ├── core/                 # Core application logic
│   │   └── exceptions.py     # Custom exception handlers
│   ├── crud/                 # Database operations (CRUD)
│   │   ├── base.py          # Base CRUD operations
│   │   ├── credential.py    # Credential CRUD operations
│   │   ├── dataset.py       # Dataset CRUD operations
│   │   ├── file.py          # File CRUD operations
│   │   └── user.py          # User CRUD operations
│   ├── databases/            # Database connections and setup
│   │   ├── mongodb.py       # MongoDB connection manager
│   │   ├── duckdb.py        # DuckDB operations
│   │   └── duckdb_manager.py # DuckDB instance management
│   ├── dependencies/         # FastAPI dependencies
│   ├── middlewares/          # Custom middleware
│   │   └── sentry.py        # Sentry monitoring setup
│   ├── models/              # Database models
│   │   ├── credential.py    # Provider and Credential models
│   │   ├── dataset.py       # Dataset models
│   │   ├── file.py          # File models
│   │   ├── user.py          # User models
│   │   ├── time_mixin.py    # Timestamp mixin
│   │   └── soft_delete_mixin.py # Soft delete functionality
│   ├── schemas/             # Pydantic schemas for API
│   │   ├── credential.py    # Credential request/response schemas
│   │   ├── dataset.py       # Dataset schemas
│   │   ├── file.py          # File schemas
│   │   ├── response.py      # Common response schemas
│   │   └── user.py          # User schemas
│   ├── services/            # Business logic services
│   │   ├── credential_service.py  # Credential management service
│   │   ├── provider_service.py    # Provider management service
│   │   ├── dataset_service.py     # Dataset processing service
│   │   ├── file_service.py        # File handling service
│   │   ├── minio_admin_service.py # MinIO administration
│   │   ├── minio_client_service.py # MinIO client operations
│   │   ├── mongodb_service.py     # MongoDB service layer
│   │   └── user.py               # User management service
│   ├── utils/               # Utility functions
│   │   ├── api_response.py  # Standardized API responses
│   │   ├── base.py          # Base utilities
│   │   ├── file_classifier.py # File type classification
│   │   ├── jwt_verification.py # JWT token verification
│   │   ├── logging.py       # Advanced logging system
│   │   └── verify_token.py  # Token verification utilities
│   └── main.py             # Application entry point
├── docs/                   # Documentation
│   ├── README_EN.md        # English documentation
│   └── README_VI.md        # Vietnamese documentation
├── img/                    # Images and assets
│   ├── logo.jpg           # Nonefinity logo
│   └── logo.ico           # Favicon
├── logs/                   # Application logs
│   └── app.log            # Main application log
├── pyproject.toml         # Project dependencies and metadata
├── uv.lock               # Locked dependencies
└── README.md             # Main readme file
```

## 🛠 Technology Stack

### Core Framework

- **FastAPI**: Modern web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **Pydantic**: Data validation and settings management

### Database & Storage

- **MongoDB**: Document database with Motor async driver
- **Beanie**: Async MongoDB ODM based on Pydantic
- **DuckDB**: In-memory analytics database for data processing
- **Redis**: In-memory data structure store for caching
- **MinIO**: Object storage for file management

### Security & Encryption

- **Cryptography**: Advanced encryption using Fernet and PBKDF2
- **Clerk**: User authentication and management
- **PyJWT**: JSON Web Token handling
- **Passlib**: Password hashing with bcrypt

### Data Processing

- **Pandas**: Data analysis and manipulation
- **PyArrow**: Columnar data processing
- **OpenPyXL**: Excel file processing
- **CharDet**: Character encoding detection

### Monitoring & Logging

- **Sentry**: Error tracking and performance monitoring
- **Custom Logging**: Structured logging with JSON and colored formatters

### Development Tools

- **HTTPX**: Modern HTTP client for async requests
- **UV**: Fast Python package and project manager
- **YAML**: Configuration file management

## ⚙️ Configuration

The application uses environment-based configuration with the following settings groups:

### Application Settings (`APP_*`)

- `APP_NAME`: Application name (default: "Nonefinity Agent")
- `APP_ENV`: Environment (dev/prod, default: "dev")
- `APP_HOST`: Host address (default: "0.0.0.0")
- `APP_PORT`: Port number (default: 8000)
- `APP_DEBUG`: Debug mode (default: True)

### Credential Encryption (`CREDENTIAL_*`)

- `CREDENTIAL_SECRET_KEY`: Secret key for credential encryption (required)
- `CREDENTIAL_ENCRYPTION_SALT`: Salt for key derivation (required)
- `CREDENTIAL_KDF_ITERATIONS`: PBKDF2 iterations (default: 100,000)

### MongoDB Settings (`MONGO_*`)

- `MONGO_HOST`: MongoDB host
- `MONGO_PORT`: MongoDB port (default: 27017)
- `MONGO_DB`: Database name
- `MONGO_USER`: Username (optional)
- `MONGO_PWD`: Password (optional)

### Redis Settings (`REDIS_*`)

- `REDIS_HOST`: Redis host
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_PWD`: Redis password (optional)

### MinIO Settings (`MINIO_*`)

- `MINIO_URL`: MinIO server URL
- `MINIO_ACCESS_KEY`: MinIO access key
- `MINIO_SECRET_KEY`: MinIO secret key
- `MINIO_ALIAS`: MinIO alias name

### Clerk Authentication (`CLERK_*`)

- `CLERK_SECRET_KEY`: Clerk secret key
- `CLERK_WEBHOOK_SECRET`: Webhook secret
- `CLERK_ISSUER`: JWT issuer
- `CLERK_JWKS_URL`: JWKS endpoint URL

### DuckDB Settings (`DUCKDB_*`)

- `DUCKDB_TEMP_FOLDER`: Temporary folder for DuckDB instances
- `DUCKDB_INSTANCE_TTL`: Instance time-to-live (default: 600s)
- `DUCKDB_CLEANUP_INTERVAL`: Cleanup interval (default: 300s)

### Sentry Monitoring (`SENTRY_*`)

- `SENTRY_DSN`: Sentry Data Source Name
- `SENTRY_TRACES_SAMPLE_RATE`: Trace sampling rate (default: 0.2)
- `SENTRY_PROFILES_SAMPLE_RATE`: Profile sampling rate (default: 0.0)
- `SENTRY_SEND_DEFAULT_PII`: Send personal information (default: False)

## 🚦 Getting Started

### Prerequisites

- Python 3.12 or higher
- UV package manager
- MongoDB instance
- Redis instance
- MinIO instance

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
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Generate encryption keys (required)**

   ```bash
   python -c "import secrets, base64; print('CREDENTIAL_SECRET_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
   python -c "import secrets, base64; print('CREDENTIAL_ENCRYPTION_SALT=' + base64.urlsafe_b64encode(secrets.token_bytes(16)).decode())"
   ```

5. **Run the application**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The application will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📋 Available API Endpoints

### Provider Management (`/api/v1/providers/`)

- `GET /`: List all AI providers
- `POST /refresh`: Refresh providers from YAML configuration

### Credential Management (`/api/v1/credentials/`)

- `POST /`: Create new credential
- `GET /`: List user credentials
- `GET /{id}`: Get specific credential
- `PUT /{id}`: Update credential
- `DELETE /{id}`: Delete credential
- `POST /test`: Test credential validity
- `GET /provider/{name}`: Get credentials by provider
- `GET /encryption/health`: Check encryption system health
- `POST /encryption/generate-key`: Generate secure encryption keys

### File Management (`/api/v1/file/`)

- File upload, processing, and management endpoints

### Dataset Management (`/api/v1/datasets/`)

- Dataset creation, manipulation, and querying endpoints

### DuckDB Operations (`/api/v1/duckdb/`)

- In-memory database operations and analytics

### Authentication (`/api/v1/auth/`)

- User authentication and authorization endpoints

### Webhooks (`/api/v1/webhooks/`)

- External service webhook handlers

## 🔐 Security Features

### Credential Encryption

- **Fernet Encryption**: Military-grade AES 128 encryption with HMAC authentication
- **PBKDF2 Key Derivation**: 100,000+ iterations for password-based key derivation
- **Configurable Security**: Adjustable encryption parameters
- **Automatic Validation**: Built-in security parameter validation

### Authentication

- **JWT Tokens**: Secure token-based authentication
- **Clerk Integration**: Professional user management system
- **Role-based Access**: Fine-grained permission control

### Data Protection

- **API Key Masking**: Sensitive data is masked in responses
- **Environment-based Secrets**: All secrets loaded from environment variables
- **Automatic Validation**: Security settings validated at startup

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

### Why MongoDB with Beanie?

- Flexible document storage
- Async/await support
- Pydantic integration
- Schema validation
- Easy data modeling

### Why Fernet Encryption?

- Symmetric encryption with authentication
- Time-based token support
- Industry-standard security
- Python cryptography library
- Simple yet secure

### Why Environment-based Configuration?

- Security best practices
- Easy deployment management
- Development/production separation
- Validation at startup
- Type safety

## 🤝 Contributing

This project follows modern Python development practices:

- Type hints throughout the codebase
- Structured logging for debugging
- Environment-based configuration
- Comprehensive error handling
- Clean architecture separation
- Security-first approach

## 📝 Notes

- All text and comments are in English as per project requirements
- The application is designed for both development and production environments
- Comprehensive monitoring and logging are built-in from the start
- Security is prioritized with encryption and validation
- The project structure supports scalable development with clear separation of concerns
- Credential management system is production-ready with enterprise-grade security
