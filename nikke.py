import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import asyncio
import requests
import json
import re
from bs4 import BeautifulSoup

# function to validate URLs
def is_valid_url(url):
    return url.startswith("http://") or url.startswith("https://")

PRYDWEN_LIST = "https://www.prydwen.gg/nikke/characters"
PRYDWEN_BASE = "https://www.prydwen.gg/nikke/characters/{slug}"

# Prydwen removed their gatsby page-data.json endpoints (HTTP 410), so
# both fetches now scrape the site's static HTML instead.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# map the icon alt text ("Burst Type 2" / "Burst Type III") to the embed key
BURST_TYPE_MAP = {
    "1": "1", "I": "1",
    "2": "2", "II": "2",
    "3": "3", "III": "3",
    "ALL": "ALL",
}

KNOWN_CLASSES = {"Attacker", "Defender", "Supporter"}

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

CUBE_EMOJIS = {
    "Vigor": "<:c_vigor:1561970866252808303>",
    "Tempering": "<:c_tempering:1561970865254563940>",
    "Bastion": "<:c_bastion:1561970864185016330>",
    "Resilience": "<:c_resilience:1561970862914011158>",
    "Endurance": "<:c_endurance:1561970861781684344>",
    "Adjutant": "<:c_adjutant:1561970860674261072>",
    "Quantum": "<:c_quantum:1561970859613098014>",
    "Onslaught": "<:c_onslaught:1561970858212200449>",
    "Destruction": "<:c_destruction:1561970856694128661>",
    "Wingman": "<:c_wingman:1561970855737692250>",
    "Healing": "<:c_healing:1561970854504562821>",
    "Assault": "<:c_assault:1561970852730249226>",
    "Relic Assist": "<:c_relicassist:1561970850859585576>",
    "Rupture": "<:c_rupture:1561970849576128575>",
    "Piercing": "<:c_piercing:1561970848305520660>",
    "Diffusion": "<:c_diffusion:1561970847151956048>",
}

def replace_with_cube_emojis(text):
    """Prefix each cube name occurrence with its custom emoji."""
    for cube, emoji in CUBE_EMOJIS.items():
        # handle both "Vigor Cube" and bare "Vigor"
        text = text.replace(f"{cube} Cube", f"{emoji} {cube} Cube")
        text = text.replace(f"{cube},", f"{emoji} {cube},")
    return text

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

# aiohttp is TLS-fingerprinted and blocked by Cloudflare (HTTP 403), so all
# Prydwen requests go through requests in a background thread instead.
def _get_html(url, timeout=30):
    response = requests.get(url, headers=BROWSER_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


# -------------------- FETCH INDEX -------------------- #
async def fetch_prydwen_index():
    global PRYDWEN_CHARACTERS

    try:
        html = await asyncio.to_thread(_get_html, PRYDWEN_LIST)
    except Exception as e:
        print(f"Failed to fetch Prydwen index: {e}")
        return

    soup = BeautifulSoup(html, "html.parser")

    characters = []
    seen_slugs = set()

    for link in soup.select('a[href^="/nikke/characters/"]'):
        # only anchor tiles containing a proper character card avatar
        card = link.select_one("div.avatar.nikke-card")
        if not card:
            continue

        slug = link["href"].rsplit("/", 1)[-1]
        if not slug or slug in seen_slugs:
            continue

        img = card.find("img")
        name = (img.get("alt") or "").strip() if img else slug
        if not name:
            continue

        # card details shown on the listing tiles come free with the index:
        # rarity class, burst type + element floating icons, card artwork
        rarity = ""
        for cls in card.get("class", []):
            if cls.startswith("rarity-"):
                rarity = cls.replace("rarity-", "")

        burst = ""
        burst_img = card.select_one("span.floating-element:not(.element) img")
        if burst_img:
            alt = (burst_img.get("alt") or "")
            match = re.search(r"(?i)burst type ([\w]+)", alt)
            if match:
                burst = BURST_TYPE_MAP.get(match.group(1), match.group(1))
            elif re.search(r"(?i)type all", alt):
                burst = "ALL"

        element = ""
        element_img = card.select_one("span.floating-element.element img")
        if element_img:
            alt = (element_img.get("alt") or "")
            match = re.search(r"(?i)([a-z]+) element", alt)
            if match:
                element = match.group(1).capitalize()

        entry = {"name": name, "slug": slug, "rarity": rarity, "element": element, "burst": burst}
        card_art = (img.get("src") or "").strip() if img else ""
        if card_art:
            entry["cardImage"] = card_art

        seen_slugs.add(slug)
        characters.append(entry)

    if not characters:
        print("Error parsing Prydwen index: no characters found.")
        return

    PRYDWEN_CHARACTERS = characters
    print(f"Loaded {len(PRYDWEN_CHARACTERS)} characters from Prydwen.")


# -------------------- FETCH CHARACTER -------------------- #
async def fetch_prydwen_character(slug):
    url = PRYDWEN_BASE.format(slug=slug)

    try:
        html = await asyncio.to_thread(_get_html, url)
    except Exception as e:
        print(f"Failed to fetch Prydwen character {slug}: {e}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    # name (e.g. <strong>Rupee</strong> inside the header)
    name_el = soup.select_one("div.left-info h1 strong")
    name = name_el.get_text(strip=True) if name_el else slug

    # rarity (e.g. <strong class="rarity-SSR">)
    rarity_el = soup.select_one("div.left-info h1 strong[class*='rarity-']")
    rarity = ""
    if rarity_el:
        for cls in rarity_el.get("class", []):
            if cls.startswith("rarity-"):
                rarity = cls.replace("rarity-", "")

    # intro paragraph lists burst / class / weapon / element / faction
    # with an <img class="intro-icon"> right after each value
    info = soup.select_one("div.combined h2")

    char = {
        "name": name,
        "slug": slug,
        "rarity": rarity,
        "element": "",
        "burstType": "",
        "manufacturer": "",
        "class": "",
        "weapon": "",
        "hasTreasure": "treasure" in name.lower(),
        "specialities": [],
        "ratings": [],
        "intro": "",
    }

    if info:
        elements = info.find_all(["strong", "img"])
        previous = ""
        for el in elements:
            if el.name == "strong":
                # skip name and rarity strongs
                if el.get("class") and any(c.startswith("rarity-") for c in el.get("class", [])):
                    continue

                text = el.get_text(strip=True)
                # class values appear without an icon right after them
                if text in KNOWN_CLASSES:
                    char["class"] = text

                previous = text
                continue

            alt = (el.get("alt") or "").lower()

            if "burst type" in alt:
                match = re.search(r"burst type ([\w]+)", alt)
                if match:
                    char["burstType"] = BURST_TYPE_MAP.get(match.group(1), match.group(1))
                    char["burst"] = previous
            elif "type all" in alt:
                # e.g. icon alt "Type All" (burst I/II/III-capable characters)
                char["burstType"] = "ALL"
            elif "weapon icon" in alt:
                char["weapon"] = previous
            elif "element icon" in alt:
                char["element"] = previous
            elif "manufacturer icon" in alt or "faction icon" in alt:
                char["manufacturer"] = previous
            elif previous and previous in KNOWN_CLASSES:
                char["class"] = previous

            previous = ""

    # specialties ("Specialties" list on the profile tab)
    spec_list = soup.select_one("div.specialities-list")
    char["specialities"] = [
        el.get_text(strip=True)
        for el in spec_list.select(".employee-role")
        if el.get_text(strip=True)
    ] if spec_list else []

    # review ratings ("Story D | Bossing D | PVP E" style)
    ratings_container = soup.select_one("div.detailed-ratings.nikke")
    char["ratings"] = []
    if ratings_container:
        for box in ratings_container.select("div.rating-box-container"):
            grade_el = box.select_one("div.rating-box")
            mode_el = box.find("p")
            if grade_el and mode_el:
                grade = grade_el.get_text(strip=True)
                mode = mode_el.get_text(strip=True)
                if grade and mode:
                    char["ratings"].append({"mode": mode, "grade": grade})

    # flavor blurb on the profile tab (not every character has one)
    intro_el = soup.select_one("div.char-intro")
    char["intro"] = intro_el.get_text(" ", strip=True) if intro_el else ""

    # character portrait (exclude card/full variants)
    thumbnail_url = None
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        if src.startswith("https://cdn.prydwen.gg/images/nikke/characters/"):
            if "/{slug}.webp".format(slug=slug) in src:
                thumbnail_url = src
                break

    if not thumbnail_url:
        # reasonable fallback based on the cdn pattern
        thumbnail_url = (
            f"https://cdn.prydwen.gg/images/nikke/characters/{slug}.webp"
        )

    # shape the thumbnail so build_character_embeds can keep consuming it
    char["smallImage"] = {
        "localFile": {
            "childImageSharp": {
                "gatsbyImageData": {
                    "images": {"fallback": {"src": thumbnail_url}}
                }
            }
        }
    }

    return char


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
    
    # embed color based on rarity / treasure variant
    if char["hasTreasure"]:
        embed_color = discord.Color(0x2F979F)  # teal for treasure variants
    elif char['rarity'] == 'SR':
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
    # add the character thumbnail
    thumbnail_url = None
    try:
        thumbnail_url = char.get("smallImage", {}).get("localFile", {}).get("childImageSharp", {}).get("gatsbyImageData", {}).get("images", {}).get("fallback", {}).get("src")
    except (AttributeError, TypeError):
        thumbnail_url = None
    
    if thumbnail_url:
        if thumbnail_url.startswith("/"):
            thumbnail_url = f"{BASE_IMAGE_URL}{thumbnail_url}"
        if is_valid_url(thumbnail_url):
            embed1.set_thumbnail(url=thumbnail_url)

    embeds.append(embed1)

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
        html = await asyncio.to_thread(_get_html, character_url)
        
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
            # extract Ideal (column labeled "Ideal", class "essential")
            ideal_col = gear_row.select_one(".column.suggestions.essential")
            ideal_items = []
            if ideal_col:
                for p in ideal_col.find_all("p"):
                    if "on-mobile" in (p.get("class") or []):
                        continue
                    text = p.get_text(strip=True)
                    if text:
                        ideal_items.append(text)

            # extract Filler (column labeled "Filler", class "ideal")
            filler_col = gear_row.select_one(".column.suggestions.ideal")
            filler_items = []
            if filler_col:
                for p in filler_col.find_all("p"):
                    if "on-mobile" in (p.get("class") or []):
                        continue
                    text = p.get_text(strip=True)
                    if text:
                        filler_items.append(text)

            # extract Priority
            priority_col = gear_row.select_one(".column.priority")
            priority_text = ""
            if priority_col:
                p = priority_col.find("p", class_="prio")
                if p:
                    priority_text = p.get_text(strip=True)

            if ideal_items or filler_items or priority_text:
                embed = discord.Embed(
                    title="Overload Gear Investment",
                    color=discord.Color.blue()
                )

                if ideal_items:
                    ideal_text = replace_with_emojis("\n".join(ideal_items))
                    embed.add_field(name="Ideal", value=ideal_text, inline=False)
                if filler_items:
                    filler_text = replace_with_emojis("\n".join(filler_items))
                    embed.add_field(name="Filler", value=filler_text, inline=False)
                if priority_text:
                    priority_text = replace_with_emojis(priority_text)
                    embed.add_field(name="Priority", value=priority_text, inline=False)

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
                    pve_text = replace_with_emojis(replace_with_cube_emojis(pve_text))
                    embed.add_field(name="PVE", value=pve_text, inline=False)
                if pvp_cubes:
                    pvp_text = ", ".join(pvp_cubes)
                    pvp_text = replace_with_emojis(replace_with_cube_emojis(pvp_text))
                    embed.add_field(name="PVP", value=pvp_text, inline=False)
                
                # add note if available
                raw_list = cube_section.find("div", class_="raw list")
                if raw_list:
                    note_p = raw_list.find("p")
                    if note_p:
                        note_text = note_p.get_text(strip=True)
                        if note_text:
                            note_text = replace_with_emojis(replace_with_cube_emojis(note_text))
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
    try:
        html = await asyncio.to_thread(_get_html, url)
    except Exception as e:
        print(f"Failed to fetch guide content {url}: {e}")
        return None

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

# -------------------- TABBED VIEW -------------------- #
TREASURE_COLOR = 0x2F979F

# short button labels for the tabs, by embed title
TAB_LABELS = [
    ("Skill Investment", "Skill Investment"),
    ("Overload Gear Investment", "Overload"),
    ("Cube Recommendations", "Cubes"),
]

def default_tab_label(index, title):
    if index == 0:
        return "Overview"
    for prefix, label in TAB_LABELS:
        if prefix in title:
            return label
    return title[:24] if title else f"Page {index + 1}"


def _accent_color(char):
    if char.get("hasTreasure"):
        return discord.Color(TREASURE_COLOR)
    if char.get("rarity") == "SR":
        return discord.Color.purple()
    return discord.Color.gold()


def _splash_url(char):
    try:
        return (
            char["smallImage"]["localFile"]["childImageSharp"]["gatsbyImageData"]
            ["images"]["fallback"]["src"]
        )
    except (KeyError, TypeError):
        return None


def _stats_line(char):
    element = char.get("element", "")
    burst = char.get("burstType", "")
    weapon = char.get("weapon", "")
    rarity = char.get("rarity", "")

    element_emoji = ELEMENT_EMOJIS.get(element, "")
    burst_emoji = BURST_EMOJIS.get(str(burst).upper(), "")
    weapon_emoji = WEAPON_EMOJIS.get(weapon, "")
    rarity_emoji = RARITY_EMOJIS.get(rarity, "")

    parts = []
    if rarity_emoji:
        parts.append(rarity_emoji)
    if weapon_emoji:
        parts.append(f"{weapon_emoji} {weapon}")
    if element_emoji:
        parts.append(f"{element_emoji} {element}")
    if burst_emoji:
        parts.append(f"{burst_emoji} Burst {burst}")

    joined = " | ".join(p for p in parts if p)
    return f"-# {joined}" if joined else ""


def _ratings_line(char):
    ratings = char.get("ratings") or []
    return " | ".join(
        f"{r['mode']} **{r['grade']}**"
        for r in ratings
        if r.get("mode") and r.get("grade")
    )


def _guide_page_text(embed):
    # turn an existing guide embed's fields into markdown
    lines = []
    for field in embed.fields:
        value = field.value or ""
        lines.append(f"**{field.name}**")
        lines.append(value)
        lines.append("")
    return "\n".join(lines).strip()


class TabbedCharacterView(ui.LayoutView):
    def __init__(self, char, embeds, page=0):
        super().__init__(timeout=300)
        self.char = char
        self.embeds = embeds
        self.page = max(0, min(page, len(embeds) - 1))
        self._build()

    def _page_text(self, index):
        # overview: specialties profile tab + class/faction not in the header
        if index == 0:
            char = self.char
            lines = []

            labels = [
                (CLASS_EMOJIS.get(char.get("class", ""), ""), "Class", char.get("class", "")),
                (MANUFACTURER_EMOJIS.get(char.get("manufacturer", ""), ""), "Faction", char.get("manufacturer", "")),
            ]
            joined = " | ".join(
                f"**{label}:** {emoji} {value}"
                for emoji, label, value in labels
                if value
            )
            if joined:
                lines.append(joined)
                lines.append("")

            specialities = char.get("specialities") or []
            if specialities:
                lines.append("**Specialties**")
                lines.append(" • ".join(specialities))

            if not lines:
                lines.append("Overview content coming soon.")

            return "\n".join(lines).strip()

        return _guide_page_text(self.embeds[index])

    def _header_text(self):
        lines = [
            f"## {self._name()}",
            _stats_line(self.char),
        ]

        ratings = _ratings_line(self.char)
        if ratings:
            lines.append(ratings)

        return "\n".join(lines)

    def _label(self, index):
        title = self.embeds[index].title or ""
        return default_tab_label(index, title)

    def _name(self):
        return self.char.get("name", "?")

    def _build(self):
        self.clear_items()

        color = _accent_color(self.char)

        container = ui.Container(accent_color=color)

        # header section: name + stats, character splash as thumbnail
        splash = _splash_url(self.char)
        header = ui.TextDisplay(self._header_text())
        if splash:
            container.add_item(ui.Section(header, accessory=ui.Thumbnail(media=splash)))
        else:
            container.add_item(header)

        container.add_item(ui.Separator())

        # active tab content
        container.add_item(ui.TextDisplay(self._page_text(self.page)))

        # tab buttons
        if len(self.embeds) > 1:
            row = ui.ActionRow()
            for i in range(len(self.embeds)):
                button = ui.Button(
                    label=self._label(i),
                    style=(
                        discord.ButtonStyle.primary if i == self.page else discord.ButtonStyle.secondary
                    ),
                    disabled=(i == self.page),
                )
                button.callback = self._make_tab_callback(i)
                row.add_item(button)
            container.add_item(row)

        self.add_item(container)

    def _make_tab_callback(self, index):
        async def callback(interaction: discord.Interaction):
            self.page = index
            self._build()
            await interaction.response.edit_message(view=self)

        return callback


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

    @app_commands.command(name="nikke", description="View a NIKKE's details & build")
    @app_commands.autocomplete(name=character_autocomplete)
    async def character(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()

        # fetch character data using slug
        char = await fetch_prydwen_character(name)
        if not char:
            await interaction.followup.send("Character not found.")
            return

        embeds = await build_character_embeds(char)

        await interaction.followup.send(view=TabbedCharacterView(char, embeds))

async def setup(bot):
    await bot.add_cog(NikkeCharacterCog(bot))