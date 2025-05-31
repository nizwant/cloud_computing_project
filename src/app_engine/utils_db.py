import os
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2 import sql
from flask import render_template, request, url_for
import math
from google.cloud import secretmanager


from utils_misc import format_duration_ms, get_release_year, get_secret


# --- Database Connection Parameters ---
client = secretmanager.SecretManagerServiceClient()
DB_NAME = os.getenv("DB_NAME", "database-instance")
DB_USER = get_secret("DB_USER", "cloud-computing-project-458205", client).strip()
DB_PASSWORD = get_secret(
    "DB_PASSWORD", "cloud-computing-project-458205", client
).strip()
DB_HOST = get_secret("DB_HOST", "cloud-computing-project-458205", client).strip()
DB_PORT = os.getenv("DB_PORT", "5432")


def get_db_connection(app):
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            cursor_factory=DictCursor,  # Use DictCursor to access columns by name
        )
        app.logger.info(
            f"Successfully connected to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}."
        )
        return conn
    except psycopg2.OperationalError as e:
        app.logger.error(f"Database connection failed: {e}")
        raise


def list_tracks_helper(app, items_per_page_default=10):
    """Displays a paginated, searchable, sortable, and filterable list of tracks."""
    conn = None
    try:
        conn = get_db_connection(app)
        cursor = conn.cursor()

        # Get query parameters
        page = request.args.get("page", 1, type=int)
        search_query = request.args.get("query", "").strip()
        sort_by = request.args.get("sort_by", "popularity_desc")
        tags_filter = request.args.get("tags", "").strip()
        items_per_page = request.args.get(
            "items_per_page", items_per_page_default, type=int
        )

        if page < 1:
            page = 1
        if items_per_page not in [10, 20, 50, 100]:
            items_per_page = items_per_page_default

        app.logger.info(
            f"Request for page: {page}, query: '{search_query}', sort_by: '{sort_by}', "
            f"tags: '{tags_filter}', items_per_page: {items_per_page}"
        )

        # Build SQL query dynamically
        where_clauses = []
        query_params = []

        if search_query:
            where_clauses.append("(track_name ILIKE %s OR artist_names ILIKE %s)")
            query_params.extend([f"%{search_query}%", f"%{search_query}%"])

        if tags_filter:
            # Assuming 'tags' is a comma-separated string in the URL
            # and 'track_tags' is a text array or similar in your DB
            # For simplicity, let's assume `track_tags` is a TEXT field in the DB
            # and we search for any of the provided tags.
            # You might need to adjust this based on how tags are stored in your DB.
            tags_list = [tag.strip() for tag in tags_filter.split(",") if tag.strip()]
            if tags_list:
                tag_conditions = []
                for tag in tags_list:
                    tag_conditions.append(
                        "track_tags ILIKE %s"
                    )  # Assuming track_tags is a TEXT field
                    query_params.append(f"%{tag}%")
                where_clauses.append(f"({' OR '.join(tag_conditions)})")

        # Build WHERE clause
        where_sql = sql.SQL("")
        if where_clauses:
            where_sql = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(
                map(sql.SQL, where_clauses)
            )

        # Build ORDER BY clause
        order_by_sql = sql.SQL("")
        if sort_by == "popularity_desc":
            order_by_sql = sql.SQL(" ORDER BY popularity DESC, track_name ASC")
        elif sort_by == "popularity_asc":
            order_by_sql = sql.SQL(" ORDER BY popularity ASC, track_name ASC")
        elif sort_by == "track_name_asc":
            order_by_sql = sql.SQL(" ORDER BY track_name ASC")
        elif sort_by == "track_name_desc":
            order_by_sql = sql.SQL(" ORDER BY track_name DESC")
        elif sort_by == "album_release_date_desc":
            order_by_sql = sql.SQL(" ORDER BY album_release_date DESC, track_name ASC")
        elif sort_by == "album_release_date_asc":
            order_by_sql = sql.SQL(" ORDER BY album_release_date ASC, track_name ASC")
        else:
            order_by_sql = sql.SQL(
                " ORDER BY popularity DESC, track_name ASC"
            )  # Default

        # Count total tracks matching the criteria
        count_query = sql.SQL("SELECT COUNT(*) FROM tracks") + where_sql + sql.SQL(";")
        cursor.execute(count_query, tuple(query_params))
        total_tracks_result = cursor.fetchone()
        total_tracks = total_tracks_result[0] if total_tracks_result else 0
        app.logger.info(f"Total tracks found for criteria: {total_tracks}")

        total_pages = (
            math.ceil(total_tracks / items_per_page) if total_tracks > 0 else 1
        )

        if page > total_pages and total_tracks > 0:
            app.logger.info(
                f"Requested page {page} is out of bounds, {total_pages} total. Setting to last page"
            )
            page = total_pages

        offset = (page - 1) * items_per_page
        if offset < 0:  # Ensure offset is not negative
            offset = 0

        # Main query for fetching tracks
        query = sql.SQL(
            """
            SELECT
                track_id,
                track_name,
                artist_names,
                album_name,
                album_release_date,
                album_image_url,
                track_duration_ms,
                explicit,
                popularity
            FROM tracks
            {where_clause}
            {order_by_clause}
            LIMIT %s OFFSET %s;
        """
        ).format(where_clause=where_sql, order_by_clause=order_by_sql)

        cursor.execute(query, tuple(query_params + [items_per_page, offset]))
        tracks_data = cursor.fetchall()
        app.logger.info(f"Fetched {len(tracks_data)} tracks for page {page}.")

        display_tracks = []
        for track in tracks_data:
            display_tracks.append(
                {
                    "id": track["track_id"],
                    "name": track["track_name"],
                    "artists": track["artist_names"],
                    "album_image_url": (
                        track["album_image_url"]
                        if track["album_image_url"]
                        else url_for("static", filename="no_image.jpg")
                    ),  # Using a local placeholder
                    "release_year": get_release_year(track["album_release_date"]),
                    "duration": format_duration_ms(track["track_duration_ms"]),
                    "explicit": track["explicit"],
                }
            )

        cursor.close()

        return render_template(
            "list_songs.html",
            tracks=display_tracks,
            current_page=page,
            total_pages=total_pages,
            total_tracks=total_tracks,
            query=search_query,
            sort_by=sort_by,
            tags=tags_filter,
            items_per_page=items_per_page,
        )

    except psycopg2.Error as e:
        app.logger.error(f"Database error in list_songs: {e}")
        if conn:
            conn.rollback()
        return (
            "<h1>500 - Internal Server Error</h1><p>A database error occurred.</p>",
            500,
        )
    except Exception as e:
        app.logger.error(f"An unexpected error occurred in list_songs: {e}")
        if conn:
            conn.rollback()
        return (
            "<h1>500 - Internal Server Error</h1><p>A database error occurred.</p>",
            500,
        )
    finally:
        if conn:
            conn.close()
            app.logger.info("Database connection closed.")


def check_if_song_exists(app, title, artist):
    conn = None
    try:
        conn = get_db_connection(app)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM tracks
            WHERE track_name ILIKE %s AND artist_names ILIKE %s
        """,
            (title, artist),
        )

        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            return {
                "status": "warning",
                "message": f"Song {title} by {artist} already exists in the database.",
            }

        return {
            "status": "success",
            "message": f"Success, song {title} by {artist} will be processed shortly!",
        }

    except Exception as e:
        app.logger.error(f"Error in push_to_pub_sub: {e}")
        return {"status": "error", "message": "Failed to process request."}
