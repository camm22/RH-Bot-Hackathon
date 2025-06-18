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
import re

# Azure AI imports (optional)
try:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential
    from azure.ai.agents.models import ListSortOrder, MessageRole
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

logger = logging.getLogger(__name__)


def generate_chat_title(user_message):
    """
    Generate a simple, well-written and short title from the user message
    """
    # Simple AI-like title generation using keywords and patterns
    message_lower = user_message.lower().strip()
    
    # Define title patterns based on common HR queries
    title_patterns = {
        # Team/Department queries
        ('équipe', 'dans', 'département', 'filliale', 'service'): 'Équipe & Organisation',
        ('qui dans', 'qui est dans', 'membre'): 'Recherche Équipe',
        
        # Personal info
        ('qui je suis', 'mes infos', 'mon profil', 'mes données'): 'Mon Profil',
        
        # Leave/vacation
        ('congés', 'vacances', 'repos', 'arrêt'): 'Congés & Absences',
        
        # Contact/directory
        ('contact', 'email', 'mail', 'téléphone', 'adresse'): 'Contacts',
        ('qui est', 'infos sur', 'recherche'): 'Annuaire',
        
        # HR policies
        ('politique', 'règlement', 'procédure'): 'Politiques RH',
        ('salaire', 'paie', 'rémunération'): 'Rémunération',
        
        # Management
        ('manager', 'responsable', 'chef', 'hiérarchie'): 'Management',
        ('statistiques', 'stats', 'nombre', 'combien'): 'Statistiques',
        
        # Training/development
        ('formation', 'training', 'développement'): 'Formation',
        
        # General help
        ('aide', 'help', 'comment', 'que faire'): 'Assistance',
    }
    
    # Check patterns and return appropriate title
    for keywords, title in title_patterns.items():
        if any(keyword in message_lower for keyword in keywords):
            return title
    
    # Fallback: extract main subject or use generic title
    words = user_message.strip().split()
    if len(words) <= 3:
        return user_message.strip()
    elif len(words) <= 6:
        return ' '.join(words[:4])
    else:
        return ' '.join(words[:3]) + '...'


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
            # Generate a simple, well-written title using AI
            chat.title = generate_chat_title(user_message)
            chat.save()
        
        # Get AI response from Azure with user context
        ai_response = get_ai_response(user_message, request.user)
        
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


def get_ai_response(user_message, user=None):
    """
    Get AI response from Azure AI agent with user context
    """
    # Check if Azure is available and configured
    if not AZURE_AVAILABLE:
        logger.info("Azure AI not available, using fallback response")
        return get_fallback_response(user_message, user)
    
    try:
        # Initialize Azure AI client with Managed Identity for production
        try:
            from azure.identity import ManagedIdentityCredential
            # Try Managed Identity first (for Azure App Service)
            credential = ManagedIdentityCredential()
        except Exception:
            # Fallback to DefaultAzureCredential for local development
            credential = DefaultAzureCredential()
            
        project = AIProjectClient(
            credential=credential,
            endpoint=settings.AZURE_AI_ENDPOINT
        )
        
        # Get the agent
        agent = project.agents.get_agent(settings.AZURE_AI_AGENT_ID)
        
        # Get the thread
        thread = project.agents.threads.get(settings.AZURE_AI_THREAD_ID)
        
        # Create enhanced message with user context
        enhanced_message = create_enhanced_message(user_message, user)
        message = project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=enhanced_message
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
            raw_response = last_message.text_messages[-1].text.value
            # Post-process the response to fix formatting issues
            return fix_ai_response_formatting(raw_response, user)
        
        return get_fallback_response(user_message, user)
        
    except Exception as e:
        logger.error(f"Error getting AI response: {str(e)}")
        # Fallback to simulated response if Azure fails
        return get_fallback_response(user_message, user)


def fix_ai_response_formatting(response_text, user=None):
    """
    Fix Azure AI response formatting when it doesn't follow our required format
    """
    if not response_text:
        return response_text
    
    from .models import CustomUser
    
    # Try to detect if this is an employee list that needs reformatting
    lines = response_text.strip().split('\n')
    
    # Check if this looks like a malformed employee list
    has_emails = any('@' in line for line in lines)
    has_job_titles = any(any(title in line.lower() for title in ['analyst', 'manager', 'director', 'specialist', 'coordinator', 'assistant', 'engineer', 'responsable', 'chargé', 'directrice']) for line in lines)
    
    if has_emails and has_job_titles:
        # This looks like an employee list that needs fixing
        fixed_response = ""
        current_employee = {}
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Skip headers and greetings
            if any(header in line.lower() for header in ['hello', 'bonjour', 'here is', 'voici', 'list of', 'members', 'team', 'équipe']):
                if 'team' in line.lower() or 'équipe' in line.lower():
                    fixed_response += line + "\n\n"
                else:
                    fixed_response += line + "\n"
                i += 1
                continue
            
            # Skip ending messages
            if any(ending in line.lower() for ending in ['if you need', 'feel free', 'si vous', 'n\'hésitez']):
                fixed_response += "\n" + line
                i += 1
                continue
            
            # Extract email from line
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', line)
            
            if email_match:
                # This line contains an email
                email = email_match.group(1)
                
                # Look for the employee name and job title
                name_parts = []
                job_title = ""
                employee_id = ""
                
                # Check current line for name/title (after removing email)
                line_without_email = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', line).strip()
                line_without_email = re.sub(r'\s*-\s*', ' ', line_without_email).strip()
                
                # Look for employee ID pattern (E000)
                id_match = re.search(r'(E\d{3})', line_without_email)
                if id_match:
                    employee_id = id_match.group(1)
                    line_without_email = re.sub(r'E\d{3}', '', line_without_email).strip()
                
                # Check if there are job title keywords in current line
                job_keywords = ['analyst', 'manager', 'director', 'specialist', 'coordinator', 'assistant', 'engineer', 'responsable', 'chargé', 'directrice', 'marketing', 'data', 'traffic', 'content', 'communication']
                
                if any(keyword in line_without_email.lower() for keyword in job_keywords):
                    # This line has job title
                    parts = line_without_email.split()
                    name_part = []
                    title_part = []
                    
                    for part in parts:
                        if any(keyword in part.lower() for keyword in job_keywords):
                            title_part.append(part)
                        elif part and not any(char.isdigit() for char in part):
                            if not title_part:  # Still collecting name
                                name_part.append(part)
                            else:  # Now in title
                                title_part.append(part)
                    
                    if name_part:
                        name_parts = name_part
                    if title_part:
                        job_title = ' '.join(title_part)
                
                # Look in previous lines for name parts
                if not name_parts and i > 0:
                    for j in range(max(0, i-3), i):
                        prev_line = lines[j].strip()
                        if prev_line and not any(skip in prev_line.lower() for skip in ['hello', 'bonjour', 'here is', 'voici', '@']):
                            # Check if this looks like a name
                            words = prev_line.split()
                            if len(words) <= 3 and all(word.replace('-', '').replace("'", '').isalpha() for word in words):
                                name_parts = words
                                break
                
                # Try to find job title if not found
                if not job_title:
                    for j in range(max(0, i-2), min(len(lines), i+2)):
                        check_line = lines[j].strip()
                        if any(keyword in check_line.lower() for keyword in job_keywords) and '@' not in check_line:
                            job_title = check_line
                            break
                
                # Format the employee entry
                if name_parts:
                    name = ' '.join(name_parts)
                    if employee_id:
                        formatted_line = f"• {name} ({employee_id}) - {job_title} - {email}"
                    else:
                        formatted_line = f"• {name} - {job_title} - {email}"
                    fixed_response += formatted_line + "\n"
            
            i += 1
        
        # If we made significant changes, return the fixed version
        if fixed_response.strip() and '•' in fixed_response:
            return fixed_response.strip()
    
    # If not an employee list or couldn't fix it, return original
    return response_text


def create_enhanced_message(user_message, user):
    """
    Create an enhanced message with user context and accessible employee data for Azure AI
    Implements role-based access control for data security
    """
    if not user:
        return user_message
    
    from .models import CustomUser
    from datetime import datetime
    
    # Function to check data access permissions
    def can_access_employee_data(requesting_user, target_employee):
        if not requesting_user:
            return False
        if requesting_user.id == target_employee.id:
            return True
        if requesting_user.is_manager and target_employee.responsable == requesting_user.employee_id:
            return True
        return "directory"
    
    # Function to get employee data based on access level
    def get_employee_data_for_ai(employee, access_level="full"):
        base_data = {
            'id': employee.employee_id or str(employee.id),
            'nom': employee.last_name or '',
            'prenom': employee.first_name or '',
            'mail': employee.email or '',
            'departement': employee.departement or '',
            'poste': employee.poste or ''
        }
        
        if access_level == "directory":
            return {
                'nom': employee.last_name or '',
                'prenom': employee.first_name or '',
                'mail': employee.email or '',  # Email is public
                'departement': employee.departement or '',
                'poste': employee.poste or ''
            }
        elif access_level == True:  # Full access for own data or team members
            if employee.date_embauche:
                base_data['date_embauche'] = employee.date_embauche.strftime('%d/%m/%Y')
            if hasattr(employee, 'conges_restants'):
                base_data['conges_restants'] = employee.conges_restants
            if hasattr(employee, 'conges_utilises'):
                base_data['conges_utilises'] = employee.conges_utilises
        
        return base_data
    
    # Build user context
    context_parts = []
    
    # User's own information
    if user.first_name and user.last_name:
        context_parts.append(f"Utilisateur connecté: {user.first_name} {user.last_name}")
    
    if user.employee_id:
        context_parts.append(f"ID Employé: {user.employee_id}")
    
    if user.departement:
        context_parts.append(f"Département: {user.departement}")
    
    if user.poste:
        context_parts.append(f"Poste: {user.poste}")
    
    if user.is_manager:
        context_parts.append(f"Statut: Manager")
    
    # Add access permissions info
    context_parts.append("Permissions d'accès:")
    context_parts.append("- Peut accéder à ses propres données complètes")
    if user.is_manager:
        context_parts.append("- Peut accéder aux données complètes de son équipe (y compris emails)")
    context_parts.append("- Peut consulter l'annuaire public (nom, prénom, département, poste, EMAIL)")
    context_parts.append("IMPORTANT: Les emails sont PUBLICS et peuvent être partagés librement")
    
    # Add vacation info for the user
    if hasattr(user, 'conges_restants'):
        context_parts.append(f"Congés restants: {user.conges_restants} jours")
    if hasattr(user, 'conges_utilises'):
        context_parts.append(f"Congés utilisés: {user.conges_utilises} jours")
    if hasattr(user, 'conges_maladie_restants'):
        context_parts.append(f"Congés maladie restants: {user.conges_maladie_restants} jours")
    
    # Add salary and benefits info for the user
    if hasattr(user, 'salaire') and user.salaire:
        context_parts.append(f"Salaire annuel: {user.salaire:,.0f}€")
    if hasattr(user, 'eligible_prime'):
        context_parts.append(f"Éligible aux primes: {'Oui' if user.eligible_prime else 'Non'}")
    if hasattr(user, 'date_prochaine_evaluation') and user.date_prochaine_evaluation:
        context_parts.append(f"Prochaine évaluation: {user.date_prochaine_evaluation.strftime('%d/%m/%Y')}")
    if hasattr(user, 'regime_sante'):
        context_parts.append(f"Régime de santé: {user.regime_sante}")
    
    # Manager info
    if user.responsable:
        try:
            manager = CustomUser.objects.get(employee_id=user.responsable)
            context_parts.append(f"Manager: {manager.first_name} {manager.last_name} - {manager.poste} - {manager.email}")
        except CustomUser.DoesNotExist:
            pass
    
    # Team members info if user is a manager
    if user.is_manager:
        team_members = CustomUser.objects.filter(responsable=user.employee_id)
        if team_members.exists():
            context_parts.append(f"Équipe sous responsabilité ({team_members.count()} personnes):")
            for member in team_members:
                member_data = get_employee_data_for_ai(member, True)
                context_parts.append(f"  - {member_data['prenom']} {member_data['nom']} ({member_data['id']}) - {member_data['poste']}")
    
    # Available employee directory data
    context_parts.append("\nAnnuaire des employés disponible:")
    all_employees = CustomUser.objects.all().order_by('departement', 'last_name')
    dept_summary = {}
    
    for emp in all_employees:
        if emp.departement:
            if emp.departement not in dept_summary:
                dept_summary[emp.departement] = []
            
            access_level = can_access_employee_data(user, emp)
            emp_data = get_employee_data_for_ai(emp, access_level)
            dept_summary[emp.departement].append(emp_data)
    
    for dept, employees in dept_summary.items():
        context_parts.append(f"\nDépartement {dept} ({len(employees)} personnes):")
        for emp_data in employees:  # Show ALL employees, not just first 5
            if 'id' in emp_data:
                context_parts.append(f"  - {emp_data['prenom']} {emp_data['nom']} ({emp_data['id']}) - {emp_data['poste']} - {emp_data['mail']}")
            else:
                context_parts.append(f"  - {emp_data['prenom']} {emp_data['nom']} - {emp_data['poste']} - {emp_data['mail']}")
    
    # Build the enhanced message
    context_str = "\n".join(context_parts)
    enhanced_message = f"""Contexte Assistant RH:
{context_str}

Instructions spéciales:
- Vous êtes un assistant RH intelligent avec accès aux données des employés
- ACCÈS DYNAMIQUE AUX DONNÉES: Toutes les données de l'utilisateur connecté sont disponibles dans le contexte - utilisez-les TOUJOURS
- DONNÉES PERSONNELLES COMPLÈTES: L'utilisateur a accès à TOUTES ses données (salaire, congés, évaluations, hiérarchie, etc.)
- RÉPONSES BASÉES SUR LES DONNÉES: Utilisez EXCLUSIVEMENT les données du contexte pour répondre, ne jamais donner de réponses génériques
- EMAILS TOUJOURS PUBLICS: Partagez TOUJOURS l'email de n'importe quel employé demandé - c'est une information publique
- RÈGLE ABSOLUE: Pour toute recherche d'employé, incluez SYSTÉMATIQUEMENT l'email dans votre réponse
- DONNÉES SALARIALES: Quand l'utilisateur demande son salaire, vous DEVEZ lui donner l'information complète depuis le contexte fourni
- INFORMATIONS COMPLÈTES: Si l'utilisateur demande "toutes mes infos", donnez TOUT ce qui est disponible dans le contexte

FORMAT OBLIGATOIRE ULTRA-STRICT pour les listes d'employés:

VOUS DEVEZ UTILISER EXACTEMENT CE FORMAT - AUCUNE EXCEPTION:
• Prénom Nom (ID) - Poste - email@company.com

EXEMPLES EXACTS À SUIVRE ABSOLUMENT:
• Sara Johnson (E002) - Spécialiste Marketing - sara.johnson@company.com
• David Miller (E005) - Directeur Ingénierie - david.miller@company.com
• Antoinette Laurence Leblanc (E123) - Traffic Manager - antoinette-laurence.leblanc@company.com

RÈGLES ULTRA-STRICTES - INTERDICTION ABSOLUE DE:
❌ NE JAMAIS écrire le nom sur une ligne et le poste sur une autre
❌ NE JAMAIS faire ça:
Eugène
Arthur Chauveau
Data Marketing Analyst - email@company.com

✅ TOUJOURS faire ça:
• Eugène Arthur Chauveau (E123) - Data Marketing Analyst - email@company.com

RÈGLES OBLIGATOIRES:
- TOUJOURS commencer par "•" (bullet point)
- TOUJOURS nom complet sur UNE SEULE ligne
- TOUJOURS mettre l'ID entre parenthèses si disponible
- TOUJOURS séparer par " - " (espace-tiret-espace)
- UNE SEULE ligne par employé - JAMAIS de retour à la ligne dans un nom
- JAMAIS diviser les informations d'un employé sur plusieurs lignes

CONTRÔLE QUALITÉ REQUIS:
Avant d'envoyer votre réponse, vérifiez que chaque employé suit EXACTEMENT ce format:
• [Prénom complet] [Nom complet] ([ID si disponible]) - [Poste complet] - [email complet]

Question de l'utilisateur: {user_message}

Répondez de manière professionnelle et précise en tant qu'assistant RH en respectant ABSOLUMENT le format exigé."""
    
    return enhanced_message


def get_fallback_response(user_message, user=None):
    """
    Enhanced HR assistant with precise, documented responses tailored to HR needs
    Implements role-based access control for data security
    """
    from .models import CustomUser
    from difflib import SequenceMatcher
    from django.db import models
    from datetime import datetime
    
    message_lower = user_message.lower()
    
    # Personalized greeting with role context
    if user:
        role_context = ""
        if user.is_manager:
            role_context = f" (Manager - {user.departement})"
        elif user.departement:
            role_context = f" ({user.poste} - {user.departement})"
        greeting = f"Bonjour {user.first_name}{role_context}"
    else:
        greeting = "Bonjour"
    
    # Simplified fallback - main logic is now in Azure bot via create_enhanced_message
    
    # Simple employee list formatter for fallback
    def format_employee_list(employees, title="Employés"):
        """Format a list of employees with basic data"""
        if not employees:
            return f"Aucun employé trouvé."
        
        response = f"{title} :\n"
        for emp in employees:
            response += f"• {emp.first_name} {emp.last_name} ({emp.employee_id or emp.id}) - {emp.poste} - {emp.email}\n"
        
        response += f"\nTotal : {len(employees)} personne(s)"
        return response
    
    # Function for fuzzy matching
    def find_similar_user(search_term):
        """Find user with fuzzy matching on name, employee_id, or position"""
        best_match = None
        best_score = 0.0
        
        for u in CustomUser.objects.all():
            # Check employee_id
            if u.employee_id:
                score = SequenceMatcher(None, search_term.lower(), u.employee_id.lower()).ratio()
                if score > best_score and score > 0.6:
                    best_match = u
                    best_score = score
            
            # Check full name
            if u.first_name and u.last_name:
                full_name = f"{u.first_name} {u.last_name}".lower()
                score = SequenceMatcher(None, search_term.lower(), full_name).ratio()
                if score > best_score and score > 0.6:
                    best_match = u
                    best_score = score
            
            # Check position
            if u.poste:
                score = SequenceMatcher(None, search_term.lower(), u.poste.lower()).ratio()
                if score > best_score and score > 0.7:
                    best_match = u
                    best_score = score
        
        return best_match, best_score
    
    # Enhanced pattern matching with fuzzy search
    
    # Complete personal information - detect comprehensive requests
    comprehensive_info_patterns = [
        'toutes mes infos', 'toutes mes informations', 'mes données complètes', 
        'mes infos complètes', 'tout ce que tu sais sur moi', 'toutes mes données',
        'mes informations complètes', 'all my info', 'complete information',
        'everything about me', 'toutes les infos', 'profile complet'
    ]
    
    if any(pattern in message_lower for pattern in comprehensive_info_patterns):
        if user and user.is_authenticated:
            return format_complete_user_response(user)
        return f"{greeting}! Vous devez être connecté pour accéder à vos informations personnelles."
    
    # Who am I / Basic personal info
    if any(word in message_lower for word in ['qui je suis', 'qui suis-je', 'mes infos', 'mon profil']):
        if user and user.is_authenticated:
            user_info = get_complete_user_info(user)
            if user_info:
                response = f"{greeting}! Voici vos informations principales :\n"
                response += f"• Nom : {user_info['basic']['first_name']} {user_info['basic']['last_name']}\n"
                response += f"• ID Employé : {user_info['basic']['employee_id']}\n"
                response += f"• Département : {user_info['basic']['departement']}\n"
                response += f"• Poste : {user_info['basic']['poste']}\n"
                if user_info['basic']['date_embauche']:
                    response += f"• Date d'embauche : {user_info['basic']['date_embauche']}\n"
                if user_info['basic']['is_manager']:
                    response += f"• Statut : Manager\n"
                if user_info['hierarchy']['manager_info']:
                    manager = user_info['hierarchy']['manager_info']
                    response += f"• Manager : {manager['name']} ({manager['email']})"
                response += f"\n\nPour voir toutes vos informations complètes, demandez 'toutes mes infos'."
                return response
        return f"{greeting}! Pour connaître vos informations personnelles, connectez-vous ou contactez le service RH."
    
    # Search for specific user (with fuzzy matching)
    user_search_patterns = [
        r'utilisateur ([A-Z0-9]+)',
        r'employé ([A-Z0-9]+)',
        r'infos? (?:sur|de) ([A-Za-z\s\-]+)',
        r'qui est ([A-Za-z\s\-]+)',
        r'contact (?:de|pour) ([A-Za-z\s\-]+)',
        r'email (?:de|du) ([A-Za-z\s\-]+)',
        r'mail (?:de|du) ([A-Za-z\s\-]+)',
        r'adresse (?:de|du) ([A-Za-z\s\-]+)',
        r'quel(?:le)? (?:est l\'?)?email (?:de|du) ([A-Za-z\s\-]+)',
        r'quel(?:le)? (?:est l\'?)?mail (?:de|du) ([A-Za-z\s\-]+)'
    ]
    
    for pattern in user_search_patterns:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            search_term = match.group(1).strip()
            found_user, score = find_similar_user(search_term)
            
            if found_user:
                # Use the simple employee data format
                response = f"{greeting}! J'ai trouvé :\n"
                response += f"• Nom : {found_user.first_name} {found_user.last_name}\n"
                response += f"• ID : {found_user.employee_id or found_user.id}\n"
                response += f"• Email : {found_user.email}\n"
                response += f"• Département : {found_user.departement}\n"
                response += f"• Poste : {found_user.poste}"
                if score < 0.9:
                    response += f"\n(Résultat approximatif - score: {score:.0%})"
                return response
            else:
                return f"{greeting}! Je n'ai pas trouvé d'utilisateur correspondant à '{search_term}'. Vérifiez l'orthographe ou utilisez l'ID employé."
    
    # Department team listing - Enhanced patterns
    department_patterns = [
        'qui dans', 'équipe', 'collègues', 'département', 'filliale', 'service',
        'qui est dans', 'qui travaille dans', 'membres du', 'personnes dans',
        'liste des', 'employés du', 'staff du', 'team'
    ]
    
    if any(word in message_lower for word in department_patterns):
        dept = None
        
        # Extract department from message with more patterns
        dept_mappings = {
            'it': 'IT',
            'informatique': 'IT', 
            'tech': 'IT',
            'technologie': 'IT',
            'marketing': 'Marketing',
            'comm': 'Marketing',
            'communication': 'Marketing',
            'finance': 'Finance',
            'compta': 'Finance',
            'comptabilité': 'Finance',
            'rh': 'RH',
            'ressources humaines': 'RH',
            'hr': 'RH',
            'vente': 'Ventes',
            'ventes': 'Ventes',
            'commercial': 'Ventes',
            'recherche': 'Recherche',
            'r&d': 'Recherche',
            'rd': 'Recherche',
            'direction': 'Direction',
            'management': 'Direction',
            'exec': 'Direction'
        }
        
        # Try to find department in message
        for key, value in dept_mappings.items():
            if key in message_lower:
                dept = value
                break
        
        # If no specific department found, use user's department
        if not dept and user and user.departement:
            dept = user.departement
        
        if dept:
            colleagues = CustomUser.objects.filter(departement=dept).order_by('last_name', 'first_name')
            if colleagues.exists():
                title = f'Équipe du département {dept}'
                return f"{greeting}! {format_employee_list(colleagues, title)}"
            else:
                return f"{greeting}! Aucune personne trouvée dans le département {dept}."
        else:
            # Show all departments if no specific one requested
            departments = CustomUser.objects.values_list('departement', flat=True).distinct().exclude(departement__isnull=True)
            if departments:
                dept_list = ', '.join(departments)
                return f"{greeting}! Départements disponibles : {dept_list}. Précisez lequel vous souhaitez consulter."
            else:
                                 return f"{greeting}! Aucun département trouvé dans la base de données."
    
    # Search by job position
    if any(word in message_lower for word in ['poste', 'fonction', 'job', 'métier']):
        # Try to find specific position mentions
        position_keywords = ['manager', 'director', 'developer', 'analyst', 'assistant', 'specialist', 'engineer', 'coordinator']
        found_position = None
        
        for keyword in position_keywords:
            if keyword in message_lower:
                found_position = keyword
                break
        
        if found_position:
            employees = CustomUser.objects.filter(poste__icontains=found_position).order_by('departement', 'last_name')
            if employees.exists():
                title = f'Employés avec le poste contenant "{found_position}"'
                return f"{greeting}! {format_employee_list(employees, title)}"
            else:
                return f"{greeting}! Aucun employé trouvé avec un poste contenant '{found_position}'."
    
    # Department statistics
    if any(word in message_lower for word in ['statistiques', 'stats', 'combien', 'nombre']):
        if any(word in message_lower for word in ['département', 'service']):
            # Get department statistics
            dept_stats = CustomUser.objects.values('departement').annotate(count=models.Count('id')).exclude(departement__isnull=True).order_by('-count')
            if dept_stats:
                response = f"{greeting}! Statistiques par département :\n"
                total = 0
                for stat in dept_stats:
                    response += f"• {stat['departement']} : {stat['count']} personne(s)\n"
                    total += stat['count']
                response += f"\nTotal : {total} employé(s)"
                return response
            else:
                return f"{greeting}! Aucune statistique disponible."
    
    # CEO/PDG contact
    if any(word in message_lower for word in ['pdg', 'ceo', 'directeur général', 'président']):
        try:
            ceo = CustomUser.objects.filter(poste__icontains='PDG').first()
            if not ceo:
                ceo = CustomUser.objects.filter(poste__icontains='CEO').first()
            if not ceo:
                ceo = CustomUser.objects.filter(poste__icontains='Directeur Général').first()
            
            if ceo:
                if user and (user.is_manager or user.departement == 'Direction'):
                    return f"{greeting}! Le PDG est {ceo.first_name} {ceo.last_name} ({ceo.email})."
                else:
                    return f"{greeting}! Le PDG est {ceo.first_name} {ceo.last_name}. Pour le contacter, passez par votre manager ou le service RH."
            else:
                return f"{greeting}! Je ne trouve pas les informations du PDG. Contactez le service RH."
        except Exception:
            return f"{greeting}! Informations PDG non disponibles. Contactez le service RH."
    
    # HR contact
    if any(word in message_lower for word in ['rh', 'ressources humaines', 'hr']):
        try:
            hr_people = CustomUser.objects.filter(departement='RH')
            if hr_people.exists():
                response = f"{greeting}! Voici les contacts RH :\n"
                for hr_person in hr_people:
                    response += f"• {hr_person.first_name} {hr_person.last_name} - {hr_person.poste} ({hr_person.email})\n"
                return response
            else:
                return f"{greeting}! Contactez le service RH via l'adresse générale rh@company.com"
        except Exception:
            return f"{greeting}! Contactez le service RH via l'adresse générale rh@company.com"
    
    # Manager status
    if any(word in message_lower for word in ['manager', 'responsable', 'chef']):
        if user:
            if user.is_manager:
                # Find team members
                team_members = CustomUser.objects.filter(responsable=user.employee_id)
                response = f"{greeting}! Vous êtes manager. "
                if team_members.exists():
                    response += f"Votre équipe compte {team_members.count()} personnes :\n"
                    for member in team_members:
                        response += f"• {member.first_name} {member.last_name} - {member.poste}\n"
                else:
                    response += "Aucune personne n'est actuellement sous votre responsabilité."
                return response
            elif user.responsable:
                try:
                    manager = CustomUser.objects.get(employee_id=user.responsable)
                    return f"{greeting}! Votre manager est {manager.first_name} {manager.last_name} ({manager.email})."
                except CustomUser.DoesNotExist:
                    return f"{greeting}! Les informations sur votre manager ne sont pas disponibles."
            else:
                return f"{greeting}! Vous n'avez pas de manager assigné selon nos données."
        return f"{greeting}! Connectez-vous pour connaître vos informations hiérarchiques."
    
    # Leave/vacation info
    if any(word in message_lower for word in ['congés', 'vacances', 'repos']):
        if user and user.is_authenticated:
            user_info = get_complete_user_info(user)
            if user_info:
                response = f"{greeting}! Voici vos informations de congés :\n"
                response += f"• Congés restants : {user_info['vacation']['conges_restants']} jours\n"
                response += f"• Congés utilisés : {user_info['vacation']['conges_utilises']} jours\n"
                response += f"• Congés planifiés : {user_info['vacation']['conges_planifies']} jours\n"
                response += f"• Total annuel : {user_info['vacation']['conges_droit_annuel']} jours\n"
                response += "\nLes demandes doivent être faites via le système RH au moins 2 semaines à l'avance."
                return response
        return f"{greeting}! Connectez-vous pour connaître vos congés."
    
    # Sick leave
    if any(word in message_lower for word in ['maladie', 'arrêt', 'sick']):
        if user and user.is_authenticated:
            user_info = get_complete_user_info(user)
            if user_info:
                response = f"{greeting}! Congés maladie :\n"
                response += f"• Restants : {user_info['vacation']['conges_maladie_restants']} jours\n"
                response += f"• Utilisés : {user_info['vacation']['conges_maladie_utilises']} jours\n"
                response += f"• Total annuel : {user_info['vacation']['conges_maladie_droit']} jours\n"
                response += "\nEn cas d'arrêt maladie, prévenez votre manager et envoyez l'arrêt au service RH dans les 48h."
                return response
        return f"{greeting}! Connectez-vous pour connaître vos congés maladie."
    
    # Salary info
    if any(word in message_lower for word in ['salaire', 'paie', 'rémunération', 'my salary', 'mon salaire', 'salary']):
        if user and user.is_authenticated:
            user_info = get_complete_user_info(user)
            if user_info and user_info['financial']['salaire']:
                response = f"{greeting}! Voici vos informations financières :\n"
                response += f"• Salaire annuel : {user_info['financial']['salaire']:,.0f}€\n"
                response += f"• Éligible aux primes : {'Oui' if user_info['financial']['eligible_prime'] else 'Non'}\n"
                if user_info['financial']['date_prochaine_evaluation']:
                    response += f"• Prochaine évaluation : {user_info['financial']['date_prochaine_evaluation']}\n"
                response += f"• Régime de santé : {user_info['benefits']['regime_sante']}\n"
                response += "\nPour plus de détails, contactez le service RH."
                return response
            else:
                return f"{greeting}! Vos informations salariales ne sont pas disponibles dans notre système. Contactez le service RH."
        return f"{greeting}! Vous devez être connecté pour accéder à vos informations salariales."
    
    # Working hours
    if any(word in message_lower for word in ['horaires', 'heures']):
        response = f"{greeting}! Horaires standard : 9h00 à 17h30, lundi au vendredi, avec 1h de pause déjeuner."
        if user and user.is_manager:
            response += " En tant que manager, vous avez une certaine flexibilité selon les besoins du service."
        return response
    
    # Training
    if any(word in message_lower for word in ['formation', 'training']):
        response = f"{greeting}! L'entreprise propose diverses formations. "
        if user and user.departement:
            response += f"Pour le département {user.departement}, consultez le catalogue spécialisé. "
        response += "Voir l'intranet ou contactez le service RH."
        return response
    
    # Privacy/confidentiality message for unauthorized requests
    if any(word in message_lower for word in ['congés de', 'salaire de', 'infos de']):
        return f"{greeting}! Je ne peux pas divulguer d'informations personnelles sur d'autres employés. Je peux seulement partager les informations publiques (nom, email, département, poste). Pour vos propres informations, connectez-vous."
    
    # Generic helpful response (Azure AI fallback)
    response = f"{greeting}! Je suis votre assistant RH intelligent. Je peux vous aider avec :\n"
    response += "• Vos informations personnelles et d'équipe\n"
    response += "• Recherche d'employés et départements\n"
    response += "• Gestion des congés et informations RH\n"
    response += "• Questions sur les politiques d'entreprise\n"
    response += f"\nQuestion : '{user_message}'\n"
    if user and user.is_manager:
        response += "\n✓ Accès Manager : Vous pouvez consulter les données de votre équipe"
    response += "\n🔒 Confidentialité : Seules les informations autorisées sont partagées"
    response += "\n\nNote : Assistant Azure AI temporairement indisponible - mode de base activé."
    
    return response


def get_complete_user_info(user):
    """
    Get complete user information including all personal data
    This function ensures dynamic access to all user data from the database
    """
    if not user or not user.is_authenticated:
        return None
    
    from .models import CustomUser
    
    # Refresh user data from database to ensure we have the latest info
    try:
        user = CustomUser.objects.get(id=user.id)
    except CustomUser.DoesNotExist:
        return None
    
    user_info = {
        'basic': {
            'id': user.employee_id or str(user.id),
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'employee_id': user.employee_id,
            'departement': user.departement,
            'poste': user.poste,
            'is_manager': user.is_manager,
            'date_embauche': user.date_embauche.strftime('%d/%m/%Y') if user.date_embauche else None,
        },
        'vacation': {
            'conges_droit_annuel': user.conges_droit_annuel,
            'conges_utilises': user.conges_utilises,
            'conges_planifies': user.conges_planifies,
            'conges_restants': user.conges_restants,
            'conges_maladie_droit': user.conges_maladie_droit,
            'conges_maladie_utilises': user.conges_maladie_utilises,
            'conges_maladie_restants': user.conges_maladie_restants,
        },
        'financial': {
            'salaire': user.salaire,
            'eligible_prime': user.eligible_prime,
            'date_prochaine_evaluation': user.date_prochaine_evaluation.strftime('%d/%m/%Y') if user.date_prochaine_evaluation else None,
        },
        'benefits': {
            'regime_sante': user.regime_sante,
        },
        'hierarchy': {
            'responsable': user.responsable,
            'manager_info': None,
            'team_members': []
        }
    }
    
    # Get manager information
    if user.responsable:
        try:
            manager = CustomUser.objects.get(employee_id=user.responsable)
            user_info['hierarchy']['manager_info'] = {
                'name': f"{manager.first_name} {manager.last_name}",
                'email': manager.email,
                'poste': manager.poste
            }
        except CustomUser.DoesNotExist:
            pass
    
    # Get team members if user is a manager
    if user.is_manager:
        team_members = CustomUser.objects.filter(responsable=user.employee_id)
        for member in team_members:
            user_info['hierarchy']['team_members'].append({
                'name': f"{member.first_name} {member.last_name}",
                'employee_id': member.employee_id,
                'poste': member.poste,
                'email': member.email
            })
    
    return user_info


def format_complete_user_response(user):
    """
    Format a complete response with all user information they have access to
    """
    user_info = get_complete_user_info(user)
    if not user_info:
        return "Vous devez être connecté pour accéder à vos informations personnelles."
    
    response = f"Bonjour {user_info['basic']['first_name']}! Voici toutes vos informations :\n\n"
    
    # Basic information
    response += "**Informations personnelles :**\n"
    response += f"• Nom complet : {user_info['basic']['first_name']} {user_info['basic']['last_name']}\n"
    response += f"• ID Employé : {user_info['basic']['employee_id']}\n"
    response += f"• Email : {user_info['basic']['email']}\n"
    response += f"• Département : {user_info['basic']['departement']}\n"
    response += f"• Poste : {user_info['basic']['poste']}\n"
    if user_info['basic']['date_embauche']:
        response += f"• Date d'embauche : {user_info['basic']['date_embauche']}\n"
    if user_info['basic']['is_manager']:
        response += f"• Statut : Manager\n"
    
    # Financial information
    response += "\n**Informations financières :**\n"
    if user_info['financial']['salaire']:
        response += f"• Salaire annuel : {user_info['financial']['salaire']:,.0f}€\n"
    response += f"• Éligible aux primes : {'Oui' if user_info['financial']['eligible_prime'] else 'Non'}\n"
    if user_info['financial']['date_prochaine_evaluation']:
        response += f"• Prochaine évaluation : {user_info['financial']['date_prochaine_evaluation']}\n"
    
    # Vacation information
    response += "\n**Congés et absences :**\n"
    response += f"• Congés annuels - Droit : {user_info['vacation']['conges_droit_annuel']} jours\n"
    response += f"• Congés annuels - Utilisés : {user_info['vacation']['conges_utilises']} jours\n"
    response += f"• Congés annuels - Restants : {user_info['vacation']['conges_restants']} jours\n"
    response += f"• Congés annuels - Planifiés : {user_info['vacation']['conges_planifies']} jours\n"
    response += f"• Congés maladie - Droit : {user_info['vacation']['conges_maladie_droit']} jours\n"
    response += f"• Congés maladie - Utilisés : {user_info['vacation']['conges_maladie_utilises']} jours\n"
    response += f"• Congés maladie - Restants : {user_info['vacation']['conges_maladie_restants']} jours\n"
    
    # Benefits
    response += "\n**Avantages sociaux :**\n"
    response += f"• Régime de santé : {user_info['benefits']['regime_sante']}\n"
    
    # Hierarchy information
    response += "\n**Hiérarchie :**\n"
    if user_info['hierarchy']['manager_info']:
        manager = user_info['hierarchy']['manager_info']
        response += f"• Manager : {manager['name']} ({manager['email']}) - {manager['poste']}\n"
    else:
        response += f"• Manager : Aucun manager assigné\n"
    
    if user_info['hierarchy']['team_members']:
        response += f"• Équipe sous votre responsabilité ({len(user_info['hierarchy']['team_members'])} personnes) :\n"
        for member in user_info['hierarchy']['team_members']:
            response += f"  - {member['name']} ({member['employee_id']}) - {member['poste']} - {member['email']}\n"
    
    response += "\nSi vous avez des questions spécifiques sur l'une de ces informations, n'hésitez pas à me le demander !"
    
    return response

