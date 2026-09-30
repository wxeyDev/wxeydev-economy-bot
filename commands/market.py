import random

import discord
from discord.ext import commands

from database.database import add_inventory, create_user, get_inventory, get_user, update_user_money
from systems.catalog import PRODUCTS
from systems.ui import error_embed, money, success_embed, user_embed


class MarketView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=120)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Bu paneli sadece komutu kullanan kişi kullanabilir.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yenile", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction, button):
        cog = interaction.client.get_cog("Market")
        await interaction.response.edit_message(embed=cog.market_embed(interaction.user), view=self)

    @discord.ui.button(label="Envanter", emoji="🎒", style=discord.ButtonStyle.primary)
    async def inventory(self, interaction, button):
        cog = interaction.client.get_cog("Market")
        await interaction.response.edit_message(embed=cog.inventory_embed(interaction.user), view=self)


class Market(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def market_embed(self, user):
        lines = []
        for key, item in PRODUCTS.items():
            tag = " • NADİR" if item["rare"] else ""
            lines.append(f"{item['emoji']} **{item['name']}**{tag}\n`{key}` • Al: **{money(item['buy'])}** · Sat: **{money(item['sell'])}**")
        embed = user_embed(user, "🛒 LOAN • Market", "Ürünleri `l al <ürün> <adet>` ile satın alabilirsin.")
        embed.description = "\n\n".join(lines)
        embed.add_field(name="Örnek", value="`l al demir 2`\n`l sat demir 1`", inline=False)
        return embed

    def inventory_embed(self, user):
        guild_id = user.guild.id if getattr(user, "guild", None) else 0
        rows = get_inventory(user.id, guild_id)
        embed = user_embed(user, "🎒 LOAN • Envanter", "Sahip olduğun ürünler.")
        if not rows:
            embed.description = "Envanterin şu an boş. \n`l market` ile alışveriş yapabilirsin."
            return embed
        lines = []
        for row in rows:
            data = PRODUCTS.get(row["item_key"])
            if data:
                lines.append(f"{data['emoji']} **{data['name']}** — `{row['quantity']} adet`")
        embed.description = "\n".join(lines)
        return embed

    @commands.hybrid_command(name="market", description="Loan marketindeki ürünleri gösterir.")
    async def market(self, ctx):
        create_user(ctx.author.id, ctx.guild.id)
        await ctx.send(embed=self.market_embed(ctx.author), view=MarketView(ctx.author.id))

    @commands.hybrid_command(name="envanter", description="Envanterindeki ürünleri gösterir.")
    async def inventory_cmd(self, ctx):
        create_user(ctx.author.id, ctx.guild.id)
        rows = get_inventory(ctx.author.id, ctx.guild.id)
        embed = user_embed(ctx.author, "🎒 LOAN • Envanter", "Sahip olduğun ürünler.")
        if not rows:
            embed.description = "Envanterin şu an boş.\n`l market` ile alışveriş yapabilirsin."
        else:
            lines = []
            for row in rows:
                data = PRODUCTS.get(row["item_key"])
                if data:
                    lines.append(f"{data['emoji']} **{data['name']}** — `{row['quantity']} adet`")
            embed.description = "\n".join(lines)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="al", description="Marketten ürün satın alır.")
    async def buy(self, ctx, item_key: str, quantity: int = 1):
        create_user(ctx.author.id, ctx.guild.id)
        item_key = item_key.lower()
        item = PRODUCTS.get(item_key)
        if not item or quantity <= 0:
            await ctx.send(embed=error_embed("Geçersiz ürün", "`l market` ile ürün kodlarını görebilirsin."))
            return
        # Small fictional market fluctuation per purchase.
        unit_price = max(1, int(item["buy"] * random.uniform(0.96, 1.06)))
        total = unit_price * quantity
        user = get_user(ctx.author.id, ctx.guild.id)
        if total > user["balance"]:
            await ctx.send(embed=error_embed("Yetersiz bakiye", f"Gerekli: **{money(total)}**\nCüzdan: **{money(user['balance'])}**"))
            return
        update_user_money(ctx.author.id, ctx.guild.id, balance_delta=-total, note=f"Market: {item['name']} x{quantity}", tx_type="market")
        add_inventory(ctx.author.id, ctx.guild.id, item_key, quantity)
        await ctx.send(embed=success_embed("Satın alma tamamlandı", f"{item['emoji']} **{item['name']} x{quantity}**\nBirim fiyat: **{money(unit_price)}**\nToplam: **{money(total)}**"))

    @commands.hybrid_command(name="sat", description="Envanterindeki ürünü satar.")
    async def sell(self, ctx, item_key: str, quantity: int = 1):
        create_user(ctx.author.id, ctx.guild.id)
        item_key = item_key.lower()
        item = PRODUCTS.get(item_key)
        if not item or quantity <= 0:
            await ctx.send(embed=error_embed("Geçersiz ürün", "`l market` ile ürün kodlarını kontrol et."))
            return
        rows = {row["item_key"]: row["quantity"] for row in get_inventory(ctx.author.id, ctx.guild.id)}
        owned = rows.get(item_key, 0)
        if owned < quantity:
            await ctx.send(embed=error_embed("Yetersiz eşya", f"Envanterinde **{owned} adet** var."))
            return
        unit_price = max(1, int(item["sell"] * random.uniform(0.96, 1.06)))
        total = unit_price * quantity
        add_inventory(ctx.author.id, ctx.guild.id, item_key, -quantity)
        update_user_money(ctx.author.id, ctx.guild.id, balance_delta=total, note=f"Market satışı: {item['name']} x{quantity}", tx_type="satış")
        await ctx.send(embed=success_embed("Satış tamamlandı", f"{item['emoji']} **{item['name']} x{quantity}** satıldı.\nToplam gelir: **{money(total)}**"))


async def setup(bot):
    await bot.add_cog(Market(bot))
