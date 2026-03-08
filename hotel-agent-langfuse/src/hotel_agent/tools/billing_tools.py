"""Billing tools — mock billing system for charges, refunds, discounts."""

from __future__ import annotations

from langchain_core.tools import tool

from hotel_agent.knowledge.hotel_data import BILLS, BOOKINGS, PROMO_CODES


@tool
def get_bill(booking_id: str) -> str:
    """Retrieve the itemized bill for a booking.

    Args:
        booking_id: The booking ID (e.g. BK-1001).
    """
    bill = BILLS.get(booking_id)
    if not bill:
        booking = BOOKINGS.get(booking_id)
        if not booking:
            return f"No booking found with ID '{booking_id}'."
        return f"No charges have been posted to booking {booking_id} yet."

    lines = [
        f"Bill for {bill['guest_name']} — Booking {booking_id}",
        "=" * 50,
    ]
    for item in bill["items"]:
        lines.append(f"  {item['date']}  {item['description']:<35} ${item['amount']:>8.2f}")
    lines.append("-" * 50)
    lines.append(f"  {'Total':<45} ${bill['total']:>8.2f}")
    lines.append(f"  {'Paid':<45} {'Yes' if bill['paid'] else 'No'}")

    return "\n".join(lines)


@tool
def process_refund(booking_id: str, amount: float, reason: str) -> str:
    """Process a refund for a guest.

    Args:
        booking_id: The booking ID.
        amount: Refund amount in USD.
        reason: Reason for the refund.
    """
    bill = BILLS.get(booking_id)
    if not bill:
        return f"No bill found for booking '{booking_id}'."

    if amount <= 0:
        return "Refund amount must be positive."

    if amount > bill["total"]:
        return f"Refund amount (${amount:.2f}) exceeds total bill (${bill['total']:.2f})."

    # Add refund as negative line item
    bill["items"].append({
        "description": f"REFUND: {reason}",
        "amount": -amount,
        "date": "2026-03-01",
    })
    bill["total"] = round(bill["total"] - amount, 2)

    return (
        f"Refund processed for booking {booking_id}:\n"
        f"  Amount: ${amount:.2f}\n"
        f"  Reason: {reason}\n"
        f"  New total: ${bill['total']:.2f}\n"
        f"  Refund will appear on the guest's card within 5-7 business days."
    )


@tool
def apply_discount(booking_id: str, promo_code: str) -> str:
    """Apply a promotional discount code to a booking.

    Args:
        booking_id: The booking ID.
        promo_code: The promotional code to apply.
    """
    booking = BOOKINGS.get(booking_id)
    if not booking:
        return f"No booking found with ID '{booking_id}'."

    code = promo_code.upper()
    discount_pct = PROMO_CODES.get(code)
    if discount_pct is None:
        return f"Invalid promo code '{promo_code}'. Please check and try again."

    discount_amount = round(booking["total_cost"] * discount_pct, 2)
    new_total = round(booking["total_cost"] - discount_amount, 2)

    # Update the bill if it exists
    bill = BILLS.get(booking_id)
    if bill:
        bill["items"].append({
            "description": f"Discount ({code} — {int(discount_pct * 100)}% off)",
            "amount": -discount_amount,
            "date": "2026-03-01",
        })
        bill["total"] = new_total

    booking["total_cost"] = new_total

    return (
        f"Promo code {code} applied to booking {booking_id}!\n"
        f"  Discount: {int(discount_pct * 100)}% — ${discount_amount:.2f} off\n"
        f"  New total: ${new_total:.2f}"
    )
