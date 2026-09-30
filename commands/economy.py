import discord
from discord.ext import commands

from database.database import (
    add_xp,
    claim_daily_state,
    claim_bank_interest,
    create_user,
    ensure_guild,
    get_transactions,
    get_user,
    update_user_money,
)
from systems.ui import error_embed, money, success_embed, user_embed


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure(self, guild_id, user_id):
        settings = ensure_guild(guild_id)
        create_user(user_id, guild_id, settings["starting_money"])
        return get_user(user_id, guild_id)

    @commands.hybrid_command(name="bakiye", description="Cüzdan, banka ve toplam varlıklarını gösterir.")
    async def balance(self, ctx):
        user = await self.ensure(ctx.guild.id, ctx.author.id)
        total = user["balance"] + user["bank"]
        required = user["level"] * 1000
        bar = "█" * round(min(user["xp"] / required, 1) * 20) + "░" * (20 - round(min(user["xp"] / required, 1) * 20))

        embed = user_embed(ctx.author, "💳 LOAN • Hesap Özeti", "Finansal durumun ve ilerlemen.")
        embed.add_field(name="💵 Cüzdan", value=f"**{money(user['balance'])}**", inline=True)
        embed.add_field(name="🏦 Banka", value=f"**{money(user['bank'])}**", inline=True)
        embed.add_field(name="💎 Toplam Varlık", value=f"**{money(total)}**", inline=False)
        embed.add_field(name=f"Level {user['level']}", value=f"`{bar}`\n`{user['xp']:,} / {required:,} XP`", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="banka", description="Banka hesabını ve finans seçeneklerini gösterir.")
    async def bank(self, ctx):
        user = await self.ensure(ctx.guild.id, ctx.author.id)
        embed = user_embed(ctx.author, "🏦 LOAN • Banka", "Paranı bankada tut, yönet ve ileride faizden yararlan.")
        embed.add_field(name="💵 Cüzdan", value=f"**{money(user['balance'])}**", inline=True)
        embed.add_field(name="🏦 Banka", value=f"**{money(user['bank'])}**", inline=True)
        embed.add_field(name="💎 Toplam", value=f"**{money(user['balance'] + user['bank'])}**", inline=False)
        embed.add_field(name="Komutlar", value="`l yatır 500`\n`l çek 500`\n`l işlemler`", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="yatir", aliases=["yatır"], description="Cüzdandan bankaya para yatırır.")
    async def deposit(self, ctx, amount: int):
        user = await self.ensure(ctx.guild.id, ctx.author.id)
        if amount <= 0:
            await ctx.send(embed=error_embed("Geçersiz miktar", "Miktar 0'dan büyük olmalı."))
            return
        if amount > user["balance"]:
            await ctx.send(embed=error_embed("Yetersiz bakiye", f"Cüzdanında sadece **{money(user['balance'])}** var."))
            return
        update_user_money(ctx.author.id, ctx.guild.id, balance_delta=-amount, bank_delta=amount, note="Bankaya para yatırma", tx_type="yatırma")
        new = get_user(ctx.author.id, ctx.guild.id)
        await ctx.send(embed=success_embed("Para yatırıldı", f"**{money(amount)}** bankaya yatırıldı.\n\nCüzdan: **{money(new['balance'])}**\nBanka: **{money(new['bank'])}**"))

    @commands.hybrid_command(name="cek", aliases=["çek"], description="Bankadan cüzdana para çeker.")
    async def withdraw(self, ctx, amount: int):
        user = await self.ensure(ctx.guild.id, ctx.author.id)
        if amount <= 0:
            await ctx.send(embed=error_embed("Geçersiz miktar", "Miktar 0'dan büyük olmalı."))
            return
        if amount > user["bank"]:
            await ctx.send(embed=error_embed("Yetersiz banka bakiyesi", f"Bankanda sadece **{money(user['bank'])}** var."))
            return
        update_user_money(ctx.author.id, ctx.guild.id, balance_delta=amount, bank_delta=-amount, note="Bankadan para çekme", tx_type="çekim")
        new = get_user(ctx.author.id, ctx.guild.id)
        await ctx.send(embed=success_embed("Para çekildi", f"**{money(amount)}** cüzdana aktarıldı.\n\nCüzdan: **{money(new['balance'])}**\nBanka: **{money(new['bank'])}**"))

    @commands.hybrid_command(name="faiz", description="Banka bakiyene günlük sanal faiz uygular.")
    async def interest(self, ctx):
        await self.ensure(ctx.guild.id, ctx.author.id)
        settings = ensure_guild(ctx.guild.id)
        result = claim_bank_interest(ctx.author.id, ctx.guild.id, settings["bank_interest"])
        if not result["ok"]:
            if result["reason"] == "cooldown":
                hours = result["remaining"] // 3600
                minutes = (result["remaining"] % 3600) // 60
                await ctx.send(embed=error_embed("Faiz henüz hazır değil", f"Tekrar almak için yaklaşık **{hours}s {minutes}dk** bekle."))
            return
        await ctx.send(embed=success_embed("Banka faizi işlendi", f"Bugünkü faiz kazancın: **{money(result['interest'])}**\nYeni banka bakiyesi: **{money(result.get('bank', get_user(ctx.author.id, ctx.guild.id)['bank']))}**"))

    @commands.hybrid_command(name="aktar", aliases=["transfer", "paraaktar"], description="Başka bir kullanıcıya cüzdandan para gönderir.")
    async def transfer(self, ctx, member: discord.Member, amount: int):
        if member.bot or member.id == ctx.author.id:
            await ctx.send(embed=error_embed("Geçersiz kullanıcı", "Kendine veya botlara para gönderemezsin."))
            return
        sender = await self.ensure(ctx.guild.id, ctx.author.id)
        await self.ensure(ctx.guild.id, member.id)
        if amount <= 0:
            await ctx.send(embed=error_embed("Geçersiz miktar", "Miktar 0'dan büyük olmalı."))
            return
        if amount > sender["balance"]:
            await ctx.send(embed=error_embed("Yetersiz bakiye", f"Cüzdanında sadece **{money(sender['balance'])}** var."))
            return
        update_user_money(ctx.author.id, ctx.guild.id, balance_delta=-amount, note=f"{member.id} kullanıcısına transfer", tx_type="transfer")
        update_user_money(member.id, ctx.guild.id, balance_delta=amount, note=f"{ctx.author.id} kullanıcısından transfer", tx_type="transfer")
        await ctx.send(embed=success_embed("Transfer tamamlandı", f"{member.mention} kullanıcısına **{money(amount)}** gönderildi."))

    @commands.hybrid_command(name="gunluk", aliases=["günlük", "daily"], description="Günlük ödülünü alır ve seri bonusu kazanır.")
    async def daily(self, ctx):
        user = await self.ensure(ctx.guild.id, ctx.author.id)
        settings = ensure_guild(ctx.guild.id)
        result = claim_daily_state(ctx.author.id, ctx.guild.id, settings["daily_reward"])
        if not result["ok"]:
            if result["reason"] == "cooldown":
                hours = result["remaining"] // 3600
                minutes = (result["remaining"] % 3600) // 60
                await ctx.send(embed=error_embed("Günlük ödül hazır değil", f"Yaklaşık **{hours}s {minutes}dk** sonra tekrar dene."))
            return
        xp = add_xp(ctx.author.id, ctx.guild.id, 25)
        text = f"Bugünkü ödülün: **{money(result['reward'])}**\nGünlük seri: **{result['streak']}**"
        if xp["leveled_up"]:
            text += f"\n\n🎉 **Level {xp['level']}** oldun!"
        await ctx.send(embed=success_embed("Günlük ödül alındı", text))

    @commands.hybrid_command(name="islemler", aliases=["işlemler"], description="Son ekonomi işlemlerini gösterir.")
    async def transactions(self, ctx):
        await self.ensure(ctx.guild.id, ctx.author.id)
        rows = get_transactions(ctx.author.id, ctx.guild.id, 10)
        if not rows:
            await ctx.send(embed=error_embed("İşlem geçmişi boş", "Henüz kayıtlı bir işlem yok."))
            return
        lines = []
        for row in rows:
            sign = "+" if row["amount"] >= 0 else ""
            note = row["note"] or row["type"]
            lines.append(f"`{row['type']}`  **{sign}{money(row['amount'])}** — {note}")
        embed = user_embed(ctx.author, "📒 LOAN • İşlem Geçmişi", "Son 10 finansal işlem.")
        embed.description = "\n".join(lines)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Economy(bot))
