-- Drop tables if they exist to ensure a clean setup (optional)
DROP TABLE IF EXISTS track_genres;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS tracks;

-- Table to store track information
CREATE TABLE tracks (
    track_id SERIAL PRIMARY KEY, -- Auto-incrementing primary key
    original_track_uri TEXT UNIQUE, -- To store the 'Track URI' for unique identification
    track_name TEXT,
    artist_names TEXT, -- From 'Artist Name(s)'
    album_name TEXT,
    album_release_date DATE, -- To store 'Album Release Date'
    album_image_url TEXT,
    track_duration_ms INTEGER,
    explicit BOOLEAN,
    popularity INTEGER,
    youtube_title TEXT,
    youtube_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, -- Optional: timestamp for when the record was created
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP  -- Optional: timestamp for when the record was last updated
);

-- Table to store unique genre names
CREATE TABLE genres (
    genre_id SERIAL PRIMARY KEY, -- Auto-incrementing primary key
    genre_name TEXT UNIQUE NOT NULL -- Genre names must be unique and not null
);

-- Junction table to link tracks and genres (many-to-many relationship)
CREATE TABLE track_genres (
    track_id INTEGER REFERENCES tracks(track_id) ON DELETE CASCADE, -- Foreign key to tracks table
    genre_id INTEGER REFERENCES genres(genre_id) ON DELETE CASCADE, -- Foreign key to genres table
    PRIMARY KEY (track_id, genre_id) -- Composite primary key to ensure unique track-genre pairings
);

-- Optional: Create a trigger to automatically update the updated_at timestamp on tracks table
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tracks_modtime
BEFORE UPDATE ON tracks
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();

-- Optional: Indexes for frequently queried columns
CREATE INDEX IF NOT EXISTS idx_tracks_artist_names ON tracks(artist_names);
CREATE INDEX IF NOT EXISTS idx_tracks_album_name ON tracks(album_name);
CREATE INDEX IF NOT EXISTS idx_genres_genre_name ON genres(genre_name);
