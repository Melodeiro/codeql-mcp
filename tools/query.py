"""Query execution: predicates and full query evaluation"""

from __future__ import annotations

from typing import TYPE_CHECKING

from validation import validate_query_file, validate_query_syntax

if TYPE_CHECKING:
    from codeqlclient import CodeQLQueryServer


def test_predicate_impl(qs: CodeQLQueryServer, file: str, db: str, symbol: str, output_path: str = "/tmp/quickeval.bqrs") -> str:
    """Implementation for test_predicate tool"""
    # Validate query file
    validation = validate_query_file(file)
    if not validation["valid"]:
        return f"Error: {validation['error']}"
    
    # Try to find symbol position
    try:
        start, scol, end, ecol = qs.find_class_identifier_position(file, symbol)
    except ValueError:
        try:
            start, scol, end, ecol = qs.find_predicate_identifier_position(
                file, symbol
            )
        except ValueError:
            return f"Error: Symbol '{symbol}' not found in {file}. Make sure the class or predicate name is correct."
    
    # Execute quick evaluation
    try:
        qs.quick_evaluate_and_wait(
            file, db, output_path, start, scol, end, ecol
        )
    except RuntimeError as re:
        return f"CodeQL evaluation failed: {re}"
    
    return output_path


def evaluate_query_impl(qs: CodeQLQueryServer, query_path: str, db_path: str, output_path: str = "/tmp/eval.bqrs") -> str:
    """Implementation for evaluate_query tool"""
    # Validate query file exists and has correct extension
    file_validation = validate_query_file(query_path)
    if not file_validation["valid"]:
        return f"Error: {file_validation['error']}"
    
    # Validate query syntax
    syntax_validation = validate_query_syntax(query_path, qs.codeql_path)
    if not syntax_validation["valid"]:
        return f"Error: {syntax_validation['error']}"
    
    # Execute query
    try:
        qs.evaluate_and_wait(query_path, db_path, output_path)
    except RuntimeError as re:
        return f"CodeQL evaluation failed: {re}"
    
    return output_path
