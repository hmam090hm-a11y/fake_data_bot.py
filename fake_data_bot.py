#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# بوت توليد بيانات وهمية

import os
import json
import csv
import io
from datetime import datetime
import asyncio
from aiohttp import web

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)

# مكتبة Faker لتوليد البيانات
from faker import Faker

# ================== الإعدادات ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").rstrip("/")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not WEBHOOK_URL:
    raise RuntimeError("❌ تأكد من BOT_TOKEN و WEBHOOK_URL")

# إعدادات Faker
fake_ar = Faker('ar_SA')  # للبيانات العربية
fake_en = Faker('en_US')  # للبيانات الإنجليزية

# ================== توليد الأشخاص ==================
def generate_person(person_id, lang='ar'):
    """توليد بيانات شخص واحد"""
    fake = fake_ar if lang == 'ar' else fake_en
    
    gender = fake.random_element(['ذكر', 'أنثى']) if lang == 'ar' else fake.random_element(['Male', 'Female'])
    
    # توليد اسم حسب الجنس
    if gender in ['ذكر', 'Male']:
        full_name = fake.name_male() if lang == 'ar' else fake.name_male()
    else:
        full_name = fake.name_female() if lang == 'ar' else fake.name_female()
    
    return {
        "id": person_id,
        "full_name": full_name,
        "gender": gender,
        "age": fake.random_int(min=18, max=70),
        "email": fake.email(),
        "phone": fake.phone_number() if lang == 'en' else f"+9665{fake.random_int(10000000, 99999999)}",
        "job": fake.job() if lang == 'ar' else fake.job(),
        "city": fake.city() if lang == 'ar' else fake.city(),
        "address": fake.address() if lang == 'ar' else fake.address()
    }

def generate_people(count, lang='ar', format_type='text'):
    """توليد مجموعة من الأشخاص"""
    people = [generate_person(i+1, lang) for i in range(min(count, 100))]  # حد أقصى 100
    
    if format_type == 'json':
        result = {
            "generated_at": datetime.now().isoformat(),
            "count": len(people),
            "language": lang,
            "format": "json",
            "people": people
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    
    elif format_type == 'csv':
        output = io.StringIO()
        if people:
            writer = csv.DictWriter(output, fieldnames=people[0].keys())
            writer.writeheader()
            writer.writerows(people)
        return output.getvalue()
    
    else:  # نص مقروء
        lines = []
        if lang == 'ar':
            lines.append(f"👥 تم توليد {len(people)} أشخاص:\n")
            for i, person in enumerate(people, 1):
                lines.append(f"{i}. {'🧔' if person['gender'] == 'ذكر' else '👩'} {person['full_name']}")
                lines.append(f"   • العمر: {person['age']} سنة")
                lines.append(f"   • الجنس: {person['gender']}")
                lines.append(f"   • الوظيفة: {person['job']}")
                lines.append(f"   • المدينة: {person['city']}")
                lines.append(f"   • 📧 {person['email']}")
                lines.append(f"   • 📱 {person['phone']}")
                lines.append(f"   • 🏠 {person['address']}")
                lines.append("")
        else:
            lines.append(f"👥 Generated {len(people)} people:\n")
            for i, person in enumerate(people, 1):
                lines.append(f"{i}. {'🧔' if person['gender'] == 'Male' else '👩'} {person['full_name']}")
                lines.append(f"   • Age: {person['age']} years")
                lines.append(f"   • Gender: {person['gender']}")
                lines.append(f"   • Job: {person['job']}")
                lines.append(f"   • City: {person['city']}")
                lines.append(f"   • 📧 {person['email']}")
                lines.append(f"   • 📱 {person['phone']}")
                lines.append(f"   • 🏠 {person['address']}")
                lines.append("")
        
        return "\n".join(lines)

# ================== معالجات البوت ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض رسالة الترحيب"""
    help_text = """
🚀 *مرحباً! أنا بوت توليد البيانات الوهمية*

*الأوامر المتاحة:*
/fake <عدد> - توليد أشخاص (نص مقروء)
/fake <عدد> json - توليد أشخاص بتنسيق JSON
/fake <عدد> csv - توليد أشخاص بتنسيق CSV
/fake <عدد> ar - توليد أشخاص عرب
/fake <عدد> en - توليد أشخاص إنجليز

*أمثلة:*
/fake 5 - 5 أشخاص عرب
/fake 3 json - 3 أشخاص بصيغة JSON
/fake 10 csv - 10 أشخاص بصيغة CSV
/fake 2 en - 2 أشخاص إنجليز
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def fake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /fake"""
    try:
        if not context.args:
            await update.message.reply_text("⚠️ الرجاء تحديد عدد الأشخاص. مثال: /fake 5")
            return
        
        # تحليل المدخلات
        count = int(context.args[0])
        if count > 100:
            await update.message.reply_text("⚠️ الحد الأقصى هو 100 شخص في المرة الواحدة")
            count = 100
        
        # تحديد الصيغة واللغة
        format_type = 'text'
        lang = 'ar'
        
        for arg in context.args[1:]:
            arg_lower = arg.lower()
            if arg_lower in ['json', 'csv']:
                format_type = arg_lower
            elif arg_lower in ['ar', 'en']:
                lang = arg_lower
        
        # توليد البيانات
        await update.message.reply_text(f"⏳ جاري توليد {count} شخص...")
        data = generate_people(count, lang, format_type)
        
        # إرسال النتائج
        if format_type == 'text':
            await update.message.reply_text(data)
        elif format_type == 'json':
            await update.message.reply_document(
                document=io.BytesIO(data.encode('utf-8')),
                filename=f'fake_people_{count}_{lang}.json'
            )
        elif format_type == 'csv':
            await update.message.reply_document(
                document=io.BytesIO(data.encode('utf-8')),
                filename=f'fake_people_{count}_{lang}.csv'
            )
            
    except ValueError:
        await update.message.reply_text("⚠️ الرجاء إدخال رقم صحيح. مثال: /fake 5")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

# ================== خادم الويب ==================
async def webhook_handler(request):
    """معالجة طلبات ويب هوك"""
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return web.Response(text="OK")

async def health_check(request):
    """فحص صحة الخادم"""
    return web.Response(text="🤖 بوت توليد البيانات يعمل!")

async def main():
    """الدالة الرئيسية"""
    global telegram_app
    
    # بناء تطبيق تليجرام
    telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("fake", fake_command))
    
    # تهيئة وتشغيل
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    await telegram_app.start()
    
    # خادم ويب
    web_app = web.Application()
    web_app.router.add_post("/webhook", webhook_handler)
    web_app.router.add_get("/", health_check)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    print(f"🚀 البوت يعمل على المنفذ {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
