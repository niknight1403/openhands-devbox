import importlib.util
import os
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "waehle_modell.py"
spec = importlib.util.spec_from_file_location("waehle_modell", SCRIPT)
modul = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modul)


class TestModellwahl(unittest.TestCase):
    def test_free_models_filtert_bezahlmodelle(self):
        payload = {
            "data": [
                {"id": "qwen/qwen3.8-27b"},
                {"id": "qwen/qwen3-coder:free"},
                {"id": "google/gemma-4-31b-it:free"},
                {"kein": "id"},
            ]
        }
        self.assertEqual(
            modul.free_models(payload),
            ["qwen/qwen3-coder:free", "google/gemma-4-31b-it:free"],
        )

    def test_free_models_haelt_kaputte_eingaben_aus(self):
        self.assertEqual(modul.free_models(None), [])
        self.assertEqual(modul.free_models({"data": "keine liste"}), [])

    def test_rank_bevorzugt_code_modelle(self):
        ranked = modul.rank(["zzz/model:free", "aaa/coder:free", "mmm/model:free"])
        self.assertEqual(ranked[0], "aaa/coder:free")
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked, sorted(ranked, key=lambda m: (0 if "coder" in m else 1, len(m), m)))

    def test_rank_entfernt_duplikate(self):
        self.assertEqual(modul.rank(["a:free", "a:free"]), ["a:free"])

    def test_normalise_strippt_openrouter_praefix(self):
        self.assertEqual(modul.normalise("openrouter/x/y:free"), "x/y:free")
        self.assertEqual(modul.normalise("x/y:free"), "x/y:free")

    def test_build_routes_ohne_schluessel_nutzt_keyfreie_route(self):
        routes = modul.build_routes({}, [])
        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0][2], modul.POLLINATIONS_BASE_URL)

    def test_keyfreie_route_ist_immer_letzte_reserve(self):
        routes = modul.build_routes({"OPENROUTER_API_KEY": "k"}, ["a/coder:free"])
        self.assertEqual(routes[-1][2], modul.POLLINATIONS_BASE_URL)
        self.assertNotEqual(routes[0][2], modul.POLLINATIONS_BASE_URL)

    def test_build_routes_mit_modellwunsch_startet_damit(self):
        routes = modul.build_routes(
            {"OPENROUTER_API_KEY": "k", "MODEL_INPUT": "openrouter/z/model:free"},
            ["a/coder:free"],
        )
        self.assertEqual(routes[0][1], "z/model:free")

    def test_build_routes_ohne_wunsch_nutzt_rangliste(self):
        routes = modul.build_routes({"OPENROUTER_API_KEY": "k"}, ["b/model:free", "a/coder:free"])
        self.assertEqual(routes[0][1], "a/coder:free")

    def test_write_env_schreibt_alle_drei_werte(self):
        import tempfile

        with tempfile.NamedTemporaryFile("r+", delete=False) as handle:
            path = handle.name
        try:
            modul.write_env(path, "openrouter/a/coder:free", modul.OPENROUTER_BASE_URL, "secret")
            content = Path(path).read_text(encoding="utf-8")
            self.assertIn("LLM_MODEL=openrouter/a/coder:free", content)
            self.assertIn(f"LLM_BASE_URL={modul.OPENROUTER_BASE_URL}", content)
            self.assertIn("LLM_API_KEY=secret", content)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
