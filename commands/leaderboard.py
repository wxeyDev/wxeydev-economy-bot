import discord
from discord.ext import commands

from database.database import create_user, leaderboard
from systems.ui import user_embed, money


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="siralamalar", aliases=["sıralamalar"], description="Sunucu ekonomi sıralamalarını gösterir.")
    async def rankings(self, ctx):
        create_user(ctx.author.id, ctx.guild.id)
        rich = leaderboard(ctx.guild.id, "balance", 10)
        levels = leaderboard(ctx.guild.id, "level", 10)
        lines_rich = []
        for i, row in enumerate(rich, 1):
            lines_rich.append(f"**{i}.** <@{row['user_id']}> — **{money(row['balance'])}**")
        lines_level = []
        for i, row in enumerate(levels, 1):
            lines_level.append(f"**{i}.** <@{row['user_id']}> — **Level {row['level']}**")
        embed = user_embed(ctx.author, "🏆 LOAN • Sıralamalar", "Bu sunucudaki oyuncu sıralamaları.")
        embed.add_field(name="💰 Zenginlik", value="\n".join(lines_rich) or "Henüz veri yok.", inline=False)
        embed.add_field(name="Level", value="\n".join(lines_level) or "Henüz veri yok.", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
