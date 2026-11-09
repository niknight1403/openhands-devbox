"""Sicherheitsregressionen fuer ausgehende HTTP-Abrufe."""

import ipaddress
import sys
import unittest
from pathlib import Path
from urllib.request import Request
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import netzwerk  # noqa: E402


class NetzwerksicherheitTest(unittest.TestCase):
    def test_redirect_auf_loopback_wird_abgelehnt(self):
        handler = netzwerk._SichereWeiterleitung()
        with self.assertRaises(netzwerk.NetzFehler):
            handler.redirect_request(
                Request("https://example.org/start"),
                None,
                302,
                "Found",
                {},
                "http://127.0.0.1/admin",
            )

    def test_redirect_auf_private_ipv6_wird_abgelehnt(self):
        handler = netzwerk._SichereWeiterleitung()
        with self.assertRaises(netzwerk.NetzFehler):
            handler.redirect_request(
                Request("https://example.org/start"),
                None,
                302,
                "Found",
                {},
                "http://[::1]/",
            )

    def test_url_mit_eingebetteten_zugangsdaten_wird_abgelehnt(self):
        with self.assertRaises(netzwerk.NetzFehler):
            netzwerk.pruefe_url("https://user:password@example.org/")

    def test_ungueltiger_port_wird_abgelehnt(self):
        with self.assertRaises(netzwerk.NetzFehler):
            netzwerk.pruefe_url("https://example.org:invalid/")

    def test_host_ohne_dns_adresse_wird_abgelehnt(self):
        with patch.object(netzwerk, "_adressen", return_value=[]):
            with self.assertRaises(netzwerk.NetzFehler):
                netzwerk.pruefe_url("https://example.org/")

    def test_alle_dns_adressen_muessen_oeffentlich_sein(self):
        with patch.object(
            netzwerk,
            "_adressen",
            return_value=[
                ipaddress.ip_address("93.184.216.34"),
                ipaddress.ip_address("10.0.0.8"),
            ],
        ):
            with self.assertRaises(netzwerk.NetzFehler):
                netzwerk.pruefe_url("https://example.org/")


if __name__ == "__main__":
    unittest.main()
