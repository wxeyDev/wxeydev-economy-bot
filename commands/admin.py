import discord
from discord.ext import commands

from database.database import create_user, ensure_guild, get_user, set_money
from systems.ui import error_embed, success_embed, user_embed, money


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def is_admin(self, ctx):
        return isinstance(ctx.author, discord.Member) and ctx.author.guild_permissions.administrator

    @commands.hybrid_command(name="para", description="Yönetici: kullanıcıya para verir.")
    async def give_money(self, ctx, member: discord.Member, amount: int):
        if not await self.is_admin(ctx):
            await ctx.send(embed=error_embed("Yetki yok", "Bu komut sadece yöneticilere açık."))
            return
        if member.bot or amount <= 0:
            await ctx.send(embed=error_embed("Geçersiz işlem", "Botlara veya negatif/0 miktara işlem yapılamaz."))
            return
        create_user(member.id, ctx.guild.id)
        row = get_user(member.id, ctx.guild.id)
        set_money(member.id, ctx.guild.id, balance=row["balance"] + amount, bank=row["bank"], note=f"Yönetici tarafından {ctx.author.id} verildi", tx_type="admin")
        await ctx.send(embed=success_embed("Para verildi", f"{member.mention} kullanıcısına **{money(amount)}** verildi."))

    @commands.hybrid_command(name="paraal", description="Yönetici: kullanıcıdan para alır.")
    async def take_money(self, ctx, member: discord.Member, amount: int):
        if not await self.is_admin(ctx):
            await ctx.send(embed=error_embed("Yetki yok", "Bu komut sadece yöneticilere açık."))
            return
        if member.bot or amount <= 0:
            await ctx.send(embed=error_embed("Geçersiz işlem", "Geçerli bir miktar gir."))
            return
        create_user(member.id, ctx.guild.id)
        row = get_user(member.id, ctx.guild.id)
        new_balance = max(0, row["balance"] - amount)
        removed = row["balance"] - new_balance
        set_money(member.id, ctx.guild.id, balance=new_balance, bank=row["bank"], note=f"Yönetici tarafından {ctx.author.id} alındı", tx_type="admin")
        await ctx.send(embed=success_embed("Para alındı", f"{member.mention} kullanıcısından **{money(removed)}** alındı."))

    @commands.hybrid_command(name="ekonomibilgi", description="Sunucunun ekonomi ayarlarını gösterir.")
    async def economy_info(self, ctx):
        settings = ensure_guild(ctx.guild.id)
        embed = user_embed(ctx.author, "⚙️ LOAN • Ekonomi Ayarları", "Bu sunucunun oyun içi ekonomi parametreleri.")
        embed.add_field(name="Başlangıç Parası", value=f"**{money(settings['starting_money'])}**", inline=True)
        embed.add_field(name="Günlük Ödül", value=f"**{money(settings['daily_reward'])}**", inline=True)
        embed.add_field(name="Banka Faizi", value=f"**{settings['bank_interest'] * 100:.2f}%**", inline=True)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))
