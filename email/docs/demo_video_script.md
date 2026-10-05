# Demo Video Recording Script & Feature Walkthrough Guide

This document provides a scene-by-scene recording script, speaker narration, and visual walkthrough guide for recording the Smart Email Intelligence system demo video.

---

## 🎬 Video Overview & Timestamp Breakdown

- **Total Duration**: 3 - 5 Minutes
- **Target Audience**: Stakeholders & Technical Evaluators
- **System Stack**: Next.js 14, FastAPI, SQLAlchemy, Redis, Celery, Vector Embeddings RAG, Multi-Tenant JWT Security.

---

## 📹 Scene-by-Scene Script

### Scene 1: Introduction & Authentication (0:00 - 0:45)
- **Visual**: Show Login Page (`http://localhost:3000/login`).
- **Action**: Click "Fill Demo Admin Credentials" or enter email & password. Click "Sign In".
- **Speaker Narration**:
  > "Welcome to the Smart Email Intelligence Platform. In this demonstration, we'll explore how our multi-tenant AI system automatically ingests, classifies, extracts metadata, and generates contextual replies for inbox workflows.
  > We log into our secure dashboard powered by JWT access tokens with token revocation capabilities."

### Scene 2: Dashboard & Real-Time Inbox Analytics (0:45 - 1:30)
- **Visual**: Show Dashboard Page (`/dashboard`).
- **Action**: Hover over KPI cards (Total Emails, Urgent Emails, Pending Actions), inspect Category Breakdown, and view Urgent Action Items.
- **Speaker Narration**:
  > "Upon login, the executive dashboard provides instant visibility into urgent emails requiring action, SLA compliance, response time targets, and automated category distribution across customer complaints, sales inquiries, and support requests."

### Scene 3: Multi-Format Ingestion & Parsing (1:30 - 2:30)
- **Visual**: Click "+ Add / Upload Email" button to open [UploadModal.tsx](file:///d:/Projects/email/frontend/src/components/UploadModal.tsx).
- **Action**:
  1. Show File Upload tab (.EML, .JSON, .CSV support).
  2. Switch to Paste Raw Text tab and paste an RFC 822 email.
  3. Submit to run real-time AI analysis.
- **Speaker Narration**:
  > "Our platform supports seamless multi-format ingestion. Users can upload raw `.EML` files, batch `.CSV` and `.JSON` datasets, or paste raw email header text.
  > The background pipeline immediately runs SHA-256 deduplication, thread matching, and AI analysis."

### Scene 4: AI Analysis, Extractions & Smart Reply (2:30 - 3:45)
- **Visual**: Navigate to Inbox (`/inbox`) and open an email detail view (`/inbox/1`).
- **Action**:
  1. Show extracted metadata (Order ID, Amount, Phone Number, Date).
  2. Show Action Items checklist and Deadline badges.
  3. Click "Generate AI Smart Reply", select tone (Professional / Apologetic / Concise), draft response, click Approve or Reject with feedback.
- **Speaker Narration**:
  > "Inside the email detail view, the AI engine extracts key entities such as order IDs, amounts, and phone numbers. It identifies action items and flags deadlines.
  > When replying, the Smart Reply engine generates context-aware responses across 6 distinct tones. If a user rejects a draft, feedback is captured for audit logging."

### Scene 5: RAG AI Assistant & Vector Embeddings (3:45 - 4:30)
- **Visual**: Navigate to Assistant page (`/assistant`).
- **Action**: Type a natural language query: *"Show me urgent customer complaints with order refunds"*. Show retrieved email citations.
- **Speaker Narration**:
  > "Our RAG AI Assistant combines structured SQL query resolution with TF-IDF cosine similarity vector embeddings. It retrieves exact matching emails and synthesizes clear, cited answers with conversation memory."

### Scene 6: Admin Portal & System Governance (4:30 - 5:00)
- **Visual**: Navigate to Admin Portal (`/admin`).
- **Action**: Switch through tabs: Users & RBAC, Category Editor, System Settings, AI Execution Diagnostics, and Audit Trail.
- **Speaker Narration**:
  > "Finally, the Admin Portal allows managers to manage user roles, customize categories, configure AI engine providers, inspect diagnostic execution logs, and monitor security audit trails."
