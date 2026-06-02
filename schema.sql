CREATE DATABASE IF NOT EXISTS robot_fleet;
USE robot_fleet;

CREATE TABLE IF NOT EXISTS robots (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(20) NOT NULL,
  model VARCHAR(30),
  status ENUM('active','idle','offline','error') DEFAULT 'idle',
  battery INT DEFAULT 100,
  location VARCHAR(50),
  last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS missions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  robot_id INT,
  start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  end_time TIMESTAMP NULL,
  status ENUM('running','completed','failed') DEFAULT 'running',
  distance_m FLOAT DEFAULT 0,
  FOREIGN KEY (robot_id) REFERENCES robots(id)
);

CREATE TABLE IF NOT EXISTS incidents (
  id INT PRIMARY KEY AUTO_INCREMENT,
  robot_id INT,
  type VARCHAR(50),
  severity ENUM('low','medium','critical'),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMP NULL,
  notes TEXT,
  FOREIGN KEY (robot_id) REFERENCES robots(id)
);

CREATE TABLE IF NOT EXISTS metrics (
  id INT PRIMARY KEY AUTO_INCREMENT,
  robot_id INT,
  battery INT,
  cpu_temp FLOAT,
  speed_ms FLOAT,
  recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (robot_id) REFERENCES robots(id)
);

INSERT INTO robots (name, model, status, battery, location) VALUES
('AMR-01', 'Sherpa 100', 'idle', 100, 'Dock-A'),
('AMR-02', 'Sherpa 100', 'idle', 100, 'Dock-B'),
('AMR-03', 'Sherpa 200', 'idle', 100, 'Dock-C'),
('AMR-04', 'Sherpa 200', 'idle', 100, 'Dock-D'),
('AMR-05', 'Sherpa 300', 'idle', 100, 'Dock-E');