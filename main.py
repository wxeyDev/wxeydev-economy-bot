import asyncio
import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from database.database import init_database


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("❌ .env dosyasında DISCORD_TOKEN bulunamadı.")


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="l ",
    intents=intents,
    help_command=None,
    case_insensitive=True,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BOT DURUMU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

status_index = 0


@tasks.loop(seconds=30)
async def update_status():
    global status_index

    server_count = len(bot.guilds)

    # Botun bulunduğu sunuculardaki yaklaşık toplam kullanıcı sayısı
    user_count = sum(guild.member_count or 0 for guild in bot.guilds)

    statuses = [
        f"WxeyDev • {server_count} sunucu",
        f"Ekonomi • {user_count:,} kullanıcı",
        "WxeyDev ekonomi sistemini yönetiyor",
        "Güçlü ekonomi, daha iyi topluluklar",
        "15+ özellik ile hizmet veriyor",
        "WxeyDev tarafından geliştirildi",
    ]

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=statuses[status_index]
        )
    )

    status_index = (status_index + 1) % len(statuses)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BOT HAZIR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ Loan aktif!")
    print(f"👤 Hesap: {bot.user}")
    print(f"🌐 Sunucu sayısı: {len(bot.guilds)}")

    if not update_status.is_running():
        update_status.start()

    try:
        synced = await bot.tree.sync()
        print(f"⚡ Slash komutları: {len(synced)}")
    except Exception as exc:
        print(f"❌ Slash senkronizasyonu başarısız: {exc}")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOMUT HATALARI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Eksik bilgi. `l bilgi` yazarak komut kullanımını görebilirsin."
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(
            "❌ Komut parametrelerinden biri hatalı. `l bilgi` ile örneklere bak."
        )
        return

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f"❌ Bu komut için biraz beklemelisin: "
            f"`{error.retry_after:.0f}s`."
        )
        return

    print(f"Komut hatası: {repr(error)}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KOMUTLARI YÜKLE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def load_extensions():
    for extension in (
        "commands.economy",
        "commands.profile",
        "commands.jobs",
        "commands.market",
        "commands.investment",
        "commands.company",
        "commands.leaderboard",
        "commands.admin",
        "commands.help",
    ):
        await bot.load_extension(extension)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BAŞLAT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def main():
    init_database()
    await load_extensions()
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())