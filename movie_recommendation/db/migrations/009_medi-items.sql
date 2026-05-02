-- 009_medi-items.sql
-- Create medi-items table

CREATE TABLE `medi-items` (
    `id` VARCHAR(36) NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `original_title` VARCHAR(255) NULL,
    `media_type` ENUM('movie', 'series') NOT NULL,
    `poster_url` VARCHAR(255) NULL,
    `backdrop_url` VARCHAR(255) NULL,
    `overview` TEXT NULL,
    `release_date` DATE NULL,
    `vote_average` DECIMAL(3, 1) NULL,
    `vote_count` INT NULL,
    `popularity` DECIMAL(10, 3) NULL,
    `runtime` INT NULL,
    `status` VARCHAR(50) NULL,
    `tagline` VARCHAR(255) NULL,
    `external_id` VARCHAR(50) NULL,
    `created_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `external_id` (`external_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
