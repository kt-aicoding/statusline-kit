import unittest
from pathlib import Path
import sys
import tempfile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from statusline_kit.cli import format_claude_status, main, upsert_codex_config, upsert_tui_status_line


class ClaudeStatusTests(unittest.TestCase):
    def test_formats_available_fields(self):
        status = format_claude_status(
            {
                "model": {"display_name": "Claude Sonnet"},
                "effort": {"level": "medium"},
                "context_window": {"used_percentage": 37.5},
                "rate_limits": {
                    "five_hour": {"used_percentage": 12},
                    "seven_day": {"used_percentage": 64},
                },
                "cost": {"total_cost_usd": 0.0214},
            }
        )

        self.assertEqual(
            "Claude Sonnet medium · Context 37.5% used · 5h 88% left · weekly 36% left",
            status,
        )

    def test_tolerates_missing_json_fields(self):
        self.assertEqual("Claude", format_claude_status({}))

    def test_formats_fractional_percentages_and_list_rate_limits(self):
        status = format_claude_status(
            {
                "model": "Claude Sonnet",
                "effort": "high",
                "context_window": {"used_percent": 0.42},
                "rate_limits": [
                    {"name": "5h", "used_percent": 0.25},
                    {"name": "weekly", "used_percent": 0.75},
                ],
            }
        )

        self.assertEqual(
            "Claude Sonnet high · Context 42% used · 5h 75% left · weekly 25% left",
            status,
        )

    def test_colors_claude_risk_segments_when_enabled(self):
        status = format_claude_status(
            {
                "model": "Claude Sonnet",
                "effort": "high",
                "context_window": {"used_percentage": 90},
                "rate_limits": {
                    "five_hour": {"remaining_percentage": 10},
                    "weekly": {"remaining_percentage": 35},
                },
            },
            use_color=True,
        )

        self.assertIn("\033[1mClaude Sonnet high\033[0m", status)
        self.assertIn("\033[31mContext 90% used\033[0m", status)
        self.assertIn("\033[31m5h 10% left\033[0m", status)
        self.assertIn("\033[33mweekly 35% left\033[0m", status)


class CodexConfigTests(unittest.TestCase):
    def test_adds_tui_section_when_missing(self):
        result = upsert_tui_status_line('model = "gpt-5-codex"\n')

        self.assertIn("[tui]", result)
        self.assertIn('"model-with-reasoning"', result)
        self.assertIn('"context-used"', result)
        self.assertIn('"five-hour-limit"', result)
        self.assertIn('"weekly-limit"', result)
        self.assertIn('"git-branch"', result)
        self.assertIn("status_line_use_colors = true", result)

    def test_replaces_status_line_and_preserves_other_tui_keys(self):
        original = """model = "gpt-5-codex"

[tui]
theme = "dark"
status_line = [
  "old",
]
status_line_use_colors = false

[tui.model_availability_nux]
gpt-5-codex = "seen"
"""
        result = upsert_tui_status_line(original)

        self.assertIn('theme = "dark"', result)
        self.assertIn('"model-with-reasoning"', result)
        self.assertNotIn('"old"', result)
        self.assertIn("[tui.model_availability_nux]", result)
        self.assertIn('gpt-5-codex = "seen"', result)

    def test_installs_safe_codex_preferences(self):
        result = upsert_codex_config('model = "gpt-5.5"\n')

        self.assertIn("check_for_update_on_startup = false", result)
        self.assertIn('project_doc_fallback_filenames = ["CLAUDE.md", "README.md"]', result)
        self.assertIn("[history]", result)
        self.assertIn('persistence = "save-all"', result)
        self.assertIn("[shell_environment_policy]", result)
        self.assertIn('"*TOKEN*"', result)
        self.assertIn("[agents]", result)
        self.assertIn("max_threads = 6", result)

    def test_full_codex_config_preserves_nested_tables(self):
        original = """model = "gpt-5.5"

[tui]
theme = "dark"
status_line = ["old"]

[tui.model_availability_nux]
gpt-5.5 = 1

[plugins."vercel@openai-curated"]
enabled = true
"""
        result = upsert_codex_config(original)

        self.assertIn('theme = "dark"', result)
        self.assertIn("[tui.model_availability_nux]", result)
        self.assertIn("gpt-5.5 = 1", result)
        self.assertIn('[plugins."vercel@openai-curated"]', result)
        self.assertIn("enabled = true", result)


class CliDispatchTests(unittest.TestCase):
    def test_install_claude_dispatch_uses_status_command_arg(self):
        with tempfile.TemporaryDirectory() as tempdir:
            settings = Path(tempdir) / "settings.json"

            code = main(
                [
                    "install-claude",
                    "--settings",
                    str(settings),
                    "--command",
                    "custom-statusline claude",
                ]
            )

            self.assertEqual(0, code)
            self.assertIn("custom-statusline claude", settings.read_text())


if __name__ == "__main__":
    unittest.main()
