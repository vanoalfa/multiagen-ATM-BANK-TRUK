import json
import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from common import save_log, delayKomunikasi

TRUCK_JID = "truk1@localhost"

class Bank(Agent):
    class Dispatcher(CyclicBehaviour):
        async def send_with_delay(self, message):
            await asyncio.sleep(delayKomunikasi)
            await self.send(message)

        async def run(self):
            msg = await self.receive(timeout=5)
            if not msg:
                return

            content = json.loads(msg.body)
            conv = msg.metadata.get("conversation-id")
            sender = str(msg.sender)

            #Pesan dari ATM
            if content.get("type") == "availability_inquiry":
                print(f"BANK1 <- ATM1 | Menerima permintaan isi ulang")
                probe = Message(to=TRUCK_JID, body=json.dumps({"type": "probe"}))
                probe.set_metadata("performative", "query-if")
                probe.set_metadata("conversation-id", conv)
                await self.send_with_delay(probe)
                print(f"BANK1 -> TRUK1 | Cek ketersediaan truk")

                # Tunggu response dari truk
                r = await self.receive(timeout=5)
                if not r:
                    print(f"BANK1 | Timeout menunggu response dari TRUK1")
                    return
                
                # Verifikasi bahwa message dari truk dan untuk conversation ini
                if (str(r.sender) != TRUCK_JID or 
                    r.metadata.get("conversation-id") != conv):
                    print(f"BANK1 | Menerima message yang tidak sesuai, mengabaikan")
                    return
                
                rc = json.loads(r.body)
                print(f"BANK1 <- TRUK1 | Kapasitas: {rc['kapasitas']:,}")

                reply = {
                    "opsi": [{
                        "truck_id": "TRUK-001",
                        "kapasitas": rc["kapasitas"],
                        "status": "tersedia"
                    }]
                }

                out = Message(to=str(msg.sender), body=json.dumps(reply))
                out.set_metadata("performative", "inform")
                out.set_metadata("conversation-id", conv)
                await self.send_with_delay(out)
                print(f"BANK1 -> ATM1 | Mengirim opsi truk tersedia")

                save_log(self.agent.jid, msg.sender, "inform", reply, conv)

            #Booking request dari atm
            if content.get("type") == "booking_request":
                print(f"BANK1 <- ATM1 | Menerima booking request")
                alloc = Message(
                    to=TRUCK_JID,
                    body=json.dumps({
                        "type": "allocate",
                        "jumlah": content["jumlah"]
                    })
                )
                alloc.set_metadata("performative", "request")
                alloc.set_metadata("conversation-id", conv)
                await self.send_with_delay(alloc)
                print(f"BANK1 -> TRUK1 | Alokasi uang: {content['jumlah']:,}")

                # Tunggu response dari truk
                r = await self.receive(timeout=5)
                if not r:
                    print(f"BANK1 | Timeout menunggu response dari TRUK1")
                    return
                
                # Verifikasi bahwa message dari truk dan untuk conversation ini
                if (str(r.sender) != TRUCK_JID or 
                    r.metadata.get("conversation-id") != conv):
                    print(f"BANK1 | Menerima message yang tidak sesuai, mengabaikan")
                    return
                
                # Kirim konfirmasi ke ATM
                out = Message(to=str(msg.sender), body=r.body)
                out.set_metadata("performative", "confirm")
                out.set_metadata("conversation-id", conv)
                await self.send_with_delay(out)
                print(f"BANK1 -> ATM1 | Konfirmasi booking")
                
                # Instruksikan TRUCK untuk mengisi ulang ATM
                rc_content = json.loads(r.body)
                refill_msg = Message(
                    to=TRUCK_JID,
                    body=json.dumps({
                        "type": "refill_atm",
                        "atm_jid": str(msg.sender),
                        "jumlah": content["jumlah"]
                    })
                )
                refill_msg.set_metadata("performative", "request")
                refill_msg.set_metadata("conversation-id", conv)
                await self.send_with_delay(refill_msg)
                print(f"BANK1 -> TRUK1 | Instruksi mengisi ulang ATM: {content['jumlah']:,}")

    async def setup(self):
        self.add_behaviour(self.Dispatcher())


#agar sesuai dengan import di main.py
class Bank1(Bank):
    pass