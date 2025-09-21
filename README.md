<div align="center">

  <img src="img/logo.jpg" alt="Nonefinity Logo" width="150" height="150" style="border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.12)">

  <br>

  <h1 style="font-size: 35px">Nonefinity Agent Backend</h1>

  <p>
    <img src="https://img.shields.io/badge/Python-orange?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-green?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/MongoDB-darkgreen?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB">
    <img src="https://img.shields.io/badge/Redis-red?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
    <img src="https://img.shields.io/badge/DuckDB-blue?style=for-the-badge&logo=&logoColor=white" alt="DuckDB">
    <img src="https://img.shields.io/badge/MinIO-purple?style=for-the-badge&logo=&logoColor=white" alt="MinIO">
    <img src="https://img.shields.io/badge/Sentry-black?style=for-the-badge&logo=sentry&logoColor=white" alt="Sentry">
  </p>

</div>

---

## 🌟 **What is Nonefinity Agent Backend?**

A **comprehensive AI agent backend platform** with advanced data processing, credential management, and multi-provider AI integration. Built for enterprise-grade AI applications with complete security, monitoring, and scalability.

### ✨ **Key Highlights**

🚀 **AI-Ready** - Multi-provider AI credential management with secure encryption
🗃️ **Data Platform** - Complete file processing with DuckDB analytics
🛡️ **Enterprise Security** - JWT authentication with encrypted credential storage
📊 **Analytics Ready** - Built-in data lake with parquet conversion
🔧 **Production Grade** - Complete monitoring, logging, and error tracking
🏗️ **Scalable Architecture** - Microservices design with clean separation

---

## 🚀 **Quick Start**

### Prerequisites

```bash
Python 3.12+ | uv Package Manager | MongoDB | Redis | MinIO
```

### Install & Run

```bash
# Clone the repository
git clone <repo-url>
cd Nonefinity_Backend

# Install dependencies
uv sync

# Create environment file
cp .env.sample .env

# Run the application
uv run uvicorn app.main:app --reload
```

**🎉 Your API will be running at:** `http://localhost:8000`

**📖 API Documentation:** `http://localhost:8000/docs`

---

## 🛠️ **Tech Stack**

<div align="center">

| Category               | Technology       | Description                         |
| ---------------------- | ---------------- | ----------------------------------- |
| **🏗️ Framework**       | FastAPI          | Modern async web framework          |
| **🐍 Language**        | Python 3.12+     | Latest Python with type hints       |
| **🗃️ Database**        | MongoDB + Redis  | Document DB + Caching               |
| **📊 Analytics**       | DuckDB           | In-process analytics database       |
| **📦 Storage**         | MinIO            | S3-compatible object storage        |
| **🔐 Authentication**  | Clerk + JWT      | Modern auth with token verification |
| **🔒 Encryption**      | Fernet (AES-128) | Credential encryption at rest       |
| **📋 Monitoring**      | Sentry           | Error tracking & performance        |
| **⚡ Package Manager** | uv               | Fast Python package management      |

</div>

---

## 📁 **Project Structure**

```
🏠 Nonefinity_Backend/
├── 📱 app/                    # Main application
│   ├── 🌐 api/               # API routes & endpoints
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── credential.py     # AI provider credentials
│   │   ├── provider.py       # AI provider management
│   │   ├── file.py           # File upload/management
│   │   ├── dataset.py        # Data processing & analytics
│   │   ├── duckdb.py         # DuckDB operations
│   │   └── webhooks.py       # Webhook handlers
│   ├── ⚙️ configs/           # Configuration management
│   │   ├── settings.py       # Environment settings
│   │   ├── setup.py          # App initialization
│   │   └── providers.yaml    # AI provider configurations
│   ├── 💾 crud/              # Database operations
│   ├── 🗃️ databases/         # DB connections & managers
│   │   ├── mongodb.py        # MongoDB connection
│   │   ├── duckdb.py         # DuckDB operations
│   │   └── duckdb_manager.py # DuckDB instance management
│   ├── 🛡️ middlewares/       # Custom middleware
│   ├── 📊 models/            # Data models
│   │   ├── user.py           # User model
│   │   ├── credential.py     # AI credentials
│   │   ├── file.py           # File metadata
│   │   └── dataset.py        # Dataset model
│   ├── 📋 schemas/           # API schemas
│   ├── 🏢 services/          # Business logic
│   │   ├── credential_service.py  # Credential management
│   │   ├── provider_service.py    # AI provider service
│   │   ├── file_service.py        # File operations
│   │   ├── dataset_service.py     # Data processing
│   │   ├── user.py               # User management
│   │   └── minio_*_service.py    # MinIO operations
│   ├── 🔧 utils/             # Utilities
│   │   ├── jwt_verification.py # JWT token handling
│   │   ├── file_classifier.py  # File type detection
│   │   └── api_response.py     # Standard responses
│   └── 🚀 main.py            # Application entry
├── 📚 docs/                  # Documentation
│   ├── README_EN.md          # English docs
│   └── README_VI.md          # Vietnamese docs
├── 🖼️ img/                   # Branding assets
├── 📝 logs/                  # Application logs
└── 📋 pyproject.toml         # Dependencies
```

---

## 🌟 **Core Features**

### 🔐 **AI Credential Management**

- **Multi-provider support** (OpenAI, Claude, etc.)
- **Encrypted storage** using Fernet (AES-128)
- **Test & validation** of AI credentials
- **Per-user credential isolation**
- **Custom provider configurations**

### 📊 **Data Processing Platform**

- **File upload & management** with MinIO storage
- **Automatic file classification** (CSV, Excel, JSON, etc.)
- **DuckDB integration** for analytics
- **Parquet conversion** for efficient storage
- **Data schema detection** and validation

### 🛡️ **Enterprise Security**

- **Clerk authentication** integration
- **JWT token verification** with custom middleware
- **Encrypted credential storage** with key derivation
- **Per-user data isolation** in MinIO buckets
- **Secure API key handling**

### 📈 **Analytics & Monitoring**

- **DuckDB analytics** for large datasets
- **Real-time query processing**
- **File processing statistics**
- **Sentry error tracking** and performance monitoring
- **Structured logging** with JSON format

### 🔧 **Developer Experience**

- **Auto-generated API docs** with FastAPI
- **Type-safe configuration** with Pydantic
- **Comprehensive error handling**
- **Clean architecture** with dependency injection
- **Test-ready** credential validation

---

## 📊 **Available Endpoints**

### 🔐 **Authentication**

| Method | Endpoint      | Description                    |
| ------ | ------------- | ------------------------------ |
| `POST` | `/auth/token` | Create JWT token from Clerk ID |
| `GET`  | `/auth/me`    | Get current user information   |

### 🗂️ **File Management**

| Method   | Endpoint                  | Description                   |
| -------- | ------------------------- | ----------------------------- |
| `POST`   | `/files/upload`           | Upload files to MinIO storage |
| `GET`    | `/files/list`             | List user's uploaded files    |
| `PUT`    | `/files/rename/{file_id}` | Rename uploaded file          |
| `DELETE` | `/files/{file_id}`        | Delete file from storage      |
| `POST`   | `/files/batch-delete`     | Delete multiple files         |

### 🔑 **AI Credentials**

| Method   | Endpoint                       | Description                     |
| -------- | ------------------------------ | ------------------------------- |
| `POST`   | `/credentials`                 | Create new AI credential        |
| `GET`    | `/credentials`                 | List user's credentials         |
| `GET`    | `/credentials/{id}`            | Get specific credential details |
| `PUT`    | `/credentials/{id}`            | Update credential               |
| `DELETE` | `/credentials/{id}`            | Delete credential               |
| `POST`   | `/credentials/test`            | Test credential validity        |
| `GET`    | `/credentials/provider/{name}` | Get credentials by provider     |

### 🤖 **AI Providers**

| Method | Endpoint             | Description                     |
| ------ | -------------------- | ------------------------------- |
| `GET`  | `/providers`         | List available AI providers     |
| `POST` | `/providers/refresh` | Refresh provider configurations |

### 📊 **Data Processing**

| Method   | Endpoint               | Description             |
| -------- | ---------------------- | ----------------------- |
| `POST`   | `/datasets/convert`    | Convert file to dataset |
| `GET`    | `/datasets`            | List user's datasets    |
| `GET`    | `/datasets/{id}`       | Get dataset details     |
| `POST`   | `/datasets/{id}/query` | Query dataset with SQL  |
| `DELETE` | `/datasets/{id}`       | Delete dataset          |

### 🦆 **DuckDB Analytics**

| Method | Endpoint          | Description                    |
| ------ | ----------------- | ------------------------------ |
| `GET`  | `/duckdb/stats`   | Get DuckDB instance statistics |
| `POST` | `/duckdb/cleanup` | Force cleanup of instances     |

### 🔔 **System**

| Method | Endpoint                 | Description                   |
| ------ | ------------------------ | ----------------------------- |
| `GET`  | `/`                      | API health and information    |
| `GET`  | `/health`                | Health check endpoint         |
| `POST` | `/webhooks/user/created` | Clerk user creation webhook   |
| `GET`  | `/docs`                  | Interactive API documentation |

---

## 🔐 **Configuration**

Create a `.env` file with your settings:

```bash
# Application
APP_NAME="Nonefinity Agent"
APP_ENV="dev"
APP_HOST="0.0.0.0"
APP_PORT=8000
APP_DEBUG=true

# Database
MONGO_HOST="localhost"
MONGO_PORT=27017
MONGO_DB="nonefinity"
MONGO_USER=""
MONGO_PWD=""

# Redis
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_PWD=""

# MinIO Storage
MINIO_HOST="localhost"
MINIO_PORT=9000
MINIO_ACCESS_KEY="minioadmin"
MINIO_SECRET_KEY="minioadmin"
MINIO_SECURE=false

# Authentication
CLERK_SECRET_KEY="your-clerk-secret"
CLERK_WEBHOOK_SECRET="your-webhook-secret"

# Credential Encryption
CREDENTIAL_SECRET_KEY="your-32-char-secret-key"
CREDENTIAL_ENCRYPTION_SALT="your-salt"
CREDENTIAL_KDF_ITERATIONS=100000

# Monitoring
SENTRY_DSN="your-sentry-dsn"
SENTRY_TRACES_SAMPLE_RATE=0.2

# CORS
CORS_ORIGINS=["http://localhost:5173"]
```

---

## 🎯 **Key Components**

### 🔐 **Credential Service**

- **Secure Encryption**: Uses PBKDF2-SHA256 + Fernet for credential storage
- **Multi-Provider**: Supports multiple AI providers with custom configurations
- **Validation**: Real-time credential testing and validation
- **Isolation**: Per-user credential management with owner-based access

### 📊 **Data Platform**

- **File Processing**: Automatic detection and conversion of data files
- **DuckDB Analytics**: High-performance in-process analytics database
- **Schema Detection**: Automatic data schema inference and validation
- **Parquet Storage**: Efficient columnar storage format

### 🏗️ **Architecture**

- **Clean Architecture**: Separation of concerns with CRUD, Services, and APIs
- **Async Processing**: Full async/await support for high performance
- **Type Safety**: Complete type hints and Pydantic validation
- **Error Handling**: Comprehensive error tracking and user-friendly messages

---

## 📖 **Documentation**

<div align="center">

| Language       | File                                | Description                      |
| -------------- | ----------------------------------- | -------------------------------- |
| **English**    | [`README_EN.md`](docs/README_EN.md) | Complete technical documentation |
| **Tiếng Việt** | [`README_VI.md`](docs/README_VI.md) | Tài liệu đầy đủ bằng tiếng Việt  |

</div>

---

## 🎯 **Why Choose Nonefinity Backend?**

✅ **AI-First Design** - Built specifically for AI agent applications
✅ **Data Platform Ready** - Complete data processing and analytics
✅ **Enterprise Security** - Military-grade encryption and authentication
✅ **Multi-Provider Support** - Works with any AI provider
✅ **Production Tested** - Battle-tested architecture patterns
✅ **Developer Friendly** - Comprehensive docs and type safety
✅ **Monitoring Built-in** - Complete observability from day one

---

## 🚀 **Recent Updates**

- ✨ **AI Credential Management** - Secure storage for multiple AI providers
- 📊 **Data Analytics Platform** - DuckDB integration for real-time analytics
- 🔐 **Enhanced Security** - Owner-based isolation and encrypted storage
- 📁 **File Processing** - Advanced file classification and conversion
- 🤖 **Provider Management** - Dynamic AI provider configuration
- 📈 **Performance Monitoring** - Complete observability stack

---

## 🤝 **Contributing**

We welcome contributions! Please see our detailed documentation for development guidelines.

1. Fork the repository
2. Create your feature branch
3. Make your changes with tests
4. Submit a pull request

---

<div align="center">

  <h3>🌟 Built with ❤️ by the Nonefinity Team</h3>

  <p>
    <strong>The complete platform for building production-grade AI agent backends</strong>
  </p>

  <p>
    <a href="docs/README_EN.md">📖 English Docs</a> •
    <a href="docs/README_VI.md">📖 Tài liệu Việt</a>
  </p>

</div>
