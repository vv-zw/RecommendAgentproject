-- 010_media_genres.sql
-- Create media_genres table

CREATE TABLE `media_genres` (
    `medi-id` VARCHAR(36) NOT NULL,
    `genre_id` INT NOT NULL,
    PRIMARY KEY (`medi-id`, `genre_id`),
    FOREIGN KEY (`medi-id`) REFERENCES `medi-items` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`genre_id`) REFERENCES `genres` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
