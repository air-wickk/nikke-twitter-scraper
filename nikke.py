import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import json
import re
from bs4 import BeautifulSoup

# function to validate URLs
def is_valid_url(url):
    return url.startswith("http://") or url.startswith("https://")

PRYDWEN_INDEX = "https://www.prydwen.gg/page-data/nikke/characters/page-data.json"
PRYDWEN_BASE = "https://www.prydwen.gg/page-data/nikke/characters/{slug}/page-data.json"

# cache of characters
PRYDWEN_CHARACTERS = []  # [{name, slug}]

# --- built-in emojis ---
BURST_EMOJIS = {
    "1": "<:Burst1:1412193379865071626>",
    "2": "<:Burst2:1412193388748476478>",
    "3": "<:Burst3:1412193401889361942>",
    "ALL": "<:BurstAll:1412193411032682576>"
}

MANUFACTURER_EMOJIS = {
    "Missilis": "<:Missilis_Icon:1412191377407737885>",
    "Pilgrim": "<:Pilgrim_Icon:1412191367299469424>",
    "Elysion": "<:Elysion_Icon:1412191358977970236>",
    "Tetra": "<:Tetra_Icon:1412191349087797450>"
}

ELEMENT_EMOJIS = {
    "Fire": "<:element_fire:1486852343541797015>",
    "Water": "<:element_water:1486852345961779330>",
    "Wind": "<:element_wind:1486852346838515792>",
    "Iron": "<:element_iron:1486852344602820760>",
    "Electric": "<:element_electric:1486852342300016780>",
}

WEAPON_EMOJIS = {
    "Sniper Rifle": "<:weapon_sniper:1486852355625455719>",
    "Sniper": "<:weapon_sniper:1486852355625455719>",
    "SMG": "<:weapon_smg:1486852353989677189>",
    "Shotgun": "<:weapon_shotgun:1486852352559288320>",
    "Rocket Launcher": "<:weapon_rocket:1486852351016046662>",
    "Minigun": "<:weapon_minigun:1486852349476737165>",
    "Assault Rifle": "<:weapon_ar:1486852347756806386>",
    "Rifle": "<:weapon_ar:1486852347756806386>",
}

CLASS_EMOJIS = {
    "Attacker": "<:class_attacker:1486852338160369664>",
    "Defender": "<:class_defender:1486852339334774826>",
    "Supporter": "<:class_support:1486852341020889178>",
}

RARITY_EMOJIS = {
    "SSR": "<:Ssr:1486859413326397603>",
    "SR": "<:Sr:1486859410654498980>",
}

# base url for images
BASE_IMAGE_URL = "https://prydwen.gg"

# -------------------- HELPERS -------------------- #
def replace_with_emojis(text):
    """Replace weapon, element, and class names with their emoji representations."""
    for weapon, emoji in WEAPON_EMOJIS.items():
        text = text.replace(weapon, emoji)
    for element, emoji in ELEMENT_EMOJIS.items():
        text = text.replace(element, emoji)
    for class_name, emoji in CLASS_EMOJIS.items():
        text = text.replace(class_name, emoji)
    return text

# -------------------- FETCH INDEX -------------------- #
async def fetch_prydwen_index():
    global PRYDWEN_CHARACTERS

    async with aiohttp.ClientSession() as session:
        async with session.get(PRYDWEN_INDEX) as resp:
            if resp.status != 200:
                print("Failed to fetch Prydwen index.")
                return
            data = await resp.json()

    try:
        nodes = data["result"]["data"]["allCharacters"]["nodes"]
        PRYDWEN_CHARACTERS = [
            {"name": n["name"], "slug": n["slug"]}
            for n in nodes
        ]
        print(f"Loaded {len(PRYDWEN_CHARACTERS)} characters from Prydwen.")
    except KeyError as e:
        print(f"Error parsing Prydwen index: {e}")
        PRYDWEN_CHARACTERS = [] 


# -------------------- FETCH CHARACTER -------------------- #
async def fetch_prydwen_character(slug):
    url = PRYDWEN_BASE.format(slug=slug)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    try:
        # character data structure
        character_data = data["result"]["data"].get("currentUnit", {}).get("nodes", [])
        # filter the character data to match the slug
        for character in character_data:
            if character.get("slug") == slug:
                return character
        return None  # return none if no matching character is found
    except Exception as e:
        print(f"Error parsing character data: {e}")
        return None


# -------------------- TEXT PARSER -------------------- #
def parse_rich_text(raw_json):
    if not raw_json:
        return ""

    data = json.loads(raw_json)

    def walk(node):
        if node["nodeType"] == "text":
            return node.get("value", "")

        text = ""
        for child in node.get("content", []):
            text += walk(child)

        if node["nodeType"] == "paragraph":
            return text + "\n"
        elif node["nodeType"].startswith("heading"):
            return f"\n**{text.strip()}**\n"
        elif node["nodeType"] == "list-item":
            return f"• {text.strip()}\n"
        elif node["nodeType"] == "blockquote":
            return f"> {text.strip()}\n"

        return text

    # remove the `■` character from the parsed text, probably meant to be a bullet point
    return "".join(walk(n) for n in data.get("content", [])).replace("■", "").strip()


# -------------------- EMBEDS -------------------- #
async def build_character_embeds(char):
    embeds = []

    name = char["name"]
    element = char["element"]
    burst = str(char["burstType"]).upper()
    manufacturer = char["manufacturer"]

    element_emoji = ELEMENT_EMOJIS.get(element, "")
    burst_emoji = BURST_EMOJIS.get(burst, "")
    manufacturer_emoji = MANUFACTURER_EMOJIS.get(manufacturer, "")

    # --- Main Embed: Overview ---
    # emoji and text labels for class and weapon
    class_emoji = CLASS_EMOJIS.get(char['class'], '')
    weapon_emoji = WEAPON_EMOJIS.get(char['weapon'], '')
    rarity_emoji = RARITY_EMOJIS.get(char['rarity'], '')
    
    # embed color based on rarity
    if char['rarity'] == 'SR':
        embed_color = discord.Color.purple()
    else:
        embed_color = discord.Color.gold()  # default is gold
    
    embed1 = discord.Embed(
        title=f"{name}",
        description=f"{rarity_emoji} | {class_emoji} {char['class']} | {weapon_emoji} {char['weapon']}",
        color=embed_color
    )

    embed1.add_field(name="Burst Type", value=f"{burst_emoji} Burst {burst}", inline=True)
    embed1.add_field(name="Manufacturer", value=f"{manufacturer_emoji} {manufacturer}", inline=True)
    embed1.add_field(name="Element", value=f"{element_emoji} {element}", inline=True)

    # add the character image
    image_url = None
    try:
        image_url = char.get("fullImage", {}).get("localFile", {}).get("childImageSharp", {}).get("gatsbyImageData", {}).get("images", {}).get("fallback", {}).get("src")
    except (AttributeError, TypeError):
        image_url = None
    
    if image_url:
        if image_url.startswith("/"):
            image_url = f"{BASE_IMAGE_URL}{image_url}"
        if is_valid_url(image_url):
            embed1.set_image(url=image_url)

    embeds.append(embed1)

    # --- Skills Embed ---
    embed2 = discord.Embed(
        title=f"{name} — Skills",
        color=discord.Color.orange()
    )

    for skill in char.get("skills", []):
        skill_name = skill.get("name", "Unknown")
        skill_slot = skill.get("slot", "N/A")
        skill_desc = parse_rich_text(skill.get("descriptionLevel10", {}).get("raw", ""))
        embed2.add_field(
            name=f"{skill_name} ({skill_slot})",
            value=skill_desc[:1024] or "No description available.",
            inline=False
        )

    embeds.append(embed2)

    # --- Guide Embeds ---
    slug = char.get("slug", "")
    guide_embeds = await build_guide_embeds(slug)
    embeds.extend(guide_embeds)

    return embeds

async def build_guide_embeds(slug):
    """Build embeds for the guides specific to the character and return them."""
    embeds = []
    
    try:
        # fetch character page HTML
        character_url = f"https://www.prydwen.gg/nikke/characters/{slug}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(character_url) as resp:
                if resp.status != 200:
                    print(f"Failed to fetch guide for {slug}: HTTP {resp.status}")
                    return []
                html = await resp.text()
        
        soup = BeautifulSoup(html, "html.parser")
        
        # --- Skill Investment ---
        skill_sections = soup.find_all("div", class_="nikke-skills")
        if skill_sections:
            # first skills section is skill investment
            skill_section = skill_sections[0]
            
            # get the data row
            data_row = skill_section.find("div", class_="nikke-skills-row data")
            if data_row:
                # extract PVE investment (skips label paragraph)
                pve_col = data_row.select_one(".column.suggestions.pve")
                pve_text = ""
                if pve_col:
                    paragraphs = pve_col.find_all("p")
                    if len(paragraphs) > 1:
                        # second paragraph contains investments
                        pve_text = paragraphs[1].get_text(strip=True)
                
                # extract PVP investments
                pvp_col = data_row.select_one(".column.suggestions.pvp")
                pvp_text = ""
                if pvp_col:
                    paragraphs = pvp_col.find_all("p")
                    if len(paragraphs) > 1:
                        pvp_text = paragraphs[1].get_text(strip=True)
                
                # extract priority
                priority_col = data_row.select_one(".column.priority")
                priority_text = ""
                if priority_col:
                    p = priority_col.find("p", class_="prio")
                    if p:
                        priority_text = p.get_text(strip=True)
                
                if pve_text or pvp_text:
                    embed = discord.Embed(
                        title="Skill Investment",
                        color=discord.Color.gold()
                    )
                    
                    # format skill progression
                    if pve_text:
                        # replace arrows with properly spaced arrows and remove parentheses
                        formatted_pve = pve_text.replace("→", " → ").replace("( → ", " → ").replace(")", "").strip()
                        # clean up multiple spaces
                        formatted_pve = re.sub(r' +', ' ', formatted_pve)
                        # replace with emojis
                        formatted_pve = replace_with_emojis(formatted_pve)
                        embed.add_field(name="PVE Investment", value=formatted_pve, inline=False)
                    if pvp_text:
                        formatted_pvp = pvp_text.replace("→", " → ").replace("( → ", " → ").replace(")", "").strip()
                        formatted_pvp = re.sub(r' +', ' ', formatted_pvp)
                        formatted_pvp = replace_with_emojis(formatted_pvp)
                        embed.add_field(name="PVP Investment", value=formatted_pvp, inline=False)
                    if priority_text:
                        priority_text = replace_with_emojis(priority_text)
                        embed.add_field(name="Priority", value=priority_text, inline=False)
                    
                    embeds.append(embed)
        
        # --- Gear Investment ---
        gear_row = soup.find("div", class_="nikke-skills-row over data")
        if gear_row:
            # extract ideal, get all content except the label
            pve_col = gear_row.select_one(".column.suggestions.pve")
            pve_items = []
            if pve_col:
                paragraphs = pve_col.find_all("p")
                # skip first paragraph (label) and collect all other text
                for p in paragraphs[1:]:
                    text = p.get_text(strip=True)
                    if text:
                        pve_items.append(text)
            
            # extract filler - get all content except the label
            pvp_col = gear_row.select_one(".column.suggestions.pvp")
            pvp_items = []
            if pvp_col:
                paragraphs = pvp_col.find_all("p")
                # skip first paragraph (label) and collect all other text
                for p in paragraphs[1:]:
                    text = p.get_text(strip=True)
                    if text:
                        pvp_items.append(text)
            
            # extract Priority
            priority_col = gear_row.select_one(".column.priority")
            priority_text = ""
            if priority_col:
                p = priority_col.find("p", class_="prio")
                if p:
                    priority_text = p.get_text(strip=True)
            
            if pve_items or pvp_items:
                embed = discord.Embed(
                    title="Gear Investment (Overload)",
                    color=discord.Color.blue()
                )
                
                if pve_items:
                    pve_text = "\n".join(pve_items)
                    pve_text = replace_with_emojis(pve_text)
                    embed.add_field(name="Ideal", value=pve_text, inline=False)
                if pvp_items:
                    pvp_text = "\n".join(pvp_items)
                    pvp_text = replace_with_emojis(pvp_text)
                    embed.add_field(name="Filler", value=pvp_text, inline=False)
                if priority_text:
                    priority_text = replace_with_emojis(priority_text)
                    embed.add_field(name="Priority", value=priority_text, inline=False)
                
                    # check for explanation
                    explanation = gear_row.find_next("div", class_="explanation")
                    if explanation:
                        exp_text = explanation.get_text(strip=True)
                        if exp_text:
                            embed.add_field(name="Note", value=exp_text, inline=False)
                    
                    embeds.append(embed)
        
        # --- Cube Investment ---
        cube_section = soup.find("div", class_="cube-investment")
        if cube_section:
            pve_cubes = []
            pvp_cubes = []
            
            # find the cube table
            cube_table = cube_section.find("div", class_="cube-table")
            if cube_table:
                columns = cube_table.find_all("div", class_="column")
                
                # first column is PVE
                if len(columns) > 0:
                    pve_col = columns[0]
                    cube_items = pve_col.find_all("li")
                    for item in cube_items:
                        # look for the cube name in the <p> tag
                        p_tag = item.find("p")
                        if p_tag:
                            cube_name = p_tag.get_text(strip=True)
                            if cube_name:
                                pve_cubes.append(cube_name)
                
                # second column is PVP
                if len(columns) > 1:
                    pvp_col = columns[1]
                    cube_items = pvp_col.find_all("li")
                    for item in cube_items:
                        p_tag = item.find("p")
                        if p_tag:
                            cube_name = p_tag.get_text(strip=True)
                            if cube_name:
                                pvp_cubes.append(cube_name)
            
            if pve_cubes or pvp_cubes:
                embed = discord.Embed(
                    title="Cube Recommendations",
                    color=discord.Color.purple()
                )
                
                if pve_cubes:
                    pve_text = ", ".join(pve_cubes)
                    pve_text = replace_with_emojis(pve_text)
                    embed.add_field(name="PVE", value=pve_text, inline=False)
                if pvp_cubes:
                    pvp_text = ", ".join(pvp_cubes)
                    pvp_text = replace_with_emojis(pvp_text)
                    embed.add_field(name="PVP", value=pvp_text, inline=False)
                
                # add note if available
                raw_list = cube_section.find("div", class_="raw list")
                if raw_list:
                    note_p = raw_list.find("p")
                    if note_p:
                        note_text = note_p.get_text(strip=True)
                        if note_text:
                            note_text = replace_with_emojis(note_text)
                            embed.add_field(name="Note", value=note_text[:1024], inline=False)
                
                embeds.append(embed)
        
    except Exception as e:
        print(f"Error building guide embeds for {slug}: {e}")
        # return a minimal embed instead of failing if missing something
        embed = discord.Embed(
            title="Character Guide",
            description="Full guide available on Prydwen.gg",
            color=discord.Color.blue(),
            url=f"https://www.prydwen.gg/nikke/characters/{slug}"
        )
        embeds.append(embed)
    
    return embeds

async def fetch_guide_content(url):
    """Fetch and parse guide content from the given URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    content = []

    for tag in soup.find_all(["h1", "h2", "h3", "p", "ul", "ol", "table"]):
        if tag.name in ["h1", "h2", "h3"]:
            content.append(f"**{tag.text.strip()}**")
        elif tag.name == "p":
            content.append(tag.text.strip())
        elif tag.name in ["ul", "ol"]:
            for li in tag.find_all("li"):
                content.append(f"• {li.text.strip()}")
        elif tag.name == "table":
            rows = tag.find_all("tr")
            table_text = []
            for row in rows:
                cols = [col.text.strip() for col in row.find_all(["td", "th"])]
                table_text.append(" | ".join(cols))
            content.append("\n".join(table_text))

    return "\n\n".join(content)

# -------------------- PAGINATION -------------------- #
class CharacterPaginator(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=120)
        self.embeds = embeds
        self.index = 0

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button):
        self.index = (self.index - 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button):
        self.index = (self.index + 1) % len(self.embeds)
        await interaction.response.edit_message(embed=self.embeds[self.index], view=self)


# -------------------- AUTOCOMPLETE -------------------- #
async def character_autocomplete(interaction: discord.Interaction, current: str):
    # matching logic like the one i made in nikketeambuilder.py
    matches = [c for c in PRYDWEN_CHARACTERS if current.lower() in c["name"].lower()]
    startswith_matches = [c for c in PRYDWEN_CHARACTERS if c["name"].lower().startswith(current.lower()) and c not in matches]
    wordstart_matches = [
        c for c in PRYDWEN_CHARACTERS
        if any(word.startswith(current.lower()) for word in c["name"].lower().split()) and c not in matches and c not in startswith_matches
    ]
    all_matches = matches + startswith_matches + wordstart_matches

    return [app_commands.Choice(name=c["name"], value=c["slug"]) for c in all_matches[:25]]


# -------------------- COG -------------------- #
class NikkeCharacterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(fetch_prydwen_index())
        self.refresh_characters.start()

    @tasks.loop(minutes=30)
    async def refresh_characters(self):
        """Refresh the character list every 30 minutes."""
        await fetch_prydwen_index()
        print("Character list refreshed.")

    @refresh_characters.before_loop
    async def before_refresh(self):
        """Wait until the bot is ready before starting the refresh loop."""
        await self.bot.wait_until_ready()

    @app_commands.command(name="nikke", description="View a NIKKE's details")
    @app_commands.autocomplete(name=character_autocomplete)
    async def character(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()

        # fetch character data using slug
        char = await fetch_prydwen_character(name)
        if not char:
            await interaction.followup.send("Character not found.")
            return

        embeds = await build_character_embeds(char)

        await interaction.followup.send(
            embed=embeds[0],
            view=CharacterPaginator(embeds)
        )

async def setup(bot):
    await bot.add_cog(NikkeCharacterCog(bot))