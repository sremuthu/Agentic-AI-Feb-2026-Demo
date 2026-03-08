"""Booking tools — mock PMS integration for room availability, reservations."""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool

from hotel_agent.knowledge.hotel_data import BOOKINGS, ROOMS, next_booking_id


@tool
def check_availability(room_type: str, check_in: str, check_out: str) -> str:
    """Check room availability for a given type and date range.

    Args:
        room_type: Room type key (standard, deluxe, premium_suite, family_suite, penthouse, accessible).
        check_in: Check-in date as YYYY-MM-DD.
        check_out: Check-out date as YYYY-MM-DD.
    """
    room_type = room_type.lower().replace(" ", "_")
    room = ROOMS.get(room_type)
    if not room:
        available_types = ", ".join(ROOMS.keys())
        return f"Unknown room type '{room_type}'. Available types: {available_types}"

    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."

    if co <= ci:
        return "Check-out must be after check-in."

    nights = (co - ci).days
    total = room["price_per_night"] * nights

    # Simulate: count overlapping bookings for this room type
    booked = sum(
        1 for b in BOOKINGS.values()
        if b["room_type"] == room_type and b["status"] in ("confirmed", "checked_in")
    )
    available_count = room["total_inventory"] - booked

    if available_count <= 0:
        return (
            f"Sorry, no {room['room_type']} rooms are available for "
            f"{check_in} to {check_out}. Please try different dates or another room type."
        )

    return (
        f"Available: {room['room_type']}\n"
        f"Dates: {check_in} to {check_out} ({nights} night{'s' if nights > 1 else ''})\n"
        f"Price: ${room['price_per_night']:.0f}/night — Total: ${total:.2f}\n"
        f"Max guests: {room['max_guests']}\n"
        f"Amenities: {', '.join(room['amenities'])}\n"
        f"Rooms remaining: {available_count}"
    )


@tool
def create_booking(guest_name: str, room_type: str, check_in: str, check_out: str) -> str:
    """Create a new reservation.

    Args:
        guest_name: Full name of the guest.
        room_type: Room type key.
        check_in: Check-in date YYYY-MM-DD.
        check_out: Check-out date YYYY-MM-DD.
    """
    room_type = room_type.lower().replace(" ", "_")
    room = ROOMS.get(room_type)
    if not room:
        return f"Unknown room type '{room_type}'."

    try:
        ci = datetime.strptime(check_in, "%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d")
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."

    nights = (co - ci).days
    if nights <= 0:
        return "Check-out must be after check-in."

    total = room["price_per_night"] * nights
    booking_id = next_booking_id()

    booking = {
        "booking_id": booking_id,
        "guest_name": guest_name,
        "room_type": room_type,
        "check_in": check_in,
        "check_out": check_out,
        "total_cost": total,
        "status": "confirmed",
    }
    BOOKINGS[booking_id] = booking

    return (
        f"Booking confirmed!\n"
        f"Booking ID: {booking_id}\n"
        f"Guest: {guest_name}\n"
        f"Room: {room['room_type']}\n"
        f"Dates: {check_in} to {check_out} ({nights} nights)\n"
        f"Total: ${total:.2f}\n"
        f"Status: Confirmed\n\n"
        f"Free cancellation up to 48 hours before check-in."
    )


@tool
def cancel_booking(booking_id: str) -> str:
    """Cancel an existing booking.

    Args:
        booking_id: The booking ID (e.g. BK-1001).
    """
    booking = BOOKINGS.get(booking_id)
    if not booking:
        return f"Booking '{booking_id}' not found. Please verify the booking ID."

    if booking["status"] == "cancelled":
        return f"Booking {booking_id} is already cancelled."

    if booking["status"] == "checked_in":
        return f"Booking {booking_id} has already been checked in and cannot be cancelled online. Please contact the front desk."

    booking["status"] = "cancelled"
    return (
        f"Booking {booking_id} has been cancelled.\n"
        f"Guest: {booking['guest_name']}\n"
        f"Room: {booking['room_type']}\n"
        f"Dates: {booking['check_in']} to {booking['check_out']}\n\n"
        f"Refund of ${booking['total_cost']:.2f} will be processed within 5-7 business days "
        f"(subject to the 48-hour cancellation policy)."
    )


@tool
def modify_booking(booking_id: str, new_check_in: str = "", new_check_out: str = "", new_room_type: str = "") -> str:
    """Modify an existing booking's dates or room type.

    Args:
        booking_id: The booking ID.
        new_check_in: New check-in date (YYYY-MM-DD), or empty to keep current.
        new_check_out: New check-out date (YYYY-MM-DD), or empty to keep current.
        new_room_type: New room type key, or empty to keep current.
    """
    booking = BOOKINGS.get(booking_id)
    if not booking:
        return f"Booking '{booking_id}' not found."

    if booking["status"] not in ("confirmed",):
        return f"Booking {booking_id} (status: {booking['status']}) cannot be modified."

    changes = []
    ci = new_check_in or booking["check_in"]
    co = new_check_out or booking["check_out"]
    rt = (new_room_type.lower().replace(" ", "_")) if new_room_type else booking["room_type"]

    room = ROOMS.get(rt)
    if not room:
        return f"Unknown room type '{rt}'."

    nights = (datetime.strptime(co, "%Y-%m-%d") - datetime.strptime(ci, "%Y-%m-%d")).days
    if nights <= 0:
        return "Check-out must be after check-in."

    new_total = room["price_per_night"] * nights

    if new_check_in and new_check_in != booking["check_in"]:
        changes.append(f"Check-in: {booking['check_in']} → {new_check_in}")
        booking["check_in"] = new_check_in

    if new_check_out and new_check_out != booking["check_out"]:
        changes.append(f"Check-out: {booking['check_out']} → {new_check_out}")
        booking["check_out"] = new_check_out

    if new_room_type and rt != booking["room_type"]:
        changes.append(f"Room: {booking['room_type']} → {rt}")
        booking["room_type"] = rt

    if new_total != booking["total_cost"]:
        changes.append(f"Total: ${booking['total_cost']:.2f} → ${new_total:.2f}")
        booking["total_cost"] = new_total

    if not changes:
        return f"No changes were made to booking {booking_id}."

    return (
        f"Booking {booking_id} updated:\n" +
        "\n".join(f"  • {c}" for c in changes) +
        f"\n\nUpdated total: ${new_total:.2f}"
    )
