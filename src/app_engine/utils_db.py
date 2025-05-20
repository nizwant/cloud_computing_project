import os
import psycopg2
from psycopg2.extras import DictCursor
from psycopg2 import sql
from flask import render_template, request, url_for
import math
from dotenv import load_dotenv

from utils_misc import format_duration_ms, get_release_year


load_dotenv()

# --- Database Connection Parameters ---
DB_NAME = os.getenv("DB_NAME", "database-instance")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
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


def list_tracks_helper(app, items_per_page):
    """Displays a paginated list of tracks."""
    conn = None
    try:
        conn = get_db_connection(app)
        cursor = conn.cursor()

        try:
            page = int(request.args.get("page", 1))
            if page < 1:
                page = 1
        except ValueError:
            page = 1
        app.logger.info(f"Request for page: {page}")

        offset = (page - 1) * items_per_page

        cursor.execute("SELECT COUNT(*) FROM tracks;")
        total_tracks_result = cursor.fetchone()
        total_tracks = total_tracks_result[0] if total_tracks_result else 0
        app.logger.info(f"Total tracks found: {total_tracks}")

        total_pages = (
            math.ceil(total_tracks / items_per_page) if total_tracks > 0 else 1
        )

        if page > total_pages and total_tracks > 0:
            app.logger.info(
                f"Requested page {page} is out of bounds ({total_pages} total). Setting to last page."
            )
            page = total_pages
            offset = (page - 1) * items_per_page

        # Using psycopg2.sql for safe query construction
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
            ORDER BY popularity DESC, track_name ASC
            LIMIT %s OFFSET %s;
        """
        )
        cursor.execute(query, (items_per_page, offset))
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
                        else url_for("static", filename="architecture.png")
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
        )

    except psycopg2.Error as e:
        app.logger.error(f"Database error in list_songs: {e}")
        if conn:
            conn.rollback()
        return (
            "<h1>500 - Internal Server Error</h1><p>A database error occurred. Please try again later.</p>",
            500,
        )
    except Exception as e:
        app.logger.error(f"An unexpected error occurred in list_songs: {e}")
        if conn:
            conn.rollback()
        return (
            "<h1>500 - Internal Server Error</h1><p>A database error occurred. Please try again later.</p>",
            500,
        )
    finally:
        if conn:
            conn.close()
            app.logger.info("Database connection closed.")
