# Nonefinity Agent Backend

<div align="center">
  <img src="../img/logo.jpg" alt="Nonefinity Logo" width="200" height="200" style="border-radius: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <br>
</div>

<div align="center">
  <h3>🤖 Ứng dụng Backend hiện đại cho Nonefinity Agent</h3>
  <p><em>Một hệ thống backend mạnh mẽ được xây dựng với FastAPI, tích hợp đầy đủ logging, monitoring và quản lý cấu hình.</em></p>
</div>

---

## 🌟 Tính Năng Đã Triển Khai

### ✅ **Framework Cốt Lõi**
- **🚀 Ứng dụng FastAPI**: Framework web async hiện đại với tài liệu OpenAPI tự động
- **📁 Cấu trúc dự án có tổ chức**: Phân tách rõ ràng các thành phần với module được tổ chức tốt
- **🐍 Python 3.12+**: Sử dụng các tính năng Python mới nhất và type hints
- **⚡ UV Package Manager**: Quản lý package và dự án Python nhanh chóng, hiện đại

### ✅ **Quản Lý Cấu Hình**
- **🔧 Cài đặt dựa trên môi trường**: Cấu hình toàn diện sử dụng Pydantic Settings
- **🏢 Cấu hình đa dịch vụ**: Các lớp cài đặt riêng biệt cho từng dịch vụ
- **🛡️ Cấu hình type-safe**: Kiểm tra kiểu đầy đủ với Pydantic models
- **🌍 Hỗ trợ biến môi trường**: Tự động load từ file `.env`

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

### ✅ **Quản Lý Vòng Đời Ứng Dụng**
- **🔄 Lifespan Events**: Xử lý khởi động và tắt ứng dụng đúng cách
- **✨ Khởi tạo mượt mà**: Khởi tạo dịch vụ theo thứ tự trong quá trình startup
- **🧹 Dọn dẹp tài nguyên**: Dọn dẹp đúng cách khi tắt ứng dụng
- **💓 Health Monitoring**: Endpoints kiểm tra sức khỏe tích hợp sẵn

## 📂 Cấu Trúc Dự Án

```
Nonefinity_Backend/
├── 📁 app/
│   ├── 🌐 api/                 # API routes và endpoints
│   ├── ⚙️ configs/            # Quản lý cấu hình
│   │   └── settings.py        # Cài đặt dựa trên môi trường
│   ├── 📋 consts/             # Các hằng số ứng dụng
│   ├── 💾 crud/               # Thao tác cơ sở dữ liệu (CRUD)
│   ├── 🗃️ databases/          # Kết nối và thiết lập cơ sở dữ liệu
│   ├── 🔗 dependencies/       # FastAPI dependencies
│   ├── 🛡️ middlewares/        # Custom middleware
│   │   └── sentry.py         # Thiết lập monitoring Sentry
│   ├── 📊 models/            # Database models
│   ├── 📋 schemas/           # Pydantic schemas cho API
│   ├── 🏢 services/          # Business logic services
│   ├── 🔧 utils/             # Các hàm tiện ích
│   │   └── logging.py        # Hệ thống logging nâng cao
│   └── 🚀 main.py            # Entry point của ứng dụng
├── 📄 docs/                  # Tài liệu dự án
│   └── README_VI.md          # Tài liệu tiếng Việt
├── 🖼️ img/                   # Hình ảnh và logo
│   ├── logo.jpg              # Logo Nonefinity
│   └── name.jpg              # Tên thương hiệu
├── 📋 pyproject.toml         # Dependencies và metadata
├── 🔒 uv.lock               # Dependencies đã khóa
└── 📖 README.md             # File readme chính
```

## 🛠️ Stack Công Nghệ

### Framework Cốt Lõi
- **FastAPI** 🚀: Framework web hiện đại để xây dựng APIs
- **Uvicorn** ⚡: ASGI server để chạy FastAPI applications
- **Pydantic** 🛡️: Validation dữ liệu và quản lý settings

### Cơ Sở Dữ Liệu & Lưu Trữ
- **MongoDB** 🍃: Document database với Motor async driver
- **Redis** 🔴: In-memory data structure store cho caching
- **Beanie** 🌱: Async MongoDB ODM dựa trên Pydantic

### Xác Thực & Bảo Mật
- **Authlib** 🔐: Thư viện OAuth và JWT authentication
- **Passlib** 🔒: Password hashing với bcrypt
- **Email Validator** ✉️: Tiện ích validation email

### Monitoring & Logging
- **Sentry** 📊: Theo dõi lỗi và hiệu suất
- **Custom Logging** 📝: Structured logging với JSON và colored formatters

### Vector Database
- **Qdrant** 🔍: Vector database cho ứng dụng AI/ML

### Công Cụ Phát Triển
- **HTTPX** 🌐: HTTP client hiện đại cho async requests
- **UV** ⚡: Fast Python package và project manager

## ⚙️ Cấu Hình

Ứng dụng sử dụng cấu hình dựa trên môi trường với các nhóm cài đặt sau:

### Cài Đặt Ứng Dụng (`APP_*`)
- `APP_NAME`: Tên ứng dụng (mặc định: "Nonefinity Agent")
- `APP_ENV`: Môi trường (dev/prod, mặc định: "dev")
- `APP_HOST`: Địa chỉ host (mặc định: "0.0.0.0")
- `APP_PORT`: Số port (mặc định: 8000)
- `APP_DEBUG`: Chế độ debug (mặc định: True)

### Cài Đặt MongoDB (`MONGO_*`)
- `MONGO_HOST`: MongoDB host
- `MONGO_PORT`: MongoDB port (mặc định: 27017)
- `MONGO_DB`: Tên database
- `MONGO_USER`: Username (tùy chọn)
- `MONGO_PWD`: Password (tùy chọn)

### Cài Đặt Redis (`REDIS_*`)
- `REDIS_URL`: URL kết nối Redis
- `REDIS_PWD`: Password Redis (tùy chọn)

### Monitoring Sentry (`SENTRY_*`)
- `SENTRY_DSN`: Sentry Data Source Name
- `SENTRY_TRACES_SAMPLE_RATE`: Tỷ lệ sampling trace (mặc định: 0.2)
- `SENTRY_PROFILES_SAMPLE_RATE`: Tỷ lệ sampling profile (mặc định: 0.0)
- `SENTRY_SEND_DEFAULT_PII`: Gửi thông tin cá nhân (mặc định: False)

### Xác Thực (`AUTH_*`)
- `AUTH_JWT_ISS`: JWT issuer (mặc định: "http://127.0.0.1:8000")
- `AUTH_JWT_AUD`: JWT audience
- `AUTH_JWT_ALG`: JWT algorithm (mặc định: "HS256")
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Thời gian hết hạn access token (mặc định: 15)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Thời gian hết hạn refresh token (mặc định: 14)

### Vector Database (`QDRANT_*`)
- `QDRANT_URL`: URL kết nối Qdrant

### Cài Đặt Khác
- `RELEASE`: Phiên bản release ứng dụng (tùy chọn)

## 🚀 Bắt Đầu

### Yêu Cầu Hệ Thống
- Python 3.12 hoặc cao hơn
- UV package manager

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
   cp .env.sample .env
   # Chỉnh sửa .env với cấu hình của bạn
   ```

4. **Chạy ứng dụng**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

Ứng dụng sẽ có sẵn tại `http://localhost:8000`

### Tài Liệu API
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📋 Các Endpoint Có Sẵn

### Health & Status
- `GET /`: Thông điệp chào mừng với thông tin ứng dụng
- `GET /health`: Endpoint kiểm tra sức khỏe

## 🔧 Tính Năng Phát Triển

### Hệ Thống Logging
Ứng dụng bao gồm hệ thống logging tinh vi với:

- **Chế độ Development**: Console output có màu sắc để debug dễ dàng
- **Chế độ Production**: JSON structured logs cho log aggregation
- **File Logging**: Output file tùy chọn cho logging bền vững
- **Hỗ trợ Context**: Thêm dữ liệu có cấu trúc vào log messages
- **Tích hợp thư viện**: Cấu hình logging cho FastAPI, MongoDB, Redis, v.v.

### Error Monitoring
Tích hợp Sentry cung cấp:

- **Theo dõi lỗi**: Tự động capture và báo cáo lỗi
- **Monitoring hiệu suất**: Request tracing và performance insights
- **Bảo mật dữ liệu**: Tự động lọc thông tin nhạy cảm
- **Custom Sampling**: Tỷ lệ sampling lỗi và trace có thể cấu hình

### Quản Lý Cấu Hình
Cấu hình dựa trên môi trường với:

- **Type Safety**: Validation Pydantic đầy đủ cho tất cả settings
- **Phân tách môi trường**: Configs khác nhau cho dev/prod environments
- **Cách ly dịch vụ**: Settings riêng biệt cho mỗi external service
- **Auto-loading**: Tự động load biến môi trường

## 🏗️ Quyết Định Kiến Trúc

### Tại Sao FastAPI?
- Hỗ trợ async/await hiện đại
- Tài liệu API tự động
- Validation dữ liệu tích hợp sẵn
- Hiệu suất cao
- Trải nghiệm developer tuyệt vời

### Tại Sao Pydantic Settings?
- Cấu hình type-safe
- Tự động parse biến môi trường
- Validation tích hợp sẵn
- Dễ dàng test với configs khác nhau

### Tại Sao Structured Logging?
- Log aggregation và tìm kiếm tốt hơn
- Định dạng log nhất quán across services
- Khả năng debugging được cải thiện
- Sẵn sàng cho production monitoring

### Tại Sao Sentry?
- Theo dõi lỗi toàn diện
- Monitoring hiệu suất
- Alerting thời gian thực
- Tích hợp với các dịch vụ phổ biến

## 🔄 Các Khu Vực Triển Khai Tương Lai

Cấu trúc dự án được chuẩn bị cho:

- **API Routes** (`app/api/`): REST API endpoints
- **Database Models** (`app/models/`): Data models và schemas
- **CRUD Operations** (`app/crud/`): Database interaction layer
- **Business Services** (`app/services/`): Business logic implementation
- **Dependencies** (`app/dependencies/`): FastAPI dependency injection
- **Database Setup** (`app/databases/`): Database connection và initialization

## 🤝 Đóng Góp

Dự án này tuân theo các practices phát triển Python hiện đại:
- Type hints throughout codebase
- Structured logging cho debugging
- Cấu hình dựa trên môi trường
- Xử lý lỗi toàn diện
- Phân tách kiến trúc rõ ràng

## 🎯 Điểm Mạnh Của Implementation

### 1. **Production-Ready từ ngày đầu**
- Theo dõi lỗi toàn diện
- Structured logging
- Cấu hình dựa trên môi trường
- Best practices bảo mật

### 2. **Trải Nghiệm Developer**
- Logs có màu sắc đẹp mắt cho development
- Cấu hình type-safe
- Tài liệu API tự động
- Cấu trúc dự án rõ ràng

### 3. **Chuẩn Bị Cho Scalability**
- Kiến trúc modular
- Async/await throughout
- Separation of concerns
- Sẵn sàng cho microservices

### 4. **Monitoring & Observability**
- Logging chi tiết với context
- Theo dõi lỗi với Sentry
- Monitoring hiệu suất
- Health checks

### 5. **Tập Trung Vào Bảo Mật**
- Thiết lập JWT authentication
- Password hashing với bcrypt
- Lọc dữ liệu nhạy cảm
- Secrets dựa trên môi trường

---

<div align="center">
  <h3>🌟 Được xây dựng với ❤️ bởi Nonefinity Team</h3>
  <p><em>Một nền tảng vững chắc cho việc xây dựng ứng dụng backend production-grade!</em></p>
</div>
