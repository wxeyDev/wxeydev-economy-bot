import discord
from discord.ext import commands

from database.database import create_user, get_company_by_user, get_inventory, get_user
from systems.ui import money, user_embed


class ProfileView(discord.ui.View):
    def __init__(self, bot, owner_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Bu paneli sadece komutu kullanan kişi yönetebilir.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Yenile", emoji="🔄", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog("Profile")
        if cog:
            embed = cog.make_embed(interaction.guild.id, interaction.user)
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Kapat", emoji="✖️", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Profil kapatıldı.", embed=None, view=None)


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def make_embed(self, guild_id, user):
        create_user(user.id, guild_id)
        row = get_user(user.id, guild_id)
        required = row["level"] * 1000
        filled = round(min(row["xp"] / required, 1) * 20)
        bar = "█" * filled + "░" * (20 - filled)
        company = get_company_by_user(guild_id, user.id)
        inventory = get_inventory(user.id, guild_id)

        embed = user_embed(user, "👤 LOAN • Profil", "Hesabının genel durumu.")
        embed.add_field(name="💵 Cüzdan", value=f"**{money(row['balance'])}**", inline=True)
        embed.add_field(name="🏦 Banka", value=f"**{money(row['bank'])}**", inline=True)
        embed.add_field(name="💎 Net Varlık", value=f"**{money(row['balance'] + row['bank'])}**", inline=False)
        embed.add_field(name=f"Level {row['level']}", value=f"`{bar}`\n`{row['xp']:,} / {required:,} XP`", inline=False)
        job_text = "Meslek seçilmemiş" if not row["job_key"] else f"{row['job_key'].title()} • Seviye {row['job_level']}"
        company_text = "Şirket yok" if not company else company["name"]
        embed.add_field(name="Kariyer", value=f"Meslek: **{job_text}**\nŞirket: **{company_text}**", inline=False)
        embed.add_field(name="Envanter", value=f"**{len(inventory)} farklı eşya**", inline=True)
        embed.add_field(name="Günlük Seri", value=f"**{row['daily_streak']} gün**", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    @commands.hybrid_command(name="profil", description="Loan profilini gösterir.")
    async def profile(self, ctx):
        embed = self.make_embed(ctx.guild.id, ctx.author)
        await ctx.send(embed=embed, view=ProfileView(self.bot, ctx.author.id))


async def setup(bot):
    await bot.add_cog(Profile(bot))
