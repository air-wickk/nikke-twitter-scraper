import discord
from discord.ext import commands
from discord import app_commands

class RoleCreateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="createrole",
        description="Create a new role with a name and color (admin only)"
    )
    @app_commands.describe(
        name="Name of the role",
        color="Hex color code (ex. #ff0000)"
    )
    async def createrole(self, interaction: discord.Interaction, name: str, color: str):
        # Check if user has administrator permission
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You must be an admin to use this command.", ephemeral=True)
            return

        # Validate hex color
        if not color.startswith("#") or len(color) != 7:
            await interaction.response.send_message("Submit a valid hex color code! (ex. #ff0000).", ephemeral=True)
            return

        try:
            discord_color = discord.Color(int(color[1:], 16))
            guild = interaction.guild
            await guild.create_role(name=name, color=discord_color)
            await interaction.response.send_message(f"Role **{name}** created with color `{color}`.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error creating role: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleCreateCog(bot))