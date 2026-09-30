import discord
from discord.ext import commands

from systems.ui import user_embed

CATEGORIES = {
    "ekonomi": {
        "label": "Ekonomi",
        "emoji": "💰",
        "title": "💰 LOAN • Ekonomi",
        "description": (
            "Temel para yönetimi ve oyuncular arası işlemler.\n\n"
            "`l bakiye` — Cüzdan, banka ve toplam varlık\n"
            "`l gunluk` — Günlük ödül + seri bonusu\n"
            "`l aktar @kullanıcı miktar` — Para gönder\n"
            "`l islemler` — Son finansal işlemler"
        ),
    },
    "banka": {
        "label": "Banka",
        "emoji": "🏦",
        "title": "🏦 LOAN • Banka",
        "description": (
            "Paranı bankaya taşıyıp yönetebilirsin.\n\n"
            "`l banka` — Banka paneli\n"
            "`l yatir 500` — Bankaya para yatır\n"
            "`l cek 500` — Bankadan para çek\n"
            "`l islemler` — İşlem geçmişi"
        ),
    },
    "meslek": {
        "label": "Meslekler",
        "emoji": "💼",
        "title": "💼 LOAN • Meslekler",
        "description": (
            "Meslek seç, çalış, meslek XP'si ve para kazan.\n\n"
            "`l meslekler` — Meslek listesini aç\n"
            "`l meslek madenci` — Meslek seç\n"
            "`l meslek` — Mevcut mesleği göster\n"
            "`l calis` — Çalış ve ödül kazan"
        ),
    },
    "market": {
        "label": "Market",
        "emoji": "🛒",
        "title": "🛒 LOAN • Market",
        "description": (
            "Sanal ürünleri alıp satabilir ve envanterini büyütebilirsin.\n\n"
            "`l market` — Ürün kataloğu\n"
            "`l al demir 2` — Ürün satın al\n"
            "`l sat demir 1` — Ürün sat\n"
            "`l envanter` — Eşyalarını göster"
        ),
    },
    "borsa": {
        "label": "Borsa",
        "emoji": "📈",
        "title": "📈 LOAN • Borsa",
        "description": (
            "Tamamen oyun içi sanal hisse sistemi.\n\n"
            "`l borsa` — Hisseleri ve fiyatları gör\n"
            "`l hisse NOVA` — Hisse detayı\n"
            "`l hisseal NOVA 2` — Hisse al\n"
            "`l hissesat NOVA 1` — Hisse sat\n"
            "`l portfoy` — Kâr/zarar ve portföy"
        ),
    },
    "sirket": {
        "label": "Şirketler",
        "emoji": "🏢",
        "title": "🏢 LOAN • Şirketler",
        "description": (
            "Kendi şirketini kur, çalışan al ve şirket seviyeni geliştir.\n\n"
            "`l sirket Atlas` — Şirket kur\n"
            "`l sirket` — Şirket merkezini göster\n"
            "`l iseal @kullanıcı 1000` — Çalışan al\n"
            "`l istenkar @kullanıcı` — Çalışan çıkar\n"
            "`l şirketayrıl` — Çalışan olarak ayrıl"
        ),
    },
    "profil": {
        "label": "Profil",
        "emoji": "👤",
        "title": "👤 LOAN • Profil",
        "description": (
            "Hesabının genel istatistiklerini burada görürsün.\n\n"
            "`l profil` — Profil paneli\n"
            "Panelde level/XP, meslek, şirket, envanter ve günlük seri bulunur."
        ),
    },
    "yonetim": {
        "label": "Yönetim",
        "emoji": "⚙️",
        "title": "⚙️ LOAN • Yönetim",
        "description": (
            "Yönetici komutları sunucu ekonomisini yönetmek için kullanılır.\n\n"
            "`l para @kullanıcı 5000` — Para ver\n"
            "`l paraal @kullanıcı 5000` — Para al\n"
            "`l ekonomibilgi` — Sunucu ekonomi ayarları"
        ),
    },
    "diger": {
        "label": "Diğer",
        "emoji": "📚",
        "title": "📚 LOAN • Diğer",
        "description": (
            "Loan komutları sunucu bazında ayrı ekonomi verisi kullanır.\n\n"
            "Prefix: `l ` + komut\n"
            "Örnek: `l bakiye`, `l market`, `l profil`\n\n"
            "Slash komutları global olarak senkronize edilir; Discord'da görünmesi biraz zaman alabilir."
        ),
    },
}


class HelpSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id
        options = [
            discord.SelectOption(label=data["label"], value=key, emoji=data["emoji"])
            for key, data in CATEGORIES.items()
        ]
        super().__init__(placeholder="Bir kategori seç...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Bu bilgi panelini sadece komutu kullanan kişi yönetebilir.", ephemeral=True)
            return
        data = CATEGORIES[self.values[0]]
        embed = user_embed(interaction.user, data["title"], data["description"])
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.select = HelpSelect(owner_id)
        self.add_item(self.select)

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Bu bilgi panelini sadece komutu kullanan kişi yönetebilir.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Ana Menü", emoji="🏠", style=discord.ButtonStyle.secondary, row=1)
    async def home(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = {
            "title": "📘 LOAN • Bilgi Merkezi",
            "description": "Loan'daki komutları kategori kategori inceleyebilirsin.\n\nAşağıdaki menüden bir kategori seç."
        }
        embed = user_embed(interaction.user, data["title"], data["description"])
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Kapat", emoji="✖️", style=discord.ButtonStyle.danger, row=1)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Bilgi paneli kapatıldı.", embed=None, view=None)


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="bilgi", aliases=["yardım", "yardim"], description="Loan komutlarını ve kullanım açıklamalarını gösterir.")
    async def help(self, ctx):
        embed = user_embed(
            ctx.author,
            "📘 LOAN • Bilgi Merkezi",
            "Loan'daki komutları kategori kategori inceleyebilirsin.\n\nAşağıdaki menüden bir kategori seç."
        )
        await ctx.send(embed=embed, view=HelpView(ctx.author.id))


async def setup(bot):
    await bot.add_cog(Help(bot))
