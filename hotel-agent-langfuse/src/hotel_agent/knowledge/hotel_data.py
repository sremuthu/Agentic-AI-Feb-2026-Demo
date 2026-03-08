"""In-memory mock hotel data simulating PMS/billing systems."""

from __future__ import annotations

ROOMS = {
    "standard": {
        "room_type": "Standard Room",
        "price_per_night": 149.0,
        "max_guests": 2,
        "total_inventory": 40,
        "amenities": ["Wi-Fi", "42\" TV", "mini-fridge", "coffee maker", "safe"],
    },
    "deluxe": {
        "room_type": "Deluxe Room",
        "price_per_night": 219.0,
        "max_guests": 3,
        "total_inventory": 30,
        "amenities": ["Wi-Fi", "55\" smart TV", "mini-fridge", "Keurig", "safe", "bathrobes"],
    },
    "premium_suite": {
        "room_type": "Premium Suite",
        "price_per_night": 349.0,
        "max_guests": 4,
        "total_inventory": 10,
        "amenities": ["Wi-Fi", "65\" smart TV", "mini-bar", "Nespresso", "safe", "bathrobes", "jacuzzi"],
    },
    "family_suite": {
        "room_type": "Family Suite",
        "price_per_night": 299.0,
        "max_guests": 5,
        "total_inventory": 8,
        "amenities": ["Wi-Fi", "2x TVs", "mini-fridge", "microwave", "coffee maker", "board games"],
    },
    "penthouse": {
        "room_type": "Penthouse Suite",
        "price_per_night": 599.0,
        "max_guests": 4,
        "total_inventory": 2,
        "amenities": ["Wi-Fi", "75\" smart TV", "full bar", "Nespresso", "Bose speaker", "butler service", "private balcony"],
    },
    "accessible": {
        "room_type": "Accessible Room",
        "price_per_night": 149.0,
        "max_guests": 2,
        "total_inventory": 6,
        "amenities": ["Wi-Fi", "42\" TV", "mini-fridge", "coffee maker", "safe", "roll-in shower", "grab bars"],
    },
}

# Mock existing bookings
BOOKINGS: dict[str, dict] = {
    "BK-1001": {
        "booking_id": "BK-1001",
        "guest_name": "Alice Johnson",
        "room_type": "deluxe",
        "check_in": "2026-03-10",
        "check_out": "2026-03-14",
        "total_cost": 876.0,
        "status": "confirmed",
    },
    "BK-1002": {
        "booking_id": "BK-1002",
        "guest_name": "Bob Smith",
        "room_type": "premium_suite",
        "check_in": "2026-03-15",
        "check_out": "2026-03-18",
        "total_cost": 1047.0,
        "status": "confirmed",
    },
    "BK-1003": {
        "booking_id": "BK-1003",
        "guest_name": "Carol Williams",
        "room_type": "standard",
        "check_in": "2026-03-20",
        "check_out": "2026-03-22",
        "total_cost": 298.0,
        "status": "checked_in",
    },
}

# Mock guest bills
BILLS: dict[str, dict] = {
    "BK-1001": {
        "booking_id": "BK-1001",
        "guest_name": "Alice Johnson",
        "items": [
            {"description": "Deluxe Room (4 nights)", "amount": 876.0, "date": "2026-03-10"},
            {"description": "Room Service - Dinner", "amount": 62.50, "date": "2026-03-11"},
            {"description": "Spa - Swedish Massage", "amount": 120.0, "date": "2026-03-12"},
            {"description": "Mini-bar", "amount": 35.0, "date": "2026-03-13"},
        ],
        "total": 1093.50,
        "paid": False,
    },
    "BK-1002": {
        "booking_id": "BK-1002",
        "guest_name": "Bob Smith",
        "items": [
            {"description": "Premium Suite (3 nights)", "amount": 1047.0, "date": "2026-03-15"},
            {"description": "Valet Parking (3 nights)", "amount": 135.0, "date": "2026-03-15"},
        ],
        "total": 1182.0,
        "paid": False,
    },
    "BK-1003": {
        "booking_id": "BK-1003",
        "guest_name": "Carol Williams",
        "items": [
            {"description": "Standard Room (2 nights)", "amount": 298.0, "date": "2026-03-20"},
            {"description": "Breakfast Buffet x2", "amount": 56.0, "date": "2026-03-20"},
        ],
        "total": 354.0,
        "paid": False,
    },
}

# Promo codes
PROMO_CODES: dict[str, float] = {
    "WELCOME10": 0.10,
    "SUMMER20": 0.20,
    "LOYALTY15": 0.15,
    "WEEKEND25": 0.25,
}

# Booking ID counter
_next_booking_id = 1004


def next_booking_id() -> str:
    global _next_booking_id
    bid = f"BK-{_next_booking_id}"
    _next_booking_id += 1
    return bid
