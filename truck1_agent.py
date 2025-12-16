import json
import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from common import delayKomunikasi

Kapasitas = 100000000

class Truck(Agent):
    class Dispatcher(CyclicBehaviour):
        async def send_with_delay(self, message):
            await asyncio.sleep(delayKomunikasi)
            await self.send(message)

        async def run(self):
            global Kapasitas
            msg = await self.receive(timeout=5)
            if not msg:
                return

            content = json.loads(msg.body)
            conv = msg.metadata.get("conversation-id")

            if content.get("type") == "probe":
                print(f"TRUK1 <- BANK1 | Menerima probe")
                reply = {"kapasitas": Kapasitas}
                m = Message(to=str(msg.sender), body=json.dumps(reply))
                m.set_metadata("performative", "inform")
                m.set_metadata("conversation-id", conv)
                await self.send_with_delay(m)
                print(f"TRUK1 -> BANK1 | Mengirim kapasitas: {Kapasitas:,}")

            if content.get("type") == "allocate":
                print(f"TRUK1 <- BANK1 | Menerima alokasi: {content['jumlah']:,}")
                Kapasitas -= content["jumlah"]
                reply = {"status": "ok", "sisa_kapasitas": Kapasitas}
                m = Message(to=str(msg.sender), body=json.dumps(reply))
                m.set_metadata("performative", "agree")
                m.set_metadata("conversation-id", conv)
                await self.send_with_delay(m)
                print(f"TRUK1 -> BANK1 | Konfirmasi alokasi, sisa kapasitas: {Kapasitas:,}")

            if content.get("type") == "refill_atm":
                print(f"TRUK1 <- BANK1 | Menerima instruksi mengisi ulang ATM")
                atm_jid = content.get("atm_jid")
                jumlah = content.get("jumlah", 0)
                
                # Kirim pesan ke ATM untuk pengisian ulang
                refill_msg = Message(
                    to=atm_jid,
                    body=json.dumps({
                        "type": "refill",
                        "jumlah": jumlah
                    })
                )
                refill_msg.set_metadata("performative", "request")
                refill_msg.set_metadata("conversation-id", conv)
                await self.send_with_delay(refill_msg)
                print(f"TRUK1 -> ATM1 | Mengisi ulang ATM: {jumlah:,}")
                
                # Tunggu konfirmasi dari ATM
                response = await self.receive(timeout=5)
                if response and str(response.sender) == atm_jid:
                    resp_content = json.loads(response.body)
                    if resp_content.get("status") == "ok":
                        print(f"TRUK1 <- ATM1 | Pengisian ulang berhasil: {resp_content.get('jumlah_diisi', 0):,}")
                        print(f"TRUK1 | Saldo ATM setelah pengisian: {resp_content.get('saldo_sekarang', 0):,}")
                    else:
                        print(f"TRUK1 <- ATM1 | Pengisian ulang gagal: {resp_content.get('alasan', 'Tidak diketahui')}")
                else:
                    print(f"TRUK1 | Timeout menunggu konfirmasi dari ATM")

    async def setup(self):
        self.add_behaviour(self.Dispatcher())


# Alias kelas agar sesuai dengan import di main.py
class Truck1(Truck):
    pass