<div align="center">
  
  <img src="img/logo.jpg" alt="Nonefinity Logo" width="150" height="150" style="border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.12)">
  
  <br>

  <h1 style="font-size: 35px">Nonefinity Agent Backend</h1>
  
  <p>
    <img src="https://img.shields.io/badge/Python-orange?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-green?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/MongoDB-darkgreen?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB">
    <img src="https://img.shields.io/badge/Redis-red?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
    <img src="https://img.shields.io/badge/Qdrant-purple?style=for-the-badge&logo=&logoColor=white" alt="Qdrant">
    <img src="https://img.shields.io/badge/Sentry-black?style=for-the-badge&logo=sentry&logoColor=white" alt="Sentry">
  </p>

</div>

---

## 🌟 **What is Nonefinity Agent Backend?**

A **production-ready FastAPI backend** designed specifically for AI agent applications. Built with modern Python practices, comprehensive monitoring, and enterprise-grade architecture.

### ✨ **Key Highlights**

🚀 **Fast & Modern** - Built on FastAPI with async/await support  
🛡️ **Production Ready** - Complete error tracking, logging, and monitoring  
🔧 **Highly Configurable** - Environment-based configuration with type safety  
📊 **Observable** - Structured logging and Sentry integration  
🏗️ **Scalable Architecture** - Clean separation of concerns and modular design  

---

## 🚀 **Quick Start**

### Prerequisites
```bash
Python 3.12+ | uv Package Manager
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

| Category | Technology | Description |
|----------|------------|-------------|
| **🏗️ Framework** | FastAPI | Modern async web framework |
| **🐍 Language** | Python 3.12+ | Latest Python with type hints |
| **🗃️ Database** | MongoDB + Redis | Document DB + Caching |
| **🔍 Vector DB** | Qdrant | AI/ML vector operations |
| **📊 Monitoring** | Sentry | Error tracking & performance |
| **🔒 Auth** | JWT + OAuth | Secure authentication |
| **📦 Package Manager** | uv | Fast Python package management |

</div>

---

## 📁 **Project Structure**

```
🏠 Nonefinity_Backend/
├── 📱 app/                    # Main application
│   ├── 🌐 api/               # API routes & endpoints
│   ├── ⚙️ configs/           # Configuration management  
│   ├── 💾 crud/              # Database operations
│   ├── 🗃️ databases/         # DB connections
│   ├── 🛡️ middlewares/       # Custom middleware
│   ├── 📊 models/            # Data models
│   ├── 📋 schemas/           # API schemas
│   ├── 🏢 services/          # Business logic
│   ├── 🔧 utils/             # Utilities
│   └── 🚀 main.py            # Application entry
├── 📚 docs/                  # Documentation
│   ├── README_EN.md          # English docs
│   └── README_VI.md          # Vietnamese docs
├── 🖼️ img/                   # Branding assets
└── 📋 pyproject.toml         # Dependencies
```

---

## 🌟 **Core Features**

### 🔧 **Smart Configuration**
- **Environment-based settings** with automatic validation
- **Type-safe configuration** using Pydantic
- **Multi-service support** (MongoDB, Redis, Sentry, etc.)
- **Auto-loading** from `.env` files

### 📝 **Advanced Logging**
- **Structured JSON logs** for production
- **Beautiful colored console** for development  
- **Context-aware logging** with metadata
- **File rotation** and compression support

### 🔍 **Production Monitoring**
- **Sentry integration** for error tracking
- **Performance monitoring** with traces
- **Health check endpoints** 
- **Privacy-focused** data filtering

### 🛡️ **Security First**
- **JWT authentication** ready
- **Password hashing** with bcrypt
- **Sensitive data filtering**
- **CORS and security headers**

---

## 📊 **Available Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Welcome message & app info |
| `GET` | `/health` | Health check status |
| `GET` | `/docs` | Interactive API documentation |
| `GET` | `/redoc` | Alternative API documentation |

---

## 🔐 **Configuration**

Create a `.env` file with your settings:

```bash
# Application
APP_NAME="Nonefinity Agent"
APP_ENV="dev"
APP_HOST="0.0.0.0"
APP_PORT=8000

# Database
MONGO_HOST="localhost"
MONGO_PORT=27017
MONGO_DB="nonefinity"

# Redis
REDIS_URL="redis://localhost:6379"

# Monitoring
SENTRY_DSN="your-sentry-dsn"
```

---

## 📖 **Documentation**

<div align="center">

| Language | File | Description |
|----------|------|-------------|
| **English** | [`README_EN.md`](docs/README_EN.md) | Complete technical documentation |
| **Tiếng Việt** | [`README_VI.md`](docs/README_VI.md) | Tài liệu đầy đủ bằng tiếng Việt |

</div>

---

## 🎯 **Why Choose Nonefinity Backend?**

✅ **Battle-tested** architecture patterns  
✅ **Zero-config** structured logging  
✅ **Built-in** error tracking and monitoring  
✅ **Type-safe** configuration management  
✅ **Production-ready** from day one  
✅ **Comprehensive** documentation  
✅ **Modern** Python practices  

---

## 🤝 **Contributing**

We welcome contributions! Please see our detailed documentation for development guidelines.

1. Fork the repository
2. Create your feature branch
3. Make your changes with tests
4. Submit a pull request

---


---

<div align="center">
  
  <h3>🌟 Built with ❤️ by the Nonefinity Team</h3>
  
  <p>
    <strong>A solid foundation for building production-grade AI agent backends</strong>
  </p>
  
  <p>
    <a href="docs/README_EN.md">📖 English Docs</a> •
    <a href="docs/README_VI.md">📖 Tài liệu Việt</a> •
  </p>

  
</div>
