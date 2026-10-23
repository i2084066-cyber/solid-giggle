import os
import re
import json
import uuid
import shutil
import zipfile
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("8582311694:AAEgxkBUS2miSMnuQDrXSDpflGFt1eAKxEQ", "").strip()
ADMIN_ID = int(os.getenv("8902530024", "0"))
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
ZIP_DIR = DATA_DIR / "zips"
EXTRACT_DIR = DATA_DIR / "extracted"
MAX_ZIP_BYTES = int(os.getenv("MAX_ZIP_BYTES", str(20 * 1024 * 1024)))
MAX_EXTRACTED_BYTES = int(os.getenv("MAX_EXTRACTED_BYTES", str(200 * 1024 * 1024)))
MAX_FILES_IN_ZIP = int(os.getenv("MAX_FILES_IN_ZIP", "5000"))
RUN_TIMEOUT = int(os.getenv("RUN_TIMEOUT", "30"))

for folder in (ZIP_DIR, EXTRACT_DIR):
    folder.mkdir(parents=True, exist_ok=True)

running_processes = {}

def is_admin(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == ADMIN_ID and ADMIN_ID != 0)

async def deny(update: Update):
    await update.effective_message.reply_text("⛔ Sirf bot owner is command ka use kar sakta hai.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    await update.message.reply_text(
        "✅ ZIP Manager Bot ready hai.\\n\\n"
        "ZIP file yahan Telegram par bhejo.\\n"
        "/help - commands\\n"
        "/files - saved ZIP list\\n"
        "/extract ID - ZIP extract\\n"
        "/run ID file.py - Python file run\\n"
        "/stop - running script stop\\n"
        "/delete ID - ZIP aur extracted folder delete\\n"
        "/status - storage status\\n"
        "/id - apna Telegram ID"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    await update.message.reply_text(
        "📌 Commands:\\n"
        "/start - bot start\\n"
        "/help - help\\n"
        "/id - Telegram user ID\\n"
        "/files - ZIP files ki list\\n"
        "/extract ID - ZIP extract\\n"
        "/run ID filename.py - extracted Python file run\\n"
        "/stop - current script stop\\n"
        "/delete ID - ZIP delete\\n"
        "/status - bot/storage status\\n\\n"
        "ZIP upload: ZIP document ko seedha bot chat me bhejo."
    )

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")

async def upload_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    doc = update.message.document
    filename = (doc.file_name or "").strip()
    if not filename.lower().endswith(".zip"):
        await update.message.reply_text("❌ Sirf .zip file bhejo.")
        return
    if doc.file_size and doc.file_size > MAX_ZIP_BYTES:
        await update.message.reply_text(
            f"❌ ZIP bahut badi hai. Is bot ki configured limit {MAX_ZIP_BYTES // (1024*1024)} MB hai."
        )
        return
    zip_id = uuid.uuid4().hex[:8]
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(filename).name)[:100] or "upload.zip"
    destination = ZIP_DIR / f"{zip_id}_{safe_name}"
    try:
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(custom_path=destination)
        record = {
            "id": zip_id,
            "name": safe_name,
            "path": str(destination),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "size": destination.stat().st_size
        }
        index_path = DATA_DIR / "index.json"
        items = json.loads(index_path.read_text()) if index_path.exists() else []
        items.append(record)
        index_path.write_text(json.dumps(items, indent=2))
        await update.message.reply_text(
            f"✅ ZIP save ho gayi!\\nID: `{zip_id}`\\nName: {safe_name}\\n"
            f"Size: {destination.stat().st_size / (1024*1024):.2f} MB\\n"
            f"Extract: /extract {zip_id}",
            parse_mode="Markdown"
        )
    except Exception as exc:
        destination.unlink(missing_ok=True)
        await update.message.reply_text(f"❌ Upload error: {str(exc)[:500]}")

def load_items():
    index_path = DATA_DIR / "index.json"
    if not index_path.exists():
        return []
    try:
        return json.loads(index_path.read_text())
    except Exception:
        return []

def save_items(items):
    (DATA_DIR / "index.json").write_text(json.dumps(items, indent=2))

async def files_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    items = load_items()
    if not items:
        await update.message.reply_text("Abhi koi ZIP saved nahi hai. ZIP file bhejo.")
        return
    lines = ["📦 Saved ZIP files:"]
    for item in items[-50:]:
        size_mb = item.get("size", 0) / (1024 * 1024)
        lines.append(f"ID: {item['id']} | {item['name']} | {size_mb:.1f} MB")
    await update.message.reply_text("\\n".join(lines))

def safe_extract(zip_path: Path, target: Path):
    target_resolved = target.resolve()
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES_IN_ZIP:
            raise ValueError(f"ZIP me {MAX_FILES_IN_ZIP} se zyada files hain.")
        total = sum(info.file_size for info in infos)
        if total > MAX_EXTRACTED_BYTES:
            raise ValueError(f"Extracted size {MAX_EXTRACTED_BYTES // (1024*1024)} MB se zyada hai.")
        for info in infos:
            name = info.filename.replace("\\\\", "/")
            if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
                raise ValueError("Unsafe absolute path ZIP me mila.")
            destination = (target / name).resolve()
            if destination != target_resolved and target_resolved not in destination.parents:
                raise ValueError("Unsafe path traversal ZIP me mila.")
            # Symlink entries are not extracted.
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP me symbolic link allowed nahi hai.")
        archive.extractall(target)

async def extract_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    if not context.args:
        await update.message.reply_text("Use: /extract ZIP_ID")
        return
    zip_id = context.args[0]
    item = next((x for x in load_items() if x["id"] == zip_id), None)
    if not item:
        await update.message.reply_text("❌ ZIP ID nahi mili. /files dekho.")
        return
    target = EXTRACT_DIR / zip_id
    if target.exists():
        await update.message.reply_text(f"ZIP pehle se extract hai: {target}")
        return
    target.mkdir(parents=True, exist_ok=True)
    try:
        safe_extract(Path(item["path"]), target)
        py_files = list(target.rglob("*.py"))
        await update.message.reply_text(
            f"✅ Extract complete.\\nPython files: {len(py_files)}\\n"
            f"Run: /run {zip_id} filename.py"
        )
    except Exception as exc:
        shutil.rmtree(target, ignore_errors=True)
        await update.message.reply_text(f"❌ Extract error: {str(exc)[:500]}")

async def run_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    if len(context.args) < 2:
        await update.message.reply_text("Use: /run ZIP_ID filename.py")
        return
    zip_id, relative_name = context.args[0], " ".join(context.args[1:])
    root = (EXTRACT_DIR / zip_id).resolve()
    script = (root / relative_name).resolve()
    if not root.exists():
        await update.message.reply_text("Pehle ZIP extract karo: /extract ZIP_ID")
        return
    if root not in script.parents or not script.is_file() or script.suffix.lower() != ".py":
        await update.message.reply_text("❌ Valid extracted .py file path do.")
        return
    if update.effective_user.id in running_processes:
        await update.message.reply_text("⚠️ Ek script pehle se chal rahi hai. /stop use karo.")
        return
    await update.message.reply_text(f"▶️ Running: {relative_name}\\nTimeout: {RUN_TIMEOUT}s")
    try:
        proc = await asyncio.create_subprocess_exec(
            "python", str(script),
            cwd=str(root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        running_processes[update.effective_user.id] = proc
        try:
            output, _ = await asyncio.wait_for(proc.communicate(), timeout=RUN_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            output, _ = await proc.communicate()
            output += b"\\n[STOPPED: time limit reached]"
        finally:
            running_processes.pop(update.effective_user.id, None)
        text_out = output.decode("utf-8", errors="replace")[-3500:] or "(No output)"
        await update.message.reply_text(
            f"Exit code: {proc.returncode}\\n\\n{text_out}"
        )
    except Exception as exc:
        running_processes.pop(update.effective_user.id, None)
        await update.message.reply_text(f"❌ Run error: {str(exc)[:500]}")

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    proc = running_processes.get(update.effective_user.id)
    if not proc or proc.returncode is not None:
        await update.message.reply_text("Koi script running nahi hai.")
        return
    proc.kill()
    await update.message.reply_text("🛑 Script stop kar di.")

async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return
    if not context.args:
        await update.message.reply_text("Use: /delete ZIP_ID")
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
  
