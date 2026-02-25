ALTER TABLE users CHANGE COLUMN hashed_password password_hash VARCHAR(128) NULL;
ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(128);
ALTER TABLE users CHANGE COLUMN birthday birth_date DATE NOT NULL;
ALTER TABLE users CHANGE COLUMN phone_number phone VARCHAR(20) NOT NULL;
ALTER TABLE users ADD COLUMN nickname VARCHAR(50) NULL AFTER phone;
ALTER TABLE users ADD UNIQUE INDEX email (email);
ALTER TABLE users ADD UNIQUE INDEX phone (phone);
