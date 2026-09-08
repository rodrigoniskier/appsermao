from pathlib import Path
import unittest


class WorkspaceCssTestCase(unittest.TestCase):
    def test_workspace_uses_app_root_instead_of_locking_body(self):
        css = Path("static/css/workspace.css").read_text(encoding="utf-8")

        body_block = css.split("#workspace-app", 1)[0]
        self.assertNotIn("overflow: hidden", body_block)
        self.assertIn("overflow-y: auto", body_block)

        self.assertIn("#workspace-app", css)
        self.assertIn("display: flex", css)
        self.assertIn("height: calc(100dvh - 54px)", css)
        self.assertIn("#tab-outline.active { display: block; }", css)


if __name__ == "__main__":
    unittest.main()
