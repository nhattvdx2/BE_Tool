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

4. Gọi `POST /api/auth/login` để nhận JWT.
5. Gửi JWT ở header `Authorization: Bearer <access_token>`.

## API

| Method | Endpoint | Auth | Mô tả |
| --- | --- | --- | --- |
| POST | `/api/auth/register` | Không | Đăng ký user chưa kích hoạt |
| POST | `/api/auth/login` | Không | Đăng nhập và nhận JWT |
| POST | `/api/auth/changepassword` | JWT | Đổi mật khẩu |
| POST | `/api/auth/acceptFuntion` | JWT | Kiểm tra quyền màn hình |
| GET | `/api/auth/me` | JWT | Thông tin user hiện tại |
| GET | `/api/voices/numberLimit` | JWT | Lấy giới hạn theo `username`, `screenid` |
| POST | `/api/voices/upload` | JWT | Upload file local theo quyền màn hình |

`screenid` hỗ trợ `clone_voice` và `design_voice`.

Ví dụ lấy limit:

```http
GET /api/voices/numberLimit?username=demo&screenid=clone_voice
Authorization: Bearer <access_token>
```

## PostgreSQL VPS

PostgreSQL phải listen trên IP mạng, cho phép IP máy chạy backend trong
`pg_hba.conf`, và firewall/security group phải mở cổng `5432` chỉ cho IP nguồn
cần thiết. Không mở PostgreSQL cho toàn bộ Internet.

## Test

Test dùng SQLite in-memory, không tác động PostgreSQL:

```bash
pytest
```
