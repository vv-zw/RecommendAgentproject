-- 011_series_and_episodes.sql
-- Create series_details and episodes tables

CREATE TABLE `series_details` (
    `medi-id` VARCHAR(36) NOT NULL,
    `number_of_seasons` INT NULL,
    `number_of_episodes` INT NULL,
    `last_air_date` DATE NULL,
    `first_air_date` DATE NULL,
    `origin_country` VARCHAR(100) NULL,
    PRIMARY KEY (`medi-id`),
    FOREIGN KEY (`medi-id`) REFERENCES `medi-items` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `episodes` (
    `id` VARCHAR(36) NOT NULL,
    `series_id` VARCHAR(36) NOT NULL,
    `season_number` INT NOT NULL,
    `episode_number` INT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `overview` TEXT NULL,
    `air_date` DATE NULL,
    `vote_average` DECIMAL(3, 1) NULL,
    `still_path` VARCHAR(255) NULL,
    PRIMARY KEY (`id`),
    FOREIGN KEY (`series_id`) REFERENCES `series_details` (`medi-id`) ON DELETE CASCADE,
    UNIQUE KEY `series_season_episode` (`series_id`, `season_number`, `episode_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
