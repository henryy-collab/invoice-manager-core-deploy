from typing import Optional


DEFAULT_DOCUMENT_TYPE = "google_ads"


class Document:
    def __init__(self, document_type: str = DEFAULT_DOCUMENT_TYPE, **fields: Optional[str]):
        super().__setattr__("document_type", document_type)
        super().__setattr__("fields", dict(fields))

    def to_dict(self) -> dict[str, Optional[str]]:
        return dict(self.fields)

    def to_full_dict(self) -> dict:
        return {
            "document_type": self.document_type,
            "fields": self.to_dict(),
        }

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.fields.get(key, default)

    def __getattr__(self, name: str) -> Optional[str]:
        if name in ("document_type", "fields"):
            return super().__getattribute__(name)
        if name.startswith("_"):
            raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
        return self.fields.get(name)

    def __setattr__(self, name: str, value) -> None:
        if name == "document_type":
            super().__setattr__(name, value)
        elif name == "fields":
            super().__setattr__(name, value)
        else:
            self.fields[name] = value

    def __getitem__(self, key: str) -> Optional[str]:
        return self.fields[key]

    def __setitem__(self, key: str, value: Optional[str]) -> None:
        self.fields[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.fields

    def __repr__(self) -> str:
        cls_name = type(self).__name__
        fields_repr = ", ".join(f"{k}={v!r}" for k, v in self.fields.items())
        return f"{cls_name}(document_type={self.document_type!r}, {fields_repr})"


Invoice = Document
