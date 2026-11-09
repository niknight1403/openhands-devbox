"""Offline-Tests für den Free Route Hunter (keine Netzwerkaufrufe)."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import free_route_hunter as hunter  # noqa: E402

OPENROUTER_PAYLOAD = {
    "data": [
        {
            "id": "qwen/qwen3-coder:free",
            "context_length": 262144,
            "pricing": {"prompt": "0", "completion": "0"},
            "supported_parameters": ["tools", "temperature"],
        },
        {
            "id": "meta/llama-tiny-apex:free",
            "context_length": 8192,
            "pricing": {"prompt": "0", "completion": "0"},
            "supported_parameters": ["temperature"],
        },
        {
            "id": "openai/gpt-4o-mini",
            "context_length": 128000,
            "pricing": {"prompt": "0.00000015", "completion": "0.0000006"},
            "supported_parameters": ["tools"],
        },
        {
            "id": "deepseek/deepseek-chat-v3:free",
            "context_length": 64000,
            "pricing": {"prompt": "0.0", "completion": "0.0"},
            "supported_parameters": ["tools"],
        },
        {
            "id": "legacy/free-without-pricing:free",
            "context_length": 32000,
        },
    ]
}


def fake_discovery(models: list[hunter.ModelInfo] | None = None):
    calls: list[str] = []

    def discover(timeout: float, env: dict[str, str]):
        calls.append(env.get("PROBE", ""))
        return list(models if models is not None else [])

    discover.calls = calls  # type: ignore[attr-defined]
    return discover


def fake_ping(ok: dict[str, bool], seen: list[str] | None = None):
    def ping(provider, model, api_key, timeout=hunter.DEFAULT_TIMEOUT):
        if seen is not None:
            seen.append(f"{provider.name}:{model}")
        if ok.get(f"{provider.name}:{model}"):
            return hunter.RouteCheck(True, 200, 123)
        return hunter.RouteCheck(False, 429, 50)

    return ping


class PriceTests(unittest.TestCase):
    def test_zero_prices(self):
        self.assertTrue(hunter._price_is_zero("0"))
        self.assertTrue(hunter._price_is_zero("0.0"))
        self.assertTrue(hunter._price_is_zero(0))
        self.assertFalse(hunter._price_is_zero("0.0000001"))
        self.assertFalse(hunter._price_is_zero(None))
        self.assertFalse(hunter._price_is_zero(True))


class DiscoveryTests(unittest.TestCase):
    def test_only_free_models_with_context(self):
        models = hunter.parse_openrouter_free_models(OPENROUTER_PAYLOAD)
        ids = [info.model for info in models]
        self.assertIn("qwen/qwen3-coder:free", ids)
        self.assertIn("deepseek/deepseek-chat-v3:free", ids)
        # zu klein
        self.assertNotIn("meta/llama-tiny-apex:free", ids)
        # kostenpflichtig
        self.assertNotIn("openai/gpt-4o-mini", ids)
        # ohne Preisangabe nicht als gratis gewertet, obwohl :free im Namen steht
        self.assertNotIn("legacy/free-without-pricing:free", ids)

    def test_tool_support_is_detected(self):
        models = {info.model: info for info in hunter.parse_openrouter_free_models(OPENROUTER_PAYLOAD)}
        self.assertTrue(models["qwen/qwen3-coder:free"].supports_tools)
        self.assertTrue(models["deepseek/deepseek-chat-v3:free"].supports_tools)

    def test_empty_payloads(self):
        self.assertEqual(hunter.parse_openrouter_free_models(None), [])
        self.assertEqual(hunter.parse_openrouter_free_models({"data": "kaputt"}), [])
        self.assertEqual(hunter.parse_openrouter_free_models({"data": [None, 42]}), [])


class RankingTests(unittest.TestCase):
    def test_coder_model_wins(self):
        coder = hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free", 262144, True)
        generic = hunter.ModelInfo("openrouter", "meta/llama-4-maverick:free", 128000, True)
        self.assertEqual(hunter.rank_candidates([generic, coder])[0], coder)

    def test_small_model_loses(self):
        big = hunter.ModelInfo("openrouter", "deepseek/deepseek-v3:free", 64000, True)
        small = hunter.ModelInfo("openrouter", "google/gemini-flash-lite:free", 128000, True)
        self.assertEqual(hunter.rank_candidates([small, big])[0], big)

    def test_large_model_beats_generic_peer(self):
        ultra = hunter.ModelInfo("openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free", 1_000_000, True)
        note = hunter.ModelInfo("openrouter", "dots-studio/dots-3-note-preview:free", 512_000, True)
        self.assertEqual(hunter.rank_candidates([note, ultra])[0], ultra)

    def test_tool_support_outranks_code_hint(self):
        with_tools = hunter.ModelInfo("openrouter", "vendor/generic:free", 128_000, True)
        without_tools = hunter.ModelInfo("openrouter", "vendor/coder:free", 128_000, False)
        self.assertEqual(hunter.rank_candidates([without_tools, with_tools])[0], with_tools)

    def test_provider_priority_and_paid_last(self):
        openrouter = hunter.ModelInfo("openrouter", "some/model:free", 64000, True)
        groq = hunter.ModelInfo("groq", "llama-3.3-70b-versatile")
        paid = hunter.ModelInfo("openai", "gpt-4o-mini")
        ordered = hunter.rank_candidates([paid, groq, openrouter])
        self.assertEqual([info.provider for info in ordered], ["openrouter", "groq", "openai"])

    def test_rank_is_deterministic_and_deduplicates(self):
        first = hunter.ModelInfo("openrouter", "b/model:free", 64000, True)
        second = hunter.ModelInfo("openrouter", "a/model:free", 64000, True)
        ordered = hunter.rank_candidates([first, second, first])
        self.assertEqual(len(ordered), 2)
        self.assertEqual(hunter.rank_candidates([first, second]), hunter.rank_candidates([second, first]))


class ForcedModelTests(unittest.TestCase):
    def test_litellm_prefix_is_stripped(self):
        self.assertEqual(
            hunter.forced_candidates("openrouter/qwen/qwen3-coder:free"),
            [hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free")],
        )

    def test_provider_name_prefix(self):
        self.assertEqual(hunter.forced_candidates("groq/llama-3.3-70b-versatile")[0].provider, "groq")

    def test_openai_prefix(self):
        self.assertEqual(hunter.forced_candidates("openai/gpt-4o-mini")[0].provider, "openai")

    def test_bare_model_defaults_to_openrouter(self):
        self.assertEqual(hunter.forced_candidates("qwen/qwen3-coder:free")[0].provider, "openrouter")

    def test_empty_input(self):
        self.assertEqual(hunter.forced_candidates("   "), [])


class CandidateBuildingTests(unittest.TestCase):
    def test_only_providers_with_keys(self):
        env = {"OPENROUTER_API_KEY": "key-1", "GROQ_API_KEY": "key-2"}
        discover = fake_discovery([hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free", 262144, True)])
        candidates = hunter.build_candidates(env, discover=discover)
        # Pollinations bleibt schlüsselfrei am Ende der Kaskade.
        self.assertEqual({info.provider for info in candidates}, {"openrouter", "groq", "pollinations"})
        self.assertEqual(len(discover.calls), 1)  # nur OpenRouter wird dynamisch geladen

    def test_without_any_key_only_keyfree_route_remains(self):
        candidates = hunter.build_candidates({}, discover=fake_discovery([]))
        self.assertEqual([info.provider for info in candidates], ["pollinations"])

    def test_paid_provider_is_excluded_by_default_and_opt_in_works(self):
        env = {"OPENAI_API_KEY": "key-1"}
        self.assertEqual(hunter.build_candidates(env, discover=fake_discovery([]))[0].provider, "pollinations")
        with_paid = hunter.build_candidates(env, discover=fake_discovery([]), include_paid=True)
        self.assertIn("openai", [info.provider for info in with_paid])

    def test_max_per_provider_limits_candidates(self):
        many = [hunter.ModelInfo("openrouter", f"vendor/model-{index}:free", 64000, True) for index in range(9)]
        candidates = hunter.build_candidates({"OPENROUTER_API_KEY": "k"}, discover=fake_discovery(many), max_per_provider=3)
        self.assertEqual(len([info for info in candidates if info.provider == "openrouter"]), 3)

    def test_forced_model_skips_the_rest(self):
        env = {"MODEL_INPUT": "groq/llama-3.3-70b-versatile", "OPENROUTER_API_KEY": "k", "GROQ_API_KEY": "g"}
        candidates = hunter.build_candidates(env, discover=fake_discovery([]))
        self.assertEqual(candidates, [hunter.ModelInfo("groq", "llama-3.3-70b-versatile")])

    def test_preference_reorders_providers(self):
        env = {"OPENROUTER_API_KEY": "k", "GROQ_API_KEY": "g", "HUNTER_PREFER": "groq,openrouter"}
        discover = fake_discovery([hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free", 262144, True)])
        candidates = hunter.build_candidates(env, discover=discover)
        self.assertEqual(candidates[0].provider, "groq")


class AutopilotHintTests(unittest.TestCase):
    def write_status(self, folder, routes):
        path = os.path.join(folder, "status.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"generated_at": "2026-01-01T00:00:00+00:00", "routes": routes}, handle)
        return path

    def test_exclude_removes_route(self):
        env = {"OPENROUTER_API_KEY": "k", "HUNTER_EXCLUDE": "openrouter:qwen/qwen3-coder:free"}
        models = [hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free", 262144, True)]
        candidates = hunter.build_candidates(env, discover=fake_discovery(models))
        self.assertNotIn("qwen/qwen3-coder:free", [info.model for info in candidates])

    def test_status_hints_bring_models_into_the_hunt(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_status(
                folder,
                [
                    {"provider": "openrouter", "model": "weak/model:free", "chat_ok": True, "tools_ok": False},
                    {"provider": "openrouter", "model": "tool/model:free", "chat_ok": True, "tools_ok": True},
                    {"provider": "gemini", "model": "gemini-2.5-flash", "chat_ok": True, "tools_ok": True},
                ],
            )
            env = {"OPENROUTER_API_KEY": "k", "HUNTER_STATUS_FILE": path}
            discover = fake_discovery([hunter.ModelInfo("openrouter", "native/model:free", 262144, True)])
            labels = [info.label for info in hunter.build_candidates(env, discover=discover)]
        # Hinweise bringen ihre Modelle mit, die Werkzeugeignung wird übernommen;
        # gemini fehlt der Schlüssel und bleibt draußen.
        self.assertIn("openrouter:tool/model:free", labels)
        self.assertIn("openrouter:weak/model:free", labels)
        self.assertNotIn("gemini:gemini-2.5-flash", labels)
        self.assertLess(
            labels.index("openrouter:tool/model:free"),
            labels.index("openrouter:weak/model:free"),
        )

    def test_hints_promote_no_keyless_route(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.write_status(
                folder,
                [
                    {"provider": "pollinations", "model": "openai", "chat_ok": True, "tools_ok": True},
                    {"provider": "openrouter", "model": "qwen/qwen3-coder:free", "chat_ok": True, "tools_ok": True},
                ],
            )
            env = {"OPENROUTER_API_KEY": "k", "HUNTER_STATUS_FILE": path}
            discover = fake_discovery([hunter.ModelInfo("openrouter", "native/model:free", 262144, True)])
            labels = [info.label for info in hunter.build_candidates(env, discover=discover)]
        # Eine schlüsselfreie Route darf trotz Hinweis nicht vor eine echte rutschen.
        self.assertNotEqual(labels[0], "pollinations:openai")
        self.assertEqual(labels[-1], "pollinations:openai")

    def test_missing_status_file_is_no_error(self):
        env = {"OPENROUTER_API_KEY": "k", "HUNTER_STATUS_FILE": "/tmp/gibt-es-nicht-xyz.json"}
        candidates = hunter.build_candidates(env, discover=fake_discovery([hunter.ModelInfo("openrouter", "a:free", 64000, True)]))
        self.assertTrue(candidates)

    def test_shell_export_is_sourceable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "route.env")
            hunter.write_env(
                {"LLM_MODEL": "openrouter/a:free", "LLM_ROUTE_NAME": "weird name", "LLM_API_KEY": "sk-test+1/2="},
                path,
                shell=True,
            )
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
        self.assertIn("export LLM_MODEL=openrouter/a:free", content)
        # Werte mit Leerzeichen werden zitiert, einfache Werte bleiben schlank
        self.assertIn("export LLM_ROUTE_NAME='weird name'", content)
        self.assertIn("export LLM_API_KEY=sk-test+1/2=", content)


class HuntTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            hunter.ModelInfo("openrouter", "a/coder-1:free", 64000, True),
            hunter.ModelInfo("openrouter", "b/coder-2:free", 64000, True),
            hunter.ModelInfo("groq", "llama-3.3-70b-versatile"),
        ]
        self.env = {"OPENROUTER_API_KEY": "k", "GROQ_API_KEY": "g"}

    def test_first_answering_route_wins(self):
        checks: list[dict] = []
        ping = fake_ping({"groq:llama-3.3-70b-versatile": True})
        chosen, result = hunter.hunt(self.candidates, self.env, ping=ping, report=checks)
        self.assertEqual(chosen.provider, "groq")
        self.assertTrue(result.ok)
        self.assertEqual(len(checks), 3)

    def test_stops_after_first_batch(self):
        seen: list[str] = []
        ping = fake_ping({}, seen=seen)
        hunter.hunt(self.candidates, self.env, ping=ping, batch_size=1)
        self.assertEqual(len(seen), 3)

    def test_no_route_returns_none(self):
        chosen, result = hunter.hunt(self.candidates, self.env, ping=fake_ping({}))
        self.assertIsNone(chosen)
        self.assertIsNone(result)


class EnvAndReportTests(unittest.TestCase):
    def setUp(self):
        self.info = hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free", 262144, True)

    def test_route_env_uses_litellm_prefix(self):
        values = hunter.route_env(self.info, "secret-key")
        self.assertEqual(values["LLM_MODEL"], "openrouter/qwen/qwen3-coder:free")
        self.assertEqual(values["LLM_BASE_URL"], "https://openrouter.ai/api/v1")
        self.assertEqual(values["LLM_API_KEY"], "secret-key")
        self.assertEqual(values["LLM_ROUTE_PROVIDER"], "openrouter")

    def test_keyfree_route_gets_placeholder(self):
        values = hunter.route_env(hunter.ModelInfo("pollinations", "openai"), "")
        self.assertEqual(values["LLM_API_KEY"], hunter.ANONYMOUS_KEY)

    def test_write_env_appends(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "env")
            hunter.write_env({"LLM_MODEL": "x"}, path)
            hunter.write_env({"LLM_API_KEY": "y"}, path)
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "LLM_MODEL=x\nLLM_API_KEY=y\n")

    def test_write_env_without_path_is_noop(self):
        hunter.write_env({"LLM_MODEL": "x"}, None)

    def test_report_contains_no_credentials(self):
        env = {"OPENROUTER_API_KEY": "super-secret-value", "GROQ_API_KEY": "second-secret"}
        checks = [{"provider": "openrouter", "model": "x", "ok": True, "status": 200, "latency_ms": 10}]
        report = hunter.build_report(self.info, hunter.RouteCheck(True, 200, 10), checks, env,
                                     hunter.available_providers(env))
        text = json.dumps(report)
        self.assertNotIn("super-secret-value", text)
        self.assertNotIn("second-secret", text)
        self.assertEqual(report["chosen"]["provider"], "openrouter")
        self.assertIn("gemini", report["providers_missing_key"])

    def test_summary_mentions_route(self):
        report = hunter.build_report(self.info, hunter.RouteCheck(True, 200, 10), [], {}, [])
        text = hunter.summary_markdown(report)
        self.assertIn("Free Route Hunter", text)
        self.assertIn("qwen/qwen3-coder:free", text)


class MainTests(unittest.TestCase):
    def run_main(self, argv, env, discover, ping):
        with tempfile.TemporaryDirectory() as folder:
            env = dict(env)
            env["GITHUB_ENV"] = os.path.join(folder, "github_env")
            env["GITHUB_STEP_SUMMARY"] = os.path.join(folder, "summary.md")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = hunter.main(argv, env=env, discover=discover, ping=ping)
            output = buffer.getvalue()
            written = {}
            if os.path.exists(env["GITHUB_ENV"]):
                with open(env["GITHUB_ENV"], encoding="utf-8") as handle:
                    for line in handle:
                        key, _, value = line.partition("=")
                        written[key] = value.strip()
            summary = ""
            if os.path.exists(env["GITHUB_STEP_SUMMARY"]):
                with open(env["GITHUB_STEP_SUMMARY"], encoding="utf-8") as handle:
                    summary = handle.read()
            return code, output, written, summary

    def test_no_candidates_exits_with_3(self):
        code, _output, written, _ = self.run_main([], {"HUNTER_ALLOW_PAID": ""}, fake_discovery([]), fake_ping({}))
        # Pollinations bleibt als schlüsselfreie Reserve übrig; ohne Erreichbarkeit greift Exit 4.
        self.assertEqual(code, 4)
        self.assertEqual(written, {})

    def test_success_writes_route_and_never_leaks_key(self):
        models = [hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free", 262144, True)]
        env = {"OPENROUTER_API_KEY": "top-secret"}
        code, output, written, summary = self.run_main(
            ["--summary"], env, fake_discovery(models), fake_ping({"openrouter:qwen/qwen3-coder:free": True})
        )
        self.assertEqual(code, 0)
        self.assertEqual(written["LLM_MODEL"], "openrouter/qwen/qwen3-coder:free")
        self.assertEqual(written["LLM_API_KEY"], "top-secret")
        self.assertNotIn("top-secret", output)
        self.assertIn("Free Route Hunter", summary)

    def test_report_file_is_written(self):
        models = [hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free", 262144, True)]
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "report.json")
            code = hunter.main(
                ["--report", path],
                env={"OPENROUTER_API_KEY": "geheim"},
                discover=fake_discovery(models),
                ping=fake_ping({"openrouter:qwen/qwen3-coder:free": True}),
            )
            self.assertEqual(code, 0)
            with open(path, encoding="utf-8") as handle:
                report = json.load(handle)
            self.assertEqual(report["chosen"]["litellm_model"], "openrouter/qwen/qwen3-coder:free")
            self.assertNotIn("geheim", json.dumps(report))

    def test_list_mode_does_not_ping(self):
        models = [hunter.ModelInfo("openrouter", "qwen/qwen3-coder:free", 262144, True)]
        seen: list[str] = []
        code = hunter.main(
            ["--list"],
            env={"OPENROUTER_API_KEY": "k"},
            discover=fake_discovery(models),
            ping=fake_ping({}, seen=seen),
        )
        self.assertEqual(code, 0)
        self.assertEqual(seen, [])

    def test_forced_model_is_used(self):
        code, _, written, _ = self.run_main(
            ["--model", "groq/llama-3.3-70b-versatile"],
            {"GROQ_API_KEY": "g"},
            fake_discovery([]),
            fake_ping({"groq:llama-3.3-70b-versatile": True}),
        )
        self.assertEqual(code, 0)
        self.assertEqual(written["LLM_MODEL"], "openai/llama-3.3-70b-versatile")


if __name__ == "__main__":
    unittest.main()
