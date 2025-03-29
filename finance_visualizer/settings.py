# CORS settings
CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)

# Explicitly add localhost to allowed origins if not already present
if not CORS_ALLOWED_ORIGINS or not any(origin.startswith('http://localhost:') for origin in CORS_ALLOWED_ORIGINS):
    # Convert to list if it's not already
    if not isinstance(CORS_ALLOWED_ORIGINS, list):
        CORS_ALLOWED_ORIGINS = list(CORS_ALLOWED_ORIGINS) if CORS_ALLOWED_ORIGINS else []
    
    # Add common localhost origins
    for port in [3000, 3001, 3002, 5000, 8000, 8080]:
        origin = f'http://localhost:{port}'
        if origin not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(origin)

# Additional CORS settings for development
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Allow all origins in development mode

# Make sure we're adding the most liberal CORS settings in development
if DEBUG:
    print("DEBUG mode enabled: Using permissive CORS settings")
    # Force allow all origins to be certain
    CORS_ALLOW_ALL_ORIGINS = True
    # Alternative approach: explicitly add the origin that's having issues
    if 'http://localhost:3001' not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append('http://localhost:3001')
    print(f"CORS_ALLOWED_ORIGINS: {CORS_ALLOWED_ORIGINS}")

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_EXPOSE_HEADERS = [
    'content-length', 
    'content-type'
] 