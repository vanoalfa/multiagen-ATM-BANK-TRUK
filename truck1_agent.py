import json, asyncio, time
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from common import save_log

# State truk
KAPASITAS_MAX = 100000000
kapasitas_sisa = 80000000  # contoh awal

class Truck1(Agent):
    class Dispatcher(CyclicBehaviour):
        async def run(self):
            global kapasitas_sisa
            msg = await self.receive(timeout=10)
            if not msg:
                return
            perf = msg.metadata.get("performative")
            conv = msg.metadata.get("conversation-id")
            content = json.loads(msg.body)

            # 1) Probe kapasitas
            if perf == "query-if" and content.get("type") == "probe_capacity":
                reply = {
                    "kapasitas_sisa": kapasitas_sisa,
                    "biaya_operasional": 50000
                }
                m = Message(to=str(msg.sender), body=json.dumps(reply))
                m.set_metadata("performative", "inform")
                m.set_metadata("conversation-id", conv)
                await self.send(m)
                print(f"TRUK-001 <- Bank1: query-if (probe_capacity)")
                print(f"TRUK-001 -> Bank1: inform (kapasitas={kapasitas_sisa})")
                save_log(str(self.agent.jid), str(msg.sender), "inform", reply, conv)

            # 2) Allocate request
            if perf == "request" and content.get("type") == "allocate":
                jumlah = content["jumlah"]
                print(f"TRUK-001 <- Bank1: request (allocate, jumlah={jumlah})")
                if jumlah <= kapasitas_sisa:
                    kapasitas_sisa -= jumlah
                    reply = {"status": "ok", "biaya_operasional": 50000}
                    m = Message(to=str(msg.sender), body=json.dumps(reply))
                    m.set_metadata("performative", "agree")
                    m.set_metadata("conversation-id", conv)
                    await self.send(m)
                    print(f"TRUK-001 -> Bank1: agree (alokasi {jumlah}, sisa={kapasitas_sisa})")
                    save_log(str(self.agent.jid), str(msg.sender), "agree", reply, conv)
                    print("Tujuan sudah tercapai. Proses komunikasi selesai (TRUK-001).")
                    await self.agent.stop()
                else:
                    reply = {"status": "gagal", "alasan": "kapasitas tidak cukup"}
                    m = Message(to=str(msg.sender), body=json.dumps(reply))
                    m.set_metadata("performative", "refuse")
                    m.set_metadata("conversation-id", conv)
                    await self.send(m)
                    print(f"TRUK-001 -> Bank1: refuse (gagal alokasi, kapasitas sisa={kapasitas_sisa})")
                    save_log(str(self.agent.jid), str(msg.sender), "refuse", reply, conv)
                    print("Tujuan sudah tercapai. Proses komunikasi selesai (TRUK-001).")
                    await self.agent.stop()

    async def setup(self):
        self.add_behaviour(self.Dispatcher())

# === main entry ===
async def main():
    a = Truck1("truk1@localhost", "1234")
    await a.start()
    while a.is_alive():
        await asyncio.sleep(1)
    await a.stop()

if __name__ == "__main__":
    asyncio.run(main())