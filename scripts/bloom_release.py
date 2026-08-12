#!/usr/bin/env python3
"""Launch Bloom with the small non-interactive policy needed by the action."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Optional


def _patch_prompt_behavior(
    git_config_module: ModuleType,
    release_module: ModuleType,
) -> None:
    """Make Bloom accept only its known historical-actions default.

    Bloom imports ``maybe_continue`` into both the git-config and release
    modules. The former needs one narrowly recognized exception for the
    historical action-list update. The latter handles release-level prompts,
    including the force-push fallback, and must always decline them.
    """

    def maybe_continue(default: str = "y", msg: str = "Continue") -> bool:
        """Accept Bloom's historical-action update prompt and no other one."""
        caller = sys._getframe(1)
        # Bloom 0.14.3 calls this with y for historical actions and n for
        # custom actions, using the default Continue message.
        return caller.f_code.co_name == "update_track" and default == "y" and msg == "Continue"

    setattr(git_config_module, "maybe_continue", maybe_continue)
    setattr(
        release_module,
        "maybe_continue",
        lambda default="y", msg="Continue": False,
    )


def install_prompt_patches() -> None:
    """Install the Bloom 0.14.3 prompt policy before importing its entry point."""
    import bloom.rosdistro_api as rosdistro_api

    original_prompt = rosdistro_api.get_non_eol_distros_prompt
    rosdistro_api.get_non_eol_distros_prompt = lambda: ""
    try:
        from bloom.commands import release as release_module
        from bloom.commands.git import config as git_config
    finally:
        rosdistro_api.get_non_eol_distros_prompt = original_prompt

    _patch_prompt_behavior(git_config, release_module)


def invoke_bloom(argv: list[str]) -> object:
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
