"""DB Agent — Data access layer that manages all database and knowledge base interactions.

Responsibilities:
- Manages ChromaDB vector store operations (search, index, update)
- Interfaces with mock PMS/billing data stores
- Ensures data consistency across agent interactions
- Provides unified data access API for all other agents
"""

from __future__ import annotations

import logging
from typing import Any

from hotel_agent.knowledge.hotel_data import BILLS, BOOKINGS, ROOMS
from hotel_agent.knowledge.vectorstore import search as vector_search, get_collection

logger = logging.getLogger(__name__)


class DBAgent:
    """Unified data access agent for the hotel system."""

    # --- Knowledge Base (RAG) ---

    def search_knowledge(self, query: str, n_results: int = 3) -> list[dict]:
        """Search the vector knowledge base for relevant hotel information."""
        return vector_search(query, n_results=n_results)

    def get_knowledge_stats(self) -> dict[str, Any]:
        """Get stats about the knowledge base."""
        try:
            collection = get_collection()
            count = collection.count()
            return {"status": "ready", "documents": count}
        except Exception as exc:
            logger.warning("Knowledge base not available: %s", exc)
            return {"status": "unavailable", "error": str(exc)}

    # --- Booking Data ---

    def get_booking(self, booking_id: str) -> dict | None:
        """Retrieve a booking record."""
        return BOOKINGS.get(booking_id)

    def list_bookings(self, guest_name: str = "", status: str = "") -> list[dict]:
        """List bookings, optionally filtered by guest name or status."""
        results = list(BOOKINGS.values())
        if guest_name:
            results = [b for b in results if guest_name.lower() in b["guest_name"].lower()]
        if status:
            results = [b for b in results if b["status"] == status]
        return results

    def get_room_info(self, room_type: str = "") -> dict | list[dict]:
        """Get room type information."""
        if room_type:
            key = room_type.lower().replace(" ", "_")
            return ROOMS.get(key, {})
        return list(ROOMS.values())

    # --- Billing Data ---

    def get_bill(self, booking_id: str) -> dict | None:
        """Retrieve a guest's bill."""
        return BILLS.get(booking_id)

    def get_billing_summary(self) -> dict[str, Any]:
        """Get an overview of all billing data."""
        total_revenue = sum(b["total"] for b in BILLS.values())
        unpaid = sum(1 for b in BILLS.values() if not b["paid"])
        return {
            "total_bills": len(BILLS),
            "total_revenue": round(total_revenue, 2),
            "unpaid_bills": unpaid,
        }

    # --- Health ---

    def check_health(self) -> dict[str, Any]:
        """Check health of all data sources."""
        kb = self.get_knowledge_stats()
        return {
            "bookings_loaded": len(BOOKINGS),
            "bills_loaded": len(BILLS),
            "rooms_configured": len(ROOMS),
            "knowledge_base": kb,
        }


# Singleton instance
db_agent = DBAgent()
