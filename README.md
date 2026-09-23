# 🎓 EduCenter Bot & CRM — O'quv Markazi Boshqaruv Tizimi

**EduCenter Bot & CRM** — O'quv markazlari faoliyatini to'liq avtomatlashtirish, o'qituvchilar, o'quvchilar va ayniqsa **ota-onalar bilan uzluksiz aloqani** ta'minlash uchun ishlab chiqilgan zamonaviy, xavfsiz va keng qamrovli platforma.

Tizim **Telegram Bot (Aiogram 3)** va **FastAPI Web CRM** modullarini yagona asinxron SQLite ma'lumotlar bazasi orqali uzviy bog'lagan holda ishlaydi.

---

## 📑 Mundarija
1. [Loyihaning Umumiy Strukturasi](#-loyihaning-umumiy-strukturasi)
2. [5 Ta Rol va Ularning To'liq Imkoniyatlari](#-5-ta-rol-va-ularning-toliq-imkoniyatlari)
   - [👑 Super Admin](#1--super-admin)
   - [🛡 Admin](#2--admin)
   - [👨‍🏫 O'qituvchi (Teacher)](#3--oqituvchi-teacher)
   - [👨‍👩‍👧 Ota-ona (Parent)](#4--ota-ona-parent)
   - [🧑‍🎓 O'quvchi (Student)](#5--oquvchi-student)
3. [🔔 Mukammal Xabarnomalar Tizimi (Notifications)](#-mukammal-xabarnomalar-tizimi-notifications)
   - [1. Real-time Oniy Davomat Xabarlari](#1-real-time-oniy-davomat-xabarlari)
   - [2. Rasmiy To'lov Kvitansiyalari va Cheklar](#2-rasmiy-tolov-kvitansiyalari-va-cheklar)
   - [3. Murojaat va Takliflar (Tickets Inbox & Reply)](#3-murojaat-va-takliflar-tickets-inbox--reply)
   - [4. Ertalabki Kunlik Xabarnoma](#4-ertalabki-kunlik-xabarnoma-avtomatlashtirilgan)
   - [5. Ommaviy Xabarnoma Tarqatish (Broadcast)](#5-ommaviy-xabarnoma-tarqatish-broadcast)
4. [🌐 Web CRM Boshqaruv Portali](#-web-crm-boshqaruv-portali)
5. [🗄 Ma'lumotlar Bazasi Sxemasi](#-malumotlar-bazasi-sxemasi)
6. [🌍 VPN-siz Ishga Tushirish Yo'llari (O'zbekiston provayderlari uchun)](#-vpn-siz-ishga-tushirish-yollari)
7. [💻 Mahalliy Muhitda (Local) O'rnatish](#-mahalliy-muhitda-local-ornatish)
8. [☁️ Serverda (Production VPS) O'rnatish](#-serverda-production-vps-ornatish)
9. [🧪 Avtomatlashtirilgan Testlar](#-avtomatlashtirilgan-testlar)

---

## 📁 Loyihaning Umumiy Strukturasi

```
educenter_bot/
│
├── 📂 bot/                         # Telegram Bot moduli (Aiogram 3)
│   ├── bot.py                     # Botni ishga tushirish, proksi va routerni sozlash
│   ├── 📂 handlers/               # Xabarlar va buyruqlar ishlovchilari
│   │   ├── admin.py               # Admin menyusi, statistika, to'lovlar, wizard, murojaatlarga javob
│   │   ├── teacher.py             # O'qituvchi menyusi, guruhlar, oniy davomat + ota-ona ogohlantirish
│   │   └── student.py             # O'quvchi & Ota-ona kabineti, farzandlar monitoringi, murojaatlar
│   └── 📂 keyboards/              # Tugmalar (Keyboards)
│       ├── default.py             # Asosiy ReplyKeyboardMarkup menyulari (5 ta rolga mos)
│       └── inline.py              # Interaktiv InlineKeyboard tugmalari (davomat, farzandlar, toifalar)
│
├── 📂 services/                    # Xizmatlar qatlami
│   ├── menu_service.py            # Telegram Menu Button (pastki chap burchakdagi WebApp tugmasi)
│   └── notifications.py           # Real-time Telegram xabarnomalar (davomat, cheklar, murojaatlar)
│
├── 📂 database/                    # Ma'lumotlar bazasi qatlami (aiosqlite)
│   ├── models.py                  # Jadvallar (users, groups, enrollments, payments, attendance, student_parents, feedbacks)
│   └── db.py                      # Asinxron CRUD operatsiyalari va tahliliy SQL so'rovlar
│
├── 📂 webapp/                      # FastAPI Web CRM boshqaruv paneli
│   ├── app.py                     # FastAPI ilovasi, API endpointlar, Excel eksport, oila bog'lash
│   ├── 📂 static/css/
│   │   └── style.css              # Zamonaviy dizayn (Glassmorphism, Card UI, Badges, Tabs)
│   └── 📂 templates/              # Jinja2 HTML shablonlari
│       ├── home.html              # Bosh portal sahifasi
│       ├── admin.html             # Admin Dashboard (Oila bog'lash, Murojaatlar, KPI, guruhlar, to'lovlar)
│       ├── teacher.html           # O'qituvchi shaxsiy portali
│       ├── parent.html            # Ota-ona shaxsiy kabineti + farzandlar monitoringi + murojaat formasi
│       └── student.html           # O'quvchi shaxsiy kabineti
│
├── 📂 tests/                       # Avtomatlashtirilgan testlar (pytest)
│   ├── test_five_portals.py       # Barcha 5 ta portalning ochilishi va integratsiyasi
│   ├── test_menu_and_deployment.py# URL va menyu generatsiyasi
│   ├── test_parent_and_feedback.py# Ota-ona bog'lash, xabarnomalar va feedback testlari
│   ├── test_real_features.py      # Baza CRUD, biriktirish, to'lov va davomat testlari
│   ├── test_student_handlers.py   # Bot matnlari va javoblari testlari
│   └── test_webapp.py             # FastAPI API endpointlari va HTML sahifalar testlari
│
├── ⚙️ config.py                    # Konfiguratsiya, atrof-muhit sozlamalari, proksi va dinamik URL lar
├── 🚀 main.py                     # Bot va WebApp ni parallel ishga tushiruvchi asosiy fayl
├── 📄 requirements.txt            # Python kutubxonalari ro'yxati
├── 🔒 .env                        # Haqiqiy maxfiy kalitlar va bot tokeni
├── 🔒 .env.example                # Namuna sozlamalar
├── 🐳 Dockerfile                  # Docker konteyner fayli
├── 🐳 docker-compose.yml          # Docker Compose konfiguratsiyasi
├── 🐧 educenter.service           # Linux VPS (systemd) doimiy ishlash xizmati
├── 🌐 nginx.conf.example          # Nginx reverse proxy va SSL konfiguratsiyasi namunasi
└── 📖 README.md                   # Loyiha hujjatlari va to'liq qo'llanma
```

---

## 📌 5 Ta Rol va Ularning To'liq Imkoniyatlari

Tizim o'quv markazining barcha ishtirokchilarini qamrab oluvchi **5 ta alohida rol** asosida ishlaydi. Har bir foydalanuvchi tizimga kirganda uning roli avtomatik aniqlanadi va unga faqat o'ziga tegishli menyu taqdim etiladi:

### 1. 👑 Super Admin (Bosh Administrator - ID: `5341602920`)
Markaz ta'sischisi yoki bosh direktori:
- **Telegram Botda:**
  - **`👥 Adminlar` (Adminlar Boshqaruvi / `/admins`):**
    - Markazning barcha tayinlangan adminlari ro'yxatini to'liq ko'rish (F.I.Sh, telefon, Telegram ID).
    - **Adminni o'chirish (`❌ O'chirish`):** Har bir admin yonidagi tugma orqali uning adminlik huquqini zudlik bilan bekor qilish va tizimdan chiqarish (tasdiqlash bilan).
    - Matnli buyruq orqali o'chirish: `/delete_admin <id>` yoki `/remove_admin <telegram_id>`.
    - **Xavfsizlik:** Super Admin hisoblari (`5341602920`) tizim darajasida himoyalangan, ularni o'chirib bo'lmaydi.
  - **`👤 Yangi admin` (`/create_admin`):** Yangi xodimlarga adminlik huquqini berish (qadamma-qadam wizard orqali: Ism-familiya ➡️ Telefon ➡️ Telegram ID).
  - **`👨‍🏫 Yangi ustoz` (`/create_teacher`):** Markazga yangi pedagoglarni qo'shish.
  - **`📈 Hisobotlar` (`/stats`):** O'quv markazining to'liq tahliliy ko'rsatkichlari:
    - Jami o'quvchilar va o'qituvchilar soni
    - Faol guruhlar soni
    - Markazning umumiy moliyaviy tushumi (so'mda)
    - Butun markaz bo'yicha o'rtacha davomat ko'rsatkichi (foizda)
  - **`📣 Xabar yuborish`:** Istalgan auditoriyaga (ota-onalar, ustozlar yoki hammaga) ommaviy e'lon tarqatish.
  - **`📊 CRM Web App` (`/admin`):** To'liq Web CRM paneliga to'g'ridan-to'g'ri kirish havolasi.
- **Web CRM da:**
  - Boshqaruv panelini to'liq ko'rish va boshqarish.
  - Adminlarni boshqarish va o'chirish (`/admin/delete-admin`).
  - Ma'lumotlar bazasining zaxira nusxasini (Backup) bir bosishda yuklab olish (`/admin/backup`).
  - O'quvchilar, To'lovlar va Davomat jadvallarini Excel (`.xlsx`) formatida eksport qilish.

### 2. 🛡 Admin
O'quv markazi ma'muri (menejer, reception):
- **Telegram Botda:**
  - To'lovlarni qabul qilish (`💰 Yangi to'lov` yoki `/add_payment`): to'lov kiritilishi bilan o'quvchi va ota-onalarga **rasmiy chek** yetib boradi.
  - Yangi kelib tushgan murojaatlar va takliflar (`💬 Murojaatlar` yoki `/feedbacks`): murojaat ostidagi "✍️ Javob berish" tugmasi orqali to'g'ridan-to'g'ri botdan javob yo'llash.
  - Guruhlar va yangi ustozlar kiritish.
  - Ommaviy xabar yuborish.
- **Web CRM da:**
  - **Guruhlar bo'limi:** Yangi guruh ochish, fan nomi, narxi, xonasi, dars jadvali va o'qituvchisini belgilash.
  - **O'quvchilarni biriktirish (Enrollment):** O'quvchini guruhga qo'shish va guruhdan chiqarish.
  - **Oila a'zolarini bog'lash (Family Tab):** Ota-ona va farzand o'rtasidagi bog'liqlikni o'rnatish (`ota`, `ona`, `vasiy`).
  - **Moliya bo'limi:** To'lovlarni kiritish, tushumlarni ko'rish, qarzdorlar ro'yxati (Debtors) monitoringi.
  - **Reyting:** Eng yaxshi davomat va to'lovga ega peshqadam o'quvchilar (Leaderboard) tahlili.
  - **Murojaatlar qutisi:** Barcha ota-ona va o'quvchilar murojaatlarini filtrlash va javob berish.

### 3. 👨‍🏫 O'qituvchi (Teacher)
O'quv markazi pedagoglari:
- **Telegram Botda:**
  - **`👥 Guruhlarim`:** O'ziga biriktirilgan barcha faol guruhlar ro'yxati, ulardagi o'quvchilar soni va oylik dars to'lovlari.
  - **`📅 Dars jadvali`:** Dars kunlari, vaqtlari va xonalar ro'yxati.
  - **`✅ Davomat` (Interaktiv oniy davomat):**
    - Kerakli guruh tanlanadi.
    - O'quvchilar ro'yxati inline tugmalarda chiqadi.
    - Har bir o'quvchini 1 bosish orqali almashtirish: `🟢 Keldi` ➡️ `🔴 Kelmadi` ➡️ `🟡 Sababli`.
    - "💾 Saqlash va yakunlash" bosilishi bilan **darsga kelmagan har bir o'quvchining ota-onasiga darhol shoshilinch ogohlantirish xabari** avtomatik jo'natiladi!
  - **`📚 Materiallar`:** Dars ishlanmalari va uslubiy qo'llanmalar bo'limi.
  - **`💬 Murojaat`:** Markaz ma'muriyatiga to'g'ridan-to'g'ri bog'lanish ma'lumotlari.
- **Web CRM da:**
  - O'qituvchi shaxsiy portali (`/teacher/{id}`): Biriktirilgan guruhlar jadvali, o'quvchilar ro'yxati va telefon raqamlari.

### 4. 👨‍👩‍👧 Ota-ona (Parent)
O'quvchilarning ota-onalari yoki vasiylari:
- **Telegram Botda:**
  - **Ro'yxatdan o'tish:** Botga kirib `📱 Telefon raqamni yuborish` tugmasi bosiladi va avtomatik ota-ona sifatida qayd etiladi.
  - **`👨‍👩‍👧 Farzandlarim`:** Ota-onaga biriktirilgan barcha farzandlar ro'yxati. Bir nechta farzandi bo'lsa, tugmalar orqali istalgan birini tanlab ma'lumotlarini ko'rish imkoniyati.
  - **`📅 Dars jadvali`:** Farzandlarining dars kunlari, soati, xonasi va o'qituvchisi ismi.
  - **`✅ Davomat`:** Farzandining oxirgi darslarga qatnashganlik holati.
  - **`💳 To'lovlar tarixi`:** Farzandi uchun qilingan to'lovlar, sanasi, summasi va to'lov turi.
  - **`💬 Murojaat yuborish`:** Markaz rahbariyatiga to'g'ridan-to'g'ri taklif, savol yoki shikoyat yo'llash (Toifasi tanlanadi: `Taklif`, `Shikoyat`, `Savol`).
  - **Chat Menu Web App:** Ekranning pastki chap burchagidagi tugma orqali to'liq ekranli shaxsiy kabinet ochiladi.
- **Web CRM da:**
  - Ota-ona shaxsiy portali (`/parent/{student_id}`): Farzandining to'lovlar grafigi, dars vaqtlari, davomat jurnali va onlayn murojaat formasi.

### 5. 🧑‍🎓 O'quvchi (Student)
O'quv markazi talabalari:
- **Telegram Botda:**
  - **`📅 Dars jadvali`:** O'zining haftalik dars vaqtlari, fanlari va o'qituvchisi.
  - **`🧑‍🏫 Bugungi mashg'ulot`:** Bugungi kunda bo'ladigan darslar eslatmasi.
  - **`💳 To'lovlar tarixi`:** O'zining to'lovlar tarixi, jami to'langan summa va oxirgi to'lovlar.
  - **`✅ Davomat`:** Shaxsiy davomat jurnali (`🟢 Keldi` / `🔴 Kelmadi` / `🟡 Sababli`).
  - **`💬 Qo'llab-quvvatlash`:** O'quv markaz ma'muriyatiga savol va murojaat yo'llash.
- **Web CRM da:**
  - O'quvchi shaxsiy portali (`/student/{id}`): Dars jadvallari, davomat foizi va to'lovlar kvitansiyalari.

---

### 📊 Rollarning Qiyosiy Imkoniyatlar Jadvali (Matrix)

| Imkoniyatlar va Funksiyalar | 👑 Super Admin (`5341602920`) | 🛡 Admin | 👨‍🏫 O'qituvchi | 👨‍👩‍👧 Ota-ona | 🧑‍🎓 O'quvchi |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Adminlarni tayinlash va o'chirish** | ✅ To'liq | ❌ | ❌ | ❌ | ❌ |
| **O'qituvchi qo'shish (`/create_teacher`)** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Guruhlar va dars jadvallarini boshqarish** | ✅ | ✅ | ❌ (faqat o'ziniki) | ❌ | ❌ |
| **To'lovlarni qabul qilish va kvitansiya berish** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Oila bog'lash (ota-ona ↔ farzand)** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Oniy interaktiv davomat olish** | ✅ | ✅ | ✅ (o'z guruhlariga) | ❌ | ❌ |
| **Davomat xabarnomasini real-time olish** | ❌ | ❌ | ❌ | ✅ (Farzandlari) | ✅ (O'ziniki) |
| **To'lov kvitansiyasini avtomatik olish** | ❌ | ❌ | ❌ | ✅ (Farzandlari) | ✅ (O'ziniki) |
| **Farzandlar monitoringi (ko'p farzandli)** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **Murojaat va taklif yuborish** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Murojaatlarga javob qaytarish** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Ommaviy e'lon tarqatish (Broadcast)** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Umumiy moliyaviy hisobotlar (`/stats`)** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Ma'lumotlar bazasi zaxirasi (`/backup`)** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Excel eksport (.xlsx)** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Shaxsiy Web App kabinetiga ega bo'lish** | ✅ (`/admin`) | ✅ (`/admin`) | ✅ (`/teacher`) | ✅ (`/parent`) | ✅ (`/student`) |

---

## 🔔 Mukammal Xabarnomalar Tizimi (Notifications)

Tizimning eng kuchli jihatlaridan biri — bu hodisalarga asoslangan (Event-Driven) real-time xabarnomalar tizimidir (`services/notifications.py`).

### 1. Real-time Oniy Davomat Xabarlari
O'qituvchi davomatni belgilab yakunlagan soniyada tizim avtomatik tahlil qiladi va xabar yuboradi:

* **Agar o'quvchi darsga kelmagan bo'lsa (`kelmadi`):**
  Bog'langan barcha ota-onalarga shoshilinch ogohlantirish jo'natiladi:
  ```text
  🚨 DIQQAT: Farzandingiz darsga kelmadi!

  Hurmatli ota-ona!
  Farzandingiz Alisher Navoiy bugun (2026-09-23) Ingliz tili (Pre-Intermediate) darsiga qatnashmadi.

  Iltimos, sababini o'qituvchiga yoki markaz ma'muriyatiga ma'lum qiling.
  📞 Aloqa: +998 90 123 45 67
  Zahro o'quv markazi
  ```

* **Agar o'quvchi darsga kelgan bo'lsa (`keldi`):**
  ```text
  🟢 Davomat xabarnomasi

  Hurmatli ota-ona!
  Farzandingiz Alisher Navoiy bugun (2026-09-23) Matematika darsiga o'z vaqtida yetib keldi va darsda qatnashmoqda.

  Zahro o'quv markazi
  ```

* **Agar sababli bo'lsa (`sababli`):**
  ```text
  🟡 Davomat xabarnomasi

  Farzandingiz Alisher Navoiy bugun (2026-09-23) Matematika darsida Sababli qatnashmadi deb qayd etildi.

  Zahro o'quv markazi
  ```

* **O'quvchining o'ziga ham bildirishnoma boradi:**
  `📋 Davomatingiz qayd etildi: Guruh: Matematika, Sana: 2026-09-23, Holat: Keldi`

---

### 2. Rasmiy To'lov Kvitansiyalari va Cheklar
Admin to'lovni botdan (`/add_payment`) yoki Web CRM dan qabul qilganda, tizim bir vaqtning o'zida ham **o'quvchiga**, ham **unga biriktirilgan barcha ota-onalarga** rasmiy chek-kvitansiyani yuboradi:

```text
✅ To'lov qabul qilindi! (Rasmiy kvitansiya)

👤 O'quvchi: Alisher Navoiy
📚 Guruh: Ingliz tili (IELTS)
💵 To'langan summa: 350,000 so'm
💳 To'lov turi: Karta
📅 Qaysi oy uchun: 2026-09
📝 Izoh: To'liq to'landi

Farzandingiz ta'limiga befarq bo'lmaganingiz uchun tashakkur!
Zahro o'quv markazi.
```

---

### 3. Murojaat va Takliflar (Tickets Inbox & Reply)
Ota-ona yoki o'quvchi bot orqali taklif/savol/shikoyat yuborganida:

1. **Adminlarga bildirishnoma:**
   Barcha Super Admin va Adminlarga darhol bildirishnoma boradi:
   ```text
   💬 Yangi murojaat qabul qilindi! (ID: #12)

   👤 Kimdan: Dilshod Rahimov (parent)
   📞 Telefon: +998901234567
   👶 O'quvchi: Alisher Navoiy
   📌 Turi: TAKLIF
   📝 Xabar:
   Yakshanba kunlari qo'shimcha so'zlashuv klubi (Speaking Club) tashkil qilinsa yaxshi bo'lardi.

   Admin panel orqali javob berishingiz mumkin.
   ```
2. **Admin javob qaytarganda:**
   Admin botdagi `✍️ Javob berish` tugmasi yoki Web CRM orqali javob yozishi bilan foydalanuvchiga javob yetib boradi:
   ```text
   📩 Murojaatingizga javob keldi!

   Hurmatli Dilshod Rahimov, sizning murojaatingiz ko'rib chiqildi:

   📝 Sizning murojaatingiz:
   «Yakshanba kunlari qo'shimcha so'zlashuv klubi tashkil qilinsa yaxshi bo'lardi.»

   💬 Javob (Admin):
   Taklifingiz uchun tashakkur! Keyingi haftadan boshlab har yakshanba soat 11:00 da bepul Speaking Club boshlanadi.

   Zahro o'quv markazi.
   ```

---

### 4. Ertalabki Kunlik Xabarnoma (Avtomatlashtirilgan)
FastAPI fon xizmati (`daily_notification_loop`) orqali har kuni ertalab soat **08:00** da ro'yxatdan o'tgan barcha ota-onalarga motivatsion va eslatuvchi xabarnoma jo'natiladi:
```text
📚 Assalomu alaykum, hurmatli ota-ona!

Bugungi mashg'ulotlar markazimiz dars jadvali asosida davom etmoqda.
O'quvchining davomati va to'lovlarini shaxsiy kabinet orqali kuzatib borishingiz mumkin.

Zahro o'quv markazi ma'muriyati.
```

---

### 5. Ommaviy Xabarnoma Tarqatish (Broadcast)
Admin bot orqali istalgan vaqtda kerakli auditoriyani tanlab e'lon yuborishi mumkin:
- **👨‍👩‍👧 Ota-onalar va o'quvchilarga**
- **👨‍🏫 Faqat o'qituvchilarga**
- **🌐 Barcha foydalanuvchilarga**

---

## 🌐 Web CRM Boshqaruv Portali

FastAPI va Jinja2 asosida yaratilgan boshqaruv paneli quyidagi sahifalarni o'z ichiga oladi:

| Sahifa | URL | Tavsifi |
| :--- | :--- | :--- |
| **Bosh Sahifa** | `/` | Tizimga kirish portali, barcha rollar havolalari |
| **Admin Dashboard** | `/admin` | Markazning umumiy boshqaruvi, statistika, guruhlar, to'lovlar, oila bog'lash |
| **O'qituvchi Portali** | `/teacher/{id}` | O'qituvchining o'z guruhlari, o'quvchilari va davomati |
| **Ota-ona Portali** | `/parent/{student_id}` | Farzandlar to'lovlari, dars jadvali va davomat nazorati |
| **O'quvchi Portali** | `/student/{id}` | O'quvchining shaxsiy ko'rsatkichlari |
| **Ma'lumotlar Zaxirasi** | `/admin/backup` | `educenter.db` faylini zaxira nusxa sifatida yuklab olish |
| **Excel Eksport** | `/admin/export/{type}` | O'quvchilar, To'lovlar, Davomat jadvallarini Excel (.xlsx) ga chiqarish |

---

## 🗄 Ma'lumotlar Bazasi Sxemasi

```mermaid
erDiagram
    users ||--o{ groups : "teachers teach"
    users ||--o{ enrollments : "students enroll"
    groups ||--o{ enrollments : "has students"
    users ||--o{ payments : "makes payment"
    groups ||--o{ payments : "paid for"
    users ||--o{ attendance : "attendance of"
    groups ||--o{ attendance : "attendance in"
    users ||--o{ student_parents : "parent of"
    users ||--o{ student_parents : "child of"
    users ||--o{ feedbacks : "submits"

    users {
        int id PK
        int telegram_id UK
        string full_name
        string phone
        string role "super_admin, admin, teacher, parent, student"
        timestamp created_at
    }

    groups {
        int id PK
        string name
        string subject
        float monthly_fee
        int teacher_id FK
        string schedule
        string room
    }

    enrollments {
        int id PK
        int student_id FK
        int group_id FK
        timestamp enrolled_at
    }

    payments {
        int id PK
        int student_id FK
        int group_id FK
        float amount
        string payment_type "naqd, karta"
        string month_for
        string note
        timestamp created_at
    }

    attendance {
        int id PK
        int group_id FK
        int student_id FK
        string date
        string status "keldi, kelmadi, sababli"
    }

    student_parents {
        int id PK
        int student_id FK
        int parent_id FK
        string relation_type "ota, ona, vasiy, boshqa"
        timestamp created_at
    }

    feedbacks {
        int id PK
        int user_id FK
        int student_id FK
        string feedback_type "taklif, shikoyat, savol"
        string message
        string status "yangi, korildi, javob_berildi"
        string admin_reply
        int replied_by FK
        timestamp created_at
        timestamp replied_at
    }
```

---

## 🌍 VPN-siz Ishga Tushirish Yo'llari

O'zbekistonda ko'pgina internet provayderlar (Uztelecom, Beeline, Ucell va boshqalar) `api.telegram.org` manziliga to'g'ridan-to'g'ri TLS ulanishlarni cheklaydi. 

Loyiha kodiga **`PROXY_URL`** to'liq integratsiya qilingan bo'lib, quyidagi usullar orqali botni **foydalanuvchi kompyuterida doimiy VPN yoqmasdan** ishlatish mumkin:

### 1-usul: Cloudflare Workers orqali Bepul Reverse Proxy (Tavsiya etiladi)
Cloudflare sizning so'rovlaringizni bepul va xavfsiz Telegram serverlariga yetkazib beradi:
1. [dash.cloudflare.com](https://dash.cloudflare.com) ga kiring va bepul ro'yxatdan o'ting.
2. **Workers & Pages** ➡️ **Create Application** ➡️ **Create Worker** tugmasini bosing.
3. Quyidagi skriptni joylashtiring va **Deploy** qiling:
   ```javascript
   export default {
     async fetch(request) {
       const url = new URL(request.url);
       url.hostname = "api.telegram.org";
       return fetch(new Request(url, {
         method: request.method,
         headers: request.headers,
         body: request.method === "GET" ? null : request.body,
       }));
     }
   };
   ```
4. Sizga berilgan worker manzilini (masalan: `https://my-telegram-proxy.workers.dev`) `.env` dagi `PROXY_URL` ga yozing.

### 2-usul: SOCKS5 / HTTP Proksi orqali
Agar sizda proksi (masalan: V2Ray, Xray, Shadowsocks yoki bepul SOCKS5) bo'lsa, `.env` fayliga kiriting:
```ini
PROXY_URL=socks5://127.0.0.1:10808
# yoki HTTP:
# PROXY_URL=http://user:password@proxy-host:port
```

### 3-usul: VPS Serverda Ishlatish (Eng ishonchli va doimiy)
Botni internetda 24/7 rejimida uzluksiz ishlashi uchun arzon xorijiy Linux VPS serverga (masalan: Timeweb, Hetzner, Vultr) o'rnatish. Serverlarda provayder blokirovkalari bo'lmaydi va bot hech qanday proksisiz to'g'ridan-to'g'ri ishlaydi.

---

## 💻 Mahalliy Muhitda (Local) O'rnatish

### 1. Talablar:
- Python 3.10 yoki undan yuqori
- Telegram Bot Token ([@BotFather](https://t.me/BotFather) dan olingan)

### 2. O'rnatish va Virtual Muhit:
```powershell
# Virtual muhit yaratish
python -m venv .venv

# Faollashtirish (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Kutubxonalarni o'rnatish
pip install -r requirements.txt
```

### 3. Sozlash (`.env`):
`.env` faylini ochib, o'zingizning sozlamalaringizni yozing:
```ini
BOT_TOKEN=8887550146:AAHoEIWaRCgeDnLYAHuRYtXcjazQXYEIf14
SUPER_ADMIN_IDS=5341602920
ADMIN_IDS=5341602920
APP_HOST=0.0.0.0
APP_PORT=8000
WEBAPP_BASE_URL=http://localhost:8000
DATABASE_PATH=educenter.db
# PROXY_URL=http://... (agar kerak bo'lsa)
```

### 4. Ishga tushirish:
```powershell
python main.py
```
* **Telegram Bot:** Polling rejimida ulanadi.
* **Web CRM:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Admin Dashboard:** [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

---

## ☁️ Serverda (Production VPS) O'rnatish

Loyihada **1 bosqichli avtomatik o'rnatish skripti** (`deploy.sh`) mavjud:

```bash
# 1. Serverga yuklash
git clone <repo_url> /var/www/educenter_bot
cd /var/www/educenter_bot

# 2. Avtomatik o'rnatish
bash deploy.sh
```

Ushbu skript quyidagilarni avtomatik amalga oshiradi:
1. Python va kerakli paketlarni o'rnatadi.
2. Virtual muhit (`.venv`) yaratadi va bog'liqliklarni yuklaydi.
3. Linux `systemd` xizmatini (`educenter.service`) yaratadi va faollashtiradi (server o'chib yonsa ham o'zi avtomatik ko'tariladi).
4. Doimiy monitoring va loglar:
   ```bash
   sudo systemctl status educenter
   sudo journalctl -u educenter -f
   ```

---

## 🧪 Avtomatlashtirilgan Testlar

Loyiha to'liq unit va integratsion testlar bilan ta'minlangan. Testlarni ishga tushirish:
```powershell
python -m pytest
```

Barcha **28 ta test** muvaffaqiyatli o'tadi (`28 passed`):
- `tests/test_five_portals.py` — Barcha 5 ta portalning ochilishi va integratsiyasi.
- `tests/test_menu_and_deployment.py` — URL generatsiyasi va Telegram menyu tugmalari.
- `tests/test_parent_and_feedback.py` — Ota-ona va farzand bog'lash, real-time bildirishnomalar, murojaat va javoblar.
- `tests/test_student_handlers.py` — Bot matnlari, klaviaturalar va rollar filtri.
- `tests/test_real_features.py` — SQLite CRUD operatsiyalari, to'lovlar va davomat.
- `tests/test_webapp.py` — FastAPI yo'nalishlari, HTML render va Excel eksport.

---

## 👨‍💻 Qo'llab-quvvatlash
EduCenter boshqaruv tizimi.  
Savol va takliflar bo'yicha Telegram: [@zahro_crm_bot](https://t.me/zahro_crm_bot)
