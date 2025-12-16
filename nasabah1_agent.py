import json, time
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, CyclicBehaviour
from spade.message import Message

class Nasabah1(Agent):
    def __init__(self, jid, password, withdraw_amount):
        super().__init__(jid, password)
        self.withdraw_amount = withdraw_amount
        self.withdraw_enabled = True

    class WithdrawBehaviour(PeriodicBehaviour):
        async def run(self):
            if not self.agent.withdraw_enabled:
                return

            msg = Message(
                to="atm1@localhost",
                body=json.dumps({
                    "type": "withdraw",
                    "amount": self.agent.withdraw_amount
                })
            )
            msg.set_metadata("performative", "request")
            msg.set_metadata("conversation-id", str(time.time()))
            await self.send(msg)

            print(f"NASABAH | Tarik {self.agent.withdraw_amount:,}")

    class ControlBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=5)
            if not msg:
                return

            content = json.loads(msg.body)
            if content.get("type") == "atm_status":
                status = content.get("status")
                if status == "offline":
                    self.agent.withdraw_enabled = False
                elif status == "online":
                    self.agent.withdraw_enabled = True

    async def setup(self):
        self.add_behaviour(self.WithdrawBehaviour(period=5))
        self.add_behaviour(self.ControlBehaviour())