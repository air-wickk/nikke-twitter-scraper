import discord
from discord.ext import commands
from discord import app_commands

# Example mapping of games to join codes
GAME_CODES = {
    "NIKKE: Goddess of Victory": "26282",
    "Azur Lane": "67120761",
    "Blue Archive": "18479",
    "Umamusume: Pretty Derby": "HONSE",
    "Girls Frontline 2: EXILIUM": "110086",
    "Browndust 2": "GOONGOON"
}

class JoinCodeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(GameSelect())

class GameSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="NIKKE: Goddess of Victory", value="NIKKE: Goddess of Victory", emoji="<:nikkeicon:1397335729683693628>"),
            discord.SelectOption(label="Azur Lane", value="Azur Lane", emoji="<:azurlaneicon:1397335781110190130>"),
            discord.SelectOption(label="Blue Archive", value="Blue Archive", emoji="<:BAicon:1397335739678593084>"),
            discord.SelectOption(label="Umamusume: Pretty Derby", value="Umamusume: Pretty Derby", emoji="<:umaicon:1397335718262735022>"),
            discord.SelectOption(label="Girls Frontline 2: EXILIUM", value="Girls Frontline 2: EXILIUM", emoji="<:gfl2icon:1397335772239233151>"),
            discord.SelectOption(label="Browndust 2", value="Browndust 2", emoji="<:browndust2icon:1397335749480939570>")
        ]
        super().__init__(
            placeholder="Choose a game...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        code = GAME_CODES.get(self.values[0], "No code found for this game.")
        await interaction.response.send_message(
            f"Join code for **{self.values[0]}**: `{code}`",
            ephemeral=True
        )

class JoinCodeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="joincode",
        description="Get the join code for one of our guilds/unions (only visible to you)"
    )
    async def joincode(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Select a game:",
            view=JoinCodeView(),
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(JoinCodeCog(bot))