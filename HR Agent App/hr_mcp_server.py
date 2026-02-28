"""
HR MCP Server — built with FastMCP
Exposes HR policies (via ChromaDB RAG) and employee data (from SQLite) as MCP tools and resources.

Run for Inspector debugging:
    mcp dev hr_mcp_server.py

Run standalone (stdio):
    python hr_mcp_server.py
"""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from hr_database import (
    create_leave_request,
    fetch_all_employees,
    fetch_employee,
    fetch_leave_balance,
)
from hr_vector_store import (
    get_policy_by_topic,
    list_policy_topics,
    search_policies,
)

mcp = FastMCP("HR Server")

# ─────────────────────────────────────────────
# Resources — policy documents (via vector store)
# ─────────────────────────────────────────────

@mcp.resource("hr://policies/{topic}")
def get_policy_resource(topic: str) -> str:
    """Get a specific HR policy document by topic.

    Available topics: remote_work, leave, performance, code_of_conduct, compensation
    """
    text = get_policy_by_topic(topic)
    if text:
        return text
    topics = ", ".join(t["topic"] for t in list_policy_topics())
    return f"Policy '{topic}' not found. Available topics: {topics}"


@mcp.resource("hr://policies")
def list_policies_resource() -> str:
    """List all available HR policy topics."""
    topics = list_policy_topics()
    lines = ["Available HR Policy Topics:\n"]
    for t in topics:
        lines.append(f"  • {t['topic']} — {t['description']}")
    lines.append("\nAccess any policy at: hr://policies/<topic>")
    return "\n".join(lines)


@mcp.resource("hr://employees/{employee_id}")
def get_employee_resource(employee_id: str) -> str:
    """Get employee profile from the SQLite database."""
    emp = fetch_employee(employee_id.upper())
    if not emp:
        return f"Employee '{employee_id}' not found."
    return json.dumps(emp, indent=2)


@mcp.resource("hr://employees")
def list_employees_resource() -> str:
    """List all employees from the SQLite database."""
    employees = fetch_all_employees()
    lines = [f"{'ID':<6} {'Name':<20} {'Role':<25} {'Department'}", "-" * 65]
    for e in employees:
        lines.append(f"{e['employee_id']:<6} {e['name']:<20} {e['role']:<25} {e['department']}")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# Tools — Policy (ChromaDB RAG-backed)
# ─────────────────────────────────────────────

@mcp.tool()
def get_hr_policy(topic: str) -> str:
    """Retrieve company HR policy text for a given topic.

    Args:
        topic: Policy topic. One of: remote_work, leave, performance,
               code_of_conduct, compensation. Partial names accepted.
    """
    text = get_policy_by_topic(topic)
    if text:
        return text
    # Fall back to semantic search if exact match fails
    results = search_policies(topic, k=1)
    if results:
        r = results[0]
        return f"[Closest match: {r['topic']}]\n\n{r['content']}"
    topics = ", ".join(t["topic"] for t in list_policy_topics())
    return f"Policy '{topic}' not found. Available topics: {topics}"


@mcp.tool()
def search_hr_policies(query: str, k: int = 3) -> str:
    """Search HR policies using hybrid semantic + keyword (BM25) retrieval.

    Use this for open-ended questions or when the exact policy topic is unknown.

    Args:
        query: Natural-language question or keyword (e.g. 'parental leave weeks', '401k').
        k:     Number of policy results to return (default 3).
    """
    results = search_policies(query, k=k)
    if not results:
        return "No relevant policies found."

    lines = [f"Found {len(results)} relevant HR policy section(s) for: '{query}'\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{'─' * 60}")
        lines.append(f"[{i}] Topic: {r['topic']}  —  {r['description']}")
        lines.append(r["content"])
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def list_hr_policies() -> str:
    """List all available HR policy topics with short descriptions."""
    topics = list_policy_topics()
    lines = ["HR Policy Topics:\n"]
    for t in topics:
        lines.append(f"  {t['topic']}: {t['description']}")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# Tools — Employee (SQLite-backed)
# ─────────────────────────────────────────────

@mcp.tool()
def get_employee_info(employee_id: str) -> str:
    """Get profile information for an employee from the HR database.

    Args:
        employee_id: Employee ID (e.g. E001, E002).
    """
    emp = fetch_employee(employee_id.upper())

    if not emp:
        return f"Employee '{employee_id}' not found in the database."
    return (
        f"Employee:   {emp['name']} ({emp['employee_id']})\n"
        f"Role:       {emp['role']}\n"
        f"Department: {emp['department']}\n"
        f"Manager:    {emp['manager_id'] or 'None (top-level)'}\n"
        f"Start date: {emp['start_date']}\n"
        f"Email:      {emp['email']}"
    )


@mcp.tool()
def list_employees() -> str:
    """List all employees in the HR database with their department and role."""
    employees = fetch_all_employees()
    if not employees:
        return "No employees found in the database."
    lines = [f"{'ID':<6} {'Name':<20} {'Role':<25} {'Department'}", "-" * 65]
    for e in employees:
        lines.append(f"{e['employee_id']:<6} {e['name']:<20} {e['role']:<25} {e['department']}")
    return "\n".join(lines)


@mcp.tool()
def check_leave_balance(employee_id: str) -> str:
    """Return the current leave balance for an employee from the HR database.

    Args:
        employee_id: Employee ID (e.g. E001).
    """
    emp = fetch_employee(employee_id.upper())
    if not emp:
        return f"Employee '{employee_id}' not found."

    bal = fetch_leave_balance(employee_id.upper())
    if not bal:
        return f"No leave balance record found for '{employee_id}'."

    return (
        f"Leave balance for {emp['name']} ({employee_id}):\n"
        f"  Annual:   {bal['annual']} day(s)\n"
        f"  Sick:     {bal['sick']} day(s)\n"
        f"  Personal: {bal['personal']} day(s)"
    )


@mcp.tool()
def submit_leave_request(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str = "",
) -> str:
    """Submit a leave request for an employee. Updates the SQLite database.

    Args:
        employee_id: Employee ID (e.g. E001).
        leave_type:  Type of leave — annual, sick, or personal.
        start_date:  Start date in YYYY-MM-DD format.
        end_date:    End date in YYYY-MM-DD format.
        reason:      Optional reason for the leave.
    """
    from datetime import datetime

    eid = employee_id.upper()

    emp = fetch_employee(eid)
    if not emp:
        return f"Employee '{employee_id}' not found."

    if leave_type not in ("annual", "sick", "personal"):
        return f"Invalid leave type '{leave_type}'. Must be annual, sick, or personal."

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end   = datetime.strptime(end_date,   "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format. Use YYYY-MM-DD."

    days = (end - start).days + 1
    if days <= 0:
        return "End date must be on or after start date."

    bal = fetch_leave_balance(eid)
    available = bal[leave_type] if bal else 0
    if days > available:
        return (
            f"Insufficient {leave_type} leave for {emp['name']}. "
            f"Requested: {days} day(s), Available: {available} day(s)."
        )

    request_id = create_leave_request(eid, leave_type, start_date, end_date, days, reason)
    remaining  = available - days

    return (
        f"Leave request {request_id} submitted successfully.\n"
        f"  Employee:  {emp['name']} ({eid})\n"
        f"  Type:      {leave_type}\n"
        f"  Dates:     {start_date} → {end_date} ({days} day(s))\n"
        f"  Status:    pending_approval\n"
        f"  Remaining {leave_type} balance: {remaining} day(s)"
    )

# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
