import base64
import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO, Union, Optional


class Content(ABC):
    @abstractmethod
    def length(self) -> int:
        pass

    def base64length(self) -> int:
        return (int(4 * self.length() / 3) + 3) & ~3

    @abstractmethod
    def stream(self) -> IO:
        pass

    @abstractmethod
    def value(self) -> bytes:
        pass

    def base64value(self) -> str:
        return base64.b64encode(self.value()).decode()


class BytesContent(Content):
    def __init__(self, buf: Union[bytes, io.BytesIO]):
        self.buf = buf if isinstance(buf, io.BytesIO) else io.BytesIO(buf)

    def length(self) -> int:
        return self.buf.getbuffer().nbytes

    def stream(self) -> IO:
        return self.buf

    def value(self) -> bytes:
        return self.buf.getvalue()


class AbstractStreamContent(Content, ABC):
    def __init__(self):
        self.cache = None

    def value(self) -> bytes:
        if self.cache:
            return self.cache
        else:
            with self.stream() as f:
                self.cache = f.read()
            return self.cache


class StreamContent(AbstractStreamContent):
    def __init__(self, input_stream: IO, content_length: int):
        super().__init__()
        self.input_stream = input_stream
        self.content_length = content_length

    def length(self) -> int:
        return self.content_length

    def stream(self) -> IO:
        return self.input_stream


class FileContent(AbstractStreamContent):
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

    def length(self) -> int:
        return Path(self.filename).stat().st_size

    def stream(self) -> IO:
        return open(self.filename, "rb")


# See https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
CONTENT_TYPE_MAP_REVERSED = {
    ".aac": "audio/aac",  # AAC audio
    ".abw": "application/x-abiword",  # AbiWord document
    ".arc": "application/x-freearc",  # Archive document (multiple files embedded)
    ".avi": "video/x-msvideo",  # AVI: Audio Video Interleave
    ".azw": "application/vnd.amazon.ebook",  # Amazon Kindle eBook format	application/vnd.amazon.ebook
    ".bin": "application/octet-stream",  # Any kind of binary data
    ".bmp": "image/bmp",  # Windows OS/2 Bitmap Graphics
    ".bz": "application/x-bzip",  # BZip archive
    ".bz2": "application/x-bzip2",  # BZip2 archive
    ".csh": "application/x-csh",  # C-Shell script
    ".css": "text/css",  # Cascading Style Sheets (CSS)
    ".csv": "text/csv",  # Comma-separated values (CSV)
    ".doc": "application/msword",  # Microsoft Word	application/msword
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # Microsoft Word (OpenXML)
    ".eot": "application/vnd.ms-fontobject",  # MS Embedded OpenType fonts
    ".epub": "application/epub+zip",  # Electronic publication (EPUB)
    ".gz": "application/gzip",  # GZip Compressed Archive
    ".gif": "image/gif",  # Graphics Interchange Format (GIF)
    ".htm": "text/html",
    ".html": "text/html",  # HyperText Markup Language (HTML)
    ".ico": "image/vnd.microsoft.icon",  # Icon format
    ".ics": "text/calendar",  # iCalendar format
    ".jar": "application/java-archive",  # Java Archive (JAR)
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",  # JPEG images
    ".js": "text/javascript",  # JavaScript
    ".json": "application/json",  # JSON format
    ".jsonld": "application/ld+json",  # JSON-LD format
    ".mid": "audio/midi",  #
    ".midi": "audio/midi",  # Musical Instrument Digital Interface (MIDI) audio/x-midi
    ".mjs": "text/javascript",  # JavaScript module
    ".mp3": "audio/mpeg",  # MP3 audio
    ".mpeg": "video/mpeg",  # MPEG Video
    ".mpkg": "application/vnd.apple.installer+xml",  # Apple Installer Package
    ".odp": "application/vnd.oasis.opendocument.presentation",  # OpenDocument presentation document
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",  # OpenDocument spreadsheet document
    ".odt": "application/vnd.oasis.opendocument.text",  # OpenDocument text document
    ".oga": "audio/ogg",  # OGG audio
    ".ogv": "video/ogg",  # OGG video
    ".ogx": "application/ogg",  # OGG
    ".opus": "audio/opus",  # Opus audio
    ".otf": "font/otf",  # OpenType font
    ".png": "image/png",  # Portable Network Graphics
    ".pdf": "application/pdf",  # Adobe Portable Document Format (PDF)
    ".php": "application/x-httpd-php",  # Hypertext Preprocessor (Personal Home Page)
    ".ppt": "application/vnd.ms-powerpoint",  # Microsoft PowerPoint
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", # Microsoft PowerPoint
    ".rar": "application/vnd.rar",  # RAR archive
    ".rtf": "application/rtf",  # Rich Text Format (RTF)
    ".sh": "application/x-sh",  # Bourne shell script
    ".svg": "image/svg+xml",  # Scalable Vector Graphics (SVG)
    ".swf": "application/x-shockwave-flash",  # Small web format (SWF) or Adobe Flash document
    ".tar": "application/x-tar",  # Tape Archive (TAR)
    ".tif": "image/tiff",  #
    ".tiff": "image/tiff",  # Tagged Image File Format (TIFF)
    ".TS": "video/mp2t",  # MPEG transport stream
    ".ttf": "font/ttf",  # TrueType Font
    ".txt": "text/plain",  # Text, (generally ASCII or ISO 8859-n)
    ".vsd": "application/vnd.visio",  # Microsoft Visio
    ".wav": "audio/wav",  # Waveform Audio Format
    ".weba": "audio/webm",  # WEBM audio
    ".webm": "video/webm",  # WEBM video
    ".webp": "image/webp",  # WEBP image
    ".woff": "font/woff",  # Web Open Font Format (WOFF)
    ".woff2": "font/woff2",  # Web Open Font Format (WOFF)
    ".xhtml": "application/xhtml+xml",  # XHTML
    ".xls": "application/vnd.ms-excel",  # Microsoft Excel
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Microsoft Excel (OpenXML)
    ".xml": "text/xml",  # XML application/xml if not readable from casual users (RFC 3023, section 3)
    ".xul": "application/vnd.mozilla.xul+xml",  # XUL
    ".zip": "application/zip",  # ZIP archive
    ".3gp": "video/3gpp",  # 3GPP audio/video container, audio/3gpp if it doesn't contain video
    ".3g2": "video/3gpp2",  # 3GPP2 audio/video container audio/3gpp2 if it doesn't contain video
    ".7z": "application/x-7z-compressed"
}


class MediaType(object):
    def __init__(self, content_type: str, application: Optional[str] = None):
        self.content_type = content_type
        self.application = application
