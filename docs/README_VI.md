# Nonefinity Agent Backend

<div align="center">
  <img src="../img/logo.jpg" alt="Nonefinity Logo" width="200" height="200" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
</div>

<div align="center">
  <h3>🤖 Ứng dụng Backend hiện đại cho Nonefinity Agent</h3>
  <p><em>Một hệ thống backend mạnh mẽ được xây dựng với FastAPI, tích hợp đầy đủ logging, monitoring, quản lý credentials AI và bảo mật nâng cao.</em></p>
</div>

---

## 🌟 Tính Năng Đã Triển Khai

### ✅ **Framework Cốt Lõi**

- **🚀 Ứng dụng FastAPI**: Framework web async hiện đại với tài liệu OpenAPI tự động
- **📁 Cấu trúc dự án có tổ chức**: Phân tách rõ ràng các thành phần với module được tổ chức tốt
- **🐍 Python 3.12+**: Sử dụng các tính năng Python mới nhất và type hints
- **⚡ UV Package Manager**: Quản lý package và dự án Python nhanh chóng, hiện đại

### ✅ **Hệ Thống Quản Lý Credential AI**

- **🔐 Lưu trữ Credential An toàn**: Mã hóa API key sử dụng Fernet encryption
- **🏢 Hỗ trợ Nhiều Provider**: OpenAI, OpenRouter và hệ thống provider có thể mở rộng
- **🔑 Thao tác CRUD**: Quản lý credential hoàn chỉnh (Tạo, Đọc, Cập nhật, Xóa)
- **🛡️ Bảo mật Nâng cao**: PBKDF2 key derivation với số lần lặp có thể cấu hình
- **✅ Kiểm tra Credential**: Validation API key tích hợp sẵn và health checks
- **📝 Cấu hình Provider**: Định nghĩa provider dựa trên YAML với auto-loading

### ✅ **Cơ Sở Dữ Liệu & Lưu Trữ**

- **🍃 Tích hợp MongoDB**: Document database với Beanie ODM cho thao tác async
- **🦆 Hỗ trợ DuckDB**: In-memory analytics database để xử lý dữ liệu
- **🔴 Tích hợp Redis**: Caching và quản lý session
- **📁 Quản lý File**: Upload, xử lý và lưu trữ với tích hợp MinIO
- **📊 Quản lý Dataset**: Xử lý dữ liệu có cấu trúc và validation schema

### ✅ **Quản Lý Cấu Hình**

- **🔧 Cài đặt dựa trên môi trường**: Cấu hình toàn diện sử dụng Pydantic Settings
- **🏢 Cấu hình đa dịch vụ**: Các lớp cài đặt riêng biệt cho từng dịch vụ
- **🛡️ Cấu hình type-safe**: Kiểm tra kiểu đầy đủ với Pydantic models
- **🌍 Hỗ trợ biến môi trường**: Tự động load từ file `.env`
- **🔒 Validation Bảo mật**: Tự động validation các cài đặt mã hóa

### ✅ **Hệ Thống Logging Nâng Cao**

- **📋 Structured Logging**: Định dạng JSON cho môi trường production
- **🌈 Console Output màu sắc**: Trải nghiệm phát triển tốt hơn với logs có màu
- **🔄 Nhiều Formatter**: JSON cho production, text màu cho development
- **📄 File Logging**: Output file có thể cấu hình với tự động tạo thư mục
- **📊 Context Logging**: Hỗ trợ thêm context có cấu trúc vào log messages
- **⚙️ Cấu hình Logger**: Điều chỉnh mức logging cho các thư viện khác nhau

### ✅ **Monitoring & Theo Dõi Lỗi**

- **🔍 Tích hợp Sentry**: Theo dõi lỗi và hiệu suất hoàn chỉnh
- **🔗 Nhiều Integration**: Tích hợp FastAPI, Redis, MongoDB, và logging
- **🔒 Bảo mật dữ liệu**: Tự động lọc thông tin nhạy cảm (headers, cookies)
- **💚 Lọc Health Check**: Loại trừ health checks khỏi theo dõi transaction
- **📈 Sampling có thể cấu hình**: Tỷ lệ sampling trace và error có thể điều chỉnh

### ✅ **Xác Thực & Bảo Mật**

- **🔐 Xác thực Clerk**: Xác thực người dùng an toàn với JWT tokens
- **👥 Quản lý User**: Quản lý vòng đời người dùng hoàn chỉnh
- **🛡️ Hệ thống Permission**: Kiểm soát truy cập dựa trên vai trò
- **🔑 Mã hóa API Key**: Mã hóa cấp quân sự cho credentials nhạy cảm
- **🔒 Security Headers**: Quản lý security header tự động

### ✅ **Quản Lý Vòng Đời Ứng Dụng**

- **🔄 Lifespan Events**: Xử lý khởi động và tắt ứng dụng đúng cách
- **✨ Khởi tạo mượt mà**: Khởi tạo dịch vụ theo thứ tự trong quá trình startup
- **🧹 Dọn dẹp tài nguyên**: Dọn dẹp đúng cách khi tắt ứng dụng
- **💓 Health Monitoring**: Endpoints kiểm tra sức khỏe tích hợp sẵn

## 📂 Cấu Trúc Dự Án

```
Nonefinity_Backend/
├── 📁 app/
│   ├── 🌐 api/                    # API routes và endpoints
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── credential.py         # API quản lý credential
│   │   ├── provider.py           # API quản lý AI provider
│   │   ├── dataset.py            # API quản lý dataset
│   │   ├── file.py              # API quản lý file
│   │   ├── duckdb.py            # API thao tác DuckDB
│   │   └── webhooks.py          # Webhook handlers
│   ├── ⚙️ configs/               # Quản lý cấu hình
│   │   ├── settings.py          # Cài đặt dựa trên môi trường
│   │   ├── providers.yaml       # Định nghĩa AI providers
│   │   └── setup.py             # Thiết lập và vòng đời ứng dụng
│   ├── 📋 consts/                # Các hằng số ứng dụng
│   │   └── user_event_type.py
│   ├── 🏗️ core/                  # Logic ứng dụng cốt lõi
│   │   └── exceptions.py        # Custom exception handlers
│   ├── 💾 crud/                  # Thao tác cơ sở dữ liệu (CRUD)
│   │   ├── base.py              # Thao tác CRUD cơ bản
│   │   ├── credential.py        # Thao tác CRUD credential
│   │   ├── dataset.py           # Thao tác CRUD dataset
│   │   ├── file.py              # Thao tác CRUD file
│   │   └── user.py              # Thao tác CRUD user
│   ├── 🗃️ databases/             # Kết nối và thiết lập cơ sở dữ liệu
│   │   ├── mongodb.py           # MongoDB connection manager
│   │   ├── duckdb.py            # Thao tác DuckDB
│   │   └── duckdb_manager.py    # Quản lý DuckDB instance
│   ├── 🔗 dependencies/          # FastAPI dependencies
│   ├── 🛡️ middlewares/           # Custom middleware
│   │   └── sentry.py            # Thiết lập monitoring Sentry
│   ├── 📊 models/                # Database models
│   │   ├── credential.py        # Provider và Credential models
│   │   ├── dataset.py           # Dataset models
│   │   ├── file.py              # File models
│   │   ├── user.py              # User models
│   │   ├── time_mixin.py        # Timestamp mixin
│   │   └── soft_delete_mixin.py # Chức năng soft delete
│   ├── 📋 schemas/               # Pydantic schemas cho API
│   │   ├── credential.py        # Credential request/response schemas
│   │   ├── dataset.py           # Dataset schemas
│   │   ├── file.py              # File schemas
│   │   ├── response.py          # Common response schemas
│   │   └── user.py              # User schemas
│   ├── 🏢 services/              # Business logic services
│   │   ├── credential_service.py  # Service quản lý credential
│   │   ├── provider_service.py    # Service quản lý provider
│   │   ├── dataset_service.py     # Service xử lý dataset
│   │   ├── file_service.py        # Service xử lý file
│   │   ├── minio_admin_service.py # Quản trị MinIO
│   │   ├── minio_client_service.py # Thao tác MinIO client
│   │   ├── mongodb_service.py     # MongoDB service layer
│   │   └── user.py               # Service quản lý user
│   ├── 🔧 utils/                 # Các hàm tiện ích
│   │   ├── api_response.py      # API responses chuẩn hóa
│   │   ├── base.py              # Tiện ích cơ bản
│   │   ├── file_classifier.py   # Phân loại file type
│   │   ├── jwt_verification.py  # Verification JWT token
│   │   ├── logging.py           # Hệ thống logging nâng cao
│   │   └── verify_token.py      # Tiện ích verification token
│   └── 🚀 main.py               # Entry point của ứng dụng
├── 📄 docs/                     # Tài liệu dự án
│   ├── README_EN.md             # Tài liệu tiếng Anh
│   └── README_VI.md             # Tài liệu tiếng Việt
├── 🖼️ img/                      # Hình ảnh và assets
│   ├── logo.jpg                 # Logo Nonefinity
│   └── logo.ico                 # Favicon
├── 📋 logs/                     # Application logs
│   └── app.log                  # Log ứng dụng chính
├── 📋 pyproject.toml            # Dependencies và metadata
├── 🔒 uv.lock                   # Dependencies đã khóa
└── 📖 README.md                 # File readme chính
```

## 🛠️ Stack Công Nghệ

### Framework Cốt Lõi

- **FastAPI** 🚀: Framework web hiện đại để xây dựng APIs
- **Uvicorn** ⚡: ASGI server để chạy FastAPI applications
- **Pydantic** 🛡️: Validation dữ liệu và quản lý settings

### Cơ Sở Dữ Liệu & Lưu Trữ

- **MongoDB** 🍃: Document database với Motor async driver
- **Beanie** 🌱: Async MongoDB ODM dựa trên Pydantic
- **DuckDB** 🦆: In-memory analytics database để xử lý dữ liệu
- **Redis** 🔴: In-memory data structure store cho caching
- **MinIO** 📁: Object storage để quản lý file

### Bảo Mật & Mã Hóa

- **Cryptography** 🔒: Mã hóa nâng cao sử dụng Fernet và PBKDF2
- **Clerk** 🔐: Xác thực và quản lý người dùng
- **PyJWT** 🎫: Xử lý JSON Web Token
- **Passlib** 🛡️: Password hashing với bcrypt

### Xử Lý Dữ Liệu

- **Pandas** 🐼: Phân tích và thao tác dữ liệu
- **PyArrow** 🏹: Xử lý dữ liệu columnar
- **OpenPyXL** 📊: Xử lý file Excel
- **CharDet** 🔍: Phát hiện character encoding

### Monitoring & Logging

- **Sentry** 📊: Theo dõi lỗi và hiệu suất
- **Custom Logging** 📝: Structured logging với JSON và colored formatters

### Công Cụ Phát Triển

- **HTTPX** 🌐: HTTP client hiện đại cho async requests
- **UV** ⚡: Fast Python package và project manager
- **YAML** 📄: Quản lý file cấu hình

## ⚙️ Cấu Hình

Ứng dụng sử dụng cấu hình dựa trên môi trường với các nhóm cài đặt sau:

### Cài Đặt Ứng Dụng (`APP_*`)

- `APP_NAME`: Tên ứng dụng (mặc định: "Nonefinity Agent")
- `APP_ENV`: Môi trường (dev/prod, mặc định: "dev")
- `APP_HOST`: Địa chỉ host (mặc định: "0.0.0.0")
- `APP_PORT`: Số port (mặc định: 8000)
- `APP_DEBUG`: Chế độ debug (mặc định: True)

### Mã Hóa Credential (`CREDENTIAL_*`)

- `CREDENTIAL_SECRET_KEY`: Secret key để mã hóa credential (bắt buộc)
- `CREDENTIAL_ENCRYPTION_SALT`: Salt để key derivation (bắt buộc)
- `CREDENTIAL_KDF_ITERATIONS`: Số lần lặp PBKDF2 (mặc định: 100,000)

### Cài Đặt MongoDB (`MONGO_*`)

- `MONGO_HOST`: MongoDB host
- `MONGO_PORT`: MongoDB port (mặc định: 27017)
- `MONGO_DB`: Tên database
- `MONGO_USER`: Username (tùy chọn)
- `MONGO_PWD`: Password (tùy chọn)

### Cài Đặt Redis (`REDIS_*`)

- `REDIS_HOST`: Redis host
- `REDIS_PORT`: Redis port (mặc định: 6379)
- `REDIS_PWD`: Password Redis (tùy chọn)

### Cài Đặt MinIO (`MINIO_*`)

- `MINIO_URL`: URL MinIO server
- `MINIO_ACCESS_KEY`: MinIO access key
- `MINIO_SECRET_KEY`: MinIO secret key
- `MINIO_ALIAS`: Tên alias MinIO

### Xác Thực Clerk (`CLERK_*`)

- `CLERK_SECRET_KEY`: Clerk secret key
- `CLERK_WEBHOOK_SECRET`: Webhook secret
- `CLERK_ISSUER`: JWT issuer
- `CLERK_JWKS_URL`: JWKS endpoint URL

### Cài Đặt DuckDB (`DUCKDB_*`)

- `DUCKDB_TEMP_FOLDER`: Thư mục tạm cho DuckDB instances
- `DUCKDB_INSTANCE_TTL`: Thời gian sống instance (mặc định: 600s)
- `DUCKDB_CLEANUP_INTERVAL`: Khoảng thời gian dọn dẹp (mặc định: 300s)

### Monitoring Sentry (`SENTRY_*`)

- `SENTRY_DSN`: Sentry Data Source Name
- `SENTRY_TRACES_SAMPLE_RATE`: Tỷ lệ sampling trace (mặc định: 0.2)
- `SENTRY_PROFILES_SAMPLE_RATE`: Tỷ lệ sampling profile (mặc định: 0.0)
- `SENTRY_SEND_DEFAULT_PII`: Gửi thông tin cá nhân (mặc định: False)

## 🚀 Bắt Đầu

### Yêu Cầu Hệ Thống

- Python 3.12 hoặc cao hơn
- UV package manager
- MongoDB instance
- Redis instance (tùy chọn)
- MinIO instance (tùy chọn)

### Cài Đặt

1. **Clone repository**

   ```bash
   git clone <repository-url>
   cd Nonefinity_Backend
   ```

2. **Cài đặt dependencies**

   ```bash
   uv sync
   ```

3. **Tạo file môi trường**

   ```bash
   cp .env.example .env
   # Chỉnh sửa .env với cấu hình của bạn
   ```

4. **Tạo encryption keys (bắt buộc)**

   ```bash
   python -c "import secrets, base64; print('CREDENTIAL_SECRET_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
   python -c "import secrets, base64; print('CREDENTIAL_ENCRYPTION_SALT=' + base64.urlsafe_b64encode(secrets.token_bytes(16)).decode())"
   ```

5. **Chạy ứng dụng**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

Ứng dụng sẽ có sẵn tại `http://localhost:8000`

### Tài Liệu API

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📋 Các API Endpoints Có Sẵn

### Quản Lý Provider (`/api/v1/providers/`)

- `GET /`: Liệt kê tất cả AI providers
- `POST /refresh`: Refresh providers từ cấu hình YAML

### Quản Lý Credential (`/api/v1/credentials/`)

- `POST /`: Tạo credential mới
- `GET /`: Liệt kê credentials của user
- `GET /{id}`: Lấy credential cụ thể
- `PUT /{id}`: Cập nhật credential
- `DELETE /{id}`: Xóa credential
- `POST /test`: Kiểm tra tính hợp lệ của credential
- `GET /provider/{name}`: Lấy credentials theo provider
- `GET /encryption/health`: Kiểm tra sức khỏe hệ thống mã hóa
- `POST /encryption/generate-key`: Tạo encryption keys an toàn

### Quản Lý File (`/api/v1/file/`)

- Endpoints upload, xử lý và quản lý file

### Quản Lý Dataset (`/api/v1/datasets/`)

- Endpoints tạo, thao tác và truy vấn dataset

### Thao Tác DuckDB (`/api/v1/duckdb/`)

- Thao tác cơ sở dữ liệu in-memory và analytics

### Xác Thực (`/api/v1/auth/`)

- Endpoints xác thực và ủy quyền người dùng

### Webhooks (`/api/v1/webhooks/`)

- Webhook handlers cho external services

## 🔐 Tính Năng Bảo Mật

### Mã Hóa Credential

- **🔒 Fernet Encryption**: Mã hóa AES 128 cấp quân sự với HMAC authentication
- **🔑 PBKDF2 Key Derivation**: 100,000+ lần lặp cho password-based key derivation
- **⚙️ Bảo mật Có thể Cấu hình**: Các tham số mã hóa có thể điều chỉnh
- **✅ Validation Tự động**: Validation tham số bảo mật tích hợp sẵn

### Xác Thực

- **🎫 JWT Tokens**: Xác thực an toàn dựa trên token
- **👥 Tích hợp Clerk**: Hệ thống quản lý người dùng chuyên nghiệp
- **🛡️ Kiểm soát Truy cập theo Vai trò**: Kiểm soát permission chi tiết

### Bảo Vệ Dữ Liệu

- **🎭 Masking API Key**: Dữ liệu nhạy cảm được che giấu trong responses
- **🌍 Secrets Dựa trên Môi trường**: Tất cả secrets được load từ biến môi trường
- **🔍 Validation Tự động**: Cài đặt bảo mật được validation khi khởi động

## 🔧 Tính Năng Phát Triển

### Hệ Thống Logging

Ứng dụng bao gồm hệ thống logging tinh vi với:

- **🎨 Chế độ Development**: Console output có màu sắc để debug dễ dàng
- **📊 Chế độ Production**: JSON structured logs cho log aggregation
- **📄 File Logging**: Output file tùy chọn cho logging bền vững
- **📋 Hỗ trợ Context**: Thêm dữ liệu có cấu trúc vào log messages
- **🔧 Tích hợp thư viện**: Cấu hình logging cho FastAPI, MongoDB, Redis, v.v.

### Error Monitoring

Tích hợp Sentry cung cấp:

- **🔍 Theo dõi lỗi**: Tự động capture và báo cáo lỗi
- **📊 Monitoring hiệu suất**: Request tracing và performance insights
- **🔒 Bảo mật dữ liệu**: Tự động lọc thông tin nhạy cảm
- **⚙️ Custom Sampling**: Tỷ lệ sampling lỗi và trace có thể cấu hình

### Quản Lý Cấu Hình

Cấu hình dựa trên môi trường với:

- **🛡️ Type Safety**: Validation Pydantic đầy đủ cho tất cả settings
- **🌍 Phân tách môi trường**: Configs khác nhau cho dev/prod environments
- **🏢 Cách ly dịch vụ**: Settings riêng biệt cho mỗi external service
- **🔄 Auto-loading**: Tự động load biến môi trường

## 🏗️ Quyết Định Kiến Trúc

### Tại Sao FastAPI?

- Hỗ trợ async/await hiện đại
- Tài liệu API tự động
- Validation dữ liệu tích hợp sẵn
- Hiệu suất cao
- Trải nghiệm developer tuyệt vời

### Tại Sao MongoDB với Beanie?

- Lưu trữ document linh hoạt
- Hỗ trợ async/await
- Tích hợp Pydantic
- Validation schema
- Modeling dữ liệu dễ dàng

### Tại Sao Fernet Encryption?

- Symmetric encryption với authentication
- Hỗ trợ time-based token
- Bảo mật theo tiêu chuẩn ngành
- Thư viện cryptography Python
- Đơn giản nhưng an toàn

### Tại Sao Cấu hình Dựa trên Môi trường?

- Best practices bảo mật
- Quản lý deployment dễ dàng
- Phân tách development/production
- Validation khi khởi động
- Type safety

## 🎯 Điểm Mạnh Của Implementation

### 1. **🚀 Production-Ready từ ngày đầu**

- Theo dõi lỗi toàn diện với Sentry
- Structured logging với context
- Cấu hình dựa trên môi trường
- Best practices bảo mật tích hợp sẵn

### 2. **🎨 Trải Nghiệm Developer Tuyệt vời**

- Logs có màu sắc đẹp mắt cho development
- Cấu hình type-safe với validation
- Tài liệu API tự động và đầy đủ
- Cấu trúc dự án rõ ràng và có tổ chức

### 3. **⚡ Chuẩn Bị Cho Scalability**

- Kiến trúc modular với separation of concerns
- Async/await throughout toàn bộ codebase
- Hỗ trợ microservices architecture
- Database và service layer tách biệt

### 4. **📊 Monitoring & Observability Toàn diện**

- Logging chi tiết với structured context
- Theo dõi lỗi realtime với Sentry
- Monitoring hiệu suất và performance insights
- Health checks và system status monitoring

### 5. **🔒 Tập Trung Vào Bảo Mật**

- Mã hóa credential cấp enterprise
- JWT authentication với Clerk integration
- Password hashing với bcrypt
- Automatic filtering của dữ liệu nhạy cảm
- Environment-based secrets management

### 6. **🔐 Hệ Thống Credential Management Chuyên nghiệp**

- Mã hóa Fernet với PBKDF2 key derivation
- Multiple AI provider support (OpenAI, OpenRouter)
- CRUD operations hoàn chỉnh với validation
- Credential testing và health monitoring
- YAML-based provider configuration

### 7. **📁 Quản Lý Dữ liệu Đa dạng**

- MongoDB cho document storage
- DuckDB cho analytics và data processing
- Redis cho caching và session management
- MinIO cho object storage
- File processing với multiple formats

---

<div align="center">
  <h3>🌟 Được xây dựng với ❤️ bởi Nonefinity Team</h3>
  <p><em>Một nền tảng vững chắc và an toàn cho việc xây dựng ứng dụng backend production-grade!</em></p>
  <p><strong>🔐 Enterprise-grade Security | 🚀 Production-Ready | ⚡ High Performance | 🎯 Developer-Friendly</strong></p>
</div>
