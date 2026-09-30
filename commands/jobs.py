import random

import discord
from discord.ext import commands

from database.database import add_job_xp, add_xp, create_user, get_user, set_job, update_user_money
from systems.catalog import JOBS
from systems.cooldowns import remaining, set_cooldown
from systems.ui import error_embed, success_embed, user_embed


class JobSelect(discord.ui.Select):
    def __init__(self, owner_id):
        options = [
            discord.SelectOption(label=data["name"], value=key, emoji=data["emoji"], description=data["description"])
            for key, data in JOBS.items()
        ]
        super().__init__(placeholder="Bir meslek seç...", options=options)
        self.owner_id = owner_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Bu menüyü sadece komutu kullanan kişi kullanabilir.", ephemeral=True)
            return
        set_job(interaction.user.id, interaction.guild.id, self.values[0])
        job = JOBS[self.values[0]]
        embed = success_embed("Meslek seçildi", f"Yeni mesleğin **{job['emoji']} {job['name']}**.\n\n`l calis` ile çalışabilirsin.")
        await interaction.response.edit_message(embed=embed, view=None)


class JobView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=120)
        self.add_item(JobSelect(owner_id))


class Jobs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="meslekler", description="Tüm meslekleri gösterir.")
    async def jobs(self, ctx):
        create_user(ctx.author.id, ctx.guild.id)
        lines = []
        for key, job in JOBS.items():
            lines.append(f"{job['emoji']} **{job['name']}** — `{job['min']}-{job['max']}$` · {job['description']}")
        embed = user_embed(ctx.author, "💼 LOAN • Meslekler", "Çalışarak para ve XP kazanabileceğin meslekler.")
        embed.description = "\n".join(lines)
        await ctx.send(embed=embed, view=JobView(ctx.author.id))

    @commands.hybrid_command(name="meslek", description="Mevcut mesleğini veya seçtiğin mesleği gösterir.")
    async def job(self, ctx, key: str = None):
        create_user(ctx.author.id, ctx.guild.id)
        if key is None:
            row = get_user(ctx.author.id, ctx.guild.id)
            if not row["job_key"]:
                await ctx.send(embed=error_embed("Meslek yok", "`l meslekler` yazıp bir meslek seç."))
                return
            job = JOBS.get(row["job_key"])
            await ctx.send(embed=user_embed(ctx.author, "💼 Mevcut Meslek", f"{job['emoji']} **{job['name']}**\nSeviye: **{row['job_level']}**\nMeslek XP: **{row['job_xp']:,}**"))
            return
        key = key.lower()
        if key not in JOBS:
            await ctx.send(embed=error_embed("Meslek bulunamadı", "Geçerli meslek için `l meslekler` yaz."))
            return
        set_job(ctx.author.id, ctx.guild.id, key)
        job = JOBS[key]
        await ctx.send(embed=success_embed("Meslek seçildi", f"Artık **{job['emoji']} {job['name']}** olarak çalışıyorsun."))

    @commands.hybrid_command(name="calis", aliases=["çalış"], description="Mesleğinde çalışarak para ve XP kazanır.")
    async def work(self, ctx):
        create_user(ctx.author.id, ctx.guild.id)
        row = get_user(ctx.author.id, ctx.guild.id)
        if not row["job_key"]:
            await ctx.send(embed=error_embed("Meslek seç", "Önce `l meslekler` ile bir meslek seç."))
            return
        key = row["job_key"]
        cd = remaining(f"work:{ctx.guild.id}:{ctx.author.id}")
        if cd:
            await ctx.send(embed=error_embed("Çalışma beklemede", f"Tekrar çalışmak için **{cd} saniye** bekle."))
            return
        job = JOBS[key]
        multiplier = 1 + ((row["job_level"] - 1) * 0.08)
        reward = int(random.randint(job["min"], job["max"]) * multiplier)
        earned_xp = random.randint(job["xp_min"], job["xp_max"])
        update_user_money(ctx.author.id, ctx.guild.id, balance_delta=reward, note=f"{job['name']} çalışması", tx_type="meslek")
        level_result = add_xp(ctx.author.id, ctx.guild.id, earned_xp)
        job_result = add_job_xp(ctx.author.id, ctx.guild.id, earned_xp)
        set_cooldown(f"work:{ctx.guild.id}:{ctx.author.id}", 60)
        text = f"{job['emoji']} Çalışmandan **{reward:,}$** kazandın.\nXP: **+{earned_xp}**"
        if level_result["leveled_up"]:
            text += f"\n\n🎉 Level atladın: **{level_result['level']}**"
        if job_result["leveled_up"]:
            text += f"\n💼 Meslek seviyen **{job_result['job_level']}** oldu."
        await ctx.send(embed=success_embed("Çalışma tamamlandı", text))


async def setup(bot):
    await bot.add_cog(Jobs(bot))
