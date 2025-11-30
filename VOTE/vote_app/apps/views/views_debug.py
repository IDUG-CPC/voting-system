from django.http import JsonResponse

def debug_view(request):
    return JsonResponse({
        "host": request.get_host(),
        "is_secure": request.is_secure(),
        "scheme": request.scheme,
        "path": request.path,
        "full_path": request.get_full_path(),
        "headers": {k: v for k, v in request.headers.items()},
    })

