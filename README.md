# 🚀 Skills Mirage — Real-Time AI Job Intelligence Platform

> Bridging the gap between **job market reality** and **personal career strategy** in the age of AI disruption.

---

## 🧠 The Problem

Millions of Indian workers are facing **AI-driven job displacement** with little to no visibility into:

* Which skills are becoming obsolete
* Which skills are emerging
* What actionable steps they should take

Existing platforms fall short:

* Government portals are static
* Job boards provide listings, not intelligence

---

## 💡 The Solution

**Skills Mirage** transforms fragmented job data into **real-time, personalized intelligence**.

* 📊 **Layer 1:** Live job market analytics
* 🧑‍💼 **Layer 2:** Personalized reskilling engine
* 🕸️ **Overlay:** Interactive knowledge graph

👉 All powered by real-time data + AI-driven insights

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│ FRONTEND · React + Vite + Three.js                       │
│ Dashboard · Worker Engine · Chatbot · Knowledge Graph    │
├──────────────────────────────────────────────────────────┤
│ BACKEND · Express + Socket.IO                            │
│ Scrapers · AI Services · REST API · WebSocket            │
├──────────────────────────────────────────────────────────┤
│ DATA · MongoDB + Redis                                   │
│ Job Listings · Worker Profiles · Skills Graph            │
├──────────────────────────────────────────────────────────┤
│ AI · Gemini 2.0 Flash + Claude API                       │
│ Risk Scoring · NLP · Chatbot · Graph Generation          │
└──────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 📊 [01] Job Market Dashboard

* Live scraping from Naukri + LinkedIn across 22 cities (Tier 1–3)
* Real-time hiring trends by city, sector, and role
* Skill intelligence (rising vs declining, week-over-week)
* AI Vulnerability Index (0–100) with transparent scoring

---

### 🧑‍💼 [02] Worker Intelligence Engine

* Inputs: job title, city, experience, user write-up
* Personalized AI Risk Score (0–100)
* Dynamic reskilling roadmap with real courses (NPTEL, SWAYAM, PMKVY)
* Context-aware recommendations (location + market specific)

---

### 🤖 [03] AI Chatbot

* Context-aware assistant (English + Hindi)
* Handles: risk, skills, courses, trends, career advice
* Powered by Claude API with conversation memory

---

### 🕸️ [04] Knowledge Graph

* Upload resume + GitHub profile
* Interactive 3D graph (Three.js)
* Maps skills, projects, certifications
* AI-powered extraction using Gemini

---

## 🛠️ Tech Stack

| Layer          | Stack                                                            |
| -------------- | ---------------------------------------------------------------- |
| **Frontend**   | React 18, Vite, TypeScript, TailwindCSS, Framer Motion, Three.js |
| **Backend**    | Express.js, TypeScript, MongoDB (Mongoose), Redis, Socket.IO     |
| **AI**         | Gemini 2.0 Flash, Claude API                                     |
| **Scraping**   | Puppeteer, Cheerio, Octokit, Apify                               |
| **Graph**      | @react-three/fiber, d3-force-3d                                  |
| **Deployment** | Docker Compose                                                   |

---

## ⚡ Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/skills-mirage.git
cd skills-mirage

# Setup environment variables
cp .env.example .env

# Start infrastructure (MongoDB + Redis)
docker-compose up -d

# Install dependencies
npm install

# Seed database
npm run db:seed

# Run development servers
npm run dev
```

👉 Open: http://localhost:5173

---

## 📁 Project Structure

```
src/
├── frontend/                 # React + Vite app
│   ├── components/           # UI components
│   ├── hooks/                # Custom hooks
│   ├── pages/                # Route pages
│   └── utils/                # Helper functions
├── backend/                  # Express API
│   ├── routes/               # REST endpoints
│   ├── services/             # Business logic + AI
│   ├── models/               # Database schemas
│   └── scripts/              # Scrapers & seeders
└── shared/                   # Shared types
```

---

## 🧪 Scripts

| Command                 | Description            |
| ----------------------- | ---------------------- |
| `npm run dev`           | Run frontend + backend |
| `npm run dev:frontend`  | Frontend only          |
| `npm run dev:backend`   | Backend only           |
| `npm run scrape:naukri` | Run Naukri scraper     |
| `npm run scrape:github` | Scrape GitHub profiles |
| `npm run db:seed`       | Seed sample data       |
| `npm run build`         | Production build       |

---

## 🎨 Design System

* 🌑 Dark theme: `#0a0a0a` (never pure black)
* 🌊 Accent gradient: `#00d4aa → #00bcd4`
* 🔤 Typography: Playfair Display (headings), DM Sans (body)
* 📐 Grid: Crosshair overlay with markers
* 🎞️ Motion: Aurora streaks, dot-matrix, smooth transitions

---

## ⚠️ Notes

* Ensure MongoDB and Redis are running (via Docker)
* Add valid API keys in `.env`
* Do NOT commit `.env` files
* Rotate keys immediately if exposed

---

## 🔮 Future Scope

* Real-time job alerts
* Predictive career trajectory modeling
* Enterprise dashboards for policy makers
* Mobile-first experience

---

## 💬 Final Note

Built with high-intensity iteration, real-world problem focus, and a clear objective:

> Turning job uncertainty into **actionable intelligence**.

---
