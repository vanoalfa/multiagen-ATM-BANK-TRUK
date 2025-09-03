import json, time, asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from common import save_log

# Mapping antara ID eksternal dan JID asli
TRUCK_MAP = {
    "TRUK-001": "truk1@localhost"
}

class Bank1(Agent):
    class Dispatcher(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return
            perf = msg.metadata.get("performative")
            conv = msg.metadata.get("conversation-id")
            content = json.loads(msg.body)

            # === 1) availability inquiry ===
            if perf == "request" and content.get("type") == "availability_inquiry":
                print(f"Bank1 <- {msg.sender}: request (availability_inquiry, jumlah={content['jumlah']})")
                save_log(str(self.agent.jid), str(msg.sender), "request(received)", content, conv)

                opsi = []
                for truck_id, truck_jid in TRUCK_MAP.items():
                    q = Message(to=truck_jid, body=json.dumps({"type": "probe_capacity"}))
                    q.set_metadata("performative", "query-if")
                    q.set_metadata("conversation-id", conv)
                    await self.send(q)
                    print(f"Bank1 -> {truck_id}: query-if (probe_capacity)")

                    r = await self.receive(timeout=3)
                    if r:
                        rc = json.loads(r.body)
                        opsi.append({
                            "truck_id": truck_id,  # pakai ID eksternal
                            "estimasi_epoch": int(time.time()) + 1800,
                            "biaya_operasional": rc["biaya_operasional"],
                            "kapasitas_sisa": rc["kapasitas_sisa"],
                            "status": "tersedia" if rc["kapasitas_sisa"] >= content["jumlah"] else "penuh"
                        })
                        print(f"Bank1 <- {truck_id}: inform (kapasitas={rc['kapasitas_sisa']})")

                reply = {
                    "type": "options",
                    "bank_id": "BANK1",
                    "opsi": opsi
                }
                m = Message(to=str(msg.sender), body=json.dumps(reply))
                m.set_metadata("performative", "inform")
                m.set_metadata("conversation-id", conv)
                await self.send(m)
                print(f"Bank1 -> {msg.sender}: inform (opsi truk dikirim)")
                save_log(str(self.agent.jid), str(msg.sender), "inform", reply, conv)

            # === 2) booking_request ===
            if perf == "request" and content.get("type") == "booking_request":
                truck_id = content["truck_id"]
                jumlah = content["jumlah"]
                print(f"Bank1 <- {msg.sender}: request (booking_request, jumlah={jumlah}, truck={truck_id})")
                save_log(str(self.agent.jid), str(msg.sender), "request(received)", content, conv)

                # mapping truck_id ke JID
                truck_jid = TRUCK_MAP.get(truck_id, None)
                if not truck_jid:
                    print(f"Bank1: ERROR, truck_id {truck_id} tidak dikenal.")
                    return

                req = {
                    "type": "allocate",
                    "jumlah": jumlah,
                    "jenis_layanan": content["jenis_layanan"]
                }
                m = Message(to=truck_jid, body=json.dumps(req))
                m.set_metadata("performative", "request")
                m.set_metadata("conversation-id", conv)
                await self.send(m)
                print(f"Bank1 -> {truck_id}: request (allocate, jumlah={jumlah})")

                r = await self.receive(timeout=5)
                if r:
                    rc = json.loads(r.body)
                    if r.metadata.get("performative") == "agree":
                        result = {
                            "type": "booking_result",
                            "booking_id": f"BK-{int(time.time())}",
                            "status": "konfirmasi",
                            "ringkasan": {
                                "truck_id": truck_id,
                                "estimasi_epoch": int(time.time()) + 1800,
                                "biaya_operasional": rc["biaya_operasional"]
                            }
                        }
                        out = Message(to=str(msg.sender), body=json.dumps(result))
                        out.set_metadata("performative", "confirm")
                        out.set_metadata("conversation-id", conv)
                        await self.send(out)
                        print(f"Bank1 -> {msg.sender}: confirm (booking berhasil dengan {truck_id})")
                        print("Tujuan sudah tercapai. Proses komunikasi selesai (Bank1).")
                        save_log(str(self.agent.jid), str(msg.sender), "confirm", result, conv)
                        await self.agent.stop()

                    else:
                        result = {
                            "type": "booking_result",
                            "booking_id": f"BK-{int(time.time())}",
                            "status": "gagal",
                            "alasan": rc.get("alasan", "truk tidak tersedia"),
                            "alternatif": []
                        }
                        out = Message(to=str(msg.sender), body=json.dumps(result))
                        out.set_metadata("performative", "disconfirm")
                        out.set_metadata("conversation-id", conv)
                        await self.send(out)
                        print(f"Bank1 -> {msg.sender}: disconfirm (booking gagal, alasan={result['alasan']})")
                        print("Tujuan sudah tercapai. Proses komunikasi selesai (Bank1).")
                        save_log(str(self.agent.jid), str(msg.sender), "disconfirm", result, conv)
                        await self.agent.stop()

    async def setup(self):
        self.add_behaviour(self.Dispatcher())

# === main entry ===
async def main():
    a = Bank1("bank1@localhost", "1234")
    await a.start()
    try:
        while a.is_alive():
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("KeyboardInterrupt, stopping agent...")
    await a.stop()

if __name__ == "__main__":
    asyncio.run(main())