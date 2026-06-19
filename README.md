# Text-to-Speech and Voice Clone Backend

Backend FastAPI cho frontend Angular/Electron, dùng PostgreSQL, SQLAlchemy,
Alembic, JWT và local file storage.

## Công nghệ

- Python 3.11+
- FastAPI + Pydantic
- SQLAlchemy 2 + Alembic
- PostgreSQL + Psycopg 3
- JWT access token
- bcrypt password hashing

## Cấu trúc

```text
app/
  api/       # routes và dependencies
  core/      # settings và security
  db/        # SQLAlchemy engine/session
  models/    # ORM models
  schemas/   # Pydantic request/response
  services/  # business logic
  utils/     # local file storage
alembic/     # database migrations
scripts/     # admin CLI
tests/       # API/service tests
```

## Cài đặt

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Cập nhật `DATABASE_URL` và `JWT_SECRET_KEY` trong `.env`. URL SQLAlchemy dùng
Psycopg 3 có dạng:

```env
DATABASE_URL=postgresql+psycopg://user:password@host:5432/database
JWT_SECRET_KEY=a-long-random-secret
CORS_ORIGINS=http://localhost:4200
```

Không commit file `.env`.

## Migration và chạy API

```bash
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Swagger: `http://127.0.0.1:8000/docs`

Trang quản trị khi chạy trực tiếp để phát triển: `http://127.0.0.1:8000/admin`.
Trên VPS, Docker Compose tách giao diện quản trị sang cổng `8080`, trong khi API
và Swagger tiếp tục dùng cổng `8000`.

Triển khai production trên VPS bằng Docker và truy cập qua IP/port được hướng
dẫn tại [`docs/04_TRIEN_KHAI_VPS.md`](docs/04_TRIEN_KHAI_VPS.md).

Kiểm tra tiến trình API và database/schema:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/health/ready
```

`/health` chỉ xác nhận process FastAPI đang chạy. `/health/ready` chỉ trả `200`
khi backend kết nối được database và migration đã tạo bảng `users`.

## Quy trình tài khoản

1. Gọi `POST /api/auth/register`. User được tạo với `is_active=false`.
2. Hai bản ghi giới hạn được tạo tương ứng trong `voice_clones` và
   `voice_designs`.
3. Admin kích hoạt tài khoản, cấp quyền và đặt limit bằng CLI:

```bash
python -m scripts.create_user demo \
  --activate \
  --clone-voice \
  --design-voice \
  --clone-limit 10 \
  --design-limit 5
```

Để cấp quyền truy cập trang quản trị cho tài khoản đầu tiên:

```bash
python -m scripts.create_user admin --activate --admin
```

Trang quản trị dùng cờ `users.is_default` làm quyền admin. Admin có thể xem
dashboard, tạo và cập nhật tài khoản, bật/tắt quyền, đặt quota, đặt lại mật
khẩu, quản lý toàn bộ voice và xem audit log. Hệ thống ngăn admin tự khóa hoặc
tự gỡ quyền quản trị của chính mình.

4. Gọi `POST /api/auth/login` để nhận JWT.
5. Gửi JWT ở header `Authorization: Bearer <access_token>`.

Login trả `401` khi username/mật khẩu sai và trả `403` khi tài khoản chưa được
kích hoạt. Response `200` chỉ trả token cùng `id`, `username`, `clone_voice`,
`design_voice` và `gen_voice`.

## API

| Method | Endpoint | Auth | Mô tả |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | Không | Đăng ký user chưa kích hoạt |
| POST | `/api/auth/login` | Không | Đăng nhập và nhận JWT |
| POST | `/api/auth/changepassword` | JWT | Đổi mật khẩu |
| POST | `/api/auth/acceptFuntion` | JWT | Kiểm tra quyền màn hình |
| GET | `/api/auth/me` | JWT | Thông tin user hiện tại |
| GET | `/api/admin/dashboard` | Admin | Thống kê hệ thống |
| GET/POST | `/api/admin/users` | Admin | Danh sách/tạo tài khoản |
| PATCH | `/api/admin/users/{userId}` | Admin | Quyền, trạng thái và quota |
| POST | `/api/admin/users/{userId}/reset-password` | Admin | Đặt lại mật khẩu |
| GET | `/api/admin/voices` | Admin | Toàn bộ thư viện voice |
| PATCH/DELETE | `/api/admin/voices/{voiceId}` | Admin | Đổi tên/xóa voice |
| GET | `/api/admin/audit` | Admin | Nhật ký request gần đây |
| POST | `/api/voices/clone` | JWT | Tạo Clone Voice và upload audio |
| POST | `/api/voices/design` | JWT | Tạo Design Voice |
| GET | `/api/voices` | JWT | Danh sách voice có phân trang |
| GET | `/api/voices/limit` | JWT | Quota voice của tài khoản |
| GET | `/api/voices/{voiceId}` | JWT | Chi tiết voice |
| PATCH | `/api/voices/{voiceId}` | JWT | Đổi tên voice |
| DELETE | `/api/voices/{voiceId}` | JWT | Xóa voice |
| GET | `/api/voices/{voiceId}/audio` | JWT | Stream audio Clone Voice |

Mọi Voice API chỉ truy vấn dữ liệu có `user_id` của JWT hiện tại. User không
thể xem, đổi tên, xóa hoặc tải audio của tài khoản khác.

Ví dụ danh sách:

```http
GET /api/voices?page=1&pageSize=10&type=voice-clone&search=giọng
Authorization: Bearer <access_token>
```

Clone Voice hỗ trợ `.wav`, `.mp3`, `.m4a`. Kích thước tối đa được cấu hình bởi
`MAX_AUDIO_FILE_SIZE_MB`.

## Audit log theo user

Mọi HTTP request được ghi JSON Lines vào file riêng theo user trong
`AUDIT_LOG_DIR`. Request chưa xác thực được ghi vào file anonymous.

```env
AUDIT_LOG_ENABLED=true
AUDIT_LOG_DIR=logs/audit
AUDIT_LOG_MAX_BYTES=10485760
AUDIT_LOG_BACKUP_COUNT=5
```

Xem log realtime:

```bash
ls -lah logs/audit
tail -f logs/audit/*.log
```

Log chỉ chứa metadata request như thời gian, request ID, method, path, status,
IP và thời gian xử lý. Body, password, JWT và Authorization header không được
ghi. Response có header `X-Request-ID` để đối chiếu với log.

## PostgreSQL VPS

PostgreSQL phải listen trên IP mạng, cho phép IP máy chạy backend trong
`pg_hba.conf`, và firewall/security group phải mở cổng `5432` chỉ cho IP nguồn
cần thiết. Không mở PostgreSQL cho toàn bộ Internet.

## Test

Test dùng SQLite in-memory, không tác động PostgreSQL:

```bash
pytest
```
