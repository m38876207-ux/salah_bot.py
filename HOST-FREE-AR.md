# 🆓 استضافة مجانية 100% وبدون نوم — Northflank

دليل خطوة بخطوة لاستضافة البوت مجانًا بشكل دائم (مش تجربة 30 يوم).

---

## ليه Northflank؟

| الميزة | Northflank Sandbox |
|---|---|
| مجاني | ✅ خطة Sandbox مجانية بشكل دائم |
| كارت ائتمان | ❌ مش مطلوب |
| بينام؟ | ❌ **Always on, no sleeping** — البوت شغال 24/7 |
| سحب الكود من GitHub | ✅ تحديث أوتوماتيك مع كل `git push` |
| Docker | ✅ بيدعم `Dockerfile` اللي في المشروع |

> ملاحظة: خطة Sandbox مخصّصة للمشاريع الشخصية/التجريبية (2 خدمة + قاعدة بيانات + 20$/شهر
> من الموارد). بوت واحد خفيف زي ده يستهلك جزء صغير جدًا منها.

---

## الخطوات

### 1) إنشاء حساب

1. افتح <https://app.northflank.com/signup>
2. سجّل بـ **GitHub** (نفس الحساب `m38876207-ux`).
3. لو طلب تفعيل إيميل، فعّله.

### 2) اعمل مشروع

1. من الداشبورد: **Create project**.
2. اسمه مثلًا `salah-bot` → **Create project**.

### 3) اربط GitHub

1. جوّه المشروع: **Add service** → **Create service**.
2. اختار **Deploy from Git repository**.
3. اضغط **Connect GitHub** واسمح لـ Northflank بالوصول.
4. اختار الريبو: **`m38876207-ux/salah_bot.py`** والبرانش **`main`**.

> لو الريبو مش ظاهر: في GitHub → Settings → Applications → Northflank →
> Configure → اختار *Only select repositories* وحدد `salah_bot.py`.

### 4) إعداد الخدمة

Northflank هيقرأ `Dockerfile` لوحده. راجع الإعدادات دي:

| الإعداد | القيمة |
|---|---|
| Service type | **Worker** (بوت مش ويب سيرفر) |
| Build type | **Dockerfile** (مكتشف أوتوماتيك) |
| Build context | `/` |
| Dockerfile path | `Dockerfile` |
| Ports | **مفيش** (Worker مالوش HTTP) |

### 5) المتغيرات (Secrets)

1. تبويب **Environment** (أو *Secret groups*).
2. اضغط **Add secret** / **New variable**:

| Key | Value |
|---|---|
| `DISCORD_TOKEN` | توكن البوت من Developer Portal |
| `DISCORD_GUILD_ID` | *(اختياري)* ID سيرفرك — يجعل الأوامر تظهر فورًا |

3. **Deploy**.

### 6) اتأكد إنه شغال

1. تبويب **Logs** → استنى البناء يخلص.
2. لازم تشوف:

   ```
   logged in as salah-bot#xxxx — 1 guild(s)
   synced 11 global commands
   ```

3. ادخل Discord واكتب `/prayer` 🎉

---

## التحديثات

أي تعديل ترفعه على GitHub:

```powershell
cd C:\Users\MSI\Desktop\salah-bot\salah_bot.py
git add -A
git commit -m "تعديل"
git push
```

Northflank بيعمل Deploy أوتوماتيك. لو مش بيحصل تلقائيًا فعّل
**Continuous deployment** في إعدادات الخدمة.

---

## مقارنة سريعة للبدائل المجانية

| الموقع | مجاني بدون تريل؟ | 24/7 بدون نوم؟ | كارت؟ |
|---|---|---|---|
| **Northflank Sandbox** | ✅ | ✅ | ❌ |
| Oracle Cloud Always Free | ✅ (VM دائم) | ✅ | ✅ (للتحقق فقط) |
| Render | ✅ | ❌ بينام بعد 15 دقيقة | ❌ |
| Railway | ❌ (تجربة ثم Hobby 5$) | ✅ | ✅ |
| Fly.io | ❌ (مفيش مجاني دائم للحسابات الجديدة) | — | ✅ |
| Koyeb | ✅ | ❌ بينام عند السكون | ❌ |
| GitHub Actions | ❌ مخالف للشروط | — | ❌ |

> Oracle Cloud: الـ 300$ تجربة 30 يوم، لكن **Always Free VM** بيفضل مجاني للأبد.
> عيبه إنه محتاج تعرف Linux وتظبط systemd، وممكن يطلبوا كارت للتحقق (بدون خصم).
