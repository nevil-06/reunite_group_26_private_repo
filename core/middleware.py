import datetime

class UserHistoryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the current date
        current_date = datetime.date.today().strftime('%Y-%m-%d')

        # Get the user's visit history from the session
        visit_history = request.session.get('visit_history', {})

        # Increment the visit count for the current date
        if current_date in visit_history:
            visit_history[current_date] += 1
        else:
            visit_history[current_date] = 1

        # Save the updated visit history back to the session
        request.session['visit_history'] = visit_history

        # Continue processing the request
        response = self.get_response(request)

        return response
