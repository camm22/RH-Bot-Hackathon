# 🚀 Guide de Déploiement Azure App Service

## Configuration d'Authentification Azure AI

### 📋 Checklist de Déploiement

#### ✅ Étape 1: Activer Managed Identity
```bash
# Via Azure Portal
1. Azure Portal → App Service "web-app-group4"
2. Settings → Identity → System assigned
3. Status: ON → Save
4. Copier l'Object ID affiché
```

#### ✅ Étape 2: Variables d'Environnement
```bash
# Dans Azure Portal → App Service → Settings → Environment variables
AZURE_TENANT_ID = 413600cf-bd4e-4c7c-8a61-69e73cddf731
AZURE_CLIENT_ID = [Object ID de l'étape 1]
```

#### ✅ Étape 3: Redémarrer l'App Service
```bash
# Azure Portal → App Service → Overview → Restart
```

### 🔧 Test de Configuration

#### Test en local:
```bash
python test_azure_connection.py
```

#### Test en production (via SSH/Console):
```bash
python test_azure_production.py
```

### 🚨 Troubleshooting

#### Erreur: "ManagedIdentityCredential authentication unavailable"
- ✅ Vérifier que Managed Identity est activé
- ✅ Redémarrer l'App Service après activation

#### Erreur: "DefaultAzureCredential failed to retrieve a token"
- ✅ Vérifier les variables d'environnement AZURE_TENANT_ID
- ✅ Vérifier l'Object ID dans AZURE_CLIENT_ID

#### Erreur: "Access denied to Azure AI resource"
- ⚠️ Il faut donner les permissions à la Managed Identity sur l'AI Resource
- 🔧 Solution: Utiliser les credentials déjà configurés dans GitHub Actions

### 🎯 Solution Rapide

#### Option A: Utiliser les credentials GitHub Actions
Les secrets GitHub sont déjà configurés :
- `AZUREAPPSERVICE_CLIENTID_E08E0CCEF05E4F8AB1F384EA6B507EE4`
- `AZUREAPPSERVICE_TENANTID_FD7F4D5D2BE9429CA4B13F8E14AD8372`

Ajoutez ces variables dans l'App Service :
```bash
AZURE_CLIENT_ID = E08E0CCEF05E4F8AB1F384EA6B507EE4
AZURE_TENANT_ID = FD7F4D5D2BE9429CA4B13F8E14AD8372
```

#### Option B: Mode Fallback (Solution temporaire)
Modifiez `config/settings.py` :
```python
# Force fallback mode for now
AZURE_AVAILABLE = False
```

### 📊 Status de l'Application

#### 🟢 Fonctionne en local avec Azure CLI
#### 🟡 Needs configuration sur Azure App Service
#### 🔵 Fallback mode disponible comme backup

### 🔗 URLs Importantes

- **App Service**: `https://web-app-group4.azurewebsites.net`
- **Azure Portal**: Console → `python test_azure_production.py`
- **Logs**: App Service → Monitoring → Log stream

### 💡 Notes de Production

1. **Managed Identity** est plus sécurisé que les secrets
2. **Environment Variables** sont persistantes après redémarrage
3. **Fallback mode** permet à l'app de fonctionner sans Azure AI
4. **Logs Azure** aident au debugging des auth issues 