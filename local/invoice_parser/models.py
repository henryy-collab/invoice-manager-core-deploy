from dataclasses import dataclass
from typing import Optional


@dataclass
class Invoice:
    account: Optional[str] = None
    number: Optional[str] = None
    date: Optional[str] = None
    total: Optional[str] = None
    currency: Optional[str] = None

    def to_dict(self) -> dict[str, Optional[str]]:
        return {
            "account": self.account,
            "number": self.number,
            "date": self.date,
            "total": self.total,
            "currency": self.currency,
        }
