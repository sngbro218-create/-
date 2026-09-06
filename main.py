import discord
from discord import app_commands
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

class TicketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = TicketBot()

# --- КОНФИГУРАЦИЯ (Измените эти ID под свой сервер) ---
ROLE_SUPPORT_ID = 1534557356279464027     # ID роли @sᴇʟʟᴇʀ
ROLE_MODERATOR_ID = 876543210987654321   # ID роли @Moderator
# ---------------------------------------------------

# Модальное окно (всплывающее поле) для ввода причины закрытия
class ReasonModal(discord.ui.Modal, title="Причина закрытия тикета"):
    reason_input = discord.ui.TextInput(
        label="Укажите причину",
        style=discord.TextStyle.long,
        placeholder="Например: Вопрос решен / Нарушение правил...",
        required=True,
        max_length=300
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Тикет закрывается по причине: **{self.reason_input.value}**.\nКанал будет удален через 5 секунд...", 
            ephemeral=False
        )
        await asyncio.sleep(5)
        await interaction.channel.delete()

# Панель управления внутри созданного тикета (Кнопки под эмбедом)
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # Кнопка: Закрыть
    @discord.ui.button(label="Отменить заказ", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_close_fast")
    async def close_fast(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Тикет закрыт. Удаление канала через 5 секунд...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    # Кнопка: Закрыть с причиной
    @discord.ui.button(label="Закрыть с причиной", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="btn_close_reason")
    async def close_reason(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ReasonModal())

    # Кнопка: Принять
    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success, emoji="🙋‍♂️", custom_id="btn_claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # --- ИЗМЕНЕНИЕ: Проверка на наличие конкретных ролей ---
        user_role_ids = [role.id for role in interaction.user.roles]
        
        if ROLE_SUPPORT_ID not in user_role_ids and ROLE_MODERATOR_ID not in user_role_ids:
            await interaction.response.send_message(
                "❌ Вы не можете принять этот тикет. Эта кнопка доступна только для администрации!", 
                ephemeral=True
            )
            return
        # -----------------------------------------------------

        await interaction.response.send_message(f"🔒 Модератор {interaction.user.mention} взял этот тикет в работу!", ephemeral=False)
        button.disabled = True
        await interaction.message.edit(view=self)


# Главная кнопка на панели для создания тикета
class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩Сделать заказ", style=discord.ButtonStyle.primary, custom_id="btn_create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        channel_name = f"ticket-{member.name}".lower().replace(" ", "-")
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        
        if existing_channel:
            await interaction.response.send_message(
                f"❌ У вас уже есть открытый тикет: {existing_channel.mention}. Вы можете создать новый только после закрытия старого!", 
                ephemeral=True
            )
            return

        support_role = guild.get_role(ROLE_SUPPORT_ID)
        mod_role = guild.get_role(ROLE_MODERATOR_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }

        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

        ping_text = f"Обращение от {member.mention}\n"
        if support_role: 
            ping_text += f"{support_role.mention} "
        if mod_role: 
            ping_text += f"{mod_role.mention}"

        embed = discord.Embed(
            title="**Заказ оформлен**",
            description=(
                "\n"
                "** <a:267042fire:1535679584002113606> Привет пока ждёшь ответа, напиши пожалуйста. Что именно ты желаешь приобрести?**"
            ),
            color=discord.Color.from_rgb(47, 49, 54)
        )
        embed.set_footer(text="Rune Shop")

        await ticket_channel.send(content=ping_text)
        await ticket_channel.send(embed=embed, view=TicketControlView())
        
        await interaction.response.send_message(f"Ваш тикет успешно создан: {ticket_channel.mention}", ephemeral=True)


@bot.event
async def on_ready():
    bot.add_view(CreateTicketView())
    bot.add_view(TicketControlView())
    print(f"✅ Бот {bot.user.name} бот успешно был включен!")

# Команда настройки панели тикетов в канале
@bot.tree.command(name="setup_tickets", description="Отправить панель поддержки")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="** Создать заказ**",
        description="⁣⁣Чтобы **сделать __заказ__** или предварительно узнать интересующие Вас вопросы **по поводу __покупки__**, жмите на 📩`(кнопка ниже)`",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=CreateTicketView())
    await interaction.response.send_message("Панель создания тикетов установлена!", ephemeral=True)

# Замените токен на новый (сброшенный в целях безопасности на Discord Developer Portal)
bot.run('MTU0NjA3Nzg5NDY4ODg5OTEwMg.G33hgS.3y2bf5TURkR3_zyTeVw5vZbzSly75tLgS8xMZQ')