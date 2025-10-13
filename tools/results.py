"""Results processing: decoding BQRS files"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codeqlclient import CodeQLQueryServer


def decode_bqrs_impl(qs: CodeQLQueryServer, bqrs_path: str, fmt: str) -> str:
    """Implementation for decode_bqrs tool"""
    return qs.decode_bqrs(bqrs_path, fmt)
