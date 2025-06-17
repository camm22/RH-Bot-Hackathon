from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .forms import CustomUserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from .models import Chat, Message
import json
import logging

# Azure AI imports (optional)
try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    from azure.ai.agents.models import ListSortOrder, MessageRole
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)


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
        
        # Get AI response from Azure
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
        logger.error(f"Error in send_message: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def get_ai_response(user_message):
    """
    Get AI response from Azure AI agent
    """
    # Check if Azure is available and configured
    if not AZURE_AVAILABLE:
        logger.info("Azure AI not available, using fallback response")
        return get_fallback_response(user_message)
    
    try:
        # Initialize Azure AI client
        project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=settings.AZURE_AI_ENDPOINT
        )
        
        # Get the agent
        agent = project.agents.get_agent(settings.AZURE_AI_AGENT_ID)
        
        # Get the thread
        thread = project.agents.threads.get(settings.AZURE_AI_THREAD_ID)
        
        # Create message
        message = project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )
        
        # Create and process run
        run = project.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id
        )
        
        if run.status == "failed":
            logger.error(f"Azure AI run failed: {run.last_error}")
            return get_fallback_response(user_message)
        
        # Get the last AI response using the specialized method
        last_message = project.agents.messages.get_last_message_by_role(
            thread_id=thread.id,
            role=MessageRole.AGENT
        )
        
        if last_message and hasattr(last_message, 'text_messages') and last_message.text_messages:
            return last_message.text_messages[-1].text.value
        
        return get_fallback_response(user_message)
        
    except Exception as e:
        logger.error(f"Error getting AI response: {str(e)}")
        # Fallback to simulated response if Azure fails
        return get_fallback_response(user_message)


def get_fallback_response(user_message):
    """
    Fallback response when Azure AI is not available
    """
    message_lower = user_message.lower()
    
    if 'horaires' in message_lower or 'heures' in message_lower:
        return "Les horaires de travail standard sont de 9h00 à 17h30 du lundi au vendredi, avec une pause déjeuner d'une heure. Pour les cadres, il peut y avoir plus de flexibilité selon les besoins du service."
    elif 'congés' in message_lower or 'vacances' in message_lower:
        return "Vous avez droit à 25 jours de congés payés par an, plus les jours fériés. Les demandes doivent être faites via le système RH au moins 2 semaines à l'avance."
    elif 'salaire' in message_lower or 'paie' in message_lower:
        return "Pour toute question concernant votre salaire, veuillez contacter le service RH directement ou consulter votre espace employé."
    elif 'formation' in message_lower:
        return "L'entreprise propose diverses formations tout au long de l'année. Consultez le catalogue de formations disponible sur l'intranet ou contactez le service RH."
    else:
        return f"Je comprends que vous vous renseignez sur '{user_message}'. Pour des informations spécifiques RH, je vous recommande de consulter le manuel employé ou de contacter directement le service des ressources humaines."

