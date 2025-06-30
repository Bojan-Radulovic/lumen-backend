from models import StreamRequest
from services.chats import create_chat, get_chat_history_for_memory, add_message
from services.database import get_db_connection_service
from services.agent import create_agent_with_tools
from typing import List
import re
from faststream.rabbit import RabbitBroker
from constants import OUTPUT_DIR
import os
import json
import base64
from fastapi.responses import StreamingResponse

def format_question_with_history(question: str, chat_history: List[dict]):
    """Add conversation history to the question"""
    if chat_history:
        history_text = ""
        
        for msg in chat_history:
            role = "Human" if msg['is_human'] else "Assistant"
            history_text += f"{role}: {msg['content']}\n"
        
        if history_text.strip():
            return f"""Previous conversation:
{history_text.strip()}

Current question: {question}

Remember our conversation history when responding."""
    
    return question

async def stream_response_service(request: StreamRequest, current_user: dict):
    question = request.question
    chat_id = request.chat_id
    
    if not chat_id:
        title_words = question.split()[:5]
        chat_title = " ".join(title_words) if title_words else "New Chat"
        if len(chat_title) > 50:
            chat_title = chat_title[:47] + "..."
        
        chat_id = create_chat(current_user['id'], chat_title)
        print(f"Created new chat with ID: {chat_id}")
    else:
        db = get_db_connection_service()
        c = db.cursor()
        c.execute('SELECT id FROM chats WHERE id = ? AND user_id = ?', (chat_id, current_user['id']))
        if not c.fetchone():
            title_words = question.split()[:5]
            chat_title = " ".join(title_words) if title_words else "New Chat"
            if len(chat_title) > 50:
                chat_title = chat_title[:47] + "..."
            
            chat_id = create_chat(current_user['id'], chat_title)
            print(f"Chat not found, created new chat with ID: {chat_id}")
    
    chat_history = get_chat_history_for_memory(chat_id, limit=10)
    
    agent = create_agent_with_tools()
    
    question_with_history = format_question_with_history(question, chat_history)
    
    add_message(chat_id, question, is_human=True)
    
    async def event_generator():
        agent_iterator = agent.iter(question_with_history)
        final_step = None
        image_id = None
        
        for step in agent_iterator:
            if output := step.get("intermediate_step"):
                action, value = output[0]
                print(step)
                if action.tool == "searx_search":
                    yield f"event: intermediate_step\ndata: Searching the web...\n\n"
                if action.tool == "python_repl":
                    yield f"event: intermediate_step\ndata: Running Python code...\n\n"
                if action.tool == "think_tool":
                    yield f"event: intermediate_step\ndata: Thinking...\n\n"
                if action.tool == "send_email_tool":
                    yield f"event: intermediate_step\ndata: Sending email...\n\n"
                if action.tool == "image_generation_tool":
                    match = re.search(r'ID:([a-f0-9-]+)', value)
                    if match:
                        image_id = match.group(1)
                        print(f"Extracted ID: {image_id}")
                    yield f"event: intermediate_step\ndata: Generating image...\n\n"
            
            final_step = step

        if final_step and isinstance(final_step, dict):
            print(final_step)
            if image_id:
                answer = "Image generated successfully!"
            else:
                answer = final_step.get("output", "")
            print("Final Answer:", answer)
            
            add_message(chat_id, answer, is_human=False, image_id=image_id)
            
            message = {
                'text': answer,
            }

            print("Sending answer to TTS...")
            try:
                async with RabbitBroker("amqp://guest:guest@localhost:5672/?heartbeat=2000") as tts_broker:
                    response = await tts_broker.publish(
                        message,
                        queue="to_tts",
                        rpc=True,
                        timeout=2000.0,
                    )
                
                response_data = {
                    'answer': answer, 
                    'audio_bytes': response.get('audio_bytes'),
                    'chat_id': chat_id
                }
                
                if image_id:
                    file_path = os.path.join(OUTPUT_DIR, f'{image_id}.png')
                    with open(file_path, 'rb') as f:
                        image_data = f.read()
                    image_bytes = base64.b64encode(image_data).decode('utf-8')
                    response_data['image_bytes'] = image_bytes
                else:
                    response_data['image_bytes'] = None
                
                yield f"event: final_answer\ndata: {json.dumps(response_data)}\n\n"
                
            except Exception as e:
                print(f"TTS Error: {e}")
                response_data = {
                    'answer': answer, 
                    'audio_bytes': None,
                    'chat_id': chat_id
                }
                yield f"event: final_answer\ndata: {json.dumps(response_data)}\n\n"
        else:
            response_data = {
                'answer': 'No answer generated', 
                'audio_bytes': None,
                'chat_id': chat_id
            }
            yield f"event: final_answer\ndata: {json.dumps(response_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")