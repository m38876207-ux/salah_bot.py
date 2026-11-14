# ☁️ رفع البوت على GitHub واستضافته 24/7

دليل مختصر لصاحب المشروع — من الرفع لحد ما البوت يشتغل ويشوفه صحابك.

---

## 1) الرفع على GitHub ✅ (تم بالفعل)

المشروع اترفع خلاص على:

**https://github.com/m38876207-ux/salah_bot.py**

| الملف | موجود في الريبو |
|---|---|
| الكود (`salahbot/`, `main.py`) | ✅ |
| بيانات الأذكار (`data/azkar.json`) | ✅ |
| `requirements.txt` | ✅ |
| `Dockerfile` + `Procfile` + `runtime.txt` | ✅ (للاستضافة) |
| `.env` (التوكن) | ❌ **مش مرفوع** — وده صح ومقصود |

> ⚠️ **قاعدة ذهبية:** التوكن سر زي كلمة سر الحساب. لو اترفع على GitHub (حتى لو الريبو خاص)
> لازم تعمل Reset Token فورًا من Developer Portal. الملف `.gitignore` بيمنع رفع `.env` تلقائيًا.

### لو عدّلت في الكود بعد كده، ارفع التعديل بأمرين:

```powershell
cd C:\Users\MSI\Desktop\salah-bot\salah_bot.py
git add -A
git commit -m "وصف التعديل"
git push
```

---

## 2) الاستضافة — البوت لازم يفضل شغال 24/7

Discord بيفصل أي بوت بيقفل، فمحتاج **سيرفر شغال على طول**. أسهل حل للمبتدئين
هو **Railway** لأنه بياخد الكود من GitHub وينشره لوحده، وكل `git push` بيعمل تحديث.

### الطريقة الموصى بها: Railway (≈ 5$ في الشهر)

1. افتح <https://railway.app> واعمل تسجيل دخول **بـ GitHub**.
2. **New Project** → **Deploy from GitHub repo**.
3. اختار الريبو **`salah_bot.py`** (لو مش ظاهر، اضغط *Configure GitHub App*
   واسمح لـ Railway بالوصول للريبو).
4. Railway هيلاقي `Dockerfile` وينشر البوت أوتوماتيك. استنى دقيقة–دقيقتين.
5. افتح الخدمة → تبويب **Variables** → **New Variable**:

   | Key | Value |
   |---|---|
   | `DISCORD_TOKEN` | توكن البوت من Developer Portal |
   | `DISCORD_GUILD_ID` | *(اختياري)* ID سيرفرك — بيخلي الأوامر تظهر فورًا |

   > توكن البوت بيجيلك من: Discord Developer Portal → تطبيقك → **Bot** → **Reset Token**.
   > متحطّهوش في الكود ولا على GitHub — متغيرات Railway مكانه الصح.

6. تبويب **Deployments** → **View Logs**. لازم تشوف:

   ```
   logged in as salah-bot#xxxx — 1 guild(s)
   synced 11 global commands
   ```

7. افتح Discord → السيرفر → اكتب `/prayer` — المفروض الأوامر ظهرت.

> **التكلفة:** خطة Hobby بـ 5$ شهريًا تكفي بوت زي ده بسهولة
> ([تفاصيل أسعار Railway](https://railway.com/pricing)).

### بدائل

| الخيار | التكلفة | ملاحظات |
|---|---|---|
| **جهازك/لابتوب قديم** | مجاني | `python main.py` وسيبه شغال (شوف القسم 4). لازم الكهرباء والنت مقطوعينش. |
| **Northflank (Sandbox)** | مجاني | خدمتين شغالين 24/7 بدون نوم — كويس لو عايز صفر تكلفة. |
| **Oracle Cloud Always Free** | مجاني | سيرفر مجاني دائم، لكن محتاج تعرف Linux شوية. |
| **Render** | مجاني بس بينام | ⚠️ الخطة المجانية بتوقف الخدمة بعد 15 دقيقة سكون → البوت بيقع. محتاج خطة مدفوعة. |
| **VPS (Contabo/Hetzner)** | 4–6$ | تحكم كامل، محتاج إعداد Linux. |

---

## 3) توصيل البوت لصاحبك

1. **العزم (Invite):** Developer Portal → **OAuth2 → URL Generator**:
   - Scopes: `bot` + `applications.commands`
   - Permissions: `Send Messages` + `Embed Links` + `Read Message History`
   - ابعت اللينك لصاحبك يدخل بيه البوت عنده (أو دخّله في سيرفرك).
2. **لو عايزه يعدّل الكود:** GitHub → الريبو → **Settings → Collaborators → Add people**
   وابعتله دعوة بإيميله/يوزرنيم GitHub.
3. **البيانات:** إعدادات السيرفرات (`guild_settings.json`) بتتحفظ جوه كونتينر Railway
   وبتتصفّر مع كل نشر جديد. لو مهمة، اربط **Volume** وامسح مسار `/app`.
   *(المواقيت والأذكار نفسها مش محتاجة أي حفظ — بتتحسب لحظيًا.)*

---

## 4) تشغيله على جهازك (بدون استضافة)

```powershell
cd C:\Users\MSI\Desktop\salah-bot\salah_bot.py
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env     # حط التوكن جوه .env
python main.py
```

البوت هيفضل شغال طول ما النافذة مفتوحة والنت شغال. للتشغيل التلقائي:
**Task Scheduler** → Create Task → عند بدء تشغيل Windows → Start a program →
`powershell.exe -WindowStyle Hidden -Command "cd C:\Users\MSI\Desktop\salah-bot\salah_bot.py; .\.venv\Scripts\python.exe main.py"`

---

## 5) حل المشاكل الشائعة

| المشكلة | الحل |
|---|---|
| الأوامر مش ظاهرة في Discord | استنى ساعة (أوامر الجلوبال بتتزامن ببطء) أو حط `DISCORD_GUILD_ID` في المتغيرات وأعد النشر |
| `Discord rejected the token` | التوكن غلط/مقطوع → Reset Token وجدّد المتغير في Railway |
| البوت ONLINE بس مش بيرد | تأكد إن الـ `applications.commands` scope موجود في لينك الدعوة |
| Railway deploy بيفشل | افتح Logs؛ غالبًا `DISCORD_TOKEN` مش متعرّف. الكود بيطبع سبب واضح في أول سطرين |
| التذكيرات مش بتوصل | `/settings reminders channel:#القناة` ولازم البوت عنده صلاحية Send + Embed في القناة |
| البوت بيفصل كل شوية | الهوست بينام (Render المجاني مثلًا) → غيّر لـ Railway/Northflank |

---

## 6) تشيك سريع إن كل حاجة سليمة

من داخل الريبو:

```powershell
python scripts/smoke_test.py         # كل الاختبارات بدون توكن
python main.py --check               # يفحص الإعدادات ويقولك ناقص إيه
```
