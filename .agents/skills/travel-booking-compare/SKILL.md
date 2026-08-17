---
name: travel-booking-compare
description: Travel itinerary generation, flight/train/hotel price comparison, PNR status tracking, and live transit alerts.
---

# Travel Booking & Transit Intelligence Skill

Facilitates travel planning, multi-provider fare comparisons, PNR status lookup, and itinerary coordination.

## Core Capabilities

### 1. PNR Status Tracking & Train Live Status
* Direct query to Indian Railways / Rapid API endpoints for 10-digit PNR.
* Extract: Train number, source/destination, charting status, passenger berths (CNF/RAC/WL).
* Alert user automatically if ticket status updates from WL to CNF.

### 2. Flight & Hotel Aggregation Strategy
* Compare routes across major aggregators (Google Flights, Skyscanner, MakeMyTrip).
* Extract: Layover duration, baggage allowance, cancellation policies, total price.

### 3. Itinerary Generation
Given destination and duration (e.g. "3-day trip to Goa"):
* Produce day-wise schedule: Morning activity, afternoon spot, sunset viewpoint, dining recommendations.
* Cross-check local weather forecasts and transit times.
