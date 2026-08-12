"""Focused tests for the Bloom-native launcher prompt policy."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import bloom_release


def _modules() -> tuple[ModuleType, ModuleType, ModuleType]:
    git_config = ModuleType("bloom.commands.git.config")
    release = ModuleType("bloom.commands.release")
    config = ModuleType("bloom.config")
    setattr(config, "ACTION_LIST_HISTORY", [["historical"]])
    setattr(config, "DEFAULT_TEMPLATE", {"actions": ["current"]})
    return git_config, release, config


def test_historical_actions_accepts_bloom_default() -> None:
    git_config, release, config = _modules()

    def update_track(track_dict: dict[str, object]) -> bool:
        return git_config.maybe_continue()

    setattr(git_config, "update_track", update_track)
    bloom_release._patch_prompt_behavior(git_config, release, config)

    assert cast(Any, git_config.update_track)({"actions": ["historical"]}) is True


def test_custom_actions_decline() -> None:
    git_config, release, config = _modules()
    track = {"actions": ["custom"]}

    def update_track(track_dict: dict[str, object]) -> bool:
        return git_config.maybe_continue("n")

    setattr(git_config, "update_track", update_track)
    bloom_release._patch_prompt_behavior(git_config, release, config)

    assert cast(Any, git_config.update_track)(track) is False
    assert track == {"actions": ["custom"]}


def test_unrelated_prompts_decline() -> None:
    git_config, release, config = _modules()
    bloom_release._patch_prompt_behavior(git_config, release, config)

    assert cast(Any, release.maybe_continue)() is False
    assert cast(Any, git_config.maybe_continue)(msg="Would you like to create a fork?") is False


def test_launcher_delegates_exact_arguments_once(monkeypatch) -> None:
    argv = ["--rosdistro", "rolling", "--track", "rolling", "package"]
    calls: list[list[str]] = []
    monkeypatch.setattr(bloom_release, "install_prompt_patches", lambda: None)
    monkeypatch.setattr(bloom_release, "invoke_bloom", lambda args: calls.append(args) or None)

    assert bloom_release.main(argv) == 0
    assert calls == [argv]
