import asyncio
import os
import tempfile
from pathlib import Path

import discord
from discord import app_commands

ROOT = Path(__file__).resolve().parent
DEOB = ROOT / "deobf" / "deob.py"
MAX_UPLOAD = 8 * 1024 * 1024
TIMEOUT = 150

# No privileged intents are needed: this bot uses slash commands/interactions.
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


def safe_name(name: str) -> str:
    name = Path(name or "script.luau").name
    if not name.lower().endswith((".lua", ".luau", ".txt")):
        name += ".luau"
    return name


async def run_deobfuscator(input_path: Path, output_path: Path, force: str | None = None):
    cmd = [
        "python3", str(DEOB), str(input_path),
        "-o", str(output_path),
        "--timeout", str(TIMEOUT),
    ]
    if force:
        cmd += ["--obfuscator", force]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(ROOT / "deobf"),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT + 20)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError("Deobfuscation timed out.")

    log = (stderr + stdout).decode("utf-8", "replace")
    if proc.returncode != 0 or not output_path.exists():
        raise RuntimeError(log[-3500:] or "Deobfuscator failed without an error message.")
    return log


async def process(interaction: discord.Interaction, attachment: discord.Attachment, force: str | None = None):
    if attachment.size > MAX_UPLOAD:
        await interaction.followup.send(f"File is too large. Maximum is {MAX_UPLOAD // (1024 * 1024)} MB.", ephemeral=True)
        return

    with tempfile.TemporaryDirectory(prefix="discord_deobf_") as td:
        td = Path(td)
        input_path = td / safe_name(attachment.filename)
        output_path = td / safe_name(attachment.filename)

        try:
            data = await attachment.read()
            input_path.write_bytes(data)
            await interaction.edit_original_response(content="⏳ Deobfuscating... this can take a while for Luraph VM scripts.")
            log = await run_deobfuscator(input_path, output_path, force)
        except Exception as exc:
            msg = str(exc)
            if len(msg) > 3500:
                msg = msg[-3500:]
            await interaction.followup.send(f"❌ Deobfuscation failed:\n```text\n{msg}\n```", ephemeral=True)
            return

        if output_path.stat().st_size > 24 * 1024 * 1024:
            await interaction.followup.send("❌ The output is larger than Discord's upload limit.", ephemeral=True)
            return

        detected = ""
        for line in log.splitlines():
            if "[+] result:" in line or "[*] obfuscator:" in line:
                detected = line.strip()
        await interaction.followup.send(
            content=f"✅ Done. {detected}" if detected else "✅ Done.",
            file=discord.File(output_path, filename=output_path.name),
        )


@tree.command(name="deobf", description="Deobfuscate a Roblox Luau/Lua file (auto-detect).")
@app_commands.describe(file="The .lua/.luau file to deobfuscate")
async def deobf(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer()
    await process(interaction, file)


@tree.command(name="luraph15", description="Run the Luraph v15 devirtualizer directly.")
@app_commands.describe(file="The Luraph script to devirtualize")
async def luraph15(interaction: discord.Interaction, file: discord.Attachment):
    await interaction.response.defer()
    await process(interaction, file, "luraph_v15")


@bot.event
async def on_ready():
    try:
        await tree.sync()
    except Exception as exc:
        print(f"Slash-command sync failed: {exc}")
    print(f"Logged in as {bot.user} ({bot.user.id})")


token = os.getenv("DISCORD_TOKEN")
if not token:
    raise RuntimeError("DISCORD_TOKEN environment variable is not set")

bot.run(token)
