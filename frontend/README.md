# N-Tier Supply Chain Intelligence - Next.js Frontend

This is the modern, interactive React-based frontend for the N-Tier platform.

## Features
- **Next.js 14+**: Leverages App Router for high performance.
- **React Flow**: Highly interactive, node-based knowledge graph visualization.
- **Tailwind CSS**: Premium, dark-themed corporate SaaS aesthetic.
- **Zustand**: Fast and lightweight local state management for Auth and UI.
- **Real-time Ingestion**: Track PDF processing status via background worker integration.

## Getting Started

1.  **Navigate to the frontend directory**:
    ```bash
    cd frontend
    ```

2.  **Install dependencies**:
    ```bash
    npm install
    ```

3.  **Run the development server**:
    ```bash
    npm run dev
    ```

4.  **Open the app**:
    Navigate to [http://localhost:3000](http://localhost:3000) in your browser.

## Backend Connection
The frontend expects the FastAPI backend to be running on [http://localhost:8000](http://localhost:8000). You can customize this by setting the `NEXT_PUBLIC_API_URL` environment variable.
