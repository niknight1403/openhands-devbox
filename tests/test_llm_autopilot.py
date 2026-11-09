"""Offline-Tests für den LLM-Autopilot (keine Netzwerkaufrufe)."""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import llm_autopilot as autopilot  # noqa: E402


def post_factory(answers: dict[tuple[str, str], tuple[int, object]]):
    """Baut einen fake POST: (base_url, modell) -> (status, payload)."""

    def post(url, payload, api_key, timeout):
        base = url.rsplit("/chat/completions", 1)[0]
        model = payload.get("model", "")
        status, body = answers.get((base, model), (404, None))
        return status, body, 42

    return post


CHAT_OK = {"choices": [{"message": {"content": "pong"}, "finish_reason": "stop"}]}
TOOL_OK = {"choices": [{"message": {"tool_calls": [{"id": "1", "type": "function"}]}, "finish_reason": "tool_calls"}]}
TOOL_TEXT_ONLY = {"choices": [{"message": {"content": "Berlin"}, "finish_reason": "stop"}]}


class CatalogTests(unittest.TestCase):
    def test_parses_values_and_defaults(self):
        routes = autopilot.parse_catalog(
            {
                "routes": [
                    {
                        "name": "unbekannt",
                        "base_url": "https://example.invalid/v1/",
                        "models": ["m1", " m2 "],
                        "key_envs": ["X_KEY"],
                    }
                ]
            },
            origin="test",
        )
        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(route.base_url, "https://example.invalid/v1")
        self.assertEqual(route.models, ("m1", "m2"))
        self.assertEqual(route.key_envs, ("X_KEY",))
        self.assertEqual(route.litellm_prefix, "openai/")
        self.assertEqual(route.origin, "test")

    def test_rejects_broken_entries(self):
        warnings: list[str] = []
        routes = autopilot.parse_catalog(
            {
                "routes": [
                    {"name": "ohne-modell", "base_url": "https://a.invalid/v1"},
                    {"name": "ohne-url", "models": ["m"]},
                    {"name": "ftp", "base_url": "ftp://a.invalid", "models": ["m"]},
                    "quatsch",
                ]
            },
            origin="test",
            warnings=warnings,
        )
        self.assertEqual(routes, [])
        self.assertEqual(len(warnings), 4)

    def test_missing_routes_field_warns(self):
        warnings: list[str] = []
        self.assertEqual(autopilot.parse_catalog({"routes": "nein"}, "test", warnings), [])
        self.assertTrue(warnings)

    def test_remote_catalog_failure_is_survivable(self):
        warnings: list[str] = []

        def broken(url, timeout, token=""):
            raise OSError("offline")

        routes = autopilot.load_remote_kataloge(["https://example.invalid/k.json"], broken, 5, warnings)
        self.assertEqual(routes, [])
        self.assertTrue(any("nicht erreichbar" in warning for warning in warnings))


class CandidateTests(unittest.TestCase):
    def test_skips_routes_without_required_key(self):
        routes = [
            autopilot.CatalogRoute("a", "https://a.invalid/v1", ("m1",), key_envs=("A_KEY",)),
            autopilot.CatalogRoute("b", "https://b.invalid/v1", ("m2",)),
        ]
        candidates, _ = autopilot.build_candidates(routes, {}, 10)
        self.assertEqual([(route.name, model) for route, model, _ in candidates], [("b", "m2")])

    def test_deduplicates_and_caps(self):
        routes = [
            autopilot.CatalogRoute("a", "https://a.invalid/v1", ("m1", "m1")),
            autopilot.CatalogRoute("a2", "https://a.invalid/v1", ("m1", "m2")),
        ]
        candidates, warnings = autopilot.build_candidates(routes, {}, 1)
        self.assertEqual(len(candidates), 1)
        self.assertTrue(any("gekappt" in warning for warning in warnings))


class ToolDetectionTests(unittest.TestCase):
    def test_has_tool_call_variants(self):
        self.assertTrue(autopilot.has_tool_call(TOOL_OK))
        self.assertFalse(autopilot.has_tool_call(TOOL_TEXT_ONLY))
        self.assertTrue(autopilot.has_tool_call({"choices": [{"message": {"tool_calls": [1]}}]}))
        self.assertTrue(autopilot.has_tool_call({"choices": [{"message": {"function_call": {"name": "x"}}}]}))
        self.assertFalse(autopilot.has_tool_call(None))
        self.assertFalse(autopilot.has_tool_call({"choices": []}))

    def test_probe_all_marks_tool_ready_route(self):
        route = autopilot.CatalogRoute("openrouter", "https://or.invalid/v1", ("coder:free",), key_envs=("K",))
        post = post_factory(
            {
                ("https://or.invalid/v1", "coder:free"): (200, CHAT_OK),
                ("https://or.invalid/v1", "coder:free"): (200, TOOL_OK),
            }
        )
        results = autopilot.probe_all([(route, "coder:free", "key")], 5, post=post)
        self.assertTrue(results[0]["chat_ok"])
        self.assertTrue(results[0]["tools_ok"])

    def test_tool_probe_only_runs_for_answering_routes(self):
        calls: list[dict] = []

        def post(url, payload, api_key, timeout):
            calls.append(payload)
            return 401, None, 5

        route = autopilot.CatalogRoute("gemini", "https://g.invalid/v1", ("flash",), key_envs=("K",))
        results = autopilot.probe_all([(route, "flash", "key")], 5, post=post)
        self.assertFalse(results[0]["chat_ok"])
        self.assertFalse(results[0]["tools_ok"])
        self.assertEqual(len(calls), 1)

    def test_rank_prefers_tool_route(self):
        ranked = autopilot.rank_probes(
            [
                {"provider": "a", "model": "x", "chat_ok": True, "tools_ok": False, "latency_ms": 10},
                {"provider": "b", "model": "y", "chat_ok": True, "tools_ok": True, "latency_ms": 90},
                {"provider": "c", "model": "z", "chat_ok": False, "tools_ok": False, "latency_ms": 5},
            ]
        )
        self.assertEqual([item["provider"] for item in ranked], ["b", "a", "c"])


class SkillTests(unittest.TestCase):
    def test_valid_skill(self):
        text = "---\nname: demo\ndescription: >\n  macht etwas\n---\n\n# Demo\n"
        self.assertEqual(autopilot.check_skill(text), (True, "ok"))

    def test_missing_frontmatter(self):
        self.assertFalse(autopilot.check_skill("# nur Text")[0])

    def test_missing_description(self):
        ok, reason = autopilot.check_skill("---\nname: demo\n---\n")
        self.assertFalse(ok)
        self.assertIn("description", reason)

    def test_too_large(self):
        text = "---\nname: demo\ndescription: x\n---\n" + "a" * autopilot.MAX_SKILL_BYTES
        self.assertFalse(autopilot.check_skill(text)[0])


class PackTests(unittest.TestCase):
    def test_parse_packs_defaults_and_warnings(self):
        warnings: list[str] = []
        packs = autopilot.parse_packs(
            {
                "packs": [
                    {"repo": "owner/repo"},
                    {"repo": "kaputt", "name": "x"},
                    {"repo": "owner/pack", "mode": "irgendwas", "select": ["a", " "]},
                ]
            },
            warnings,
        )
        self.assertEqual(len(packs), 2)
        self.assertEqual(packs[0]["mode"], "validate")
        self.assertEqual(packs[1]["mode"], "validate")
        self.assertEqual(packs[1]["select"], ["a"])
        self.assertEqual(len(warnings), 2)

    def _fake_fetchers(self, listing, skills: dict[str, str]):
        def fetch_json(url, timeout=5, token=""):
            return listing

        def fetch_text(url, timeout=5, token=""):
            name = url.split("/")[-2]
            if name in skills:
                return skills[name]
            raise OSError("kein Skill")

        return fetch_json, fetch_text

    def test_validate_mode_reports_without_writing(self):
        fetch_json, fetch_text = self._fake_fetchers(
            [{"type": "dir", "name": "frontend"}, {"type": "file", "name": "README.md"}],
            {"frontend": "---\nname: frontend\ndescription: ui\n---\n"},
        )
        pack = {"name": "p", "repo": "o/r", "ref": "main", "path": "skills", "mode": "validate", "select": []}
        with tempfile.TemporaryDirectory() as folder:
            report = autopilot.process_pack(pack, fetch_json, fetch_text, install_dir=folder)
            self.assertTrue(report["ok"])
            self.assertEqual(report["installed"], 0)
            self.assertEqual(os.listdir(folder), [])

    def test_install_mode_writes_skill(self):
        fetch_json, fetch_text = self._fake_fetchers(
            [{"type": "dir", "name": "frontend"}],
            {"frontend": "---\nname: frontend\ndescription: ui\n---\n"},
        )
        pack = {"name": "p", "repo": "o/r", "ref": "main", "path": "skills", "mode": "install", "select": ["frontend"]}
        with tempfile.TemporaryDirectory() as folder:
            report = autopilot.process_pack(pack, fetch_json, fetch_text, install_dir=folder)
            self.assertTrue(report["ok"])
            self.assertEqual(report["installed"], 1)
            self.assertTrue(os.path.isfile(os.path.join(folder, "frontend", "SKILL.md")))

    def test_unlistable_pack_is_reported(self):
        def broken(url, timeout=5, token=""):
            raise OSError("offline")

        pack = {"name": "p", "repo": "o/r", "ref": "main", "path": "skills", "mode": "validate", "select": []}
        report = autopilot.process_pack(pack, broken, broken)
        self.assertFalse(report["ok"])
        self.assertIn("nicht abrufbar", report["reason"])


class RunTests(unittest.TestCase):
    def setUp(self):
        self.listing = [{"type": "dir", "name": "frontend"}]
        self.skills = {"frontend": "---\nname: frontend\ndescription: ui\n---\n"}

    def fake_fetch_json(self, url, timeout=5, token=""):
        if "api.github.com" in url:
            return self.listing
        return {"routes": []}

    def fake_fetch_text(self, url, timeout=5, token=""):
        return self.skills[url.split("/")[-2]]

    def test_status_has_best_route_and_no_secret(self):
        post = post_factory({("https://text.pollinations.ai/openai", "openai"): (200, TOOL_OK)})
        env = {"OPENROUTER_API_KEY": "geheimer-schluessel"}
        with mock.patch.object(autopilot.hunter, "discover_openrouter", lambda timeout, env: []):
            status = autopilot.run(env, post=post, fetch_json_fn=self.fake_fetch_json, fetch_text_fn=self.fake_fetch_text)
        self.assertEqual(status["best"]["provider"], "pollinations")
        self.assertTrue(status["best"]["tools_ok"])
        self.assertNotIn("geheimer-schluessel", json.dumps(status))
        self.assertIn("generated_at", status)

    def test_no_route_reachable_gives_empty_best(self):
        post = post_factory({})
        with mock.patch.object(autopilot.hunter, "discover_openrouter", lambda timeout, env: []):
            status = autopilot.run({}, post=post, fetch_json_fn=self.fake_fetch_json, fetch_text_fn=self.fake_fetch_text)
        self.assertIsNone(status["best"])
        self.assertTrue(all(not route["chat_ok"] for route in status["routes"]))

    def test_packs_only_mode_skips_probing(self):
        calls: list[str] = []

        def post(url, payload, api_key, timeout):
            calls.append(url)
            return 200, CHAT_OK, 1

        status = autopilot.run(
            {},
            post=post,
            fetch_json_fn=self.fake_fetch_json,
            fetch_text_fn=self.fake_fetch_text,
            packs_only=True,
        )
        self.assertEqual(calls, [])
        self.assertTrue(status["packs"])

    def test_summary_markdown(self):
        status = {
            "best": {"provider": "groq", "model": "llama", "latency_ms": 120, "tools_ok": True},
            "routes": [{"chat_ok": True, "tools_ok": True}, {"chat_ok": False, "tools_ok": False}],
            "packs": [{"name": "p", "ok": True, "reason": "geprüft"}],
            "warnings": ["ein Hinweis"],
        }
        text = autopilot.summary_markdown(status)
        self.assertIn("LLM-Autopilot", text)
        self.assertIn("groq", text)
        self.assertIn("ein Hinweis", text)


class MainTests(unittest.TestCase):
    def run_main(self, argv, env, **injected):
        with tempfile.TemporaryDirectory() as folder:
            env = dict(env)
            env["GITHUB_STEP_SUMMARY"] = os.path.join(folder, "summary.md")
            path = os.path.join(folder, "status.json")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = autopilot.main(argv + ["--status", path], env=env, **injected)
            status = None
            if os.path.exists(path):
                with open(path, encoding="utf-8") as handle:
                    status = json.load(handle)
            summary = ""
            if os.path.exists(env["GITHUB_STEP_SUMMARY"]):
                with open(env["GITHUB_STEP_SUMMARY"], encoding="utf-8") as handle:
                    summary = handle.read()
            return code, status, summary

    def test_success_writes_status(self):
        post = post_factory({("https://text.pollinations.ai/openai", "openai"): (200, TOOL_OK)})
        with mock.patch.object(autopilot.hunter, "discover_openrouter", lambda timeout, env: []):
            code, status, summary = self.run_main(
                ["--summary"],
                {},
                post=post,
                fetch_json_fn=lambda url, timeout=5, token="": {"packs": []},
                fetch_text_fn=lambda url, timeout=5, token="": "",
            )
        self.assertEqual(code, 0)
        self.assertEqual(status["best"]["provider"], "pollinations")
        self.assertIn("LLM-Autopilot", summary)

    def test_exit_5_when_nothing_answers(self):
        with mock.patch.object(autopilot.hunter, "discover_openrouter", lambda timeout, env: []):
            code, status, _ = self.run_main(
                [],
                {},
                post=post_factory({}),
                fetch_json_fn=lambda url, timeout=5, token="": {"packs": []},
                fetch_text_fn=lambda url, timeout=5, token="": "",
            )
        self.assertEqual(code, 5)
        self.assertIsNone(status["best"])


if __name__ == "__main__":
    unittest.main()
