import discord
from discord import app_commands
from discord.ext import commands

import aiohttp
import io
from PIL import Image


TEAM_SIZE = 5
CHARACTER_API = "https://api.dotgg.gg/nikke/characters"
CHARACTER_IMG_BASE = "https://static.dotgg.gg/nikke/characters/"

# Global character list
NIKKE_LIST = []

async def fetch_nikke():
    """Fetch the list of NIKKE characters from the API and store globally."""
    global NIKKE_LIST
    async with aiohttp.ClientSession() as session:
        async with session.get(CHARACTER_API) as resp:
            if resp.status == 200:
                NIKKE_LIST = await resp.json()

def get_unique_manufacturers():
    """Return a sorted list of unique manufacturers from NIKKE_LIST."""
    manufacturers = set()
    for character in NIKKE_LIST:
        manufacturers.add(character.get("manufacturer", "Unknown"))
    return sorted(manufacturers)

def get_character_by_name(character_name):
    """Return the character dict from NIKKE_LIST by name, or None if not found."""
    for character in NIKKE_LIST:
        if character.get("name") == character_name:
            return character
    return None

BURST_EMOJIS = {
    1: "<:Burst1:1412193379865071626>",
    2: "<:Burst2:1412193388748476478>",
    3: "<:Burst3:1412193401889361942>",
    "ALL": "<:BurstAll:1412193411032682576>"
}
MANUFACTURER_EMOJIS = {
    "Missilis": "<:Missilis_Icon:1412191377407737885>",
    "Pilgrim": "<:Pilgrim_Icon:1412191367299469424>",
    "Elysion": "<:Elysion_Icon:1412191358977970236>",
    "Tetra": "<:Tetra_Icon:1412191349087797450>"
}

def get_burst_emoji(burst):
    if isinstance(burst, str):
        if burst.upper() == "ALL" or burst.lower() == "p":
            return BURST_EMOJIS["ALL"]
    try:
        burst_num = int(burst)
        return BURST_EMOJIS.get(burst_num, "")
    except Exception:
        return ""

def get_manufacturer_emoji(manufacturer):
    return MANUFACTURER_EMOJIS.get(manufacturer, "")

# -------------------- SELECTS -------------------- #

class ManufacturerSelect(discord.ui.Select):

    def __init__(self):
        # Always get the latest manufacturers from NIKKE_LIST
        manufacturers = get_unique_manufacturers() if NIKKE_LIST else []
        manufacturer_options = [
            discord.SelectOption(label=manufacturer)
            for manufacturer in manufacturers
        ]
        # If no options, add a disabled placeholder
        if not manufacturer_options:
            manufacturer_options = [discord.SelectOption(label="No data loaded yet", value="nodata", default=True, description="Try again in a moment", emoji="❌")]
        super().__init__(placeholder="Choose manufacturer...", min_values=1, max_values=1, options=manufacturer_options)

    async def callback(self, interaction: discord.Interaction):
        selected_manufacturer = self.values[0]
        team_select_view = NikkeTeamSelectView(selected_manufacturer)
        await interaction.response.edit_message(
            content=f"Manufacturer selected: **{selected_manufacturer}**\nNow select your team:",
            view=team_select_view
        )

class ManufacturerSelectView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ManufacturerSelect())


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
                burst = char.get("burst", "?")
                manufacturer = char.get("manufacturer", "?")
                burst_emoji = get_burst_emoji(burst)
                manufacturer_emoji = get_manufacturer_emoji(manufacturer)
                padded_name = f"**{char_name}**" + " " * (max_name_len - len(char_name))
                team_lines.append(f"• {burst_emoji} {padded_name} {manufacturer_emoji}")
            else:
                team_lines.append("• —")
        else:
            team_lines.append("• —")
    embed.description = "\n".join(team_lines)
    embed.set_footer(text="Click a slot to change it. Confirm when ready.")
    return embed



# --- Helper functions for team image and embed --- #
async def compose_team_image(character_names):
    from PIL import ImageDraw
    character_image_urls = []
    for name in character_names:
        char = get_character_by_name(name)
        if char:
            image_url = CHARACTER_IMG_BASE + char.get("img", "") + ".webp"
            character_image_urls.append(image_url)
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
        element_gradients = {
            "Fire": [(225, 49, 27, 128), (235, 59, 37, 128)],
            "Wind": [(28, 236, 166, 128), (38, 246, 176, 128)],
            "Iron": [(223, 205, 58, 128), (233, 215, 68, 128)],
            "Electric": [(244, 39, 252, 128), (234, 49, 242, 128)],
            "Water": [(26, 159, 228, 128), (36, 169, 238, 128)]
        }
        bg_size = 432
        bg_images = []
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
                bg = Image.new("RGBA", (bg_size, bg_size), (0,0,0,0))
                grad_draw = ImageDraw.Draw(bg)
                for y in range(bg_size):
                    ratio = y / float(bg_size - 1)
                    r = int(grad[0][0] * (1 - ratio) + grad[1][0] * ratio)
                    g = int(grad[0][1] * (1 - ratio) + grad[1][1] * ratio)
                    b = int(grad[0][2] * (1 - ratio) + grad[1][2] * ratio)
                    a = int(grad[0][3] * (1 - ratio) + grad[1][3] * ratio)
                    grad_draw.line([(0, y), (bg_size - 1, y)], fill=(r, g, b, a), width=1)
                img_resized = img.resize((bg_size, bg_size), Image.LANCZOS)
                bg.paste(img_resized, (0, 0), img_resized)
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
                    emoji_size = int(bg_size * 0.25)  # slightly larger burst icon
                    emoji_img = emoji_img.resize((emoji_size, emoji_size), Image.LANCZOS)
                    bg.paste(emoji_img, (8, 8), emoji_img)
                bg_images.append(bg)
        total_width = sum(img.size[0] for img in bg_images)
        max_height = max(img.size[1] for img in bg_images)
        composite = Image.new("RGBA", (total_width, max_height), (0,0,0,0))
        x_offset = 0
        for img in bg_images:
            composite.paste(img, (x_offset, 0), img)
            x_offset += img.size[0]
        with io.BytesIO() as image_binary:
            composite.save(image_binary, format="PNG")
            image_binary.seek(0)
            return image_binary.read()
    except Exception:
        return None

def build_team_embed(title, character_names, image_bytes=None, image_urls=None):
    embed = discord.Embed(title=title, color=discord.Color.blue())
    character_fields = []
    for slot_index, character_name in enumerate(character_names):
        char = get_character_by_name(character_name)
        if char:
            manufacturer = char.get("manufacturer", "?")
            manufacturer_emoji = get_manufacturer_emoji(manufacturer)
            character_fields.append((slot_index, character_name, manufacturer_emoji))
    team_lines = []
    max_name_len = 0
    for slot_index, character_name, manufacturer_emoji in character_fields:
        if len(character_name) > max_name_len:
            max_name_len = len(character_name)
    for slot_index, character_name, manufacturer_emoji in character_fields:
        padded_name = f"**{character_name}**" + " " * (max_name_len - len(character_name))
        team_lines.append(f"• {manufacturer_emoji} {padded_name}")
    for idx in range(len(character_fields), TEAM_SIZE):
        team_lines.append("• —")
    embed.description = "\n".join(team_lines)
    if image_bytes:
        embed.set_image(url="attachment://team.png")
    elif image_urls and len(image_urls) > 0:
        embed.set_image(url=image_urls[0])
        if len(image_urls) > 1:
            embed.add_field(
                name="Other Team Members",
                value="\n".join([f"[Slot {i+1}]({url})" for i, url in enumerate(image_urls)]),
                inline=False
            )
    return embed

class TeamTitleModal(discord.ui.Modal, title="Team Title"):
    team_title = discord.ui.TextInput(label="Enter a title for your team (optional):", required=False, min_length=0)

    def __init__(self, selected_character_names):
        super().__init__()
        self.selected_character_names = selected_character_names

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_display_name = interaction.user.display_name if hasattr(interaction.user, 'display_name') else interaction.user.name
        title_value = self.team_title.value.strip() if self.team_title.value else ""
        embed_title = title_value if title_value else f"{user_display_name}'s NIKKE Team"
        image_bytes = await compose_team_image(self.selected_character_names)
        if image_bytes:
            file = discord.File(io.BytesIO(image_bytes), filename="team.png")
            embed = build_team_embed(embed_title, self.selected_character_names, image_bytes=image_bytes)
            await interaction.client.get_channel(interaction.channel_id).send(embed=embed, file=file)
        else:
            # fallback: show first character as image, add links for the rest
            image_urls = []
            for name in self.selected_character_names:
                char = get_character_by_name(name)
                if char:
                    image_urls.append(CHARACTER_IMG_BASE + char.get("img", "") + ".webp")
            embed = build_team_embed(embed_title, self.selected_character_names, image_urls=image_urls)
            await interaction.client.get_channel(interaction.channel_id).send(embed=embed)


# -------------------- COG -------------------- #
class NikkeTeamCog(commands.Cog):
    # - - - - - -  -- - -
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(fetch_nikke())

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