# Telegram ZIP Manager Bot

## Features
- Telegram se ZIP files upload karna
- Multiple ZIP files save karna (fixed count limit nahi; hosting storage/platform limits apply)
- ZIP list, safe extract, Python script run/stop, delete, status
- Owner-only commands using Telegram numeric user ID

## 1. Bot token aur Telegram ID
1. Telegram me `@BotFather` kholo.
2. `/newbot` bhejo aur bot ka naam/username set karo.
3. BotFather se mila token copy karo. Token kisi ko share mat karna.
4. Apne naye bot ko `/start` bhejo.
5. Apna numeric Telegram ID jaanne ke liye `@userinfobot` ko `/start` bhejo, ya bot deploy hone ke baad `/id` command use karo.

## 2. GitHub par upload
1. ZIP ko extract karo.
2. GitHub par New repository banao.
3. Is folder ki sab files repository me upload karo. `data/` aur `.env` upload mat karna.
4. Commit changes.

## 3. Render par deploy
1. Render.com me login karo.
2. New + -> Blueprint select karo.
3. GitHub repository connect karo.
4. Render `render.yaml` detect karega. Apply/Deploy karo.
5. Service ke Environment section me:
   - `BOT_TOKEN` = BotFather token
   - `ADMIN_ID` = tumhara numeric Telegram user ID
6. Save changes / Deploy.

## 4. Telegram commands
- `/start` - bot start/help
- `/help` - commands list
- `/id` - apna Telegram ID
- `/files` - saved ZIP list
- `/extract ZIP_ID` - ZIP extract
- `/run ZIP_ID filename.py` - extracted Python file run
- `/stop` - running script stop
- `/delete ZIP_ID` - ZIP aur extracted folder delete
- `/status` - ZIP count/storage status

ZIP upload karne ke liye `.zip` document seedha bot ko bhejo. Bot reply me ZIP ID dega.

## Important limits
- Is project me ZIP count par koi artificial limit nahi hai. "Unlimited" storage guarantee nahi hoti: Render disk, plan, Telegram aur network limits apply karte hain.
- Telegram cloud Bot API se bot download limit aam taur par 20 MB per file hai; is project ka default per-ZIP limit 20 MB rakha gaya hai.
- Render free worker ka local filesystem persistent nahi hota. Restart/redeploy par uploaded ZIPs delete ho sakti hain. Permanent storage ke liye paid persistent disk ya external storage configure karo.
- `/run` uploaded Python code execute karta hai. Sirf apni trusted ZIP upload karo. Bot ko private rakho; `ADMIN_ID` security check enabled hai.
- Python script ko 30 seconds ke baad automatically stop kiya jayega (Render env me `RUN_TIMEOUT` badal sakte ho).
- Yeh bot ZIP ke andar ki dependencies automatically install nahi karta.
