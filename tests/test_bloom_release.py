"""Focused tests for the Bloom-native launcher prompt policy."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import bloom_release


def _modules() -> tuple[ModuleType, ModuleType, ModuleType]:
    git_config = ModuleType("bloom.commands.git.config")
    release = ModuleType("bloom.commands.release")
    config = ModuleType("bloom.config")
    setattr(config, "ACTION_LIST_HISTORY", [["historical"]])
    setattr(config, "DEFAULT_TEMPLATE", {"actions": ["current"]})
    return git_config, release, config


def update_track(git_config: ModuleType, config: ModuleType, track: dict) -> dict:
    """Model Bloom 0.14.3's update_track default selection."""
    actions = track["actions"]
    default = "y" if actions in config.ACTION_LIST_HISTORY else "n"
    if git_config.maybe_continue(default):
        track["actions"] = config.DEFAULT_TEMPLATE["actions"]
    return track


def test_historical_actions_accept_bloom_default() -> None:
    git_config, release, config = _modules()
    bloom_release._patch_prompt_behavior(git_config, release)

    track = {"actions": ["historical"]}
    assert update_track(git_config, config, track)["actions"] == ["current"]


def test_custom_actions_decline_and_remain_unmodified() -> None:
    git_config, release, config = _modules()
    bloom_release._patch_prompt_behavior(git_config, release)

    track = {"actions": ["custom"]}
    assert update_track(git_config, config, track)["actions"] == ["custom"]


def test_unrelated_git_and_release_prompts_decline() -> None:
    git_config, release, config = _modules()
    bloom_release._patch_prompt_behavior(git_config, release)

    def unrelated_git_prompt() -> bool:
        return git_config.maybe_continue()

    assert unrelated_git_prompt() is False
    assert release.maybe_continue("y", "Pushing changes failed; add --force?") is False


def test_launcher_delegates_exact_arguments_once(monkeypatch) -> None:
    argv = ["--rosdistro", "rolling", "--track", "rolling", "package"]
    calls: list[list[str]] = []
    monkeypatch.setattr(bloom_release, "install_prompt_patches", lambda: None)
    monkeypatch.setattr(bloom_release, "invoke_bloom", lambda args: calls.append(args) or None)

    assert bloom_release.main(argv) == 0
    assert calls == [argv]
