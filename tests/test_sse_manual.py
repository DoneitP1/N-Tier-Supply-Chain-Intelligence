import redis
import json
import time
import requests
import threading

def simulate_redis_publish(user_id, doc_id, filename):
    time.sleep(2)
    r = redis.from_url("redis://localhost:6379/0")
    payload = {
        "id": doc_id,
        "filename": filename,
        "status": "processed",
        "created_at": "2024-03-24T12:00:00Z"
    }
    print(f"Publishing to ingestion_updates:{user_id}...")
    r.publish(f"ingestion_updates:{user_id}", json.dumps(payload))

def test_sse():
    # Note: This requires the server to be running and authentication to be bypassed or a real token provided.
    # For a unit-like test, we can mock the redis part if we just want to test the routing, 
    # but here we'll assume a local dev environment.
    
    print("This script is a guide for manual/semi-automated verification.")
    print("To verify SSE:")
    print("1. Start the FastAPI server.")
    print("2. Run this script's publish function while listening to /api/ingest/events.")
    
    # In a real scenario, I'd use a tool to run the server and client.
    # However, since I can't easily run a persistent server and a long-lived sse client in one go here,
    # I will provide this script as an artifact/tool for the user or for my own execution if I start the server.

if __name__ == "__main__":
    # Example usage:
    # simulate_redis_publish(user_id=1, doc_id=123, filename="test.pdf")
    test_sse()
