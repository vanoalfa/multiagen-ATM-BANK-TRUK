# Sistem Multiagen ATM (Tugas 1)

Proyek ini mensimulasikan interaksi beberapa agen: ATM, Bank, Truk pengisi uang, dan Nasabah. Simulasi berjalan berbasis SPADE (XMPP) dan bisa dikonfigurasi lewat argumen terminal.

## Fitur Utama
- Penarikan tunai oleh agen Nasabah ke ATM.
- Permintaan isi ulang otomatis ketika saldo ATM di bawah threshold.
- Bank melakukan pengecekan ketersediaan Truk dan menginstruksikan pengisian.
- Batas maksimal pengisian ulang ATM (5x), dengan penghentian simulasi ketika batas tercapai dan saldo kembali turun di bawah threshold.
- Penundaan komunikasi (`delayKomunikasi`) terpusat di `common.py`.
- Nasabah berhenti menarik saat ATM dalam status offline (menunggu isi ulang) dan kembali menarik saat online.
- Pemilihan hari/waktu simulasi via argumen CLI.

## Prasyarat
- Python 3.10+ (disarankan).
- Dependensi SPADE dan pandas terpasang di environment/venv Anda.

## Menjalankan Simulasi (Terminal)
Aktifkan virtual environment Anda (jika ada), lalu jalankan:
```bash
python main.py --hari Monday --waktu Morning
```
Argumen:
- `--hari` / `-d` : Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday (default: Monday)
- `--waktu` / `-t`: Morning, Afternoon, Evening, Night (default: Morning)

Output awal akan menampilkan konfigurasi simulasi (hari, waktu, kapasitas ATM, dan tarik per transaksi).

## Struktur Agen (ringkas)
- `atm1_agent.py`: logika ATM, cek threshold, kirim permintaan refill, terima pengisian, broadcast status online/offline ke Nasabah.
- `bank1_agent.py`: menerima permintaan refill, cek truk, kirim opsi truk, kirim konfirmasi booking, instruksikan truk refill.
- `truck1_agent.py`: merespons probe/allocate, mengisi ulang ATM sesuai instruksi Bank.
- `nasabah1_agent.py`: mengirim permintaan tarik berkala; berhenti ketika ATM offline dan lanjut ketika ATM online.
- `common.py`: menyimpan `delayKomunikasi` dan utilitas log.
- `main.py`: titik masuk simulasi; memulai semua agen dan menghentikan simulasi saat batas refill tercapai dan saldo jatuh di bawah threshold.

## Catatan Penghentian Simulasi
Simulasi berhenti otomatis ketika:
- `refill_count` mencapai 5x **dan**
- saldo ATM kembali di bawah `threshold`.

## Logging
- Log pesan agen dicatat di direktori `logs/` (lihat `log.json` atau `logs/messages.log` jika tersedia).
## Dataset
Dataset yang digunakan diambil dari: https://www.kaggle.com/datasets/zoya77/atm-cash-demand-forecasting-and-management
## Lisensi
Gunakan sesuai kebutuhan akademik/tugas


