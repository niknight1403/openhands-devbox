"""Tests für die lokale Offline-Route (keine Netzwerkaufrufe)."""
from __future__ import annotations

import io
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import free_route_hunter as hunter  # noqa: E402
import llm_autopilot as autopilot  # noqa: E402
import local_llm_router as router  # noqa: E402

LOCAL_ENV = {
    "LLM_OFFLINE": "1",
    "LOCAL_LLM_BASE_URL": "http://127.0.0.1:11434/v1",
    "LOCAL_LLM_MODEL": "qwen2.5-coder:7b",
    "LOCAL_LLM_LITELLM_PREFIX": "openai/",
    "LOCAL_LLM_API_KEY": "local-dummy-key",
}


def _write_config(directory: Path, text: str) -> Path:
    config = directory / "local-llm.env"
    config.write_text(text, encoding="utf-8")
    return config


def _probe_stub(status=200, tool_call=True):
    """Ersetzt den HTTP-Aufruf: Modellliste, Chat und Werkzeugaufruf."""

    def call(method: str, url: str, payload: dict | None = None, api_key: str = "", timeout: float = 20.0):
        if url.endswith("/models"):
            return router.HttpResult(200, {"data": [{"id": "qwen2.5-coder:7b"}]})
        if payload and payload.get("tools"):
            message = {"tool_calls": [{"id": "1", "type": "function", "function": {"name": "list_files", "arguments": "{}"}}]}
            return router.HttpResult(status, {"choices": [{"message": message}]})
        return router.HttpResult(status, {"choices": [{"message": {"content": "OK"}}]})

    return call


def _failing_stub(detail="connection refused"):
    return lambda method, url, payload=None, api_key="", timeout=20.0: router.HttpResult("error", None, detail)


class LocalRouteConfigTests(unittest.TestCase):
    def test_defaults_are_local_only(self) -> None:
        route = router.load_config({}, config_path=Path("/nonexistent/local-llm.env"))
        self.assertTrue(route.offline)
        self.assertTrue(route.strict)
        self.assertEqual(route.base_url, "http://host.docker.internal:11434/v1")
        self.assertEqual(route.model_string, "openai/qwen2.5-coder:7b")
        self.assertEqual(route.api_key, "local-dummy-key")

    def test_config_file_values_are_used(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = _write_config(
                Path(temp),
                "# Kommentar\nLOCAL_LLM_BASE_URL=http://127.0.0.1:4000/v1\nLOCAL_LLM_MODEL=llama3.2:3b\n"
                "LOCAL_LLM_LITELLM_PREFIX=ollama_chat/\nLLM_OFFLINE=0\n",
            )
            route = router.load_config({}, config_path=config)
            self.assertEqual(route.base_url, "http://127.0.0.1:4000/v1")
            self.assertEqual(route.model_string, "ollama_chat/llama3.2:3b")
            self.assertFalse(route.offline)

    def test_empty_prefix_yields_bare_model(self) -> None:
        route = router.load_config(
            {"LOCAL_LLM_LITELLM_PREFIX": ""}, config_path=Path("/nonexistent")
        )
        self.assertEqual(route.model_string, "qwen2.5-coder:7b")

    def test_environment_overrides_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = _write_config(Path(temp), "LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1\n")
            route = router.load_config({"LOCAL_LLM_BASE_URL": "http://10.0.0.9:11434/v1/"}, config_path=config)
            self.assertEqual(route.base_url, "http://10.0.0.9:11434/v1")

    def test_offline_flag_parsing(self) -> None:
        for value in ("1", "true", "YES", "on"):
            self.assertTrue(router.offline_requested({"LLM_OFFLINE": value}))
        for value in ("0", "false", "", "nein"):
            self.assertFalse(router.offline_requested({"LLM_OFFLINE": value}))


class LocalHostTests(unittest.TestCase):
    def test_local_hosts_are_accepted(self) -> None:
        for url in (
            "http://host.docker.internal:11434/v1",
            "http://127.0.0.1:4000/v1",
            "http://localhost:11434/v1",
            "http://[::1]:11434/v1",
            "http://192.168.1.20:11434/v1",
            "http://10.0.0.5:11434/v1",
            "http://172.17.0.2:11434/v1",
        ):
            self.assertTrue(router.is_local_endpoint(url), url)

    def test_public_endpoints_are_rejected(self) -> None:
        for url in (
            "https://api.openai.com/v1",
            "https://openrouter.ai/api/v1",
            "http://example.com/v1",
            "ftp://127.0.0.1/models",
            "http://user:pass@127.0.0.1:11434/v1",
            "",
        ):
            self.assertFalse(router.is_local_endpoint(url), url)

    def test_strict_rejects_remote_endpoint(self) -> None:
        route = router.LocalRoute(base_url="https://api.openai.com/v1", model="gpt-4o-mini")
        with self.assertRaises(ValueError):
            router.validate(route)

    def test_non_strict_allows_remote_endpoint(self) -> None:
        route = router.LocalRoute(base_url="https://api.openai.com/v1", model="gpt-4o-mini", strict=False)
        router.validate(route)

    def test_missing_model_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            router.validate(router.LocalRoute(base_url="http://127.0.0.1:11434/v1", model=""))


class RouteValuesTests(unittest.TestCase):
    def test_route_values_cover_every_llm_variable(self) -> None:
        route = router.load_config(LOCAL_ENV, config_path=Path("/nonexistent"))
        values = router.route_values(route)
        self.assertEqual(
            set(values),
            {"LLM_OFFLINE", "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_ROUTE_NAME", "LLM_ROUTE_PROVIDER"},
        )
        self.assertEqual(values["LLM_MODEL"], "openai/qwen2.5-coder:7b")
        self.assertEqual(values["LLM_BASE_URL"], "http://127.0.0.1:11434/v1")
        self.assertEqual(values["LLM_API_KEY"], "local-dummy-key")
        self.assertEqual(values["LLM_ROUTE_PROVIDER"], "local")
        self.assertEqual(values["LLM_OFFLINE"], "1")

    def test_write_is_idempotent_and_keeps_other_keys(self) -> None:
        route = router.load_config(LOCAL_ENV, config_path=Path("/nonexistent"))
        with tempfile.TemporaryDirectory() as temp:
            env_file = Path(temp) / ".env"
            env_file.write_text("LOCAL_BACKEND_API_KEY=abc\nLLM_MODEL=openrouter/alt\nLLM_BASE_URL=https://cloud/v1\n")
            router.write_route_env(env_file, route)
            router.write_route_env(env_file, route)
            lines = env_file.read_text().splitlines()
            self.assertIn("LOCAL_BACKEND_API_KEY=abc", lines)
            self.assertEqual(sum(1 for line in lines if line.startswith("LLM_MODEL=")), 1)
            self.assertEqual(sum(1 for line in lines if line.startswith("LLM_BASE_URL=")), 1)
            self.assertIn("LLM_MODEL=openai/qwen2.5-coder:7b", lines)
            self.assertNotIn("LLM_MODEL=openrouter/alt", lines)
            self.assertNotIn("LLM_BASE_URL=https://cloud/v1", lines)
            self.assertEqual(stat.S_IMODE(env_file.stat().st_mode), 0o600)

    def test_shell_export_masks_key(self) -> None:
        route = router.load_config(LOCAL_ENV, config_path=Path("/nonexistent"))
        lines = router.shell_export(route)
        key_line = next(line for line in lines if "LLM_API_KEY" in line)
        self.assertNotIn("local-dummy-key", key_line)
        self.assertTrue(key_line.startswith("export LLM_API_KEY="))


class ProbeTests(unittest.TestCase):
    def test_probe_reports_reachable_route(self) -> None:
        route = router.load_config(LOCAL_ENV, config_path=Path("/nonexistent"))
        probe = router.check_route(route, call=_probe_stub())
        self.assertTrue(probe.ok)
        self.assertTrue(probe.models_ok)
        self.assertTrue(probe.model_listed)
        self.assertTrue(probe.tools_ok)

    def test_probe_reports_unreachable_route(self) -> None:
        route = router.load_config(LOCAL_ENV, config_path=Path("/nonexistent"))
        probe = router.check_route(route, call=_failing_stub())
        self.assertFalse(probe.ok)
        self.assertFalse(probe.models_ok)
        self.assertTrue(probe.error)

    def test_probe_can_skip_tools(self) -> None:
        route = router.load_config(LOCAL_ENV, config_path=Path("/nonexistent"))
        probe = router.check_route(route, call=_probe_stub(), probe_tools=False)
        self.assertTrue(probe.ok)
        self.assertFalse(probe.tools_ok)


class CliTests(unittest.TestCase):
    def test_apply_writes_local_route_and_prints_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env_file = Path(temp) / ".env"
            env_file.write_text("LOCAL_BACKEND_API_KEY=abc\n")
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                code = router.main(["--apply", "--env-file", str(env_file)], env=LOCAL_ENV)
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue().strip(), "local")
            text = env_file.read_text()
            self.assertIn("LLM_BASE_URL=http://127.0.0.1:11434/v1", text)
            self.assertIn("LLM_MODEL=openai/qwen2.5-coder:7b", text)
            self.assertIn("LOCAL_BACKEND_API_KEY=abc", text)

    def test_apply_in_cloud_mode_leaves_file_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env_file = Path(temp) / ".env"
            env_file.write_text("LOCAL_BACKEND_API_KEY=abc\n")
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                code = router.main(
                    ["--apply", "--env-file", str(env_file)], env={"LLM_OFFLINE": "0"}
                )
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue().strip(), "cloud")
            self.assertEqual(env_file.read_text(), "LOCAL_BACKEND_API_KEY=abc\n")

    def test_check_returns_error_code_when_router_is_down(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = router.main(["--check"], env=LOCAL_ENV, call=_failing_stub())
        self.assertEqual(code, 5)
        self.assertIn("Kein Cloud-Fallback", err.getvalue())

    def test_json_output_contains_masked_key(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = router.main(["--json", "--check"], env=LOCAL_ENV, call=_probe_stub())
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["mode"], "local")
        self.assertNotEqual(payload["route"]["LLM_API_KEY"], "local-dummy-key")
        self.assertTrue(payload["probe"]["chat_ok"])

    def test_strict_config_error_returns_7(self) -> None:
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = router.main(["--apply"], env={"LOCAL_LLM_BASE_URL": "https://api.openai.com/v1"})
        self.assertEqual(code, 7)
        self.assertIn("nicht lokal", err.getvalue())


class HunterOfflineTests(unittest.TestCase):
    def test_offline_mode_never_hunts_cloud_routes(self) -> None:
        calls: list[str] = []

        def discover(timeout, env):
            calls.append("discover")
            return []

        pings: list[str] = []

        def ping(provider, model, api_key, timeout):
            pings.append(f"{provider.name}:{model}")
            return hunter.RouteCheck(True, 200, 12)

        with tempfile.TemporaryDirectory() as temp:
            env_file = Path(temp) / "route.env"
            out = io.StringIO()
            with redirect_stdout(out):
                code = hunter.main(
                    ["--env-file", str(env_file)],
                    env={**LOCAL_ENV, "LOCAL_LLM_CONFIG": str(Path(temp) / "missing.env")},
                    discover=discover,
                    ping=ping,
                )
            self.assertEqual(code, 0)
            self.assertEqual(calls, [])
            self.assertEqual(pings, ["local:qwen2.5-coder:7b"])
            values = router.read_env_file(env_file)
            self.assertEqual(values["LLM_BASE_URL"], "http://127.0.0.1:11434/v1")
            self.assertEqual(values["LLM_MODEL"], "openai/qwen2.5-coder:7b")
            self.assertEqual(values["LLM_OFFLINE"], "1")
            self.assertIn("Offline-Modus", out.getvalue())

    def test_offline_mode_fails_without_cloud_fallback(self) -> None:
        def ping(provider, model, api_key, timeout):
            return hunter.RouteCheck(False, "error", 3)

        with tempfile.TemporaryDirectory() as temp:
            env_file = Path(temp) / "route.env"
            with redirect_stdout(io.StringIO()) as out:
                code = hunter.main(
                    ["--env-file", str(env_file)],
                    env={**LOCAL_ENV, "LOCAL_LLM_CONFIG": str(Path(temp) / "missing.env")},
                    discover=lambda timeout, env: [],
                    ping=ping,
                )
            self.assertEqual(code, 5)
            self.assertFalse(env_file.exists())
            self.assertIn("Kein Cloud-Fallback", out.getvalue())

    def test_cloud_mode_keeps_original_behaviour(self) -> None:
        providers = hunter.available_providers({"OPENROUTER_API_KEY": "x"})
        self.assertIn("openrouter", [provider.name for provider in providers])


class AutopilotOfflineTests(unittest.TestCase):
    def test_catalog_accepts_local_http_route(self) -> None:
        warnings: list[str] = []
        payload = {
            "routes": [
                {
                    "name": "local-ollama",
                    "base_url": "http://host.docker.internal:11434/v1",
                    "models": ["qwen2.5-coder:7b"],
                }
            ]
        }
        routes = autopilot.parse_catalog(payload, origin="test", warnings=warnings)
        self.assertEqual(len(routes), 1)
        self.assertEqual(warnings, [])

    def test_catalog_still_rejects_public_http_route(self) -> None:
        warnings: list[str] = []
        routes = autopilot.parse_catalog(
            {"routes": [{"name": "unsicher", "base_url": "http://api.example.com/v1", "models": ["m"]}]},
            origin="test",
            warnings=warnings,
        )
        self.assertEqual(routes, [])
        self.assertTrue(warnings)

    def test_offline_run_probes_only_local_routes(self) -> None:
        probed: list[str] = []

        def post(url, payload, api_key, timeout):
            probed.append(url)
            return 200, {"choices": [{"message": {"content": "OK"}}]}, 5

        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / "catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "routes": [
                            {
                                "name": "local-ollama",
                                "base_url": "http://127.0.0.1:11434/v1",
                                "models": ["qwen2.5-coder:7b"],
                            },
                            {
                                "name": "cloud",
                                "base_url": "https://api.example.com/v1",
                                "models": ["gross"],
                            },
                        ]
                    }
                )
            )
            status = autopilot.run(
                {
                    "LLM_OFFLINE": "1",
                    "AUTOPILOT_CATALOG": str(catalog),
                    "AUTOPILOT_PACKS": str(Path(temp) / "packs.json"),
                    "OPENROUTER_API_KEY": "sollte-nicht-genutzt-werden",
                },
                post=post,
                fetch_json_fn=lambda *args, **kwargs: {},
                fetch_text_fn=lambda *args, **kwargs: "",
                install_dir=temp,
            )
            self.assertEqual(status["mode"], "local")
            self.assertTrue(probed)
            self.assertTrue(all("127.0.0.1" in url for url in probed), probed)
            self.assertEqual({route["provider"] for route in status["routes"]}, {"local-ollama"})


class BootstrapLocalRouteTests(unittest.TestCase):
    """Der Codespace-Start schreibt die lokale Route und jagt keine Cloud-Anbieter."""

    def test_bootstrap_applies_local_route_and_skips_hunter(self) -> None:
        import shutil
        import subprocess

        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "config").mkdir()
            (root / "bin").mkdir()
            shutil.copy2(source / "scripts" / "bootstrap-codespace.sh", root / "scripts")
            shutil.copy2(source / "scripts" / "local_llm_router.py", root / "scripts")
            shutil.copy2(source / "config" / "local-llm.env", root / "config")
            calls = root / "docker-calls.txt"
            docker = root / "bin" / "docker"
            docker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$DOCKER_CALLS"\n')
            docker.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{root / 'bin'}{os.pathsep}{env['PATH']}"
            env["DOCKER_CALLS"] = str(calls)
            env.pop("LLM_OFFLINE", None)
            env["LOCAL_LLM_CONFIG"] = str(root / "config" / "local-llm.env")

            result = subprocess.run(
                ["bash", str(root / "scripts" / "bootstrap-codespace.sh")],
                cwd=root,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
            values = router.read_env_file(root / ".env")
            self.assertEqual(values["LLM_MODEL"], "openai/qwen2.5-coder:7b")
            self.assertEqual(values["LLM_BASE_URL"], "http://host.docker.internal:11434/v1")
            self.assertEqual(values["LLM_OFFLINE"], "1")
            self.assertIn("Lokale Offline-Route aktiv", result.stdout)
            self.assertEqual(calls.read_text().splitlines(), ["compose up -d"])


if __name__ == "__main__":
    unittest.main()
