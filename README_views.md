# views.py Complete Documentation

## Overview

The `users/views.py` file is the core backend logic of the HR chatbot application. It contains all view functions, API endpoints, and AI integration logic for handling user interactions, chat management, and intelligent HR assistance.

## File Structure

```
users/views.py (561 lines)
├── Imports & Configuration
├── Authentication Views
├── Chat Interface Views  
├── Chat API Endpoints
├── AI Integration Core
└── Fallback Response System
```

## Imports & Dependencies

```python
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
```

## Authentication Views

### `home_view(request)` - Lines 28-29
**Purpose**: Renders the application landing page
- **Template**: `users/home.html`
- **Features**: Shows welcome page without navigation bar
- **Access**: Public (no authentication required)

### `register_view(request)` - Lines 32-42
**Purpose**: Handles user registration
- **Methods**: GET (show form), POST (process registration)
- **Form**: `CustomUserCreationForm` for creating users with HR data
- **Flow**: Form validation → User creation → Redirect to login
- **Template**: `users/register.html`

### `login_view(request)` - Lines 45-54
**Purpose**: Handles user authentication
- **Methods**: GET (show form), POST (process login)
- **Form**: Django's `AuthenticationForm`
- **Flow**: Credentials validation → Login → Redirect to chat
- **Template**: `users/login.html`

### `logout_view(request)` - Lines 57-59
**Purpose**: Logs out users
- **Flow**: Clear session → Redirect to login page
- **Security**: Properly clears all session data

## Chat Interface Views

### `dashboard_view(request)` - Lines 62-64
**Purpose**: Legacy dashboard redirect
- **Authentication**: `@login_required` decorator
- **Behavior**: Redirects to main chat interface

### `chat_view(request)` - Lines 67-69
**Purpose**: Main chat interface
- **Authentication**: `@login_required` decorator
- **Template**: `users/chat.html`
- **Features**: Single-page application with Alpine.js

### `webcam_view(request)` - Lines 72-74
**Purpose**: Future webcam feature interface
- **Template**: `users/webcam.html`
- **Status**: Placeholder for future development

## Chat API Endpoints

### `get_chats(request)` - Lines 77-93
**Purpose**: Retrieves all chats for authenticated user
- **Method**: GET
- **Endpoint**: `/api/chats/`
- **Authentication**: `@login_required`
- **Returns**: JSON with chat list
- **Data Structure**:
  ```json
  {
    "chats": [
      {
        "id": 1,
        "title": "Chat title",
        "lastMessage": "Preview of last message...",
        "created_at": "2025-06-18T09:54:56",
        "updated_at": "2025-06-18T09:54:56"
      }
    ]
  }
  ```

### `create_chat(request)` - Lines 96-109
**Purpose**: Creates new chat session
- **Method**: POST
- **Endpoint**: `/api/chats/create/`
- **Authentication**: `@login_required`
- **Security**: `@csrf_exempt` decorator
- **Flow**: Create Chat object → Return metadata
- **Returns**: New chat object with ID and timestamps

### `delete_chat(request, chat_id)` - Lines 112-119
**Purpose**: Deletes specific chat
- **Method**: DELETE
- **Endpoint**: `/api/chats/{id}/delete/`
- **Authentication**: `@login_required`
- **Security**: Only chat owner can delete (enforced by `get_object_or_404`)
- **Features**: Cascading delete of all associated messages

### `get_messages(request, chat_id)` - Lines 122-138
**Purpose**: Retrieves all messages for a chat
- **Method**: GET
- **Endpoint**: `/api/chats/{id}/messages/`
- **Authentication**: `@login_required`
- **Security**: Access control via `get_object_or_404`
- **Returns**: Chronologically ordered message list
- **Data Structure**:
  ```json
  {
    "messages": [
      {
        "id": 1,
        "sender": "user|ai",
        "text": "Message content",
        "timestamp": "09:54"
      }
    ]
  }
  ```

### `send_message(request, chat_id)` - Lines 141-199
**Purpose**: Main message processing endpoint
- **Method**: POST
- **Endpoint**: `/api/chats/{id}/send/`
- **Authentication**: `@login_required`
- **Security**: CSRF protection and user validation

**Message Processing Flow**:
1. Parse JSON request body
2. Validate message content (non-empty)
3. Create user message in database
4. Update chat title (if first message)
5. Generate AI response via `get_ai_response()`
6. Create AI message in database
7. Update chat timestamp
8. Return both messages to frontend

**Error Handling**:
- JSON decode errors → 400 Bad Request
- Empty messages → 400 Bad Request
- General exceptions → 500 Internal Server Error with logging

## AI Integration Core

### `get_ai_response(user_message, user=None)` - Lines 202-255
**Purpose**: Main AI orchestration function
**Azure AI Integration**:
- Checks `AZURE_AVAILABLE` flag
- Initializes `AIProjectClient` with Azure credentials
- Uses configured agent and thread IDs from settings
- Processes enhanced messages through Azure AI pipeline

**Process Flow**:
1. Check Azure availability
2. Initialize Azure AI client
3. Get agent and thread references
4. Create enhanced message with `create_enhanced_message()`
5. Send message to Azure AI
6. Create and process AI run
7. Extract response from thread
8. Return formatted response

**Fallback Strategy**:
- Azure failures → `get_fallback_response()`
- Import errors → Local processing
- Configuration issues → Graceful degradation

### `create_enhanced_message(user_message, user)` - Lines 258-389
**Purpose**: Creates rich context for Azure AI with role-based data access

**Context Building Process**:

1. **User Information**:
   ```python
   # Basic user context
   context_parts.append(f"Utilisateur connecté: {user.first_name} {user.last_name}")
   context_parts.append(f"ID Employé: {user.employee_id}")
   context_parts.append(f"Département: {user.departement}")
   context_parts.append(f"Poste: {user.poste}")
   ```

2. **Permission Matrix**:
   ```python
   def can_access_employee_data(requesting_user, target_employee):
       if requesting_user.id == target_employee.id:
           return True  # Own data
       if requesting_user.is_manager and target_employee.responsable == requesting_user.employee_id:
           return True  # Team data
       return "directory"  # Public data only
   ```

3. **Data Access Levels**:
   - **Full Access**: Personal data + vacation details + sensitive info
   - **Directory Access**: Name, department, position, email only

4. **Team Information** (for managers):
   ```python
   if user.is_manager:
       team_members = CustomUser.objects.filter(responsable=user.employee_id)
       # Include complete team roster with contact details
   ```

5. **Employee Directory**:
   - Complete organizational structure
   - Department-wise employee listings
   - Contact information (emails are public)
   - Position and hierarchy information

**Enhanced Message Structure**:
```
Contexte Assistant RH:
Utilisateur connecté: John Smith (Manager - IT)
ID Employé: JS001
Département: IT
Poste: Chief Technology Officer
Statut: Manager

Permissions d'accès:
- Peut accéder à ses propres données complètes
- Peut accéder aux données complètes de son équipe (y compris emails)
- Peut consulter l'annuaire public (nom, prénom, département, poste, EMAIL)
IMPORTANT: Les emails sont PUBLICS et peuvent être partagés librement

Congés restants: 25.0 jours
Congés utilisés: 0.0 jours
Manager: David Miller

Équipe sous responsabilité (27 personnes):
- Laetitia Adam (LA001) - Data Analyst
- Arthur Bazin (AB002) - Ingénieur cloud
[... complete team listing]

Annuaire des employés disponible:
Département IT (27 personnes):
- Laetitia Adam (LA001) - Data Analyst - laetitia.adam@company.com
[... complete directory with emails]

Instructions spéciales:
- Vous êtes un assistant RH intelligent avec accès aux données des employés
- Les EMAILS sont PUBLICS et peuvent être partagés librement avec tous
- Fournissez des réponses précises et documentées adaptées aux besoins RH
- Pour les demandes d'équipe/département, listez TOUS les employés avec ce format sur des lignes séparées:
  "• Prénom Nom (ID) - Poste - email@company.com"
- Pour les managers, vous avez accès complet aux données de leur équipe
- Ne limitez jamais le nombre d'employés affichés, montrez la liste complète
- Format des réponses: utilisez des puces (•) et des retours à la ligne pour une meilleure lisibilité
- Structurez vos réponses avec des espaces et des sauts de ligne pour une présentation claire

Question de l'utilisateur: {user_message}
```

## Fallback Response System

### `get_fallback_response(user_message, user=None)` - Lines 392-561
**Purpose**: Intelligent local processing when Azure AI is unavailable

**Core Features**:
1. **Pattern Recognition**: Regex-based query classification
2. **Fuzzy Search**: Employee lookup with similarity scoring
3. **Role-Based Responses**: Different information based on user role
4. **Employee Directory**: Local database querying

**Query Processing Categories**:

#### Personal Information Queries
- **Patterns**: `['qui je suis', 'qui suis-je', 'mes infos', 'mon profil']`
- **Response**: Complete personal profile with HR data
- **Data Included**:
  - Name, employee ID, department, position
  - Employment date, manager information
  - Management status and team size

#### Employee Search
- **Patterns**: Multiple regex patterns for user lookup
  ```python
  user_search_patterns = [
      r'utilisateur ([A-Z0-9]+)',      # By employee ID
      r'employé ([A-Z0-9]+)',          # By employee ID
      r'infos? (?:sur|de) ([A-Za-z\s\-]+)',  # By name
      r'qui est ([A-Za-z\s\-]+)',      # By name
      r'contact (?:de|pour) ([A-Za-z\s\-]+)'  # By name
  ]
  ```

- **Fuzzy Search Algorithm**:
  ```python
  def find_similar_user(search_term):
      best_match = None
      best_score = 0.0
      
      for user in CustomUser.objects.all():
          # Check employee_id (60% threshold)
          # Check full name (60% threshold)  
          # Check position (70% threshold)
          
      return best_match, best_score
  ```

#### Department Team Listings
- **Enhanced Pattern Recognition**:
  ```python
  department_patterns = [
      'qui dans', 'équipe', 'collègues', 'département', 'filliale', 'service',
      'qui est dans', 'qui travaille dans', 'membres du', 'personnes dans',
      'liste des', 'employés du', 'staff du', 'team'
  ]
  ```

- **Department Mapping**:
  ```python
  dept_mappings = {
      'it': 'IT', 'informatique': 'IT', 'tech': 'IT',
      'marketing': 'Marketing', 'comm': 'Marketing',
      'finance': 'Finance', 'compta': 'Finance',
      'rh': 'RH', 'ressources humaines': 'RH',
      'vente': 'Ventes', 'ventes': 'Ventes', 'commercial': 'Ventes',
      'recherche': 'Recherche', 'r&d': 'Recherche',
      'direction': 'Direction', 'management': 'Direction'
  }
  ```

#### Position-Based Search
- **Patterns**: `['poste', 'fonction', 'job', 'métier']`
- **Keywords**: `['manager', 'director', 'developer', 'analyst', 'assistant', 'specialist', 'engineer', 'coordinator']`
- **Functionality**: Search employees by job title with fuzzy matching

#### Statistics and Analytics
- **Patterns**: `['statistiques', 'stats', 'combien', 'nombre']`
- **Features**: Department headcount, organizational metrics
- **SQL Query**: 
  ```python
  dept_stats = CustomUser.objects.values('departement').annotate(
      count=models.Count('id')
  ).exclude(departement__isnull=True).order_by('-count')
  ```

#### Leave and HR Information
- **Vacation Queries**: Personal leave balances and usage
- **Sick Leave**: Medical leave tracking
- **Salary Information**: Personal compensation data (restricted)
- **Working Hours**: Standard schedule information
- **Training**: Available courses and development programs

#### Management and Hierarchy
- **Manager Status**: Team information for managers
- **Team Listings**: Direct reports with contact details
- **Hierarchy Navigation**: Organizational structure queries
- **Contact Information**: Manager and peer contacts

**Security Features in Fallback**:
- **Privacy Protection**: Restricts personal data of other employees
- **Role Validation**: Checks user permissions before data access
- **Data Sanitization**: Safe error messages without data leakage
- **Access Logging**: Tracks unauthorized access attempts

**Response Formatting**:
```python
def format_employee_list(employees, title="Employés"):
    if not employees:
        return f"Aucun employé trouvé."
    
    response = f"{title} :\n"
    for emp in employees:
        response += f"• {emp.first_name} {emp.last_name} ({emp.employee_id or emp.id}) - {emp.poste} - {emp.email}\n"
    
    response += f"\nTotal : {len(employees)} personne(s)"
    return response
```

## Security Implementation

### Authentication & Authorization
- All chat endpoints require `@login_required`
- CSRF protection on state-changing operations
- Object-level permissions (users can only access their chats)

### Data Access Control
- Role-based access matrix implementation
- Manager privilege validation
- Public vs. private data segregation

### Error Handling
- Comprehensive try-catch blocks
- Sanitized error messages
- Logging for debugging without exposing sensitive data

### Input Validation
- JSON parsing with error handling
- Message length and format validation
- SQL injection prevention through ORM

## Performance Considerations

### Database Optimization
- Efficient queries with proper filtering
- Minimal database hits per request
- Optimized relationship traversal

### Azure AI Integration
- Connection pooling and reuse
- Graceful fallback mechanisms
- Token usage optimization

### Memory Management
- Limited context size for AI requests
- Efficient data structures
- Proper cleanup of resources

## Conclusion

The `views.py` file implements a comprehensive HR chatbot system with:
- **Secure authentication and authorization**
- **Intelligent AI integration with Azure**
- **Robust fallback mechanisms**
- **Role-based data access control**
- **Comprehensive employee directory functionality**
- **Real-time chat capabilities**
- **Enterprise-grade security features**

This implementation provides a production-ready HR assistant that can handle complex queries while maintaining strict data security and providing intelligent, contextual responses to employees and managers alike. 