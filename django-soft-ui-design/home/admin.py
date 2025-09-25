from django.contrib import admin
import matplotlib
from django.contrib.admin import DateFieldListFilter

matplotlib.use('Agg')  # Use non-interactive backend
from .models import Ticket, Pass, TicketLog, Show, Tag, PaymentDetails, FakeTransaction, Income, ServiceAndShows, Feedback
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.db.models import Count, Sum
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import path
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.http import JsonResponse
import matplotlib.pyplot as plt
import io
import base64
from django.utils.safestring import mark_safe
import calendar
from datetime import datetime
from django.db.models.functions import TruncMonth
from django.db import models  # Import models here
from .models import Income, Museum


def generate_chart(x, y, title="Chart", x_label="X-axis", y_label="Y-axis"):
    """
    Generate a bar chart with values displayed on the bars.
    """
    import matplotlib.pyplot as plt
    import io
    import base64

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(6, 4))

    # Create the bar chart
    bars = ax.bar(x, y, color="skyblue")

    # Add values on top of the bars
    for bar in bars:
        yval = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            yval,
            f"{yval:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
            color="black"
        )

    # Set chart title and labels
    ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    plt.tight_layout()

    # Save the chart to a PNG image in memory
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()

    # Encode the image to base64 for rendering in HTML
    return base64.b64encode(image_png).decode("utf-8")


@admin.register(Pass)
class PassAdmin(admin.ModelAdmin):
    list_display = ('name', 'staff_id', 'category', 'status', 'qr_code_preview')  # Show Staff ID in the list
    readonly_fields = ('qr_code', 'qr_code_uuid')  # Prevent editing QR code fields
    search_fields = ('name', 'staff_id')  # Allow searching by name and staff ID
    list_filter = ('category', 'status')  # Allow filtering by category and status

    def qr_code_preview(self, obj):
        """Display QR code in the admin."""
        if obj.qr_code:
            return format_html('<img src="{}" width="100" height="100" />', obj.qr_code.url)
        return "No QR Code"

    qr_code_preview.short_description = "QR Code"

@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_name', 'location','museum_name','ticket_age', 'nationality', 'price', 'discount_percent',
        'is_discount_active', 'discount_dropdown', 'final_price', 'status', 'show_tag', 'toggle_status'
    )
    list_filter = ('ticket_age', 'nationality', 'status', 'service_tags', 'is_discount_active','museum_name')
    search_fields = ('ticket_name', 'description')
    ordering = ('ticket_name', 'status')
    filter_horizontal = ('service_tags',)
    fieldsets = (
        (None, {
            'fields': (
                'ticket_name', 'ticket_age', 'nationality', 'price', 'discount_percent',
                'is_discount_active', 'description', 'status', 'service_tags' ,'location'
            )
        }),
    )

    def discount_dropdown(self, obj):
        """
        Render a dropdown for toggling the discount status.
        """
        active_url = reverse("admin:toggle_show_field_status", args=[obj.pk, "is_discount_active", "True"])
        inactive_url = reverse("admin:toggle_show_field_status", args=[obj.pk, "is_discount_active", "False"])

        return format_html(
            """
            <select onchange="toggleDiscount(this.value)">
                <option value="{}" {}>Active</option>
                <option value="{}" {}>Inactive</option>
            </select>
            <script>
                function toggleDiscount(url) {{
                    fetch(url, {{
                        method: 'POST',
                        headers: {{
                            'X-CSRFToken': '{}',
                            'Content-Type': 'application/json'
                        }}
                    }})
                    .then(response => {{
                        if (response.ok) {{
                            location.reload();
                        }} else {{
                            alert('Failed to toggle discount status!');
                        }}
                    }})
                    .catch(() => alert('Failed to toggle discount status!'));
                }}
            </script>
            """,
            active_url,
            'selected' if obj.is_discount_active else '',
            inactive_url,
            'selected' if not obj.is_discount_active else '',
            "{{ csrf_token }}"
        )

    #discount_dropdown.short_description = "Discount Status"

    def toggle_status(self, obj):
        """
        Render toggle buttons in the admin list view for updating the status.
        """
        active_url = reverse("admin:toggle_show_field_status", args=[obj.pk, "status", "Active"])
        inactive_url = reverse("admin:toggle_show_field_status", args=[obj.pk, "status", "Not Active"])

        return format_html(
            """
            <div style="display: flex; gap: 10px;">
                <button
                    class="btn btn-sm btn-success"
                    onclick="event.preventDefault(); toggleStatus('{}')"
                    style="{}">Activate</button>
                <button
                    class="btn btn-sm btn-danger"
                    onclick="event.preventDefault(); toggleStatus('{}')"
                    style="{}">Deactivate</button>
            </div>
            <script>
                function toggleStatus(url) {{
                    fetch(url, {{
                        method: 'POST',
                        headers: {{
                            'X-CSRFToken': '{}',
                            'Content-Type': 'application/json'
                        }}
                    }})
                    .then(response => {{
                        if (response.ok) {{
                            location.reload();
                        }} else {{
                            alert('Failed to toggle status!');
                        }}
                    }})
                    .catch(() => alert('Failed to toggle status!'));
                }}
            </script>
            """,
            active_url,
            "display: none;" if obj.status == "Active" else "",
            inactive_url,
            "display: none;" if obj.status == "Not Active" else "",
            "{{ csrf_token }}"
        )

    #toggle_status.short_description = "Toggle Status"

    @method_decorator(csrf_exempt)
    def toggle_show_field_status_view(self, request, pk, field, new_status):
        """
        Handle AJAX requests to toggle a field's status for a Show instance.
        Supports toggling of 'status' and 'is_discount_active'.
        """
        if request.method != "POST":
            return JsonResponse({"error": "Only POST requests are allowed."}, status=405)

        # Fetch the show object using the primary key
        show = get_object_or_404(Show, pk=pk)

        # Define the allowed fields for toggling
        allowed_fields = ["status", "is_discount_active"]

        # Ensure the field is toggleable
        if field not in allowed_fields:
            return JsonResponse({"error": f"Field '{field}' is not toggleable."}, status=400)

        # Validate and update the field
        if field == "status" and new_status not in ["Active", "Not Active"]:
            return JsonResponse({"error": f"Invalid status value for '{field}'."}, status=400)
        if field == "is_discount_active" and new_status not in ["True", "False"]:
            return JsonResponse({"error": f"Invalid status value for '{field}'."}, status=400)

        # Set the field value dynamically
        setattr(show, field, new_status == "True" if field == "is_discount_active" else new_status)

        # Save the updated instance
        show.save()

        return JsonResponse({"success": True, "field": field, "new_status": getattr(show, field)})

    def get_urls(self):
        """
        Extend admin URLs to include custom endpoints for toggling fields.
        """
        urls = super().get_urls()
        custom_urls = [
            path(
                "toggle-status/<int:pk>/<str:field>/<str:new_status>/",
                self.admin_site.admin_view(self.toggle_show_field_status_view),
                name="toggle_show_field_status",
            ),
        ]
        return custom_urls + urls

    # Custom Changelist View for Status Counts
    def changelist_view(self, request, extra_context=None):
        """
        Display cards showing the number of Active and Not Active shows.
        """
        active_count = Show.objects.filter(status="Active").count()
        not_active_count = Show.objects.filter(status="Not Active").count()

        extra_context = extra_context or {}
        extra_context["is_show"] = True
        extra_context["active_count"] = active_count
        extra_context["not_active_count"] = not_active_count

        return super().changelist_view(request, extra_context=extra_context)

    # Custom Changelist View for Location Toggle
    def location_toggle(self, obj):
        """
        Render toggle buttons for the location based on the Museum locations.
        """
        locations = Museum.objects.values_list('location', flat=True).distinct()

        buttons_html = ""
        for location in locations:
            location_url = reverse("admin:toggle_show_field_status", args=[obj.pk, "location", location])
            buttons_html += format_html(
                """
                <button
                    class="btn btn-sm btn-info"
                    onclick="event.preventDefault(); toggleLocation('{}')"
                    style="{}">{}</button>
                """,
                location_url,
                "display: none;" if obj.location == location else "",
                location
            )

        return format_html(
            """
            <div style="display: flex; gap: 10px;">
                {buttons_html}
            </div>
            <script>
                function toggleLocation(url) {{
                    fetch(url, {{
                        method: 'POST',
                        headers: {{
                            'X-CSRFToken': '{}',
                            'Content-Type': 'application/json'
                        }}
                    }})
                    .then(response => {{
                        if (response.ok) {{
                            location.reload();
                        }} else {{
                            alert('Failed to toggle location!');
                        }}
                    }})
                    .catch(() => alert('Failed to toggle location!'));
                }}
            </script>
            """,
            buttons_html,
            "{{ csrf_token }}"
        )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)

@admin.register(ServiceAndShows)
class ServiceAndShowsAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'status', 'ticket_limit', 'title_image', 'other_images')  # Add image fields to the list display
    list_filter = ('type', 'status', 'service_tags')  # Add filter options on the sidebar for easy filtering
    search_fields = ('name', 'description')  # Enable search functionality by name and description
    ordering = ('name', 'status')  # Default ordering in the admin list
    filter_horizontal = ('service_tags',)  # For many-to-many relationships to show a better UI for selecting tags
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'type', 'status', 'title_image', 'other_images', 'service_tags', 'ticket_limit')  # Include all fields
        }),
    )  # Show all fields without additional sections



@admin.register(PaymentDetails)
class PaymentDetailsAdmin(admin.ModelAdmin):
    list_display = ("upi_id", "phone_number", "name", "bank_name", "status")
    fields = ("upi_id", "phone_number", "name", "bank_name", "status")

    def has_add_permission(self, request):
        # Restrict adding more than one entry
        if PaymentDetails.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "session_id",
        "nationality",
        'user',
        "adult_count",  # Replaced age_category with adult_count
        "child_count",  # Added child_count
        "total_count",  # Added total_count
        "transaction_id",
        "transaction_at",
        "qr_code_display",  # This should reference a valid method
        "qr_code_uuid",
        "ticket_amount",
        "entry_in",
        "entry_out",
        "entry_t",
        "dinosaur_show_in",
        "dinosaur_show_out",
        "dinosaur_t",
        "ancient_statues_in",
        "ancient_statues_out",
        "ancient_t",
        "ice_age_show_in",
        "ice_age_show_out",
        "ice_age_t",
        "photography",
        "photography_t",
    )
    list_filter = ("nationality", "transaction_at", "photography",'user')
    search_fields = ("session_id", "transaction_id",'user')

    def qr_code_display(self, obj):
        """
        Returns the QR code as an image tag in the admin table.
        """
        if hasattr(obj, "qr_code") and obj.qr_code:
            return format_html('<img src="{}" alt="QR Code" style="width: 50px; height: 50px;" />', obj.qr_code.url)
        return "No QR Code"

    qr_code_display.short_description = "QR Code"  # Label for the admin column




@admin.register(FakeTransaction)
class FakeTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "amount",
        "sender",
        "status",
        "created_at",
    )  # Columns displayed in the admin list view
    list_filter = ("status", "created_at")  # Filters in the admin sidebar
    search_fields = ("transaction_id", "sender")  # Searchable fields
    readonly_fields = ("transaction_id", "created_at")  # Read-only fields
    ordering = ("-created_at",)  # Default ordering (most recent first)

    def has_add_permission(self, request):
        return False


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("income_id", "transaction_id", "sender", "amount", "date_received", "session_id", "booking_type")
    list_filter = (("date_received", DateFieldListFilter), "booking_type")
    search_fields = ("transaction_id", "sender", "session_id")

    def changelist_view(self, request, extra_context=None):
        queryset = self.get_queryset(request)

        # Calculate total income
        total_amount = queryset.aggregate(total=Sum("amount"))["total"] or 0

        # Apply date range filtering if specified
        date_from = request.GET.get("date_received__gte")
        date_to = request.GET.get("date_received__lte")

        filtered_queryset = queryset
        if date_from:
            filtered_queryset = filtered_queryset.filter(date_received__gte=date_from)
        if date_to:
            filtered_queryset = filtered_queryset.filter(date_received__lte=date_to)

        filtered_total = filtered_queryset.aggregate(total=Sum("amount"))["total"] or 0

        # Calculate totals by booking type
        data_by_category = (
            filtered_queryset.values_list("booking_type")  # Use values_list to get tuples
            .annotate(total=Sum("amount"))
            .order_by("booking_type")
        )
        # Calculate average performance
        total_categories = len(data_by_category)
        average_performance = (100 / total_categories) if total_categories > 0 else 0

        # Flatten data and calculate performance
        booking_type_totals = []
        for booking_type, total in data_by_category:
            performance = (total / total_amount * 100) if total_amount > 0 else 0
            is_above_average = performance >= average_performance  # Compare to average
            booking_type_totals.append((booking_type, total, performance, is_above_average))

        # Generate the graph for booking types
        categories = [item[0] for item in booking_type_totals]  # Booking type names
        values = [item[1] for item in booking_type_totals]  # Corresponding totals

        booking_type_chart = generate_chart(
            x=categories,
            y=values,
            title="Total Amount by Booking Type",
            x_label="Booking Type",
            y_label="Total Amount (₹)"
        )
        booking_type_graph_html = f'<img src="data:image/png;base64,{booking_type_chart}" alt="Graph">'

        # Calculate month-wise income
        month_data = (
            filtered_queryset.annotate(month=TruncMonth("date_received"))
            .values_list("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        month_names = [calendar.month_name[entry[0].month] for entry in month_data]
        month_values = [entry[1] for entry in month_data]

        # Generate the month-wise income graph
        month_chart = generate_chart(
            x=month_names,
            y=month_values,
            title="Month-wise Income",
            x_label="Month",
            y_label="Income (₹)"
        )
        month_graph_html = f'<img src="data:image/png;base64,{month_chart}" alt="Graph">'

        # Calculate the highest income month
        highest_month_name = "N/A"
        highest_month_income = 0
        if month_data:
            highest_month = max(month_data, key=lambda x: x[1])
            highest_month_name = calendar.month_name[highest_month[0].month]
            highest_month_income = highest_month[1]

        # Calculate the current month's performance
        current_month = datetime.now().month
        current_month_income = next(
            (entry[1] for entry in month_data if entry[0].month == current_month), 0
        )
        previous_month_income = next(
            (entry[1] for entry in month_data if entry[0].month == current_month - 1), 0
        )
        performance_change = (
            ((current_month_income - previous_month_income) / previous_month_income * 100)
            if previous_month_income > 0
            else 0
        )

        # Prepare data for template context
        extra_context = extra_context or {}
        extra_context.update({
            "is_income": True,
            "total_amount": total_amount,
            "filtered_total": filtered_total,
            "booking_type_totals": booking_type_totals,  # List of tuples
            "booking_type_graph_html": mark_safe(booking_type_graph_html),
            "month_graph_html": mark_safe(month_graph_html),
            "highest_month_name": highest_month_name,
            "highest_month_income": highest_month_income,
            "current_month_income": current_month_income,
            "performance_change": performance_change,
        })

        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'send_from', 'created_at', 'ratings', 'phone_number')
    list_filter = ('send_from', 'ratings')
    search_fields = ('session_id', 'message', 'phone_number')
    ordering = ('-created_at',)
    fields = ('session_id', 'message', 'send_from', 'ratings', 'phone_number', 'created_at')
    readonly_fields = ('created_at',)  # Don't allow editing of the creation time
# Register other models


@admin.register(Museum)  # This is the decorator to register the model with Django admin
class MuseumAdmin(admin.ModelAdmin):
    list_display = ('museum_name', 'location', 'status', 'open_time', 'close_time', 'tags')
    list_filter = ('status', 'tags')
    search_fields = ('museum_name', 'location', 'tags')
    ordering = ('museum_name',)
    fieldsets = (
        (None, {
            'fields': ('museum_name', 'location', 'status', 'tags')
        }),
        ('Operating Hours', {
            'fields': ('open_time', 'close_time')
        }),
    )

admin.site.register(TicketLog)

