from django.db import models
import uuid
from PIL import Image, ImageDraw
import qrcode
from django.utils.timezone import now
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError


def generate_unique_id():
    """Generates a unique 24-character alphanumeric ID."""
    return uuid.uuid4().hex[:24]

class Tag(models.Model):

    name = models.CharField(max_length=50, unique=True, verbose_name="Tag Name")

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Ticket(models.Model):
    SESSION_NATIONALITY_CHOICES = [
        ("Indian", "Indian"),
        ("Foreigner", "Foreigner"),
    ]

    # Removed AGE_CATEGORY_CHOICES as per your request

    session_id = models.CharField(max_length=400, editable=False)
    user = models.CharField(max_length=400, editable=False)
    nationality = models.CharField(max_length=20, choices=SESSION_NATIONALITY_CHOICES)
    adult_count = models.PositiveIntegerField(default=0)  # Number of adults
    child_count = models.PositiveIntegerField(default=0)  # Number of children
    total_count = models.PositiveIntegerField(default=0)  # Total count (sum of adults and children)
    qr_code = models.ImageField(upload_to="qr_codes/", null=True, blank=True)
    qr_code_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100)
    transaction_at = models.DateTimeField(default=now)
    ticket_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Access Booleans
    entry_in = models.BooleanField(default=False)
    entry_out = models.BooleanField(default=False)
    dinosaur_show_in = models.BooleanField(default=False)
    dinosaur_show_out = models.BooleanField(default=False)
    ancient_statues_in = models.BooleanField(default=False)
    ancient_statues_out = models.BooleanField(default=False)
    ice_age_show_in = models.BooleanField(default=False)
    ice_age_show_out = models.BooleanField(default=False)
    photography = models.BooleanField(default=False)

    # New columns as booleans to represent whether the activity has happened
    entry_t = models.BooleanField(default=False)
    dinosaur_t = models.BooleanField(default=False)
    ancient_t = models.BooleanField(default=False)
    ice_age_t = models.BooleanField(default=False)
    photography_t = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Automatically update total_count when saving the ticket
        self.total_count = self.adult_count + self.child_count
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket {self.nationality} (Adults: {self.adult_count}, Children: {self.child_count}) - Session {self.session_id} - Amount: ₹{self.ticket_amount}"



class Pass(models.Model):
    CATEGORY_CHOICES = [
        ("Staff", "Staff"),
        ("Guest", "Guest"),
        ("Official", "Official"),
    ]

    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Not Active", "Not Active"),
        ("Blocked", "Blocked"),
    ]

    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    staff_id = models.CharField(max_length=50, null=True, blank=True,unique=True)  # Optional for guests
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Active")
    qr_code = models.ImageField(upload_to="qr_code_pass/", null=True, blank=True)  # Store QR code image in `qr_code_pass/`
    qr_code_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # Unique ID for the pass

    def save(self, *args, **kwargs):
        # Generate QR code when creating/updating the pass
        if not self.qr_code:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )

            # QR code data for the pass
            qr_data = f"ps-{self.qr_code_uuid}"
            qr.add_data(qr_data)
            qr.make(fit=True)

            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")

            # Save the image to the `qr_code` field
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            file_name = f"qr_code_pass_{self.qr_code_uuid}.png"  # Ensure the file is saved in the correct directory
            self.qr_code.save(file_name, ContentFile(buffer.read()), save=False)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pass {self.name} ({self.category})"




class TicketLog(models.Model):
    TICKET_CATEGORY_CHOICES = [
        ("Booking", "Booking"),
        ("Pass", "Pass"),
    ]

    ticket_category = models.CharField(max_length=20, choices=TICKET_CATEGORY_CHOICES)
    location = models.CharField(max_length=100)
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.ticket_category} at {self.location} - {self.time}"


class Show(models.Model):
    TICKET_AGE_CHOICES = [
        ("Adult", "Adult"),
        ("Child", "Child"),
    ]

    NATIONALITY_CHOICES = [
        ("Indian", "Indian"),
        ("Foreigner", "Foreigner"),
    ]

    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Not Active", "Not Active"),
    ]

    # Fields
    service_tags = models.ManyToManyField(Tag, related_name="shows", blank=True)

    ticket_name = models.CharField(max_length=100, verbose_name="Ticket Name")
    ticket_age = models.CharField(
        max_length=10,
        choices=TICKET_AGE_CHOICES,
    )
    nationality = models.CharField(
        max_length=20,
        choices=NATIONALITY_CHOICES,
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,


    )
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,

        help_text="Enter the discount percentage (e.g., 10.00 for 10%)",
    )
    is_discount_active = models.BooleanField(
        default=False,

        help_text="Enable or disable the discount for this show",
    )
    description = models.TextField(

        help_text="Provide a brief description of the show",
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Active",

    )

    # Static location choices (initially empty, but can be filled during runtime)
    location = models.CharField(
        max_length=255,
        blank=True,

    )
    museum_name = models.CharField(
        max_length=255,
        blank=True,

    )

    # Metadata
    class Meta:
        verbose_name = "Show"
        verbose_name_plural = "Shows"
        ordering = ["ticket_name", "ticket_age", "nationality"]

    def __str__(self):
        return f"{self.ticket_name} - {self.get_ticket_age_display()} ({self.get_nationality_display()})"

    def show_tag(self):
        """Returns a string representation of all associated tags"""
        return ", ".join([tag.name for tag in self.service_tags.all()])

    show_tag.short_description = "Tags"

    def final_price(self):
        """Calculate the price after applying discount."""
        if self.is_discount_active and self.discount_percent > 0:
            return self.price - (self.price * (self.discount_percent / 100))
        return self.price

        # Method to set location dynamically during the save process
    def save(self, *args, **kwargs):
        # Dynamically set the location to one of the available locations from the Museum model
        if not self.location:  # If location is not manually set, assign one from the Museum
            from .models import Museum  # Import Museum model here
            distinct_locations = Museum.objects.values_list('location', flat=True).distinct()
            if distinct_locations:
                self.location = distinct_locations[0]  # Set the first available location (can be modified)

        super().save(*args, **kwargs)

    final_price.short_description = "Final Price"




class ServiceAndShows(models.Model):
    TYPE_CHOICES = [
        ("service", "Service"),
        ("show", "Show"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Not Active", "Not Active"),
    ]
    TAG_CHOICES = [
        ("help", "Help"),
        ("transport", "Transport"),
        ("food", "Food"),
        ("purchase", "Purchase"),
        ("buy", "Buy"),
        ("assistance", "Assistance"),
        ("stories", "Stories"),
        ("infos", "Information"),
    ]

    # Fields
    name = models.CharField(max_length=100, verbose_name="Name")
    description = models.TextField(verbose_name="Description", help_text="Provide details about the service or show")
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="service",
        verbose_name="Type",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Active",
        verbose_name="Status",
    )
    service_tags = models.ManyToManyField(
        "Tag",
        blank=True,
        verbose_name="Tags",
        help_text="Select tags related to this service or show",
    )
    ticket_limit = models.IntegerField(
        null=True, blank=True, verbose_name="Ticket Limit", help_text="Leave empty for services"
    )
    title_image = models.ImageField(
        upload_to='service_and_shows/title_images/',
        null=True,
        blank=True,
        verbose_name="Title Image",
        help_text="Upload the main title image for the service/show"
    )
    other_images = models.ImageField(
        upload_to='service_and_shows/other_images/',
        null=True,
        blank=True,
        verbose_name="Other Images",
        help_text="Upload any other images related to this service/show"
    )

    # Metadata
    class Meta:
        verbose_name = "Service and Show"
        verbose_name_plural = "Services and Shows"
        ordering = ["name", "status"]

    # String representation
    def __str__(self):
        return self.name





class PaymentDetails(models.Model):
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Not Active", "Not Active"),
    ]

    upi_id = models.CharField(max_length=100, verbose_name="UPI ID")
    phone_number = models.CharField(max_length=15, verbose_name="Phone Number")
    name = models.CharField(max_length=100, verbose_name="Name")
    bank_name = models.CharField(max_length=100, verbose_name="Bank Name")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        verbose_name="Status",
        default="Active"
    )

    def save(self, *args, **kwargs):
        if PaymentDetails.objects.exists() and not self.pk:
            raise ValidationError("You can only create one instance of PaymentDetails.")
        super(PaymentDetails, self).save(*args, **kwargs)

    def __str__(self):
        return f"Payment Details ({self.name})"

    class Meta:
        verbose_name = "Payment Detail"
        verbose_name_plural = "Payment Details"


class FakeTransaction(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    sender = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=[("Success", "Success"), ("Failed", "Failed")])
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.status}"

class Income(models.Model):
    """
    Model to track income from online payments.
    """
    income_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    transaction_id = models.CharField(max_length=50, unique=True, verbose_name="Transaction ID")
    sender = models.CharField(max_length=100, verbose_name="Sender")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Amount")
    date_received = models.DateTimeField(default=now, verbose_name="Date Received")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    session_id = models.CharField(max_length=100, verbose_name="Session ID")  # New field for session ID
    booking_type = models.CharField(
        max_length=20,
        choices=[("Chatbot", "Chatbot"), ("Web", "Web"), ("Counter", "Counter")],
        default="Chatbot",
        verbose_name="Booking Type"
    )  # New field for booking type

    def __str__(self):
        return f"Income #{self.income_id} - ₹{self.amount}"

    class Meta:
        verbose_name = "Income"
        verbose_name_plural = "Income"
        ordering = ["-date_received"]  # Order by most recent income first


class Feedback(models.Model):
    session_id = models.CharField(max_length=255, null=False, blank=False)
    message = models.TextField(null=False, blank=True)
    send_from = models.CharField(max_length=20, choices=[('chatbot', 'Chatbot'), ('forms', 'Forms')], default='chatbot')
    created_at = models.DateTimeField(auto_now_add=True)
    ratings = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], null=False)
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"Feedback from {self.session_id} on {self.created_at}"

    class Meta:
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedbacks'
        ordering = ['-created_at']  # Newest feedback comes first


class Museum(models.Model):
    MUSEUM_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    museum_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=MUSEUM_STATUS_CHOICES, default='active')
    tags = models.CharField(max_length=255, blank=True, null=True)
    open_time = models.TimeField()
    close_time = models.TimeField()

    def __str__(self):
        return self.museum_name


