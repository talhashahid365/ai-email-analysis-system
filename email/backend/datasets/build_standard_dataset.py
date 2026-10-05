"""Builds datasets/standard_test_dataset.json - the fixed benchmark every intern is tested against (spec §26).

90 emails: exactly 10 in each of 9 categories. Every email carries hand-written expected results (category,
priority, sentiment, reply/action required, extracted fields, deadlines, action items, reply keywords).

All emails are 'received' on Monday 2026-09-14 09:00 so relative deadlines have one correct answer:
tomorrow=2026-09-15, Wednesday=09-16, Thursday=09-17, Friday=09-18, next Monday=09-21, end of month=09-30.
The emails were written independently of the rule engine's keyword lists; do not tune the engine to them.
Run:  python datasets/build_standard_dataset.py
"""
import json
import os

RECEIVED = "2026-09-14T09:00:00"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "standard_test_dataset.json")
DATA = []


def E(cat, name, addr, subject, body, pri, sent, reply, action, ext=None, dl=None, acts=None, rk=None):
    DATA.append({
        "id": len(DATA) + 1, "sender_name": name, "sender_email": addr, "subject": subject, "body_plain": body.strip(),
        "received_at": RECEIVED,
        "expected": {"category": cat, "priority": pri, "sentiment": sent, "reply_required": reply,
                     "action_required": action, "extracted": ext or {}, "deadlines": dl or [],
                     "action_items": acts or [], "reply_keywords": rk or []}})


CC, SI, SR, MR, IP, JA, GI, UR, SP = ("Customer Complaint", "Sales Inquiry", "Support Request", "Meeting Request",
                                     "Invoice / Payment", "Job Application", "General Information", "Urgent", "Spam")

# ---------------------------------------------------------------- 10 customer complaints
E(CC, "Sarah Ahmed", "sarah.ahmed@clientcorp.com", "Laptop arrived with a cracked screen - order #1029",
  "Hello,\n\nOrder #1029 reached me yesterday and the laptop screen is cracked across the corner. I paid $1,200 for this and I'm very disappointed. Please refund me or send a replacement within 3 days.\n\nSarah Ahmed\nClientCorp\n+92 300 9876543",
  "HIGH", "Negative", True, True, {"order_number": "1029", "amount": "$1,200", "customer_name": "Sarah Ahmed", "phone_number": "+92 300 9876543"},
  [{"phrase": "within 3 days", "due_date": "2026-09-17"}], ["refund or replacement"], ["1029", "sorry"])
E(CC, "Bilal Raza", "bilal.raza@gmail.com", "Third time my delivery is late",
  "This is the third time your courier has delivered late. Order 5587 was supposed to arrive last Tuesday and it still hasn't. I'm furious and honestly thinking about cancelling my account. Sort this out today or I'm done.",
  "HIGH", "Angry", True, True, {"order_number": "5587"}, [], ["locate order 5587"], ["5587", "apolog"])
E(CC, "Maria Fernandes", "maria.f@brightlabs.io", "Wrong item shipped",
  "Hi team,\n\nI ordered the blue 32GB model but received the red 16GB one (order #7745). It's not what I paid for. Could you arrange an exchange? Happy to return the wrong unit.\n\nThanks,\nMaria Fernandes",
  "MEDIUM", "Negative", True, True, {"order_number": "7745", "customer_name": "Maria Fernandes"}, [], ["arrange exchange"], ["7745", "exchange"])
E(CC, "Usman Tariq", "usman.tariq@outlook.com", "Charged twice for my subscription",
  "I was billed $49 two times this month for the same plan. This is unacceptable, please refund the duplicate charge. My account email is usman.tariq@outlook.com. I expect an answer by Thursday.",
  "HIGH", "Angry", True, True, {"amount": "$49", "email_address": "usman.tariq@outlook.com"}, [{"phrase": "Thursday", "due_date": "2026-09-17"}],
  ["refund duplicate charge"], ["refund", "duplicate"])
E(CC, "Ayesha Khan", "ayesha@designhouse.pk", "Very poor experience with your support team",
  "I contacted support three times about my broken invoice template and each agent told me something different. Nobody followed up. The service I received was well below what you advertise. I would like a call from a manager.",
  "MEDIUM", "Negative", True, True, {"customer_name": "Ayesha Khan"}, [], ["manager to call customer"], ["manager", "apolog"])
E(CC, "Daniel Wright", "dwright@northwind.com", "Product stopped working after two weeks",
  "The air purifier I bought (order #3302) stopped working after just two weeks. It's within warranty and I want a replacement unit shipped. Your site says 12-month warranty so this should be simple.",
  "MEDIUM", "Negative", True, True, {"order_number": "3302", "product": "air purifier"}, [], ["ship replacement"], ["3302", "replacement"])
E(CC, "Hina Siddiqui", "hina.s@yahoo.com", "Rude behaviour at your Lahore store",
  "I visited your Lahore branch on Saturday and the staff member at the counter was dismissive and rude when I asked about a return. I've shopped with you for years and have never been treated like that. I'd like an apology and an explanation.",
  "MEDIUM", "Negative", True, True, {"customer_name": "Hina Siddiqui", "location": "Lahore"}, [], ["investigate store incident"], ["apolog"])
E(CC, "Peter Novak", "p.novak@acmelogistics.eu", "Refund still not received",
  "You promised my refund of $310 for order #8120 within 10 working days. It has now been 25 days and nothing. Please escalate this and send me the transaction reference by Friday.",
  "HIGH", "Angry", True, True, {"order_number": "8120", "amount": "$310"}, [{"phrase": "Friday", "due_date": "2026-09-18"}],
  ["escalate refund", "send transaction reference"], ["8120", "refund"])
E(CC, "Fatima Noor", "fatima.noor@gmail.com", "Misleading description of the sofa",
  "The listing said the sofa seats three adults and is made of genuine leather. What arrived seats two and the cover is clearly synthetic. I feel misled. Please tell me how you plan to make this right.",
  "MEDIUM", "Negative", True, True, {"product": "sofa"}, [], ["resolve misleading listing complaint"], ["sorry", "make this right"])
E(CC, "Tom Becker", "tom@beckerandsons.com", "Disappointed with the latest update",
  "Since your last app update, exporting reports takes ten minutes and crashes half the time. We rely on this every day. I'm disappointed, this was never a problem before and nobody warned us.",
  "MEDIUM", "Negative", True, True, {"company": "Becker and Sons"}, [], ["investigate export regression"], ["update", "apolog"])

# ---------------------------------------------------------------- 10 sales inquiries
E(SI, "Omar Sheikh", "omar@greenfieldfoods.com", "Pricing for 200 user licences",
  "Hello,\n\nWe're a food distribution company with about 200 staff and we'd like pricing for your Business plan, including volume discounts. Could you also send the updated quotation by Friday? We are making a decision next week.\n\nOmar Sheikh\nGreenfield Foods",
  "MEDIUM", "Positive", True, True, {"customer_name": "Omar Sheikh", "company": "Greenfield Foods"}, [{"phrase": "Friday", "due_date": "2026-09-18"}],
  ["send updated quotation"], ["pricing", "quotation"])
E(SI, "Laura Chen", "laura.chen@pixelforge.com", "Interested in your enterprise plan",
  "Hi there, our team of 40 designers is looking for a tool like yours. Can you tell me what the enterprise plan includes and whether SSO is supported? A brochure would be great.",
  "MEDIUM", "Positive", True, True, {"customer_name": "Laura Chen", "company": "PixelForge"}, [], ["send enterprise plan details"], ["enterprise", "sso"])
E(SI, "Hamza Iqbal", "hamza@startupnest.pk", "Do you offer discounts for startups?",
  "We're a four-person startup and your pricing is a bit steep for us right now. Is there any startup or early-stage discount? We'd likely sign up this month if the numbers work.",
  "MEDIUM", "Neutral", True, True, {"customer_name": "Hamza Iqbal"}, [], ["share startup pricing"], ["discount"])
E(SI, "Elena Petrova", "elena@baltictrade.lv", "Request for a product demo",
  "Good afternoon. We would like to see a live demo of your inventory module before we shortlist vendors. Our procurement review closes on 25 September.",
  "MEDIUM", "Neutral", True, True, {"customer_name": "Elena Petrova"}, [{"phrase": "25 September", "due_date": "2026-09-25"}], ["schedule product demo"], ["demo"])
E(SI, "Kevin O'Brien", "kevin@obrienbuild.ie", "Bulk order quote - 500 units",
  "We need a quote for 500 units of the X200 sensor, delivered to Dublin. Please include lead time and payment terms. If the price is right we will place the order within 3 days.",
  "HIGH", "Positive", True, True, {"product": "X200 sensor", "location": "Dublin"}, [{"phrase": "within 3 days", "due_date": "2026-09-17"}],
  ["prepare bulk quote"], ["x200", "lead time"])
E(SI, "Sana Malik", "sana.malik@learnloop.com", "Partnership / reseller programme",
  "Hello, we run an ed-tech consultancy and several of our clients ask about your product. Do you have a reseller or partner programme? I'd love to understand margins and onboarding.",
  "LOW", "Positive", True, True, {"customer_name": "Sana Malik", "company": "LearnLoop"}, [], ["send partner programme info"], ["partner"])
E(SI, "Richard Hall", "rhall@hallmedical.com", "Question about annual billing prices",
  "Is there a discount if we pay annually instead of monthly? Also does the price include onboarding and training? Thanks.",
  "LOW", "Neutral", True, False, {}, [], [], ["annual", "onboarding"])
E(SI, "Zara Qureshi", "zara@craftcorner.com", "Can your tool integrate with Shopify?",
  "We sell handmade goods on Shopify and want to know whether your product connects to it. If yes, what's the cost of the integration?",
  "LOW", "Neutral", True, False, {"product": "Shopify"}, [], [], ["shopify"])
E(SI, "Martin Lopez", "m.lopez@riveratech.mx", "Trial extension and quote",
  "Our 14-day trial ends tomorrow and we're not finished testing. Could you extend it by a week and send a quote for 25 seats afterwards?",
  "MEDIUM", "Positive", True, True, {}, [{"phrase": "tomorrow", "due_date": "2026-09-15"}], ["extend trial", "send quote for 25 seats"], ["trial"])
E(SI, "Nadia Hussain", "nadia@urbanfit.pk", "Requesting catalogue and price list",
  "Please send me your latest catalogue and wholesale price list. We own three gyms and are looking for a new equipment supplier.",
  "LOW", "Positive", True, True, {"customer_name": "Nadia Hussain"}, [], ["send catalogue and price list"], ["catalogue"])

# ---------------------------------------------------------------- 10 support requests
E(SR, "Ali Raza", "ali.raza@techsolutions.pk", "Cannot log in to my account",
  "Hi support, I've been unable to log in since this morning. It says 'invalid credentials' even after I reset my password. My username is ali.raza. Please help.",
  "MEDIUM", "Neutral", True, True, {"customer_name": "Ali Raza"}, [], ["investigate login failure"], ["password", "login"])
E(SR, "Julia Martins", "julia@fernhill.co.uk", "Export to PDF gives a blank page",
  "When I export any report to PDF I get an empty page. This started after Monday. I'm on Chrome 128 and Windows 11. Screenshot attached.",
  "MEDIUM", "Neutral", True, True, {}, [], ["investigate PDF export"], ["pdf"])
E(SR, "Imran Butt", "imran@butttextiles.com", "How do I add a new team member?",
  "Quick question - where do I add a new colleague to our workspace and set their permissions? I couldn't find it in settings.",
  "LOW", "Neutral", True, False, {}, [], [], ["settings", "invite"])
E(SR, "Chloe Dubois", "chloe.dubois@lumiere.fr", "Email notifications not arriving",
  "I stopped receiving notification emails about three days ago. I've checked spam and my notification settings are all on. Can you check what's wrong on your side?",
  "MEDIUM", "Neutral", True, True, {}, [], ["check notification delivery"], ["notification"])
E(SR, "Ravi Patel", "ravi@patelanalytics.in", "API returns 500 on /v2/reports",
  "Our integration started getting HTTP 500 on GET /v2/reports at around 08:00 UTC today. Request ID req_9f31ab. This affects our nightly sync. Please look into it as soon as you can.",
  "HIGH", "Neutral", True, True, {}, [], ["investigate API 500 error"], ["req_9f31ab", "investigat"])
E(SR, "Sophie Turner", "sophie@bluepeak.com", "Need help changing my billing address",
  "Hi, I moved offices and need to update the billing address on our account. I can't find the option anywhere. Could someone guide me?",
  "LOW", "Neutral", True, False, {}, [], [], ["billing address"])
E(SR, "Kamran Ali", "kamran@alihardware.pk", "App crashes when I open the dashboard",
  "Since yesterday the mobile app crashes every time I open the dashboard tab. I reinstalled it but it still happens. iPhone 14, iOS 17.",
  "MEDIUM", "Negative", True, True, {}, [], ["investigate mobile crash"], ["crash", "ios"])
E(SR, "Anna Kowalski", "anna.k@polskabuild.pl", "Two-factor codes not working",
  "My authenticator app codes keep getting rejected when I log in. The clock on my phone is correct. Could you reset 2FA for my account?",
  "MEDIUM", "Neutral", True, True, {}, [], ["reset 2FA"], ["two-factor", "reset"])
E(SR, "Hassan Mirza", "hassan@mirzaassociates.com", "Feature question: bulk import",
  "Is there a way to bulk import contacts from a CSV? I only see manual entry. If it's not available yet, is it on the roadmap?",
  "LOW", "Neutral", True, False, {}, [], [], ["csv", "import"])
E(SR, "Grace Okafor", "grace@okaforgroup.ng", "Shared link says access denied",
  "I shared a project link with a client and they get 'access denied'. I set it to anyone with the link. Please advise what I'm missing.",
  "LOW", "Neutral", True, False, {}, [], [], ["permission", "link"])

# ---------------------------------------------------------------- 10 meeting requests
E(MR, "Priya Nair", "priya.nair@brightpath.com", "Catch-up call next week?",
  "Hi, could we schedule a 30-minute call next Tuesday afternoon to go over the Q4 roadmap? Let me know what time suits you.",
  "MEDIUM", "Neutral", True, True, {"customer_name": "Priya Nair"}, [{"phrase": "next Tuesday", "due_date": "2026-09-22"}], ["confirm call time"], ["tuesday"])
E(MR, "James Cooper", "jcooper@summitcap.com", "Meeting request: partnership discussion",
  "Hello, I'd like to meet to discuss a possible partnership. I'm free on Wednesday at 11:00 in your office or on Zoom. Please confirm what works.",
  "MEDIUM", "Positive", True, True, {"customer_name": "James Cooper"}, [{"phrase": "Wednesday", "due_date": "2026-09-16"}], ["confirm meeting"], ["wednesday"])
E(MR, "Amna Yousuf", "amna@elevatehr.com", "Interview panel scheduling",
  "We need to schedule the final panel interview for the Product Manager role. The panel is available on Thursday at 14:00 or Friday at 10:00. Please pick one and confirm by tomorrow.",
  "MEDIUM", "Neutral", True, True, {}, [{"phrase": "tomorrow", "due_date": "2026-09-15"}], ["pick interview slot"], ["thursday", "friday"])
E(MR, "Luca Romano", "luca@romanodesign.it", "Project kickoff - proposed times",
  "Hi! To kick off the website project, could we meet on 25 September at 10:00 CET on Google Meet? If that doesn't work, suggest another day that week.",
  "MEDIUM", "Positive", True, True, {"meeting_date": "25 September"}, [{"phrase": "25 September", "due_date": "2026-09-25"}], ["confirm kickoff meeting"], ["25 september"])
E(MR, "Farah Anwar", "farah@anwarlegal.com", "Can we reschedule our Friday meeting?",
  "Something urgent came up on my side. Could we move our Friday meeting to next Monday at the same time? Apologies for the short notice.",
  "MEDIUM", "Neutral", True, True, {}, [{"phrase": "next Monday", "due_date": "2026-09-21"}], ["confirm rescheduled meeting"], ["monday"])
E(MR, "Mark Davidson", "mark.d@davidsonco.com", "Quarterly business review invite",
  "I'd like to set up our quarterly business review. Does Thursday at 15:00 in the Karachi office work? Please accept the calendar invite if it does.",
  "LOW", "Neutral", True, True, {"location": "Karachi"}, [{"phrase": "Thursday", "due_date": "2026-09-17"}], ["accept calendar invite"], ["thursday"])
E(MR, "Ines Costa", "ines@costaventures.pt", "Intro call with our CTO",
  "Our CTO would like a short intro call with your engineering lead. Any slot on Wednesday or Thursday this week would be great.",
  "LOW", "Positive", True, True, {}, [{"phrase": "Wednesday", "due_date": "2026-09-16"}], ["offer intro call slots"], ["wednesday", "thursday"])
E(MR, "Bashir Ahmad", "bashir@ahmadassociates.pk", "Lunch meeting this week",
  "Are you free for lunch on Friday? I'd like to talk through the contract renewal in person. Say 13:00 at the usual place?",
  "LOW", "Positive", True, False, {}, [{"phrase": "Friday", "due_date": "2026-09-18"}], [], ["friday"])
E(MR, "Rachel Green", "rachel@greenfieldschool.org", "Parent-teacher style demo session",
  "Could we book a one-hour training session for our staff at the school? We'd prefer the morning of 30 September, on site if possible.",
  "LOW", "Positive", True, True, {}, [{"phrase": "30 September", "due_date": "2026-09-30"}], ["book training session"], ["30 september"])
E(MR, "Tariq Jamil", "tariq@jamilgroup.com", "Board presentation dry run",
  "We should do a dry run of the board presentation before it goes live. Can we meet within 3 days? Conference room B is free on Thursday morning.",
  "MEDIUM", "Neutral", True, True, {"location": "Conference room B"}, [{"phrase": "within 3 days", "due_date": "2026-09-17"}], ["schedule dry run"], ["thursday"])

# ---------------------------------------------------------------- 10 invoice / payment
E(IP, "Accounts - Northwind", "accounts@northwind.com", "Invoice INV-2041 attached - due 30 September",
  "Dear customer,\n\nPlease find attached invoice INV-2041 for $2,450.00 covering August services. Payment is due by 30 September. Bank details are on the invoice.\n\nRegards,\nNorthwind Accounts",
  "MEDIUM", "Neutral", True, True, {"invoice_number": "INV-2041", "amount": "$2,450.00", "company": "Northwind"}, [{"phrase": "30 September", "due_date": "2026-09-30"}], ["pay invoice INV-2041"], ["inv-2041"])
E(IP, "Billing Team", "billing@cloudhost.io", "Payment failed for your hosting plan",
  "We couldn't charge the card on file for your hosting plan ($89). Please update your payment method within 3 days to avoid suspension of service.",
  "HIGH", "Neutral", True, True, {"amount": "$89"}, [{"phrase": "within 3 days", "due_date": "2026-09-17"}], ["update payment method"], ["payment"])
E(IP, "Sadia Rehman", "sadia@rehmantraders.pk", "Payment confirmation for invoice 7781",
  "Hi, I've transferred PKR 185,000 for invoice 7781 today. Reference number TRX-55512. Please confirm receipt and send an official receipt.",
  "MEDIUM", "Positive", True, True, {"invoice_number": "7781", "amount": "PKR 185,000"}, [], ["confirm receipt", "send receipt"], ["7781", "receipt"])
E(IP, "Collections", "collections@steelworks.com", "Reminder: invoice INV-1988 overdue",
  "This is a reminder that invoice INV-1988 for $5,200 is now 15 days overdue. Please arrange payment by Friday to avoid late fees.",
  "HIGH", "Negative", True, True, {"invoice_number": "INV-1988", "amount": "$5,200"}, [{"phrase": "Friday", "due_date": "2026-09-18"}], ["arrange payment"], ["inv-1988"])
E(IP, "Vendor Finance", "finance@officesupplyco.com", "Your receipt for order #6612",
  "Thank you for your payment of $134.50. Your receipt for order #6612 is attached. No further action is required.",
  "LOW", "Positive", False, False, {"order_number": "6612", "amount": "$134.50"}, [], [], [])
E(IP, "Zeeshan Haider", "zeeshan@haiderengineering.com", "Question about the amount on invoice 3305",
  "Invoice 3305 shows $4,800 but our purchase order agreed $4,200. Can you check and issue a corrected invoice before the end of this month?",
  "MEDIUM", "Neutral", True, True, {"invoice_number": "3305", "amount": "$4,800"}, [{"phrase": "end of this month", "due_date": "2026-09-30"}], ["issue corrected invoice"], ["3305", "corrected"])
E(IP, "Payroll", "payroll@brightpath.com", "Expense reimbursement approval needed",
  "Please approve the expense report of $612 submitted by Priya for the Dubai trip so payroll can include it in this cycle. Deadline for approval is Wednesday.",
  "MEDIUM", "Neutral", True, True, {"amount": "$612", "location": "Dubai"}, [{"phrase": "Wednesday", "due_date": "2026-09-16"}], ["approve expense report"], ["approve"])
E(IP, "Stripe", "receipts@stripe.com", "Your Stripe payout of $3,210 is on the way",
  "A payout of $3,210.00 has been initiated and should arrive in your bank account within 3 days. No action is needed.",
  "LOW", "Neutral", False, False, {"amount": "$3,210.00"}, [], [], [])
E(IP, "Credit Control", "credit@globalfreight.com", "Final notice - invoice GF-7720",
  "Final notice: invoice GF-7720 for $9,900 remains unpaid. If payment is not received by tomorrow we will pass the account to our collections agency.",
  "CRITICAL", "Negative", True, True, {"invoice_number": "GF-7720", "amount": "$9,900"}, [{"phrase": "tomorrow", "due_date": "2026-09-15"}], ["pay invoice GF-7720"], ["gf-7720", "payment"])
E(IP, "Neha Sharma", "neha@sharmaconsulting.in", "Could you resend invoice for August?",
  "I can't find the August invoice in my inbox. Could you please resend it? We need it for our books this week.",
  "LOW", "Neutral", True, True, {}, [], ["resend August invoice"], ["invoice"])

# ---------------------------------------------------------------- 10 job applications
E(JA, "Ahmed Siddiqui", "ahmed.siddiqui@gmail.com", "Application for Backend Developer position",
  "Dear Hiring Manager,\n\nI'm applying for the Backend Developer role. I have 4 years of experience with Python and FastAPI. My CV is attached. I'm available for an interview next week.\n\nAhmed Siddiqui\n+92 321 5550101",
  "MEDIUM", "Positive", True, True, {"customer_name": "Ahmed Siddiqui", "phone_number": "+92 321 5550101"}, [], ["review application"], ["application", "interview"])
E(JA, "Mei Lin", "mei.lin@outlook.com", "Data Scientist application - Mei Lin",
  "Hello, I would like to apply for the Data Scientist opening posted on LinkedIn. I hold an MSc in Statistics and have worked on churn models for two years. Resume attached.",
  "MEDIUM", "Positive", True, True, {"customer_name": "Mei Lin"}, [], ["review application"], ["application"])
E(JA, "Carlos Mendes", "carlos.mendes@proton.me", "Internship enquiry",
  "Hi, I'm a final-year computer science student and I'm looking for a summer internship. Do you have any openings in engineering? I've attached my CV.",
  "LOW", "Positive", True, False, {}, [], [], ["internship"])
E(JA, "Sara Bashir", "sara.bashir@gmail.com", "Following up on my application",
  "I applied for the UX Designer role two weeks ago and haven't heard back. Could you let me know the status of my application? Thank you for your time.",
  "LOW", "Neutral", True, True, {"customer_name": "Sara Bashir"}, [], ["update applicant on status"], ["status"])
E(JA, "Liam Walker", "liam.walker@walkerdev.com", "Senior Frontend Engineer - application",
  "Please accept my application for the Senior Frontend Engineer role. I've led React teams for six years. Portfolio: walkerdev.com. I can start with one month notice.",
  "MEDIUM", "Positive", True, True, {"customer_name": "Liam Walker"}, [], ["review application"], ["application"])
E(JA, "Noor Fatima", "noor.fatima@yahoo.com", "Application: Marketing Executive",
  "Respected Sir/Madam, I wish to apply for the Marketing Executive position. I have two years of experience in social media campaigns. CV attached. Kindly consider my application.",
  "MEDIUM", "Positive", True, True, {"customer_name": "Noor Fatima"}, [], ["review application"], ["application"])
E(JA, "Peter Schmidt", "p.schmidt@web.de", "Request to reschedule interview",
  "Thank you for inviting me for an interview on Thursday. Unfortunately I have a clash. Would Friday morning be possible instead?",
  "MEDIUM", "Neutral", True, True, {}, [{"phrase": "Friday", "due_date": "2026-09-18"}], ["reschedule interview"], ["friday"])
E(JA, "Aisha Rahman", "aisha.rahman@gmail.com", "Referral for DevOps role",
  "Hi, Usman from your platform team suggested I send my CV for the DevOps Engineer opening. I have strong experience with Kubernetes and Terraform. Hope to hear from you.",
  "MEDIUM", "Positive", True, True, {"customer_name": "Aisha Rahman"}, [], ["review application"], ["devops"])
E(JA, "Victor Ionescu", "victor@ionescu.ro", "Offer acceptance",
  "I am delighted to accept your offer for the Project Manager position. I will sign the contract and return it by Friday. Looking forward to joining on 1 October.",
  "MEDIUM", "Positive", True, True, {"customer_name": "Victor Ionescu"}, [{"phrase": "Friday", "due_date": "2026-09-18"}], ["send onboarding details"], ["welcome"])
E(JA, "Zainab Ali", "zainab.ali@gmail.com", "Graduate programme - cover letter",
  "Dear team, please find my cover letter and transcript for your graduate programme. I am particularly interested in the analytics track. Thank you for considering me.",
  "LOW", "Positive", True, False, {"customer_name": "Zainab Ali"}, [], [], ["graduate"])

# ---------------------------------------------------------------- 10 general information
E(GI, "HR Department", "hr@brightpath.com", "Office closed on Monday for public holiday",
  "Dear all, the office will be closed next Monday for the public holiday. Normal working hours resume on Tuesday. Enjoy the long weekend.",
  "LOW", "Neutral", False, False, {}, [], [], [])
E(GI, "IT Support", "it@brightpath.com", "Scheduled maintenance this weekend",
  "FYI: the internal wiki will be offline for maintenance on Saturday between 02:00 and 04:00. No action is needed from you.",
  "LOW", "Neutral", False, False, {}, [], [], [])
E(GI, "Product Team", "product@brightpath.com", "Release notes - version 4.8",
  "Hi everyone, version 4.8 is live. Highlights: faster search, new dashboard widgets and improved export. Full release notes are on the wiki.",
  "LOW", "Positive", False, False, {}, [], [], [])
E(GI, "Newsletter", "news@techweekly.com", "This week in AI - issue 212",
  "Welcome to this week's issue. Stories: new open-weight models, a look at vector databases, and tips for writing better prompts. Read on for the full roundup.",
  "LOW", "Neutral", False, False, {}, [], [], [])
E(GI, "CEO Office", "ceo@brightpath.com", "Company all-hands recap",
  "Thanks to everyone who joined the all-hands. The slides and recording are now in the shared drive. Please send any questions to your team lead.",
  "LOW", "Positive", False, False, {}, [], [], [])
E(GI, "Facilities", "facilities@brightpath.com", "New parking arrangements",
  "From next month the visitor parking area will be reserved for guests only. Staff are asked to use the south lot. Maps are posted at reception.",
  "LOW", "Neutral", False, False, {}, [], [], [])
E(GI, "Legal", "legal@brightpath.com", "Updated data-protection policy",
  "Please be aware that our data-protection policy has been updated. A summary of the changes is available on the intranet. You are not required to respond.",
  "LOW", "Neutral", False, False, {}, [], [], [])
E(GI, "Community Manager", "community@opensourceconf.org", "Thank you for speaking at the conference",
  "Thank you for your talk last week - the feedback has been wonderful. Recordings will be published soon. We hope to see you again next year.",
  "LOW", "Positive", False, False, {}, [], [], [])
E(GI, "Finance Ops", "finops@brightpath.com", "Quarterly results summary",
  "Hi all, Q3 results are in and the summary deck is attached for your information. Revenue was up on the previous quarter. We'll discuss details at the next all-hands.",
  "LOW", "Positive", False, False, {}, [], [], [])
E(GI, "Alex Morgan", "alex.morgan@partnerco.com", "FYI: we moved offices",
  "Just letting you know that our company has moved to a new address. Our phone numbers and email addresses stay the same. Nothing for you to do.",
  "LOW", "Neutral", False, False, {}, [], [], [])

# ---------------------------------------------------------------- 10 urgent
E(UR, "Security Ops", "secops@brightpath.com", "URGENT: suspicious logins detected on admin account",
  "We detected 40 failed and 3 successful logins from an unknown IP on the admin account in the last hour. Please rotate credentials and confirm back immediately.",
  "CRITICAL", "Urgent", True, True, {}, [], ["rotate admin credentials"], ["credentials"])
E(UR, "Plant Manager", "plant@steelworks.com", "Production line down - need help now",
  "Line 3 has been down since 06:00 and we are losing roughly $8,000 per hour. We need your engineer on the phone within the hour. Call me on +92 300 1112223.",
  "CRITICAL", "Urgent", True, True, {"phone_number": "+92 300 1112223", "amount": "$8,000"}, [], ["call plant manager"], ["engineer"])
E(UR, "Dr. Imtiaz", "imtiaz@cityclinic.pk", "Patient portal is down - urgent",
  "Our patient portal has been returning errors since 08:30 and patients cannot access their reports. Please treat this as top priority and update me every 30 minutes.",
  "CRITICAL", "Urgent", True, True, {}, [], ["restore patient portal"], ["priority", "update"])
E(UR, "Legal Counsel", "counsel@lawgroup.com", "Court filing deadline tomorrow",
  "We must file the signed affidavit with the court by tomorrow noon. I still need your signature page. Please return it today without fail.",
  "CRITICAL", "Urgent", True, True, {}, [{"phrase": "tomorrow", "due_date": "2026-09-15"}], ["return signature page"], ["signature"])
E(UR, "Karen Phillips", "karen@bigretail.com", "Website checkout failing during our sale",
  "Our checkout is throwing errors in the middle of our biggest sale of the year. Every minute counts. Need someone to look at this immediately.",
  "CRITICAL", "Urgent", True, True, {}, [], ["fix checkout"], ["immediately", "checkout"])
E(UR, "Shipping Desk", "desk@globalfreight.com", "Shipment held at customs - action needed today",
  "Container MSKU-884412 is held at the port pending your commercial invoice. Demurrage charges start tomorrow. Send the missing document today.",
  "HIGH", "Urgent", True, True, {}, [{"phrase": "tomorrow", "due_date": "2026-09-15"}], ["send commercial invoice"], ["document"])
E(UR, "CFO Office", "cfo@brightpath.com", "Need the audit figures before 3pm",
  "The auditors are in the building and need the reconciled bank statements before 3pm today. Please send them to me as soon as possible.",
  "HIGH", "Urgent", True, True, {}, [], ["send reconciled bank statements"], ["statements"])
E(UR, "Data Center", "noc@datahost.net", "Disk failure on your primary server",
  "Disk 2 on your primary database server has failed and the array is degraded. Another failure would cause data loss. Please authorise the replacement right away.",
  "CRITICAL", "Urgent", True, True, {}, [], ["authorise disk replacement"], ["replacement"])
E(UR, "Hospital Admin", "admin@cityhospital.pk", "Emergency: backup generator contract lapsed",
  "Our backup generator service contract lapsed last night. If we lose power we have no cover. We need this renewed today - please call me urgently.",
  "CRITICAL", "Urgent", True, True, {}, [], ["renew generator contract"], ["renew"])
E(UR, "Client Lead", "lead@megaclient.com", "Escalation: executive demo in two hours",
  "Our executive team demo starts in two hours and the staging environment is returning errors. We need it fixed before then or we risk losing the deal.",
  "CRITICAL", "Urgent", True, True, {}, [], ["fix staging environment"], ["staging"])

# ---------------------------------------------------------------- 10 spam
E(SP, "Prize Center", "winner@lucky-draw-prizes.biz", "CONGRATULATIONS! You won $1,000,000",
  "You have been selected as the winner of our international lottery! Click the link below and send your bank details to claim your $1,000,000 prize today. Limited time only!!!",
  "LOW", "Positive", False, False)
E(SP, "Cheap Meds", "offers@pharma-discount24.ru", "Buy cheap pills online - 90% off",
  "Best prices on all medications, no prescription needed! Order now and get free shipping. Click here to buy. Unsubscribe at the bottom if you don't want these offers.",
  "LOW", "Neutral", False, False)
E(SP, "SEO Experts", "growth@rankfast-seo.xyz", "Get to #1 on Google in 7 days guaranteed",
  "Hello Sir, we can put your website on the first page of Google in just 7 days. 100% guaranteed results. Reply now for a special discount package. Hurry, offer ends tonight!",
  "LOW", "Neutral", False, False)
E(SP, "Crypto Gains", "invest@double-your-btc.top", "Double your Bitcoin in 24 hours",
  "Send us 0.1 BTC and we will return 0.2 BTC within 24 hours. No risk. Thousands of satisfied investors. Act now before this opportunity disappears!",
  "LOW", "Positive", False, False)
E(SP, "Account Security", "security@paypa1-verify.com", "Your account has been limited - verify now",
  "Dear user, we noticed unusual activity. Your account will be closed unless you confirm your password and card number at the link below within 24 hours.",
  "LOW", "Urgent", False, False)
E(SP, "Dream Jobs", "hr@work-from-home-cash.info", "Earn $500 a day from home!!!",
  "No experience needed! Work only 2 hours a day and make $500 daily. Just pay a small registration fee to get started. Join thousands of happy members today!",
  "LOW", "Positive", False, False)
E(SP, "Luxury Watches", "sales@replica-watches-outlet.cn", "Rolex watches 80% off",
  "Genuine-looking luxury watches at unbeatable prices. Buy 2 get 1 free. Visit our outlet now. Delivery worldwide. Unsubscribe here.",
  "LOW", "Neutral", False, False)
E(SP, "Dear Friend", "prince.abubakar@royalmail-ng.org", "Business proposal - confidential",
  "Dear Friend, I am a lawyer representing a late client who left $12.5 million with no heirs. I need your help to transfer the funds. You will receive 30 percent. Reply with your details urgently.",
  "LOW", "Neutral", False, False)
E(SP, "Weight Loss Pro", "info@slimfast-miracle.shop", "Lose 20 pounds in 2 weeks with this one trick",
  "Doctors hate this simple trick! Lose 20 pounds in 2 weeks without diet or exercise. Order today and get a free bonus bottle. Limited stock!",
  "LOW", "Positive", False, False)
E(SP, "Survey Rewards", "rewards@free-gift-survey.click", "Claim your free iPhone - 2 minute survey",
  "You have been chosen to receive a brand new iPhone. Complete this short survey to claim your free gift. Hurry, only 3 left!",
  "LOW", "Positive", False, False)

assert len(DATA) == 90, len(DATA)
for cat in {d["expected"]["category"] for d in DATA}:
    assert sum(d["expected"]["category"] == cat for d in DATA) == 10, cat

if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(DATA, fh, indent=2, ensure_ascii=False)
    print(f"wrote {len(DATA)} emails -> {OUT}")
