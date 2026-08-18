---
name: travel-booking-compare
description: Travel itinerary generation, flight/train/hotel price comparison, PNR status tracking, and live transit alerts.
---

# Travel Booking & Transit Intelligence Skill

Facilitates travel planning, multi-provider fare comparisons, PNR status lookup, and itinerary coordination.

## Core Capabilities

### 1. PNR Status Tracking & Train Live Status
* Real-time query to Indian Railways / IRCTC live PNR endpoints for 10-digit PNR.
* Extract and display complete booking details:
  - **Train Information**: Train Number, Train Name, Train Running Status.
  - **Route & Stations**: Origin, Destination, Boarding Point, Reservation Upto with station codes and full names.
  - **Schedule**: Date of Journey (DOJ), Booking Date, Departure Time, Arrival Time, Duration.
  - **Class & Quota**: Full class description (e.g., 3A AC 3-Tier, SL Sleeper) and Quota (General, Tatkal, Premium Tatkal).
  - **Charting Status**: Live Charting badge (🟢 Chart Prepared / ⏳ Chart Not Prepared).
  - **Passenger Breakdown**: Individual passenger status (CNF / RAC / WL), assigned Coach & Berth number, Berth Type (Lower/Middle/Upper/Side), and Confirmation Probability percentage for waitlist.
  - **Amenities & Logistics**: Expected Platform Number, Total Ticket Fare (₹), Pantry Car availability, Coach Composition.
  - **Official Verification**: Direct links to official Indian Rail PNR Portal, SMS `139` enquiry, and 24x7 helpline.

### 2. Flight & Hotel Aggregation Strategy
* Compare routes across major aggregators (Google Flights, Skyscanner, MakeMyTrip).
* Extract: Layover duration, baggage allowance, cancellation policies, total price.

### 3. Itinerary Generation
Given destination and duration (e.g. "3-day trip to Goa"):
* Produce day-wise schedule: Morning activity, afternoon spot, sunset viewpoint, dining recommendations.
* Cross-check local weather forecasts and transit times.
