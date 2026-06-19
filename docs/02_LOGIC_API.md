# 02. Logic API và vận hành

Tài liệu này mô tả các mục chính từ 5 đến 8:

5. Logic Auth API.
6. Logic Voice API.
7. CLI quản trị tài khoản.
8. Mã HTTP và lưu ý vận hành API.

Tài liệu liên quan:

- [01_TONG_QUAN_VA_KIEN_TRUC.md](./01_TONG_QUAN_VA_KIEN_TRUC.md)
- [03_CAU_TRUC_DATABASE.md](./03_CAU_TRUC_DATABASE.md)

## 5. Logic Auth API

### 5.1 Đăng ký

```http
POST /api/auth/register
```

Route: `register()` trong `app/api/routes/auth.py`.

Service: `register_user()` trong `app/services/auth_service.py`.

Luồng:

1. `RegisterRequest` kiểm tra username, password và email.
2. `normalize_username()` trim và chuyển username thành lowercase.
3. Email được trim và chuyển lowercase.
4. Kiểm tra username hoặc email đã tồn tại.
5. Nếu trùng, trả HTTP `409`.
6. Password được hash bằng bcrypt.
7. Tạo user với:

   ```text
   clone_voice = false
   design_voice = true
   gen_voice = true
   is_active = false
   is_default = false
   ```

8. Tạo một bản ghi `voice_clones`.
9. Tạo một bản ghi `voice_designs`.
10. Commit cả ba bản ghi.
11. Trả HTTP `200`, không trả password hash.

User mới chưa thể login cho đến khi được đặt `is_active=true`.

### 5.2 Đăng nhập

```http
POST /api/auth/login
```

Route: `login()`.

Service: `authenticate_user()`.

Luồng:

1. Chuẩn hóa username.
2. Tìm user theo username.
3. So sánh password với bcrypt hash.
4. User không tồn tại hoặc password sai:

   ```http
   HTTP 401
   {"detail": "Invalid username or password"}
   ```

5. Password đúng nhưng user chưa active:

   ```http
   HTTP 403
   {"detail": "Account is not active"}
   ```

6. Thành công: tạo JWT và trả:

```json
{
  "access_token": "<jwt-token>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "demo",
    "clone_voice": false,
    "design_voice": true,
    "gen_voice": true
  }
}
```

### 5.3 Đổi mật khẩu

```http
POST /api/auth/changepassword
Authorization: Bearer <token>
```

Route: `change_user_password()`.

Service: `change_password()`.

Luồng:

1. `CurrentUser` xác thực JWT và trạng thái active.
2. So sánh `current_password` với hash hiện tại.
3. Sai password hiện tại: trả HTTP `400`.
4. Băm password mới.
5. Cập nhật `users.password_hash` và commit.

### 5.4 Kiểm tra quyền màn hình

```http
POST /api/auth/acceptFuntion
Authorization: Bearer <token>
```

Route: `accept_function()`.

Service: `has_screen_access()`.

Quy tắc:

- User thường chỉ kiểm tra được chính mình.
- User `is_default=true` có thể kiểm tra user khác.
- Screen hỗ trợ:
  - `clone_voice` hoặc `voice_clone`.
  - `design_voice` hoặc `voice_design`.
  - `gen_voice` hoặc `voice_gen`.
- `allowed=true` khi user active và quyền tương ứng là `true`.
- Screen không hỗ trợ trả HTTP `400`.

### 5.5 Thông tin user hiện tại

```http
GET /api/auth/me
Authorization: Bearer <token>
```

Hàm `me()` trả user đã xác thực, gồm email, quyền, trạng thái và timestamps.
Response không chứa password hash.

## 6. Logic Voice API

### 6.1 Quy tắc chung

- Mọi endpoint dùng `CurrentVoiceUser`.
- Mọi truy vấn voice luôn có `Voice.user_id == current_user.id`.
- User khác nhận `VOICE_NOT_FOUND`, không được biết voice có tồn tại.
- `voice_name_normalized = casefold(trimmed_name)`.
- Unique constraint `(user_id, voice_name_normalized)` chống race condition.
- Cùng tên được phép ở hai tài khoản khác nhau.

Response chung:

```json
{
  "id": "voice-uuid",
  "userId": "user-public-uuid",
  "voiceName": "Giọng mẫu 01",
  "generationMethod": "voice-clone",
  "createdAt": "2026-06-15T10:00:00Z",
  "updatedAt": "2026-06-15T10:00:00Z"
}
```

### 6.2 Tạo Clone Voice

```http
POST /api/voices/clone
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

Fields:

```text
voiceName
audioFile
```

Logic `create_clone_voice()`:

1. Kiểm tra `clone_voice=true`.
2. Khóa dòng `voice_clones` bằng `SELECT ... FOR UPDATE`.
3. Đếm số Clone Voice và so sánh `voice_clones.number_limit`.
4. Chuẩn hóa và kiểm tra tên.
5. Chỉ nhận WAV, MP3, M4A và MIME tương ứng.
6. Ghi file theo chunk; vượt `MAX_AUDIO_FILE_SIZE_MB` thì xóa file tạm.
7. Tên lưu nội bộ là UUID, không dùng tên upload.
8. Lưu metadata và `storage_key` trong bảng `voices`.
9. Nếu DB commit lỗi trùng tên, rollback và xóa file vừa lưu.

### 6.3 Tạo Design Voice

```http
POST /api/voices/design
Authorization: Bearer <token>
Content-Type: application/json
```

Logic `create_design_voice()`:

1. Kiểm tra `design_voice=true`.
2. Kiểm tra quota Design Voice.
3. Kiểm tra tên không trùng.
4. `validate_design_options()` kiểm tra language, gender, age, pitch, style.
5. English bắt buộc `englishAccent`, không nhận `chineseDialect`.
6. Chinese bắt buộc `chineseDialect`, không nhận `englishAccent`.
7. Lưu metadata, không tạo file audio.

Tập enum hiện khai báo trong `app/services/voice_service.py`. Khi OmniVoice
thay đổi option, cập nhật các constant `OMNIVOICE_*`.

### 6.4 Danh sách và phân trang

```http
GET /api/voices?page=1&pageSize=10&type=voice-clone&search=giọng
Authorization: Bearer <token>
```

- `page >= 1`.
- `pageSize` từ 1 đến 100.
- `type`: `voice-clone` hoặc `voice-design`.
- `search`: tìm không phân biệt hoa/thường bằng `ILIKE`.
- Chỉ trả metadata, không trả binary audio.
- Sắp xếp mới nhất trước.

### 6.5 Chi tiết và đổi tên

```http
GET /api/voices/{voiceId}
PATCH /api/voices/{voiceId}
Authorization: Bearer <token>
```

PATCH body:

```json
{"voiceName": "Tên mới"}
```

`get_owned_voice()` đảm bảo voice thuộc JWT user. Rename kiểm tra lại unique
name cả ở service và database.

### 6.6 Xóa voice

```http
DELETE /api/voices/{voiceId}
Authorization: Bearer <token>
```

- Xóa metadata trong PostgreSQL.
- Nếu là Clone Voice có `storage_key`, xóa luôn file audio.
- Thành công trả HTTP `204`.

### 6.7 Stream audio

```http
GET /api/voices/{voiceId}/audio
Authorization: Bearer <token>
```

- Chỉ chủ sở hữu được tải.
- Chỉ áp dụng cho `voice-clone`.
- Resolve path bên trong `UPLOAD_DIR`.
- Dùng `FileResponse` để stream với MIME và tên file gốc.

### 6.8 Quota

```http
GET /api/voices/limit
GET /api/voices/limit?type=voice-clone
Authorization: Bearer <token>
```

Response:

```json
{"current": 3, "limit": 10, "remaining": 7}
```

Không truyền `type` thì trả tổng Clone + Design. Khi tạo voice, server luôn
gọi `ensure_voice_quota()`, không tin trạng thái do FE gửi. Dòng limit được
khóa trong transaction để các request đồng thời không vượt quota.

### 6.9 Error format

```json
{
  "code": "VOICE_NAME_EXISTS",
  "message": "Tên giọng nói đã tồn tại.",
  "details": null
}
```

| Code | HTTP |
| --- | --- |
| `VOICE_NAME_EXISTS` | 409 |
| `VOICE_LIMIT_REACHED` | 403 |
| `VOICE_NOT_FOUND` | 404 |
| `INVALID_AUDIO_FILE` | 422 |
| `INVALID_DESIGN_OPTIONS` | 422 |
| `FILE_TOO_LARGE` | 413 |
| `UNAUTHORIZED` | 401 |
| `FORBIDDEN` | 403 |

## 7. CLI quản trị tài khoản

File: `scripts/create_user.py`.

CLI chỉ cập nhật user đã đăng ký:

```bash
python -m scripts.create_user demo \
  --activate \
  --clone-voice \
  --design-voice \
  --gen-voice \
  --clone-limit 10 \
  --design-limit 5
```

Hàm `main()`:

- Tìm user theo username lowercase.
- Có thể cập nhật password.
- Có thể kích hoạt user.
- Có thể bật quyền Clone, Design và Gen.
- Có thể đổi Clone/Design limit.
- Commit thay đổi trong một transaction.

CLI hiện chưa có option tắt quyền.

## 8. Mã HTTP và lưu ý vận hành

### Mã HTTP

| Mã | Trường hợp |
| --- | --- |
| `200` | Nghiệp vụ thành công |
| `400` | Input nghiệp vụ sai |
| `401` | Thiếu/sai JWT hoặc username/password sai |
| `403` | User chưa active hoặc không có quyền |
| `409` | Username/email đã tồn tại |
| `422` | Pydantic validation thất bại |
| `503` | Database lỗi hoặc schema chưa migration |

### Health check

```http
GET /health
```

Chỉ xác nhận FastAPI process đang chạy.

```http
GET /health/ready
```

Kiểm tra cả kết nối database và sự tồn tại của bảng `users`.

### Lưu ý

- Phải chạy `alembic upgrade head` trước khi phục vụ API.
- `JWT_SECRET_KEY` production phải mạnh và không commit.
- Hệ thống chưa có refresh token hoặc token revoke list.
- Audio local cần backup. Production nên thay storage adapter bằng S3/MinIO.
- Metadata nằm trong DB; không lưu binary audio trong PostgreSQL.
- API đã kiểm tra quota bằng số bản ghi hiện tại, không giảm một counter riêng.
- Endpoint gọi engine OmniVoice thực tế chưa được triển khai.

### Audit log mỗi lần gọi API

Mọi request, gồm cả request lỗi, tạo một JSON event:

```json
{
  "timestamp": "2026-06-19T10:00:00+00:00",
  "requestId": "uuid",
  "userId": "public-user-uuid",
  "method": "POST",
  "path": "/api/voices/clone",
  "statusCode": 200,
  "durationMs": 35.42,
  "clientIp": "127.0.0.1",
  "userAgent": "Angular/Electron"
}
```

Phân file:

- JWT hợp lệ hoặc login/register thành công: file của username.
- Chưa đăng nhập, token sai, login thất bại: file anonymous.
- Tên file được sanitize và thêm hash để hai username không ghi nhầm file.

Tra cứu theo request ID:

```bash
grep -R 'request-id-can-tim' logs/audit/
```

Rotation mặc định:

- Mỗi file tối đa 10 MB.
- Giữ 5 file backup.
- Có thể thay đổi qua `.env`.

Audit file phù hợp cho kiểm tra vận hành trên một instance. Khi chạy nhiều
worker/VPS, nên chuyển log stdout sang hệ thống tập trung như Loki/ELK hoặc dùng
audit sink chuyên dụng để tránh phân tán log.
