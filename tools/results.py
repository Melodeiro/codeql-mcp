"""Results processing: decoding BQRS files"""


def decode_bqrs_impl(qs, bqrs_path: str, fmt: str) -> str:
    """Implementation for decode_bqrs tool"""
    return qs.decode_bqrs(bqrs_path, fmt)
