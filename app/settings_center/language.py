"""Language selection (Phase 18.8). Confirmed via the reuse audit: no
i18n/localization system exists anywhere in this project (every
"language" hit repo-wide referred to generated-code language, e.g. EA
Generator's MQL5/Python output, not UI localization). `Language` exists
so the setting can be stored and surfaced in the UI, but selecting
anything other than English has no visible effect today -- honestly
documented, not silently ignored."""

from enum import Enum


class Language(str, Enum):
    ENGLISH = "en"
