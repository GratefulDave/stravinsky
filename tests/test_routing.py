"""Tests for routing module."""

import json
import tempfile
import threading
import time
from pathlib import Path

from mcp_bridge.routing import get_provider_tracker
from mcp_bridge.routing.config import (
    FallbackConfig,
    TaskRoutingRule,
    load_routing_config,
)
from mcp_bridge.routing.task_classifier import TaskType, classify_task, get_routing_for_task


class TestProviderStateTracking:
    def test_initial_state_all_available(self) -> None:
        tracker = get_provider_tracker()
        assert tracker.is_available("claude")
        assert tracker.is_available("openai")
        assert tracker.is_available("gemini")

    def test_mark_rate_limited(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("openai", duration=2)
        assert not tracker.is_available("openai")
        assert tracker.is_available("claude")
        assert tracker.is_available("gemini")

    def test_cooldown_expiration(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("gemini", duration=2)
        assert not tracker.is_available("gemini")
        time.sleep(2.5)
        assert tracker.is_available("gemini")

    def test_get_status(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("claude", duration=5)
        status = tracker.get_status()
        assert "claude" in status
        assert "openai" in status
        assert "gemini" in status
        assert status["claude"]["availability"] == "rate_limited"
        assert "cooldown_remaining" in status["claude"]
        assert status["claude"]["cooldown_remaining"] > 0

    def test_get_fallback_provider(self) -> None:
        tracker = get_provider_tracker()
        fallback = tracker.get_fallback_provider("claude")
        assert fallback in ["claude", "openai", "gemini"]
        tracker.mark_rate_limited("openai", duration=5)
        fallback = tracker.get_fallback_provider("openai")
        assert fallback != "openai"
        assert fallback in ["claude", "gemini"]

    def test_mark_success(self) -> None:
        tracker = get_provider_tracker()
        for _ in range(5):
            tracker.mark_success("openai")
        status = tracker.get_status()
        assert status["openai"]["total_requests"] >= 5
        assert status["openai"]["total_failures"] == 0

    def test_mark_error(self) -> None:
        tracker = get_provider_tracker()
        for _ in range(3):
            tracker.mark_error("gemini", "test error")
        status = tracker.get_status()
        assert status["gemini"]["total_failures"] >= 3


class TestTaskClassification:
    def test_code_generation_detection(self) -> None:
        prompts = [
            "implement a login feature",
            "create a new API endpoint",
            "write a function to parse JSON",
            "build a user registration system",
        ]
        for prompt in prompts:
            task_type = classify_task(prompt)
            assert task_type == TaskType.CODE_GENERATION, f"Failed for: {prompt}"

    def test_debugging_detection(self) -> None:
        prompts = [
            "fix the authentication bug",
            "debug the memory leak",
            "why is this crashing?",
            "troubleshoot the API error",
        ]
        for prompt in prompts:
            task_type = classify_task(prompt)
            assert task_type == TaskType.DEBUGGING, f"Failed for: {prompt}"

    def test_documentation_detection(self) -> None:
        prompts = [
            "write docs for the API",
            "document this function",
            "create a README",
            "add comments to explain this code",
        ]
        for prompt in prompts:
            task_type = classify_task(prompt)
            assert task_type == TaskType.DOCUMENTATION, f"Failed for: {prompt}"

    def test_refactoring_detection(self) -> None:
        prompts = [
            "refactor this code to use classes",
            "clean up the messy functions",
            "improve the code structure",
            "optimize this algorithm",
        ]
        for prompt in prompts:
            task_type = classify_task(prompt)
            assert task_type == TaskType.CODE_REFACTORING, f"Failed for: {prompt}"

    def test_general_fallback(self) -> None:
        prompts = ["hello", "what time is it?", "random question"]
        for prompt in prompts:
            task_type = classify_task(prompt)
            assert task_type == TaskType.GENERAL, f"Failed for: {prompt}"

    def test_get_routing_for_task(self) -> None:
        provider, model = get_routing_for_task(TaskType.CODE_GENERATION)
        assert isinstance(provider, str)
        assert provider in ["claude", "openai", "gemini"]


class TestConfigLoading:
    def test_load_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_routing_config(tmpdir)
            assert isinstance(config.task_routing, dict)
            assert "code_generation" in config.task_routing
            assert "debugging" in config.task_routing
            assert config.fallback.enabled is True
            assert config.fallback.cooldown_seconds == 300

    def test_load_project_config_overrides_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            stravinsky_dir = project_path / ".stravinsky"
            stravinsky_dir.mkdir()
            config_file = stravinsky_dir / "routing.json"
            custom_config = {
                "routing": {
                    "task_routing": {
                        "code_generation": {"provider": "gemini", "model": "gemini-custom-model"}
                    },
                    "fallback": {"enabled": False, "cooldown_seconds": 600},
                }
            }
            config_file.write_text(json.dumps(custom_config))
            config = load_routing_config(str(project_path))
            code_gen = config.task_routing.get("code_generation")
            assert code_gen is not None
            assert code_gen.provider == "gemini"
            assert code_gen.model == "gemini-custom-model"
            assert config.fallback.enabled is False
            assert config.fallback.cooldown_seconds == 600

    def test_config_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_routing_config(tmpdir)
            assert isinstance(config.task_routing, dict)
            for task_name, rule in config.task_routing.items():
                assert isinstance(task_name, str)
                assert isinstance(rule, TaskRoutingRule)
                assert isinstance(rule.provider, str)
            assert isinstance(config.fallback, FallbackConfig)
            assert isinstance(config.fallback.enabled, bool)
            assert isinstance(config.fallback.chain, list)
            assert isinstance(config.fallback.cooldown_seconds, int)


class TestFallbackChain:
    def test_fallback_chain_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_routing_config(tmpdir)
            chain = config.fallback.chain
            assert len(chain) == 3
            assert "claude" in chain
            assert "openai" in chain
            assert "gemini" in chain

    def test_fallback_with_multiple_unavailable(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("claude", duration=5)
        tracker.mark_rate_limited("openai", duration=5)
        fallback = tracker.get_fallback_provider("claude")
        assert fallback == "gemini"

    def test_fallback_returns_preferred_when_all_unavailable(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("claude", duration=5)
        tracker.mark_rate_limited("openai", duration=5)
        tracker.mark_rate_limited("gemini", duration=5)
        fallback = tracker.get_fallback_provider("claude")
        assert fallback == "claude"


class TestThreadSafety:
    def test_concurrent_mark_rate_limited(self) -> None:
        tracker = get_provider_tracker()

        def mark_limited() -> None:
            for _ in range(50):
                tracker.mark_rate_limited("test_provider", duration=1)

        threads = [threading.Thread(target=mark_limited) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        status = tracker.get_status()
        assert "test_provider" in status
        assert status["test_provider"]["availability"] == "rate_limited"

    def test_concurrent_mark_success_error(self) -> None:
        tracker = get_provider_tracker()

        def mark_successes() -> None:
            for _ in range(100):
                tracker.mark_success("concurrent_test")

        def mark_errors() -> None:
            for _ in range(50):
                tracker.mark_error("concurrent_test", "test error")

        success_threads = [threading.Thread(target=mark_successes) for _ in range(3)]
        error_threads = [threading.Thread(target=mark_errors) for _ in range(2)]
        all_threads = success_threads + error_threads
        for t in all_threads:
            t.start()
        for t in all_threads:
            t.join()
        status = tracker.get_status()
        assert "concurrent_test" in status
        assert status["concurrent_test"]["total_requests"] >= 300
        assert status["concurrent_test"]["total_failures"] >= 100

    def test_concurrent_is_available_checks(self) -> None:
        tracker = get_provider_tracker()
        results: list[bool] = []
        lock = threading.Lock()

        def check_availability() -> None:
            for _ in range(100):
                available = tracker.is_available("check_test")
                with lock:
                    results.append(available)

        threads = [threading.Thread(target=check_availability) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 500
        assert all(results)


class TestEdgeCases:
    def test_unknown_provider(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("unknown_provider", duration=5)
        is_available = tracker.is_available("unknown_provider")
        assert not is_available

    def test_zero_cooldown(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("zero_test", duration=0)
        assert tracker.is_available("zero_test")

    def test_negative_cooldown(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("negative_test", duration=-1)
        assert tracker.is_available("negative_test")

    def test_very_long_cooldown(self) -> None:
        tracker = get_provider_tracker()
        tracker.mark_rate_limited("long_test", duration=3600)
        assert not tracker.is_available("long_test")
        time.sleep(1)
        assert not tracker.is_available("long_test")
