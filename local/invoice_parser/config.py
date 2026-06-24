from pydantic import BaseModel, Field, field_validator, model_validator

import re


class RegexPattern(BaseModel):
    regex: str
    group: int = 1
    flags: list[str] = Field(default_factory=list)

    @field_validator("regex")
    @classmethod
    def regex_must_compile(cls, v: str) -> str:
        try:
            re.compile(v)
        except re.error as exc:
            raise ValueError(f"Invalid regex: {exc}")
        return v


class AccountParserConfig(BaseModel):
    patterns: list[RegexPattern] = Field(default_factory=list)
    unknown_values: list[str] = Field(default_factory=list)
    fallback: str = "UNKNOWN"


class NumberParserConfig(BaseModel):
    patterns: list[RegexPattern] = Field(default_factory=list)
    require_digit: bool = True
    fallback_to_filename: bool = True
    filename_pattern: str = r"^\d+$"

    @field_validator("filename_pattern")
    @classmethod
    def pattern_must_compile(cls, v: str) -> str:
        try:
            re.compile(v)
        except re.error as exc:
            raise ValueError(f"Invalid regex: {exc}")
        return v


class DetailsBlockConfig(BaseModel):
    enabled: bool = True
    header: str = "Details"
    dot_separator_regex: str = r"^\.{5,}$"
    label_regex: str = r"Invoice\s*number|Invoice\s*date|Payment\s*terms|Billing\s*ID|Account\s*ID|Tax\s*Invoice"
    max_label_length: int = 80


class DateParserConfig(BaseModel):
    parse_formats: list[str] = Field(default_factory=list)
    nearby_line_window: int = 2
    details_block: DetailsBlockConfig = Field(default_factory=DetailsBlockConfig)


class CurrencyParserConfig(BaseModel):
    primary_regex: str = r"Total\s*amount\s*due\s*in\s*([A-Z]{3})"
    symbol_map: dict[str, str] = Field(default_factory=dict)

    @field_validator("primary_regex")
    @classmethod
    def regex_must_compile(cls, v: str) -> str:
        try:
            re.compile(v)
        except re.error as exc:
            raise ValueError(f"Invalid regex: {exc}")
        return v


class TotalParserConfig(BaseModel):
    primary_regex: str = r"Total\s*amount\s*due(?:\s*in\s*[A-Z]{3})?[:\s]*([A-Z$€£¥]*)\s*([\d,]+\.\d{2})"
    fallback_regex: str = r"(?:HK\$|US\$|\$|€|£|¥)\s*([\d,]+\.\d{2})"
    pick_max: bool = True

    @field_validator("primary_regex", "fallback_regex")
    @classmethod
    def regex_must_compile(cls, v: str) -> str:
        try:
            re.compile(v)
        except re.error as exc:
            raise ValueError(f"Invalid regex: {exc}")
        return v


class ParsersConfig(BaseModel):
    account: AccountParserConfig = Field(default_factory=lambda: AccountParserConfig(
        patterns=[
            RegexPattern(regex=r"^Account:\s*(.+?)(?=\s*\[|\s*$)", flags=["IGNORECASE", "MULTILINE"]),
            RegexPattern(regex=r"Account\s*ID[:\s]+([\d\-]+)", flags=["IGNORECASE"]),
        ],
        unknown_values=["-", "—", "--", "N/A", "n/a"],
    ))
    number: NumberParserConfig = Field(default_factory=lambda: NumberParserConfig(
        patterns=[
            RegexPattern(regex=r"Invoice\s*number[:\s]+([A-Z0-9\-]+)", flags=["IGNORECASE"]),
        ],
    ))
    date: DateParserConfig = Field(default_factory=lambda: DateParserConfig(
        parse_formats=["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"],
    ))
    currency: CurrencyParserConfig = Field(default_factory=lambda: CurrencyParserConfig(
        primary_regex=r"Total\s*amount\s*due\s*in\s*([A-Z]{3})",
        symbol_map={"HK$": "HKD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"},
    ))
    total: TotalParserConfig = Field(default_factory=lambda: TotalParserConfig(
        primary_regex=r"Total\s*amount\s*due(?:\s*in\s*[A-Z]{3})?[:\s]*([A-Z$€£¥]*)\s*([\d,]+\.\d{2})",
        fallback_regex=r"(?:HK\$|US\$|\$|€|£|¥)\s*([\d,]+\.\d{2})",
    ))


class FeatureFlags(BaseModel):
    archive: bool = True
    skip_already_processed: bool = True
    manual_review_for_missing: list[str] = Field(default_factory=lambda: ["account", "date"])
    number_fallback_to_filename: bool = True
    deduplicate_within_run: bool = True
    dry_run: bool = False


class ArchiveConfig(BaseModel):
    mode: str = "copy_original"


class PlaceholderConfig(BaseModel):
    sanitize: bool = False
    fallback: str = "unknown"


class FilenameConfig(BaseModel):
    placeholders: dict[str, PlaceholderConfig] = Field(default_factory=lambda: {
        "account": PlaceholderConfig(sanitize=True, fallback="UNKNOWN"),
        "number": PlaceholderConfig(sanitize=True, fallback="unknown"),
        "date": PlaceholderConfig(fallback="unknown-date"),
        "total": PlaceholderConfig(fallback="unknown"),
        "currency": PlaceholderConfig(fallback="unknown"),
    })
    manual_review_prefix: str = "000_"
    already_processed_patterns: list[str] = Field(default_factory=lambda: [
        r"_Invoice_\d{8}\.pdf$",
        r"_unparsed\.pdf$",
        r"^000_",
    ])
    collision_suffix: str = "_{counter}"

    @model_validator(mode="after")
    def ensure_default_placeholders(self):
        defaults = {
            "account": PlaceholderConfig(sanitize=True, fallback="UNKNOWN"),
            "number": PlaceholderConfig(sanitize=True, fallback="unknown"),
            "date": PlaceholderConfig(fallback="unknown-date"),
            "total": PlaceholderConfig(fallback="unknown"),
            "currency": PlaceholderConfig(fallback="unknown"),
        }
        for key, default in defaults.items():
            self.placeholders.setdefault(key, default)
        return self


class RcloneConfig(BaseModel):
    enabled: bool = False
    remote: str = "mydrive-shared"
    source_drive_folder: str | None = None
    destination_drive_folder: str | None = None
    destination_subfolder_template: str | None = None
    archive_drive_folder: str | None = None


class ReportsConfig(BaseModel):
    enabled: bool = True
    filename_template: str = "parsed_fields_{timestamp}.csv"


class GoogleSheetsConfig(BaseModel):
    enabled: bool = False
    spreadsheet_url: str | None = None
    service_account_file: str | None = None
    tab_name_template: str = "%b %Y"
    date_format: str = "%d/%m/%Y"
    skip_existing_by: str = "number"
    raw_sheet_suffix: str = " [Auto]"
    protect_raw_sheets: bool = True

    @field_validator("spreadsheet_url")
    @classmethod
    def spreadsheet_url_must_contain_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if "/d/" not in v:
            raise ValueError("spreadsheet_url must be a valid Google Sheets URL")
        return v


class AppConfig(BaseModel):
    source_folder: str
    filename_template: str = "{account}_{number}_Invoice_{date}.pdf"
    date_format: str = "%Y%m%d"
    archive_folder: str = "archive"
    log_file: str = "parse_and_rename.log"
    timezone: str = "Asia/Hong_Kong"
    input_folder: str | None = None
    output_folder: str | None = None
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    archive: ArchiveConfig = Field(default_factory=ArchiveConfig)
    parsers: ParsersConfig = Field(default_factory=ParsersConfig)
    filename: FilenameConfig = Field(default_factory=FilenameConfig)
    rclone: RcloneConfig = Field(default_factory=RcloneConfig)
    reports: ReportsConfig = Field(default_factory=ReportsConfig)
    google_sheets: GoogleSheetsConfig = Field(default_factory=GoogleSheetsConfig)

    @model_validator(mode="after")
    def resolve_working_folders(self):
        if self.input_folder is None:
            self.input_folder = self.source_folder
        if self.output_folder is None:
            self.output_folder = self.source_folder
        return self
