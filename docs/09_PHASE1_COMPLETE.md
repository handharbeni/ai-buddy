# BAPENDA Local AI Platform - Frontend Implementation

## Overview

This document outlines the frontend implementation plan for the BAPENDA Local AI Platform using Next.js 14 with App Router.

## Frontend Architecture

### Core Principles

1. **Security by Design**: All client-side communication requires JWT authentication
2. **Scope Enforcement**: Frontend respects data scope limitations set by backend
3. **Accessibility**: WCAG 2.1 AA compliant
4. **Performance**: Optimized for low-bandwidth environments
5. **Mobile First**: Responsive design for all device sizes

### Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Next.js 14 | 14.0+ |
| Language | TypeScript | 5.0+ |
| Styling | Tailwind CSS | 3.4+ |
| Routing | App Router | File-based |
| API Client | Custom API client | - |
| State Management | React Context + SWR | - |
| Testing | Playwright | 1.40+ |

## File Structure

```
/frontend/
├── package.json
├── tsconfig.json
├── next.config.js
├── .env.local
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── admin/
│   │   │   └── page.tsx
│   │   ├── audit/
│   │   │   └── page.tsx
│   │   └── settings/
│   │       └── page.tsx
│   └── components/
│       ├── ChatMessage.tsx
│   │   ├── ToolResult.tsx
│   │   ├── DataTable.tsx
│   │   ├── Chart.tsx
│   │   └── Citation.tsx
│   └── lib/
│       ├── api.ts
│       └── auth.ts
├── tests/
│   └── e2e/
│       └── login.spec.ts
└── public/
    └── favicon.ico
```

## Phase 1: Setup and Configuration

### 1.1 Environment Variables

Create `.env.example` with:

```env
NEXT_PUBLIC_API_URL=https://api.bapenda.local
NEXT_PUBLIC_WS_URL=wss://api.bapenda.local
NEXT_PUBLIC_TELEMETRY_DISABLED=1
```

### 2. Initialization

```bash
# Create project
npx create-next-app@latest frontend --typescript --eslint --app

# Install dependencies
cd frontend && npm install

# Copy environment template
cp .env.example .env

# Install additional dependencies
npm install axios swr tailwindcss postcss autoprefixer eslint eslint-config-next