"""Document Loader: normalizes raw source text before parsing.

Deterministic, offline, source-type-aware text cleanup only -- no
network access, no file-format parsing libraries, no OCR, no video
download. The caller is responsible for having already turned a PDF,
video, or image into plain text (per `PROJECT_VISION.md`'s "No External
APIs" convention); this class's job is only to strip source-specific
noise (code comments, YouTube timestamps, OCR whitespace artifacts) so
every downstream stage sees comparable, clean text regardless of source.
"""

import re

from app.ai_extraction.models import DocumentContent, SourceType

_YOUTUBE_TIMESTAMP_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")
_PINE_MQL_LINE_COMMENT_RE = re.compile(r"//.*$", re.MULTILINE)
_C_STYLE_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_EASYLANGUAGE_BLOCK_COMMENT_RE = re.compile(r"\{.*?\}", re.DOTALL)
# Deliberately excludes '_' -- markdown emphasis can use underscores
# (`_word_`), but underscores are also extremely common inside plain
# identifiers extracted strategies actually use ("fast_ma", "slow_ma").
# Stripping them would corrupt "fast_ma" into "fastma", which can then
# false-positive-match an unrelated registered name as a substring (e.g.
# "slowma" containing "wma" -> a spurious WMA indicator mention).
_MARKDOWN_EMPHASIS_RE = re.compile(r"[*`]{1,3}")
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_MULTI_BLANK_LINE_RE = re.compile(r"\n{3,}")


class DocumentLoader:
    """Normalizes raw document text according to its declared `SourceType`."""

    def load(self, raw_text: str, source_type: SourceType) -> DocumentContent:
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

        if source_type == SourceType.YOUTUBE_TRANSCRIPT:
            text = _YOUTUBE_TIMESTAMP_RE.sub("", text)
        elif source_type in (SourceType.PINE_SCRIPT, SourceType.MQL4, SourceType.MQL5):
            text = _C_STYLE_BLOCK_COMMENT_RE.sub(" ", text)
            text = _PINE_MQL_LINE_COMMENT_RE.sub("", text)
        elif source_type == SourceType.EASYLANGUAGE:
            text = _EASYLANGUAGE_BLOCK_COMMENT_RE.sub(" ", text)
        elif source_type == SourceType.MARKDOWN:
            # Headings are kept (SectionDetector uses '#' markers); only
            # inline emphasis markers are stripped so keyword matching
            # isn't tripped up by "**entry**" vs "entry".
            text = _MARKDOWN_EMPHASIS_RE.sub("", text)
        elif source_type == SourceType.OCR_TEXT:
            text = _MULTI_SPACE_RE.sub(" ", text)

        text = _MULTI_BLANK_LINE_RE.sub("\n\n", text).strip()
        if not text:
            # `DocumentContent.normalized_text` strips whitespace too (the
            # base model's `str_strip_whitespace=True`), so a bare space
            # wouldn't survive -- use a visible placeholder token instead.
            # `ExtractionValidator` catches genuinely empty/too-short input
            # before this stage ever runs; this only guards direct,
            # non-pipeline use of the loader.
            text = "(empty)"

        return DocumentContent(source_type=source_type, normalized_text=text, line_count=text.count("\n") + 1)
