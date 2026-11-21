# IMPLEMENTATION PLAN: OmniPDF2MD (Local Universal PDF-to-Markdown App)

## 0. Project Overview & Architectural Philosophy

### Objective
Xây dựng ứng dụng chạy hoàn toàn cục bộ (**100% local-first, offline-capable**) có khả năng chuyển đổi **mọi loại file PDF** (PDF xuất từ văn bản số, PDF scan ảnh, PDF nhiều cột, bảng biểu phức tạp, tài liệu chứa công thức toán học LaTeX, PDF tiếng Việt bị lỗi mã font, PDF có mật khẩu) sang định dạng **Markdown chuẩn sạch** kèm trích xuất hình ảnh và siêu dữ liệu.

### Core Principle: "No Single Engine Fits All"
Không một thư viện đơn lẻ nào xử lý tối ưu mọi loại PDF. Hệ thống áp dụng kiến trúc **Per-Page Smart Router (Định tuyến thông minh theo từng trang)** kết hợp **Strategy Pattern**:
1. **Phân tích từng trang (Pre-flight Inspection):** Đo mật độ văn bản, tỷ lệ ảnh phủ trang, phát hiện bảng/công thức và kiểm tra lỗi bảng mã Unicode/CMap.
2. **Định tuyến đa tầng (Multi-Tier Engine Routing):**
   - **Tier 1 — Fast Engine (`pymupdf4llm`):** Xử lý trang văn bản thuần túy với tốc độ cao (~50–100ms/trang trên CPU).
   - **Tier 2 — Deep Layout & OCR Engine (`docling`):** Xử lý trang scan, bảng biểu phức tạp (TableFormer), bố cục nhiều cột (chạy tốt trên CPU/GPU, giấy phép MIT).
   - **Tier 3 — Local VLM Fallback (Optional via Ollama API):** Dành riêng cho trang cực khó (chữ viết tay, công thức toán phức tạp bị mờ, font tiếng Việt cũ TCVN3/VNI bị hỏng CMap) thông qua mô hình Vision chạy local (ví dụ: `qwen2.5vl` / `qwen3-vl`).
3. **Hậu xử lý thống nhất (Unified Post-Processing):** Ghép trang, khử lặp Header/Footer, nối từ bị ngắt dòng, chuẩn hóa công thức LaTeX (`$...$` / `$$...$$`), lưu ảnh tài nguyên theo đường dẫn tương đối.

### Non-Goals (Scope Boundaries)
- Không phụ thuộc API đám mây (OpenAI/Claude API chỉ là tùy chọn mở rộng về sau, không phải yêu cầu cốt lõi).
- Không xây dựng hệ thống quản lý tài khoản/đăng nhập (ứng dụng cá nhân chạy trên `127.0.0.1`).
- Không biên dịch ứng dụng nặng kiểu Electron ở giai đoạn v1; sử dụng kiến trúc **FastAPI serving React Static Bundle** (mở trực tiếp trên trình duyệt cục bộ bằng 1 lệnh).

---

## 1. Tech Stack & Directory Structure

### Tech Stack
- **Runtime:** Python 3.12+ (quản lý gói bằng `uv` hoặc `venv`), Node.js 20+ (build Frontend).
- **Core PDF Engines:** `pymupdf` (fitz), `pymupdf4llm`, `docling`, `httpx` (gọi Ollama local API khi bật chế độ VLM).
- **Backend API:** `FastAPI`, `Uvicorn`, `Pydantic v2`, `aiosqlite` (lưu lịch sử job & hash cache), Server-Sent Events (`sse-starlette`) để đẩy tiến độ theo thời gian thực.
- **Frontend UI:** `React 19`, `TypeScript`, `Vite`, `TailwindCSS`, `pdfjs-dist` (xem PDF gốc), `react-markdown` + `remark-gfm` + `remark-math` + `rehype-katex` (hiển thị Markdown & Toán trực tiếp).
- **CLI & Packaging:** `Typer` + `Rich` (dùng chung tầng `core/` với Web App).
- **Quality & Testing:** `pytest`, `pytest-asyncio`, `ruff`, `mypy`.

### Target Repository Layout
```text
omnipdf2md/
├── AGENTS.md                     # Quy tắc bắt buộc cho Antigravity Agent
├── PLAN.md                       # File kế hoạch này
├── PROGRESS.md                   # Agent cập nhật trạng thái sau mỗi Phase
├── pyproject.toml                # Cấu hình Python dependencies, ruff, pytest
├── src/
│   └── omnipdf/
│       ├── __init__.py
│       ├── config.py             # Pydantic Settings (paths, threads, Ollama URL, OCR langs)
│       ├── core/
│       │   ├── models.py         # Data contracts: PageProfile, ConversionJob, PageResult
│       │   ├── inspector.py      # Phân loại từng trang PDF + phát hiện lỗi font/scan
│       │   ├── router.py         # Điều phối trang -> Engine phù hợp theo từng batch bộ nhớ
│       │   ├── postprocess.py    # Khử header/footer lặp, chuẩn hóa LaTeX, quản lý assets
│       │   └── engines/
│       │       ├── base.py       # Abstract Base Class: BaseConverterEngine
│       │       ├── fast_pymupdf.py
│       │       ├── deep_docling.py
│       │       └── vlm_ollama.py # Optional Vision LLM local fallback
│       ├── storage/
│       │   ├── db.py             # SQLite lưu lịch sử & SHA-256 deduplication cache
│       │   └── workspace.py      # Quản lý thư mục output, đóng gói ZIP (md + assets)
│       ├── api/
│       │   ├── main.py           # FastAPI app, mount static UI, CORS localhost
│       │   ├── routes.py         # Upload, Start/Cancel Job, Download, Settings
│       │   └── worker.py         # Isolated background worker + SSE progress broadcaster
│       └── cli.py                # Lệnh `omnipdf convert`, `omnipdf serve`, `omnipdf doctor`
├── web/                          # Frontend React + Vite + Tailwind
│   ├── package.json
│   └── src/
│       ├── components/           # Dropzone, JobQueue, SplitPaneViewer, EngineSettings
│       └── hooks/                # useJobProgress (SSE)
└── tests/
    ├── fixtures/                 # Script tự sinh bộ PDF test đa dạng (không commit file nặng)
    ├── unit/
    └── integration/
```

---

## 2. Detailed Technical Specifications

### 2.1. Pre-Flight Page Inspector (`inspector.py`)
Mỗi trang PDF được chấm điểm độc lập thay vì gán nhãn chung cho cả tài liệu (vì nhiều tài liệu kết hợp trang văn bản số và trang scan phụ lục):
- **Kiểm tra mã hóa:** Nếu `doc.is_encrypted`, yêu cầu mật khẩu từ cấu hình job; nếu sai, trả lỗi rõ ràng `EncryptedPDFError` (không crash server).
- **Phân loại trang (`PageType`):**
  1. `DIGITAL_CLEAN`: Tổng số ký tự >= 50, tỷ lệ ảnh bao phủ trang < 35%, không phát hiện cấu trúc bảng/đa cột phức tạp, tỷ lệ ký tự lỗi < 2%. -> **Gửi Tier 1 (Fast)**.
  2. `COMPLEX_LAYOUT`: Có văn bản số nhưng phát hiện >= 2 cột văn bản, nhiều khối vẽ vector (bảng không kẻ viền/biểu đồ), hoặc ký hiệu toán học dày đặc. -> **Gửi Tier 2 (Docling)**.
  3. `SCANNED_IMAGE`: Tổng số ký tự < 50 và diện tích ảnh chiếm > 60% trang. -> **Gửi Tier 2 (Docling OCR)** hoặc **Tier 3 (VLM)** nếu người dùng chọn chế độ High-Accuracy.
  4. `GARBLED_ENCODING`: Có văn bản số nhưng chứa tỷ lệ cao ký tự thay thế (`\ufffd`), ký tự Private Use Area (`U+E000–U+F8FF`), hoặc tổ hợp dấu tiếng Việt lỗi (dấu hiệu font cũ TCVN3/VNI hỏng CMap). -> **Ép chuyển sang OCR/VLM (render trang thành ảnh 300 DPI rồi nhận diện lại)**.

### 2.2. Memory & Process Safety (Anti-OOM Design)
- **Batch Chunking:** Với file lớn (> 30 trang), chia nhỏ thành từng lô `batch_size` (mặc định 15 trang). Xử lý xong từng lô, ghi kết quả tạm xuống đĩa, gọi `gc.collect()` và giải phóng VRAM GPU (nếu dùng PyTorch/CUDA).
- **Process Isolation:** Chạy tiến trình chuyển đổi nặng trong `ProcessPoolExecutor` hoặc subprocess riêng biệt. Nếu file PDF bị hỏng cấu trúc gây Segmentation Fault ở tầng C/C++ (MuPDF/OCR), tiến trình API chính vẫn sống và báo trạng thái `FAILED` cho đúng job đó.
- **UTF-8 Strictness:** Toàn bộ thao tác đọc/ghi file trong Python bắt buộc truyền tường minh `encoding="utf-8"` để tránh lỗi `UnicodeEncodeError` (cp1252) trên Windows.

### 2.3. Post-Processing Standards (`postprocess.py`)
- **Header/Footer Deduplication:** So sánh dòng đầu và dòng cuối của các trang liên tiếp (dùng chuẩn hóa số trang bằng regex `\d+`). Nếu xuất hiện lặp lại ở > 60% số trang, tự động loại bỏ.
- **Asset Management:** Mọi ảnh trích xuất lưu tại `<output_dir>/assets/p{page:04d}_img{idx:02d}.png` và chèn vào Markdown bằng đường dẫn tương đối `![Page 1 Image 1](assets/p0001_img01.png)`.
- **LaTeX Normalization:** Chuyển đồng nhất inline math sang `$...$` và block math sang `$$...$$`.
- **YAML Frontmatter (tùy chọn bật/tắt):**
  ```yaml
  ---
  source_file: "example.pdf"
  sha256: "..."
  total_pages: 42
  engines_used: ["pymupdf4llm", "docling_ocr"]
  converted_at: "2026-11-21T22:00:00+07:00"
  ---
  ```

---

## 3. Phased Execution Roadmap

> **AGENT INSTRUCTION:** Thực hiện tuần tự từng Phase. Sau mỗi Phase, BẮT BUỘC chạy toàn bộ lệnh trong **Verification Gate**, ghi kết quả vào `PROGRESS.md`, và chỉ chuyển Phase tiếp theo khi 100% kiểm thử đạt yêu cầu.

### Phase 0: Workspace Scaffolding & Synthetic Test Suite
- [ ] Khởi tạo `pyproject.toml`, cấu trúc thư mục `src/omnipdf`, `tests/`, cấu hình `ruff` và `mypy`.
- [ ] Tạo file `AGENTS.md` chứa các ràng buộc kỹ thuật (UTF-8, type hints, không dùng đường dẫn cứng).
- [ ] Viết script `tests/fixtures/generate_samples.py` dùng `pymupdf` + `Pillow` tự động tạo bộ PDF kiểm thử chuẩn:
  1. `clean_vn.pdf`: Văn bản tiếng Việt Unicode có tiêu đề H1-H3, danh sách, đoạn văn.
  2. `table_multicol.pdf`: Bố cục 2 cột kèm bảng có đường kẻ.
  3. `scanned_sim.pdf`: Render văn bản tiếng Anh/Việt thành ảnh raster rồi nhúng vào PDF (không có text layer).
  4. `mixed.pdf`: Ghép trang số + trang scan + trang có hình minh họa.
  5. `encrypted.pdf`: PDF khóa bằng mật khẩu `secret123`.
- [ ] **Verification Gate 0:**
  - Chạy `python tests/fixtures/generate_samples.py` tạo đủ 5 file PDF hợp lệ.
  - Chạy `ruff check .` và `pytest` trả exit code `0`.

### Phase 1: Core Architecture, Inspector, Fast Engine & CLI
- [ ] Xây dựng `core/models.py` (Pydantic schemas cho `PageProfile`, `ConversionConfig`, `ConversionResult`).
- [ ] Cài đặt `core/inspector.py` phân loại chính xác 4 loại trang (`DIGITAL_CLEAN`, `COMPLEX_LAYOUT`, `SCANNED_IMAGE`, `GARBLED_ENCODING`) và phát hiện mã hóa.
- [ ] Định nghĩa `core/engines/base.py` và cài đặt `core/engines/fast_pymupdf.py` (hỗ trợ trích xuất ảnh ra `assets/`).
- [ ] Cài đặt `core/postprocess.py` (khử lặp header/footer, chuẩn hóa dòng trống, YAML frontmatter).
- [ ] Xây dựng `cli.py` với lệnh `omnipdf convert <input> -o <output> --mode auto|fast|deep` và `omnipdf doctor` (kiểm tra Python, GPU/CUDA, kết nối Ollama, trạng thái model local).
- [ ] **Verification Gate 1:**
  - Unit tests xác nhận `inspector.py` phân loại đúng 100% các trang trong 5 file fixture.
  - Chạy `omnipdf convert tests/fixtures/clean_vn.pdf -o /tmp/test_out` xuất ra file `.md` đọc đúng tiếng Việt UTF-8 không vỡ dấu.
  - Kiểm thử xử lý `encrypted.pdf` cả trường hợp đúng mật khẩu và sai mật khẩu.

### Phase 2: Deep Layout Engine (Docling), Local VLM Fallback & Smart Router
- [ ] Cài đặt `core/engines/deep_docling.py` tích hợp `docling` với cấu hình:
  - Hỗ trợ bật/tắt OCR theo trang.
  - Hỗ trợ tùy chọn ngôn ngữ OCR (mặc định `["en", "vi"]`).
  - Tự động phát hiện thiết bị (`cuda` / `mps` / `cpu`) và cấu hình số luồng CPU an toàn.
- [ ] Cài đặt `core/engines/vlm_ollama.py`:
  - Render trang PDF sang PNG (DPI tùy chỉnh, mặc định 200 DPI).
  - Gửi yêu cầu tới Ollama local endpoint (`/api/chat`) kèm prompt hệ thống nghiêm ngặt (chỉ xuất Markdown + LaTeX, cấm bình luận thừa).
  - Xử lý timeout và fallback mượt mà nếu Ollama không chạy.
- [ ] Cài đặt `core/router.py`:
  - Nhận kết quả từ `inspector.py`, gom nhóm trang liên tiếp theo engine tương ứng để tối ưu hiệu năng khởi tạo model.
  - Xử lý theo batch (Anti-OOM), xuất callback tiến độ theo từng trang `(current_page, total_pages, engine_used)`.
  - Hợp nhất kết quả theo đúng thứ tự trang gốc và chạy qua `postprocess.py`.
- [ ] **Verification Gate 2:**
  - Chạy `omnipdf convert tests/fixtures/mixed.pdf --mode auto` -> log xác nhận trang văn bản đi qua `fast_pymupdf` và trang scan đi qua `deep_docling`.
  - Chạy test trên `scanned_sim.pdf` trích xuất được đúng nội dung chữ từ ảnh.
  - Mock test cho `vlm_ollama.py` xác nhận xử lý đúng response và lỗi kết nối (`ConnectionRefusedError`).

### Phase 3: Local Backend API, SQLite Storage & Real-time Streaming
- [ ] Cài đặt `storage/db.py` (SQLite) lưu bảng `jobs` (id, filename, sha256, status, mode, progress, output_path, error_message, created_at).
- [ ] Cài đặt cơ chế **Hash Cache**: Nếu file upload có cùng `sha256` và cùng cấu hình chuyển đổi, cho phép trả kết quả tức thì (kèm cờ `force_reconvert` để chạy lại).
- [ ] Xây dựng `api/worker.py` chạy chuyển đổi bất đồng bộ, hỗ trợ hàng đợi tuần tự (tránh chạy 2 model OCR song song gây tràn RAM) và cơ chế hủy job (`Cancel`).
- [ ] Xây dựng `api/routes.py`:
  - `POST /api/jobs`: Upload 1 hoặc nhiều file PDF + cấu hình (mode, password, ocr_langs, use_vlm, extract_images).
  - `GET /api/jobs` & `GET /api/jobs/{id}`: Lấy danh sách và chi tiết job.
  - `GET /api/jobs/{id}/events`: SSE stream cập nhật trạng thái và tiến độ từng trang.
  - `POST /api/jobs/{id}/cancel`: Hủy job đang chạy.
  - `GET /api/jobs/{id}/result`: Trả về nội dung Markdown + danh sách assets + metadata định tuyến từng trang.
  - `GET /api/jobs/{id}/download`: Tải file `.md` (hoặc `.zip` nếu có kèm thư mục `assets/`).
  - `GET /api/system/status`: Kiểm tra phần cứng (CPU/GPU), model đã tải, trạng thái Ollama.
- [ ] **Verification Gate 3:**
  - Integration tests dùng `httpx.AsyncClient` kiểm thử toàn bộ vòng đời job: Upload -> SSE progress -> Lấy kết quả -> Tải ZIP -> Giải nén kiểm tra ảnh và file `.md`.
  - Test kịch bản upload file giả mạo đuôi `.pdf` (file text đổi tên) phải trả HTTP `400 Bad Request` an toàn.

### Phase 4: Local Web Studio UI (React + Vite + Tailwind)
- [ ] Khởi tạo project trong `web/` với Vite + React + TypeScript + TailwindCSS.
- [ ] Xây dựng giao diện tối giản, chuyên nghiệp gồm 4 khu vực chính:
  1. **Header & System Bar:** Trạng thái phần cứng (CPU/GPU badge), trạng thái Ollama, nút mở bảng Cài đặt.
  2. **Upload & Batch Queue Sidebar:** Kéo-thả nhiều PDF, chọn chế độ (`Auto Smart`, `Fast Text`, `Deep OCR/Layout`, `Local VLM`), nhập mật khẩu PDF (nếu cần), thanh tiến độ theo từng trang + nút Cancel.
  3. **Split-Pane Inspector (Trọng tâm):**
     - Bên trái: Trình xem PDF gốc (`pdfjs-dist`) có đồng bộ số trang.
     - Bên phải: Chuyển đổi giữa **Rendered Markdown** (hỗ trợ bảng GFM, code block, công thức KaTeX, ảnh local) và **Raw Markdown Editor** (cho phép sửa nhanh trực tiếp và lưu lại).
     - Hiển thị badge nhỏ ở mỗi trang cho biết Engine nào đã xử lý trang đó.
  4. **Export Toolbar:** Nút Copy Markdown, Download `.md`, Download `.zip` (kèm assets).
- [ ] **Verification Gate 4:**
  - Chạy `npm run build` trong `web/` thành công không có lỗi TypeScript hay warning nghiêm trọng.
  - Khởi chạy FastAPI + UI, dùng trình duyệt kiểm thử thực tế luồng kéo thả `mixed.pdf` -> xem tiến độ -> hiển thị song song PDF và Markdown -> tải file ZIP thành công.

### Phase 5: Unified Launcher, Packaging & Final Hardening
- [ ] Cấu hình FastAPI tự động mount thư mục `web/dist` khi chạy ở chế độ production.
- [ ] Hoàn thiện lệnh `omnipdf serve --port 8765 --open`: khởi động server localhost và tự mở trình duyệt mặc định.
- [ ] Viết script cài đặt 1 chạm (`setup.ps1` cho Windows và `setup.sh` cho Linux/macOS) tạo môi trường ảo, cài dependencies và kiểm tra `omnipdf doctor`.
- [ ] Hoàn thiện `README.md` (hướng dẫn cài đặt, bảng so sánh chế độ, cách cài PyTorch CUDA nếu có GPU NVIDIA, cách bật Ollama VLM).
- [ ] **Verification Gate 5 (Final Acceptance):**
  - Chạy toàn bộ test suite: `pytest --cov=src/omnipdf`.
  - Chạy kiểm tra chất lượng mã: `ruff check .` và `mypy src/`.
  - Kiểm thử khởi chạy sạch từ 1 lệnh `omnipdf serve` trên môi trường mới.

---

## 4. Agent Operational Rules (Tóm tắt đưa vào `AGENTS.md`)

1. **Scope Discipline:** Không tự ý cài thêm thư viện nặng ngoài danh sách trong `PLAN.md` trừ khi có lý do kỹ thuật rõ ràng và được ghi vào `PROGRESS.md`.
2. **Error Escalation:** Nếu gặp lỗi cài đặt hoặc lỗi test, tự chẩn đoán và thử tối đa **3 hướng tiếp cận khác nhau**; nếu vẫn thất bại, dừng lại báo cáo nguyên nhân gốc và đề xuất phương án cho người dùng.
3. **Deterministic Paths:** Luôn sử dụng `pathlib.Path`, tuyệt đối không nối chuỗi đường dẫn bằng `/` hoặc `\` thủ công để đảm bảo tương thích Windows và Linux.
4. **No Silent Failures:** Không dùng `except Exception: pass`. Mọi lỗi trích xuất ở từng trang phải được ghi log kèm số trang và gắn thẻ cảnh báo `<!-- [OmniPDF Warning: Page X failed...] -->` trong file Markdown đầu ra nếu không thể phục hồi.