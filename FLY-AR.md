# 🛫 النشر على Fly.io (نسخة الـ Worker)

المشكلة اللي ظهرت في الصورة (`Checking https://...fly.dev` → `timeout`) سببها إن
Fly فاكر البوت **موقع ويب** وبيدور على منفذ 80 و health check. البوت مش بيستقبل
HTTP خالص — بيتكلم مع Discord عبر WebSocket. الحل موجود في `fly.toml` اللي في
المشروع: **مفيش `[http_service]` خالص**، والماكينة بتفضل شغالة (`min_machines_running = 1`).

---

## 0) قبل أي حاجة — جدّد التوكن

التوكن اللي كتبته في الشات يعتبر مكشوف. من Developer Portal → Bot → **Reset Token**،
والتوكن الجديد **متحطّهوش في الكود ولا في GitHub**.

---

## 1) اختار طريقة النشر

### الطريقة أ — CLI (أسهل وأضمن)

1. حمّل `flyctl` من: <https://fly.io/docs/flyctl/install/> (Windows: PowerShell install script).
2. افتح PowerShell في مجلد المشروع:

```powershell
cd C:\Users\MSI\Desktop\salah-bot\salah_bot.py
fly auth signup        # أو fly auth login لو عندك حساب
fly apps create salah-bot-py
fly secrets set DISCORD_TOKEN=التوكن-الجديد-هنا
fly deploy
```

3. تابع اللوج مباشرة:

```powershell
fly logs
```

لازم تشوف:

```
logged in as salah-bot#xxxx — 1 guild(s)
synced 11 global commands
```

4. اتأكد إن الماكينة شغالة:

```powershell
fly status
fly machines list
```

> ⚠️ لو `fly robots` بتعمل deploy من GitHub: شيل **Health check** بتاع HTTP من إعدادات
> الـ app، وخلي نوع الـ process **worker** مش web، ويقرأ `fly.toml` من الريبو.

### الطريقة ب — من لوحة Fly (من غير Terminal)

1. افتح <https://fly.io/apps> → الـ app بتاعك (`salah-bot-py`).
2. **Settings → Secrets** → عدّل `DISCORD_TOKEN` بالتوكن الجديد.
3. **Settings → Health checks** → **شيل** أي HTTP health check.
4. اتأكد إن آخر ديبلوي بيستخدم الـ commit اللي فيه `fly.toml`
   (4e5042b أو أحدث) — عيد **Deploy** من نفس الصفحة.

---

## 2) بعد ما يشتغل

```powershell
fly secrets list        # يتأكد إن التوكن متسجل
fly logs                # لوج البوت لايف
fly scale count 1       # ماكينة واحدة كفاية
fly scale memory 256    # لو الميموري عالية/واطية
```

- **تحديث:** `git push` + `fly deploy` (أو GitHub integration لو مفعّلة).
- **إيقاف مؤقت:** `fly scale count 0` — **إرجاع:** `fly scale count 1`.

---

## 3) ملاحظة عن التكلفة

Fly مابقاش عنده allowance مجاني دائم للحسابات الجديدة؛ الحساب بيبدأ بـ trial ثم
Pay-as-you-go. ماكينة `shared-cpu-1x / 256MB` شغالة 24/7 بتكلفة بسيطة جدًا
(عادة أقل من دولار–دولارين شهريًا لبوت زي ده).

لو عايز **مجاني 100% بدون كارت**: استخدم **Northflank Sandbox** — الدليل في
`HOST-FREE-AR.md`، وهو بيدعم نفس `Dockerfile` بالظبط.

---

## 4) لو Fly رفض ينشر

| الرسالة | الحل |
|---|---|
| `timeout trying to get your app` | اتأكد إن الديبلوي على كوميت فيه `fly.toml` الجديد (`GET /health`) |
| `DISCORD_TOKEN` غير معرّف | `fly secrets set DISCORD_TOKEN=...` ثم `fly deploy` |
| `Improper token has been passed` | ⚠️ **السبب الأشهر**: عملت Reset Token بس **ما حدّثتش** الـ secret في Fly. حدّثه وأعد النشر |
| الماكينة بترجع تقف | `fly logs` وشوف الخطأ، وبعدين `fly scale count 1` |
| الأوامر مش ظاهرة | حط `DISCORD_GUILD_ID` أو استنى ساعة (global commands) |
| `/health` بيرجع timeout أو بيفشل | الماكينة مش شغالة خالص: `fly status` ثم `fly logs` |

### أهم فحص بعد أي Reset للتوكن

البوت بياخد التوكن من **Fly Secrets** مش من GitHub. أول ما تعمل Reset:
التوكن القديم بيبقى باطل → البوت بيقع فورًا → `/health` بيفشل.

```powershell
fly secrets set DISCORD_TOKEN=التوكن-الجديد
fly deploy
fly logs
```
