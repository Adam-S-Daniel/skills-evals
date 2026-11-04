"""harness/sealed.py: the one check every sealed-lane widening keys on."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "harness"))

import sealed  # noqa: E402

PROXY_URL = "http://skills-evals-1-ab12cd34-credproxy:8080"


class TestSealedContainer(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dockerenv = Path(tmp.name) / ".dockerenv"
        self.dockerenv.write_text("", encoding="utf-8")
        self.missing = Path(tmp.name) / "absent"

    def proxy_env(self, **extra):
        return {"SKILLS_EVALS_IN_CONTAINER": "1", "EVAL_SEAL": "proxy",
                "ANTHROPIC_BASE_URL": PROXY_URL,
                "CLAUDE_CODE_OAUTH_TOKEN": "dummy-not-a-token", **extra}

    def allowlist_env(self, **extra):
        return {"SKILLS_EVALS_IN_CONTAINER": "1", "EVAL_SEAL": "allowlist",
                "CLAUDE_CODE_OAUTH_TOKEN": "example-token-value", **extra}

    def check(self, environ, dockerenv=None):
        return sealed.sealed_container(environ, dockerenv or self.dockerenv)

    def test_proxy_seal(self):
        self.assertEqual(self.check(self.proxy_env()), "proxy")

    def test_allowlist_seal(self):
        self.assertEqual(self.check(self.allowlist_env()), "allowlist")

    def test_every_condition_is_required(self):
        for environ in (self.proxy_env(), self.allowlist_env()):
            with self.subTest(seal=environ["EVAL_SEAL"]):
                self.assertIsNone(self.check(environ, self.missing))
                for flag in (None, "", "0", "true", " 1"):
                    env = dict(environ)
                    if flag is None:
                        del env["SKILLS_EVALS_IN_CONTAINER"]
                    else:
                        env["SKILLS_EVALS_IN_CONTAINER"] = flag
                    self.assertIsNone(self.check(env), flag)
                for seal in (None, "", "PROXY", "credproxy", "none"):
                    env = dict(environ)
                    if seal is None:
                        del env["EVAL_SEAL"]
                    else:
                        env["EVAL_SEAL"] = seal
                    self.assertIsNone(self.check(env), seal)

    def test_proxy_needs_the_sidecar_url_and_the_dummy(self):
        for url in ("", "https://api.example.com:443", "http://api.example.com:8080",
                    "http://user:pw@proxy:8080", "http://proxy:8080/path",
                    "http://proxy", "http://Proxy:8080", PROXY_URL + "\n"):
            with self.subTest(url=url):
                self.assertIsNone(self.check(self.proxy_env(ANTHROPIC_BASE_URL=url)))
        env = self.proxy_env()
        del env["ANTHROPIC_BASE_URL"]
        self.assertIsNone(self.check(env))
        for token in ("", "example-token-value"):
            with self.subTest(token=token):
                self.assertIsNone(self.check(self.proxy_env(CLAUDE_CODE_OAUTH_TOKEN=token)))

    def test_allowlist_needs_a_token_and_no_base_url(self):
        self.assertIsNone(self.check(self.allowlist_env(CLAUDE_CODE_OAUTH_TOKEN="")))
        env = self.allowlist_env()
        del env["CLAUDE_CODE_OAUTH_TOKEN"]
        self.assertIsNone(self.check(env))
        self.assertIsNone(self.check(self.allowlist_env(ANTHROPIC_BASE_URL=PROXY_URL)))

    def test_default_reads_the_process_environment_and_real_dockerenv(self):
        # Outside a container (no /.dockerenv) it is None whatever the env says.
        if Path("/.dockerenv").exists():
            self.skipTest("running inside a container")
        self.assertIsNone(sealed.sealed_container(self.proxy_env()))


if __name__ == "__main__":
    unittest.main()
