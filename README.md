# Account Verification Backend

FastAPI backend dùng để kiểm tra tài khoản và mật khẩu do dự án Angular/Electron gửi lên.
Tài khoản được lưu trong SQLite; mật khẩu chỉ được lưu dưới dạng PBKDF2 hash.

## Cài đặt và chạy

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m scripts.create_user admin
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
```

Các biến trong `.env.example` là tài liệu tham khảo. Có thể export chúng trước khi chạy:

```bash
export DATABASE_PATH=data/accounts.sqlite3
export CORS_ORIGINS=http://localhost:4200
```

Mở tài liệu API tại `http://127.0.0.1:8000/docs`.

## API xác thực

```http
POST /api/auth/verify
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

Thành công trả HTTP `200`:

```json
{
  "valid": true,
  "user": {
    "username": "admin"
  }
}
```

Sai tài khoản hoặc mật khẩu trả HTTP `401`.

## Gọi từ Angular

```ts
verify(username: string, password: string) {
  return this.http.post<{ valid: boolean; user: { username: string } }>(
    'http://127.0.0.1:8000/api/auth/verify',
    { username, password }
  );
}
```

Không lưu mật khẩu trong Angular/Electron. Khi deploy qua mạng, đặt API sau HTTPS.

## Test

```bash
pytest
```
