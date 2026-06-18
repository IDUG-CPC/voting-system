
class SessionEventMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.session_event = request.session.get("session_event")
        return self.get_response(request)
