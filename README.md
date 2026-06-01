# AGZ Support Time Bot

ربات تلگرامی ثبت زمان پاسخگویی تیم پشتیبانی AGZ.
ثبت شروع/پایان شیفت، گزارش روزانه و ماهانه (تاریخ شمسی، تایم‌زون تهران)، پنل مدیریت و ارسال خودکار گزارش شبانه.

## Stack

- Python 3.12 · aiogram 3 · SQLAlchemy 2 (async) · MySQL (aiomysql) · Alembic · APScheduler
- Timezone: `Asia/Tehran` · تاریخ شمسی با `jdatetime`

## ساختار پروژه

```
app/
  main.py            # entrypoint (polling + scheduler)
  config.py          # settings + logging
  bot/               # dispatcher, keyboards, states, middlewares
  handlers/          # start, shifts, reports, admin, common
  services/          # business logic
  database/          # models, engine, repositories
  scheduler/         # daily report job
  utils/             # datetime, jalali, formatters
alembic/             # migrations
```

## معماری

```
Telegram ⇄ Bot Layer ⇄ Handlers ⇄ Services ⇄ Repositories ⇄ MySQL
                                      ▲
                          APScheduler (۲۳:۰۰ تهران)
```

- **یک شیفت فعال در هر کاربر** با ستون generated و unique index سطح دیتابیس تضمین می‌شود (معادل partial unique index در MySQL).
- شروع/پایان شیفت **Transaction Safe** (با `SELECT ... FOR UPDATE`).
- **Anti-Spam** روی callbackهای حساس از طریق middleware.

## نقش‌ها

- **Owner**: آیدی‌های موجود در `OWNER_IDS` — دسترسی کامل + پنل مدیریت.
- **Allowed**: کاربری که Owner دسترسی داده (`is_allowed = true`).
- **Unauthorized**: فقط پیام عدم دسترسی می‌بیند.

## نصب گزارش در گروه/تاپیک

Owner داخل گروه یا تاپیک پیام `نصب` را بفرستد تا گزارش شبانه همان‌جا ارسال شود،
و پیام `حذف` را بفرستد تا غیرفعال شود.

## شخصی‌سازی متن‌ها و ایموجی پریمیوم (Custom Emoji)

از پنل مدیریت → **✏️ شخصی‌سازی متن‌ها** می‌توانید متن پیام‌ها (خوش‌آمد، شروع/پایان
پاسخگویی، پشتیبانی، تاریخ امروز و …) را تغییر دهید. کافی است **ایموجی پریمیوم
(Custom Emoji) را مستقیماً داخل همان متن بنویسید**؛ ربات به‌صورت خودکار طبق
داکیومنت تلگرام، `custom_emoji_id` و موقعیت دقیق هر ایموجی را از
`message.entities` استخراج و ذخیره می‌کند و هنگام نمایش، عیناً همان ایموجی پریمیوم
را در همان جای متن بازتولید می‌کند (نیازی به ارسال جداگانهٔ شناسه نیست).

- نوشتن ایموجی پریمیوم داخل متن نیازمند **تلگرام پریمیوم** برای فرستندهٔ (Owner) است.
- آفست‌ها بر حسب **UTF-16** ذخیره می‌شوند و هنگام جایگزینی متغیرهایی مثل
  `{minutes}`/`{jalali}` به‌درستی جابه‌جا می‌شوند تا ایموجی سرجای خود بماند.
- هر شناسه پیش از ذخیره با `get_custom_emoji_stickers` بررسی می‌شود؛ اگر ربات
  نتواند ایموجی را ارسال کند، در زمان نمایش به‌صورت خودکار به **متن ساده** برمی‌گردد.

نکات فنی:

- پیام‌ها با **message entities** ساخته می‌شوند (نه `parse_mode`)، بنابراین
  Bold/Italic و `custom_emoji` بدون تداخل کنار هم کار می‌کنند (`parse_mode=None`).
- اگر ایموجی پریمیوم تنظیم نشده باشد، ربات به‌صورت خودکار به **ایموجی معمولی**
  برمی‌گردد و پیام همچنان معتبر است.
- **متن دکمه‌های شیشه‌ای (inline) از ایموجی پریمیوم پشتیبانی نمی‌کند**؛ در دکمه‌ها
  فقط از ایموجی معمولی استفاده می‌شود (مثل 🟢/🔴/🔵).

دیتای ذخیره‌شده در جدول `text_settings`: `text_key`، `text_value`،
`custom_emoji_id`، `formatting_config`.

## تجربهٔ کاربری (UX)

- با کلیک روی هر دکمه، منوی قبلی شلوغ نمی‌شود: پیام قبلی **ویرایش** می‌شود و در
  صورت ناممکن بودن، حذف و پیام تازه ارسال می‌شود (helper به‌نام `safe_edit_or_send`).
- خطاهای رایج تلگرام (`message is not modified`، `message to delete not found`،
  `message can't be edited`) بدون کرش مدیریت می‌شوند و `callback` همیشه پاسخ می‌گیرد.
- در استارت، فقط دستور `/start - شروع ربات` ثبت می‌شود (`set_my_commands`).

## راه‌اندازی محلی (توسعه)

ابتدا دیتابیس MySQL را با charset مناسب بسازید:

```sql
CREATE DATABASE agz_support CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'agz'@'localhost' IDENTIFIED BY 'agz';
GRANT ALL PRIVILEGES ON agz_support.* TO 'agz'@'localhost';
FLUSH PRIVILEGES;
```

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # سپس BOT_TOKEN و DATABASE_URL را تنظیم کنید
alembic upgrade head
python -m app.main
```

> روی ویندوز معادل فعال‌سازی: `.venv\Scripts\activate`

## اجرای دائمی روی Ubuntu 24.04

ابتدا MySQL را نصب و دیتابیس را بسازید (`sudo apt install mysql-server`، سپس همان دستورات SQL بخش بالا).
پروژه را در `/opt/agz-support-time-bot` قرار دهید:

```bash
cd /opt/agz-support-time-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # مقادیر واقعی را وارد کنید
alembic upgrade head

sudo cp agz-support-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable agz-support-bot
sudo systemctl start agz-support-bot
sudo systemctl status agz-support-bot
```

مشاهده لاگ‌ها:

```bash
journalctl -u agz-support-bot -f      # لاگ systemd
tail -f /opt/agz-support-time-bot/logs/bot.log
```

سرویس با `Restart=always` بعد از کرش و بعد از reboot سرور به‌صورت خودکار اجرا می‌شود.

## تنظیمات (`.env`)

| کلید | توضیح |
|------|-------|
| `BOT_TOKEN` | توکن ربات از BotFather |
| `OWNER_IDS` | آیدی عددی مالک‌ها، با کاما جدا شده |
| `DATABASE_URL` | DSN آسنکرون MySQL (`mysql+aiomysql://...?charset=utf8mb4`) |
| `TIMEZONE` | پیش‌فرض `Asia/Tehran` |
| `DAILY_REPORT_HOUR` / `DAILY_REPORT_MINUTE` | زمان گزارش شبانه |
| `LOG_LEVEL` / `LOG_FILE` | تنظیمات لاگ |

> فایل `.env` هرگز نباید commit شود (در `.gitignore` است).
