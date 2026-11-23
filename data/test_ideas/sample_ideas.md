# Sample ideas (Phase 0)

Ten ideas for testing classification and requirement extraction: 3 business, 3 software,
3 technology, 1 deliberately vague. Expected requirements are the must-have items a
correct extraction should surface; wording will differ, meaning should not.

| # | Category | Idea | Expected requirements (must) |
| --- | --- | --- | --- |
| 1 | business | A subscription box that delivers regional spices and a recipe card to home cooks in Pakistan, sourced from small local suppliers. | Subscription billing with monthly/annual plans; supplier onboarding and quality checks; delivery scheduling by city; recipe content per box; cancellation and refund flow. |
| 2 | business | A neighbourhood laundry service where customers schedule a pickup by WhatsApp and pay per kilogram. | Pickup/drop-off scheduling; per-kg price calculation; order status tracking; rider assignment; payment on delivery or online. |
| 3 | business | A co-working space in Lahore aimed at freelancers, with day passes, meeting rooms, and a mentor-in-residence programme. | Desk/room booking with conflict checks; membership plans and invoicing; access control at the door; mentor session scheduling; occupancy reporting. |
| 4 | software | A mobile app that helps university students find affordable tutors nearby and book sessions in-app. | Tutor search with filters (subject, price, distance); booking with availability; reviews and ratings; in-app payment; tutor identity verification. |
| 5 | software | A web dashboard for small clinics to manage appointments, patient records, and SMS reminders. | Appointment calendar with double-booking prevention; patient record storage; SMS reminder scheduling; role-based access for staff; export of daily schedule. |
| 6 | software | A browser extension that tracks time spent on distracting sites and blocks them during focus sessions. | Site allow/block lists; focus session timer; time tracking and daily report; block page with override; settings sync across devices. |
| 7 | technology | A low-cost IoT sensor network for detecting water leaks in apartment buildings, using LoRa and a solar-powered gateway. | Leak detection from flow/pressure sensors; LoRa gateway with solar power budget; alert delivery to building manager; sensor battery life monitoring; installation guide. |
| 8 | technology | An on-device speech-to-text model for Urdu that runs offline on mid-range Android phones. | Urdu acoustic model under a mobile size budget; offline inference on mid-range hardware; accuracy benchmark against a held-out set; streaming partial transcripts; no audio leaves the device. |
| 9 | technology | A computer-vision system that counts footfall in retail stores from existing CCTV cameras while preserving privacy. | Person detection and counting accuracy target; works with existing camera feeds; privacy-preserving (no faces stored); per-store hourly reports; deployment on edge hardware. |
| 10 | vague | Something with AI for students. | Category is not determinable from the text; extraction must list missing information (problem, users, features, platform) rather than invent them; zero confident functional requirements. |

## Notes for evaluation

- Ideas 1-3 should classify as `business`, 4-6 as `software`, 7-9 as `technology`.
- Idea 10 must return low confidence plus populated `missing_information`; a confident
  category with invented features is a failure of the extraction stage.
- Each extraction should produce 5-12 requirements; idea 1 and idea 5 should include at
  least one `non_functional` requirement (payment reliability, patient data privacy).
