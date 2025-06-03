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


def get_all_genres(app, cursor):
    """Fetches all unique genre names from the database."""
    try:
        cursor.execute("SELECT genre_name FROM genres ORDER BY genre_name ASC;")
        genres = cursor.fetchall()
        return genres
    except psycopg2.Error as e:
        app.logger.error(f"Error fetching genres: {e}")
        return []


def list_tracks_helper(app, items_per_page_default=10):
    """Displays a paginated, searchable, sortable, and filterable list of tracks."""
    conn = None
    try:
        conn = get_db_connection(app)
        cursor = conn.cursor()

        # Get all genres for the dropdown
        all_genres = get_all_genres(app, cursor)

        # Get query parameters
        page = request.args.get("page", 1, type=int)
        search_query = request.args.get("query", "").strip()
        sort_by = request.args.get("sort_by", "popularity_desc")
        # Use request.args.getlist for multiple selected values
        selected_genres = request.args.getlist("tags")
        items_per_page = request.args.get(
            "items_per_page", items_per_page_default, type=int
        )

        if page < 1:
            page = 1
        if items_per_page not in [10, 20, 50, 100]:
            items_per_page = items_per_page_default

        app.logger.info(
            f"Request for page: {page}, query: '{search_query}', sort_by: '{sort_by}', "
            f"selected_genres: '{selected_genres}', items_per_page: {items_per_page}"
        )

        # Build SQL query dynamically
        where_clauses = []
        query_params = []

        # Base query to fetch tracks
        from_clause = sql.SQL("FROM tracks t")

        # Determine if DISTINCT ON is needed
        needs_distinct_on = False
        if selected_genres:
            from_clause = sql.SQL(
                "FROM tracks t JOIN track_genres tg ON t.track_id = tg.track_id JOIN genres g ON tg.genre_id = g.genre_id"
            )
            where_clauses.append("g.genre_name = ANY(%s)")
            query_params.append(selected_genres)
            needs_distinct_on = True  # Set to True if genre filtering is active

        if search_query:
            where_clauses.append("(t.track_name ILIKE %s OR t.artist_names ILIKE %s)")
            query_params.extend([f"%{search_query}%", f"%{search_query}%"])

        # Build WHERE clause
        where_sql = sql.SQL("")
        if where_clauses:
            where_sql = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(
                map(sql.SQL, where_clauses)
            )

        # Build ORDER BY clause
        order_by_parts = []
        if needs_distinct_on:
            # When DISTINCT ON is used, track_id must be the first in ORDER BY
            order_by_parts.append(
                sql.SQL("t.track_id ASC")
            )  # Arbitrarily pick an order for track_id itself

        if sort_by == "popularity_desc":
            order_by_parts.append(sql.SQL("t.popularity DESC"))
            order_by_parts.append(sql.SQL("t.track_name ASC"))
        elif sort_by == "popularity_asc":
            order_by_parts.append(sql.SQL("t.popularity ASC"))
            order_by_parts.append(sql.SQL("t.track_name ASC"))
        elif sort_by == "track_name_asc":
            order_by_parts.append(sql.SQL("t.track_name ASC"))
        elif sort_by == "track_name_desc":
            order_by_parts.append(sql.SQL("t.track_name DESC"))
        elif sort_by == "album_release_date_desc":
            order_by_parts.append(sql.SQL("t.album_release_date DESC"))
            order_by_parts.append(sql.SQL("t.track_name ASC"))
        elif sort_by == "album_release_date_asc":
            order_by_parts.append(sql.SQL("t.album_release_date ASC"))
            order_by_parts.append(sql.SQL("t.track_name ASC"))
        else:  # Default sort
            order_by_parts.append(sql.SQL("t.popularity DESC"))
            order_by_parts.append(sql.SQL("t.track_name ASC"))

        order_by_sql = sql.SQL(" ORDER BY ") + sql.SQL(", ").join(order_by_parts)

        # Count total tracks matching the criteria
        count_query_select = (
            sql.SQL("SELECT COUNT(DISTINCT t.track_id)")
            if needs_distinct_on
            else sql.SQL("SELECT COUNT(*)")
        )
        count_query = count_query_select + from_clause + where_sql + sql.SQL(";")

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
        select_distinct_clause = (
            sql.SQL("SELECT DISTINCT ON (t.track_id)")
            if needs_distinct_on
            else sql.SQL("SELECT")
        )
        query = sql.SQL(
            """
            {select_distinct_clause}
                t.track_id,
                t.track_name,
                t.artist_names,
                t.album_name,
                t.album_release_date,
                t.album_image_url,
                t.track_duration_ms,
                t.explicit,
                t.popularity
            {from_clause}
            {where_clause}
            {order_by_clause}
            LIMIT %s OFFSET %s;
        """
        ).format(
            select_distinct_clause=select_distinct_clause,
            from_clause=from_clause,
            where_clause=where_sql,
            order_by_clause=order_by_sql,
        )

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
            selected_genres=selected_genres,
            all_genres=all_genres,
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
