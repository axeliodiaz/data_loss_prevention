CREATE DATABASE IF NOT EXISTS dlp_project;
CREATE DATABASE IF NOT EXISTS test_dlp_project;

GRANT ALL PRIVILEGES ON dlp_project.* TO 'admin'@'%';
GRANT ALL PRIVILEGES ON test_dlp_project.* TO 'admin'@'%';
FLUSH PRIVILEGES;