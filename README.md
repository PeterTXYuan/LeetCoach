# LeetCoach

LeetCoach is a Chrome extension that helps users learn how to think through LeetCode problems instead of immediately showing final answers.

## Vision

Don't give me the answer.
Teach me how to discover it.

## MVP

The first milestone focuses on a small working loop:

- Open LeetCoach from the Chrome extension toolbar.
- Show a side panel home experience.
- Detect supported `leetcode.com/problems/*` pages.
- Fetch pattern information from a local backend.
- Show guided thinking steps from a mock AI provider.

## Current Status

This repository currently contains the initial Chrome extension side panel scaffold built with React, TypeScript, Vite, and Manifest V3.

## Development

Install dependencies:

```bash
npm install
```

Build the extension:

```bash
npm run build
```

The Chrome-loadable extension bundle is generated in `dist/`.

## Backend

Install backend dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Run the local FastAPI server:

```bash
uvicorn app.main:app --reload
```

The backend serves `GET /health` and `GET /api/problems/{slug}` at `http://localhost:8000`.
