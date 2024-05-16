import telebot
from loguru import logger
import os
import time
import json
from pathlib import Path
from telebot.types import InputFile
from img_proc import Img
import requests
from bot_utils import upload_image_to_s3, download_image_from_s3, parse_result
import threading

images_bucket = os.environ['BUCKET_NAME']
images_prefix = os.environ['BUCKET_PREFIX']

class ExceptionHandler(telebot.ExceptionHandler):
    """
    An implementation of the telegram bot exception handler class
    """
    _lock = threading.Lock()

    def __init__(self, bot):
        self.bot = bot
        self._chat_id = None

    @property
    def chat_id(self):
        with self._lock:
            return self._chat_id

    @chat_id.setter
    def chat_id(self, value):
        with self._lock:
            self._chat_id = value

    def handle(self, exception):
        with self._lock:
            if self._chat_id is not None:
                logger.exception(f"Exception in chat {self.chat_id}: {exception}")
                return self.bot.send_message(self.chat_id, f"An error has occurred:\n{exception}")
            else:
                logger.exception("Exception occurred without an active chat context.")
        return False

class BotFactory:
    """
    BotFactory class as its name implies, this class makes use of an OO pattern called Factory,
    to generate a bot depending on the incoming message and its parameters.
    """
    _lock = threading.Lock()
    _curr_bot = None

    def __init__(self, token, telegram_chat_url):
        self.tgbot = telebot.TeleBot(token)

        # Remove any existing webhooks configured in Telegram servers
        self.tgbot.remove_webhook()
        time.sleep(0.5)

        # Set the webhook URL
        self.tgbot.set_webhook(url=f'{telegram_chat_url}/{token}/', timeout=90)

        # Initiate the exception handler and pass it the bot object to handle messages
        self.tgbot.exception_handler = ExceptionHandler(self.tgbot)

        logger.info(f'Telegram Bot information\n\n{self.tgbot.get_me()}')

    @property
    def curr_bot(self):
        with self._lock:
            return self._curr_bot

    @curr_bot.setter
    def curr_bot(self, value):
        with self._lock:
            self._curr_bot = value

    def is_current_msg_photo(self, msg):
        """
        Check if it's an image
        """
        return "photo" in msg

    def is_a_reply(self, msg):
        """
        Check if it's a reply
        """
        return "reply_to_message" in msg

    def is_prediction(self, msg):
        """
        Check if it's a prediction
        """
        return msg.get("caption", "").strip().lower() == "predict"

    def get_bot(self, msg = ""):
        """
        Get the respective bot based on the incoming message and return the bot instance itself
        """
        logger.info('Getting a bot...')
        # Check for a reply
        if self.is_a_reply(msg) and not isinstance(BotFactory.curr_bot, QuoteBot):
            BotFactory.curr_bot = QuoteBot(self.tgbot)
        # Check for an image
        elif self.is_current_msg_photo(msg):
            if self.is_prediction(msg) and not isinstance(BotFactory.curr_bot, ObjectDetectionBot):
                # For ObjectDetectionBot with "predict" caption
                BotFactory.curr_bot = ObjectDetectionBot(self.tgbot)
            elif not isinstance(BotFactory.curr_bot, ImageProcessingBot):
                # For general image processing
                BotFactory.curr_bot = ImageProcessingBot(self.tgbot)
        # Fallback basic Bot
        else:
            BotFactory.curr_bot = Bot(self.tgbot)

        return BotFactory.curr_bot

class Bot:
    """
    Bot class to handle the basic 'echo' bot
    """
    def __init__(self, tgbot):
        self._tgbot = tgbot

    def __getattr__(self, name):
        """
        This method converts this class to a wrapper class, meaning any call to an attribute of a method that are not in the immediate class will be 'referred' to the class being wrapped. In this case the Bot class wraps the telebot.TeleBot class.
        """
        return getattr(self._tgbot, name)

    def handle_exception(self, exception, chat_id):
        """
        This is a wrapper function which makes use of the exception handling mechanism
        By using it this way it maintains context hence when the ExceptionHandler sends a message it's as if it was sent
        by the bot itself.
        """
        self.exception_handler.chat_id = chat_id
        self.exception_handler.handle(exception)

    def send_welcome(self, chat_id):
        """
        This method is used to both greet and give instructions to the user.
        """
        text = '''
Welcome to the Image Processing Bot!

Upload an image and type in the caption the action you'd like to do.

*NOTE:* You need to type in the words or numbers. For *Concat* you need to upload more than one image

These are the available actions:
1. *Blue* - blurs the image.
    a. You may specify noise level by inputting a floating point number

    *example usage: blur 10*
2. *Contour* - applies a contour effect to the image

    *example usage: contour*
3. *Rotate* - rotates the image
    a. You may also input either *clockwise* or *anti-clockwise* (default *clockwise*)
    b. You may also input the degrees to rotate (default *90*)
        i. *90*
        ii. *180*
        iii. *270*
    c. You may enter either of the above or both

    *example usage: anti-clockwise 180*
4. *Salt and pepper* - randomly sprinkle white and black pixels on the image
    a. You may specify noise level by inputting a floating point number representing the proportion of the image pixels to be affected by noise.

    *example usage: salt and pepper 0.1*
5. *Concat* - concatenates two or more images
    a. You may also send the direction of either *horizontal* or *vertical* (default *horizontal*)
    b. You may also specify the sides to be concatenated based on the direction (default *right-to-left*)
        i. horizontal: *right-to-left*, *left-to-right*
        ii. vertical: *top-to-bottom*, *bottom-to-top*

    *example usage: concat vertical top-to-bottom*
6. *Segment* - represented in a more simplified manner, and so we can then identify objects and boundaries more easily.

    *example usage: segment*
7. *Predict* - identifies items in the image

    *example usage: predict*
'''
        self.send_message(chat_id, text, parse_mode="Markdown")

    def send_text(self, chat_id, text):
        """
        This method is the basic one for sending text to the user.
        """
        self.send_message(chat_id, text)

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Regular Bot - incoming message: {msg}')
        chat_id = msg['chat']['id']

        if "text" in msg:
            text = msg["text"].lower()
            if any(substring in text for substring in ["start", "help", "hello"]):
                self.send_welcome(chat_id)
            else:
                self.send_text(chat_id, f'Your original message: {msg["text"]}')
        else:
            e = Exception('None user message received')
            logger.exception(e)
            self.handle_exception(e, chat_id)

class QuoteBot(Bot):
    """
    This bot is an extension of the original bot and is dedicated for sending quoted text
    """
    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        """
        This method is the basic one for sending quoted text to the user.
        """
        self.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)

    def handle_message(self, msg):
        """Quote Bot message handler"""
        logger.info(f'Quote Bot - incoming message: {msg}')
        chat_id = msg['chat']['id']

        if "text" in msg:
            if msg["text"] != 'Please don\'t quote me':
                self.send_text_with_quote(chat_id, msg["text"], quoted_msg_id=msg["message_id"])
        else:
            e = Exception('None user message received')
            logger.exception(e)
            self.handle_exception(e, chat_id)

class ImageProcessingBot(Bot):
    """
    This bot is an extension of the original bot and is dedicated for image processing operations
    """

    def __init__(self, tgbot):
        super().__init__(tgbot)
        self.media_groups = {}
        self.direction = None
        self.sides = None

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return file_info.file_path:
        """
        file_info = self.get_file(msg['photo'][-1]['file_id'])
        data = self.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        try:
            with open(file_info.file_path, 'wb') as photo:
                photo.write(data)
        except OSError as e:
            logger.exception(e)
            self.handle_exception(f"{e}\nPlease try again.", msg["chat"]["id"])
            return None

        return file_info.file_path

    def handle_photo(self, chat_id, img_path, caption=""):
        """
        This method is used to send images to the user
        """
        try:
            if not img_path.exists() and img_path.is_file():
                raise FileNotFoundError("Image doesn't exist or it's not a file. Please try again")
        except FileNotFoundError as e:
            logger.exception(e)
            self.handle_exception(e, chat_id)
            return

        if not caption:
            self.send_photo(
                chat_id,
                InputFile(img_path)
            )
        else:
            self.send_photo(
                chat_id,
                InputFile(img_path),
                caption=caption
            )

    def handle_message(self, msg):
        """Image Bot message handler"""
        logger.info(f"Image Processing Bot - incoming message {msg}")
        chat_id = msg['chat']['id']

        # Check whether a caption was sent and if so assign to variable
        caption = msg.get("caption", "").strip().lower()
        # Check wether the incoming image is part of a media group i.e. more than one image was sent
        media_group_id = msg.get("media_group_id", None)
        try:
            if not caption and not media_group_id:
                raise RuntimeError("Please specify an action you'd like to execute on the image and try again.\nIf you're unsure, please refer to 'help' for assistance and try again.")

            if caption:
                if not any(substring in caption for substring in ["blur", "contour", "rotate", "salt and pepper", "concat", "segment"]):
                    raise ValueError("Invalid image action specified. Please refer to the 'help' for assistance and try again.")

                if "concat" in caption and not media_group_id:
                    raise RuntimeError("You need to upload more than one image in order to concat. Please try again.")
        except ValueError as e:
            logger.exception(e)
            self.handle_exception(e, chat_id)
            return
        except RuntimeError as e:
            logger.exception(e)
            self.handle_exception(e, chat_id)
            return

        image_path = self.download_user_photo(msg)

        try:
            if not image_path:
                raise Exception("Was unable to download image from Bot. Please try again.")
        except Exception as e:
            logger.exception(e)
            self.handle_exception(e, chat_id)
            return

        try:
            img = Img(image_path)
        except Exception as e:
            logger.exception(e)
            self.handle_exception(f"{e}\nPlease try again.", chat_id)
            return

        if (caption and "concat" in caption) or media_group_id:
            if caption:
                instruction = caption.replace("concat", "").strip()

                if instruction:
                    for substring in ["horizontal", "vertical"]:
                        if substring in instruction:
                            self.direction = substring
                            break
                    if self.direction:
                        instruction = instruction.replace(self.direction, "").strip()

                    if instruction:
                        self.sides = instruction

            # Initialize the group in the dictionary if it doesn't exist
            if media_group_id not in self.media_groups:
                self.media_groups[media_group_id] = []

            self.media_groups[media_group_id].append(img)

            if len(self.media_groups[media_group_id]) > 1:
                try:
                    if self.direction and self.sides:
                        self.media_groups[media_group_id][0].concat(self.media_groups[media_group_id][1], self.direction, self.sides)
                    elif self.direction:
                        self.media_groups[media_group_id][0].concat(self.media_groups[media_group_id][1], direction=self.direction)
                    elif self.sides:
                        self.media_groups[media_group_id][0].concat(self.media_groups[media_group_id][1], sides=self.sides)
                    else:
                        self.media_groups[media_group_id][0].concat(self.media_groups[media_group_id][1])

                    image_path = self.media_groups[media_group_id][0].save_img()
                    # Send the response with the modified image back to the bot
                    self.handle_photo(chat_id, image_path)
                except ValueError as e:
                    logger.exception(f"{e}\nPlease try again.")
                    self.handle_exception(f"{e}\nPlease try again.", chat_id)
                    return
                except RuntimeError as e:
                    logger.exception(f"{e}\nPlease try again.")
                    self.handle_exception(f"{e}\nPlease try again.", chat_id)
                    return
                except Exception as e:
                    logger.exception(f"{e}\nPlease try again.")
                    self.handle_exception(f"{e}\nPlease try again.", chat_id)
                    return
                finally:
                    # Clean the handled group from the media groups dictionary and reset the direction and sides
                    del self.media_groups[media_group_id]
                    self.direction = None
                    self.sides = None
        else:
            try:
                if "blur" in caption:
                    blur_level = caption.replace("blur", "").strip()
                    if blur_level:
                        img.blur(blur_level)
                    else:
                        img.blur()
                elif "contour" in caption:
                    img.contour()
                elif "rotate" in caption:
                    direction = None
                    degree = None
                    instruction = caption.replace("rotate", "").strip()
                    if instruction:
                        for substring in ["anti-clockwise", "clockwise"]:
                            if substring in instruction:
                                direction = substring
                                break
                        if direction:
                            instruction = instruction.replace(direction, "").strip()

                        if instruction:
                            degree = instruction

                    if direction and degree:
                        img.rotate(direction, degree)
                    elif direction:
                        img.rotate(direction=direction)
                    elif degree:
                        img.rotate(deg=degree)
                    else:
                        img.rotate()
                elif "salt and pepper" in caption:
                    noise_level = caption.replace("salt and pepper", "").strip()
                    if noise_level:
                        img.salt_n_pepper(noise_level)
                    else:
                        img.salt_n_pepper()
                elif "segment" in caption:
                    img.segment()

                image_path = img.save_img()
                # Send the response with the modified image back to the bot
                self.handle_photo(chat_id, image_path)
            except ValueError as e:
                logger.exception(f"{e}\nPlease try again.")
                self.handle_exception(f"{e}\nPlease try again.", chat_id)
            except Exception as e:
                logger.exception(f"{e}\nPlease try again.")
                self.handle_exception(f"{e}\nPlease try again.", chat_id)

class ObjectDetectionBot(ImageProcessingBot):
    """
    The ObjectDetectionBot class is an extension to the ImageProcessingBot class and essentially extends its functionality to detect items in a user sent image.
    """
    def handle_message(self, msg):
        """Object Detection Bot message handler"""
        logger.info(f"Prediction Bot - incoming message {msg}")
        chat_id = msg['chat']['id']

        # Check whether a caption was sent and if so assign to variable
        caption = msg.get("caption", "").strip().lower()

        if "predict" not in caption:
            super().handle_message(msg)
        elif "predict" in caption:
            image_path = self.download_user_photo(msg)

            try:
                if not image_path:
                    raise Exception("Was unable to download image from Bot. Please try again.")
            except Exception as e:
                logger.exception(e)
                self.handle_exception(e, chat_id)
                return

            # Let the user that something is happening
            self.send_text(chat_id, "Processing, please wait...")

            image_name = os.path.basename(image_path)

            try:
                response = upload_image_to_s3(images_bucket, f"{images_prefix}/{image_name}", image_path)

                if response[1] != 200:
                    raise Exception(f"{response[0]}\nPlease try again.")
            except Exception as e:
                logger.exception(e)
                self.handle_exception(e, chat_id)
                return

            # Implemented a retry mechanism when calling the Yolo service together with catching all raised exceptions and handling them gracefully.
            response = None
            retry = 0
            max_retries = 3
            curr_exception = None
            while retry < max_retries:
                try:
                    response = requests.post(f"http://{os.environ['YOLO5_NAME']}:{os.environ['YOLO5_PORT']}/predict?imgName={image_name}", timeout=90)
                    response.raise_for_status()  # This will raise HTTPError for 4XX or 5XX status codes
                    logger.info(json.dumps(response.json()))
                    break
                except requests.ConnectionError as e:
                    curr_exception = e
                    logger.exception(e)
                except requests.Timeout as e:
                    curr_exception = e
                    logger.exception(e)
                except requests.HTTPError as e:
                    curr_exception = f"HTTP error occurred: {e.response.status_code}\n{e}"
                    logger.exception(curr_exception)
                except Exception as e:
                    curr_exception = e
                    logger.exception(e)

                retry += 1
                if retry < max_retries:
                    time.sleep(3)

            if retry == max_retries:
                self.handle_exception(curr_exception, chat_id)
                return

            # Upon success downloaded the resulting image and send it to the user together with a summary of the results.
            if response.status_code == 200:
                response_data = response.json()
                try:
                    res = download_image_from_s3(images_bucket, response_data["original_img_path"], response_data["original_img_path"], images_prefix)

                    if res[1] != 200:
                        raise Exception(f"{res[0]}\nPlease try again.")

                    parsed_results = ""
                    try:
                        parsed_results = parse_result(response_data)
                    except Exception as e:
                        raise e

                    image_path = Path(response_data["original_img_path"])
                    # Send the response with the modified image back to the bot
                    self.handle_photo(chat_id, image_path, parsed_results)
                except Exception as e:
                    logger.exception(e)
                    self.handle_exception(e, chat_id)