def format_duration_ms(duration_ms):
    """Converts duration from milliseconds to MM:SS string format."""
    if duration_ms is None:
        return "N/A"
    try:
        total_seconds = int(duration_ms) / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    except (ValueError, TypeError):
        return "N/A"


def get_release_year(release_date):
    """Extracts the year from a date object or string."""
    if release_date is None:
        return "N/A"
    if hasattr(release_date, "year"):  # If it's a date/datetime object
        return str(release_date.year)
    try:  # If it's a string like 'YYYY-MM-DD'
        year_str = str(release_date).split("-")[0]
        if year_str.isdigit() and len(year_str) == 4:
            return year_str
        else:
            return "N/A"
    except Exception:
        return "N/A"
