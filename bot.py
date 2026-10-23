async def auto_reply(update, context):
    if update.message and update.message.text:
        msg = update.message.text.lower()

        if "hello" in msg:
            reply = "Hello bro! 👋"
        elif "hi" in msg:
            reply = "Hi! Welcome ❤️"
        elif "help" in msg:
            reply = "How can I help you?"
        else:
            reply = "Your message received ✅"

        await update.message.reply_text(reply)xt("Use: /delete ZIP_ID")
        return
    zip_id = context.args[0]
    items = load_items()
    item = next((x for x in items if x["id"] == zip_id), None)
    if not item:
        await update.message.reply_text("ZIP ID nahi mili.")
        return
    Path(item["path"]).unlink(missing_ok=True)
    shutil.rmtree(EXTRACT_DIR / zip_id, ignore_errors=True)
    save_items([x for x in items if x["id"] != zip_id])
    await update.message.reply_text(f"🗑️ ZIP {zip_id} delete ho gayi.")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    items = load_items()
    total = sum(x.get("size", 0) for x in items)
    await update.message.reply_text(
        f"✅ Bot online\\nZIP count: {len(items)}\\n"
        f"Saved ZIP size: {total / (1024*1024):.2f} MB\\n"
        f"ZIP limit: {MAX_ZIP_BYTES / (1024*1024):.0f} MB per file"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Telegram error:", context.error)

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN Render Environment me set nahi hai.")
    if ADMIN_ID == 0:
        raise RuntimeError("ADMIN_ID Render Environment me set nahi hai.")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("files", files_cmd))
    app.add_handler(CommandHandler("extract", extract_cmd))
    app.add_handler(CommandHandler("run", run_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("delete", delete_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, upload_zip))
    app.add_error_handler(error_handler)
    print("ZIP Manager Bot started.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
  
