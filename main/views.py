from django.shortcuts import render,redirect
from .models import GalleryCategory,GalleryImage,Event,Booking,EmailSubscription
from django.utils import timezone
from django.core.mail import send_mail
from . form import BookingForm
from django.db import IntegrityError

import io
import qrcode
from django.http import JsonResponse,HttpResponse,FileResponse
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics


# Create your views here.

def home(request):
    
    images = GalleryImage.objects.all()
    categories=GalleryCategory.objects.all()
    # Fetch all active upcoming events
    upcoming_events = Event.objects.filter(is_active=True, date__gte=timezone.now()).order_by('date')

    # Fetch the most upcoming event (if any)
    most_upcoming_event = upcoming_events.first() if upcoming_events else None

    # Pass the events and the most upcoming event to the template
    context={'images':images,'categories':categories,'events': upcoming_events,
        'most_upcoming_event': most_upcoming_event,
        'most_upcoming_event_date': most_upcoming_event.date if most_upcoming_event else None}

    return render(request, 'home.html',context)

def about(request):
    return render(request, 'about.html', {})

def location(request):
    return render(request, 'location.html', {})

def gallery(request):
    return render(request, 'gallery.html', {})

def contact(request):
    return render(request, 'contact.html', {})

from django.http import JsonResponse

def event_list(request):
    # Fetch all active upcoming events
    upcoming_events = Event.objects.filter(is_active=True, date__gte=timezone.now()).order_by('date')

    # Fetch the most upcoming event (if any)
    most_upcoming_event = upcoming_events.first() if upcoming_events else None

    # Pass the events and the most upcoming event to the template
    context = {
        'events': upcoming_events,
        'most_upcoming_event': most_upcoming_event,
        'most_upcoming_event_date': most_upcoming_event.date if most_upcoming_event else None
    }
    
    return render(request, 'event.html', context)
def generate_custom_ticket_pdf(booking, event):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(letter[0] * 2/3, letter[1] * 1/4))  # Adjust size according to your ticket template

    # Load the ticket template image
    template_image_path = "static/images/Beige Modern Boarding Pass Ticket.png"
    c.drawImage(template_image_path, 0, 0, width=letter[0] * 2/3, height=letter[1] * 1/4)

    # Register artistic fonts
    pdfmetrics.registerFont(TTFont('Lobster', 'static/fonts/Lobster-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('DancingScript', 'static/fonts/DancingScript-Regular.ttf'))

    # Define gold color
    gold_color = HexColor('#FFD700')

    # Add text to the template
    c.setFont("Lobster", 24)
    c.setFillColor(gold_color)
    c.drawString(100, 170, f"{event.title.upper()}")  # Position for Event Title
    c.setFont("DancingScript", 8)
    c.drawString(30, 110, f"NAME: {booking.name} ")  # Position for Name
    c.drawString(30, 90, f"PHONE NUMBER: {booking.phone_number}")  # Position for Phone Number
    c.drawString(30, 70, f"EMAIL: {booking.email}")  # Position for Email

    

    # Generate and add QR code
    qr = qrcode.QRCode(box_size=2)
    qr.add_data(f"Booking ID: {booking.id}")
    qr.make(fit=True)
    img_qr = qr.make_image(fill="black", back_color="white")
    qr_buffer = io.BytesIO()
    img_qr.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    qr_image = ImageReader(qr_buffer)
    c.drawImage(qr_image, 320, 60, width=60, height=60)  # Position for QR Code

    # Finalize the PDF
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.getvalue()

def book_event(request, event_id):
    event = Event.objects.get(id=event_id)
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.event = event
            try:
                booking.save()

                # Save email to Subscription model
                subscription, created = EmailSubscription.objects.get_or_create(email=booking.email)

                # Create PDF
                pdf_content = generate_custom_ticket_pdf(booking, event)

                # Send email with PDF attachment
                email_subject = 'Your Booking Confirmation and Ticket'
                email_body = render_to_string('booking_confirmation_email.html', {'event': event, 'booking': booking})
                email = EmailMessage(
                    email_subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [booking.email],
                )
                email.attach(f"Booking_{booking.id}.pdf", pdf_content, "application/pdf")
                email.send()

                # Return a JSON response with a success message
                return HttpResponse("Success", content_type="text/plain")

            except IntegrityError:
                # Return JSON response indicating a duplicate entry
                return JsonResponse({"error": "This email or phone number has already been used for booking."}, status=400)

        # If the form is invalid, return a 400 error
        return JsonResponse({"error": "There was an error with your booking. Please try again."}, status=400)

    # If it's not a POST request, return a 400 error
    return JsonResponse({"error": "Invalid request method."}, status=400)