import json, asyncio, time
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.message import Message
from common import save_log

class ATM1(Agent):
    class Scenario(OneShotBehaviour):
        async def run(self):
            bank_jid = "bank1@localhost"
            conv = f"conv-{int(time.time())}"

            # Step 1: request availability inquiry
            req = {
                "type": "availability_inquiry",
                "jumlah": 20000000
            }
            m = Message(to=bank_jid, body=json.dumps(req))
            m.set_metadata("performative", "request")
            m.set_metadata("conversation-id", conv)
            await self.send(m)
            print(f"ATM1 -> Bank1: request (availability_inquiry, jumlah={req['jumlah']})")
            save_log(str(self.agent.jid), bank_jid, "request", req, conv)

            # Step 2: receive options
            reply = await self.receive(timeout=5)
            if reply:
                rc = json.loads(reply.body)
                print(f"ATM1 <- Bank1: inform (opsi={len(rc['opsi'])})")
                save_log(str(self.agent.jid), str(reply.sender), "inform(received)", rc, conv)

                # pilih truk pertama yang tersedia
                opsi_truk = None
                for o in rc["opsi"]:
                    if o["status"] == "tersedia":
                        opsi_truk = o
                        break
                if not opsi_truk:
                    print("ATM1: Tidak ada truk tersedia")
                    print("Tujuan sudah tercapai. Proses komunikasi selesai (ATM1).")
                    await self.agent.stop()
                    return

                # Step 3: kirim booking request
                book = {
                    "type": "booking_request",
                    "jumlah": 20000000,
                    "truck_id": opsi_truk["truck_id"],
                    "jenis_layanan": "isi_uang"
                }
                m2 = Message(to=bank_jid, body=json.dumps(book))
                m2.set_metadata("performative", "request")
                m2.set_metadata("conversation-id", conv)
                await self.send(m2)
                print(f"ATM1 -> Bank1: request (booking_request, jumlah={book['jumlah']}, truck={book['truck_id']})")
                save_log(str(self.agent.jid), bank_jid, "request", book, conv)

                # Step 4: receive confirm/disconfirm
                r2 = await self.receive(timeout=5)
                if r2:
                    if r2.metadata.get("performative") == "confirm":
                        print(f"ATM1 <- Bank1: confirm (booking berhasil)")
                    else:
                        print(f"ATM1 <- Bank1: disconfirm (booking gagal)")
                    save_log(str(self.agent.jid), str(r2.sender), r2.metadata.get("performative"), json.loads(r2.body), conv)
                    print("Tujuan sudah tercapai. Proses komunikasi selesai (ATM1).")
                    await self.agent.stop()

    async def setup(self):
        self.add_behaviour(self.Scenario())

# === main entry ===
async def main():
    a = ATM1("atm1@localhost", "1234")
    await a.start()
    while a.is_alive():
        await asyncio.sleep(1)
    await a.stop()

if __name__ == "__main__":
    asyncio.run(main())