import httpx

async def dispatch_notification(webhook_url: str, message: str, image_path: str = None) -> dict:
    """Sends a markdown message to a webhook (e.g., Feishu, ServerChan)."""
    if not webhook_url or webhook_url == "dummy":
        return {"status": "mock", "message": "No real webhook configured, printing to console", "content": message}
        
    try:
        payload = {"msg_type": "text", "content": {"text": message}}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            
        if response.status_code == 200:
            return {"status": "success"}
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
