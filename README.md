# 🚀 ebs-encrypted-archive

<img src="ebs.png" alt="ebs ekran görüntüsü" />

**ebs-encrypted-archive**, güçlü ve kolay kullanımlı bir **şifreli dosya paketleyici**dir.  
Python ve PySide6 ile geliştirilmiş olup, **Argon2** tabanlı anahtar türetme ve **AES-GCM** ile güvenli şifreleme sağlar.  
Dosya ve klasörleri güvenli şekilde paketleyip, parola korumalı olarak arşivler.

---

## 📦 Nedir? Ne İşe Yarar?

`ebs-encrypted-archive`, dosya ve klasörlerinizi tek bir şifreli paket halinde toplamanıza ve güvenle saklamanıza olanak verir. Böylece:

- Dosyalarınızın gizliliğini korur.
- Parola olmadan içeriklere erişilemez.
- Çok büyük dosyaları parçalar halinde şifreler.
- Güçlü Argon2 ile anahtar türetme ile parola güvenliğini artırır.
- AES-GCM algoritması ile hem şifreler hem veri bütünlüğünü sağlar.

---

## ⚙️ Özellikler

- Dosya ve klasör bazlı paketleme (alt klasörler dahil).
- Parola ile güçlü şifreleme (**Argon2 + AES-GCM**).
- Paket içeriğini listeleme.
- Paketi şifreli şekilde çıkarma.
- Çoklu dosya ve büyük dosya desteği (chunk bazlı).
- GUI tabanlı kolay kullanım (PySide6).
- İşlem sırasında arayüz donmasını önleyen thread yapısı.
- Parola girişinde gizlilik (şifre maskelenir).
- Argon2 parametrelerinin (zaman, bellek, paralellik) ayarlanabilmesi.
- Platformlar arası uyumluluk (Windows, Linux, macOS).

---

## 💻 Desteklenen İşletim Sistemleri

- Windows 10 ve üstü
- Linux dağıtımları (Ubuntu, Fedora, Debian, vs.)
- macOS (modern sürümler)

---

## 📸 Ekran Görüntüsü

<img src="ebs.png" alt="Ekran Görüntüsü" />

---

## 🚀 Kurulum

1. **Python 3.9 veya üzeri** kurulu olduğundan emin olun.
2. Gerekli bağımlılıkları yükleyin:
   ```bash
   pip install PySide6 cryptography argon2-cffi
   ```

---

## 🛠️ Kullanım

### Programı çalıştırmak için:
```bash
python ebs_secure_pack.py
```

### Uygulamayı tek dosya olarak derlemek için:
```bash
pyinstaller --onefile --noconsole ebs_secure_pack.py
```

### Özellikler:
- **Dosya Ekle:** Paketlemek istediğiniz dosyaları seçin.
- **Klasör Ekle:** Alt klasörler dahil tüm dosyaları seçilen klasörden ekleyin.
- **Paket Oluştur:** Seçilen dosyaları parola ile şifreleyip tek bir `.encpack` dosyası oluşturur.
- **Paketi Listele:** Var olan `.encpack` dosyasının içeriğini görüntüler.
- **Paketi Çıkar:** Parola girerek şifreli paketi belirtilen klasöre açar.

---

## ⚙️ Argon2 Parametreleri Açıklaması

- **Zaman Maliyeti (time_cost):** Hesaplama kaç kere yapılacak (daha yüksek → daha güvenli ve yavaş).
- **Bellek Maliyeti (memory_cost):** Kullanılacak bellek miktarı (KiB cinsinden, yüksek değer → daha güvenli).
- **Paralellik (parallelism):** Paralel iş parçacığı sayısı (çok çekirdekli işlemciler için optimize).

> Varsayılan değerler performans ve güvenlik arasında iyi bir denge sağlar.

---

## 🔒 Güvenlik Avantajları

- **Güçlü parola tabanlı anahtar türetme:** Argon2 ID tipi ile parola kırılmaya karşı dayanıklıdır.
- **AES-GCM:** Hem şifreleme hem veri bütünlüğü sağlar (veri değiştirilirse açma işlemi başarısız olur).
- **Her dosya için benzersiz nonce:** Tekrarlanan saldırılara karşı direnç.
- **Chunk tabanlı şifreleme:** Büyük dosyaların güvenli ve etkili paketlenmesi.
- **Parola olmadan dosya içeriği tamamen gizli kalır.**

---

## 📄 Lisans

Bu proje **Apache License 2.0** ile lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakabilirsiniz.

---

## 🤝 Katkıda Bulunma

Katkılarınızı memnuniyetle karşılarız! İsterseniz:

- Hata bildirimi,
- Yeni özellik önerisi,
- Kod geliştirme

yapabilirsiniz.

---

## 💬 İletişim

Sorularınız için [EBSMail Adresi](mailto:ebubekiryazilim@gmail.com) adresinden bana ulaşabilirsiniz.

---

⭐️ Eğer bu projeyi faydalı bulduysanız, bir ⭐ bırakmayı unutmayın!
