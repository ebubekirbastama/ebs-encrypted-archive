import sys
import os
import json
import struct
import time
import datetime
from pathlib import Path
from typing import List, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import Type, hash_secret_raw
import secrets


MAGIC = b"ENCPACKv1"
CHUNK_SIZE = 1024 * 1024  # 1 MB


# Kriptografi yardımcı sınıfı
class KriptoYardimci:
    @staticmethod
    def anahtar_turet(parola: str, salt: bytes, time_cost=2, memory_cost=102400, parallelism=8, key_len=32) -> bytes:
        pw_bytes = parola.encode("utf-8")
        return hash_secret_raw(secret=pw_bytes, salt=salt, time_cost=time_cost,
                               memory_cost=memory_cost, parallelism=parallelism,
                               hash_len=key_len, type=Type.ID)

    @staticmethod
    def paket_olustur(dosya_listesi: List[Tuple[Path, Path]], parola: str, cikis_yolu: Path, argon_params: dict):
        """
        dosya_listesi: [(tam_dosya_yolu: Path, göreceli_yol: Path), ...]
        """
        salt = secrets.token_bytes(16)
        key = KriptoYardimci.anahtar_turet(parola, salt, **argon_params)
        aesgcm = AESGCM(key)

        metadata = {"dosyalar": [], "olusturma_tarihi": time.time()}

        with open(cikis_yolu, "wb+") as out_f:
            # Başlık yaz
            out_f.write(MAGIC)
            out_f.write(struct.pack("B", len(salt)))
            out_f.write(salt)
            out_f.write(struct.pack("I", argon_params["time_cost"]))
            out_f.write(struct.pack("I", argon_params["memory_cost"]))
            out_f.write(struct.pack("B", argon_params["parallelism"]))
            out_f.write(struct.pack("Q", 0))  # meta uzunluğu için placeholder

            for dosya, goreceli_yol in dosya_listesi:
                dosya_meta = {
                    "goreceli_yol": str(goreceli_yol).replace("\\", "/"),  # Unix tarzı yol işaretçisi
                    "orjinal_boyut": dosya.stat().st_size,
                    "chunklar": []
                }
                with open(dosya, "rb") as f:
                    idx = 0
                    while True:
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        nonce = secrets.token_bytes(12)
                        ct = aesgcm.encrypt(nonce, chunk, None)
                        pos = out_f.tell()
                        out_f.write(struct.pack("B", len(nonce)))
                        out_f.write(nonce)
                        out_f.write(struct.pack("Q", len(ct)))
                        out_f.write(ct)
                        dosya_meta["chunklar"].append({"index": idx, "pos": pos})
                        idx += 1
                metadata["dosyalar"].append(dosya_meta)

            meta_bytes = json.dumps(metadata).encode("utf-8")
            meta_len = len(meta_bytes)
            out_f.write(meta_bytes)

            # Meta uzunluğunu başlıktaki placeholder'a yaz
            out_f.seek(len(MAGIC) + 1 + len(salt) + 4 + 4 + 1)
            out_f.write(struct.pack("Q", meta_len))

    @staticmethod
    def paket_icerigini_listele(paket_yolu: Path) -> dict:
        with open(paket_yolu, "rb") as f:
            magic = f.read(len(MAGIC))
            if magic != MAGIC:
                raise ValueError("Bu dosya geçerli bir encpack paketi değil!")
            salt_len = struct.unpack("B", f.read(1))[0]
            salt = f.read(salt_len)
            time_cost = struct.unpack("I", f.read(4))[0]
            memory_cost = struct.unpack("I", f.read(4))[0]
            parallelism = struct.unpack("B", f.read(1))[0]
            meta_len = struct.unpack("Q", f.read(8))[0]

            f.seek(-meta_len, os.SEEK_END)
            meta = json.loads(f.read(meta_len).decode("utf-8"))
            return {
                "argon": {
                    "time_cost": time_cost,
                    "memory_cost": memory_cost,
                    "parallelism": parallelism,
                    "salt_hex": salt.hex()
                },
                "meta": meta
            }


    @staticmethod
    def paket_cikar(paket_yolu: Path, parola: str, cikis_klasoru: Path):
        import datetime
    
        # Alt klasör oluştur
        zaman_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        cikis_klasoru = cikis_klasoru / f"ebs_cikti_{zaman_str}"
        cikis_klasoru.mkdir(parents=True, exist_ok=True)
    
        with open(paket_yolu, "rb") as f:
            magic = f.read(len(MAGIC))
            if magic != MAGIC:
                raise ValueError("Bu dosya geçerli bir encpack paketi değil!")
            salt_len = struct.unpack("B", f.read(1))[0]
            salt = f.read(salt_len)
            time_cost = struct.unpack("I", f.read(4))[0]
            memory_cost = struct.unpack("I", f.read(4))[0]
            parallelism = struct.unpack("B", f.read(1))[0]
            meta_len = struct.unpack("Q", f.read(8))[0]
    
            f.seek(-meta_len, os.SEEK_END)
            meta = json.loads(f.read(meta_len).decode("utf-8"))
    
            key = KriptoYardimci.anahtar_turet(parola, salt, time_cost=time_cost, memory_cost=memory_cost, parallelism=parallelism)
            aesgcm = AESGCM(key)
    
            for dosya_meta in meta.get("dosyalar", []):
                goreceli_yol = Path(dosya_meta["goreceli_yol"])
                dosya_cikti = cikis_klasoru / goreceli_yol
                dosya_cikti.parent.mkdir(parents=True, exist_ok=True)  # Klasörleri oluştur
                with open(dosya_cikti, "wb") as wf:
                    for chunk in dosya_meta["chunklar"]:
                        f.seek(chunk["pos"])
                        nlen = struct.unpack("B", f.read(1))[0]
                        nonce = f.read(nlen)
                        ct_len = struct.unpack("Q", f.read(8))[0]
                        ct = f.read(ct_len)
                        try:
                            pt = aesgcm.decrypt(nonce, ct, None)
                        except Exception:
                            raise ValueError("Parola yanlış veya dosya bozuk!")
                        wf.write(pt)



# Thread sinyalleri için sınıf
class IslemSinyalleri(QtCore.QObject):
    bitti = QtCore.Signal(object)
    hata = QtCore.Signal(object)


# İşçi thread sınıfı
class IslemThread(QtCore.QThread):
    def __init__(self, fonksiyon, *args, **kwargs):
        super().__init__()
        self.fonksiyon = fonksiyon
        self.args = args
        self.kwargs = kwargs
        self.sinyaller = IslemSinyalleri()

    def run(self):
        try:
            sonuc = self.fonksiyon(*self.args, **self.kwargs)
            self.sinyaller.bitti.emit(sonuc)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            self.sinyaller.hata.emit(tb)


# Ana pencere sınıfı
class AnaPencere(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EncPack - Şifreli Dosya Paketi Oluşturucu")
        self.resize(900, 600)

        self.thread = None  # Çalışan thread referansı

        merkez = QtWidgets.QWidget()
        self.setCentralWidget(merkez)
        ana_duzen = QtWidgets.QVBoxLayout(merkez)
        ana_duzen.setContentsMargins(12, 12, 12, 12)
        ana_duzen.setSpacing(10)

        # Üst kısım (başlık ve butonlar)
        ust_duzen = QtWidgets.QHBoxLayout()
        baslik = QtWidgets.QLabel("EncPack - Şifreli Paketleyici (Eğitim Amaçlı)")
        baslik.setObjectName("baslikLabel")
        baslik.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        ust_duzen.addWidget(baslik)

        self.btn_dosya_ekle = QtWidgets.QPushButton("Dosya Ekle")
        self.btn_klasor_ekle = QtWidgets.QPushButton("Klasör Ekle")
        self.btn_paket_olustur = QtWidgets.QPushButton("Paket Oluştur")
        self.btn_paket_listele = QtWidgets.QPushButton("Paketi Listele")
        self.btn_paket_cikar = QtWidgets.QPushButton("Paketi Çıkar")
        ust_duzen.addWidget(self.btn_dosya_ekle)
        ust_duzen.addWidget(self.btn_klasor_ekle)
        ust_duzen.addWidget(self.btn_paket_olustur)
        ust_duzen.addWidget(self.btn_paket_listele)
        ust_duzen.addWidget(self.btn_paket_cikar)

        ana_duzen.addLayout(ust_duzen)

        # Orta kısım (dosya listesi ve ayarlar)
        orta_duzen = QtWidgets.QHBoxLayout()

        # Dosya listesi sol panel
        self.dosya_model = QtGui.QStandardItemModel()
        self.dosya_listesi = QtWidgets.QListView()
        self.dosya_listesi.setModel(self.dosya_model)
        self.dosya_listesi.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        sol_panel = QtWidgets.QVBoxLayout()
        sol_panel.addWidget(QtWidgets.QLabel("Paketlenecek Dosyalar:"))
        sol_panel.addWidget(self.dosya_listesi)

        btn_kaldir = QtWidgets.QPushButton("Seçilenleri Kaldır")
        btn_temizle = QtWidgets.QPushButton("Listeyi Temizle")
        alt_btn_duzen = QtWidgets.QHBoxLayout()
        alt_btn_duzen.addWidget(btn_kaldir)
        alt_btn_duzen.addWidget(btn_temizle)
        sol_panel.addLayout(alt_btn_duzen)

        orta_duzen.addLayout(sol_panel, 3)

        # Sağ panel (ayarlar + log)
        sag_panel = QtWidgets.QVBoxLayout()
        sag_panel.addWidget(QtWidgets.QLabel("Ayarlar"))

        self.pw_giris = QtWidgets.QLineEdit()
        self.pw_giris.setEchoMode(QtWidgets.QLineEdit.Password)
        self.pw_giris.setPlaceholderText("Paket için parola giriniz")
        sag_panel.addWidget(QtWidgets.QLabel("Parola:"))
        sag_panel.addWidget(self.pw_giris)

        self.time_spin = QtWidgets.QSpinBox()
        self.time_spin.setRange(1, 8)
        self.time_spin.setValue(2)
        sag_panel.addWidget(QtWidgets.QLabel("Argon2 zaman maliyeti:"))
        sag_panel.addWidget(self.time_spin)

        self.mem_spin = QtWidgets.QSpinBox()
        self.mem_spin.setRange(32, 1024000)
        self.mem_spin.setValue(102400)
        sag_panel.addWidget(QtWidgets.QLabel("Argon2 bellek maliyeti (KiB):"))
        sag_panel.addWidget(self.mem_spin)

        self.par_spin = QtWidgets.QSpinBox()
        self.par_spin.setRange(1, 16)
        self.par_spin.setValue(8)
        sag_panel.addWidget(QtWidgets.QLabel("Argon2 paralellik:"))
        sag_panel.addWidget(self.par_spin)

        sag_panel.addStretch(1)
        sag_panel.addWidget(QtWidgets.QLabel("Log"))
        self.log_alani = QtWidgets.QPlainTextEdit()
        self.log_alani.setReadOnly(True)
        self.log_alani.setMaximumBlockCount(1000)
        sag_panel.addWidget(self.log_alani, 2)

        orta_duzen.addLayout(sag_panel, 2)

        ana_duzen.addLayout(orta_duzen)

        # Alt kısım (durum çubuğu)
        self.durum_cubugu = QtWidgets.QLabel("Hazır")
        ana_duzen.addWidget(self.durum_cubugu)

        # Bağlantılar
        self.btn_dosya_ekle.clicked.connect(self.dosya_ekle)
        self.btn_klasor_ekle.clicked.connect(self.klasor_ekle)
        self.btn_paket_olustur.clicked.connect(self.paket_olustur)
        self.btn_paket_listele.clicked.connect(self.paket_listele)
        self.btn_paket_cikar.clicked.connect(self.paket_cikar)
        btn_kaldir.clicked.connect(self.secilenleri_kaldir)
        btn_temizle.clicked.connect(self.listeyi_temizle)

        # El simgesi için: butonlar üzerine gelince cursor değişsin
        for btn in [self.btn_dosya_ekle, self.btn_klasor_ekle, self.btn_paket_olustur,
                    self.btn_paket_listele, self.btn_paket_cikar, btn_kaldir, btn_temizle]:
            btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        # Stil (QSS)
        self.setStyleSheet("""
            #baslikLabel { font-size: 18pt; font-weight: 600; }
            QPushButton { padding: 8px 12px; border-radius: 8px; }
            QListView { background: #f6f7fb; border: 1px solid #ddd; }
            QPlainTextEdit { background: #0f1720; color: #e6eef8; border-radius: 8px; padding: 8px; }
        """)

    def log_yaz(self, *args):
        zaman = time.strftime("%Y-%m-%d %H:%M:%S")
        self.log_alani.appendPlainText(f"[{zaman}] " + " ".join(map(str, args)))

    def dosya_ekle(self):
        dosyalar, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Paketlenecek dosyaları seçin")
        if dosyalar:
            mevcut_dosya_yollar = set()
            for i in range(self.dosya_model.rowCount()):
                data = self.dosya_model.item(i).data()
                if isinstance(data, tuple):
                    mevcut_dosya_yollar.add(data[0])
                else:
                    mevcut_dosya_yollar.add(data)

            eklenecek_sayisi = 0
            for d in dosyalar:
                path_d = Path(d)
                if path_d not in mevcut_dosya_yollar:
                    item = QtGui.QStandardItem(path_d.name)
                    # Göreceli yol olarak sadece dosya adı (dosya tekil)
                    item.setData((path_d, path_d.name))
                    self.dosya_model.appendRow(item)
                    eklenecek_sayisi += 1
            self.log_yaz(f"{eklenecek_sayisi} dosya eklendi.")

    def klasor_ekle(self):
        klasor = QtWidgets.QFileDialog.getExistingDirectory(self, "Klasör seçin")
        if klasor:
            klasor_path = Path(klasor)
            dosyalar = [p for p in klasor_path.rglob('*') if p.is_file()]
            if not dosyalar:
                QtWidgets.QMessageBox.information(self, "Bilgi", "Seçilen klasörde dosya bulunamadı.")
                return

            mevcut_dosya_yollar = set()
            for i in range(self.dosya_model.rowCount()):
                data = self.dosya_model.item(i).data()
                if isinstance(data, tuple):
                    mevcut_dosya_yollar.add(data[0])
                else:
                    mevcut_dosya_yollar.add(data)

            eklenecek_sayisi = 0
            for dosya in dosyalar:
                if dosya not in mevcut_dosya_yollar:
                    # Göreceli yol klasör kökünden itibaren
                    goreceli_yol = dosya.relative_to(klasor_path)
                    item = QtGui.QStandardItem(str(goreceli_yol))
                    item.setData((dosya, goreceli_yol))
                    self.dosya_model.appendRow(item)
                    eklenecek_sayisi += 1

            self.log_yaz(f"{eklenecek_sayisi} dosya klasörden (alt klasörler dahil) eklendi.")

    def secilenleri_kaldir(self):
        secilenler = self.dosya_listesi.selectionModel().selectedIndexes()
        for index in sorted(secilenler, reverse=True):
            self.dosya_model.removeRow(index.row())
        self.log_yaz("Seçilen dosyalar kaldırıldı.")

    def listeyi_temizle(self):
        self.dosya_model.clear()
        self.log_yaz("Dosya listesi temizlendi.")

    def parola_al(self):
        pw = self.pw_giris.text()
        if not pw:
            pw, ok = QtWidgets.QInputDialog.getText(self, "Parola", "Paketi korumak için parola girin:", QtWidgets.QLineEdit.Password)
            if not ok or not pw:
                raise ValueError("Parola gerekli.")
        return pw

    def paket_olustur(self):
        try:
            dosya_listesi = [self.dosya_model.item(i).data() for i in range(self.dosya_model.rowCount())]
            if not dosya_listesi:
                QtWidgets.QMessageBox.warning(self, "Uyarı", "Lütfen paketlemek için en az bir dosya seçin.")
                return
            cikis_dosya, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Paket olarak kaydet", filter="EncPack dosyaları (*.encpack)")
            if not cikis_dosya:
                return
            parola = self.parola_al()
            argon_params = {
                "time_cost": self.time_spin.value(),
                "memory_cost": self.mem_spin.value(),
                "parallelism": self.par_spin.value()
            }
            self.durum_cubugu.setText("Paket oluşturuluyor...")
            QtWidgets.QApplication.processEvents()

            self.thread = IslemThread(KriptoYardimci.paket_olustur, dosya_listesi, parola, Path(cikis_dosya), argon_params)
            self.thread.sinyaller.bitti.connect(lambda res: self.islem_bitti(f"Paket oluşturuldu: {cikis_dosya}"))
            self.thread.sinyaller.hata.connect(self.islem_hatasi)
            self.thread.start()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Hata", str(e))

    def paket_listele(self):
        paket_dosya, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Paket dosyasını seçin", filter="EncPack dosyaları (*.encpack)")
        if not paket_dosya:
            return
        try:
            bilgi = KriptoYardimci.paket_icerigini_listele(Path(paket_dosya))
            meta = bilgi["meta"]
            dosya_sayisi = len(meta.get("dosyalar", []))
            toplam_boyut = sum(d.get("orjinal_boyut", 0) for d in meta.get("dosyalar", []))
            self.log_yaz(f"Paket dosyası: {paket_dosya}")
            self.log_yaz(f"Dosya sayısı: {dosya_sayisi}, Toplam boyut: {toplam_boyut / 1024 / 1024:.2f} MB")
            for d in meta.get("dosyalar", []):
                self.log_yaz(f"- {d['goreceli_yol']} ({d['orjinal_boyut']} byte)")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Hata", f"Paket okunamadı:\n{e}")

    def paket_cikar(self):
        paket_dosya, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Paket dosyasını seçin", filter="EncPack dosyaları (*.encpack)")
        if not paket_dosya:
            return
        cikis_klasoru = QtWidgets.QFileDialog.getExistingDirectory(self, "Çıkarılacak klasörü seçin")
        if not cikis_klasoru:
            return
        parola, ok = QtWidgets.QInputDialog.getText(self, "Parola", "Paketi açmak için parolayı girin:", QtWidgets.QLineEdit.Password)
        if not ok or not parola:
            QtWidgets.QMessageBox.warning(self, "Uyarı", "Parola gerekli.")
            return

        self.durum_cubugu.setText("Paket çıkarılıyor...")
        QtWidgets.QApplication.processEvents()
        self.thread = IslemThread(KriptoYardimci.paket_cikar, Path(paket_dosya), parola, Path(cikis_klasoru))
        self.thread.sinyaller.bitti.connect(lambda res: self.islem_bitti(f"Paket başarıyla çıkarıldı: {cikis_klasoru}"))
        self.thread.sinyaller.hata.connect(self.islem_hatasi)
        self.thread.start()

    def islem_bitti(self, mesaj):
        self.durum_cubugu.setText(mesaj)
        self.log_yaz(mesaj)

    def islem_hatasi(self, hata):
        if "Parola yanlış veya dosya bozuk!" in hata:
            mesaj = "Şifre hatalı ya da dosya bozuk."
        else:
            mesaj = f"Hata:\n{hata}"
    
        self.durum_cubugu.setText("İşlem sırasında hata oluştu!")
        self.log_yaz("Hata:", hata)
        QtWidgets.QMessageBox.critical(self, "Hata", mesaj)
    


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec())
