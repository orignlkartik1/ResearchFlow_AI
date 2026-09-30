import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from my_agent.backend.main import app


class WebUITests(unittest.TestCase):
    def test_home_and_static_assets_are_served_in_web_only_mode(self):
        with patch.dict(os.environ, {"ENABLE_TELEGRAM": "false"}, clear=True):
            with TestClient(app) as client:
                home = client.get("/")
                stylesheet = client.get("/static/style.css")
                script = client.get("/static/app.js")

        self.assertEqual(home.status_code, 200)
        self.assertIn("ResearchFlow-AI", home.text)
        self.assertIn('/static/style.css', home.text)
        self.assertIn('/static/app.js', home.text)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("text/css", stylesheet.headers["content-type"])
        self.assertIn("@media (max-width: 620px)", stylesheet.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn("fetch(\"/api/analyze-pdf\"", script.text)
        self.assertIn("NO_EXTRACTABLE_TEXT", script.text)
        self.assertIn("INVALID_PDF", script.text)
        self.assertIn("analysisText.textContent = data.result.response", script.text)
        self.assertNotIn(".innerHTML", script.text)


if __name__ == "__main__":
    unittest.main()
