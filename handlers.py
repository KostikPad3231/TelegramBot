import logging
import os

import requests
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from create_bot import client, model

router = Router()
MINDEE_API_KEY = os.getenv('MINDEE_API_KEY')
if not MINDEE_API_KEY:
    logging.error('Bot token not set')

user_chat_histories = {}


# FSM
class CarInsurance(StatesGroup):
    uploading_passport = State()
    uploading_vehicle_id = State()
    data_confirmation = State()
    price_quotation = State()


def mock_mindee_extract_vin(vehicle_doc_photo):
    return {
        'registration plate': 'AA0000AA',
        'vin': "1AAAA11111A111111",
        'make': "Mitsubishi Outlander",
        'type': 'crossover',
        'category': 'B',
        "year": "2015",
        'chassis number': '12345',
        'body number': '67890',
        'color': 'white',
    }


async def openai_generate(text: str, purpose: str, state: str = None, user_input: str = None, data: dict = None):
    """
    Generate a response using OpenAI API.

    Args:
        text: Base text or context for the response.
        purpose: Either "conversation" or "policy".
        state: Current FSM state (e.g., "uploading_passport").
        user_input: User's latest message for context (optional).

    Returns:
        Generated response as a string.
    """
    try:
        if purpose == 'policy':
            # For policy generation
            prompt = f"""
            Generate a car insurance policy document based on the following details:
            - Name: {data['given_names']} {data['surname']}
            - ID number: {data['id_number']}
            - Country: {data['country']}
            - Vehicle: {data['make']}
            - VIN: {data['vin']}
            - Premium: 100 USD
            - Effective Date: "insert today"
            - Expiry Date: "insert date one year after today"
            - Terms: Standard coverage for one year.

            Format the output as a clear, professional document with a unique policy number.
            """
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system', 'content': 'You are a professional insurance bot.'},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()

        elif purpose == 'conversation':
            state_instructions = {
                'uploading_passport': 'The user should upload a photo of their passport. Politely ask for the passport photo.',
                'uploading_vehicle_id': 'The user should upload a photo of their vehicle identification document. Request the vehicle document.',
                'data_confirmation': 'The user should confirm or cancel the extracted data. Ask them to select "Confirm" or "Cancel".',
                'price_quotation': 'The user should agree or disagree with the insurance price. Ask them to select "Agree" or "Disagree".'
            }

            instruction = state_instructions.get(state)
            prompt = f"""
            You are a friendly car insurance bot. Your goal is to assist the user in purchasing car insurance while keeping the conversation natural and on-topic.

            Current state: {state}
            Instruction: {instruction}
            User input: {user_input or "None"}
            Context: {text}

            Respond in a conversational, human-like tone. If the user input is off-topic, acknowledge it briefly and redirect them to the expected action. Keep the response concise (1-2 sentences).
            """
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system', 'content': 'You are a friendly and professional insurance bot.'},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=100,
                temperature=0.9,
            )
            return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f'OpenAI API error: {e}')
        return 'Sorry, something went wrong. Please follow the instructions.'


# def mock_openai_generate(text: str, purpose: str) -> str:
#     if purpose == "conversation":
#         return f"Here's a friendly response: {text}"
#     elif purpose == "policy":
#         return f"""
#         Insurance Policy
#         Policy Number: INS-{uuid.uuid4().hex[:8]}
#         Name: John Doe
#         Vehicle: Honda Civic 2020
#         VIN: 1HGCM82633A004352
#         Premium: 100 USD
#         Effective Date: 2025-05-06
#         Expiry Date: 2026-05-06
#         Terms: Standard coverage for one year.
#         """
#     return text


async def upload_photo(file_content, file_extension='jpg', mime_type='image/jpeg'):
    """
    Upload passport photo to Mindee and extract info from it.

    Args:
        file_content: the passport photo.
        file_extension: the file extension of the photo.
        mime_type: the mime type for sendin request.

    Returns:
        Extracted information.
    """
    url = 'https://api.mindee.net/v1/products/mindee/passport/v1/predict'
    headers = {
        'Authorization': f'Token {MINDEE_API_KEY}'
    }

    try:
        filename = f'photo.{file_extension}'
        files = {
            'document': (filename, file_content, mime_type)
        }

        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        logging.error(f'API request error: {e}')
        return None


def get_confirmation_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Confirm')],
            [KeyboardButton(text='Cancel')],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_price_confirmation_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='Agree')],
            [KeyboardButton(text='Disagree')],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


async def download_photo(photo, bot):
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    file_path = file_info.file_path
    file_extension = file_path.split('.')[-1].lower() if '.' in file_path else 'jpg'
    mime_type = 'image/jpeg'
    if file_extension == 'png':
        mime_type = 'image/png'
    elif file_extension == 'gif':
        mime_type = 'image/gif'
    elif file_extension == 'webp':
        mime_type = 'image/webp'
    return downloaded_file, file_extension, mime_type


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    welcome_text = await openai_generate(
        'Welcome the user and explain that you\'re here to help them purchase car insurance.',
        purpose='conversation',
        state='uploading_passport'
    )
    await message.answer(welcome_text)
    await state.set_state(CarInsurance.uploading_passport)


@router.message(CarInsurance.uploading_passport, F.photo)
async def get_passport_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    bot = message.bot
    downloaded_photo, file_extension, mime_type = await download_photo(photo, bot)
    result = await upload_photo(downloaded_photo, file_extension, mime_type)
    passport = result['document']
    for key in ['inference', 'prediction']:
        if isinstance(passport, dict) and key in passport:
            passport = passport[key]
        else:
            break
    if not passport:
        error_text = await openai_generate(
            'Inform the user that the passport image could not be processed and ask them to upload it again.',
            purpose='conversation',
            state='uploading_passport'
        )
        await message.answer(error_text)
        await state.set_state(CarInsurance.uploading_passport)
        return

    await state.update_data(passport=result)

    praise_text = await openai_generate(
        'Thank the user.',
        purpose='conversation',
        state='uploading_vehicle_id'
    )
    await message.answer(praise_text)
    await state.set_state(CarInsurance.uploading_vehicle_id)


@router.message(CarInsurance.uploading_vehicle_id, F.photo)
async def get_vehicle_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    bot = message.bot
    downloaded_photo, file_extension, mime_type = await download_photo(photo, bot)
    extracted_data = mock_mindee_extract_vin(downloaded_photo)
    data = await state.get_data()
    passport = data['passport']['document']
    for key in ['inference', 'prediction']:
        if isinstance(passport, dict) and key in passport:
            passport = passport[key]
        else:
            break

    answer = 'Please confirm the extracted information:\n\n\nPassport\n\n'
    data_for_insurance = dict()
    for key in set(data['passport']['document']['inference']['product']['features']) - {'orientation', }:
        if isinstance(passport[key], list):
            given_names = ', '.join((map(lambda x: x["value"], passport[key])))
            answer += f'{key} - ' + given_names + '\n'
            data_for_insurance[key] = given_names
        else:
            answer += f'{key} - {passport[key]["value"]}\n'
            data_for_insurance[key] = passport[key]['value']
    answer += '\n\nVehicle info:\n\n'
    for key in ['registration plate', 'vin', 'make', 'type', 'category', 'year', 'chassis number', 'body number',
                'color']:
        answer += f'{key} - {extracted_data[key]}\n'
        data_for_insurance[key] = extracted_data[key]
    await state.update_data(data=data_for_insurance)

    success_text = await openai_generate(
        'Thank the user for uploading the passport and ask him to confirm the extracted information.',
        purpose='conversation',
        state='data_confirmation'
    )
    await message.answer(f"{success_text}\n\n{answer}", reply_markup=get_confirmation_keyboard())
    await state.set_state(CarInsurance.data_confirmation)


@router.message(CarInsurance.data_confirmation)
async def handle_data_confirmation(message: Message, state: FSMContext):
    if message.text.lower() == 'confirm':
        price_text = await openai_generate(
            'Inform the user that the insurance premium is 100 USD and ask if they agree.',
            purpose='conversation',
            state='price_quotation'
        )
        await message.answer(price_text, reply_markup=get_price_confirmation_keyboard())
        await state.set_state(CarInsurance.price_quotation)
    elif message.text.lower() == 'cancel':
        cancel_text = await openai_generate(
            'Acknowledge the cancellation and ask the user to upload their passport again.',
            purpose='conversation',
            state='uploading_passport'
        )
        await message.answer(cancel_text, reply_markup=ReplyKeyboardRemove())
        await state.set_state(CarInsurance.uploading_passport)
    else:
        error_text = await openai_generate(
            'The user provided an invalid response. Remind them to select \'Confirm\' or \'Cancel\'.',
            purpose='conversation',
            state='data_confirmation',
            user_input=message.text
        )
        await message.answer(error_text, reply_markup=get_confirmation_keyboard())


@router.message(CarInsurance.price_quotation)
async def handle_price_quotation(message: Message, state: FSMContext):
    if message.text.lower() == 'agree':
        data = await state.get_data()
        policy = await openai_generate('', purpose='policy', data=data)
        success_text = await openai_generate(
            'Thank the user for their purchase and inform them that their policy is ready.',
            purpose='conversation',
            state=None
        )
        await message.answer(f"{success_text}\n\n{policy}", reply_markup=ReplyKeyboardRemove())
        await state.clear()
    elif message.text.lower() == 'disagree':
        apology = await openai_generate(
            'Apologize and inform the user that 100 USD is the only available price.',
            purpose='conversation',
            state=None
        )
        await message.answer(apology, reply_markup=ReplyKeyboardRemove())
        await state.clear()
    else:
        error_text = await openai_generate(
            'The user provided an invalid response. Remind them to select "Agree" or "Disagree".',
            purpose='conversation',
            state='price_quotation',
            user_input=message.text
        )
        await message.answer(error_text, reply_markup=get_price_confirmation_keyboard())


@router.message()
async def handle_other(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        current_state = current_state.split(':')[-1]
    redirect_text = await openai_generate(
        'The user sent an unexpected message. Politely redirect them to the current step or to /start if no state is active.',
        purpose='conversation',
        state=current_state,
        user_input=message.text
    )
    await message.answer(redirect_text, reply_markup=ReplyKeyboardRemove())
