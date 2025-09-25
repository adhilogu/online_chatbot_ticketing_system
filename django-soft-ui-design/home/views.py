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
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from googletrans import Translator
import requests
import json
import ast
from django.contrib.auth.models import User
from .models import  Show, PaymentDetails, Ticket, FakeTransaction, Income ,ServiceAndShows
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









def index(request):
    return render(request, 'pages/index.html')

# Check Rasa server connectivity
def check_rasa_server():
    # Use the correct endpoint for Rasa status check
    rasa_url = "http://localhost:5005/status"
    try:
        # Check if the server is reachable
        response = requests.get(rasa_url, timeout=10)
        if response.status_code == 200:
            print("Rasa server is running.")
            return True
        else:
            print(f"Unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Rasa server check failed: {e}")
        return False


# Check Google Translate API connectivity
def check_google_translate():
    try:
        translator = Translator()
        test_translation = translator.translate("test", dest="es")
        return test_translation.text == "prueba"
    except Exception as e:
        print(f"Google Translate API check failed: {e}")
        return False


# Perform system checks and return JSON response
def system_check(request):
    # Perform backend checks
    bot_connected = check_rasa_server()
    translator_working = check_google_translate()
    chat_server_active = True  # Assume chat server is active for now

    checks = [
        {"check": "Ensuring chat server is active...", "result": bot_connected},
        {"check": "Checking Google Translate API connection...", "result": translator_working},
    ]

    # Determine if all backend checks passed
    all_checks_passed = all(check["result"] for check in checks)

    # Handle AJAX requests
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"checks": checks, "all_checks_passed": all_checks_passed})

    # Render system checker page for normal requests
    return render(request, "pages/syschecker.html", {"checks": checks})


"""# Render the chat page
def chat_page(request):
    return render(request, "pages/chat.html")"""


@login_required
def chat_page(request):
    # Ensure that only users with specific roles (admin or registered users) can access the chat
    if not request.user.is_authenticated:
        return HttpResponseForbidden("You must be logged in to access the chat.")

    return render(request, 'pages/chat.html')


def login_as_guest(request):
    # Check if the user is already authenticated
    if request.user.is_authenticated:
        return redirect('chat_page')

    # Create a guest user or get a guest user (you can customize this part)
    guest_user, created = User.objects.get_or_create(username="guest", email="guest@example.com")

    # Log the guest user in
    login(request, guest_user)

    # Redirect the user to the chat page or wherever you want
    return redirect('chat_page')

def translate_text(text, dest_language):
    """Translate text into the desired language."""
    try:
        translator = Translator()
        translated_text = translator.translate(text, dest=dest_language).text
        #print(f"Translated Text: '{translated_text}' to Language: {dest_language}")
        return translated_text
    except Exception as e:
        print(f"Error translating text: {e}")
        return text  # Fallback to original text


def generate_audio(text, dest_language, session_key):
    """Generate audio from the translated text."""
    try:
        #print(f"Generating audio for text: '{text}' in Language: {dest_language}")

        audio_file = f"audio_response_{session_key}.mp3"
        audio_path = os.path.join("static", "audio", audio_file)

        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        # Generate speech using the translated text
        tts = gTTS(text=text, lang=dest_language)  # Use the exact destination language code
        tts.save(audio_path)

        # Optional: Speed up the audio
        sped_up_audio_path = os.path.join("static", "audio", f"sped_up_{audio_file}")
        subprocess.run(
            ["ffmpeg", "-i", audio_path, "-filter:a", "atempo=1.2", "-y", sped_up_audio_path],
            check=True,
        )

        return f"/static/audio/sped_up_{audio_file}"
    except Exception as e:
        print(f"Error generating audio: {e}")
        return None


@csrf_exempt
def payment_page(request):
    if request.method == "GET":
        # Render payment page with query parameters
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

        # Save the transaction in the database
        transaction = FakeTransaction.objects.create(
            transaction_id=transaction_id,
            amount=amount,
            sender=sender,
            status="Success",
        )

        print(f"Payment Successful! Transaction ID: {transaction_id}, Amount: {amount}, Sender: {sender}")

        # Save the transaction_id in the session
        request.session["transaction_id"] = transaction_id

        # Return the success message as JSON
        response_data = {
            "transaction_id": transaction_id,
            "amount": amount,
            "status": transaction.status,
            "message": f"Payment successful! Amount: ₹{amount}, Transaction ID: {transaction_id}",
        }

        # Check the transaction status and respond accordingly
        if transaction.status == "Success":
            # Redirect to the chat page after a successful payment
            return JsonResponse(response_data)

        else:
            return JsonResponse({
                "message": "Payment failed. Please try again.",
                "status": "Failed"
            })

        # Since the redirect logic is handled in the frontend, there's no need for further redirect in this view.



@csrf_exempt
def verify_transaction(request):
    """
    Verify if the payment transaction was successful.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        transaction_id = data.get("transaction_id")

        # Check the transaction in the database
        transaction = FakeTransaction.objects.filter(transaction_id=transaction_id).first()
        if not transaction or transaction.status != "Success":
            return JsonResponse({"error": "Transaction not found or failed."}, status=404)

        # Return transaction details without generating tickets
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
        sender = data.get(request.user)

        # Check if the transaction exists and is successful
        try:
            transaction = FakeTransaction.objects.get(transaction_id=transaction_id, status="Success")
        except FakeTransaction.DoesNotExist:
            return JsonResponse({"error": "Transaction not found or not verified."}, status=400)

        # Add verified payment to the Income model
        if not Income.objects.filter(transaction_id=transaction_id).exists():  # Avoid duplicate income entries
            Income.objects.create(
                transaction_id=transaction_id,
                sender=sender,
                amount=amount,
                description="Online payment received and verified.",
            )
            print(f"Income recorded for transaction: {transaction_id}")

        return JsonResponse({"message": f"Payment verified and recorded. Amount: ₹{amount}, Transaction ID: {transaction_id}"})

    return JsonResponse({"error": "Invalid request."}, status=400)


def confirm_details(extracted_data, selected_language):
    """
    Generate a confirmation message with extracted details and buttons.
    """
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

    print(f"Calculating bill for: {ticket_type}, {nationality}, Adults: {adult_count}, Children: {children_count}")

    # Fetch active ticket prices
    active_tickets = Show.objects.filter(
        Q(ticket_name__iexact=ticket_type) & Q(status="Active")
    )
    print("Active Tickets:", active_tickets)

    adult_price = active_tickets.filter(ticket_age="Adult", nationality=nationality).first()
    child_price = active_tickets.filter(ticket_age="Child", nationality=nationality).first()

    if not adult_price:
        print(f"No active adult price found for {ticket_type}, {nationality}")
    if not child_price:
        print(f"No active child price found for {ticket_type}, {nationality}")

    if not adult_price or not child_price:
        return None

    total_adult_cost = adult_count * adult_price.price
    total_child_cost = children_count * child_price.price
    total_cost = total_adult_cost + total_child_cost

    print(f"Total Cost: ₹{total_cost}, Adult Cost: ₹{total_adult_cost}, Child Cost: ₹{total_child_cost}")

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
    """
    Generate a single ticket with QR code for the given transaction ID and session key.
    """
    tickets = []
    total_tickets = adult_count + children_count  # Total tickets = adults + children
    print(f"Generating {total_tickets} tickets for Transaction ID: {transaction_id}, Session Key: {session_key}")

    try:
        # Create a single ticket instance for the entire session (adults and children combined)
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

        # Reset total price before calculation
        total_price = 0

        # Show mapping for determining which shows to include in the total price
        show_mapping = {
            "entry_in": "Entry",
            "dinosaur_show_in": "Dinosaur Show",
            "ancient_statues_in": "Ancient Statues",
            "ice_age_show_in": "Ice Age Show",
            "photography": "Photography",
        }

        # Fetch all active shows for the given nationality
        active_shows = Show.objects.filter(
            nationality=nationality,
            status="Active"
        )

        # Convert the active shows to a dictionary for faster lookup by ticket_name
        active_show_dict = {show.ticket_name: show for show in active_shows}
        print(f"Loaded active shows: {list(active_show_dict.keys())}")  # Debug line to verify shows are loaded

        # Calculate the price for each show based on whether access is enabled
        for field, show_name in show_mapping.items():
            if getattr(ticket, field):  # If the ticket has access to this show
                show = active_show_dict.get(show_name)

                if show:
                    print(f"Show found: {show_name}, Price: ₹{show.price}")  # Debug line
                    total_price += show.price  # Add the price of this show to the total price
                else:
                    print(f"Show not found: {show_name}")  # Debug line if show isn't in the active list

        # Multiply the total price of applicable shows by the total ticket count (adult + child)
        ticket.ticket_amount = total_price * total_tickets

        # Save the ticket with the calculated amount
        ticket.save()

        # Generate QR code for the ticket
        # Generate QR code for the ticket
        qr_data = str(ticket.qr_code_uuid)
        qr_image = qrcode.make(qr_data)
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")
        buffer.seek(0)

        # Save the QR code image
        file_name = f"ticket_qr_{ticket.transaction_id}_{ticket.id}.png"
        ticket.qr_code.save(file_name, ContentFile(buffer.read()), save=False)
        ticket.save()

        tickets.append(ticket)
        print(f"QR Code saved for ticket: {ticket.id}, Amount: ₹{ticket.ticket_amount}")

        # Prepare the response with QR codes and ticket details
        qr_codes = [
            {
                "age_category": "Combined",  # Since you're combining adults and children
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
        print(f"Error in `generate_qr`: {e}")
        return []


@csrf_exempt
def send_message(request):
    if request.method == "POST":
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        data = json.loads(request.body)
        user_message = data.get("message", "")
        selected_language = data.get("language", "en")

        #print(f"Selected Language: {selected_language}")

        rasa_url = "http://localhost:5005/webhooks/rest/webhook"
        bot_reply = "I didn't understand that."
        reply_type = "unknown"
        audio_url = None
        extracted_data = {}

        # Check if there's a currently playing audio in session and stop it
        if "current_audio_url" in request.session:
            stop_audio_path = os.path.join("static", request.session["current_audio_url"].lstrip("/"))
            if os.path.exists(stop_audio_path):
                try:
                    os.remove(stop_audio_path)
                    print(f"Stopped and removed previous audio: {stop_audio_path}")
                except Exception as e:
                    print(f"Error stopping previous audio: {e}")
            del request.session["current_audio_url"]



        # Handle "confirm" button
        if user_message == "confirm":
            extracted_data = request.session.get("extracted_data", {})
            if not extracted_data:
                return JsonResponse({"reply": "No ticket details available to process. Please start again."})

            # Debugging: Ensure extracted data is correct
            print(f"Extracted data for bill calculation: {extracted_data}")

            # Calculate the bill
            bill = calculate_bill(extracted_data)
            if not bill:
                return JsonResponse({"reply": "Unable to calculate the bill. Please check your ticket details."})

            total_cost = float(bill["total_cost"])  # Convert Decimal to float
            breakdown = bill["breakdown"]

            # Convert all Decimal values in the breakdown to float
            breakdown = {key: float(value) for key, value in breakdown.items()}
            request.session["total_cost"] = total_cost  # Save total cost in session for later use

            translated_bot_reply = translate_text(
                f"Your total bill is ₹{total_cost:.2f}. "
                f"(Adults: ₹{breakdown['adult_cost']:.2f} @ ₹{breakdown['adult_price']:.2f}/ticket, "
                f"Children: ₹{breakdown['child_cost']:.2f} @ ₹{breakdown['child_price']:.2f}/ticket)",
                selected_language
            )

            buttons = [
                {"title": translate_text("Pay", selected_language), "payload": "pay_now"},
                {"title": translate_text("Cancel", selected_language), "payload": "cancel_ticket"},
            ]

            # Generate new audio for the bill
            audio_url = generate_audio(translated_bot_reply, selected_language, session_key)
            if audio_url:
                request.session["current_audio_url"] = audio_url

            return JsonResponse({
                "reply": translated_bot_reply,
                "buttons": buttons,
                "reply_type": "bill",
                "data": {"total_cost": total_cost, "breakdown": breakdown},
                "audio_url": audio_url,
            })


        # Check if the message is "pay_now"
        if user_message == "pay_now":
            total_cost = request.session.get("total_cost", 0)  # Retrieve the total cost from session
            payment_details = PaymentDetails.objects.first()  # Fetch payment details from the database

            if not payment_details:
                return JsonResponse({"reply": "Payment details are not available."})

            # Construct the payment page URL with the amount, note, and payment details
            payment_page_url = (
                f"/payment/?amount={total_cost}&note=Payment for Museum Tickets"
            )

            return JsonResponse({
                "reply": f"Redirecting you to the payment page. Your total amount is ₹{total_cost}.",
                "payment_url": payment_page_url,  # Send the payment page URL to the client
            })

        # Handle QR Code Request: "fetch_qr_codes"
        if user_message == "fetch_qr_codes":
            print(f"Fetching QR codes for session: {session_key}")

            # Query Ticket model using session_key
            tickets = Ticket.objects.filter(session_id=session_key)

            # Check if tickets exist for the session
            if not tickets.exists():
                return JsonResponse({
                    "reply": "No QR codes found for your session.",
                    "reply_type": "qr_codes",
                    "qr_codes": [],
                })

            # Prepare the QR codes data along with total ticket counts
            qr_codes = []
            total_adult_count = 0
            total_child_count = 0
            total_tickets = 0

            for ticket in tickets:
                if ticket.qr_code:  # Check if QR code exists
                    qr_codes.append({
                        "qr_code_url": ticket.qr_code.url,  # URL of the QR code image
                        "adult_count": ticket.adult_count,  # Adult ticket count for this ticket
                        "child_count": ticket.child_count,  # Child ticket count for this ticket
                        "total_tickets": ticket.adult_count + ticket.child_count,  # Total tickets for this ticket
                    })
                    # Sum up the total adult and child counts
                    total_adult_count += ticket.adult_count
                    total_child_count += ticket.child_count
                    total_tickets += ticket.adult_count + ticket.child_count

            # Prepare the final response with QR codes and ticket summary
            return JsonResponse({
                "reply": "Here are your QR codes.",
                "reply_type": "qr_codes",
                "qr_codes": qr_codes,
                "total_adult_count": total_adult_count,
                "total_child_count": total_child_count,
                "total_tickets": total_tickets,
            })

        if user_message == "payment_successful":
            print("Processing payment_successful message...")
            transaction_id = request.session.get("transaction_id")
            if not transaction_id:
                return JsonResponse({"reply": "No transaction details found. Please complete the payment first."})

            # Verify the transaction
            transaction = FakeTransaction.objects.filter(transaction_id=transaction_id, status="Success").first()
            if transaction:
                print(f"Transaction verified: {transaction.transaction_id}")

                # Ensure the transaction is recorded in the Income model
                income_entry, created = Income.objects.get_or_create(
                    transaction_id=transaction.transaction_id,
                    defaults={
                        "sender": request.user,
                        "amount": transaction.amount,
                        "description": f"Payment received via transaction {transaction.transaction_id}",
                        "session_id": request.session.session_key,
                        "booking_type": "Chatbot",
                    }
                )
                if created:
                    print(f"Income entry created for transaction ID: {transaction_id}")
                else:
                    print(f"Income entry already exists for transaction ID: {transaction_id}")

                # **Step 1: Check if tickets are already generated for this transaction**
                existing_tickets = Ticket.objects.filter(transaction_id=transaction_id).exists()
                if existing_tickets:
                    print(f"Tickets already exist for transaction ID: {transaction_id}")
                    # Fetch existing tickets and return QR codes with the new structure
                    qr_codes = [
                        {"qr_code_url": t.qr_code.url, "total_count": t.total_count}
                        for t in Ticket.objects.filter(transaction_id=transaction_id)
                    ]
                    return JsonResponse({
                        "reply": f"Payment successful! Amount: ₹{transaction.amount}, Transaction ID: {transaction.transaction_id}. Tickets already generated.",
                        "reply_type": "qr_codes",
                        "qr_codes": qr_codes,
                    })

                # **Step 2: Ticket Generation Logic**
                # Use the session key for ticket generation
                session_key = request.session.session_key
                extracted_data = request.session.get("extracted_data", {})

                # Extract details from the session data
                adult_count = int(extracted_data.get("adult_count", 0))
                children_count = int(extracted_data.get("children_count", 0))
                nationality = extracted_data.get("nationality", "Unknown")

                # Determine access details
                access_details = {
                    "entry_in": "entry" in extracted_data.get("ticket_type", "").lower(),
                    "entry_out": "entry" in extracted_data.get("ticket_type", "").lower(),
                    "dinosaur_show_in": "dinosaur show" in extracted_data.get("ticket_type", "").lower(),
                    "dinosaur_show_out": "dinosaur show" in extracted_data.get("ticket_type", "").lower(),
                    "ancient_statues_in": "ancient statues" in extracted_data.get("ticket_type", "").lower(),
                    "ancient_statues_out": "ancient statues" in extracted_data.get("ticket_type", "").lower(),
                    "ice_age_show_in": "ice age show" in extracted_data.get("ticket_type", "").lower(),
                    "ice_age_show_out": "ice age show" in extracted_data.get("ticket_type", "").lower(),
                    "photography": "photography" in extracted_data.get("ticket_type", "").lower(),
                }

                # **Step 3: Ensure ticket generation only happens once**
                try:
                    print(f"Generating tickets for Transaction ID: {transaction_id}")
                    qr_codes = generate_qr(transaction_id, session_key, nationality, adult_count, children_count,
                                           access_details)
                    if not qr_codes:
                        raise ValueError("QR Code generation returned an empty list.")
                except Exception as e:
                    print(f"Error during ticket generation: {e}")
                    return JsonResponse({"reply": "Tickets generation failed after payment."})

                print(f"Tickets successfully generated. QR Codes: {qr_codes}")

                # Prepare the response with QR codes for each category
                qr_code_message = "".join(
                    f"<br/>Here is your ticket QR code (Total: {qr['total_count']}): <img src='{qr['qr_code_url']}' alt='QR Code' style='width:150px;height:150px;' />"
                    for qr in qr_codes
                )
                return JsonResponse({
                    "reply": f"Payment successful! Amount: ₹{transaction.amount}, Transaction ID: {transaction.transaction_id}. Tickets are generated."
                             f"{qr_code_message}",
                    "reply_type": "qr_codes",
                    "qr_codes": qr_codes,  # Include generated QR codes in the response
                })

            print("Transaction not found or failed.")
            return JsonResponse({"reply": "Transaction not found or failed."})

        # Translate user message to English for Rasa
        def translate_user_message():
            nonlocal user_message, translated_user_message
            try:
                translated_user_message = translate_text(user_message, "en")
            except Exception as e:
                print(f"Error translating user message: {e}")
                translated_user_message = user_message

        translated_user_message = None
        translate_user_message()

        payload = {"sender": session_key, "message": translated_user_message}

        try:
            # Send Rasa API request
            response = requests.post(rasa_url, json=payload, timeout=10)
            response.raise_for_status()
            response_data = response.json()

            if response_data:
                bot_reply = response_data[0].get("text", "I didn't understand that.")
                custom_data = response_data[1].get("custom", {})
                reply_type = custom_data.get("reply_type", "unknown")

                # Handle Ask Services and Ticket Type
                if reply_type in ["ask_services", "ticket_type"]:
                    items = []



                    if reply_type == "ask_services":
                        services_and_shows = ServiceAndShows.objects.filter(status="Active", type="service")
                        items = [{"title": service_and_show.name,
                                  "payload": f"I need {service_and_show.name}"} for service_and_show in
                                 services_and_shows]

                        bot_reply = "What kind of service do you need?"


                    elif reply_type == "ticket_type":
                        shows = Show.objects.filter(status="Active")
                        distinct_shows = {show.ticket_name: show for show in shows}.values()
                        items = [{"title": show.ticket_name, "payload": f"I need {show.ticket_name} ticket"} for show in
                                 distinct_shows]
                        bot_reply = "What kind of ticket do you need?"



                    # Threaded translation for bot reply and button titles
                    translated_bot_reply = None
                    translated_titles = [None] * len(items)

                    def translate_bot_reply():
                        nonlocal translated_bot_reply
                        translated_bot_reply = translate_text(bot_reply, selected_language)

                    def translate_buttons():
                        for i, item in enumerate(items):
                            translated_titles[i] = {
                                "title": translate_text(item["title"], selected_language),
                                "payload": item["payload"],
                            }

                    reply_thread = Thread(target=translate_bot_reply)
                    button_thread = Thread(target=translate_buttons)
                    reply_thread.start()
                    button_thread.start()
                    reply_thread.join()
                    button_thread.join()

                    options_text = ", ".join([item["title"] for item in translated_titles])
                    full_audio_text = f"{translated_bot_reply}. Available options are: {options_text}"

                    audio_url = generate_audio(full_audio_text, selected_language, session_key)
                    if audio_url:
                        request.session["current_audio_url"] = audio_url

                    return JsonResponse({
                        "reply": translated_bot_reply,
                        "buttons": translated_titles,
                        "reply_type": reply_type,
                        "audio_url": audio_url,
                    })

                # Handle Confirmation Reply Type
                elif reply_type == "confirmation":
                    pattern = (
                        r"Here are your (?P<nationality>\w+) (?P<adult_count>\d+) adult and "
                        r"(?P<children_count>\d+) children tickets for (?P<ticket_type>.+)\."
                    )
                    match = re.search(pattern, bot_reply)
                    if match:
                        extracted_data = match.groupdict()
                        request.session["extracted_data"] = extracted_data

                    translated_bot_reply, buttons = confirm_details(extracted_data, selected_language)
                    audio_url = generate_audio(translated_bot_reply, selected_language, session_key)
                    if audio_url:
                        request.session["current_audio_url"] = audio_url

                    return JsonResponse({
                        "reply": translated_bot_reply,
                        "buttons": buttons,
                        "reply_type": reply_type,
                        "data": extracted_data,
                        "audio_url": audio_url,
                    })


                elif reply_type == "nationality":
                    # Bot reply for selecting nationality
                    bot_reply = "Are you Indian or Foreigner"

                    # Buttons for nationality
                    buttons = [
                        {"title": "Indian", "payload": "/select_nationality_indian"},
                        {"title": "Foreigner", "payload": "/select_nationality_foreigner"}
                    ]

                    # Optionally generate audio for the reply
                    audio_url = generate_audio(bot_reply, selected_language, session_key)
                    if audio_url:
                        request.session["current_audio_url"] = audio_url

                    return JsonResponse({
                        "reply": bot_reply,
                        "buttons": buttons,
                        "reply_type": reply_type,
                        "audio_url": audio_url,
                    })


        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Rasa: {e}")
            bot_reply = "Error: Could not connect to the bot server."

        translated_bot_reply = translate_text(bot_reply, selected_language)
        audio_url = generate_audio(translated_bot_reply, selected_language, session_key)
        if audio_url:
            request.session["current_audio_url"] = audio_url

        return JsonResponse({
            "reply": translated_bot_reply,
            "reply_type": reply_type,
            "audio_url": audio_url,
        })

    return JsonResponse({"reply": "Invalid request."}, status=400)




def qrmodaldisplay(request):
    if request.method == 'POST':
        # Get the session_id from the request body
        data = json.loads(request.body)
        session_id = data.get('session_id')

        if not session_id:
            return JsonResponse({"message": "Session ID not provided."}, status=400)

        # Query the Ticket model to find tickets associated with this session_id
        tickets = Ticket.objects.filter(session_id=session_id)

        if not tickets.exists():
            return JsonResponse({"message": "No tickets found for this session."}, status=404)

        # Prepare QR code data and calculate totals
        qr_codes = []
        total_adult_count = 0
        total_child_count = 0
        total_tickets = 0

        for ticket in tickets:
            # Check if QR code exists and add details
            if ticket.qr_code:
                qr_codes.append({
                    "qr_code_url": ticket.qr_code.url,  # Assuming qr_code is an ImageField
                    "adult_count": ticket.adult_count,
                    "child_count": ticket.child_count,
                    "total_tickets": ticket.adult_count + ticket.child_count,
                })
                # Sum up the total adult and child counts
                total_adult_count += ticket.adult_count
                total_child_count += ticket.child_count
                total_tickets += ticket.adult_count + ticket.child_count
            else:
                # If QR code is missing for a ticket, log the issue for debugging
                print(f"No QR code found for Ticket ID: {ticket.id}")  # Debugging line for missing QR code

        # Return the QR codes along with total counts
        return JsonResponse({
            "qr_codes": qr_codes,
            "total_adult_count": total_adult_count,
            "total_child_count": total_child_count,
            "total_tickets": total_tickets
        })

    # If the request method is not POST, return an error response
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

                # Dynamically get the boolean field (e.g., entry_in, dinosaur_show_in)
                if hasattr(ticket, ticket_type) and isinstance(getattr(ticket, ticket_type), bool):
                    # Check the current status of the field
                    if getattr(ticket, ticket_type, False):  # If it's True, gate opens
                        # Open the gate (perform your action here, like updating status)
                        # Then set the corresponding boolean field to False (0)
                        setattr(ticket, ticket_type, False)
                        ticket.save()  # Save the changes to the ticket
                        return JsonResponse({"status": "success", "message": "Gate Opened and Entry Marked"})
                    else:
                        return JsonResponse({"status": "failure", "message": "Gate is already closed"})
                else:
                    return JsonResponse({"status": "error", "message": f"Invalid ticket type {ticket_type}"})

            except Ticket.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Ticket not found"})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON input"})
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"})


