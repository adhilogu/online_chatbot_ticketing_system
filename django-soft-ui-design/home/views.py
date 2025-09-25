import subprocess
import uuid
from django.contrib.auth.decorators import login_required
import pyttsx3
import os
import requests
from django.http import JsonResponse, HttpResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from gtts import gTTS
import json
from django.http import HttpResponseForbidden
import logging
from django.shortcuts import render, get_object_or_404
from googletrans import Translator
import requests
import json
import ast
from django.contrib.auth.models import User
from .models import Show, PaymentDetails, Ticket, FakeTransaction, Income, ServiceAndShows
from uuid import uuid4
from datetime import datetime
from threading import Thread
import re
from django.db.models import Q
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.shortcuts import redirect
from django.contrib.auth import login
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from decimal import Decimal
import google.generativeai as genai

# Configure logging for better debugging
logger = logging.getLogger(__name__)
import os
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_TRACE"] = ""
# Configure Gemini API
genai.configure(api_key="AIzaSyCvo25ccJwHRNUHLqLCeE_Ay3dvHu4HM0g")  # Replace with a valid Google AI API key
model = genai.GenerativeModel('gemini-2.5-flash')

def index(request):
    return render(request, 'pages/index.html')

# Check Gemini API connectivity
def check_gemini_api():
    try:
        response = model.generate_content("Test connection")
        logger.info("Gemini API test response: %s", response.text)
        return bool(response.text)
    except Exception as e:
        logger.error("Gemini API check failed: %s", e)
        return False

# Check Google Translate API connectivity
def check_google_translate():
    try:
        translator = Translator()
        test_translation = translator.translate("test", dest="es")
        return test_translation.text == "prueba"
    except Exception as e:
        logger.error("Google Translate API check failed: %s", e)
        return False

# Perform system checks and return JSON response
def system_check(request):
    bot_connected = check_gemini_api()
    translator_working = check_google_translate()

    checks = [
        {"check": "Checking Gemini API connection...", "result": bot_connected},
        {"check": "Checking Google Translate API connection...", "result": translator_working},
    ]

    all_checks_passed = all(check["result"] for check in checks)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"checks": checks, "all_checks_passed": all_checks_passed})

    return render(request, "pages/syschecker.html", {"checks": checks})

@login_required
def chat_page(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden("You must be logged in to access the chat.")
    return render(request, 'pages/chat.html')

def login_as_guest(request):
    if request.user.is_authenticated:
        return redirect('chat_page')

    guest_user, created = User.objects.get_or_create(username="guest", email="guest@example.com")
    login(request, guest_user)
    return redirect('chat_page')

def translate_text(text, dest_language):
    """Translate text into the desired language."""
    try:
        translator = Translator()
        translated_text = translator.translate(text, dest=dest_language).text
        return translated_text
    except Exception as e:
        logger.error("Error translating text: %s", e)
        return text

def generate_audio(text, dest_language, session_key):
    """Generate audio from the translated text."""
    try:
        audio_file = f"audio_response_{session_key}.mp3"
        audio_path = os.path.join("static", "audio", audio_file)

        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        tts = gTTS(text=text, lang=dest_language)
        tts.save(audio_path)

        sped_up_audio_path = os.path.join("static", "audio", f"sped_up_{audio_file}")
        subprocess.run(
            ["ffmpeg", "-i", audio_path, "-filter:a", "atempo=1.2", "-y", sped_up_audio_path],
            check=True,
        )
        return f"/static/audio/sped_up_{audio_file}"
    except Exception as e:
        logger.error("Error generating audio: %s", e)
        return None

def get_conversation_state(session_key):
    """Get or initialize conversation state for a session."""
    if not hasattr(get_conversation_state, 'conversations'):
        get_conversation_state.conversations = {}

    if session_key not in get_conversation_state.conversations:
        get_conversation_state.conversations[session_key] = {
            'state': 'greeting',
            'collected_data': {},
            'last_intent': None
        }
    return get_conversation_state.conversations[session_key]

def set_conversation_state(session_key, state, data=None):
    """Update conversation state for a session."""
    conv_state = get_conversation_state(session_key)
    conv_state['state'] = state
    if data:
        conv_state['collected_data'].update(data)

def analyze_user_intent(user_message, conversation_state):
    """Use Gemini to analyze user intent and extract information."""
    services = ServiceAndShows.objects.filter(status="Active", type="service")
    shows = Show.objects.filter(status="Active")
    distinct_shows = {show.ticket_name: show for show in shows}.values()

    service_names = [service.name for service in services]
    show_names = [show.ticket_name for show in distinct_shows]

    prompt = f"""
    You are a museum chatbot assistant. Analyze the user's message and determine their intent.

    Available services: {', '.join(service_names)}
    Available ticket types: {', '.join(show_names)}

    Current conversation state: {conversation_state['state']}
    Previously collected data: {conversation_state.get('collected_data', {})}

    User message: "{user_message}"

    Based on the user's message, determine:
    1. The main intent (greeting, ticket_booking, service_request, nationality_selection, ticket_type_selection, count_specification, confirmation, payment, help)
    2. Extract any relevant information (nationality, adult_count, children_count, ticket_type, service_type)
    3. Provide an appropriate response

    Respond strictly in JSON format only (no extra text or markdown):
    {{
        "intent": "detected_intent",
        "extracted_data": {{
            "nationality": "Indian/Foreigner or null",
            "adult_count": "number or null",
            "children_count": "number or null",
            "ticket_type": "ticket type name or null",
            "service_type": "service name or null"
        }},
        "response": "Your response to the user",
        "next_state": "next conversation state",
        "buttons": []
    }}

    For ticket booking flow:
    - If user wants tickets, ask for nationality first
    - Then ask for ticket type
    - Then ask for number of adults and children
    - Finally confirm details before payment

    Be helpful and guide users through the process step by step.
    """

    try:
        generation_config = {"response_mime_type": "application/json"}
        response = model.generate_content(prompt, generation_config=generation_config)
        logger.info("Gemini raw response: %s", response.text)
        result = json.loads(response.text)
        return result
    except json.JSONDecodeError as json_err:
        logger.error("JSON parsing error from Gemini response: %s", json_err)
        return {
            "intent": "unknown",
            "extracted_data": {},
            "response": "I'm sorry, there was an issue processing your request. Please try again.",
            "next_state": "greeting",
            "buttons": []
        }
    except Exception as e:
        logger.error("Error analyzing intent with Gemini: %s", e)
        return {
            "intent": "unknown",
            "extracted_data": {},
            "response": "I'm sorry, I couldn't connect to the AI service. Please check back later.",
            "next_state": "greeting",
            "buttons": []
        }

@csrf_exempt
def payment_page(request):
    if request.method == "GET":
        amount = request.GET.get("amount", 0)
        sender = request.GET.get("sender", "Unknown Sender")
        return render(request, "pages/payment_page.html", {
            "amount": amount,
            "sender": sender,
        })

    if request.method == "POST":
        data = json.loads(request.body)
        transaction_id = data.get("transaction_id")
        amount = data.get("amount")
        sender = data.get("sender")

        transaction = FakeTransaction.objects.create(
            transaction_id=transaction_id,
            amount=amount,
            sender=sender,
            status="Success",
        )
        logger.info(f"Payment Successful! Transaction ID: {transaction_id}, Amount: {amount}, Sender: {sender}")

        request.session["transaction_id"] = transaction_id

        response_data = {
            "transaction_id": transaction_id,
            "amount": amount,
            "status": transaction.status,
            "message": f"Payment successful! Amount: ₹{amount}, Transaction ID: {transaction_id}",
        }

        if transaction.status == "Success":
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                "message": "Payment failed. Please try again.",
                "status": "Failed"
            })

@csrf_exempt
def verify_transaction(request):
    if request.method == "POST":
        data = json.loads(request.body)
        transaction_id = data.get("transaction_id")

        transaction = FakeTransaction.objects.filter(transaction_id=transaction_id).first()
        if not transaction or transaction.status != "Success":
            return JsonResponse({"error": "Transaction not found or failed."}, status=404)

        return JsonResponse({
            "transaction_id": transaction.transaction_id,
            "amount": transaction.amount,
            "status": transaction.status,
            "message": f"Payment successful! Amount: ₹{transaction.amount}, Transaction ID: {transaction.transaction_id}",
        })
    return JsonResponse({"error": "Invalid request."}, status=400)

@csrf_exempt
def process_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)
        transaction_id = data.get("transaction_id")
        amount = data.get("amount")
        sender = data.get("sender")

        try:
            transaction = FakeTransaction.objects.get(transaction_id=transaction_id, status="Success")
        except FakeTransaction.DoesNotExist:
            return JsonResponse({"error": "Transaction not found or not verified."}, status=400)

        if not Income.objects.filter(transaction_id=transaction_id).exists():
            Income.objects.create(
                transaction_id=transaction_id,
                sender=sender,
                amount=amount,
                description="Online payment received and verified.",
            )
            logger.info(f"Income recorded for transaction: {transaction_id}")

        return JsonResponse({
            "message": f"Payment verified and recorded. Amount: ₹{amount}, Transaction ID: {transaction_id}"
        })
    return JsonResponse({"error": "Invalid request."}, status=400)

def confirm_details(extracted_data, selected_language):
    translated_bot_reply = translate_text(
        f"Are your details correct? Nationality: {extracted_data['nationality']}, "
        f"Adults: {extracted_data['adult_count']}, Children: {extracted_data['children_count']}, "
        f"Show: {extracted_data['ticket_type']}.",
        selected_language
    )
    buttons = [
        {"title": translate_text("Confirm", selected_language), "payload": "confirm"},
        {"title": translate_text("Cancel/Edit", selected_language), "payload": "cancel_or_edit"}
    ]
    return translated_bot_reply, buttons

def calculate_bill(extracted_data):
    ticket_type = extracted_data.get("ticket_type", "").strip()
    nationality = extracted_data.get("nationality", "").strip()
    adult_count = int(extracted_data.get("adult_count", 0))
    children_count = int(extracted_data.get("children_count", 0))

    logger.info(f"Calculating bill for: {ticket_type}, {nationality}, Adults: {adult_count}, Children: {children_count}")

    active_tickets = Show.objects.filter(
        Q(ticket_name__iexact=ticket_type) & Q(status="Active")
    )
    logger.info("Active Tickets: %s", active_tickets)

    adult_price = active_tickets.filter(ticket_age="Adult", nationality=nationality).first()
    child_price = active_tickets.filter(ticket_age="Child", nationality=nationality).first()

    if not adult_price or not child_price:
        logger.warning(f"No active prices found for {ticket_type}, {nationality}")
        return None

    total_adult_cost = adult_count * adult_price.price
    total_child_cost = children_count * child_price.price
    total_cost = total_adult_cost + total_child_cost

    logger.info(f"Total Cost: ₹{total_cost}, Adult Cost: ₹{total_adult_cost}, Child Cost: {total_child_cost}")

    return {
        "total_cost": total_cost,
        "breakdown": {
            "adult_cost": total_adult_cost,
            "child_cost": total_child_cost,
            "adult_price": adult_price.price,
            "child_price": child_price.price,
        }
    }

def generate_qr(transaction_id, session_key, nationality, adult_count, children_count, access_details):
    tickets = []
    total_tickets = adult_count + children_count
    logger.info(f"Generating {total_tickets} tickets for Transaction ID: {transaction_id}, Session Key: {session_key}")

    try:
        ticket = Ticket(
            session_id=session_key,
            nationality=nationality,
            transaction_id=transaction_id,
            transaction_at=FakeTransaction.objects.get(transaction_id=transaction_id).created_at,
            entry_in=access_details.get("entry_in", False),
            entry_out=access_details.get("entry_out", False),
            dinosaur_show_in=access_details.get("dinosaur_show_in", False),
            dinosaur_show_out=access_details.get("dinosaur_show_out", False),
            ancient_statues_in=access_details.get("ancient_statues_in", False),
            ancient_statues_out=access_details.get("ancient_statues_out", False),
            ice_age_show_in=access_details.get("ice_age_show_in", False),
            ice_age_show_out=access_details.get("ice_age_show_out", False),
            photography=access_details.get("photography", False),
            adult_count=adult_count,
            child_count=children_count,
        )

        total_price = 0
        show_mapping = {
            "entry_in": "Entry",
            "dinosaur_show_in": "Dinosaur Show",
            "ancient_statues_in": "Ancient Statues",
            "ice_age_show_in": "Ice Age Show",
            "photography": "Photography",
        }

        active_shows = Show.objects.filter(nationality=nationality, status="Active")
        active_show_dict = {show.ticket_name: show for show in active_shows}

        for field, show_name in show_mapping.items():
            if getattr(ticket, field):
                show = active_show_dict.get(show_name)
                if show:
                    total_price += show.price

        ticket.ticket_amount = total_price * total_tickets
        ticket.save()

        qr_data = str(ticket.qr_code_uuid)
        qr_image = qrcode.make(qr_data)
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        buffer.seek(0)

        file_name = f"ticket_qr_{ticket.transaction_id}_{ticket.id}.png"
        ticket.qr_code.save(file_name, ContentFile(buffer.read()), save=False)
        ticket.save()

        tickets.append(ticket)
        logger.info(f"QR Code saved for ticket: {ticket.id}, Amount: ₹{ticket.ticket_amount}")

        qr_codes = [
            {
                "age_category": "Combined",
                "qr_code_url": ticket.qr_code.url,
                "ticket_types": [
                    "ENTRY IN" if ticket.entry_in else None,
                    "ENTRY OUT" if ticket.entry_out else None,
                    "DINOSAUR SHOW IN" if ticket.dinosaur_show_in else None,
                    "DINOSAUR SHOW OUT" if ticket.dinosaur_show_out else None,
                    "ANCIENT STATUES IN" if ticket.ancient_statues_in else None,
                    "ANCIENT STATUES OUT" if ticket.ancient_statues_out else None,
                    "ICE AGE SHOW IN" if ticket.ice_age_show_in else None,
                    "ICE AGE SHOW OUT" if ticket.ice_age_show_out else None,
                    "PHOTOGRAPHY" if ticket.photography else None,
                ]
            }
        ]
        return qr_codes
    except Exception as e:
        logger.error("Error in generate_qr: %s", e)
        return []


@csrf_exempt
def send_message(request):
    if request.method != 'POST':
        return JsonResponse({'reply': 'Invalid request.'}, status=400)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        language = data.get('language', 'en')
        logger.info("Received message: %s, language: %s", user_message, language)

        if not user_message:
            return JsonResponse({'reply': 'Please provide a message.'}, status=400)

        # Ensure session exists
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key

        # Mock Gemini response for testing
        if user_message == "test_language":
            return JsonResponse({
                'reply': f"Language test successful: {language}",
                'reply_type': 'text',
                'data': {}
            })

        # Call Gemini API
        result = analyze_user_intent(user_message, language, session_id)
        response_text = result.get('response', 'No response from AI.')

        # Translate if not English
        if language != 'en':
            try:
                translator = Translator()
                translated_response = translator.translate(response_text, dest=language).text
                result['response'] = translated_response
            except Exception as e:
                logger.error("Translation error: %s", e)
                result['response'] = response_text  # Fallback to English

        return JsonResponse({
            'reply': result['response'],
            'buttons': result.get('buttons', []),
            'reply_type': result.get('reply_type', 'text'),
            'data': result.get('data', {})
        })
    except Exception as e:
        logger.error("Error in send_message: %s", e)
        return JsonResponse({'reply': 'Error processing request.'}, status=500)



@csrf_exempt
def qrmodaldisplay(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        session_id = data.get('session_id')

        if not session_id:
            return JsonResponse({"message": "Session ID not provided."}, status=400)

        tickets = Ticket.objects.filter(session_id=session_id)

        if not tickets.exists():
            return JsonResponse({"message": "No tickets found for this session."}, status=404)

        qr_codes = []
        total_adult_count = 0
        total_child_count = 0
        total_tickets = 0

        for ticket in tickets:
            if ticket.qr_code:
                qr_codes.append({
                    "qr_code_url": ticket.qr_code.url,
                    "adult_count": ticket.adult_count,
                    "child_count": ticket.child_count,
                    "total_tickets": ticket.adult_count + ticket.child_count,
                })
                total_adult_count += ticket.adult_count
                total_child_count += ticket.child_count
                total_tickets += ticket.adult_count + ticket.child_count
            else:
                logger.warning(f"No QR code found for Ticket ID: {ticket.id}")

        return JsonResponse({
            "qr_codes": qr_codes,
            "total_adult_count": total_adult_count,
            "total_child_count": total_child_count,
            "total_tickets": total_tickets
        })

    return JsonResponse({"message": "Invalid request method."}, status=400)

@csrf_exempt
def validate_ticket(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            qr_code_uuid = data.get("qr_code_uuid")
            ticket_type = data.get("ticket_type")

            if not qr_code_uuid or not ticket_type:
                return JsonResponse({"status": "error", "message": "Invalid data provided"})

            try:
                ticket = Ticket.objects.get(qr_code_uuid=qr_code_uuid)

                if hasattr(ticket, ticket_type) and isinstance(getattr(ticket, ticket_type), bool):
                    if getattr(ticket, ticket_type, False):
                        setattr(ticket, ticket_type, False)
                        ticket.save()
                        return JsonResponse({"status": "success", "message": "Gate Opened and Entry Marked"})
                    else:
                        return JsonResponse({"status": "failure", "message": "Gate is already closed"})
                else:
                    return JsonResponse({"status": "error", "message": f"Invalid ticket type {ticket_type}"})

            except Ticket.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Ticket not found"})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON input"})
    return JsonResponse({"status": "error", "message": "Invalid request method"})