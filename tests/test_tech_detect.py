"""Tests for tech stack auto-detection module."""
import json
import subprocess
import sys
import os

import pytest

# Ensure the project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.tech_detect import detect_tech_stack


# ---------------------------------------------------------------------------
# Helper to write files inside tmp_path
# ---------------------------------------------------------------------------

def _write(tmp_path, name, content=""):
    """Create a file (with optional content) under tmp_path, creating dirs."""
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


# ---------------------------------------------------------------------------
# Individual stack detection
# ---------------------------------------------------------------------------

class TestWebFrontend:
    def test_detects_react(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"dependencies": {"react": "^18"}}))
        result = detect_tech_stack(str(tmp_path))
        assert "web-frontend" in result["stacks"]
        assert result["qa_tool"] == "playwright"
        assert result["ui_validation"] == "browser-automation"
        assert "XSS" in result["security_focus"]

    def test_detects_vue(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"dependencies": {"vue": "^3"}}))
        result = detect_tech_stack(str(tmp_path))
        assert "web-frontend" in result["stacks"]

    def test_detects_svelte(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"devDependencies": {"svelte": "^4"}}))
        result = detect_tech_stack(str(tmp_path))
        assert "web-frontend" in result["stacks"]

    def test_detects_angular(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"dependencies": {"@angular/core": "^16"}}))
        result = detect_tech_stack(str(tmp_path))
        assert "web-frontend" in result["stacks"]


class TestWebBackend:
    def test_detects_express(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"dependencies": {"express": "^4"}}))
        result = detect_tech_stack(str(tmp_path))
        assert "web-backend" in result["stacks"]
        assert result["qa_tool"] == "supertest"
        assert result["ui_validation"] == "none"
        assert "SQLi" in result["security_focus"]

    def test_detects_fastify(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"dependencies": {"fastify": "^4"}}))
        result = detect_tech_stack(str(tmp_path))
        assert "web-backend" in result["stacks"]

    def test_detects_nestjs(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"dependencies": {"@nestjs/core": "^10"}}))
        result = detect_tech_stack(str(tmp_path))
        assert "web-backend" in result["stacks"]


class TestElectron:
    def test_detects_electron(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({"dependencies": {"electron": "^25"}}))
        result = detect_tech_stack(str(tmp_path))
        assert "desktop-electron" in result["stacks"]
        assert result["qa_tool"] == "playwright"
        assert result["ui_validation"] == "window-automation"
        assert "node-integration" in result["security_focus"]
        assert "IPC" in result["security_focus"]


class TestTauri:
    def test_detects_tauri(self, tmp_path):
        _write(tmp_path, "Cargo.toml", '[dependencies]\ntauri = "1.4"')
        result = detect_tech_stack(str(tmp_path))
        assert "desktop-tauri" in result["stacks"]
        assert result["qa_tool"] == "playwright"
        assert result["ui_validation"] == "window-automation"
        assert "IPC" in result["security_focus"]
        assert "command-injection" in result["security_focus"]


class TestIOS:
    def test_detects_podfile(self, tmp_path):
        _write(tmp_path, "Podfile", "platform :ios, '15.0'")
        result = detect_tech_stack(str(tmp_path))
        assert "ios" in result["stacks"]
        assert result["qa_tool"] == "xctest"
        assert result["ui_validation"] == "simulator"
        assert "keychain" in result["security_focus"]

    def test_detects_xcodeproj(self, tmp_path):
        (tmp_path / "MyApp.xcodeproj").mkdir()
        result = detect_tech_stack(str(tmp_path))
        assert "ios" in result["stacks"]


class TestAndroid:
    def test_detects_build_gradle(self, tmp_path):
        _write(tmp_path, "build.gradle", "")
        result = detect_tech_stack(str(tmp_path))
        assert "android" in result["stacks"]
        assert result["qa_tool"] == "maestro"
        assert result["ui_validation"] == "emulator"
        assert "intent-injection" in result["security_focus"]

    def test_detects_android_manifest(self, tmp_path):
        _write(tmp_path, "AndroidManifest.xml", "")
        result = detect_tech_stack(str(tmp_path))
        assert "android" in result["stacks"]


class TestFlutter:
    def test_detects_flutter(self, tmp_path):
        _write(tmp_path, "pubspec.yaml", "")
        result = detect_tech_stack(str(tmp_path))
        assert "mobile-cross-platform" in result["stacks"]
        assert result["qa_tool"] == "maestro"
        assert result["ui_validation"] == "simulator"
        assert "platform-specific" in result["security_focus"]


class TestRustCLI:
    def test_detects_rust_cli(self, tmp_path):
        _write(tmp_path, "Cargo.toml", '[package]\nname = "mycli"')
        result = detect_tech_stack(str(tmp_path))
        assert "cli-rust" in result["stacks"]
        assert result["qa_tool"] == "shell-e2e"
        assert result["ui_validation"] == "none"
        assert "input-validation" in result["security_focus"]

    def test_cargo_with_tauri_is_not_cli_rust(self, tmp_path):
        _write(tmp_path, "Cargo.toml", '[dependencies]\ntauri = "1.4"')
        result = detect_tech_stack(str(tmp_path))
        assert "cli-rust" not in result["stacks"]


class TestGo:
    def test_detects_go(self, tmp_path):
        _write(tmp_path, "go.mod", "module example.com/myapp")
        result = detect_tech_stack(str(tmp_path))
        assert "cli-go" in result["stacks"]
        assert result["qa_tool"] == "shell-e2e"
        assert result["ui_validation"] == "none"
        assert "path-traversal" in result["security_focus"]


class TestPython:
    def test_detects_pyproject(self, tmp_path):
        _write(tmp_path, "pyproject.toml", "")
        result = detect_tech_stack(str(tmp_path))
        assert "python" in result["stacks"]
        assert result["qa_tool"] == "pytest"
        assert result["ui_validation"] == "none"
        assert "dependency-audit" in result["security_focus"]

    def test_detects_setup_py(self, tmp_path):
        _write(tmp_path, "setup.py", "")
        result = detect_tech_stack(str(tmp_path))
        assert "python" in result["stacks"]


# ---------------------------------------------------------------------------
# Multi-stack detection
# ---------------------------------------------------------------------------

class TestMultiStack:
    def test_detects_react_and_express(self, tmp_path):
        _write(tmp_path, "package.json", json.dumps({
            "dependencies": {"react": "^18", "express": "^4"}
        }))
        result = detect_tech_stack(str(tmp_path))
        assert "web-frontend" in result["stacks"]
        assert "web-backend" in result["stacks"]
        # Primary qa_tool/ui_validation come from first detected stack
        assert result["qa_tool"] == "playwright"
        assert result["ui_validation"] == "browser-automation"
        # Security focus is merged and deduplicated
        assert "XSS" in result["security_focus"]
        assert "SQLi" in result["security_focus"]

    def test_detects_python_and_go(self, tmp_path):
        _write(tmp_path, "pyproject.toml", "")
        _write(tmp_path, "go.mod", "module example.com/app")
        result = detect_tech_stack(str(tmp_path))
        assert "python" in result["stacks"]
        assert "cli-go" in result["stacks"]


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

class TestFallback:
    def test_generic_when_nothing_matches(self, tmp_path):
        result = detect_tech_stack(str(tmp_path))
        assert result["stacks"] == ["generic"]
        assert result["qa_tool"] == "shell-e2e"
        assert result["ui_validation"] == "none"
        assert result["security_focus"] == ["general"]


# ---------------------------------------------------------------------------
# CLI mode
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_outputs_valid_json(self, tmp_path):
        _write(tmp_path, "go.mod", "module example.com/myapp")
        result = subprocess.run(
            [sys.executable, "-m", "lib.tech_detect", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "stacks" in data
        assert "cli-go" in data["stacks"]

    def test_cli_defaults_to_cwd(self, tmp_path):
        """CLI with no args should use current working directory."""
        script = os.path.join(os.path.dirname(__file__), "..", "lib", "tech_detect.py")
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["stacks"] == ["generic"]
