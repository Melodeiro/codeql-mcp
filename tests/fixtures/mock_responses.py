"""
Mock responses for CodeQL operations
"""

import json


class MockCodeQLResponses:
    """Collection of mock responses for CodeQL commands"""

    @staticmethod
    def database_resolve_output(language="python"):
        """Mock output from 'codeql resolve database'"""
        return f"""
primaryLanguage: {language}
creationMetadata:
  sha: abc123def456
  cliVersion: 2.15.0
  creationTime: 2025-01-15T10:30:00Z
sourceLocationPrefix: /path/to/source
baseline:
  location:
    startLine: 1
    startColumn: 1
    endLine: 1000
    endColumn: 1
""".strip()

    @staticmethod
    def database_baseline_output(lines=5000):
        """Mock output from 'codeql database print-baseline'"""
        return f"Database has baseline of {lines} lines of code"

    @staticmethod
    def supported_languages_output():
        """Mock output from 'codeql resolve languages'"""
        return """
cpp
csharp
go
java
javascript
python
ruby
swift
        """.strip()

    @staticmethod
    def query_packs_output():
        """Mock output from 'codeql resolve packs --kind=query'"""
        return """
codeql/cpp-queries (1.0.0): /path/to/cpp-queries
codeql/csharp-queries (1.0.0): /path/to/csharp-queries
codeql/go-queries (1.0.0): /path/to/go-queries
codeql/java-queries (1.0.0): /path/to/java-queries
codeql/javascript-queries (1.0.0): /path/to/javascript-queries
codeql/python-queries (1.0.0): /path/to/python-queries
codeql/ruby-queries (1.0.0): /path/to/ruby-queries
codeql/swift-queries (1.0.0): /path/to/swift-queries
        """.strip()

    @staticmethod
    def discover_queries_output(language="python"):
        """Mock output from 'codeql resolve queries'"""
        base_path = f"/path/to/codeql/{language}/ql/src"

        if language == "python":
            return json.dumps({
                "python": [
                    f"{base_path}/Security/CWE-089/SqlInjection.ql",
                    f"{base_path}/Security/CWE-079/ReflectedXss.ql",
                    f"{base_path}/Security/CWE-078/CommandInjection.ql",
                    f"{base_path}/Security/CWE-022/PathInjection.ql",
                    f"{base_path}/Security/CWE-798/HardcodedCredentials.ql",
                    f"{base_path}/Security/CWE-502/UnsafeDeserialization.ql",
                    f"{base_path}/Quality/Maintainability/DuplicateBlock.ql",
                    f"{base_path}/Quality/Reliability/UnusedVariable.ql"
                ]
            })
        elif language == "javascript":
            return json.dumps({
                "javascript": [
                    f"{base_path}/Security/CWE-089/SqlInjection.ql",
                    f"{base_path}/Security/CWE-079/DomBasedXss.ql",
                    f"{base_path}/Security/CWE-078/CommandInjection.ql",
                    f"{base_path}/Security/CWE-352/MissingCsrfMiddleware.ql"
                ]
            })
        else:
            return json.dumps({language: []})

    @staticmethod
    def sarif_output():
        """Mock SARIF output from analysis"""
        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "CodeQL",
                            "organization": "GitHub",
                            "semanticVersion": "2.15.0",
                            "rules": [
                                {
                                    "id": "py/sql-injection",
                                    "name": "SqlInjection",
                                    "shortDescription": {
                                        "text": "SQL query built from user-controlled sources"
                                    },
                                    "fullDescription": {
                                        "text": "If a SQL query is built from user-provided data without sufficient sanitization, a user may be able to run malicious database queries."
                                    },
                                    "defaultConfiguration": {
                                        "level": "error"
                                    },
                                    "properties": {
                                        "tags": ["security", "external/cwe/cwe-089"],
                                        "kind": "path-problem",
                                        "precision": "high",
                                        "problem.severity": "error"
                                    }
                                }
                            ]
                        }
                    },
                    "results": [
                        {
                            "ruleId": "py/sql-injection",
                            "ruleIndex": 0,
                            "rule": {
                                "id": "py/sql-injection",
                                "index": 0
                            },
                            "message": {
                                "text": "This SQL query depends on a [user-provided value](1)."
                            },
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "uri": "app.py",
                                            "uriBaseId": "%SRCROOT%"
                                        },
                                        "region": {
                                            "startLine": 25,
                                            "startColumn": 15,
                                            "endLine": 25,
                                            "endColumn": 48
                                        }
                                    }
                                }
                            ],
                            "partialFingerprints": {
                                "primaryLocationLineHash": "abc123def456:1",
                                "primaryLocationStartColumnFingerprint": "15"
                            },
                            "codeFlows": [
                                {
                                    "threadFlows": [
                                        {
                                            "locations": [
                                                {
                                                    "location": {
                                                        "physicalLocation": {
                                                            "artifactLocation": {
                                                                "uri": "app.py",
                                                                "uriBaseId": "%SRCROOT%"
                                                            },
                                                            "region": {
                                                                "startLine": 20,
                                                                "startColumn": 20,
                                                                "endLine": 20,
                                                                "endColumn": 34
                                                            }
                                                        },
                                                        "message": {
                                                            "text": "user-provided value"
                                                        }
                                                    }
                                                },
                                                {
                                                    "location": {
                                                        "physicalLocation": {
                                                            "artifactLocation": {
                                                                "uri": "app.py",
                                                                "uriBaseId": "%SRCROOT%"
                                                            },
                                                            "region": {
                                                                "startLine": 25,
                                                                "startColumn": 15,
                                                                "endLine": 25,
                                                                "endColumn": 48
                                                            }
                                                        },
                                                        "message": {
                                                            "text": "SQL query"
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def bqrs_decode_json():
        """Mock JSON output from BQRS decoding"""
        return json.dumps({
            "#select": {
                "tuples": [
                    {
                        "url": "file:///path/to/source/app.py:25:15:25:48",
                        "string": "SQL injection vulnerability"
                    },
                    {
                        "url": "file:///path/to/source/utils.py:10:5:10:25",
                        "string": "Potential XSS vulnerability"
                    }
                ]
            }
        }, indent=2)

    @staticmethod
    def bqrs_decode_csv():
        """Mock CSV output from BQRS decoding"""
        return """url,string
"file:///path/to/source/app.py:25:15:25:48","SQL injection vulnerability"
"file:///path/to/source/utils.py:10:5:10:25","Potential XSS vulnerability"
"""

    @staticmethod
    def database_create_success():
        """Mock success output from database creation"""
        return """
Successfully created database at /path/to/database.
        """.strip()

    @staticmethod
    def database_create_error():
        """Mock error output from database creation"""
        return """
FATAL ERROR: Failed to run autobuilder: could not auto-detect a suitable build method

Build failed. For more information, see the build log:
/tmp/codeql-build-log.txt
        """.strip()

    @staticmethod
    def analysis_success():
        """Mock success output from database analysis"""
        return """
Running queries.
[1/15 eval 245ms] Evaluation done; writing results to /tmp/analysis.sarif.
[2/15 eval 180ms] Evaluation done; writing results to /tmp/analysis.sarif.
...
[15/15 eval 95ms] Evaluation done; writing results to /tmp/analysis.sarif.
Successfully wrote results to /tmp/analysis.sarif.
        """.strip()

    @staticmethod
    def analysis_error():
        """Mock error output from database analysis"""
        return """
ERROR: Could not process query pack codeql/python-queries: Invalid query suite.
        """.strip()


class MockQueryFiles:
    """Sample CodeQL query files for testing"""

    @staticmethod
    def sql_injection_query():
        """Sample SQL injection query"""
        return '''
/**
 * @name SQL query built from user-controlled sources
 * @description Building a SQL query from user-controlled sources is vulnerable to insertion of
 *              malicious SQL code by the user.
 * @kind path-problem
 * @problem.severity error
 * @precision high
 * @id py/sql-injection
 * @tags security
 *       external/cwe/cwe-089
 */

import python
import semmle.python.security.dataflow.SqlInjectionQuery
import DataFlow::PathGraph

from SqlInjectionFlow::PathNode source, SqlInjectionFlow::PathNode sink
where SqlInjectionFlow::flowPath(source, sink)
select sink.getNode(), source, sink, "This SQL query depends on a $@.", source.getNode(),
  "user-provided value"
'''

    @staticmethod
    def xss_query():
        """Sample XSS query"""
        return '''
/**
 * @name Reflected server-side cross-site scripting
 * @description Writing user input directly to a web page
 *              allows for a cross-site scripting vulnerability.
 * @kind path-problem
 * @problem.severity error
 * @precision high
 * @id py/reflective-xss
 * @tags security
 *       external/cwe/cwe-079
 */

import python
import semmle.python.security.dataflow.ReflectedXssQuery
import DataFlow::PathGraph

from ReflectedXssFlow::PathNode source, ReflectedXssFlow::PathNode sink
where ReflectedXssFlow::flowPath(source, sink)
select sink.getNode(), source, sink, "Cross-site scripting vulnerability due to $@.",
  source.getNode(), "user-provided value"
'''

    @staticmethod
    def simple_test_query():
        """Simple test query for quick evaluation"""
        return '''
import python

class TestCall extends Call {
  TestCall() { this.getFunc().(Name).getId() = "print" }
}

predicate isPrintCall(Call c) {
  c instanceof TestCall
}

from TestCall tc
select tc, "Print call found"
'''


class MockDatabaseStructure:
    """Helper to create mock database structures"""

    @staticmethod
    def create_minimal_db(db_path):
        """Create minimal database structure"""
        from pathlib import Path

        db_path = Path(db_path)
        db_path.mkdir(parents=True, exist_ok=True)

        # Create required files
        (db_path / "src.zip").write_text("mock source archive")
        (db_path / "codeql-database.yml").write_text(f"""
primaryLanguage: python
creationMetadata:
  sha: test123
  cliVersion: 2.15.0
  creationTime: 2025-01-15T10:30:00Z
""")

        # Create database schema files
        schema_dir = db_path / "db-python"
        schema_dir.mkdir(exist_ok=True)
        (schema_dir / "default").mkdir(exist_ok=True)

        return str(db_path)

    @staticmethod
    def create_query_pack(pack_path, language="python"):
        """Create minimal query pack structure"""
        from pathlib import Path

        pack_path = Path(pack_path)
        pack_path.mkdir(parents=True, exist_ok=True)

        # Create qlpack.yml
        (pack_path / "qlpack.yml").write_text(f"""
name: test/{language}-queries
version: 1.0.0
dependencies:
  codeql/{language}-all: "*"
""")

        # Create query directories
        security_dir = pack_path / "Security"
        security_dir.mkdir(exist_ok=True)

        if language == "python":
            # SQL injection query
            sql_dir = security_dir / "CWE-089"
            sql_dir.mkdir(exist_ok=True)
            (sql_dir / "SqlInjection.ql").write_text(MockQueryFiles.sql_injection_query())

            # XSS query
            xss_dir = security_dir / "CWE-079"
            xss_dir.mkdir(exist_ok=True)
            (xss_dir / "ReflectedXss.ql").write_text(MockQueryFiles.xss_query())

        return str(pack_path)