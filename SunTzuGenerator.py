import queue

# Importing necessary modules from the Telegram package
from telegram           import Update, InputFile, Sticker, StickerSet, InputSticker
from telegram.ext       import Application, CommandHandler, MessageHandler, filters
from telegram.error     import TimedOut, TelegramError
from telegram.constants import StickerFormat

import re
import textwrap
from io  import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Telegram Bot token obtained from BotFather
# Thanks ChatGPT for making me understand this step
TOKEN = '----------:-----------------------------------'

# Function to handle the /start command
async def start(update, context):
    await update.message.reply_text('Sun Tzu is quoting for you!')

# Function to create an image with the provided quote, author, and book
def create_image(quote, author, book):
    lines = textwrap.wrap(quote, width=32)
    
    # Adding author and book information to the lines
    if book is None:
        lines += [f'cit. {author}']
    else:
        lines += [f'cit. {author}, {book}']

    # Loading font
    font = ImageFont.truetype('Arial.ttf', 20)

    ascent, descent = font.getmetrics()
    heights = []
    widths = []

    for line in lines:
        (width, baseline), (offset_x, offset_y) = font.font.getsize(line)
        height = ascent + descent
        widths += [width]
        heights += [height]
   
    max_width = max(widths)

    # Check if the image exceeds Telegram's maximum supported size
    if sum(heights) > 512 or max_width > 512:
        return None

    if max_width < 512:
        max_width = 512

    # Creating the image
    image = Image.new('RGBA', (max_width, sum(heights)), color=(0, 0, 0, 0))
    draw  = ImageDraw.Draw(image)

    coord_x = 0
    coord_y = 0
    for line in lines:
        draw.text(xy=(coord_x, coord_y), text=line, font=font, fill=(200, 200, 200, 255))
        height = ascent + descent
        coord_y += height

    return image

# Function to handle replies with quotes for sticker creation
async def reply(update, context):
    text = update.message.text

    # Using regular expression to extract quote, author, and book from the message
    m = re.search(r'^.*"(.*)"\s*cit\.\s*(.+\s*Tzu)\s*(,.+)?.*$', text)

    try:
        if m:
            user_id = update.message.from_user.id

            # Checking if the user is an admin
            try:
                admins = await context.bot.get_chat_administrators(update.message.chat_id)
            except:
                # In private chats there are no administrators so the
                # previous expression will raise an exception of the
                # telegram.error.BadRequest type
                admins = None

            if admins is not None and not any(admin.user.id == user_id for admin in admins):
               await update.message.reply_text('You have to be an admin to add a new sticker')
               return

            await update.message.reply_text('Building your sticker...')
            quote  = m.group(1).strip() # Cause whitespace characters to be
            author = m.group(2).strip() # ignored at the ends of the string

            # The book can be omitted
            if m.group(3) is None:
                book = None
            else:
                # Remove the comma
                book = m.group(3).strip()[1:]

            # Creating the image for the sticker
            image = create_image(f'"{quote}"', author, book)

            if image is None:
                await update.message.reply_text('I cannot build your sticker, its size is greater than max supported by Telegram (512x512px)')
                return

            filename = f'{author}_{book}_stiker.png'
            image.save(filename, 'PNG')

            sticker_image = Image.open(filename)
            sticker_file  = BytesIO()
            sticker_image.save(sticker_file, format='PNG')
            sticker_file.seek(0)

            # Checking if sticker pack exists
            pack_long_name  = 'Quotes_by_' + context.bot.username
            pack_short_name = 'quotes_by_' + context.bot.username
            pack_exists     = False

            try:
                sticker_set = await context.bot.get_sticker_set(pack_short_name)
                pack_exists = True
            except TelegramError as e:
                pack_exists = False
                print(f'Telegram error: {e}')

            # Adding sticker to the pack
            # - The dragon emoji is used to find quikly the package
            # - If the package does not exist, it creates a new one
            sticker = InputSticker(sticker=open(filename, 'rb'), emoji_list=('🐲'))
            if pack_exists is True:
                await context.bot.add_sticker_to_set(user_id=user_id, name=pack_short_name, sticker=sticker)
            else:
                await context.bot.create_new_sticker_set(user_id=user_id, name=pack_short_name, title=pack_long_name, stickers=[sticker], sticker_format='static')
            await update.message.reply_text('Sticker added')
            await context.bot.send_sticker(update.message.chat_id, sticker_file)
    except TimedOut:
        print('Exception has been raised: TimeOut')

# Main function to initialize and run the bot
def main():
    app = Application.builder().token(TOKEN).build()

    # Add handlers to commands/messages
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

    print('bot listening...')
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# Entry point of the script

# I'm not sure if I like this style or not...
# Python's entry main styles suck!

if __name__ == '__main__':
    main()
