import asyncio
import sys

from game_v3_ios import run_game, run_game_web


if __name__ == "__main__":
    if sys.platform == "emscripten":
        asyncio.run(run_game_web())
    else:
        run_game()
