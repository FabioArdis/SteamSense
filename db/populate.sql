-- populate from exact
INSERT INTO bulk_title_map (game_title, appid, match_method, match_score)
SELECT DISTINCT bug.game_title, bg.appid, 'exact', 100.0
FROM bulk_user_game bug
JOIN bulk_games bg ON bug.game_title = bg.title
ON CONFLICT (game_title) DO NOTHING;

-- populate from normalized
INSERT INTO bulk_title_map (game_title, appid, match_method, match_score)
SELECT DISTINCT bug.game_title, bg.appid, 'normalized', 95.0
FROM bulk_user_game bug
JOIN bulk_games bg
    ON TRIM(regexp_replace(lower(bug.game_title), '[^a-z0-9 ]', '', 'g'))
     = TRIM(regexp_replace(lower(bg.title), '[^a-z0-9 ]', '', 'g'))
WHERE bug.game_title NOT IN (SELECT game_title FROM bulk_title_map)
ON CONFLICT (game_title) DO NOTHING;