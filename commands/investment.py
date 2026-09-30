import random

import discord
from discord.ext import commands

from database.database import create_user, get_portfolio, get_stock, get_stocks, get_user, set_portfolio, set_stock_price, update_user_money
from systems.ui import error_embed, money, pct, success_embed, user_embed


class Investment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def refresh_prices(self):
        for row in get_stocks():
            current = row["price"]
            change = random.uniform(-0.06, 0.06)
            new = max(1.0, round(current * (1 + change), 2))
            set_stock_price(row["symbol"], new)

    @commands.hybrid_command(name="borsa", description="Sanal borsa fiyatlarını gösterir.")
    async def stocks(self, ctx):
        create_user(ctx.author.id, ctx.guild.id)
        self.refresh_prices()
        rows = get_stocks()
        lines = []
        for row in rows:
            diff = ((row["price"] - row["last_price"]) / row["last_price"]) * 100 if row["last_price"] else 0
            lines.append(f"`{row['symbol']}` **{row['name']}** — {money(row['price'])} · `{pct(diff)}`")
        embed = user_embed(ctx.author, "📈 LOAN • Sanal Borsa", "Tamamen oyun içi sanal varlıklardır; gerçek para değildir.")
        embed.description = "\n".join(lines)
        embed.add_field(name="İşlemler", value="`l hisse NOVA`\n`l hisseal NOVA 2`\n`l hissesat NOVA 1`\n`l portfoy`", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="hisse", description="Bir sanal hissenin ayrıntısını gösterir.")
    async def stock(self, ctx, symbol: str):
        self.refresh_prices()
        row = get_stock(symbol)
        if not row:
            await ctx.send(embed=error_embed("Hisse bulunamadı", "`l borsa` ile sembolleri gör."))
            return
        change = ((row["price"] - row["last_price"]) / row["last_price"]) * 100 if row["last_price"] else 0
        embed = user_embed(ctx.author, f"📊 {row['symbol']} • {row['name']}", f"Sektör: **{row['sector']}**")
        embed.add_field(name="Fiyat", value=f"**{money(row['price'])}**", inline=True)
        embed.add_field(name="Hareket", value=f"**{pct(change)}**", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="hisseal", description="Sanal borsadan hisse satın alır.")
    async def buy_stock(self, ctx, symbol: str, quantity: int = 1):
        create_user(ctx.author.id, ctx.guild.id)
        self.refresh_prices()
        row = get_stock(symbol)
        if not row or quantity <= 0:
            await ctx.send(embed=error_embed("Geçersiz işlem", "`l borsa` ile doğru sembolü kontrol et."))
            return
        price = float(row["price"])
        total = int(price * quantity)
        user = get_user(ctx.author.id, ctx.guild.id)
        if total > user["balance"]:
            await ctx.send(embed=error_embed("Yetersiz bakiye", f"Gerekli: **{money(total)}**"))
            return
        portfolio = {r["symbol"]: r for r in get_portfolio(ctx.author.id, ctx.guild.id)}
        existing = portfolio.get(row["symbol"])
        old_qty = existing["quantity"] if existing else 0
        old_avg = existing["average_price"] if existing else 0
        new_qty = old_qty + quantity
        new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
        set_portfolio(ctx.author.id, ctx.guild.id, row["symbol"], new_qty, new_avg)
        update_user_money(ctx.author.id, ctx.guild.id, balance_delta=-total, note=f"Hisse alımı: {row['symbol']} x{quantity}", tx_type="borsa")
        await ctx.send(embed=success_embed("Hisse alındı", f"`{row['symbol']}` x**{quantity}**\nToplam: **{money(total)}**\nOrtalama maliyet: **{money(new_avg)}**"))

    @commands.hybrid_command(name="hissesat", description="Portföyündeki hisseleri satar.")
    async def sell_stock(self, ctx, symbol: str, quantity: int = 1):
        create_user(ctx.author.id, ctx.guild.id)
        self.refresh_prices()
        row = get_stock(symbol)
        if not row or quantity <= 0:
            await ctx.send(embed=error_embed("Geçersiz işlem", "`l borsa` ile doğru sembolü kontrol et."))
            return
        portfolio = {r["symbol"]: r for r in get_portfolio(ctx.author.id, ctx.guild.id)}
        existing = portfolio.get(row["symbol"])
        if not existing or existing["quantity"] < quantity:
            owned = existing["quantity"] if existing else 0
            await ctx.send(embed=error_embed("Yetersiz hisse", f"Portföyünde **{owned} adet** var."))
            return
        price = float(row["price"])
        income = int(price * quantity)
        new_qty = existing["quantity"] - quantity
        set_portfolio(ctx.author.id, ctx.guild.id, row["symbol"], new_qty, existing["average_price"])
        update_user_money(ctx.author.id, ctx.guild.id, balance_delta=income, note=f"Hisse satışı: {row['symbol']} x{quantity}", tx_type="borsa")
        await ctx.send(embed=success_embed("Hisse satıldı", f"`{row['symbol']}` x**{quantity}**\nGelir: **{money(income)}**"))

    @commands.hybrid_command(name="portfoy", aliases=["portföy"], description="Hisse portföyünü ve kâr/zararı gösterir.")
    async def portfolio(self, ctx):
        create_user(ctx.author.id, ctx.guild.id)
        self.refresh_prices()
        rows = get_portfolio(ctx.author.id, ctx.guild.id)
        if not rows:
            await ctx.send(embed=error_embed("Portföy boş", "`l borsa` ile yatırım fırsatlarına bakabilirsin."))
            return
        lines = []
        total_value = 0
        total_cost = 0
        for row in rows:
            value = row["quantity"] * row["price"]
            cost = row["quantity"] * row["average_price"]
            pnl = value - cost
            total_value += value
            total_cost += cost
            lines.append(f"`{row['symbol']}` x**{row['quantity']}** · Değer **{money(value)}** · K/Z **{money(pnl)}**")
        embed = user_embed(ctx.author, "💼 LOAN • Yatırım Portföyü", "Sanal yatırımlarının özeti.")
        embed.description = "\n".join(lines)
        embed.add_field(name="Toplam Değer", value=f"**{money(total_value)}**", inline=True)
        embed.add_field(name="Toplam Maliyet", value=f"**{money(total_cost)}**", inline=True)
        embed.add_field(name="Toplam K/Z", value=f"**{money(total_value - total_cost)}**", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Investment(bot))
