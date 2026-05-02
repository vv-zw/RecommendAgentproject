-- 013_watch_history.sql
-- Create watch_history table

CREATE TABLE `watch_history` (
    `id` VARCHAR(36) NOT NULL,
    `user_id` VARCHAR(36) NOT NULL,
    `medi-id` VARCHAR(36) NOT NULL,
    `watched_at` DATETIME NULL DEFAULT CURRENT_TIMESTAMP,
    `progress_seconds` INT NULL,
    `completed` TINYINT(1) NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    FOREIGN KEY (`medi-id`) REFERENCES `medi-items` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
