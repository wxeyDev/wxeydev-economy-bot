import discord
from discord.ext import commands

from database.database import (
    add_company_employee,
    create_company,
    create_user,
    get_company_by_user,
    get_company_members,
    get_user,
    claim_salary,
    remove_company_employee,
    update_user_money,
    update_company,
)
from systems.ui import error_embed, money, success_embed, user_embed

COMPANY_COST = 5000


class Company(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="sirket", aliases=["şirket"], description="Şirket bilgilerini gösterir veya şirket kurar.")
    async def company(self, ctx, *, name: str = None):
        create_user(ctx.author.id, ctx.guild.id)
        company = get_company_by_user(ctx.guild.id, ctx.author.id)
        if name is not None:
            if company:
                await ctx.send(embed=error_embed("Zaten şirketin var", f"Mevcut şirketin: **{company['name']}**"))
                return
            clean = name.strip()
            if len(clean) < 3 or len(clean) > 30:
                await ctx.send(embed=error_embed("Geçersiz şirket adı", "Şirket adı 3-30 karakter arasında olmalı."))
                return
            user = get_user(ctx.author.id, ctx.guild.id)
            if user["balance"] < COMPANY_COST:
                await ctx.send(embed=error_embed("Yetersiz bakiye", f"Şirket kurmak için **{money(COMPANY_COST)}** gerekiyor."))
                return
            create_company(ctx.guild.id, ctx.author.id, clean, COMPANY_COST)
            update_user_money(ctx.author.id, ctx.guild.id, balance_delta=-COMPANY_COST, note=f"Şirket kuruldu: {clean}", tx_type="şirket")
            await ctx.send(embed=success_embed("Şirket kuruldu", f"🏢 **{clean}** artık senin şirketin.\nBaşlangıç kasası: **{money(COMPANY_COST)}**"))
            return

        if not company:
            await ctx.send(embed=error_embed("Şirket yok", f"Şirket kurmak için `l sirket [isim]` kullan.\nKurulum ücreti: **{money(COMPANY_COST)}**"))
            return
        members = get_company_members(company["id"])
        lines = []
        for member in members[:15]:
            role = member["role"]
            lines.append(f"<@{member['user_id']}> — {role} · Maaş {money(member['salary'])}")
        value = company["treasury"] + (company["level"] * 5000)
        embed = user_embed(ctx.author, f"🏢 {company['name']}", "Şirket merkezi")
        embed.add_field(name="Kasa", value=f"**{money(company['treasury'])}**", inline=True)
        embed.add_field(name="Seviye", value=f"**{company['level']}**", inline=True)
        embed.add_field(name="Tahmini Değer", value=f"**{money(value)}**", inline=True)
        embed.add_field(name="Çalışanlar", value="\n".join(lines) if lines else "Yok", inline=False)
        embed.add_field(name="Yönetim", value="`l iseal @kullanıcı 1000`\n`l istenkar @kullanıcı`", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="iseal", description="Şirketine bir çalışan alır.")
    async def hire(self, ctx, member: discord.Member, salary: int):
        company = get_company_by_user(ctx.guild.id, ctx.author.id)
        if not company or company["owner_id"] != ctx.author.id:
            await ctx.send(embed=error_embed("Yetki yok", "Bu komut sadece şirket sahibine açık."))
            return
        if member.bot or member.id == ctx.author.id or salary < 0:
            await ctx.send(embed=error_embed("Geçersiz çalışan", "Botları/kendini ekleyemezsin ve maaş negatif olamaz."))
            return
        create_user(member.id, ctx.guild.id)
        if get_company_by_user(ctx.guild.id, member.id):
            await ctx.send(embed=error_embed("Çalışan zaten şirkette", "Bu kullanıcının zaten bir şirketi/işi var."))
            return
        if not add_company_employee(ctx.guild.id, company["id"], member.id, salary):
            await ctx.send(embed=error_embed("İşlem başarısız", "Çalışan eklenemedi."))
            return
        update_company(ctx.guild.id, company["id"], xp_delta=100)
        await ctx.send(embed=success_embed("Çalışan işe alındı", f"{member.mention} şirkete katıldı. Maaş: **{money(salary)}**"))

    @commands.hybrid_command(name="istenkar", description="Şirketinden bir çalışanı çıkarır.")
    async def fire(self, ctx, member: discord.Member):
        company = get_company_by_user(ctx.guild.id, ctx.author.id)
        if not company or company["owner_id"] != ctx.author.id:
            await ctx.send(embed=error_embed("Yetki yok", "Bu komut sadece şirket sahibine açık."))
            return
        if member.id == ctx.author.id:
            await ctx.send(embed=error_embed("Geçersiz işlem", "Şirket sahibini işten çıkaramazsın."))
            return
        if not remove_company_employee(company["id"], member.id):
            await ctx.send(embed=error_embed("Çalışan bulunamadı", "Bu kullanıcı şirketinde görünmüyor."))
            return
        await ctx.send(embed=success_embed("Çalışan çıkarıldı", f"{member.mention} şirketten çıkarıldı."))

    @commands.hybrid_command(name="maas", aliases=["maaş"], description="Şirket maaşını günlük olarak alır.")
    async def salary(self, ctx):
        company = get_company_by_user(ctx.guild.id, ctx.author.id)
        if not company:
            await ctx.send(embed=error_embed("Şirket yok", "Maaş alabilmek için bir şirkette çalışan olmalısın."))
            return
        result = claim_salary(ctx.guild.id, company["id"], ctx.author.id)
        if not result["ok"]:
            messages = {
                "not_member": "Bu şirketin çalışanı değilsin.",
                "zero_salary": "Tanımlı bir maaşın yok.",
                "treasury": f"Şirket kasasında yeterli para yok. Kasa: **{money(result['treasury'])}**",
            }
            if result["reason"] == "cooldown":
                left = result["remaining"]
                messages["cooldown"] = f"Maaş için yaklaşık **{left // 3600}s {(left % 3600) // 60}dk** bekle."
            await ctx.send(embed=error_embed("Maaş alınamadı", messages.get(result["reason"], "İşlem başarısız.")))
            return
        await ctx.send(embed=success_embed("Maaş alındı", f"Şirketinden **{money(result['salary'])}** maaş aldın."))

    @commands.hybrid_command(name="sirketayril", aliases=["şirketayrıl", "sirketayrıl"], description="Çalışanı olduğun şirketten ayrılır.")
    async def leave_company(self, ctx):
        company = get_company_by_user(ctx.guild.id, ctx.author.id)
        if not company:
            await ctx.send(embed=error_embed("Şirket yok", "Bir şirketin içinde değilsin."))
            return
        if company["owner_id"] == ctx.author.id:
            await ctx.send(embed=error_embed("Kurucu ayrılamaz", "Kurucunun şirketi kapatması/başka sisteme devretmesi gerekir."))
            return
        remove_company_employee(company["id"], ctx.author.id)
        await ctx.send(embed=success_embed("Şirketten ayrıldın", f"**{company['name']}** şirketinden ayrıldın."))


async def setup(bot):
    await bot.add_cog(Company(bot))
