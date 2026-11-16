"""End-to-end verification script testing chat and hardware endpoints via TestClient."""
import json
from fastapi.testclient import TestClient
from app.main import app

def run_e2e():
    print("=" * 60)
    print("STARTING E2E VERIFICATION FOR LINUX HARDWARE AI ASSISTANT")
    print("=" * 60)

    client = TestClient(app)

    # 1. Health check
    print("\n1. Testing GET /api/health...")
    res = client.get("/api/health")
    print(f"Status: {res.status_code}")
    print(f"Response: {json.dumps(res.json(), indent=2)}")
    assert res.status_code == 200

    # 2. Hardware summary
    print("\n2. Testing GET /api/hardware...")
    res = client.get("/api/hardware")
    print(f"Status: {res.status_code}")
    hw_data = res.json()
    print(f"Detected OS: {hw_data['environment']['distro_name']} (WSL2: {hw_data['environment']['is_wsl2']})")
    print(f"CPU Model: {hw_data['cpu']['model']}")
    print(f"RAM Total: {hw_data['ram']['total_human']}")
    print(f"GPU Count: {hw_data['gpu']['count']}")
    print(f"Storage Devices: {len(hw_data['storage']['devices'])}")
    assert res.status_code == 200

    # 3. Chat: Single-tool question
    print("\n3. Testing POST /api/chat ('How much RAM do I have?')...")
    res = client.post("/api/chat", json={"message": "How much RAM do I have?", "history": []})
    print(f"Status: {res.status_code}")
    chat1 = res.json()
    print(f"Tools Used: {chat1['tools_used']}")
    print(f"Answer snippet: {chat1['answer'][:200]}...")
    assert res.status_code == 200
    assert "inspect_ram" in chat1["tools_used"]

    # 4. Chat: Multi-tool question (RAM upgrade)
    print("\n4. Testing POST /api/chat ('Can I upgrade my RAM to 32 GB?')...")
    res = client.post("/api/chat", json={"message": "Can I upgrade my RAM to 32 GB?", "history": []})
    print(f"Status: {res.status_code}")
    chat2 = res.json()
    print(f"Tools Used: {chat2['tools_used']}")
    print(f"Answer snippet:\n{chat2['answer'][:300]}...")
    assert res.status_code == 200
    assert "inspect_ram" in chat2["tools_used"]
    assert "inspect_memory_slots" in chat2["tools_used"]

    # 5. Chat: GPU and Follow-up Question
    print("\n5. Testing POST /api/chat ('What GPU do I have?' + Follow-up: 'Is it good for machine learning?')...")
    res_gpu = client.post("/api/chat", json={"message": "What GPU do I have?", "history": []})
    gpu_ans = res_gpu.json()["answer"]
    
    # Follow-up with history
    history = [
        {"role": "user", "content": "What GPU do I have?"},
        {"role": "assistant", "content": gpu_ans},
    ]
    res_ml = client.post(
        "/api/chat",
        json={"message": "Is it good for machine learning?", "history": history},
    )
    ml_ans = res_ml.json()
    print(f"Follow-up Answer snippet:\n{ml_ans['answer'][:300]}...")
    assert "machine learning" in ml_ans["answer"].lower() or "cuda" in ml_ans["answer"].lower()

    # 6. Static files
    print("\n6. Testing GET / (Static HTML Dashboard)...")
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "Linux Hardware AI Assistant" in res_html.text
    print("Static HTML served successfully.")

    print("\n" + "=" * 60)
    print("ALL E2E VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_e2e()
