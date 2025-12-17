import asyncio
import argparse
import pandas as pd
from atm1_agent import ATM1
from bank1_agent import Bank1
from truck1_agent import Truck1
from nasabah1_agent import Nasabah1

CSV_PATH = "data/atm_cash_management_dataset.csv"

# Nilai default (bisa diubah lewat terminal)
DEFAULT_HARI = "Monday"   # Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
DEFAULT_WAKTU = "Morning" # Morning, Afternoon, Evening, Night

INITIAL_ATM_BALANCE = 15000000

def load_withdrawal_amount(hari: str, waktu: str):
    df = pd.read_csv(CSV_PATH)

    filtered = df[
        (df["Day_of_Week"] == hari) &
        (df["Time_of_Day"] == waktu)
    ]

    total_uang = (filtered["Total_Withdrawals"]).sum()

    return int(total_uang / 6)

async def main(hari: str, waktu: str):
    tarik_per_transaksi = load_withdrawal_amount(hari, waktu)

    print("=== KONFIGURASI SIMULASI ===")
    print(f"Hari         : {hari}")
    print(f"Waktu        : {waktu}")
    print(f"Kapasitas ATM: {INITIAL_ATM_BALANCE:,}")
    print(f"Tarik/Transaksi Nasabah: {tarik_per_transaksi:,}")
    print("===========================")

    atm = ATM1("atm1@localhost", "1234", INITIAL_ATM_BALANCE)
    bank = Bank1("bank1@localhost", "1234")
    truck = Truck1("truk1@localhost", "1234")
    nasabah = Nasabah1(
        "nasabah1@localhost",
        "1234",
        tarik_per_transaksi
    )

    await bank.start()
    await truck.start()
    await atm.start()
    await nasabah.start()

    while True:
        await asyncio.sleep(1)

        # Hentikan simulasi bila pengisian ulang sudah mencapai batas
        # dan saldo kembali turun di bawah threshold (ATM tidak bisa diisi lagi).
        if atm.refill_count >= atm.max_refills and atm.balance < atm.threshold:
            print(
                f"Simulasi selesai: pengisian ulang mencapai {atm.refill_count}x, "
                f"saldo ATM {atm.balance:,} di bawah threshold {atm.threshold:,}."
            )
            await nasabah.stop()
            await atm.stop()
            await bank.stop()
            await truck.stop()
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulasi ATM Multi-Agent")
    parser.add_argument("--hari", "-d", default=DEFAULT_HARI,
                        help="Pilihan hari: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday")
    parser.add_argument("--waktu", "-t", default=DEFAULT_WAKTU,
                        help="Pilihan waktu: Morning, Afternoon, Evening, Night")
    args = parser.parse_args()

    asyncio.run(main(args.hari, args.waktu))