# Standard dataset results (90 emails)

| Metric | Correct | Total | % |
|---|---|---|---|
| category | 62 | 90 | 68.9 |
| priority_exact | 53 | 90 | 58.9 |
| priority_within_one_level | 84 | 90 | 93.3 |
| sentiment | 44 | 90 | 48.9 |
| reply_required | 80 | 90 | 88.9 |
| action_required | 71 | 90 | 78.9 |
| summary_present | 90 | 90 | 100.0 |
| extraction_fields | 55 | 64 | 85.9 |
| deadlines | 22 | 27 | 81.5 |
| action_items_found | 54 | 59 | 91.5 |
| reply_mentions_key_terms | 22 | 68 | 32.4 |

## Category accuracy by class

| Category | Correct | Total |
|---|---|---|
| Customer Complaint | 6 | 10 |
| Sales Inquiry | 8 | 10 |
| Support Request | 5 | 10 |
| Meeting Request | 8 | 10 |
| Invoice / Payment | 9 | 10 |
| Job Application | 7 | 10 |
| General Information | 9 | 10 |
| Urgent | 5 | 10 |
| Spam | 5 | 10 |

## Most common confusions

- Urgent -> General Information: 3
- Spam -> General Information: 3
- Customer Complaint -> General Information: 2
- Support Request -> Other: 2
- Spam -> Sales Inquiry: 2
- Customer Complaint -> Invoice / Payment: 1
- Customer Complaint -> Support Request: 1
- Sales Inquiry -> Invoice / Payment: 1
- Sales Inquiry -> Support Request: 1
- Support Request -> Meeting Request: 1

## Sample of category misses

- #2 category: expected Customer Complaint, got General Information - Third time my delivery is late
- #5 category: expected Customer Complaint, got Invoice / Payment - Very poor experience with your support team
- #6 category: expected Customer Complaint, got Support Request - Product stopped working after two weeks
- #9 category: expected Customer Complaint, got General Information - Misleading description of the sofa
- #17 category: expected Sales Inquiry, got Invoice / Payment - Question about annual billing prices
- #18 category: expected Sales Inquiry, got Support Request - Can your tool integrate with Shopify?
- #24 category: expected Support Request, got Other - Email notifications not arriving
- #25 category: expected Support Request, got Meeting Request - API returns 500 on /v2/reports
- #26 category: expected Support Request, got Invoice / Payment - Need help changing my billing address
- #29 category: expected Support Request, got Other - Feature question: bulk import
- #30 category: expected Support Request, got Customer Complaint - Shared link says access denied
- #39 category: expected Meeting Request, got Sales Inquiry - Parent-teacher style demo session
- #40 category: expected Meeting Request, got Other - Board presentation dry run
- #48 category: expected Invoice / Payment, got General Information - Your Stripe payout of $3,210 is on the way
- #54 category: expected Job Application, got Other - Following up on my application
- #57 category: expected Job Application, got Meeting Request - Request to reschedule interview
- #59 category: expected Job Application, got General Information - Offer acceptance
- #64 category: expected General Information, got Support Request - This week in AI - issue 212
- #72 category: expected Urgent, got Support Request - Production line down - need help now
- #74 category: expected Urgent, got General Information - Court filing deadline tomorrow
- #75 category: expected Urgent, got General Information - Website checkout failing during our sale
- #76 category: expected Urgent, got Invoice / Payment - Shipment held at customs - action needed today
- #77 category: expected Urgent, got General Information - Need the audit figures before 3pm
- #83 category: expected Spam, got Sales Inquiry - Get to #1 on Google in 7 days guaranteed
- #85 category: expected Spam, got General Information - Your account has been limited - verify now
