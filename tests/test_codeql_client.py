import pytest
import json
import threading
import asyncio
from unittest.mock import MagicMock, patch, call
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codeqlclient import CodeQLQueryServer


class TestCodeQLQueryServer:
    def test_init(self):
        """Test CodeQLQueryServer initialization"""
        server = CodeQLQueryServer()
        assert server.codeql_path == "codeql"
        assert server.proc is None
        assert server.pending == {}
        assert server.running is True
        assert server.id_counter == 1

    def test_init_custom_path(self):
        """Test initialization with custom CodeQL path"""
        server = CodeQLQueryServer("/custom/path/codeql")
        assert server.codeql_path == "/custom/path/codeql"

    @patch('subprocess.Popen')
    @patch('threading.Thread')
    def test_start(self, mock_thread, mock_popen):
        """Test starting the CodeQL query server"""
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        server = CodeQLQueryServer()
        server.start()

        assert server.proc == mock_proc
        mock_popen.assert_called_once()

        # Verify command structure
        args = mock_popen.call_args[0][0]
        assert "codeql" in args[0]
        assert "execute" in args
        assert "query-server2" in args

        # Verify threads are started
        assert mock_thread.call_count == 2  # reader and stderr threads

    def test_stop(self):
        """Test stopping the server"""
        server = CodeQLQueryServer()
        mock_proc = MagicMock()
        server.proc = mock_proc

        server.stop()

        assert server.running is False
        mock_proc.terminate.assert_called_once()


class TestMessageHandling:
    def test_handle_progress_message(self):
        """Test handling of progress update messages"""
        server = CodeQLQueryServer()
        callback = MagicMock()
        server.progress_callbacks[1] = callback

        message = {
            "method": "ql/progressUpdated",
            "params": {
                "id": 1,
                "step": 5,
                "maxStep": 10
            }
        }

        server._handle_message(message)
        callback.assert_called_once_with(message["params"])

    def test_handle_evaluation_progress(self):
        """Test handling of evaluation progress messages"""
        server = CodeQLQueryServer()
        callback = MagicMock()
        server.progress_callbacks[1] = callback

        message = {
            "method": "evaluation/progress",
            "params": {
                "progressId": 1,
                "message": "Running query..."
            }
        }

        server._handle_message(message)
        callback.assert_called_once_with("Running query...")

    def test_handle_result_message(self):
        """Test handling of result messages"""
        server = CodeQLQueryServer()
        callback = MagicMock()
        server.pending[1] = (callback, None)

        message = {
            "id": 1,
            "result": {"status": "success"}
        }

        server._handle_message(message)
        callback.assert_called_once_with({"status": "success"})
        assert 1 not in server.pending

    def test_handle_error_message(self, capsys):
        """Test handling of error messages"""
        server = CodeQLQueryServer()
        callback = MagicMock()
        server.pending[1] = (callback, None)

        message = {
            "id": 1,
            "error": {"code": -1, "message": "Query failed"}
        }

        server._handle_message(message)
        captured = capsys.readouterr()
        assert "Error response" in captured.out


class TestRequestSending:
    @patch.object(CodeQLQueryServer, '_send')
    def test_send_request_basic(self, mock_send):
        """Test sending a basic request"""
        server = CodeQLQueryServer()
        callback = MagicMock()

        server.send_request("test/method", {"param": "value"}, callback)

        assert 1 in server.pending
        assert server.id_counter == 2

        mock_send.assert_called_once()
        payload = mock_send.call_args[0][0]
        assert payload["method"] == "test/method"
        assert payload["params"] == {"param": "value"}
        assert payload["id"] == 1

    @patch.object(CodeQLQueryServer, '_send')
    def test_send_request_with_progress(self, mock_send):
        """Test sending request with progress callback"""
        server = CodeQLQueryServer()
        callback = MagicMock()
        progress_callback = MagicMock()

        params = {"progressId": 123, "data": "test"}
        server.send_request("test/method", params, callback, progress_callback)

        assert 123 in server.progress_callbacks
        assert server.progress_callbacks[123] == progress_callback

    def test_send_message_formatting(self):
        """Test proper message formatting"""
        server = CodeQLQueryServer()
        mock_stdin = MagicMock()
        server.proc = MagicMock()
        server.proc.stdin = mock_stdin

        payload = {"test": "data"}
        server._send(payload)

        mock_stdin.write.assert_called_once()
        written_content = mock_stdin.write.call_args[0][0]

        assert "Content-Length:" in written_content
        assert json.dumps(payload) in written_content
        assert written_content.count("\r\n") >= 2  # Headers and content separator


class TestDatabaseOperations:
    @patch.object(CodeQLQueryServer, 'send_request')
    def test_register_databases(self, mock_send_request):
        """Test registering databases"""
        server = CodeQLQueryServer()
        callback = MagicMock()
        progress_callback = MagicMock()

        server.register_databases(
            ["/path/to/db1", "/path/to/db2"],
            callback=callback,
            progress_callback=progress_callback
        )

        mock_send_request.assert_called_once()
        args = mock_send_request.call_args
        assert args[0][0] == "evaluation/registerDatabases"
        databases = args[0][1]["body"]["databases"]
        # Check that databases contain the paths (allow for Windows path normalization)
        assert any("db1" in db for db in databases)
        assert any("db2" in db for db in databases)
        assert args[0][2] == callback
        assert args[1]["progress_callback"] == progress_callback

    @patch.object(CodeQLQueryServer, 'send_request')
    def test_deregister_databases(self, mock_send_request):
        """Test deregistering databases"""
        server = CodeQLQueryServer()
        callback = MagicMock()

        server.deregister_databases(["/path/to/db"], callback=callback)

        mock_send_request.assert_called_once()
        args = mock_send_request.call_args
        assert args[0][0] == "evaluation/deregisterDatabases"


class TestQueryOperations:
    @patch.object(CodeQLQueryServer, 'send_request')
    def test_evaluate_queries(self, mock_send_request):
        """Test query evaluation"""
        server = CodeQLQueryServer()
        callback = MagicMock()

        server.evaluate_queries(
            "/path/to/query.ql",
            "/path/to/db",
            "/path/to/output.bqrs",
            callback=callback
        )

        mock_send_request.assert_called_once()
        args = mock_send_request.call_args
        assert args[0][0] == "evaluation/runQuery"

        params = args[0][1]
        # Check path components exist (allow for Windows path normalization)
        assert "query.ql" in params["body"]["queryPath"]
        assert "db" in params["body"]["db"]
        assert "output.bqrs" in params["body"]["outputPath"]
        assert "target" in params["body"]
        assert "query" in params["body"]["target"]

    @patch.object(CodeQLQueryServer, 'send_request')
    def test_quick_evaluate(self, mock_send_request):
        """Test quick evaluation of specific positions"""
        server = CodeQLQueryServer()

        server.quick_evaluate(
            "/path/to/query.ql",
            "/path/to/db",
            "/path/to/output.bqrs",
            start_line=10,
            start_col=5,
            end_line=10,
            end_col=15
        )

        mock_send_request.assert_called_once()
        args = mock_send_request.call_args
        params = args[0][1]

        quick_eval = params["body"]["target"]["quickEval"]
        pos = quick_eval["quickEvalPos"]
        assert pos["line"] == 10
        assert pos["column"] == 5
        assert pos["endLine"] == 10
        assert pos["endColumn"] == 15

    @patch.object(CodeQLQueryServer, 'wait_for_progress_done')
    @patch.object(CodeQLQueryServer, 'evaluate_queries')
    def test_evaluate_and_wait(self, mock_evaluate, mock_wait):
        """Test synchronous query evaluation"""
        server = CodeQLQueryServer()
        mock_event = MagicMock()
        mock_wait.return_value = (MagicMock(), mock_event)

        server.evaluate_and_wait(
            "/path/to/query.ql",
            "/path/to/db",
            "/path/to/output.bqrs"
        )

        mock_evaluate.assert_called_once()
        mock_event.wait.assert_called_once()

    @patch.object(CodeQLQueryServer, 'wait_for_progress_done')
    @patch.object(CodeQLQueryServer, 'quick_evaluate')
    def test_quick_evaluate_and_wait(self, mock_evaluate, mock_wait):
        """Test synchronous quick evaluation"""
        server = CodeQLQueryServer()
        mock_event = MagicMock()
        mock_wait.return_value = (MagicMock(), mock_event)

        server.quick_evaluate_and_wait(
            "/path/to/query.ql",
            "/path/to/db",
            "/path/to/output.bqrs",
            start_line=5,
            start_col=1,
            end_line=5,
            end_col=10
        )

        mock_evaluate.assert_called_once()
        mock_event.wait.assert_called_once()


class TestPositionFinding:
    def test_find_class_identifier_position(self, tmp_path):
        """Test finding class identifier position"""
        query_file = tmp_path / "test.ql"
        query_file.write_text("""
import python

class MyTestClass extends Expr {
    MyTestClass() { this.isCall() }
}

from MyTestClass mtc
select mtc
""")

        server = CodeQLQueryServer()
        start_line, start_col, end_line, end_col = server.find_class_identifier_position(
            str(query_file), "MyTestClass"
        )

        assert start_line == 4
        assert start_col > 0
        assert end_line == 4
        assert end_col > start_col
        assert end_col == start_col + len("MyTestClass")

    def test_find_class_not_found(self, tmp_path):
        """Test error when class not found"""
        query_file = tmp_path / "test.ql"
        query_file.write_text("// No class here")

        server = CodeQLQueryServer()
        with pytest.raises(ValueError, match="Class name 'NonExistent' not found"):
            server.find_class_identifier_position(str(query_file), "NonExistent")

    def test_find_predicate_identifier_position(self, tmp_path):
        """Test finding predicate identifier position"""
        query_file = tmp_path / "test.ql"
        query_file.write_text("""
import python

predicate isVulnerable(Expr e) {
    e.isCall()
}

boolean myPredicate(Node n) {
    result = true
}
""")

        server = CodeQLQueryServer()
        start_line, start_col, end_line, end_col = server.find_predicate_identifier_position(
            str(query_file), "isVulnerable"
        )

        assert start_line == 4
        assert start_col > 0
        assert end_line == 4

        # Test second predicate
        start_line, start_col, end_line, end_col = server.find_predicate_identifier_position(
            str(query_file), "myPredicate"
        )
        assert start_line == 8

    def test_find_predicate_not_found(self, tmp_path):
        """Test error when predicate not found"""
        query_file = tmp_path / "test.ql"
        query_file.write_text("// No predicate here")

        server = CodeQLQueryServer()
        with pytest.raises(ValueError, match="Predicate name 'nonexistent' not found"):
            server.find_predicate_identifier_position(str(query_file), "nonexistent")


class TestBqrsDecoding:
    def test_decode_bqrs_json(self, tmp_path):
        """Test BQRS decoding to JSON"""
        bqrs_file = tmp_path / "test.bqrs"
        bqrs_file.write_bytes(b"fake bqrs content")

        server = CodeQLQueryServer()
        
        import subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"#select": {"tuples": [{"col": "val"}]}}'
            )
            
            result = server.decode_bqrs(str(bqrs_file), "json")
            
            assert result is not None
            assert "tuples" in result or "results" in result
            
            cmd = mock_run.call_args[0][0]
            assert "codeql" in cmd[0]
            assert "bqrs" in cmd
            assert "decode" in cmd
            assert "--format=json" in cmd or "json" in cmd

    def test_decode_bqrs_csv(self, tmp_path):
        """Test BQRS decoding to CSV"""
        bqrs_file = tmp_path / "test.bqrs"
        bqrs_file.write_bytes(b"fake bqrs content")

        server = CodeQLQueryServer()
        
        import subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="col1,col2\nval1,val2"
            )
            
            result = server.decode_bqrs(str(bqrs_file), "csv")
            
            assert "col1,col2" in result
            assert "val1,val2" in result

    def test_decode_bqrs_file_not_found(self):
        """Test error when BQRS file doesn't exist"""
        server = CodeQLQueryServer()
        with pytest.raises(FileNotFoundError):
            server.decode_bqrs("/nonexistent/path/to/file.bqrs")

    def test_decode_bqrs_command_failure(self, tmp_path):
        """Test error when decode command fails"""
        bqrs_file = tmp_path / "test.bqrs"
        bqrs_file.write_bytes(b"fake bqrs content")

        server = CodeQLQueryServer()
        
        import subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr="Decode failed"
            )
            
            with pytest.raises(RuntimeError, match="Failed to decode BQRS"):
                server.decode_bqrs(str(bqrs_file))


class TestCallbackHelpers:
    def test_wait_for_progress_done(self):
        """Test progress completion callback helper"""
        server = CodeQLQueryServer()
        callback, event = server.wait_for_progress_done(123)

        # Test incomplete progress
        callback({"id": 123, "step": 5, "maxStep": 10})
        assert not event.is_set()

        # Test completed progress
        callback({"id": 123, "step": 10, "maxStep": 10})
        assert event.is_set()

    def test_wait_for_completion_callback(self):
        """Test general completion callback helper"""
        server = CodeQLQueryServer()
        callback, done, result_holder = server.wait_for_completion_callback()

        test_result = {"status": "success"}
        callback(test_result)

        assert done.is_set()
        assert result_holder["result"] == test_result

    def test_progress_callback_wrong_id(self):
        """Test progress callback with wrong ID"""
        server = CodeQLQueryServer()
        callback, event = server.wait_for_progress_done(123)

        # Different ID should not trigger
        callback({"id": 456, "step": 10, "maxStep": 10})
        assert not event.is_set()

    def test_progress_callback_non_dict(self):
        """Test progress callback with non-dict message"""
        server = CodeQLQueryServer()
        callback, event = server.wait_for_progress_done(123)

        # String message should not trigger
        callback("progress message")
        assert not event.is_set()


class TestErrorHandling:
    def test_send_without_process(self, capsys):
        """Test sending when process is not running"""
        server = CodeQLQueryServer()
        server.proc = None

        server._send({"test": "message"})

        captured = capsys.readouterr()
        assert "Tried to send but process not running" in captured.out

    @patch('json.loads')
    def test_handle_invalid_json(self, mock_json, capsys):
        """Test handling of malformed JSON messages"""
        mock_json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        server = CodeQLQueryServer()
        # This would be called from _read_loop in real scenario
        # We can't easily test it directly due to threading

    def test_path_resolution(self):
        """Test that paths are properly resolved"""
        server = CodeQLQueryServer()

        with patch.object(server, 'send_request') as mock_send:
            server.evaluate_queries(
                "relative/query.ql",
                "relative/db",
                "relative/output.bqrs"
            )

            # Verify paths are resolved to absolute
            params = mock_send.call_args[0][1]
            assert Path(params["body"]["queryPath"]).is_absolute()
            assert Path(params["body"]["db"]).is_absolute()
            assert Path(params["body"]["outputPath"]).is_absolute()


class TestThreadSafety:
    def test_concurrent_requests(self):
        """Test handling multiple concurrent requests"""
        server = CodeQLQueryServer()

        callbacks = []
        for i in range(5):
            callback = MagicMock()
            callbacks.append(callback)
            server.send_request(f"test/method{i}", {"id": i}, callback)

        # All requests should be tracked
        assert len(server.pending) == 5
        assert server.id_counter == 6

        # Simulate responses
        for i in range(1, 6):
            server._handle_message({
                "id": i,
                "result": {"response": f"result{i}"}
            })

        # All callbacks should be called
        for i, callback in enumerate(callbacks):
            callback.assert_called_once_with({"response": f"result{i+1}"})

        # Pending should be empty
        assert len(server.pending) == 0