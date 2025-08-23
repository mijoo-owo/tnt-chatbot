# DÀN Ý BÁO CÁO: RAG CHATBOT

## PHẦN 1: GIỚI THIỆU (1-2 trang)

### 1.1 Phát biểu bài toán
- Nhu cầu truy vấn thông tin từ nhiều tài liệu/website khác nhau
- Hạn chế của việc tìm kiếm thủ công trong khối lượng dữ liệu lớn
- Yêu cầu hệ thống chatbot thông minh có thể "đọc hiểu" và trả lời câu hỏi dựa trên nội dung cụ thể

### 1.2 Tổng quan về các công nghệ giải quyết

#### LLM thuần túy (GPT, Gemini)
- **Ưu điểm**: Khả năng sinh ngôn ngữ mạnh mẽ
- **Nhược điểm**: Hallucination, thiếu kiến thức cụ thể, không cập nhật

#### Fine-tuning
- **Ưu điểm**: Tùy chỉnh sâu
- **Nhược điểm**: Chi phí cao, cần dữ liệu lớn, khó cập nhật

#### RAG (Retrieval Augmented Generation)
- **Ưu điểm**: Kết hợp tìm kiếm + sinh text, cập nhật dễ dàng, chi phí thấp
- **Nhược điểm**: Phụ thuộc chất lượng retrieval

### 1.3 Lý do lựa chọn RAG
- Tính thực tiễn và khả năng mở rộng
- Độ chính xác cao với dữ liệu cụ thể
- Khả năng truy xuất nguồn gốc thông tin

---

## PHẦN 2: CÔNG VIỆC TRIỂN KHAI (Phần chính)

### 2.1 Kiến trúc RAG và so sánh với LLM thuần túy
Trình bày nguyên lý hoạt động của LLM thuần và các hạn chế như hiện tượng hallucination, thiếu kiến thức cụ thể, không cập nhật thời gian thực. Giới thiệu cách RAG khắc phục các vấn đề này thông qua quy trình Retrieve → Augment → Generate, giúp kết hợp khả năng tìm kiếm dữ liệu cụ thể và sinh câu trả lời tự nhiên.

### 2.2 Các thành phần chính của hệ thống
Mô tả từng khối chức năng và vai trò trong kiến trúc RAG:
- **Xử lý tài liệu (Document Processing)**: Tiền xử lý nội dung từ nhiều nguồn và định dạng.
- **Cơ sở dữ liệu vector (Vector Database)**: Lưu trữ embedding và hỗ trợ truy vấn theo độ tương đồng.
- **Cơ chế truy xuất (Retrieval Mechanism)**: Xác định và trích xuất các đoạn văn bản liên quan nhất.
- **Bộ sinh câu trả lời (Generation)**: Sử dụng LLM để tạo phản hồi dựa trên ngữ cảnh đã truy xuất.

### 2.3 Xử lý dữ liệu từ nhiều nguồn
- **Tài liệu PDF**: Phân biệt PDF text-based và PDF scan; tích hợp PaddleOCR cho tiếng Việt; áp dụng thuật toán lọc văn bản nhiễu.
- **Định dạng khác**: Word (python-docx), Excel (openpyxl, xlrd), tệp văn bản (xử lý encoding).
- **Dữ liệu web**: Sử dụng BeautifulSoup để trích xuất nội dung, loại bỏ thành phần không liên quan (navigation, quảng cáo) và áp dụng chiến lược crawling cùng miền.

[//]: # (### 2.4 Lưu trữ và tìm kiếm ngữ nghĩa)

[//]: # (- **Lựa chọn ChromaDB**: So sánh với Pinecone, Weaviate; ưu điểm về lưu trữ bền vững và cập nhật gia tăng.)

[//]: # (- **Embedding và truy vấn**: Sử dụng OpenAI text-embedding-3-large, so sánh với sentence-transformers, áp dụng cosine similarity để tìm kiếm văn bản liên quan.)

[//]: # ()
[//]: # (### 2.5 Xử lý văn bản trước khi lưu trữ)

[//]: # (- **Chiến lược chia đoạn &#40;Text Chunking&#41;**: Tối ưu kích thước đoạn &#40;8000 ký tự&#41;, xử lý chồng lấn &#40;800 ký tự&#41;, so sánh chia đoạn theo kích thước cố định và chia đoạn ngữ nghĩa.)

[//]: # (- **Loại bỏ trùng lặp và kiểm soát chất lượng**: Sử dụng hash để phát hiện trùng lặp, lọc nội dung kém chất lượng, quản lý metadata phục vụ truy vấn.)

### 2.4 Xây dựng và quản lý cơ sở dữ liệu vector

#### 2.4.1 Tiền xử lý và phân đoạn văn bản
- Chiến lược text chunking (kích thước, overlap)
- So sánh fixed-size vs semantic chunking
- Xử lý ranh giới câu/đoạn

#### 2.4.2 Vector embedding và dedupe
- Lựa chọn mô hình embedding (OpenAI vs alternatives)
- Chuyển đổi text thành vector
- Loại bỏ trùng lặp bằng hash

#### 2.4.3 Lưu trữ và indexing
- Lựa chọn ChromaDB (so sánh Pinecone, Weaviate)
- Cấu trúc metadata
- Cập nhật gia tăng

#### 2.4.4 Tìm kiếm và truy xuất
- Cosine similarity
- Optimization techniques (HNSW, IVF)
- Ranking và filtering

### 2.6 Tích hợp với mô hình ngôn ngữ
- **Chọn mô hình**: GPT-4o-mini, lý do lựa chọn, quản lý cửa sổ ngữ cảnh.
- **Kỹ thuật prompt**: Thiết kế prompt cho RAG để tối ưu tính chính xác và ngữ cảnh trả lời.
- **Streaming**: Sinh câu trả lời theo thời gian thực để cải thiện trải nghiệm người dùng, kết hợp xử lý lỗi.

### 2.7 Quản lý phiên làm việc và bộ nhớ
- **Quản lý trạng thái**: Sử dụng Streamlit Session State để lưu lịch sử trò chuyện, theo dõi tài liệu đã tải.
- **Quản lý ngữ cảnh**: Giới hạn 10 lượt trao đổi, tối ưu xử lý tài liệu nhằm giảm tải bộ nhớ và chi phí.

---

## PHẦN 3: KẾT QUẢ ĐẠT ĐƯỢC

### 3.1 Giao diện và trải nghiệm người dùng
Mô tả giao diện Streamlit, khả năng tải tệp, nhập URL để crawling, và giao diện trò chuyện. Nhấn mạnh yếu tố thân thiện và dễ thao tác.

### 3.2 Các tính năng chính
- **Xử lý tài liệu đa định dạng**: Hỗ trợ PDF, Word, Excel, TXT; OCR tiếng Việt với độ chính xác > X%; tốc độ xử lý trung bình Y giây/tệp.
- **Tích hợp nội dung web**: Khả năng crawling URL, lọc nhiễu, giới hạn phạm vi miền.
- **Hỏi đáp thông minh**: Đánh giá độ chính xác phản hồi, khả năng dẫn nguồn, hỗ trợ đa ngôn ngữ với trọng tâm tiếng Việt.

### 3.3 Đánh giá hiệu năng và hạn chế
- **Tốc độ xử lý**: Benchmark so với baseline (ví dụ xử lý thủ công hoặc hệ thống tương tự).
- **Sử dụng bộ nhớ và chi phí API**: Thống kê mức tiêu thụ, chi phí trung bình trên mỗi truy vấn.
- **Khả năng mở rộng**: Đánh giá khi số lượng tài liệu và truy vấn tăng.
- **Hạn chế hiện tại**: Các trường hợp thất bại, nội dung OCR sai, giới hạn ngữ cảnh.

### 3.4 Hướng cải thiện
Ưu tiên cải tiến theo mức ảnh hưởng:
1. Cải thiện chiến lược chunking để giảm trùng lặp và nâng cao độ chính xác retrieval.
2. Bổ sung hỗ trợ đa phương tiện (hình ảnh, bảng biểu).
3. Tăng cường xử lý tiếng Việt chuyên sâu (tokenization, từ ghép).
4. Tích hợp mô hình LLM nội bộ để giảm chi phí và bảo mật dữ liệu.

---

## PHỤ LỤC (nếu cần)
- Code structure overview
- Configuration examples
- API usage statistics
- Technical specifications
