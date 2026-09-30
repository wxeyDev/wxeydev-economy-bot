import discord

LOAN_COLOR = discord.Color.from_rgb(88, 101, 242)
SUCCESS_COLOR = discord.Color.from_rgb(46, 204, 113)
ERROR_COLOR = discord.Color.from_rgb(231, 76, 60)
WARNING_COLOR = discord.Color.from_rgb(241, 196, 15)
INFO_COLOR = discord.Color.from_rgb(52, 152, 219)


def create_embed(title, description=None, color=LOAN_COLOR):
    embed = discord.Embed(title=title, description=description or "", color=color)
    embed.set_footer(text="Loan • Ekonomi & Sosyal Sistem")
    return embed


def user_embed(user, title, description=None, color=LOAN_COLOR):
    embed = create_embed(title, description, color)
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    return embed


def success_embed(title, description):
    return create_embed(f"✅ {title}", description, SUCCESS_COLOR)


def error_embed(title, description):
    return create_embed(f"❌ {title}", description, ERROR_COLOR)


def warning_embed(title, description):
    return create_embed(f"⚠️ {title}", description, WARNING_COLOR)


def info_embed(title, description):
    return create_embed(f"ℹ️ {title}", description, INFO_COLOR)


def money(amount):
    if isinstance(amount, float):
        return f"${amount:,.2f}"
    return f"${amount:,}"


def xp_bar(current, required, length=20):
    if required <= 0:
        return "█" * length
    ratio = max(0.0, min(current / required, 1.0))
    filled = round(ratio * length)
    return "█" * filled + "░" * (length - filled)


def pct(value):
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"
