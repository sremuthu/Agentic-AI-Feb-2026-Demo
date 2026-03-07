# CrewAI Travel Agent

A multi-agent AI travel booking system built with [CrewAI](https://crewai.com), featuring intelligent agents for travel planning, booking, and customer service — with optional voice interaction via OpenAI Whisper and TTS.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Agents](#agents)
- [Tools](#tools)
- [Workflows](#workflows)
- [Agent Sequence Diagrams](#agent-sequence-diagrams)
- [Setup](#setup)
- [Running the App](#running-the-app)

---

## Overview

```mermaid
graph TD
    User["👤 User"] --> CS["Customer Service Agent"]
    CS --> TA["Travel Advisor Agent"]
    CS --> BA["Booking Specialist Agent"]
    TA --> BA
    BA --> CS

    TA --> F["FlightSearchTool"]
    TA --> H["HotelSearchTool"]
    TA --> TI["TravelInfoTool"]
    TA --> W["WeatherTool"]

    BA --> F
    BA --> H
    BA --> BT["BookingTool"]

    CS --> TI
    CS --> W
    CS --> S["SerperDevTool (Web Search)"]
```

---

## Project Structure

```
crew-ai-travelagent/
├── agents/
│   ├── travel_advisor_agent.py      # Travel recommendations & itinerary planning
│   ├── booking_agent.py             # Booking processing & confirmation
│   └── customer_service_agent.py    # Customer intake & routing
├── core/
│   ├── travel_booking_crew.py       # Crew orchestration & workflow methods
│   └── crew_tasks.py                # Task definitions for each workflow step
├── tools/
│   └── travel_tools.py              # 5 custom tools (Flight, Hotel, Booking, Info, Weather)
├── config/
│   └── settings.py                  # Pydantic settings (temperatures, flags)
├── main.py                          # CLI entry point
├── streamlit_app.py                 # Web UI with voice support
├── voice_utils.py                   # OpenAI Whisper STT + TTS helpers
├── code_review_demo.py              # Standalone code review demo
├── requirements.txt
└── .env.example
```

---

## Agents

```mermaid
graph LR
    subgraph Agents
        CS["🙋 Customer Service\nRep\ntemp=0.7"]
        TA["🗺️ Travel Advisor\ntemp=0.8"]
        BA["📋 Booking Specialist\ntemp=0.3"]
    end

    CS -- "delegates to" --> TA
    CS -- "delegates to" --> BA
    TA -- "handoff for booking" --> BA
```

### Customer Service Representative

| Attribute | Value |
|-----------|-------|
| **Goal** | Understand customer needs and route to appropriate specialists |
| **Temperature** | 0.7 (balanced, friendly) |
| **Allow Delegation** | Yes |
| **Tools** | TravelInfoTool, WeatherTool, SerperDevTool |

Greets customers, gathers trip requirements, and routes them to the Travel Advisor or Booking Specialist.

---

### Travel Advisor

| Attribute | Value |
|-----------|-------|
| **Goal** | Provide personalized travel recommendations and create comprehensive itineraries |
| **Temperature** | 0.8 (creative, exploratory) |
| **Allow Delegation** | Yes |
| **Tools** | FlightSearchTool, HotelSearchTool, TravelInfoTool, WeatherTool |

Researches destinations, finds flights and hotels, builds day-by-day itineraries, and considers weather and seasonal factors.

---

### Booking Specialist

| Attribute | Value |
|-----------|-------|
| **Goal** | Accurately process travel bookings and provide confirmation |
| **Temperature** | 0.3 (precise, deterministic) |
| **Allow Delegation** | No |
| **Tools** | FlightSearchTool, HotelSearchTool, BookingTool |

Verifies all details, processes bookings with 100% accuracy, generates confirmation numbers, and handles modifications/cancellations.

---

## Tools

```mermaid
graph LR
    subgraph Custom Tools
        FT["✈️ FlightSearchTool\nSearch flights by origin,\ndestination, dates, passengers"]
        HT["🏨 HotelSearchTool\nSearch hotels by location,\ndates, guests, budget"]
        BT["📝 BookingTool\nCreate flight & hotel\nbookings, generate IDs"]
        TI["ℹ️ TravelInfoTool\nVisa, currency, language,\nattractions by destination"]
        WT["🌤️ WeatherTool\nCurrent weather &\n3-day forecast"]
    end
```

| Tool | Input | Output |
|------|-------|--------|
| **FlightSearchTool** | origin, destination, dates, passengers | 3 flight options with airline, price, duration |
| **HotelSearchTool** | destination, check-in/out, guests, max budget | 3 hotel options with ratings, amenities, price |
| **BookingTool** | booking type, details, customer info | Booking ID (`BK{timestamp}`), confirmation number |
| **TravelInfoTool** | destination, info type | Visa requirements, currency, attractions, best time |
| **WeatherTool** | destination, days | 3-day forecast with condition, temps, precipitation |

> **Note:** All tools use mock/simulated data. No external travel API key is required.

---

## Workflows

Four built-in workflows define which tasks and agents are activated:

```mermaid
graph TD
    WF{Workflow Type}

    WF -->|new_customer_inquiry| W1["1. Initial Greeting\n2. Trip Planning"]
    WF -->|flight_booking| W2["1. Flight Search\n2. Booking\n3. Follow-up"]
    WF -->|hotel_booking| W3["1. Hotel Search\n2. Booking\n3. Follow-up"]
    WF -->|complete_trip| W4["1. Trip Planning\n2. Flight Search\n3. Hotel Search\n4. Booking\n5. Follow-up"]
```

### Tasks

| Task | Agent | Description |
|------|-------|-------------|
| **Initial Greeting** | Customer Service | Greet customer, gather needs, determine routing |
| **Trip Planning** | Travel Advisor | Full itinerary with activities, costs, and alternatives |
| **Flight Search** | Travel Advisor | Compare 3–5 flight options with pros/cons |
| **Hotel Search** | Travel Advisor | Curate 3–4 hotel picks with reviews and policies |
| **Booking** | Booking Specialist | Verify, process, confirm — generate booking ID |
| **Customer Follow-up** | Customer Service | Confirm satisfaction, offer travel tips and add-ons |

---

## Agent Sequence Diagrams

### Complete Trip Planning

```mermaid
sequenceDiagram
    actor User
    participant CS as Customer Service
    participant TA as Travel Advisor
    participant BA as Booking Specialist

    User->>CS: "Plan a 7-day trip to Paris, budget $5000"
    CS->>CS: Greet & gather requirements
    CS->>TA: Route: complete_trip workflow

    TA->>TA: Research destination (TravelInfoTool)
    TA->>TA: Check weather (WeatherTool)
    TA->>TA: Build day-by-day itinerary

    TA->>TA: Search flights (FlightSearchTool)
    TA->>TA: Compare options, select best 3–5

    TA->>TA: Search hotels (HotelSearchTool)
    TA->>TA: Filter by budget, recommend top 3

    TA->>BA: Hand off booking details

    BA->>BA: Verify all travel info
    BA->>BA: Process booking (BookingTool)
    BA->>BA: Generate confirmation number

    BA->>CS: Booking confirmed

    CS->>User: Confirmation + travel tips + follow-up
```

---

### Customer Inquiry Routing

```mermaid
sequenceDiagram
    actor User
    participant CS as Customer Service
    participant TA as Travel Advisor
    participant BA as Booking Specialist

    User->>CS: Initial inquiry

    CS->>CS: Analyze inquiry keywords

    alt Contains "book" or "reserve"
        CS->>BA: Route to Booking Specialist
        BA->>User: Booking workflow
    else Contains "flight" or "hotel"
        CS->>TA: Route to Travel Advisor
        TA->>User: Search results
    else General question
        CS->>User: Basic info + next steps
    end
```

---

### Voice Interaction Flow (Streamlit)

```mermaid
sequenceDiagram
    actor User
    participant MIC as Microphone
    participant W as Whisper STT
    participant Crew as Travel Crew
    participant TTS as OpenAI TTS
    participant Speaker as Audio Output

    User->>MIC: Speak travel request
    MIC->>W: Audio bytes
    W->>Crew: Transcribed text
    Crew->>Crew: Run agent workflow
    Crew->>TTS: Agent response text
    TTS->>Speaker: MP3 audio
    Speaker->>User: Spoken response
```

---

## Setup

### Prerequisites

- Python 3.10+
- OpenAI API key

### Install

```bash
cd crew-ai-travelagent

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your keys:

```env
OPENAI_API_KEY=sk-...

# Optional — mock data is used if not provided
TRAVEL_API_KEY=your_travel_api_key_here
TRAVEL_API_BASE_URL=https://api.travelbooking.com

# Agent settings (defaults shown)
CUSTOMER_SERVICE_TEMPERATURE=0.7
TRAVEL_ADVISOR_TEMPERATURE=0.8
BOOKING_AGENT_TEMPERATURE=0.3
MAX_ITERATIONS=10
VERBOSE=true
```

---

## Running the App

### Option 1 — CLI (Interactive)

```bash
python main.py
```

Presents a menu to choose a workflow, prompts for trip requirements, and runs the full agent crew in the terminal.

### Option 2 — Streamlit Web UI (with Voice)

```bash
streamlit run streamlit_app.py
```

Opens a browser-based chat interface with:
- Voice input (OpenAI Whisper)
- Voice output with selectable voice (`alloy`, `echo`, `fable`, `nova`, `onyx`, `shimmer`)
- Text input fallback
- Chat history

### Option 3 — Code Review Demo

A standalone CrewAI demo with a Coder + Reviewer agent pair that writes and reviews Python code.

```bash
python code_review_demo.py
```

---

## Architecture Summary

```mermaid
flowchart TD
    subgraph Entry Points
        CLI["main.py\nCLI"]
        UI["streamlit_app.py\nWeb UI + Voice"]
        DEMO["code_review_demo.py\nStandalone Demo"]
    end

    subgraph Core
        CREW["TravelBookingCrew\nOrchestrator"]
        TASKS["TravelBookingTasks\nTask Factory"]
        SETTINGS["Settings\nPydantic Config"]
    end

    subgraph Agents
        CS["Customer Service"]
        TA["Travel Advisor"]
        BA["Booking Specialist"]
    end

    subgraph Tools
        FT["FlightSearchTool"]
        HT["HotelSearchTool"]
        BT["BookingTool"]
        TI["TravelInfoTool"]
        WT["WeatherTool"]
        SDT["SerperDevTool"]
    end

    subgraph Voice
        VU["voice_utils.py\nWhisper STT / TTS"]
    end

    CLI --> CREW
    UI --> CREW
    UI --> VU
    CREW --> TASKS
    CREW --> SETTINGS
    TASKS --> CS
    TASKS --> TA
    TASKS --> BA
    CS --> TI & WT & SDT
    TA --> FT & HT & TI & WT
    BA --> FT & HT & BT
```
