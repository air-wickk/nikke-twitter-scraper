import discord
from discord import app_commands
from discord.ext import commands, tasks

import aiohttp
import io
from PIL import Image

import nikke


TEAM_SIZE = 5

# Global character list
NIKKE_LIST = []

# The roster comes from Prydwen (same source as /nikke), built from the
# listing page itself (name, burst, element, rarity, card art) so no
# per-character pages are needed at all.

async def fetch_nikke():
    """Build the team roster from Prydwen's enriched character index."""
    global NIKKE_LIST

    try:
        await nikke.fetch_prydwen_index()
    except Exception as e:
        print(f"Prydwen index fetch failed, previous roster retained: {e}")
        return

    roster = nikke.PRYDWEN_CHARACTERS

    # counter to the old dotgg roster, every entry here is a distinct group
    # from Prydwen's index, so searching "red hood" no longer offers a
    # dotgg-era duplicate; alt costumes ("Rupee: Winter Shopper") are
    # separate units and stay in the list
    picked = roster

    entries = []
    for entry in picked:
        slug = entry["slug"]
        # cropped head shot, same art the /nikke command uses for thumbnails
        head_art = f"https://cdn.prydwen.gg/images/nikke/characters/{slug}.webp"
        entries.append({
            "name": entry["name"],
            "url": slug,
            "img": head_art,
            "burst": entry.get("burst", ""),
            "rarity": entry.get("rarity", ""),
            "element": entry.get("element", ""),
        })

    if entries:
        NIKKE_LIST = entries
        print(f"Loaded {len(NIKKE_LIST)} team characters from Prydwen.")


def get_character_by_name(character_name):
    """Return the character dict from NIKKE_LIST by name, or None if not found."""
    for character in NIKKE_LIST:
        if character.get("name") == character_name:
            return character
    return None

# -------------------- SELECTS -------------------- #

# --- Slot-based Team Builder --- #
class NikkeSearchModal(discord.ui.Modal, title="Search for a NIKKE"):
    nikke_name = discord.ui.TextInput(label="Enter NIKKE name (partial or full):", required=True)

    def __init__(self, slot_index, current_team):
        super().__init__()
        self.slot_index = slot_index
        self.current_team = current_team

    async def on_submit(self, interaction: discord.Interaction):
        query = self.nikke_name.value.strip().lower()
        # Always show dropdown if more than one match, even if one is exact
        matches = [c for c in NIKKE_LIST if c.get("name", "").lower() == query]
        startswith_matches = [c for c in NIKKE_LIST if c.get("name", "").lower().startswith(query) and c not in matches]
        wordstart_matches = [c for c in NIKKE_LIST if any(word.startswith(query) for word in c.get("name", "").lower().split()) and c not in matches and c not in startswith_matches]
        all_matches = matches + startswith_matches + wordstart_matches
        if not all_matches:
            await interaction.response.edit_message(
                content=f"No NIKKE found for '{query}'. Try again.",
                view=NikkeTeamSlotView(self.current_team),
                embed=build_team_preview_embed(self.current_team)
            )
            return
        if len(all_matches) == 1:
            chosen = all_matches[0]
            new_team = self.current_team.copy()
            new_team[self.slot_index] = chosen.get("name")
            await interaction.response.edit_message(
                content=None,
                view=NikkeTeamSlotView(new_team),
                embed=build_team_preview_embed(new_team)
            )
        else:
            # Multiple matches: always show a select menu for user to pick
            await interaction.response.edit_message(
                content=f"Multiple matches found for '{query}'. Please select:",
                view=NikkeAmbiguousSelectView(self.slot_index, self.current_team, all_matches),
                embed=build_team_preview_embed(self.current_team)
            )

class NikkeTeamSlotButton(discord.ui.Button):
    def __init__(self, slot_index, current_team):
        label = f"Slot {slot_index+1}"
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.slot_index = slot_index
        self.current_team = current_team

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(NikkeSearchModal(self.slot_index, self.current_team))

class FinishTeamButton(discord.ui.Button):
    def __init__(self, current_team):
        super().__init__(label="Finish & Confirm Team", style=discord.ButtonStyle.success)
        self.current_team = current_team

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TeamTitleModal(self.current_team))

class NikkeTeamSlotView(discord.ui.View):
    def __init__(self, current_team):
        super().__init__(timeout=300)
        for i in range(TEAM_SIZE):
            self.add_item(NikkeTeamSlotButton(i, current_team))
        if all(current_team):
            self.add_item(FinishTeamButton(current_team))

def build_team_preview_embed(team_names):
    # The embed title will be set by the command, so no need for a static title here
    embed = discord.Embed(color=discord.Color.blurple())
    team_lines = []
    max_name_len = 0
    for name in team_names:
        if name:
            char = get_character_by_name(name)
            if char:
                char_name = char.get('name', '?')
                if len(char_name) > max_name_len:
                    max_name_len = len(char_name)
    for idx, name in enumerate(team_names):
        if name:
            char = get_character_by_name(name)
            if char:
                char_name = char.get('name', '?')
                element_emoji = nikke.ELEMENT_EMOJIS.get(char.get("element", "?"), "")
                padded_name = f"**{char_name}**" + " " * (max_name_len - len(char_name))
                team_lines.append(f"• {element_emoji} {padded_name}")
            else:
                team_lines.append("• —")
        else:
            team_lines.append("• —")
    embed.description = "\n".join(team_lines)
    embed.set_footer(text="Click a slot to change it. Confirm when ready.")
    return embed



# --- Helper functions for team image and embed --- #
def _character_image_url(char):
    """Resolve a character entry into an image URL ( Prydwen card art)."""
    if not char:
        return None
    img = char.get("img", "")
    if not img:
        return None
    if img.startswith("http://") or img.startswith("https://"):
        return img
    return f"https://cdn.prydwen.gg/images/nikke/characters/{img}.webp"

async def compose_team_image(character_names):
    from PIL import ImageDraw, ImageChops
    character_image_urls = []
    for name in character_names:
        url = _character_image_url(get_character_by_name(name))
        if url:
            character_image_urls.append(url)
    if len(character_image_urls) != 5:
        return None
    try:
        images = []
        async with aiohttp.ClientSession() as session:
            for url in character_image_urls:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        img_bytes = await resp.read()
                        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                        images.append(img)
        # soft, subdued element palettes: real top-to-bottom gradients
        # (light tint fading into a deeper tone) behind the head crops,
        # plus muted mid-tones for the tile borders
        element_gradients = {
            "Fire": [(233, 128, 104, 140), (152, 52, 40, 190)],
            "Wind": [(120, 214, 185, 140), (44, 148, 118, 190)],
            "Iron": [(238, 188, 136, 150), (186, 122, 62, 190)],
            "Electric": [(238, 148, 242, 140), (162, 84, 176, 190)],
            "Water": [(118, 178, 222, 140), (56, 116, 176, 190)]
        }
        element_colors = {
            "Fire": (198, 92, 70),
            "Wind": (74, 178, 150),
            "Iron": (212, 152, 92),
            "Electric": (204, 116, 210),
            "Water": (92, 154, 200)
        }
        bg_size = 432
        tile_radius = 30
        tile_gap = 14
        burst_emoji_ids = {
            1: "1412193379865071626",
            2: "1412193388748476478",
            3: "1412193401889361942",
            "ALL": "1412193411032682576"
        }
        async def fetch_emoji_img(session, emoji_id):
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
            async with session.get(url) as resp:
                if resp.status == 200:
                    img_bytes = await resp.read()
                    return Image.open(io.BytesIO(img_bytes)).convert("RGBA")
                return None

        async with aiohttp.ClientSession() as emoji_session:
            emoji_cache = {}
            for idx, img in enumerate(images):
                char_name = character_names[idx]
                char_data = get_character_by_name(char_name)
                element = char_data.get("element", "") if char_data else ""
                grad = element_gradients.get(element, [(255,255,255,32),(255,255,255,32)])
                tile = Image.new("RGBA", (bg_size, bg_size), (0,0,0,0))
                grad_draw = ImageDraw.Draw(tile)
                for y in range(bg_size):
                    ratio = y / float(bg_size - 1)
                    r = int(grad[0][0] * (1 - ratio) + grad[1][0] * ratio)
                    g = int(grad[0][1] * (1 - ratio) + grad[1][1] * ratio)
                    b = int(grad[0][2] * (1 - ratio) + grad[1][2] * ratio)
                    a = int(grad[0][3] * (1 - ratio) + grad[1][3] * ratio)
                    grad_draw.line([(0, y), (bg_size - 1, y)], fill=(r, g, b, a), width=1)
                img_resized = img.resize((bg_size, bg_size), Image.LANCZOS)
                tile.paste(img_resized, (0, 0), img_resized)
                burst = char_data.get("burst", "?") if char_data else "?"
                burst_key = None
                if isinstance(burst, int):
                    burst_key = burst
                elif isinstance(burst, str):
                    if burst.strip().isdigit():
                        burst_key = int(burst.strip())
                    elif burst.strip().upper() in ("P", "ALL"):
                        burst_key = "ALL"
                emoji_id = burst_emoji_ids.get(burst_key, burst_emoji_ids.get("ALL"))
                if emoji_id not in emoji_cache:
                    emoji_img = await fetch_emoji_img(emoji_session, emoji_id)
                    emoji_cache[emoji_id] = emoji_img
                else:
                    emoji_img = emoji_cache[emoji_id]
                if emoji_img:
                    emoji_size = int(bg_size * 0.22)
                    emoji_img = emoji_img.resize((emoji_size, emoji_size), Image.LANCZOS)
                    tile.paste(emoji_img, (18, 18), emoji_img)

                # clip everything to a rounded tile, then add the element border
                corner_mask = Image.new("L", (bg_size, bg_size), 0)
                ImageDraw.Draw(corner_mask).rounded_rectangle(
                    [0, 0, bg_size - 1, bg_size - 1], radius=tile_radius, fill=255
                )
                tile.putalpha(ImageChops.multiply(tile.getchannel("A"), corner_mask))

                tile_draw = ImageDraw.Draw(tile)
                border_color = element_colors.get(element, (255, 255, 255))
                tile_draw.rounded_rectangle(
                    [2, 2, bg_size - 3, bg_size - 3],
                    radius=tile_radius,
                    outline=border_color + (170,),
                    width=4,
                )
                images[idx] = tile

        composite_width = (
            len(images) * bg_size + (len(images) - 1) * tile_gap + tile_gap * 2
        )
        composite_height = bg_size + tile_gap * 2
        composite = Image.new("RGBA", (composite_width, composite_height), (0,0,0,0))

        x_offset = tile_gap
        for tile in images:
            composite.alpha_composite(tile, (x_offset, tile_gap))
            x_offset += bg_size + tile_gap
        with io.BytesIO() as image_binary:
            composite.save(image_binary, format="PNG")
            image_binary.seek(0)
            return image_binary.read()
    except Exception:
        return None

# -------------------- FINAL TEAM CARD -------------------- #
class TeamTitleModal(discord.ui.Modal, title="Team Title"):
    team_title = discord.ui.TextInput(label="Enter a title for your team (optional):", required=False, min_length=0)

    def __init__(self, selected_character_names):
        super().__init__()
        self.selected_character_names = selected_character_names

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_display_name = interaction.user.display_name if hasattr(interaction.user, 'display_name') else interaction.user.name
        title_value = self.team_title.value.strip() if self.team_title.value else ""
        card_title = title_value if title_value else f"{user_display_name}'s NIKKE Team"

        image_bytes = await compose_team_image(self.selected_character_names)
        gallery_urls = []
        file = None
        if image_bytes:
            file = discord.File(io.BytesIO(image_bytes), filename="team.png")
            gallery_urls.append("attachment://team.png")
        else:
            # fallback: show every member's splash, no compositing needed
            for name in self.selected_character_names:
                url = _character_image_url(get_character_by_name(name))
                if url:
                    gallery_urls.append(url)

        view = TeamCardView(card_title, self.selected_character_names, gallery_urls, byline=user_display_name)
        channel = interaction.client.get_channel(interaction.channel_id)
        if file:
            await channel.send(view=view, file=file)
        else:
            await channel.send(view=view)


# -------------------- TABBED TEAM CARD -------------------- #
def _member_lines(character_names):
    lines = []
    for name in character_names:
        char = get_character_by_name(name)
        if not char:
            lines.append("• —")
            continue
        element_emoji = nikke.ELEMENT_EMOJIS.get(char.get("element", "?"), "")
        lines.append(f"• {element_emoji} **{char.get('name', '?')}**")
    return "\n".join(lines)


class TeamCardView(discord.ui.LayoutView):
    def __init__(self, title, character_names, gallery_urls, byline=""):
        super().__init__(timeout=None)

        container = discord.ui.Container(accent_color=discord.Color.blue())

        header_lines = [f"## {title}"]
        if byline:
            header_lines.append(f"-# by {byline}")
        header = discord.ui.TextDisplay("\n".join(header_lines))
        splash = gallery_urls[0] if gallery_urls else None
        # don't reuse the composited banner as both banner and thumbnail
        if splash and splash.startswith("http"):
            container.add_item(discord.ui.Section(header, accessory=discord.ui.Thumbnail(media=splash)))
        else:
            container.add_item(header)

        if gallery_urls:
            gallery = discord.ui.MediaGallery(
                *(discord.MediaGalleryItem(url) for url in gallery_urls[:5])
            )
            container.add_item(gallery)

        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(_member_lines(character_names)))

        self.add_item(container)


# -------------------- COG -------------------- #
class NikkeTeamCog(commands.Cog):
    # - - - - - -  -- - -
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(fetch_nikke())
        self.refresh_characters.start()

    @tasks.loop(minutes=30)
    async def refresh_characters(self):
        """Refresh the roster (picks up new Prydwen-only characters)."""
        await fetch_nikke()

    @refresh_characters.before_loop
    async def before_refresh(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="buildteam", description="Build your NIKKE team")
    async def buildteam(self, interaction: discord.Interaction):
        team = [None] * TEAM_SIZE
        await interaction.response.send_message(
            "Click a slot to pick a NIKKE. You can change any slot before confirming:",
            view=NikkeTeamSlotView(team),
            embed=build_team_preview_embed(team),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(NikkeTeamCog(bot))

class NikkeAmbiguousSelect(discord.ui.Select):
    def __init__(self, slot_index, current_team, matches):
        options = [
            discord.SelectOption(label=char.get("name", "Unknown"), value=char.get("name", "Unknown"))
            for char in matches[:25]
        ]
        super().__init__(placeholder="⚠️ Multiple results found. Confirm the NIKKE:", min_values=1, max_values=1, options=options)
        self.slot_index = slot_index
        self.current_team = current_team

    async def callback(self, interaction: discord.Interaction):
        chosen_name = self.values[0]
        new_team = self.current_team.copy()
        new_team[self.slot_index] = chosen_name
        await interaction.response.edit_message(
            content=None,
            view=NikkeTeamSlotView(new_team),
            embed=build_team_preview_embed(new_team)
        )

class NikkeAmbiguousSelectView(discord.ui.View):
    def __init__(self, slot_index, current_team, matches):
        super().__init__(timeout=120)
        self.add_item(NikkeAmbiguousSelect(slot_index, current_team, matches))