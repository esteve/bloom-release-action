#!/usr/bin/env python3
"""Launch Bloom with the small non-interactive policy needed by the action."""

from __future__ import annotations

import sys
import inspect
from types import ModuleType
from typing import Any, Optional

_PATCH_MARKER = "_release_ros_robot_prompt_patch"


def _patch_prompt_behavior(
    git_config_module: ModuleType,
    release_module: ModuleType,
    bloom_config_module: ModuleType,
) -> None:
    """Make Bloom accept only its known historical-actions default.

    Bloom imports ``maybe_continue`` into both the git-config and release
    modules. The former needs one narrowly recognized exception for the
    historical action-list update. The latter handles release-level prompts,
    including the force-push fallback, and must always decline them.
    """
    if getattr(git_config_module, _PATCH_MARKER, False):
        return

    historical_actions = getattr(bloom_config_module, "ACTION_LIST_HISTORY", ())
    default_template = getattr(bloom_config_module, "DEFAULT_TEMPLATE", {})
    if (
        not isinstance(historical_actions, (list, tuple))
        or not isinstance(default_template, dict)
        or not isinstance(default_template.get("actions"), list)
    ):
        raise ValueError("Bloom action history/default actions are unavailable")
    default_actions = default_template["actions"]

    def maybe_continue(default: Any = "y", msg: Any = "Continue") -> bool:
        # Bloom 0.14.3's historical-action update is the sole accepted prompt.
        # Check the caller and the track data as well as the exact prompt, so a
        # different git-config prompt cannot accidentally be accepted.
        frame = inspect.currentframe()
        caller = frame.f_back if frame is not None else None
        track_data = caller.f_locals.get("track_dict") if caller else None
        if track_data is None and caller:
            track_data = caller.f_locals.get("track_data")
        actions = track_data.get("actions") if isinstance(track_data, dict) else None
        is_historical = isinstance(actions, list) and any(
            actions == historical and actions != default_actions
            for historical in historical_actions
        )
        if (
            caller is not None
            and caller.f_code.co_name == "update_track"
            and msg == "Continue"
            and is_historical
        ):
            return str(default).lower() == "y"
        return False

    def decline(*args: Any, **kwargs: Any) -> bool:
        return False

    # update_track resolves this module-level alias at call time. Do not patch
    # bloom.util.maybe_continue: unrelated Bloom commands retain their behavior
    # outside this release invocation.
    setattr(git_config_module, "maybe_continue", maybe_continue)
    setattr(release_module, "maybe_continue", decline)
    setattr(git_config_module, _PATCH_MARKER, True)


def install_prompt_patches() -> None:
    """Install the Bloom 0.14.3 prompt policy before importing its entry point."""
    import bloom.rosdistro_api as rosdistro_api

    # Bloom's config module evaluates a help-text network lookup at import
    # time. The prompt patch only needs local action constants, so avoid an
    # unrelated network dependency while loading it.
    original_prompt = rosdistro_api.get_non_eol_distros_prompt
    rosdistro_api.get_non_eol_distros_prompt = lambda: ""
    try:
        from bloom import config as bloom_config
    finally:
        rosdistro_api.get_non_eol_distros_prompt = original_prompt

    from bloom.commands import release as release_module
    from bloom.commands.git import config as git_config

    _patch_prompt_behavior(git_config, release_module, bloom_config)


def invoke_bloom(argv: list[str]) -> Any:
    """Invoke Bloom's normal release entry point with the exact argument list."""
    from bloom.commands.release import main as bloom_release_main

    return bloom_release_main(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Install the prompt policy and delegate once to Bloom."""
    install_prompt_patches()
    result = invoke_bloom(sys.argv[1:] if argv is None else argv)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
