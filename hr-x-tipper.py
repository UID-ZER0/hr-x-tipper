import asyncio
import time
from math import sqrt
from typing import Dict

from highrise import BaseBot, Position, User
from highrise.models import SessionMetadata


class CircleTippingBot(BaseBot):
    # Define the reward zone
    circle_center = (10.0, 8.0)   # You can change this to your preferred center
    circle_radius = 2.5

    # Which emotes are eligible for rewards
    rewardable_emotes = {
        "dance_move_1": 1,
        "yoga_pose": 1,
        "heart": 1
    }

    def __init__(self):
        self.user_state: Dict[str, Dict] = {}  # Keeps track of each user's state
        self.task = None

    def is_in_circle(self, position: Position) -> bool:
        dx = position.x - self.circle_center[0]
        dy = position.y - self.circle_center[1]
        return sqrt(dx * dx + dy * dy) <= self.circle_radius

    async def on_start(self, metadata: SessionMetadata) -> None:
        print("Bot started.")
        self.task = asyncio.create_task(self.track_time_loop())

    async def on_user_move(self, user: User, position: Position, *args, **kwargs) -> None:
        state = self.user_state.setdefault(user.id, {
            "in_circle": False,
            "emoting": False,
            "start": None,
            "total": 0,
            "rewarded": False
        })

        state["in_circle"] = self.is_in_circle(position)
        if state["in_circle"] and state["emoting"] and state["start"] is None:
            state["start"] = time.time()

    async def on_emote(self, user: User, emote: str, *args, **kwargs) -> None:
        if emote not in self.rewardable_emotes:
            return

        pos = await self.highrise.get_user_position(user.id)
        state = self.user_state.setdefault(user.id, {
            "in_circle": False,
            "emoting": False,
            "start": None,
            "total": 0,
            "rewarded": False
        })

        state["in_circle"] = self.is_in_circle(pos)
        state["emoting"] = True
        if state["in_circle"] and state["start"] is None:
            state["start"] = time.time()

    async def track_time_loop(self):
        while True:
            now = time.time()
            for user_id, state in self.user_state.items():
                if state["in_circle"] and state["emoting"] and not state["rewarded"]:
                    if state["start"] is not None:
                        state["total"] += now - state["start"]
                        state["start"] = now

                        if state["total"] >= 600:
                            try:
                                await self.highrise.tip_user(user_id, "gold_bar_1")
                                state["rewarded"] = True
                                print(f"🎉 Rewarded {user_id} for emoting in the circle for 10 minutes!")
                            except Exception as e:
                                print(f"❌ Failed to tip {user_id}: {e}")
                else:
                    state["start"] = None  # Reset if they leave or stop emoting
            await asyncio.sleep(5)
