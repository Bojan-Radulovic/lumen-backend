from faststream.rabbit import RabbitBroker

async def tts_service(text, current_user: dict):
    message = {
        'text': text,
    }
    print("Sending answer to TTS...")
    try:
        async with RabbitBroker("amqp://guest:guest@localhost:5672/") as tts_broker:
            response = await tts_broker.publish(
                message,
                queue="to_tts",
                rpc=True,
                timeout=2000.0,
            )
        print("I received a response")
        return {
            "audio_bytes": response.get("audio_bytes"),
            "answer": text,
        }
    except Exception as e:
        print(f"TTS Error: {e}")
        return {
            "audio_bytes": None,
            "answer": text,
        }