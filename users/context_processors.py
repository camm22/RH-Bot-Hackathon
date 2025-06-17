def show_navbar(request):
    excluded_paths = ['/', '/login/', '/register/']
    return {
        'show_navbar': request.path not in excluded_paths
    }
