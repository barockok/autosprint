"""Tests for agent selection logic."""
import json
from lib.agent_selector import select_agents, render_selection


class TestAgentSelection:
    def test_css_only_change_selects_ui(self):
        result = select_agents(["src/styles.css"], "change button color")
        assert "ui" in result["reviewers"]
        assert "security" not in result["reviewers"]
        assert "tpm" not in result["reviewers"]

    def test_auth_file_selects_security(self):
        result = select_agents(["src/auth/login.ts"], "add login endpoint")
        assert "security" in result["reviewers"]

    def test_readme_change_selects_tpm(self):
        result = select_agents(["README.md", "src/app.ts"], "update docs")
        assert "tpm" in result["reviewers"]

    def test_large_change_selects_tpm(self):
        files = [f"src/file{i}.ts" for i in range(15)]
        result = select_agents(files, "refactor modules")
        assert "tpm" in result["reviewers"]

    def test_pure_backend_skips_ui(self):
        result = select_agents(["src/server.ts", "src/db.ts"], "add database query")
        assert "ui" not in result["reviewers"]
        assert "qa" in result["reviewers"]

    def test_payment_feature_selects_security(self):
        result = select_agents(["src/checkout.ts"], "add stripe payment")
        assert "security" in result["reviewers"]

    def test_pair_principle_minimum_one_reviewer(self):
        result = select_agents(["config.yaml"], "update config value")
        assert len(result["reviewers"]) >= 1
        assert "dev" in result["agents"]

    def test_dev_always_included(self):
        result = select_agents(["anything.ts"])
        assert "dev" in result["agents"]

    def test_full_feature_selects_multiple(self):
        result = select_agents(
            ["src/components/LoginForm.tsx", "src/auth/handler.ts", "README.md"],
            "add OAuth2 login with UI"
        )
        assert "qa" in result["reviewers"]
        assert "ui" in result["reviewers"]
        assert "security" in result["reviewers"]
        assert "tpm" in result["reviewers"]

    def test_docs_only_skips_qa(self):
        result = select_agents(["README.md", "docs/guide.md"], "update documentation")
        assert "qa" not in result["reviewers"] or "tpm" in result["reviewers"]

    def test_env_file_selects_security(self):
        result = select_agents(["src/app.ts", ".env.example"], "add env vars")
        assert "security" in result["reviewers"]

    def test_docker_change_selects_tpm(self):
        result = select_agents(["docker-compose.yml", "src/app.ts"], "add docker setup")
        assert "tpm" in result["reviewers"]

    def test_result_has_reasons(self):
        result = select_agents(["src/components/Button.tsx"], "add button")
        for reviewer in result["reviewers"]:
            assert reviewer in result["reason"]
            assert len(result["reason"][reviewer]) > 0

    def test_result_has_skipped_reasons(self):
        result = select_agents(["src/utils.ts"], "add helper function")
        for agent in result["skipped"]:
            assert len(result["skipped"][agent]) > 0

    def test_vue_file_selects_ui(self):
        result = select_agents(["src/App.vue"], "update layout")
        assert "ui" in result["reviewers"]

    def test_svelte_file_selects_ui(self):
        result = select_agents(["src/Page.svelte"], "update page")
        assert "ui" in result["reviewers"]

    def test_migration_file_selects_security(self):
        result = select_agents(["src/database/migration.ts"], "add migration")
        assert "security" in result["reviewers"]


class TestRenderSelection:
    def test_renders_markdown_table(self):
        result = select_agents(["src/components/Nav.tsx", "src/auth/login.ts"], "add nav with auth")
        output = render_selection(result)
        assert "| Agent" in output
        assert "ACTIVE" in output
        assert "Dev" in output
        assert "reviewer(s) selected" in output

    def test_shows_skipped_agents(self):
        result = select_agents(["src/utils.ts"], "add helper")
        output = render_selection(result)
        assert "SKIPPED" in output
