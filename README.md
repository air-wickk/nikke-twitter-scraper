# NIKKE Twitter Scraper

This project is a Discord bot that tracks a specified NIKKE Twitter account (NIKKE_en) and sends its posts to a designated Discord channel. The bot uses Discord.py for Discord interactions and Twitter web scraping for fetching tweets, and it also includes a set of NIKKE utilities powered by Prydwen data: character details and builds, banner schedules, team building, and role assignment.

## Features

- Monitors a specified Twitter account (NIKKE_en) for new tweets and posts them to a Discord channel.
- NIKKE utilities: character details and builds, banner schedules, team building, and role assignment.
- Owner-only sync command (`@Bot sync`) to instantly sync slash commands to the server.
- Self-destructing DM error messages for invalid suggestion attempts.
- Dynamic bot status updates.
- Includes a Flask web server for deployment compatibility.
- Configurable via environment variables.

## Settings

- The bot keeps hardcoded defaults from environment variables (channels, tracked account).
- Hosts scrape Prydwen automatically; no manual upkeep is needed for new characters or banners.

## Available Commands

- `/nikke <name>` – view a NIKKE's details & build
- `/banners` – current and upcoming NIKKE banners
- `/buildteam` – build a team of NIKKEs and publish it with a composited banner image
- `/role` – assign your favorite NIKKE as a server role
- `/suggestion <title> <description>` – submit feedback, visible only to you
- `/joincode` – dropdown menu of join codes for various games/guilds, visible only to you
- `@Bot sync` – owner-only, force-syncs slash commands to the server
