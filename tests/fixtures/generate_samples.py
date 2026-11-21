"""Synthetic test PDF fixture generator for OmniPDF2MD.

Creates 5 standardized PDF test files adhering to strict Vietnamese typography
and diverse structural layout scenarios.
"""

from io import BytesIO
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/times.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
]


def get_unicode_font_path() -> Path:
    """Find an available TrueType font that supports Vietnamese Unicode diacritics."""
    for font_path in FONT_CANDIDATES:
        if font_path.is_file():
            return font_path
    raise FileNotFoundError(
        "No suitable Unicode TrueType font found. Arial or DejaVuSans is required."
    )


def generate_clean_vn(output_path: Path, font_path: Path) -> Path:
    """Generate a clean digital Vietnamese PDF with headers, lists, and paragraphs."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    page.insert_font(fontname="ArialVN", fontfile=str(font_path))

    # Title
    page.insert_text(
        fitz.Point(50, 60),
        "BÁO CÁO KỸ THUẬT DỰ ÁN OMNIPDF2MD",
        fontname="ArialVN",
        fontsize=16,
        color=(0.1, 0.2, 0.5),
    )

    # Subtitle / Section
    page.insert_text(
        fitz.Point(50, 95),
        "1. Giới thiệu tổng quan và mục tiêu kiến trúc",
        fontname="ArialVN",
        fontsize=13,
        color=(0.2, 0.2, 0.2),
    )

    # Paragraph with full Vietnamese diacritics
    body_text_1 = (
        "OmniPDF2MD là giải pháp chuyển đổi PDF sang Markdown chạy 100% cục bộ (local-first). "
        "Hệ thống giải quyết triệt để bài toán vỡ font tiếng Việt, mất cấu trúc bảng biểu, "
        "và xử lý linh hoạt tài liệu hỗn hợp số hóa lẫn bản quét scan chất lượng thấp.\n"
        "Kiểm thử đầy đủ các nguyên âm tiếng Việt có dấu: "
        "a á à ả ã ạ ă ắ ằ ẳ ẵ ặ â ấn ầ ẩ ẫ ậ "
        "e é è ẻ ẽ ẹ ê ế ề ể ễ ệ "
        "i í ì ỉ ĩ ị "
        "o ó ò ỏ õ ọ ô ố ồ ổ ỗ ộ ơ ớ ờ ở ỡ ợ "
        "u ú ù ủ ũ ụ ư ứ ừ sử ữ ự "
        "y ý ỳ ỷ ỹ ỵ."
    )
    rect_body_1 = fitz.Rect(50, 115, 545, 230)
    page.insert_textbox(
        rect_body_1,
        body_text_1,
        fontname="ArialVN",
        fontsize=10.5,
        color=(0.1, 0.1, 0.1),
    )

    # Section 2: Bullet list
    page.insert_text(
        fitz.Point(50, 260),
        "2. Các trụ cột thiết kế chính",
        fontname="ArialVN",
        fontsize=13,
        color=(0.2, 0.2, 0.2),
    )

    bullets = [
        "• Định tuyến thông minh theo từng trang (Per-Page Routing): Không áp đặt một engine cho toàn bộ file.",
        "• Khử lặp tiêu đề đầu trang và chân trang (Header/Footer Deduplication) chính xác trên 60%.",
        "• Bảo vệ tài nguyên bộ nhớ (Anti-OOM): Xử lý phân lô (batch chunking) an toàn trên mọi thiết bị.",
        "• Chuẩn hóa công thức toán học sang định dạng chuẩn LaTeX ($inline$ và $$block$$).",
    ]

    y_pos = 285
    for bullet in bullets:
        rect_bullet = fitz.Rect(50, y_pos, 545, y_pos + 35)
        page.insert_textbox(
            rect_bullet,
            bullet,
            fontname="ArialVN",
            fontsize=10,
            color=(0.15, 0.15, 0.15),
        )
        y_pos += 30

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    return output_path


def generate_table_multicol(output_path: Path, font_path: Path) -> Path:
    """Generate a multi-column and bordered table PDF layout."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="ArialVN", fontfile=str(font_path))

    # Header
    page.insert_text(
        fitz.Point(50, 60),
        "TÀI LIỆU CẤU TRÚC: ĐA CỘT VÀ BẢNG BIỂU DỮ LIỆU",
        fontname="ArialVN",
        fontsize=15,
        color=(0.1, 0.3, 0.4),
    )

    # Column 1 (Left: x=50 to 285)
    col1_text = (
        "CỘT TRÁI — KIẾN TRÚC ROUTER\n\n"
        "Inspector phân tích từng trang dựa trên mật độ văn bản số, "
        "tỷ lệ vùng ảnh quét và các đặc trưng hình học vector. "
        "Nếu trang có cấu trúc cột phức tạp, bộ điều phối sẽ gán nhãn "
        "COMPLEX_LAYOUT để chuyển tiếp sang Tier 2 (Docling TableFormer)."
    )
    page.insert_textbox(
        fitz.Rect(50, 90, 285, 230),
        col1_text,
        fontname="ArialVN",
        fontsize=9.5,
        color=(0.1, 0.1, 0.1),
    )

    # Column 2 (Right: x=310 to 545)
    col2_text = (
        "CỘT PHẢI — CÔNG THỨC VÀ BẢNG\n\n"
        "Đối với các bảng không viền hoặc đa cột lồng ghép, "
        "công nghệ phân tích bố cục sâu giúp tái tạo lại bảng "
        "thành bảng Markdown GFM hoàn chỉnh mà không làm xáo trộn "
        "thứ tự đọc của các dòng văn bản."
    )
    page.insert_textbox(
        fitz.Rect(310, 90, 545, 230),
        col2_text,
        fontname="ArialVN",
        fontsize=9.5,
        color=(0.1, 0.1, 0.1),
    )

    # Draw separator line between columns
    page.draw_line(fitz.Point(297, 95), fitz.Point(297, 220), color=(0.8, 0.8, 0.8), width=1)

    # Table Title
    page.insert_text(
        fitz.Point(50, 260),
        "Bảng 1: Bảng so sánh các tầng xử lý (Conversion Tiers)",
        fontname="ArialVN",
        fontsize=12,
        color=(0.2, 0.2, 0.2),
    )

    # Draw Table
    # Table rect: x=50 to 545, y=280 to 440
    # Columns: STT (40px: 50-90), Thành phần (140px: 90-230), Động cơ (135px: 230-365), Hiệu năng (180px: 365-545)
    cols = [50, 90, 230, 365, 545]
    row_height = 32
    y_start = 280

    rows_data = [
        ["STT", "Thành phần", "Động cơ xử lý", "Mục tiêu hiệu năng"],
        ["01", "Trang văn bản thuần", "PyMuPDF4LLM", "< 100ms / trang (CPU)"],
        ["02", "Bảng biểu phức tạp", "Docling TableFormer", "Chính xác cấu trúc > 95%"],
        ["03", "Trang scan / ảnh mờ", "Docling OCR (RapidOCR)", "Nhận diện tiếng Việt chuẩn"],
        ["04", "Trang lỗi font nặng", "Local VLM (Ollama)", "Tái tạo hoàn toàn bằng AI"],
    ]

    for r_idx, row in enumerate(rows_data):
        y_curr = y_start + r_idx * row_height
        # Header background
        if r_idx == 0:
            page.draw_rect(
                fitz.Rect(cols[0], y_curr, cols[-1], y_curr + row_height),
                color=(0.3, 0.4, 0.6),
                fill=(0.9, 0.93, 0.98),
            )
        else:
            page.draw_rect(
                fitz.Rect(cols[0], y_curr, cols[-1], y_curr + row_height),
                color=(0.7, 0.7, 0.7),
            )

        for c_idx, cell_text in enumerate(row):
            # Vertical cell border
            page.draw_line(
                fitz.Point(cols[c_idx], y_curr),
                fitz.Point(cols[c_idx], y_curr + row_height),
                color=(0.7, 0.7, 0.7),
            )
            # Cell text
            cell_rect = fitz.Rect(
                cols[c_idx] + 5,
                y_curr + 4,
                cols[c_idx + 1] - 5,
                y_curr + row_height - 2,
            )
            font_size = 9.5 if r_idx == 0 else 9.0
            page.insert_textbox(
                cell_rect,
                cell_text,
                fontname="ArialVN",
                fontsize=font_size,
                color=(0, 0, 0) if r_idx > 0 else (0.1, 0.2, 0.4),
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    return output_path


def generate_scanned_sim(output_path: Path, font_path: Path) -> Path:
    """Generate a simulated scanned page: rendered image only, ZERO text layer."""
    # Create an image using Pillow (simulate 200 DPI A4: 1654 x 2338)
    img_w, img_h = 1654, 2338
    image = Image.new("RGB", (img_w, img_h), color=(248, 247, 243))  # slightly aged paper color
    draw = ImageDraw.Draw(image)

    font_large: ImageFont.ImageFont | ImageFont.FreeTypeFont
    font_med: ImageFont.ImageFont | ImageFont.FreeTypeFont
    try:
        font_large = ImageFont.truetype(str(font_path), 52)
        font_med = ImageFont.truetype(str(font_path), 36)
    except Exception:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()

    # Draw simulated scanned receipt/document
    draw.text((150, 160), "ỦY BAN NHÂN DÂN THÀNH PHỐ", fill=(30, 30, 30), font=font_large)
    draw.text((150, 240), "SỞ KHOA HỌC VÀ CÔNG NGHỆ", fill=(40, 40, 40), font=font_med)
    draw.line([(150, 300), (900, 300)], fill=(80, 80, 80), width=3)

    content_lines = [
        "VĂN BẢN QUÉT SCAN LƯU TRỮ LỊCH SỬ NĂM 2015",
        "Số hồ sơ: 458/QĐ-SKHCN-CNTT",
        "",
        "Trang tài liệu này được tạo ra từ bản scan tài liệu giấy.",
        "Hoàn toàn không có tầng văn bản số (Text Layer) trong cấu trúc file PDF.",
        "Hệ thống bắt buộc phải sử dụng công nghệ OCR hoặc Vision LLM",
        "để nhận diện và trích xuất ký tự tiếng Việt có dấu.",
        "",
        "Danh mục các thiết bị kiểm định kỹ thuật số:",
        "1. Máy phân tích quang phổ chuẩn phòng thí nghiệm.",
        "2. Thiết bị đo kiểm thông số mạng cục bộ băng thông cao.",
        "3. Hệ thống lưu trữ dữ liệu an toàn tiêu chuẩn quốc gia.",
    ]

    y_text = 360
    for line in content_lines:
        draw.text((150, y_text), line, fill=(50, 50, 50), font=font_med)
        y_text += 70

    # Save image buffer
    img_buf = BytesIO()
    image.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    # Create PDF and insert only the image (NO text layer inserted)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(0, 0, 595, 842), stream=img_bytes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    return output_path


def generate_mixed(output_path: Path, font_path: Path) -> Path:
    """Generate a 4-page mixed document: digital, table, scan, and image illustration."""
    doc = fitz.open()

    # Page 1: Digital text
    p1 = doc.new_page(width=595, height=842)
    p1.insert_font(fontname="ArialVN", fontfile=str(font_path))
    p1.insert_text(
        fitz.Point(50, 80),
        "TÀI LIỆU HỖN HỢP — TRANG 1: VĂN BẢN SỐ (DIGITAL)",
        fontname="ArialVN",
        fontsize=14,
        color=(0.1, 0.2, 0.5),
    )
    p1.insert_textbox(
        fitz.Rect(50, 110, 545, 300),
        "Trang này chứa nội dung văn bản kỹ thuật số chuẩn, "
        "được xuất trực tiếp từ bộ soạn thảo. Router cần nhận diện là DIGITAL_CLEAN "
        "và gửi tới Tier 1 (Fast PyMuPDF) để xử lý trong thời gian nhanh nhất.",
        fontname="ArialVN",
        fontsize=11,
        color=(0.1, 0.1, 0.1),
    )

    # Page 2: Table & Multi-column
    p2 = doc.new_page(width=595, height=842)
    p2.insert_font(fontname="ArialVN", fontfile=str(font_path))
    p2.insert_text(
        fitz.Point(50, 80),
        "TÀI LIỆU HỖN HỢP — TRANG 2: CẤU TRÚC PHỨC TẠP",
        fontname="ArialVN",
        fontsize=14,
        color=(0.1, 0.2, 0.5),
    )
    p2.insert_textbox(
        fitz.Rect(50, 110, 280, 250),
        "Cột 1: Thông số quy chuẩn thiết kế phần mềm mã nguồn mở...",
        fontname="ArialVN",
        fontsize=10,
        color=(0.15, 0.15, 0.15),
    )
    p2.insert_textbox(
        fitz.Rect(300, 110, 545, 250),
        "Cột 2: Quy trình tích hợp liên tục và kiểm thử tự động...",
        fontname="ArialVN",
        fontsize=10,
        color=(0.15, 0.15, 0.15),
    )
    # Draw simple table
    p2.draw_rect(fitz.Rect(50, 270, 545, 340), color=(0.4, 0.4, 0.4), fill=(0.95, 0.95, 0.95))
    p2.insert_text(
        fitz.Point(60, 305),
        "Chỉ số: A=100, B=250, Tổng cộng=350 đơn vị",
        fontname="ArialVN",
        fontsize=10,
        color=(0.1, 0.1, 0.1),
    )

    # Page 3: Pure Scanned Raster image
    p3 = doc.new_page(width=595, height=842)
    img_scan = Image.new("RGB", (1000, 1400), color=(245, 245, 240))
    draw_sc = ImageDraw.Draw(img_scan)
    draw_sc.text((80, 100), "BẢN SCAN ĐÍNH KÈM PHỤ LỤC", fill=(40, 40, 40))
    draw_sc.text((80, 160), "Nội dung hoàn toàn nằm trong ảnh raster.", fill=(60, 60, 60))
    buf_scan = BytesIO()
    img_scan.save(buf_scan, format="PNG")
    p3.insert_image(fitz.Rect(0, 0, 595, 842), stream=buf_scan.getvalue())

    # Page 4: Digital text with an illustration image
    p4 = doc.new_page(width=595, height=842)
    p4.insert_font(fontname="ArialVN", fontfile=str(font_path))
    p4.insert_text(
        fitz.Point(50, 80),
        "TÀI LIỆU HỖN HỢP — TRANG 4: HÌNH ẢNH MINH HỌA",
        fontname="ArialVN",
        fontsize=14,
        color=(0.1, 0.2, 0.5),
    )
    p4.insert_textbox(
        fitz.Rect(50, 110, 545, 180),
        "Dưới đây là hình ảnh biểu đồ minh họa kiến trúc đường ống dữ liệu (pipeline). "
        "Bộ trích xuất cần lưu hình ảnh này vào thư mục assets/.",
        fontname="ArialVN",
        fontsize=10.5,
        color=(0.1, 0.1, 0.1),
    )

    # Create an illustration graphic
    chart_img = Image.new("RGB", (600, 350), color=(230, 240, 255))
    chart_draw = ImageDraw.Draw(chart_img)
    chart_draw.rectangle([(20, 20), (580, 330)], outline=(50, 100, 200), width=3)
    chart_draw.rectangle([(60, 80), (200, 270)], fill=(70, 130, 220))
    chart_draw.rectangle([(240, 140), (380, 270)], fill=(90, 170, 120))
    chart_draw.rectangle([(420, 50), (540, 270)], fill=(220, 120, 80))
    chart_draw.text((70, 290), "PyMuPDF", fill=(20, 20, 20))
    chart_draw.text((250, 290), "Docling", fill=(20, 20, 20))
    chart_draw.text((430, 290), "Local VLM", fill=(20, 20, 20))
    chart_buf = BytesIO()
    chart_img.save(chart_buf, format="PNG")
    p4.insert_image(fitz.Rect(100, 200, 495, 430), stream=chart_buf.getvalue())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    return output_path


def generate_encrypted(output_path: Path, font_path: Path, password: str = "secret123") -> Path:
    """Generate an encrypted PDF requiring password to open."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="ArialVN", fontfile=str(font_path))
    page.insert_text(
        fitz.Point(50, 80),
        "TÀI LIỆU BẢO MẬT — ENCRYPTED PDF",
        fontname="ArialVN",
        fontsize=15,
        color=(0.6, 0.1, 0.1),
    )
    page.insert_textbox(
        fitz.Rect(50, 110, 545, 250),
        "Tài liệu này được bảo vệ bằng mật mã AES-256. "
        "Mật khẩu kiểm thử mặc định là: secret123. "
        "Nếu người dùng không cung cấp mật khẩu hoặc nhập sai, "
        "hệ thống phải trả về lỗi EncryptedPDFError một cách rõ ràng.",
        fontname="ArialVN",
        fontsize=11,
        color=(0.1, 0.1, 0.1),
    )

    perm = int(
        fitz.PDF_PERM_ACCESSIBILITY
        | fitz.PDF_PERM_PRINT
        | fitz.PDF_PERM_COPY
        | fitz.PDF_PERM_ANNOTATE
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(
        str(output_path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner123",
        user_pw=password,
        permissions=perm,
    )
    doc.close()
    return output_path


def generate_all_samples(output_dir: Path | None = None) -> list[Path]:
    """Generate all 5 synthetic sample PDFs in the designated fixtures directory."""
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent

    output_dir.mkdir(parents=True, exist_ok=True)
    font_path = get_unicode_font_path()
    print(f"[OmniPDF Fixtures] Using Unicode font: {font_path}")

    files = [
        generate_clean_vn(output_dir / "clean_vn.pdf", font_path),
        generate_table_multicol(output_dir / "table_multicol.pdf", font_path),
        generate_scanned_sim(output_dir / "scanned_sim.pdf", font_path),
        generate_mixed(output_dir / "mixed.pdf", font_path),
        generate_encrypted(output_dir / "encrypted.pdf", font_path, password="secret123"),
    ]

    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f" -> Generated: {f.name} ({size_kb:.1f} KB)")

    return files


if __name__ == "__main__":
    generate_all_samples()
