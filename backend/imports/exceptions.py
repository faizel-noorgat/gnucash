from __future__ import annotations


class ImportError(Exception):
    pass


class CsvParseError(ImportError):
    pass


class ColumnMappingError(ImportError):
    pass
