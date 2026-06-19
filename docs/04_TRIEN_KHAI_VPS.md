# Triển khai trang quản trị trên VPS

Trang quản trị là HTML/CSS/JavaScript nên không cần build một frontend riêng.
Trong cấu hình VPS, Nginx phục vụ giao diện trên cổng riêng và proxy các request
API tới FastAPI. Sau khi hai service chạy, truy cập:

```text
http://13.140.181.69:8080/admin
```

## 1. Chuẩn bị VPS

Cài Git và Docker Engine cùng Docker Compose plugin. Clone source:

```bash
sudo mkdir -p /opt/be-tool
sudo chown "$USER":"$USER" /opt/be-tool
git clone https://github.com/nhattvdx2/BE_Tool.git /opt/be-tool
cd /opt/be-tool
```

## 2. Cấu hình môi trường

Tạo `.env` trên VPS và không commit file này:

```env
APP_PORT=8000
ADMIN_PORT=8080
DATABASE_URL=postgresql+psycopg://nhattv:<DB_PASSWORD>@13.140.181.69:5432/app_tool_db?connect_timeout=5
CORS_ORIGINS=http://13.140.181.69:8080,http://localhost:4200
JWT_SECRET_KEY=<RANDOM_SECRET_AT_LEAST_32_CHARACTERS>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
UPLOAD_DIR=/app/uploads
MAX_AUDIO_FILE_SIZE_MB=20
AUDIT_LOG_ENABLED=true
AUDIT_LOG_DIR=/app/logs/audit
AUDIT_LOG_MAX_BYTES=10485760
AUDIT_LOG_BACKUP_COUNT=5
```

Sinh JWT secret bằng lệnh:

```bash
openssl rand -hex 32
```

Nếu PostgreSQL nằm cùng VPS, PostgreSQL vẫn phải cho phép kết nối từ Docker
network. Không mở cổng `5432` cho toàn Internet; chỉ cho phép các IP/network cần
thiết trong firewall và `pg_hba.conf`.

## 3. Build và chạy

```bash
cd /opt/be-tool
docker compose -f compose.vps.yaml up -d --build
docker compose -f compose.vps.yaml ps
docker compose -f compose.vps.yaml logs -f backend
```

Container `backend` tự chạy `alembic upgrade head` trước khi khởi động FastAPI.
Container `admin` phục vụ giao diện trên cổng `8080` và proxy `/api` nội bộ tới
backend. Dữ liệu upload nằm tại `/opt/be-tool/uploads`, log audit tại
`/opt/be-tool/logs/audit`.

## 4. Tạo tài khoản quản trị

```bash
docker compose -f compose.vps.yaml exec backend \
  python -m scripts.create_user admin --activate --admin
```

Lệnh sẽ yêu cầu nhập mật khẩu nếu không truyền `--password`.

## 5. Mở firewall và kiểm tra

Với UFW:

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 8080/tcp
sudo ufw status
```

Kiểm tra từ máy bên ngoài:

```bash
curl http://13.140.181.69:8000/health
curl http://13.140.181.69:8000/health/ready
```

Kết quả mong đợi:

```json
{"status":"ok"}
{"status":"ready","database":"ok","schema":"ok"}
```

Sau đó mở `http://13.140.181.69:8080/admin` và đăng nhập bằng tài khoản có
`is_active=true`, `is_default=true`.

## 6. Cập nhật phiên bản mới

```bash
cd /opt/be-tool
git pull origin main
docker compose -f compose.vps.yaml up -d --build
```

Không dùng `--reload` trên môi trường production.
