# Free ICT Gift Bot

Telegram bot: har kuni bepul keys, referal dasturi, TON/so'm mukofotlari.

## Loyiha tuzilishi

```
freegift_bot/
├── main.py              # Botni ishga tushiruvchi asosiy fayl
├── config.py            # Sozlamalar (token, admin ID, sovrinlar, limitlar)
├── database.py           # Ma'lumotlar bazasi modellari (SQLAlchemy)
├── requirements.txt      # Kerakli kutubxonalar
└── handlers/
    ├── start.py           # /start, ro'yxatdan o'tish, kanal obunasi tekshiruvi
    ├── case.py             # Kunlik keys ochish logikasi
    ├── referral.py          # Referal tizimi va balans
    └── withdraw.py          # Pul/TON yechib olish + admin tasdiqlash
```

## O'rnatish

1. **PostgreSQL o'rnating** va bo'sh baza yarating:
   ```
   createdb freegift
   ```

2. **Kutubxonalarni o'rnating:**
   ```
   pip install -r requirements.txt
   ```

3. **`.env` yoki muhit o'zgaruvchilarini sozlang** (yoki `config.py` ichida to'g'ridan-to'g'ri yozing):
   ```
   export BOT_TOKEN="123456:ABC-DEF..."
   export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/freegift"
   ```

4. **`config.py` faylida quyidagilarni o'zgartiring:**
   - `ADMIN_IDS` — o'zingizning Telegram ID raqamingiz (bilishning eng oson yo'li: @userinfobot ga yozish)
   - `REQUIRED_CHANNEL` — trading kanalingiz username'i (@ belgisisiz)
   - `CASE_PRIZES` — sovrinlar ro'yxati va ularning ehtimollik og'irliklari
   - `DAILY_TON_BUDGET` — kuniga qancha TON sarflashga tayyor ekanligingiz

5. **Botni ishga tushiring:**
   ```
   python main.py
   ```

## Muhim: TON to'lovlari haqida

Bu bot **avtomatik TON o'tkazmasini amalga oshirmaydi** — atayin shunday qilingan, chunki:
- Avtomatik kripto o'tkazmalar xatoga yo'l qo'yadigan va xavfli
- Admin har bir so'rovni ko'rib chiqib, qo'lda TON hamyonidan yuboradi, so'ng botda "Tasdiqlash" tugmasini bosadi

Agar kelajakda avtomatlashtirmoqchi bo'lsangiz, TON blockchain bilan ishlash uchun `pytonlib` yoki `tonsdk` kutubxonasini alohida integratsiya qilish kerak — bu qo'shimcha xavfsizlik choralarini talab qiladi (hot wallet boshqaruvi, tranzaksiya monitoring).

## Firibgarlikka qarshi choralar (allaqachon kiritilgan)

- Referal mukofoti faqat referal **3 kun faol bo'lgach** to'lanadi (soxta akkauntlarga qarshi)
- Keys ochishda **24 soatlik cooldown**
- Kunlik **umumiy TON byudjet limiti** — belgilangan miqdordan oshsa, "bo'sh" natija chiqadi
- Ban tizimi (`is_banned`) — admin shubhali foydalanuvchilarni bloklashi mumkin

## Keyingi qadamlar (tavsiya)

1. **Admin panel** — statistika, foydalanuvchilarni ban qilish, sovrinlarni tahrirlash uchun alohida buyruqlar yoki veb-panel
2. **Telefon raqam tasdiqlash** — referal firibgarligini yanada kamaytirish uchun
3. **Mini-ilova (WebApp)** — keys ochishni chiroyli animatsiya bilan ko'rsatish uchun (keyingi bosqichda birga quramiz)
4. **Monitoring** — kunlik xarajat va foydalanuvchilar sonini kuzatib borish uchun log/dashboard

## Bot buyruqlari

- `/start` — botni boshlash / referal linkdan kirish
- `/withdraw` — TON yoki so'm balansini yechib olish so'rovi yuborish
