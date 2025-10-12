"""Query and pack discovery: languages, packs, and security queries"""

import subprocess
import json
from pathlib import Path


def list_supported_languages_impl(qs) -> list:
    """Implementation for list_supported_languages tool"""
    try:
        result = subprocess.run([qs.codeql_path, "resolve", "languages"],
                              capture_output=True, text=True)

        if result.returncode != 0:
            return ["Error getting languages: " + result.stderr]

        # Parse the output to extract language names
        languages = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                # Extract language name from the output format
                lang = line.strip().split()[0] if line.strip().split() else line.strip()
                languages.append(lang)

        return languages

    except Exception as e:
        return [f"Error: {str(e)}"]


def list_query_packs_impl(qs) -> dict:
    """Implementation for list_query_packs tool"""
    try:
        # Get installed packs using codeql resolve packs
        result = subprocess.run(
            [qs.codeql_path, "resolve", "packs", "--kind=query"],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            # Fallback to static list if command fails
            return {
                "error": "Could not dynamically list packs, using defaults",
                "packs": {
                    "python": "codeql/python-queries",
                    "javascript": "codeql/javascript-queries",
                    "java": "codeql/java-queries",
                    "csharp": "codeql/csharp-queries",
                    "cpp": "codeql/cpp-queries",
                    "go": "codeql/go-queries",
                    "ruby": "codeql/ruby-queries"
                }
            }

        # Parse the output to extract pack information
        packs_by_language = {}
        lines = result.stdout.strip().split('\n')

        for line in lines:
            if 'codeql/' in line and '-queries' in line:
                # Extract pack name from the line
                parts = line.strip().split()
                for part in parts:
                    if 'codeql/' in part and '-queries' in part:
                        pack_name = part.split('(')[0].strip()
                        # Extract language from pack name
                        lang = pack_name.replace('codeql/', '').replace('-queries', '')

                        # Map to standard language names
                        lang_map = {
                            'javascript': 'javascript-typescript',
                            'java': 'java-kotlin',
                            'cpp': 'c-cpp'
                        }
                        display_lang = lang_map.get(lang, lang)

                        packs_by_language[display_lang] = {
                            "pack": pack_name,
                            "suites": [
                                f"{pack_name}:codeql-suites/{lang}-code-scanning.qls",
                                f"{pack_name}:codeql-suites/{lang}-security-extended.qls",
                                f"{pack_name}:codeql-suites/{lang}-security-and-quality.qls"
                            ]
                        }
                        break

        return packs_by_language if packs_by_language else {
            "message": "No query packs found. Install CodeQL packs first."
        }

    except Exception as e:
        return {"error": f"Error listing packs: {str(e)}"}


def discover_queries_impl(qs, pack_name: str = None, language: str = None, category: str = None) -> list:
    """Implementation for discover_queries tool"""
    try:
        cmd = [qs.codeql_path, "resolve", "queries", "--format=bylanguage"]

        if pack_name:
            cmd.append(pack_name)
        elif language:
            # Use standard pack for language
            lang_packs = {
                "python": "codeql/python-queries",
                "javascript": "codeql/javascript-queries",
                "typescript": "codeql/javascript-queries",
                "java": "codeql/java-queries",
                "kotlin": "codeql/java-queries",
                "csharp": "codeql/csharp-queries",
                "cpp": "codeql/cpp-queries",
                "c": "codeql/cpp-queries",
                "go": "codeql/go-queries",
                "ruby": "codeql/ruby-queries",
                "swift": "codeql/swift-queries",
                "rust": "codeql/rust-queries"
            }
            if language.lower() in lang_packs:
                cmd.append(lang_packs[language.lower()])
            else:
                return [f"Unsupported language: {language}"]
        else:
            return [f"Error: specify either language or pack name"]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return [f"Error discovering queries: {result.stderr}"]

        data = json.loads(result.stdout)

        # Handle bylanguage format: {"byLanguage": {"python": {"path/to/query.ql": {}, ...}}}
        if "byLanguage" in data:
            data = data["byLanguage"]

        queries = []
        for extractor, query_data in data.items():
            # query_data is dict: {"path/to/query.ql": {metadata}, ...}
            for query_path in query_data.keys():
                query_info = {
                    "path": query_path,
                    "language": extractor,
                    "filename": Path(query_path).name
                }

                if category:
                    if category.lower() in query_path.lower():
                        queries.append(query_info)
                else:
                    queries.append(query_info)

        return queries

    except Exception as e:
        return [f"Error: {str(e)}"]


async def find_security_queries_impl(qs, get_db_info_func, discover_queries_func, 
                                     language: str = None, vulnerability_type: str = None, 
                                     db_path: str = None) -> dict:
    """Implementation for find_security_queries tool
    
    Note: Requires async functions for get_database_info and discover_queries
    """
    try:
        # If db_path provided, get language from database
        if db_path and not language:
            db_info = await get_db_info_func(db_path)
            if "error" in db_info:
                return db_info
            language = db_info.get("language")
            if not language:
                return {"error": "Could not determine language from database"}

        if not language:
            return {"error": "Either language or db_path must be specified"}

        # Get all queries for the language
        all_queries = await discover_queries_func(language=language, category="security")

        if isinstance(all_queries, list) and len(all_queries) > 0 and isinstance(all_queries[0], str) and all_queries[0].startswith("Error"):
            return {"error": all_queries[0]}

        # Group by vulnerability types
        security_queries = {}

        vuln_patterns = {
            "sql_injection": ["sql", "injection", "sqli", "cwe-089"],
            "xss": ["xss", "cross-site", "scripting", "cwe-079"],
            "command_injection": ["command", "injection", "exec", "cwe-078"],
            "path_traversal": ["path", "traversal", "directory", "cwe-022"],
            "hardcoded_credentials": ["hardcoded", "credentials", "password", "cwe-798"],
            "csrf": ["csrf", "cross-site", "request", "forgery", "cwe-352"],
            "deserialization": ["deserialization", "pickle", "unmarshal", "cwe-502"],
            "xxe": ["xxe", "xml", "external", "entity", "cwe-611"],
            "ldap_injection": ["ldap", "injection", "cwe-090"],
            "code_injection": ["code", "injection", "eval", "cwe-094"],
            "buffer_overflow": ["buffer", "overflow", "bounds", "cwe-119", "cwe-120"],
            "use_after_free": ["use", "after", "free", "cwe-416"],
            "null_pointer": ["null", "pointer", "dereference", "cwe-476"],
            "integer_overflow": ["integer", "overflow", "cwe-190"],
            "weak_crypto": ["crypto", "cryptography", "weak", "md5", "sha1", "cwe-327"],
            "insecure_random": ["random", "insecure", "predictable", "cwe-338"]
        }

        for query in all_queries:
            if isinstance(query, dict):
                query_path = query.get("path", "").lower()
                query_name = query.get("filename", "").lower()

                for vuln_type, patterns in vuln_patterns.items():
                    if vulnerability_type and vulnerability_type.lower() != vuln_type:
                        continue

                    if any(pattern in query_path or pattern in query_name for pattern in patterns):
                        if vuln_type not in security_queries:
                            security_queries[vuln_type] = []
                        security_queries[vuln_type].append(query)

        return security_queries

    except Exception as e:
        return {"error": f"Error finding security queries: {str(e)}"}
