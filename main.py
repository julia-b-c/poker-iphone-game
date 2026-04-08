import asyncio
import sys

from game_v3_ios import run_game, run_game_web


if sys.platform == "emscripten":
    asyncio.create_task(run_game_web())
else:
    run_game()
