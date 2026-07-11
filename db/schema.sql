CREATE TABLE users (
  steam_id BIGINT PRIMARY KEY,
  country VARCHAR(2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE games(
  appid INT PRIMARY KEY,

  title VARCHAR(255),
  release_date DATE,
  price INT CHECK (price >= 0),
  total_achievements INT DEFAULT 0,

  genres TEXT[] DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',

  metacritic INT,
  positive_reviews INT,
  negative_reviews INT,

  developers TEXT[] DEFAULT '{}',
  publishers TEXT[] DEFAULT '{}',

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), 
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE user_game (
  steam_id BIGINT REFERENCES users(steam_id) ON DELETE CASCADE,
  appid INT REFERENCES games(appid) ON DELETE CASCADE,

  PRIMARY KEY (steam_id, appid),

  playtime_minutes INT DEFAULT 0 NOT NULL,
  last_played DATE,

  achievements_unlocked INT DEFAULT 0,

  engagement_score REAL, 

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bulk_user_game (
  bulk_user_id BIGINT NOT NULL,
  game_title VARCHAR(255) NOT NULL,
  playtime_hours REAL NOT NULL,

  PRIMARY KEY (bulk_user_id, game_title)
);

CREATE TABLE bulk_games (
  appid INT PRIMARY KEY,
  title TEXT,
  release_date DATE,
  price INT CHECK (price >= 0),
  total_achievements INT DEFAULT 0,

  genres TEXT[] DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',

  metacritic INT,
  positive_reviews INT,
  negative_reviews INT,
  developers TEXT[] DEFAULT '{}',
  publishers TEXT[] DEFAULT '{}',

  recommendations INT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE bulk_title_map (
    game_title TEXT PRIMARY KEY,
    appid INT NOT NULL REFERENCES bulk_games(appid),
    match_method VARCHAR(20) NOT NULL,
    match_score REAL
);