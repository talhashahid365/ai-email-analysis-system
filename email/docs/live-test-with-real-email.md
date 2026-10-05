# Live test with your real e-mail (admin flow)

Goal: a customer e-mails you -> it shows up in the website -> you reply as admin -> the customer really gets the
reply and the website records (inbox status, dashboard "Replied", Response Status chart) update.

## 1. One-time setup (Gmail)
1. Google Account -> Security -> turn on 2-Step Verification -> create an **App password**.
2. Gmail -> Settings -> Forwarding and POP/IMAP -> **Enable IMAP**.
3. In `backend/.env` set (same app password for both):
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=you@gmail.com
   SMTP_PASSWORD=<app password>
   IMAP_HOST=imap.gmail.com
   IMAP_USER=you@gmail.com
   IMAP_PASSWORD=<app password>
   GEMINI_API_KEY=<your key>
   GEMINI_MODEL=gemini-3.5-flash
   ```
4. Easiest start: copy `backend/.env.local.example` to `backend/.env` and fill the Gmail lines.
5. Check the mail settings: `cd backend && python check_mail.py` (add `--send-test other@address.com` to send one test e-mail). Every line must say OK.
6. Restart the backend. (Optional AI key check: `python check_llm.py`.)
7. Register in the website with ANY e-mail first (the first account becomes admin), or run `python make_admin.py`.

## 1b. Automatic mode (no buttons, no dummy data)
With the IMAP lines filled in, the backend checks the mailbox by itself every `IMAP_SYNC_INTERVAL_SECONDS` (30 s)
and the Inbox page re-reads the list every 15 s (green "Live" dot). A customer's mail, and any follow-up reply they
send to your answer, appears on its own. Every follow-up lands in the same conversation, shown in the
"Conversation" panel of the open email, and is marked "Waiting for your reply". Only mail from the last
`IMAP_SINCE_DAYS` (3) days is imported.

## 2. Test
1. From a **different** address (your phone / second Gmail) send a query to `you@gmail.com`,
   e.g. "Please refund order #1029, the product arrived damaged."
   (Mail sent *by* `you@gmail.com` itself is ignored on purpose.)
2. Website -> Inbox -> **Sync Mailbox**. The message appears with Category / Priority / Sentiment filled by Gemini.
3. Open it -> pick a tone -> edit the draft -> **Approve & Transmit**.
   - Green message "Reply e-mailed to ..." = it was really sent. Check the second address's inbox.
   - Amber message "NOT e-mailed" = SMTP is not set up, the reply is only recorded.
   - Red message = Gmail rejected it (nothing was recorded as replied).
4. Verify the records:
   - Inbox: the email's reply status becomes `replied`; the thread shows your outbound message.
   - Dashboard: **Email Activity** "Replied" line rises for today; **Response Status** donut moves from
     Pending to Responded; average response time appears.
   - Admin -> audit log: `ai.approve_reply` with `delivered: true`.

## 3. Automated version of the same flow
`cd backend && python -m pytest tests/test_reply_roundtrip.py -v` (SMTP/IMAP are faked, no real mail is sent).

## Known limits
- Replies you type directly in Gmail (not through the website) are ignored on purpose and do not mark the mail as "replied".
- Only the newest `IMAP_MAX_FETCH` messages are checked per sync; older ones are skipped.

## Troubleshooting: "TimeoutError" / "handshake operation timed out"
The connection to Gmail opens but the TLS handshake hangs (router, antivirus or VPN interfering). The backend now retries
automatically with TLS 1.2 only (`MAIL_TLS_MODE=auto`). `python check_mail.py` prints which mode worked. If it still fails:
try the phone hotspot, turn off the antivirus' e-mail/HTTPS scanning, or set `SMTP_PORT=465`.
