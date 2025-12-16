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
- Evaluasi log komunikasi disediakan melalui `evaluasi.py`.

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

## Evaluasi
- Jalankan evaluasi dari log:
  ```bash
  python evaluasi.py --log logs/messages.log --output logs/evaluasi.json
  ```
- Ringkasan yang dihitung:
  - **Total pesan**: jumlah seluruh pesan yang tercatat.
  - **Distribusi performative**: hitungan per jenis performative (inform/request/agree/dll).
  - **Distribusi pengirim**: hitungan pesan per agen pengirim.
  - **Latensi per percakapan (makespan percakapan)**: durasi per `conversation_id`, dihitung dari timestamp pesan pertama hingga pesan terakhir dalam percakapan itu (berapa lama satu percakapan berlangsung).
  - **Response time**: selisih antara pesan pertama dan pesan kedua pada percakapan yang sama (perkiraan waktu respon awal terhadap sebuah permintaan).
  - **Total makespan simulasi**: durasi global dari pesan pertama yang tercatat hingga pesan terakhir (lama keseluruhan komunikasi yang terekam di log).
  - **Reassign count**: jumlah pesan dengan performative `reassign` (misal skenario pengalihan tugas/sumber daya).
  - **Failure count & failure rate**: banyaknya pesan performative `failure` dan persentasenya terhadap total pesan.
  - **Recovery time**: pada percakapan yang mengalami `failure`, selisih waktu dari pesan failure ke pesan non-failure pertama berikutnya (indikasi seberapa cepat pulih).

Contoh hasil (cuplikan keluaran terminal / evaluasi.json):
```json
{
  "total_messages": 1434,
  "by_performative": {
    "inform": 1434
  },
  "by_sender": {
    "atm1@localhost": 970,
    "bank1@localhost": 464
  },
  "latency_per_conversation_seconds": {
    "count": 1005,
    "min": 0.0,
    "max": 1.6315698623657227,
    "avg": 0.02432077488495936
  },
  "response_time_seconds": {
    "count": 429,
    "min": 0.01328587532043457,
    "max": 1.6315698623657227,
    "avg": 0.05697524186336633
  },
  "total_makespan_seconds": 17996.079337120056,
  "failure_count": 0,
  "failure_rate": 0.0,
  "reassign_count": 0,
  "recovery_time_after_failure_seconds": {
    "count": 0,
    "min": 0,
    "max": 0,
    "avg": 0
  }
}
```

Penjelasan contoh hasil di atas:
- **"total_messages": 1434**  
  Artinya selama simulasi tercatat 1434 pesan yang dikirim antar agen.

- **"by_performative": {"inform": 1434}**  
  Semua pesan yang terekam menggunakan performative `inform` (tidak ada `request`, `agree`, dll yang tercatat oleh logger saat ini).

- **"by_sender": {"atm1@localhost": 970, "bank1@localhost": 464}**  
  - ATM mengirim 970 pesan (misalnya balasan ke Nasabah, permintaan/log ke Bank, konfirmasi ke Truk).  
  - Bank mengirim 464 pesan (misalnya probe ke Truk, opsi ke ATM, konfirmasi booking, instruksi refill).

- **"latency_per_conversation_seconds"**  
  - `"count": 1005` → ada 1005 percakapan (berbasis `conversation_id`) yang dianalisis.  
  - `"min": 0.0` → percakapan tercepat selesai instan (semua pesan waktu yang sama atau hanya 1 pesan).  
  - `"max": 1.63...` → percakapan paling lama membutuhkan sekitar 1,63 detik dari pesan pertama hingga terakhir.  
  - `"avg": 0.0243...` → rata-rata satu percakapan selesai dalam ~0,024 detik (24 ms), menunjukkan komunikasi antar agen cukup cepat.

- **"response_time_seconds"**  
  - `"count": 429` → hanya 429 percakapan yang punya minimal 2 pesan (sehingga response time bisa dihitung).  
  - `"min": 0.0132...` → respon tercepat hanya sekitar 0,013 detik (13 ms) setelah pesan pertama.  
  - `"max": 1.63...` → respon paling lambat sekitar 1,63 detik.  
  - `"avg": 0.0569...` → rata-rata waktu respon awal sekitar 0,056 detik (56 ms).

- **"total_makespan_seconds": 17996.0793...**  
  Durasi total simulasi (dari pesan pertama yang tercatat sampai pesan terakhir) sekitar 17.996 detik (~5 jam jika log berasal dari beberapa sesi, atau ~5 jam waktu simulasi/eksekusi).

- **"failure_count": 0, "failure_rate": 0.0**  
  Tidak ada pesan dengan performative `failure`, sehingga secara log tidak terlihat kegagalan protokol komunikasi.

- **"reassign_count": 0**  
  Tidak ada pesan dengan performative `reassign`, artinya tidak ada skenario pengalihan tugas yang tercatat.

- **"recovery_time_after_failure_seconds": {"count": 0, ...}**  
  Karena tidak ada `failure`, tidak ada recovery time yang bisa dihitung (semua nilai 0).

## Lisensi
Gunakan sesuai kebutuhan akademik/tugas

