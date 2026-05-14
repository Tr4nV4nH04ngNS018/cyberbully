# 🛡️ CyberGuard — Hệ thống Phát hiện Cyberbullying bằng AI

> **Phiên bản:** 2.0.1-ai  
> **Tác giả:** Võ Tá Dũng & Phạm Hoàng Hiếu — VKU 25NS  
> **Công nghệ:** Python Flask + Google Gemini / OpenAI GPT-4o

---

## 📋 Mục lục

- [Giới thiệu](#-giới-thiệu)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Hướng dẫn cài đặt](#-hướng-dẫn-cài-đặt)
- [Cấu hình API Key](#-cấu-hình-api-key)
- [Chạy ứng dụng](#-chạy-ứng-dụng)
- [API Endpoints](#-api-endpoints)
- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Giải thích mã nguồn](#-giải-thích-mã-nguồn)
- [Xử lý sự cố](#-xử-lý-sự-cố)
- [Bảo mật](#-bảo-mật)

---

## 🎯 Giới thiệu

CyberGuard là hệ thống phát hiện cyberbullying (bắt nạt mạng) sử dụng trí tuệ nhân tạo. Thay vì chỉ dựa vào danh sách từ khóa cố định, hệ thống tận dụng các mô hình ngôn ngữ lớn (LLM) để **phân tích ngữ cảnh** của văn bản tiếng Việt, cho kết quả chính xác hơn.

### Tính năng chính

| Tính năng | Mô tả |
|-----------|-------|
| 🧠 Phân tích AI | Sử dụng Gemini hoặc GPT-4o để hiểu ngữ cảnh |
| 📊 4 mức phân loại | `clean` → `warning` → `danger` → `critical` |
| 🔍 Chi tiết vi phạm | Liệt kê cụ thể từng nội dung vi phạm |
| 📈 Thống kê realtime | Theo dõi số lượng phân tích và vi phạm |
| 🌐 Giao diện web | UI hiện đại, responsive, dark theme |
| 📝 Logging | Ghi log toàn bộ hoạt động ra file |

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────┐
│                  Trình duyệt                     │
│              (index.html + JS)                   │
└──────────────┬──────────────────┬────────────────┘
               │ POST /analyze    │ GET /stats
               ▼                  ▼
┌─────────────────────────────────────────────────┐
│              Flask Web Server                    │
│                (app.py)                          │
│  ┌───────────────────────────────────────────┐  │
│  │            AIEngine Class                  │  │
│  │  ┌─────────────┐  ┌────────────────────┐  │  │
│  │  │ _call_gemini │  │  _call_openai      │  │  │
│  │  └──────┬───────┘  └────────┬───────────┘  │  │
│  └─────────┼───────────────────┼──────────────┘  │
└────────────┼───────────────────┼─────────────────┘
             ▼                   ▼
     Google Gemini API    OpenAI GPT-4o API
```

### Luồng xử lý

1. Người dùng nhập văn bản → Nhấn **"Phân tích ngay"**
2. Frontend gửi `POST /analyze` với body `{ "text": "..." }`
3. Backend gọi AI API (Gemini hoặc OpenAI) với system prompt chuyên biệt
4. AI trả về kết quả JSON gồm: status, severity, violations, suggestion
5. Backend parse JSON → ghi log → trả về cho frontend
6. Frontend render kết quả với màu sắc và animation tương ứng

---

## 💻 Yêu cầu hệ thống

| Yêu cầu | Phiên bản tối thiểu |
|----------|---------------------|
| Python | 3.8 trở lên |
| pip | Đi kèm Python |
| Trình duyệt | Chrome, Firefox, Edge (bản mới) |
| Kết nối Internet | Cần thiết (để gọi AI API) |

---

## 🚀 Hướng dẫn cài đặt

### Bước 1: Kiểm tra Python

Mở **Command Prompt** hoặc **PowerShell**, chạy:

```bash
python --version
```

Nếu chưa có Python, tải tại: https://www.python.org/downloads/

> ⚠️ Khi cài Python, **nhớ tick ✅ "Add Python to PATH"**

### Bước 2: Mở thư mục dự án

```bash
cd C:\Users\ACER\Downloads\Doancs1
```

### Bước 3: (Khuyến nghị) Tạo môi trường ảo

```bash
python -m venv venv
venv\Scripts\activate
```

> Khi thấy `(venv)` ở đầu dòng lệnh là đã kích hoạt thành công.

### Bước 4: Cài đặt thư viện

```bash
pip install -r requirements.txt
```

Danh sách thư viện cần thiết:
- `flask` — Web framework
- `python-dotenv` — Đọc biến môi trường từ file `.env`

---

## 🔑 Cấu hình API Key

### Lấy API Key miễn phí từ Google Gemini

1. Truy cập: https://aistudio.google.com/apikey
2. Đăng nhập bằng tài khoản Google
3. Nhấn **"Create API Key"**
4. Copy API key vừa tạo

### Cập nhật file `.env`

Mở file `.env` trong thư mục dự án và sửa:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=paste_api_key_moi_cua_ban_vao_day
OPENAI_API_KEY=
```

### Sử dụng OpenAI (tùy chọn)

Nếu muốn dùng OpenAI GPT-4o thay vì Gemini:

1. Truy cập: https://platform.openai.com/api-keys
2. Tạo API key mới
3. Sửa `.env`:

```env
AI_PROVIDER=openai
GEMINI_API_KEY=
OPENAI_API_KEY=sk-paste_api_key_openai_vao_day
```

> ⚠️ **Lưu ý:** OpenAI API là dịch vụ trả phí. Gemini có gói miễn phí.

---

## ▶️ Chạy ứng dụng

### Khởi động server

```bash
python app.py
```

Kết quả mong đợi:

```
============================================================
  Cyberbullying Detector v2.0.1 — AI-Powered
  Tác giả: Võ Tá Dũng & Phạm Hoàng Hiếu — VKU 25NS
  AI Provider : GEMINI
  API Key set : YES
  Server      : http://127.0.0.1:5000
============================================================
```

### Mở trình duyệt

Truy cập: **http://127.0.0.1:5000**

### Sử dụng

1. Nhập hoặc dán văn bản cần kiểm tra vào ô nhập liệu
2. Hoặc nhấn các nút mẫu: **✅ Bình thường**, **⚠️ Xúc phạm**, **🚨 Nghiêm trọng**
3. Nhấn **"Phân tích ngay"** (hoặc `Ctrl + Enter`)
4. Xem kết quả phân tích bên dưới

### Dừng server

Nhấn `Ctrl + C` trong cửa sổ terminal.

---

## 📡 API Endpoints

### `GET /` — Trang chính
Trả về giao diện web (index.html).

### `POST /analyze` — Phân tích văn bản

**Request:**
```json
{
  "text": "Nội dung cần phân tích"
}
```

**Response (thành công):**
```json
{
  "status": "danger",
  "severity": "medium",
  "confidence": 0.85,
  "violations": [
    {
      "type": "keyword",
      "content": "nội dung vi phạm",
      "severity": "medium",
      "label": "Xúc phạm nhân phẩm"
    }
  ],
  "violation_count": 1,
  "suggestion": "Nội dung có dấu hiệu xúc phạm, nên xem xét chỉnh sửa.",
  "explanation": "Văn bản chứa từ ngữ miệt thị nhắm vào cá nhân...",
  "timestamp": "2026-05-13 17:30:00",
  "provider": "gemini"
}
```

**Giới hạn:** Tối đa 5000 ký tự mỗi lần phân tích.

### `GET /stats` — Thống kê

```json
{
  "statistics": {
    "total": 10,
    "violations": 3,
    "clean": 7
  },
  "provider": "gemini",
  "version": "2.0.1-ai"
}
```

### `GET /health` — Kiểm tra trạng thái

```json
{
  "status": "ok",
  "provider": "gemini",
  "api_key_set": true,
  "timestamp": "2026-05-13T17:30:00"
}
```

---

## 📁 Cấu trúc thư mục

```
Doancs1/
├── app.py                  # Backend chính (Flask + AIEngine)
├── .env                    # Biến môi trường (API keys) — KHÔNG đẩy lên Git
├── .gitignore              # Danh sách file bỏ qua khi dùng Git
├── requirements.txt        # Danh sách thư viện Python cần cài
├── cyberbullying_log.txt   # Log hoạt động (tự tạo khi chạy)
├── README.md               # File hướng dẫn này
└── templates/
    └── index.html          # Giao diện web (HTML + CSS + JS)
```

---

## 🔬 Giải thích mã nguồn

### `app.py` — Backend

| Thành phần | Dòng | Chức năng |
|------------|------|-----------|
| `AIEngine` class | 28-164 | Lớp chính xử lý AI |
| `SYSTEM_PROMPT` | 29-57 | Prompt hướng dẫn AI phân tích cyberbullying |
| `__init__()` | 62-75 | Khởi tạo, đọc API key từ `.env` |
| `_parse_json()` | 78-82 | Parse JSON từ phản hồi AI (xử lý cả markdown) |
| `_call_openai()` | 84-98 | Gọi OpenAI GPT-4o API |
| `_call_gemini()` | 100-114 | Gọi Google Gemini API |
| `analyze()` | 116-151 | Hàm chính: gọi AI → parse → ghi log → trả kết quả |
| `_fallback_error()` | 153-164 | Trả response lỗi chuẩn hóa |
| Route `/analyze` | 175-190 | Endpoint nhận text và trả kết quả phân tích |
| Route `/stats` | 193-199 | Endpoint trả thống kê |
| Route `/health` | 202-209 | Endpoint kiểm tra sức khỏe server |

### `templates/index.html` — Frontend

| Thành phần | Chức năng |
|------------|-----------|
| CSS Variables (`:root`) | Hệ thống màu sắc dark theme |
| Grid background | Nền lưới động bằng CSS |
| `analyze()` function | Gửi request tới backend và hiển thị kết quả |
| `renderResult()` function | Render kết quả AI với status bar, badges, violations |
| `esc()` function | Escape HTML để chống tấn công XSS |
| `updateStats()` function | Cập nhật thống kê realtime |

### Quy trình phân loại của AI

| Mức | Status | Severity | Ý nghĩa |
|-----|--------|----------|----------|
| 🟢 | `clean` | `clean` | Nội dung bình thường, an toàn |
| 🟡 | `warning` | `low` | Có thể nhạy cảm tùy ngữ cảnh |
| 🟠 | `danger` | `medium` | Có dấu hiệu xúc phạm, miệt thị |
| 🔴 | `critical` | `high` | Chửi thề nặng, đe dọa bạo lực |

---

## 🔧 Xử lý sự cố

### ❌ Lỗi "API Key not found"

**Nguyên nhân:** API key trong `.env` không hợp lệ hoặc đã hết hạn.

**Cách fix:**
1. Vào https://aistudio.google.com/apikey
2. Tạo API key mới
3. Mở file `.env`, thay key cũ bằng key mới
4. Khởi động lại server (`Ctrl+C` rồi `python app.py`)

### ❌ Lỗi "API Key set: NO"

**Nguyên nhân:** File `.env` thiếu hoặc sai tên biến.

**Cách fix:** Kiểm tra file `.env` có đúng format:
```env
AI_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
```

### ❌ Lỗi "ModuleNotFoundError: No module named 'flask'"

**Cách fix:**
```bash
pip install -r requirements.txt
```

### ❌ Lỗi "Address already in use" (port 5000 đã bị dùng)

**Cách fix:** Đổi port trong `app.py` dòng cuối:
```python
app.run(debug=True, port=5001)  # Đổi thành 5001
```

### ❌ AI trả về "dữ liệu không hợp lệ"

**Nguyên nhân:** AI đôi khi trả JSON bị lỗi format.

**Cách fix:** Thử phân tích lại. Nếu lỗi liên tục, kiểm tra log trong `cyberbullying_log.txt`.

---

## 🔒 Bảo mật

> ⚠️ **QUAN TRỌNG:** Không bao giờ chia sẻ file `.env` hoặc đẩy lên GitHub!

- File `.gitignore` đã được cấu hình để bỏ qua `.env`
- API key nên được tạo riêng cho mỗi môi trường
- Frontend đã có hàm `esc()` chống tấn công XSS
- Server chỉ nên chạy ở chế độ `debug=True` khi phát triển

### Khi triển khai production

```python
# Thay đổi dòng cuối app.py:
app.run(debug=False, host="0.0.0.0", port=5000)
```

---

## 📄 License

Đồ án môn học — VKU 2025. Sử dụng cho mục đích học tập.

---

*Được tạo bởi Võ Tá Dũng & Phạm Hoàng Hiếu — VKU 25NS*
