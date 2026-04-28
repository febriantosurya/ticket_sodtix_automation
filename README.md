# Ticket Bot

Automated ticket buyer for sodtix.com. Monitors target categories, grabs first available, fills checkout form instantly.

## Requirements

- Google Chrome (make sure you know your Chrome version — check at `chrome://settings/help`)

## Getting Started

1. Download `TicketBot` (Linux) or `TicketBot.exe` (Windows)
2. Place it in its own folder
3. Run it — on first launch, click **Edit info.json** to create and fill in your details

## Filling in info.json

```json
{
  "buyer": {
    "full_name": "Your Name",
    "number": "08xxxxxxxxxx",
    "email": "you@example.com"
  },
  "ticket_holders": [
    {
      "full_name": "Holder Name",
      "number": "08xxxxxxxxxx",
      "gender": "Male",
      "dob": "DD/MM/YYYY",
      "ktp": ""
    }
  ]
}
```

- `buyer` — person receiving the order confirmation email
- `ticket_holders` — one entry per ticket; add more objects to buy multiple tickets
- `gender` — must be exactly `Male` or `Female`
- `dob` — format `DD/MM/YYYY`
- `ktp` — 16-digit ID number; leave empty `""` if the event doesn't require it

## Usage

1. Paste the event URL into the **Event URL** field
2. Enter target categories in priority order, comma-separated — e.g. `TRIBUNE 5, TRIBUNE 2`
3. Set **Chrome Version** to match your installed Chrome (check at `chrome://settings/help`)
4. Click **Start**

The bot will:
- Refresh the page until tickets open
- Select the first available category by priority
- Automatically fill and submit the checkout form

5. Once done, the browser stays open so you can review or complete payment
6. Click **Stop** to cancel, or **Quit** to close everything

## Notes

- `info.json` must be in the same folder as the executable
- Do not close the browser manually while the bot is running — use **Stop** or **Quit**
