import base64
import io

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


class ProfileDocumentError(Exception):
    pass


class ProfileDocumentService:
    def extract_text(self, file_name: str, file_data_base64: str) -> str:
        raw_bytes = self._decode_base64(file_data_base64)
        lowered_name = (file_name or "resume.pdf").lower()
        if lowered_name.endswith(".pdf"):
            return self._extract_pdf_text(raw_bytes)
        try:
            return raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProfileDocumentError("暂时只支持 PDF 或 UTF-8 文本文件。") from exc

    def _decode_base64(self, file_data_base64: str) -> bytes:
        data = file_data_base64 or ""
        if "," in data:
            data = data.split(",", 1)[1]
        try:
            return base64.b64decode(data)
        except Exception as exc:
            raise ProfileDocumentError("无法解析上传文件内容。") from exc

    def _extract_pdf_text(self, raw_bytes: bytes) -> str:
        if PdfReader is None:
            raise ProfileDocumentError("当前环境未安装 pypdf，暂时无法解析 PDF，请先部署最新 requirements 或直接粘贴文本。")
        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
        except Exception as exc:
            raise ProfileDocumentError("PDF 文件读取失败，请确认文件未损坏。") from exc

        parts = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                parts.append(text.strip())
        result = "\n".join(parts).strip()
        if not result:
            raise ProfileDocumentError("PDF 中没有解析到可用文本，请尝试复制文本粘贴。")
        return result


def get_profile_document_service() -> ProfileDocumentService:
    return ProfileDocumentService()
