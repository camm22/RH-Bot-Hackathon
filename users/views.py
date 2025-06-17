from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from .models import Chat, Message
import json
import time


def home_view(request):
    return render(request, 'users/home.html', {'show_navbar': False})


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form, })


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('chat')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    return redirect('chat')


@login_required
def chat_view(request):
    return render(request, 'users/chat.html')


def webcam_view(request):
    return render(request, 'users/webcam.html')


# API Views
@login_required
@require_http_methods(["GET"])
def get_chats(request):
    """Get all chats for the current user"""
    chats = Chat.objects.filter(user=request.user)
    chat_data = []
    
    for chat in chats:
        chat_data.append({
            'id': chat.id,
            'title': chat.title,
            'lastMessage': chat.last_message,
            'created_at': chat.created_at.isoformat(),
            'updated_at': chat.updated_at.isoformat(),
        })
    
    return JsonResponse({'chats': chat_data})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def create_chat(request):
    """Create a new chat"""
    chat = Chat.objects.create(user=request.user)
    
    return JsonResponse({
        'id': chat.id,
        'title': chat.title,
        'lastMessage': chat.last_message,
        'created_at': chat.created_at.isoformat(),
        'updated_at': chat.updated_at.isoformat(),
    })


@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def delete_chat(request, chat_id):
    """Delete a chat"""
    chat = get_object_or_404(Chat, id=chat_id, user=request.user)
    chat.delete()
    return JsonResponse({'success': True})


@login_required
@require_http_methods(["GET"])
def get_messages(request, chat_id):
    """Get all messages for a specific chat"""
    chat = get_object_or_404(Chat, id=chat_id, user=request.user)
    messages = chat.messages.all()
    
    message_data = []
    for message in messages:
        message_data.append({
            'id': message.id,
            'sender': message.sender,
            'text': message.content,
            'timestamp': message.created_at.strftime('%H:%M'),
        })
    
    return JsonResponse({'messages': message_data})


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request, chat_id):
    """Send a message and get AI response"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        
        # Create user message
        user_msg = Message.objects.create(
            chat=chat,
            sender='user',
            content=user_message
        )
        
        # Update chat title if it's the first message
        if chat.messages.count() == 1:
            chat.title = user_message[:30] + ('...' if len(user_message) > 30 else '')
            chat.save()
        
        # TODO: Connect to Azure LLM service
        # For now, simulate AI response
        ai_response = get_ai_response(user_message)
        
        # Create AI message
        ai_msg = Message.objects.create(
            chat=chat,
            sender='ai',
            content=ai_response
        )
        
        # Update chat timestamp
        chat.save()  # This updates the updated_at field
        
        return JsonResponse({
            'user_message': {
                'id': user_msg.id,
                'sender': 'user',
                'text': user_msg.content,
                'timestamp': user_msg.created_at.strftime('%H:%M'),
            },
            'ai_message': {
                'id': ai_msg.id,
                'sender': 'ai',
                'text': ai_msg.content,
                'timestamp': ai_msg.created_at.strftime('%H:%M'),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_ai_response(user_message):
    """
    TODO: Integrate with Azure LLM service
    
    This function should:
    1. Connect to Azure OpenAI or Azure ML endpoint
    2. Send the user message to the LLM
    3. Return the AI response
    
    For now, return a simulated response
    """
    # Simulate processing time
    time.sleep(1)
    
    # Simple response based on user message
    responses = [
        f"I understand you're asking about: '{user_message}'. Let me help you with that.",
        f"That's an interesting question about '{user_message}'. Here's what I think...",
        f"Based on your message '{user_message}', I can provide some insights.",
        f"Thank you for asking about '{user_message}'. Let me explain...",
    ]
    
    # Simple keyword-based responses
    message_lower = user_message.lower()
    if 'hello' in message_lower or 'hi' in message_lower:
        return "Hello! How can I assist you today?"
    elif 'help' in message_lower:
        return "I'm here to help! You can ask me questions about various topics, and I'll do my best to provide useful answers."
    elif 'about' in message_lower and 'yourself' in message_lower:
        return "I'm RH-Bot AI, your intelligent assistant. I'm designed to help answer questions, provide information, and assist with various tasks."
    else:
        import random
        return random.choice(responses)

