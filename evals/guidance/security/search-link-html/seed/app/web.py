"""HTTP handlers: `term` arrives straight from the query string."""
from app import views


def no_results(request):
    term = request.args.get("q", "")
    return views.render_title("Help center") + views.render_search_link(term)
