"""
Tests for backend/executor.py — subprocess and Docker calls are mocked.
"""

import subprocess
from unittest.mock import MagicMock, patch

from backend.executor import _timeout_result, _local_run, _docker_run, _run, SANDBOX_TIMEOUT


class TestTimeoutResult:
    def test_structure(self):
        result = _timeout_result()
        assert result["stdout"] == ""
        assert result["exit_code"] == 1
        assert "TimeoutError" in result["stderr"]

    def test_message_includes_timeout_seconds(self):
        result = _timeout_result()
        assert str(SANDBOX_TIMEOUT) in result["stderr"]


class TestLocalRun:
    def _mock_proc(self, stdout="", stderr="", returncode=0):
        proc = MagicMock()
        proc.stdout = stdout
        proc.stderr = stderr
        proc.returncode = returncode
        return proc

    def test_success(self):
        with patch("backend.executor.subprocess.run", return_value=self._mock_proc(stdout="42\n")):
            result = _local_run("print(42)")
        assert result["stdout"] == "42\n"
        assert result["exit_code"] == 0

    def test_nonzero_exit_code_on_error(self):
        with patch("backend.executor.subprocess.run",
                   return_value=self._mock_proc(stderr="NameError", returncode=1)):
            result = _local_run("undefined_var")
        assert result["exit_code"] == 1
        assert "NameError" in result["stderr"]

    def test_timeout_returns_timeout_result(self):
        with patch("backend.executor.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("python3", SANDBOX_TIMEOUT)):
            result = _local_run("import time; time.sleep(999)")
        assert result["exit_code"] == 1
        assert "TimeoutError" in result["stderr"]

    def test_stdout_capped_at_8192(self):
        big_stdout = "A" * 10_000
        with patch("backend.executor.subprocess.run",
                   return_value=self._mock_proc(stdout=big_stdout)):
            result = _local_run("whatever")
        assert len(result["stdout"]) == 8192

    def test_stderr_capped_at_4096(self):
        big_stderr = "E" * 6_000
        with patch("backend.executor.subprocess.run",
                   return_value=self._mock_proc(stderr=big_stderr, returncode=1)):
            result = _local_run("whatever")
        assert len(result["stderr"]) == 4096


class TestDockerRun:
    def _mock_proc(self, stdout="", stderr="", returncode=0):
        proc = MagicMock()
        proc.stdout = stdout
        proc.stderr = stderr
        proc.returncode = returncode
        return proc

    def test_success(self):
        with patch("backend.executor.subprocess.run",
                   return_value=self._mock_proc(stdout="hello\n")):
            result = _docker_run("print('hello')")
        assert result["stdout"] == "hello\n"
        assert result["exit_code"] == 0

    def test_timeout_returns_timeout_result(self):
        with patch("backend.executor.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("docker", SANDBOX_TIMEOUT + 5)):
            result = _docker_run("import time; time.sleep(999)")
        assert result["exit_code"] == 1
        assert "TimeoutError" in result["stderr"]

    def test_docker_failure_falls_back_to_local(self):
        fallback = {"stdout": "ok\n", "stderr": "", "exit_code": 0}
        with patch("backend.executor.subprocess.run", side_effect=Exception("image not found")), \
             patch("backend.executor._local_run", return_value=fallback) as mock_local:
            result = _docker_run("print('ok')")
        mock_local.assert_called_once()
        assert result == fallback

    def test_passes_network_none_flag(self):
        with patch("backend.executor.subprocess.run",
                   return_value=self._mock_proc()) as mock_run:
            _docker_run("pass")
            cmd = mock_run.call_args.args[0]
        assert "--network" in cmd
        assert "none" in cmd


class TestRun:
    def test_dispatches_to_docker_when_available(self):
        docker_result = {"stdout": "", "stderr": "", "exit_code": 0}
        with patch("backend.executor.shutil.which", return_value="/usr/bin/docker"), \
             patch("backend.executor._docker_run", return_value=docker_result) as mock_docker:
            _run("pass")
        mock_docker.assert_called_once_with("pass")

    def test_dispatches_to_local_when_no_docker(self):
        local_result = {"stdout": "", "stderr": "", "exit_code": 0}
        with patch("backend.executor.shutil.which", return_value=None), \
             patch("backend.executor._local_run", return_value=local_result) as mock_local:
            _run("pass")
        mock_local.assert_called_once_with("pass")
