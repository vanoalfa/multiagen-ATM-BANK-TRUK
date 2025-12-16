import json
import asyncio
import time
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from common import save_log, delayKomunikasi


class ATM(Agent):
    def __init__(self, jid, password, initial_balance, threshold=2000000, max_capacity=15000000):
        super().__init__(jid, password)
        self.balance = initial_balance
        self.threshold = threshold
        self.max_capacity = max_capacity
        self.refill_count = 0
        self.max_refills = 5
        self.pending_refill_amount = 0
        self.pending_refill_conv = None
        self.nasabah_notified_offline = False

    class Dispatcher(CyclicBehaviour):
        async def send_with_delay(self, message):
            await asyncio.sleep(delayKomunikasi)
            await self.send(message)

        async def notify_nasabah(self, status):
            msg = Message(
                to="nasabah1@localhost",
                body=json.dumps({
                    "type": "atm_status",
                    "status": status
                })
            )
            msg.set_metadata("performative", "inform")
            msg.set_metadata("conversation-id", str(time.time()))
            await self.send_with_delay(msg)
            if status == "offline":
                print("ATM1 | Status: OFFLINE (saldo di bawah threshold, penarikan nasabah dihentikan)")
            elif status == "online":
                print("ATM1 | Status: ONLINE (saldo di atas threshold, penarikan nasabah dibuka kembali)")

        #Kirim permintaan refill bila saldo di bawah threshold dan belum ada permintaan berjalan
        async def request_refill_if_needed(self):
            if self.agent.refill_count >= self.agent.max_refills:
                return
            if self.agent.balance >= self.agent.threshold:
                return
            if self.agent.pending_refill_amount > 0:
                return

            #Beri tahu agen nasabah bahwa ATM offline (sedang menunggu isi ulang)
            if not self.agent.nasabah_notified_offline:
                await self.notify_nasabah("offline")
                self.agent.nasabah_notified_offline = True

            needed_amount = self.agent.max_capacity - self.agent.balance
            if needed_amount <= 0:
                return

            conv_id = str(time.time())
            self.agent.pending_refill_amount = needed_amount
            self.agent.pending_refill_conv = conv_id

            req = {
                "type": "availability_inquiry",
                "jumlah": needed_amount
            }
            m = Message(to="bank1@localhost", body=json.dumps(req))
            m.set_metadata("performative", "request")
            m.set_metadata("conversation-id", conv_id)
            await self.send_with_delay(m)
            print(f"ATM1 -> BANK1 | Saldo rendah, minta isi ulang: {needed_amount:,} (conv {conv_id})")

        async def run(self):
            #cek saldo sebelum memproses pesan
            await self.request_refill_if_needed()

            msg = await self.receive(timeout=5)
            if not msg:
                return

            content = json.loads(msg.body)
            conv = msg.metadata.get("conversation-id")
            sender = str(msg.sender)

            #Respon Bank dan opsi truk
            if sender == "bank1@localhost" and content.get("opsi"):
                print(f"ATM1 <- BANK1 | Menerima opsi truk tersedia")
                #Pilih truk yang tersedia
                if content["opsi"] and len(content["opsi"]) > 0:
                    truck_info = content["opsi"][0]
                    print(f"ATM1 | Memilih truk: {truck_info.get('truck_id')}")
                    
                    #Gunakan jumlah yang sudah disimpan saat mengirim availability_inquiry
                    needed_amount = self.agent.pending_refill_amount
                    if needed_amount == 0:
                        #Fallback: hitung ulang jika tidak ada yang tersimpan
                        needed_amount = min(self.agent.max_capacity - self.agent.balance, 50_000_000)
                    
                    #Kirim booking request ke Bank
                    booking_req = {
                        "type": "booking_request",
                        "truck_id": truck_info.get("truck_id"),
                        "jumlah": needed_amount
                    }
                    booking_msg = Message(to="bank1@localhost", body=json.dumps(booking_req))
                    booking_msg.set_metadata("performative", "request")
                    booking_msg.set_metadata("conversation-id", conv)
                    await self.send_with_delay(booking_msg)
                    print(f"ATM1 -> BANK1 | Mengirim booking request: {booking_req['jumlah']:,}")

            #Konfirmasi booking dari bank
            if sender == "bank1@localhost" and content.get("status") == "ok" and "sisa_kapasitas" in content:
                print(f"ATM1 <- BANK1 | Menerima konfirmasi booking")
                print(f"ATM1 | Booking berhasil, sisa kapasitas truk: {content['sisa_kapasitas']:,}")

            #Pengisian ulang dari TRUCK
            if sender == "truk1@localhost" and content.get("type") == "refill":
                print(f"ATM1 <- TRUK1 | Menerima permintaan pengisian ulang")
                refill_amount = content.get("jumlah", 0)
                
                # Cek apakah sudah mencapai batas maksimal pengisian ulang
                if self.agent.refill_count >= self.agent.max_refills:
                    print(f"ATM1 -> TRUK1 | Pengisian ulang ditolak: sudah mencapai batas maksimal ({self.agent.max_refills}x)")
                    reply = {"status": "gagal", "alasan": f"Sudah mencapai batas maksimal pengisian ulang ({self.agent.max_refills}x)"}
                else:
                    # Hitung jumlah yang bisa diisi (tidak boleh melebihi max_capacity)
                    current_balance = self.agent.balance
                    max_refill = self.agent.max_capacity - current_balance
                    actual_refill = min(refill_amount, max_refill)
                    
                    if actual_refill > 0:
                        self.agent.balance += actual_refill
                        self.agent.refill_count += 1
                        # Reset pending_refill_amount setelah pengisian selesai
                        self.agent.pending_refill_amount = 0
                        self.agent.pending_refill_conv = None

                        # Jika saldo sudah di atas threshold, beri tahu nasabah ATM kembali online
                        if self.agent.balance >= self.agent.threshold and self.agent.nasabah_notified_offline:
                            await self.notify_nasabah("online")
                            self.agent.nasabah_notified_offline = False

                        print(f"ATM1 | Menerima pengisian ulang: {actual_refill:,}")
                        print(f"ATM1 | Saldo setelah diisi ulang: {self.agent.balance:,} (Pengisian ke-{self.agent.refill_count}/{self.agent.max_refills})")
                        
                        if actual_refill < refill_amount:
                            print(f"ATM1 | Peringatan: Hanya bisa diisi {actual_refill:,} karena batas maksimal kapasitas {self.agent.max_capacity:,}")
                        
                        reply = {"status": "ok", "jumlah_diisi": actual_refill, "saldo_sekarang": self.agent.balance}
                    else:
                        print(f"ATM1 -> TRUK1 | Pengisian ulang tidak diperlukan: saldo sudah mencapai maksimal")
                        reply = {"status": "gagal", "alasan": "Saldo sudah mencapai kapasitas maksimal"}
                
                out = Message(to=str(msg.sender), body=json.dumps(reply))
                out.set_metadata("performative", "inform")
                out.set_metadata("conversation-id", conv)
                await self.send_with_delay(out)
                print(f"ATM1 -> TRUK1 | Konfirmasi pengisian ulang")

            #Penarikan dari nasabah
            if content.get("type") == "withdraw":
                amount = content["amount"]

                if self.agent.balance >= amount:
                    self.agent.balance -= amount
                    reply = {"status": "ok", "sisa_saldo": self.agent.balance}
                else:
                    reply = {"status": "gagal", "alasan": "saldo ATM tidak cukup"}

                out = Message(to=str(msg.sender), body=json.dumps(reply))
                out.set_metadata("performative", "inform")
                out.set_metadata("conversation-id", conv)
                await self.send_with_delay(out)

                save_log(self.agent.jid, msg.sender, "inform", reply, conv)
                print(f"ATM1 | Tarik {amount:,} | Saldo: {self.agent.balance:,}")

                #Isi ulang
                if self.agent.balance < self.agent.threshold:
                    # Hanya log info; permintaan refill dikelola proaktif oleh request_refill_if_needed
                    if self.agent.refill_count >= self.agent.max_refills:
                        print(f"ATM1 | Saldo rendah tapi pengisian ulang sudah mencapai batas maksimal ({self.agent.max_refills}x)")
                    else:
                        await self.request_refill_if_needed()

    async def setup(self):
        self.add_behaviour(self.Dispatcher())


# Alias kelas agar sesuai dengan import di main.py
class ATM1(ATM):
    pass