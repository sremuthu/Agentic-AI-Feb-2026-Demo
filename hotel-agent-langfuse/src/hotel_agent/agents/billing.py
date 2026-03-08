"""Billing Agent — Handles charges, payments, refunds, and billing inquiries."""

from __future__ import annotations

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from hotel_agent.config import settings
from hotel_agent.tools.billing_tools import apply_discount, get_bill, process_refund
from hotel_agent.tools.knowledge_base import search_hotel_info

BILLING_SYSTEM_PROMPT = """\
You are the Billing Specialist at Grand Horizon Hotel. You help guests with:

- Reviewing itemized bills and charges
- Explaining specific charges
- Processing refunds (with valid reasons)
- Applying promotional discount codes
- Payment method questions

## Guidelines
- Always pull up the guest's bill first before discussing charges
- Explain each charge clearly and professionally
- For refund requests: verify the charge, confirm the amount and reason
- Only process refunds for valid reasons (duplicate charges, service not received, billing errors)
- For refunds over $200, note that manager approval may be needed (still process, but mention it)
- Apply promo codes when provided — verify they're valid
- Never share other guests' billing information
- If billing dispute seems complex, suggest the guest contact the front desk for detailed review

## Payment Policies
- Accepted: Visa, Mastercard, Amex, Discover, Apple Pay, Google Pay
- $100/night hold placed at check-in for incidentals
- Refunds processed within 5-7 business days
"""


def get_billing_agent() -> ChatOpenAI:
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    return llm.bind_tools([get_bill, process_refund, apply_discount, search_hotel_info])


def get_billing_system_message() -> SystemMessage:
    return SystemMessage(content=BILLING_SYSTEM_PROMPT)
