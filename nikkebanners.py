import asyncio
import datetime
import re
import discord
from discord.ext import commands
from bs4 import BeautifulSoup

import nikke

PRYDWEN_BANNERS = "https://www.prydwen.gg/nikke/banners"
CACHE_TTL = 300
_banner_cache = {"ts": 0.0, "banners": []}

RARITY_COLORS = {
    "SSR": 0x9B59B6,
    "SR": 0xF1C40F,
    "R": 0x3498DB,
}

# banner chips use weapon abbreviations ("RL"), our emoji map uses full names
WEAPON_LABELS = {
    "AR": "Assault Rifle",
    "SR": "Sniper Rifle",
    "RL": "Rocket Launcher",
    "SMG": "SMG",
    "SG": "Shotgun",
    "MG": "Minigun",
}


def _epoch(value):
    try:
        return int(
            datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        )
    except Exception:
        return None


def _parse_banners(html):
    soup = BeautifulSoup(html, "html.parser")
    banners = []
    for section, label in (
        ("current-character", "current"),
        ("upcoming-character", "next"),
    ):
        grid = soup.select_one(f'div.banner-grid[data-banner-grid="{section}"]')
        if not grid:
            continue
        for card in grid.select("article.banner-card"):
            name_el = card.select_one("p.banner-name")
            link = card.select_one("a.banner-card-link")
            art = card.select_one(".banner-art img")
            rarity_el = card.select_one("span.rarity")
            kind_el = card.select_one("span.banner-type")
            timer = card.select_one(".art-timer")
            phase_name = card.select_one(".banner-phase-meta span")
            phase_range = card.select_one(".banner-phase-meta strong")
            copy_el = card.select_one(".banner-copy")

            chips = {}
            for chip in card.select("span.icon-chip"):
                title = chip.get("title") or ""
                key, _, value = title.partition(":")
                if value:
                    chips[key.strip().lower()] = value.strip()

            rateups = [
                {
                    "text": a.get_text(strip=True),
                    "href": a.get("href", ""),
                }
                for a in card.select("a.featured-rate-up")
            ]

            banner = {
                "section": label,
                "name": name_el.get_text(strip=True) if name_el else "",
                "slug": (link.get("href") or "").rsplit("/", 1)[-1] if link else "",
                "art": art.get("src") if art else None,
                "rarity": rarity_el.get_text(strip=True) if rarity_el else "",
                "kind": kind_el.get_text(strip=True) if kind_el else "",
                "mode": (timer.get("data-mode", "") or "") if timer else "",
                "start": _epoch(timer.get("data-start-global", "")) if timer else None,
                "end": _epoch(timer.get("data-end-global", "")) if timer else None,
                "phase": phase_name.get_text(strip=True) if phase_name else "",
                "range": phase_range.get_text(strip=True) if phase_range else "",
                "chips": chips,
                "copy": copy_el.get_text(" ", strip=True) if copy_el else "",
                "rateups": rateups,
            }
            # upcoming cards don't carry a rarity chip; the copy does
            # ("the new Limited SSR debuting in ...")
            if not banner["rarity"] and banner["copy"]:
                match = re.search(r"Limited (SSR)|\b(SSR|SR)\b", banner["copy"])
                if match:
                    banner["rarity"] = match.group(1) or match.group(2)
            if banner["name"] or banner["slug"]:
                banners.append(banner)
    return banners


async def fetch_prydwen_banners():
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if _banner_cache["banners"] and now - _banner_cache["ts"] < CACHE_TTL:
        return _banner_cache["banners"]

    html = await asyncio.to_thread(nikke._get_html, PRYDWEN_BANNERS)
    banners = _parse_banners(html)
    if banners:
        _banner_cache["banners"] = banners
        _banner_cache["ts"] = now
    return banners


def _chip_line(chips):
    parts = []
    weapon = chips.get("weapon", "")
    if weapon:
        emoji = nikke.WEAPON_EMOJIS.get(WEAPON_LABELS.get(weapon, weapon), "")
        parts.append(f"{emoji} **{weapon}**".strip())
    role = chips.get("role", "")
    if role:
        emoji = nikke.CLASS_EMOJIS.get(role, "")
        parts.append((f"{emoji} " if emoji else "") + f"**{role}**")
    manufacturer = chips.get("manufacturer", "")
    if manufacturer:
        emoji = nikke.MANUFACTURER_EMOJIS.get(manufacturer, "")
        parts.append((f"{emoji} " if emoji else "") + f"**{manufacturer}**")
    element = chips.get("element", "")
    if element:
        emoji = nikke.ELEMENT_EMOJIS.get(element, "")
        parts.append((f"{emoji} " if emoji else "") + f"**{element}**")
    return " | ".join(parts)


def _banner_container(banner, page=None):
    container = discord.ui.Container(
        accent_color=discord.Color(RARITY_COLORS.get(banner["rarity"], nikke.TREASURE_COLOR))
    )

    subparts = []
    kind = banner["kind"].capitalize() if banner["kind"] else ""
    if kind:
        subparts.append(kind)
    rarity_emoji = nikke.RARITY_EMOJIS.get(banner["rarity"], "")
    if rarity_emoji:
        subparts.append(rarity_emoji)
    if banner["phase"]:
        subparts.append(banner["phase"])
    sub = f"-# {' • '.join(subparts)}" if subparts else ""
    heading = f"## {banner['name']}"
    container.add_item(
        discord.ui.TextDisplay(f"{heading}\n{sub}" if sub else heading)
    )

    if banner["art"]:
        container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(banner["art"])))
        container.add_item(discord.ui.Separator())

    chips = _chip_line(banner["chips"])
    info_lines = []
    if page:
        info_lines.append(f"-# Banner {page}")
    is_live = banner["section"] == "current" and banner["mode"] != "upcoming"
    if not is_live and banner["start"]:
        # upcoming cards: data-start-global holds the expected start date
        info_lines.append(f"-# Expected start on <t:{banner['start']}:F> (<t:{banner['start']}:R>)")
    if banner["end"]:
        info_lines.append(
            f"-# Ends on <t:{banner['end']}:F> (<t:{banner['end']}:R>)" if is_live
            else f"-# Scheduled until <t:{banner['end']}:F>"
        )
    if not (banner["start"] or banner["end"]) and banner["range"]:
        info_lines.append(f"-# {banner['range']}")
    if chips:
        info_lines.append(chips)
    if info_lines:
        container.add_item(discord.ui.TextDisplay("\n".join(info_lines)))

    if banner["copy"]:
        container.add_item(discord.ui.TextDisplay(banner["copy"][:4000]))

    return container


class _PagerButton(discord.ui.Button):
    def __init__(self, pager, forward):
        super().__init__(
            label="Next ▶" if forward else "◀ Previous",
            style=discord.ButtonStyle.secondary,
        )
        self.pager = pager
        self.forward = forward

    async def callback(self, interaction: discord.Interaction):
        pager = self.pager
        if self.forward:
            pager.index = min(pager.index + 1, len(pager.banners) - 1)
        else:
            pager.index = max(pager.index - 1, 0)
        pager.rebuild()
        await interaction.response.edit_message(view=pager)


class BannerPagerView(discord.ui.LayoutView):
    def __init__(self, banners):
        super().__init__(timeout=None)
        self.banners = banners
        self.index = 0
        self.rebuild()

    def rebuild(self):
        self.index = max(0, min(self.index, len(self.banners) - 1))
        self.clear_items()
        banner = self.banners[self.index]
        page = f"{self.index + 1} of {len(self.banners)}" if len(self.banners) > 1 else None
        container = _banner_container(banner, page=page)
        if len(self.banners) > 1:
            prev = _PagerButton(self, False)
            nxt = _PagerButton(self, True)
            prev.disabled = self.index == 0
            nxt.disabled = self.index >= len(self.banners) - 1
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.ActionRow(prev, nxt))
        self.add_item(container)


class NikkeBannersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("nikkebanners loaded")

    @discord.app_commands.command(
        name="banners",
        description="Show current and upcoming NIKKE banners"
    )
    async def banners_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            banners = await fetch_prydwen_banners()
        except Exception as e:
            await interaction.followup.send(
                f"Failed to load banners right now: {e}", ephemeral=True
            )
            return

        if not banners:
            await interaction.followup.send(
                "No banner data could be parsed. Let an admin know!", ephemeral=True
            )
            return

        view = BannerPagerView(banners)
        await interaction.followup.send(view=view)


async def setup(bot):
    await bot.add_cog(NikkeBannersCog(bot))
