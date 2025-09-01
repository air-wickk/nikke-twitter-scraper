import discord
from discord.ext import commands
from discord import app_commands

NIKKE_LIST = [
    # Elysion Burst 1
    {"name": "Emma", "manufacturer": "Elysion", "burst": 1},
    {"name": "Miranda", "manufacturer": "Elysion", "burst": 1},
    {"name": "Sora", "manufacturer": "Elysion", "burst": 1},
    {"name": "Zwei", "manufacturer": "Elysion", "burst": 1},
    {"name": "Anchor", "manufacturer": "Elysion", "burst": 1},
    {"name": "Neon", "manufacturer": "Elysion", "burst": 1},
    # Elysion Burst 2
    {"name": "Arcana", "manufacturer": "Elysion", "burst": 2},
    {"name": "Diesel", "manufacturer": "Elysion", "burst": 2},
    {"name": "Eunhwa", "manufacturer": "Elysion", "burst": 2},
    {"name": "Marciana", "manufacturer": "Elysion", "burst": 2},
    {"name": "Mast", "manufacturer": "Elysion", "burst": 2},
    {"name": "Poli", "manufacturer": "Elysion", "burst": 2},
    {"name": "Signal", "manufacturer": "Elysion", "burst": 2},
    {"name": "Delta", "manufacturer": "Elysion", "burst": 2},
    # Elysion Burst 3
    {"name": "Brid", "manufacturer": "Elysion", "burst": 3},
    {"name": "D", "manufacturer": "Elysion", "burst": 3},
    {"name": "Guillotine", "manufacturer": "Elysion", "burst": 3},
    {"name": "Helm", "manufacturer": "Elysion", "burst": 3},
    {"name": "K", "manufacturer": "Elysion", "burst": 3},
    {"name": "Maiden", "manufacturer": "Elysion", "burst": 3},
    {"name": "Phantom", "manufacturer": "Elysion", "burst": 3},
    {"name": "Privaty", "manufacturer": "Elysion", "burst": 3},
    {"name": "Quiry", "manufacturer": "Elysion", "burst": 3},
    {"name": "Soline", "manufacturer": "Elysion", "burst": 3},
    {"name": "Vesti", "manufacturer": "Elysion", "burst": 3},
    {"name": "Rapi", "manufacturer": "Elysion", "burst": 3},
    # Missilis Burst 1
    {"name": "Jackal", "manufacturer": "Missilis", "burst": 1},
    {"name": "Liter", "manufacturer": "Missilis", "burst": 1},
    {"name": "Pepper", "manufacturer": "Missilis", "burst": 1},
    {"name": "Tia", "manufacturer": "Missilis", "burst": 1},
    {"name": "Tove", "manufacturer": "Missilis", "burst": 1},
    {"name": "Ether", "manufacturer": "Missilis", "burst": 1},
    {"name": "N102", "manufacturer": "Missilis", "burst": 1},
    # Missilis Burst 2
    {"name": "Admi", "manufacturer": "Missilis", "burst": 2},
    {"name": "Centi", "manufacturer": "Missilis", "burst": 2},
    {"name": "Elegg", "manufacturer": "Missilis", "burst": 2},
    {"name": "Flora", "manufacturer": "Missilis", "burst": 2},
    {"name": "Guilty", "manufacturer": "Missilis", "burst": 2},
    {"name": "Mori", "manufacturer": "Missilis", "burst": 2},
    {"name": "Naga", "manufacturer": "Missilis", "burst": 2},
    {"name": "Quency", "manufacturer": "Missilis", "burst": 2},
    {"name": "Sin", "manufacturer": "Missilis", "burst": 2},
    {"name": "Trina", "manufacturer": "Missilis", "burst": 2},
    {"name": "Yuni", "manufacturer": "Missilis", "burst": 2},
    # Missilis Burst 3
    {"name": "Crow", "manufacturer": "Missilis", "burst": 3},
    {"name": "Drake", "manufacturer": "Missilis", "burst": 3},
    {"name": "Ein", "manufacturer": "Missilis", "burst": 3},
    {"name": "Epinel", "manufacturer": "Missilis", "burst": 3},
    {"name": "Julia", "manufacturer": "Missilis", "burst": 3},
    {"name": "Kilo", "manufacturer": "Missilis", "burst": 3},
    {"name": "Laplace", "manufacturer": "Missilis", "burst": 3},
    {"name": "Mana", "manufacturer": "Missilis", "burst": 3},
    {"name": "Maxwell", "manufacturer": "Missilis", "burst": 3},
    {"name": "Trony", "manufacturer": "Missilis", "burst": 3},
    {"name": "Mihara", "manufacturer": "Missilis", "burst": 3},
    # Tetra Burst 1
    {"name": "Cocoa", "manufacturer": "Tetra", "burst": 1},
    {"name": "Exia", "manufacturer": "Tetra", "burst": 1},
    {"name": "Frima", "manufacturer": "Tetra", "burst": 1},
    {"name": "Ludmilla", "manufacturer": "Tetra", "burst": 1},
    {"name": "Mary", "manufacturer": "Tetra", "burst": 1},
    {"name": "Milk", "manufacturer": "Tetra", "burst": 1},
    {"name": "Moran", "manufacturer": "Tetra", "burst": 1},
    {"name": "Noise", "manufacturer": "Tetra", "burst": 1},
    {"name": "Rei", "manufacturer": "Tetra", "burst": 1},
    {"name": "Rosanna", "manufacturer": "Tetra", "burst": 1},
    {"name": "Rouge", "manufacturer": "Tetra", "burst": 1},
    {"name": "Rumani", "manufacturer": "Tetra", "burst": 1},
    {"name": "Sakura", "manufacturer": "Tetra", "burst": 1},
    {"name": "Soda", "manufacturer": "Tetra", "burst": 1},
    {"name": "Volume", "manufacturer": "Tetra", "burst": 1},
    {"name": "Yan", "manufacturer": "Tetra", "burst": 1},
    {"name": "Mica", "manufacturer": "Tetra", "burst": 1},
    # Tetra Burst 2
    {"name": "Ade", "manufacturer": "Tetra", "burst": 2},
    {"name": "Aria", "manufacturer": "Tetra", "burst": 2},
    {"name": "Bay", "manufacturer": "Tetra", "burst": 2},
    {"name": "Biscuit", "manufacturer": "Tetra", "burst": 2},
    {"name": "Blanc", "manufacturer": "Tetra", "burst": 2},
    {"name": "Clay", "manufacturer": "Tetra", "burst": 2},
    {"name": "Crust", "manufacturer": "Tetra", "burst": 2},
    {"name": "Dolla", "manufacturer": "Tetra", "burst": 2},
    {"name": "Folkwang", "manufacturer": "Tetra", "burst": 2},
    {"name": "Leona", "manufacturer": "Tetra", "burst": 2},
    {"name": "Nero", "manufacturer": "Tetra", "burst": 2},
    {"name": "Novel", "manufacturer": "Tetra", "burst": 2},
    {"name": "Rupee", "manufacturer": "Tetra", "burst": 2},
    {"name": "Viper", "manufacturer": "Tetra", "burst": 2},
    {"name": "Anis", "manufacturer": "Tetra", "burst": 2},
    {"name": "Belorta", "manufacturer": "Tetra", "burst": 2},
    # Tetra Burst 3
    {"name": "Alice", "manufacturer": "Tetra", "burst": 3},
    {"name": "Bready", "manufacturer": "Tetra", "burst": 3},
    {"name": "Noir", "manufacturer": "Tetra", "burst": 3},
    {"name": "Sugar", "manufacturer": "Tetra", "burst": 3},
    {"name": "Yulha", "manufacturer": "Tetra", "burst": 3},
    {"name": "Neve", "manufacturer": "Tetra", "burst": 3},
    # Pilgrim Burst 1
    {"name": "Dorothy", "manufacturer": "Pilgrim", "burst": 1},
    {"name": "Little Mermaid", "manufacturer": "Pilgrim", "burst": 1},
    {"name": "Rapunzel", "manufacturer": "Pilgrim", "burst": 1},
    {"name": "Red Hood", "manufacturer": "Pilgrim", "burst": 1},
    # Pilgrim Burst 2
    {"name": "Crown", "manufacturer": "Pilgrim", "burst": 2},
    {"name": "Grave", "manufacturer": "Pilgrim", "burst": 2},
    {"name": "Nihilister", "manufacturer": "Pilgrim", "burst": 2},
    {"name": "Noah", "manufacturer": "Pilgrim", "burst": 2},
    {"name": "Red Hood", "manufacturer": "Pilgrim", "burst": 2},
    # Pilgrim Burst 3
    {"name": "Cinderella", "manufacturer": "Pilgrim", "burst": 3},
    {"name": "Harran", "manufacturer": "Pilgrim", "burst": 3},
    {"name": "Isabel", "manufacturer": "Pilgrim", "burst": 3},
    {"name": "Modernia", "manufacturer": "Pilgrim", "burst": 3},
    {"name": "Red Hood", "manufacturer": "Pilgrim", "burst": 3},
    {"name": "Scarlet", "manufacturer": "Pilgrim", "burst": 3},
    {"name": "Snow White", "manufacturer": "Pilgrim", "burst": 3},
]

NIKKE_ROLE_INFO = {
    # Elysion
    "Emma": {"color": "#b63734", "role_name": "Emma"},
    "Miranda": {"color": "#707286", "role_name": "Miranda"},
    "Sora": {"color": "#bdc2f7", "role_name": "Sora"},
    "Zwei": {"color": "#9b94a4", "role_name": "Zwei"},
    "Anchor": {"color": "#d6e8fb", "role_name": "Anchor"},
    "Neon": {"color": "#309ce5", "role_name": "Neon"},
    "Arcana": {"color": "#73a1f5", "role_name": "Arcana"},
    "Diesel": {"color": "#5b8dfc", "role_name": "Diesel"},
    "Eunhwa": {"color": "#a092bc", "role_name": "Eunhwa"},
    "Marciana": {"color": "#edbe91", "role_name": "Marciana"},
    "Mast": {"color": "#d54d6c", "role_name": "Mast"},
    "Poli": {"color": "#d3d4e4", "role_name": "Poli"},
    "Signal": {"color": "#baa695", "role_name": "Signal"},
    "Delta": {"color": "#e0bc97", "role_name": "Delta"},
    "Brid": {"color": "#4b74df", "role_name": "Brid"},
    "D": {"color": "#5e7285", "role_name": "D"},
    "Guillotine": {"color": "#7886ba", "role_name": "Guillotine"},
    "Helm": {"color": "#86b0de", "role_name": "Helm"},
    "K": {"color": "#e3a12e", "role_name": "K"},
    "Maiden": {"color": "#b90f2c", "role_name": "Maiden"},
    "Phantom": {"color": "#a493c9", "role_name": "Phantom"},
    "Privaty": {"color": "#a6d5d4", "role_name": "Privaty"},
    "Quiry": {"color": "#fcaeba", "role_name": "Quiry"},
    "Soline": {"color": "#d9c3c4", "role_name": "Soline"},
    "Vesti": {"color": "#e3200d", "role_name": "Vesti"},
    "Rapi": {"color": "#ff535a", "role_name": "Rapi"},
    # Missilis
    "Jackal": {"color": "#e1a6d7", "role_name": "Jackal"},
    "Liter": {"color": "#ecdb6d", "role_name": "Liter"},
    "Pepper": {"color": "#e58da6", "role_name": "Pepper"},
    "Tia": {"color": "#6d7cb6", "role_name": "Tia"},
    "Tove": {"color": "#e06634", "role_name": "Tove"},
    "Ether": {"color": "#af6cae", "role_name": "Ether"},
    "N102": {"color": "#c2bdcc", "role_name": "N102"},
    "Admi": {"color": "#3baba3", "role_name": "Admi"},
    "Centi": {"color": "#fbaf36", "role_name": "Centi"},
    "Elegg": {"color": "#f9ed42", "role_name": "Elegg"},
    "Flora": {"color": "#b085c4", "role_name": "Flora"},
    "Guilty": {"color": "#8cb528", "role_name": "Guilty"},
    "Mori": {"color": "#e7dee8", "role_name": "Mori"},
    "Naga": {"color": "#59588d", "role_name": "Naga"},
    "Quency": {"color": "#f59394", "role_name": "Quency"},
    "Sin": {"color": "#bf64ed", "role_name": "Sin"},
    "Trina": {"color": "#d9efed", "role_name": "Trina"},
    "Yuni": {"color": "#fce1ec", "role_name": "Yuni"},
    "Crow": {"color": "#f7746b", "role_name": "Crow"},
    "Drake": {"color": "#e45b70", "role_name": "Drake"},
    "Ein": {"color": "#a4a0f0", "role_name": "Ein"},
    "Epinel": {"color": "#4ccfd0", "role_name": "Epinel"},
    "Julia": {"color": "#d0d9e2", "role_name": "Julia"},
    "Kilo": {"color": "#a5e8cf", "role_name": "Kilo"},
    "Laplace": {"color": "#ffdc6b", "role_name": "Laplace"},
    "Mana": {"color": "#87c0b0", "role_name": "Mana"},
    "Maxwell": {"color": "#fec45c", "role_name": "Maxwell"},
    "Trony": {"color": "#f49d38", "role_name": "Trony"},
    "Mihara": {"color": "#8464a8", "role_name": "Mihara"},
    # Tetra
    "Cocoa": {"color": "#ec9993", "role_name": "Cocoa"},
    "Exia": {"color": "#7b7c9a", "role_name": "Exia"},
    "Frima": {"color": "#b42952", "role_name": "Frima"},
    "Ludmilla": {"color": "#e2d3e5", "role_name": "Ludmilla"},
    "Mary": {"color": "#8d9dcd", "role_name": "Mary"},
    "Milk": {"color": "#bbbbbb", "role_name": "Milk"},
    "Moran": {"color": "#e1b545", "role_name": "Moran"},
    "Noise": {"color": "#aca4ea", "role_name": "Noise"},
    "Rei": {"color": "#d5c5f0", "role_name": "Rei"},
    "Rosanna": {"color": "#e4dee2", "role_name": "Rosanna"},
    "Rouge": {"color": "#ad1c39", "role_name": "Rouge"},
    "Rumani": {"color": "#3c7bdc", "role_name": "Rumani"},
    "Sakura": {"color": "#7f1a1a", "role_name": "Sakura"},
    "Soda": {"color": "#c7d76a", "role_name": "Soda"},
    "Volume": {"color": "#e1635e", "role_name": "Volume"},
    "Yan": {"color": "#b09e9c", "role_name": "Yan"},
    "Mica": {"color": "#c85945", "role_name": "Mica"},
    "Ade": {"color": "#a9af54", "role_name": "Ade"},
    "Aria": {"color": "#989492", "role_name": "Aria"},
    "Bay": {"color": "#f35868", "role_name": "Bay"},
    "Biscuit": {"color": "#d8a010", "role_name": "Biscuit"},
    "Blanc": {"color": "#f8f3ee", "role_name": "Blanc"},
    "Clay": {"color": "#f8969f", "role_name": "Clay"},
    "Crust": {"color": "#febed3", "role_name": "Crust"},
    "Dolla": {"color": "#9b6073", "role_name": "Dolla"},
    "Folkwang": {"color": "#d7c7df", "role_name": "Folkwang"},
    "Leona": {"color": "#f6b3b2", "role_name": "Leona"},
    "Nero": {"color": "#d56d9a", "role_name": "Nero"},
    "Novel": {"color": "#efb44b", "role_name": "Novel"},
    "Rupee": {"color": "#ffe017", "role_name": "Rupee"},
    "Viper": {"color": "#e7759f", "role_name": "Viper"},
    "Anis": {"color": "#f4ae58", "role_name": "Anis"},
    "Belorta": {"color": "#e1546a", "role_name": "Belorta"},
    "Alice": {"color": "#f294b7", "role_name": "Alice"},
    "Bready": {"color": "#b19589", "role_name": "Bready"},
    "Noir": {"color": "#d69d78", "role_name": "Noir"},
    "Sugar": {"color": "#bf7489", "role_name": "Sugar"},
    "Yulha": {"color": "#ce3f58", "role_name": "Yulha"},
    "Neve": {"color": "#b2adcb", "role_name": "Neve"},
    # Pilgrim
    "Dorothy": {"color": "#e080a7", "role_name": "Dorothy"},
    "Little Mermaid": {"color": "#6cd3c2", "role_name": "Little Mermaid"},
    "Rapunzel": {"color": "#4cadbb", "role_name": "Rapunzel"},
    "Crown": {"color": "#fff8e6", "role_name": "Crown"},
    "Grave": {"color": "#d23b2a", "role_name": "Grave"},
    "Nihilister": {"color": "#e54559", "role_name": "Nihilister"},
    "Noah": {"color": "#ffe5e5", "role_name": "Noah"},
    "Cinderella": {"color": "#e2e2ed", "role_name": "Cinderella"},
    "Harran": {"color": "#bb4e8c", "role_name": "Harran"},
    "Isabel": {"color": "#8760a4", "role_name": "Isabel"},
    "Modernia": {"color": "#a5a4ae", "role_name": "Modernia"},
    "Red Hood": {"color": "#f01e22", "role_name": "Red Hood"},
    "Scarlet": {"color": "#8e71c0", "role_name": "Scarlet"},
    "Snow White": {"color": "#f3f0f5", "role_name": "Snow White"},
}

MANUFACTURERS = sorted(set(n["manufacturer"] for n in NIKKE_LIST))
BURST_NUMBERS = [1, 2, 3]

class ManufacturerSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=m, value=m) for m in MANUFACTURERS]
        super().__init__(placeholder="Choose a manufacturer...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        manufacturer = self.values[0]
        view = BurstSelectView(manufacturer)
        await interaction.response.edit_message(content=f"Selected manufacturer: **{manufacturer}**\nNow choose burst number:", view=view)

class ManufacturerSelectView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ManufacturerSelect())

class BurstSelect(discord.ui.Select):
    def __init__(self, manufacturer):
        options = [discord.SelectOption(label=f"Burst {b}", value=str(b)) for b in BURST_NUMBERS]
        super().__init__(placeholder="Choose burst number...", min_values=1, max_values=1, options=options)
        self.manufacturer = manufacturer

    async def callback(self, interaction: discord.Interaction):
        burst = int(self.values[0])
        view = NikkeSelectView(self.manufacturer, burst)
        await interaction.response.edit_message(content=f"Manufacturer: **{self.manufacturer}**\nBurst: **{burst}**\nNow choose your Nikke:", view=view)

class BurstSelectView(discord.ui.View):
    def __init__(self, manufacturer):
        super().__init__()
        self.add_item(BurstSelect(manufacturer))

class NikkeSelect(discord.ui.Select):
    def __init__(self, manufacturer, burst):
        filtered = [n for n in NIKKE_LIST if n["manufacturer"] == manufacturer and n["burst"] == burst]
        options = [discord.SelectOption(label=n["name"], value=n["name"]) for n in filtered]
        if not options:
            options = [discord.SelectOption(label="No Nikkes found", value="none", default=True)]
        super().__init__(placeholder="Choose your Nikke...", min_values=1, max_values=1, options=options)
        self.manufacturer = manufacturer
        self.burst = burst

    async def callback(self, interaction: discord.Interaction):
        nikke_name = self.values[0]
        if nikke_name == "none":
            await interaction.response.send_message("No Nikkes found for this filter.", ephemeral=True)
            return
        guild = interaction.guild
        member = interaction.user
        role_info = NIKKE_ROLE_INFO.get(nikke_name, {"color": "#FFFFFF", "role_name": nikke_name})
        role_name = role_info["role_name"]
        # Convert hex string to discord.Color
        hex_color = role_info["color"]
        if isinstance(hex_color, str) and hex_color.startswith("#"):
            role_color = discord.Color(int(hex_color[1:], 16))
        else:
            role_color = discord.Color(0xFFFFFF)

        # Remove any existing Nikke character roles before assigning new one
        nikke_role_names = set(NIKKE_ROLE_INFO.keys())
        roles_to_remove = [r for r in member.roles if r.name in nikke_role_names]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)

        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name, color=role_color, mentionable=False)
            try:
                target_role = discord.utils.get(guild.roles, id=1281491070672179201)
                if target_role:
                    await role.move(below=target_role)
            except Exception:
                pass  # Ignore if we can't move it
        await member.add_roles(role)
        await interaction.response.send_message(f"You have been assigned the role: **{role_name}**!", ephemeral=True)

class NikkeSelectView(discord.ui.View):
    def __init__(self, manufacturer, burst):
        super().__init__()
        self.add_item(NikkeSelect(manufacturer, burst))

class NikkeRoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="nikkerole", description="Select your favorite NIKKE role (only visible to you)")
    async def nikke(self, interaction: discord.Interaction):
        view = ManufacturerSelectView()
        await interaction.response.send_message("Select your NIKKE's manufacturer:", view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(NikkeRoleCog(bot))